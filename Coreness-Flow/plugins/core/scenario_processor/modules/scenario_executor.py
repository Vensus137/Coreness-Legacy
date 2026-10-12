"""Исполнитель сценариев"""

import asyncio
from typing import Any, Callable, Dict, Optional, Tuple


class ScenarioExecutor:
    """
    Исполнитель сценариев
    - Выполнение сценариев по ID и по имени
    - Координация выполнения шагов
    - Обработка переходов между шагами
    """
    
    def __init__(self, logger, step_executor, transition_handler, cache_manager, scenario_timeout: float = 0):
        self.logger = logger
        self.step_executor = step_executor
        self.transition_handler = transition_handler
        self.cache_manager = cache_manager
        self.scenario_timeout = scenario_timeout  # 0 — без таймаута
    
    async def execute_scenario(self, scenario_id: int, event: Dict[str, Any], scenario_metadata: Dict[str, Any], execute_scenario_by_name_func: Callable) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Выполнение сценария по ID. Возвращает кортеж (result, cache)"""
        if self.scenario_timeout > 0:
            try:
                return await asyncio.wait_for(
                    self._execute_scenario_impl(scenario_id, event, scenario_metadata, execute_scenario_by_name_func),
                    timeout=self.scenario_timeout
                )
            except asyncio.TimeoutError:
                self.logger.warning(f"Таймаут выполнения сценария {scenario_id} ({self.scenario_timeout} с)")
                return ('error', None)
        return await self._execute_scenario_impl(scenario_id, event, scenario_metadata, execute_scenario_by_name_func)
    
    async def _execute_scenario_impl(self, scenario_id: int, event: Dict[str, Any], scenario_metadata: Dict[str, Any], execute_scenario_by_name_func: Callable) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Внутренняя реализация выполнения сценария по ID."""
        try:
            # Использование метаданных сценария для изолированной обработки
            scenario_data = scenario_metadata['scenario_index'].get(scenario_id)
            if not scenario_data:
                self.logger.warning(f"Сценарий {scenario_id} не найден в индексе")
                return ('error', None)
            
            # Получение шагов сценария (tuple)
            step = scenario_data.get('step', ())
            if not step:
                self.logger.warning(f"Сценарий {scenario_id} не имеет шагов")
                return ('error', None)
            
            # Сортировка шагов по порядку
            sorted_step = sorted(step, key=lambda x: x.get('step_order', 0))
            
            scenario_name = scenario_data.get('data', {}).get('name', f'Scenario {scenario_id}')
            
            # Создание копии события для накопления данных между шагами
            data = event.copy()
            data['_scenario_metadata'] = scenario_metadata  # Добавить метаданные для использования в execute_scenario
            if '_cache' not in data:
                data['_cache'] = {}
            # Инициализация цепочки сценариев для отладки
            if 'scenario_chain' not in data or not isinstance(data.get('scenario_chain'), list):
                data['scenario_chain'] = [scenario_name]
            else:
                data['scenario_chain'] = data['scenario_chain'].copy()
                data['scenario_chain'].append(scenario_name)
            
            # Выполнение каждого шага
            i = 0
            while i < len(sorted_step):
                step_data = sorted_step[i]
                params = step_data.get('params', {})
                
                # Выполнение шага
                step_result = await self.step_executor.execute_step(step_data, data)
                transition = step_data.get('transition', [])
                
                # Слияние response_data в _cache
                response_data = step_result.get('response_data', {})
                if response_data:
                    self.cache_manager.merge_response_data(
                        response_data=response_data,
                        data=data,
                        action_name=step_data.get('action_name'),
                        params=params
                    )
                
                # Добавление ошибки из действия в атрибут last_error
                error = step_result.get('error')
                if error is not None:
                    data['last_error'] = error
                
                # Добавление результата выполнения действия в атрибут last_result
                result = step_result.get('result')
                if result is not None:
                    data['last_result'] = result

                # Логирование ошибки действия с указанием сценария для удобства отладки
                if result == 'error' and error:
                    err_code = error.get('code', 'UNKNOWN')
                    err_msg = error.get('message', '')
                    action_name = step_data.get('action_name', step_data.get('action', '?'))
                    self.logger.warning(
                        "Сценарий '%s': действие '%s' вернуло ошибку: %s — %s",
                        scenario_name,
                        action_name,
                        err_code,
                        err_msg,
                    )
                
                # Проверка response_data на abort из execute_scenario
                scenario_result = response_data.get('scenario_result')
                if scenario_result == 'abort':
                    cache = self.cache_manager.extract_cache(data)
                    return ('abort', cache)
                
                # Обработка переходов на основе результата шага
                transition_result = await self.transition_handler.process_transitions(
                    step_result.get('result'),
                    transition
                )
                transition_action = transition_result.get('action', 'continue')
                transition_value = transition_result.get('value')
                
                # Обработка переходов
                if transition_action == 'abort':
                    result, cache = await self.transition_handler.handle_stop_abort_break('abort', data)
                    return (result, cache)
                    
                elif transition_action == 'break':
                    result, cache = await self.transition_handler.handle_stop_abort_break('break', data)
                    return (result, cache)
                    
                elif transition_action == 'jump_to_scenario':
                    result, cache = await self.transition_handler.handle_jump_to_scenario(
                        transition_value=transition_value,
                        data=data,
                        scenario_metadata=scenario_metadata,
                        execute_scenario_by_name_func=execute_scenario_by_name_func
                    )
                    
                    if result == 'continue':
                        i += 1
                        continue
                    else:
                        return (result, cache)
                    
                elif transition_action == 'execute_scenario':
                    result, cache = await self.transition_handler.handle_execute_scenario(
                        transition_value=transition_value,
                        data=data,
                        step_executor=self.step_executor,
                        cache_manager=self.cache_manager
                    )
                    
                    if result == 'continue':
                        i += 1
                        continue
                    else:
                        return (result, cache)
                    
                elif transition_action == 'move_steps':
                    result, new_index, cache = await self.transition_handler.handle_move_steps(
                        transition_value=transition_value,
                        current_index=i,
                        sorted_step=sorted_step,
                        data=data
                    )
                    
                    if result == 'continue':
                        i = new_index
                        continue
                    else:
                        return ('success', cache)
                    
                elif transition_action == 'jump_to_step':
                    result, new_index, cache = await self.transition_handler.handle_jump_to_step(
                        transition_value=transition_value,
                        sorted_step=sorted_step,
                        data=data
                    )
                    
                    if result == 'continue':
                        i = new_index
                        continue
                    else:
                        return ('success', cache)
                
                # Продолжение со следующим шагом
                i += 1
            
            # Возврат только _cache из финальных данных
            cache = self.cache_manager.extract_cache(data)
            return ('success', cache)
                
        except Exception as e:
            self.logger.error(f"Ошибка выполнения сценария {scenario_id}: {e}")
            try:
                cache = self.cache_manager.extract_cache(data)
            except (NameError, UnboundLocalError):
                cache = None
            return ('error', cache)
    
    async def execute_scenario_by_name(self, scenario_name: str, data: Dict[str, Any], scenario_metadata: Dict[str, Any], execute_scenario_func: Callable) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Поиск и выполнение сценария по имени. Возвращает кортеж (result, cache)"""
        try:
            if scenario_metadata is None:
                return ('error', None)
            
            scenario_name_index = scenario_metadata['scenario_name_index']
            
            # Быстрый O(1) поиск через индекс
            if scenario_name not in scenario_name_index:
                self.logger.warning(f"Сценарий '{scenario_name}' не найден")
                return ('error', None)
            
            target_scenario_id = scenario_name_index[scenario_name]
            
            # Создание копии данных для передачи в сценарий
            data = data.copy()
            
            result, cache = await execute_scenario_func(
                scenario_id=target_scenario_id,
                event=data,
                scenario_metadata=scenario_metadata
            )
            
            return (result, cache)
            
        except Exception as e:
            self.logger.error(f"Ошибка выполнения сценария '{scenario_name}': {e}")
            return ('error', None)
