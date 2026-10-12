"""Исполнитель шагов сценариев"""

import asyncio
from typing import Any, Dict


class StepExecutor:
    """
    Исполнитель шагов сценариев
    - Выполнение шагов с обработкой плейсхолдеров
    - Обработка синхронных и асинхронных действий
    """
    
    def __init__(self, logger, api_bus, step_timeout: float = 0):
        self.logger = logger
        self.api_bus = api_bus
        self.step_timeout = step_timeout  # 0 — без таймаута
    
    async def execute_step(self, step: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение шага сценария с обработкой плейсхолдеров"""
        try:
            # Валидация шага
            if not step or not isinstance(step, dict):
                self.logger.warning("Получен невалидный шаг")
                return {
                    'result': 'error',
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Невалидный шаг'
                    }
                }
            
            action_name = step.get('action_name')
            if not action_name:
                self.logger.warning("Шаг не содержит action_name")
                return {
                    'result': 'error',
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Отсутствует action_name'
                    }
                }
            
            params = step.get('params', {})
            
            # Проверка флага async
            is_async = step.get('async', False)
            action_id = step.get('action_id')  # Уникальный ID для отслеживания async-действий
            
            # Обработка плейсхолдеров в параметрах шага
            processed_params = await self._process_placeholders(params, data)
            
            # Слияние накопленных данных с обработанными параметрами шага
            action_data = {**data, **processed_params}
            
            # Защита системных атрибутов от перезаписи (защита от инъекций)
            if 'system' in data:
                action_data['system'] = data['system']  # Восстановить оригинальные system данные
            
            # Если async - запустить асинхронно и сохранить Future
            if is_async:
                if not action_id:
                    self.logger.warning("Async-действие требует action_id")
                    return {
                        'result': 'error',
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'message': 'Отсутствует action_id для async-действия'
                        }
                    }
                
                return await self._with_step_timeout(
                    self.execute_action_async(action_name, action_data, action_id)
                )
            else:
                return await self._with_step_timeout(
                    self.execute_action(action_name, action_data)
                )
            
        except Exception as e:
            self.logger.error(f"Ошибка выполнения шага {step.get('step_id', 'unknown')}: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Внутренняя ошибка: {str(e)}'
                }
            }
    
    async def _process_placeholders(self, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка плейсхолдеров в параметрах через placeholder_processor"""
        try:
            # Вызов placeholder_processor через API Bus
            result = await self.api_bus.call('process_placeholders_full', {
                'data': params,
                'values': data
            })
            
            if result.get('result') == 'success':
                response_data = result.get('response_data', {})
                return response_data.get('data', params)
            else:
                self.logger.warning(f"Ошибка обработки плейсхолдеров: {result.get('error')}")
                return params
                
        except Exception as e:
            self.logger.error(f"Ошибка вызова placeholder_processor: {e}")
            return params
    
    async def _with_step_timeout(self, coro):
        """Обёртка с таймаутом на выполнение шага."""
        if self.step_timeout <= 0:
            return await coro
        try:
            return await asyncio.wait_for(coro, timeout=self.step_timeout)
        except asyncio.TimeoutError:
            self.logger.warning(f"Таймаут выполнения шага ({self.step_timeout} с)")
            return {
                'result': 'timeout',
                'error': {
                    'code': 'TIMEOUT',
                    'message': f'Превышен таймаут шага ({self.step_timeout} с)'
                }
            }
    
    async def execute_action(self, action_name: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение действия через API Bus"""
        try:
            result = await self.api_bus.call(action_name, action_data)
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка выполнения действия {action_name}: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Внутренняя ошибка: {str(e)}'
                }
            }
    
    async def execute_action_async(self, action_name: str, action_data: Dict[str, Any], action_id: str) -> Dict[str, Any]:
        """Запуск действия асинхронно; сохраняется concurrent.futures.Future, чтобы wait_for_action можно было вызывать из любого event loop."""
        try:
            current_async_action = action_data.get('_async_action', {})
            # submit_action возвращает concurrent.futures.Future — безопасно для ожидания из любого loop
            future = self.api_bus.submit_action(action_name, action_data)
            current_async_action[action_id] = future
            return {
                'result': 'success',
                'response_data': {
                    '_async_action': current_async_action
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска async-действия {action_name}: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Внутренняя ошибка: {str(e)}'
                }
            }
