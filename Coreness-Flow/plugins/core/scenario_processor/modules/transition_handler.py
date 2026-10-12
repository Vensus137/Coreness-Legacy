"""Обработчик переходов между шагами сценария"""

from typing import Any, Dict, List, Optional, Tuple


class TransitionHandler:
    """
    Обработчик переходов между шагами сценария
    - Парсинг переходов по результату действия
    - Обработка всех типов переходов
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def process_transitions(self, action_result: str, transition: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Обработка переходов по результату действия. Возвращает словарь с ключами action и value"""
        try:
            # Сначала ищем переход "any" - он обрабатывается первым
            any_transition = None
            matching_transition = None
            
            for transition_data in transition:
                if transition_data.get('action_result') == 'any':
                    any_transition = transition_data
                elif transition_data.get('action_result') == action_result:
                    matching_transition = transition_data
            
            # Используем "any" переход если есть, иначе ищем по action result
            final_transition = any_transition if any_transition else matching_transition
            
            if not final_transition:
                return {'action': 'continue', 'value': None}
            
            transition_action = final_transition.get('transition_action', 'continue')
            transition_value = final_transition.get('transition_value')
            
            # Выполнение перехода (stop убран — сценарии по событию работают независимо)
            if transition_action == 'continue':
                return {'action': 'continue', 'value': None}
                
            elif transition_action == 'break':
                return {'action': 'break', 'value': None}
                
            elif transition_action == 'abort':
                return {'action': 'abort', 'value': None}
                
            elif transition_action == 'jump_to_scenario':
                if not transition_value:
                    return {'action': 'continue', 'value': None}
                return {'action': 'jump_to_scenario', 'value': transition_value}
                
            elif transition_action == 'execute_scenario':
                if not transition_value:
                    return {'action': 'continue', 'value': None}
                return {'action': 'execute_scenario', 'value': transition_value}
                
            elif transition_action == 'move_steps':
                return {'action': 'move_steps', 'value': transition_value}
            
            elif transition_action == 'jump_to_step':
                return {'action': 'jump_to_step', 'value': transition_value}
                
            else:
                return {'action': 'continue', 'value': None}
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки переходов: {e}")
            return {'action': 'continue', 'value': None}
    
    async def handle_stop_abort_break(self, transition_action: str, data: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Обработка переходов abort, break. Возвращает кортеж (result, cache)"""
        cache = data.get('_cache') if isinstance(data.get('_cache'), dict) else None
        return (transition_action, cache)
    
    async def handle_jump_to_scenario(self, transition_value: Any, data: Dict[str, Any], scenario_metadata: Dict[str, Any], execute_scenario_by_name_func) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Обработка перехода jump_to_scenario. Возвращает кортеж (result, cache)"""
        if not transition_value:
            return ('continue', None)
        
        if isinstance(transition_value, str):
            # Одиночный сценарий
            jump_data = data.copy()
            jump_result, jump_cache = await execute_scenario_by_name_func(
                scenario_name=transition_value,
                data=jump_data,
                scenario_metadata=scenario_metadata
            )
            
            # Если переходный сценарий вернул abort — передать дальше
            if jump_result == 'abort':
                cache = jump_cache if jump_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
                return (jump_result, cache)
            
            # Текущий сценарий завершён успешно - вернуть кэш из jump или из data
            cache = jump_cache if jump_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
            return ('success', cache)
            
        elif isinstance(transition_value, list):
            # Массив сценариев - выполнить последовательно
            last_cache = None
            jump_data = data.copy()
            
            for scenario_name in transition_value:
                jump_result, jump_cache = await execute_scenario_by_name_func(
                    scenario_name=scenario_name,
                    data=jump_data,
                    scenario_metadata=scenario_metadata
                )
                
                # Сохранить последний кэш
                if jump_cache:
                    last_cache = jump_cache
                
                # Если любой переходный сценарий вернул abort — прервать цепочку
                if jump_result == 'abort':
                    cache = last_cache if last_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
                    return (jump_result, cache)
            
            # Все сценарии завершены успешно - вернуть последний кэш или из data
            cache = last_cache if last_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
            return ('success', cache)
        else:
            self.logger.warning(f"Неверный тип transition_value для jump_to_scenario: {type(transition_value)}, ожидается str или list")
            return ('continue', None)
    
    async def handle_move_steps(self, transition_value: Any, current_index: int, sorted_step: List[Dict[str, Any]], data: Dict[str, Any]) -> Tuple[str, Optional[int], Optional[Dict[str, Any]]]:
        """Обработка перехода move_steps. Возвращает кортеж (result, new_index, cache)"""
        step_count = transition_value or 1
        try:
            step_count = int(step_count)
        except (ValueError, TypeError):
            step_count = 1
        
        new_index = current_index + step_count
        
        # Проверка границ
        if 0 <= new_index < len(sorted_step):
            return ('continue', new_index, None)
        elif new_index < 0:
            return ('continue', 0, None)
        else:
            cache = data.get('_cache') if isinstance(data.get('_cache'), dict) else None
            return ('success', None, cache)
    
    async def handle_jump_to_step(self, transition_value: Any, sorted_step: List[Dict[str, Any]], data: Dict[str, Any]) -> Tuple[str, Optional[int], Optional[Dict[str, Any]]]:
        """Обработка перехода jump_to_step. Возвращает кортеж (result, new_index, cache)"""
        step_index = transition_value
        try:
            step_index = int(step_index)
        except (ValueError, TypeError):
            return ('continue', None, None)
        
        if 0 <= step_index < len(sorted_step):
            return ('continue', step_index, None)
        else:
            cache = data.get('_cache') if isinstance(data.get('_cache'), dict) else None
            return ('success', None, cache)
    
    async def handle_execute_scenario(self, transition_value: Any, data: Dict[str, Any], step_executor, cache_manager) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Обработка перехода execute_scenario через вызов действия execute_scenario.
        Выполняет сценарий и возвращается к текущему сценарию.
        Возвращает кортеж (result, cache)
        """
        if not transition_value:
            return ('continue', None)
        
        try:
            # Создание виртуального шага для вызова действия execute_scenario
            virtual_step = {
                'action_name': 'execute_scenario',
                'params': {
                    'scenario': transition_value,
                    'return_cache': True,  # Всегда возвращать кэш для слияния
                }
            }
            
            # Выполнение через StepExecutor (как обычный шаг)
            step_result = await step_executor.execute_step(virtual_step, data)
            
            # Слияние response_data в _cache (как в обычном шаге)
            response_data = step_result.get('response_data', {})
            if response_data:
                cache_manager.merge_response_data(
                    response_data=response_data,
                    data=data,  # Кэш автоматически сливается в data!
                    action_name='execute_scenario',
                    params=virtual_step['params']
                )
            
            # Проверка scenario_result на abort
            scenario_result = response_data.get('scenario_result')
            if scenario_result == 'abort':
                cache = cache_manager.extract_cache(data)
                return ('abort', cache)

            # Продолжение выполнения текущего сценария
            return ('continue', None)
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки перехода execute_scenario: {e}")
            return ('continue', None)
