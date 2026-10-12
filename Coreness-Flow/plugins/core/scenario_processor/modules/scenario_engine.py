"""Движок обработки событий по сценариям"""

import asyncio
from typing import Any, Dict, Optional, Tuple

from .cache_manager import CacheManager
from .scenario_cache import ScenarioCache
from .scenario_executor import ScenarioExecutor
from .scenario_finder import ScenarioFinder
from .scenario_loader import ScenarioLoader
from .step_executor import StepExecutor
from .transition_handler import TransitionHandler


class ScenarioEngine:
    """
    Движок обработки событий по сценариям
    Оркестратор - координирует все компоненты:
    - ScenarioCache - кэширование сценариев
    - ScenarioLoader - загрузка сценариев из YAML
    - ScenarioFinder - поиск сценариев по событиям
    - ScenarioExecutor - выполнение сценариев
    """
    
    def __init__(self, logger, api_bus, scenarios_path: str, step_timeout: float = 0, scenario_timeout: float = 0):
        self.logger = logger
        self.api_bus = api_bus
        
        # Инициализация компонентов
        self.cache = ScenarioCache(self.logger)
        self.loader = ScenarioLoader(self.logger, self.api_bus, scenarios_path)
        self.finder = ScenarioFinder(self.logger, self.api_bus)
        
        # Создание компонентов выполнения
        cache_manager = CacheManager(self.logger, self.api_bus)
        step_executor = StepExecutor(self.logger, self.api_bus, step_timeout=step_timeout)
        transition_handler = TransitionHandler(self.logger)
        
        self.executor = ScenarioExecutor(
            self.logger,
            step_executor,
            transition_handler,
            cache_manager,
            scenario_timeout=scenario_timeout
        )
    
    async def process_event(self, event: Dict[str, Any]) -> bool:
        """Обработка события по сценариям"""
        try:
            # Загрузка сценариев если ещё не загружены
            if not self.cache.has_cache():
                cache_data = await self.loader.load_scenarios()
                self.cache.set_cache(cache_data)
            
            # Получение метаданных сценария для изолированной обработки событий
            scenario_metadata = self.cache.get_scenario_metadata()
            if not scenario_metadata:
                self.logger.warning("Не удалось получить метаданные сценариев")
                return False
            
            # Поиск подходящих сценариев (использование метаданных)
            scenario_ids = await self.finder.find_scenarios_by_event(event, scenario_metadata)
            
            if scenario_ids:
                # Запуск всех сценариев параллельно, независимо друг от друга
                async def run_one(scenario_id: int):
                    result, _ = await self.executor.execute_scenario(
                        scenario_id=scenario_id,
                        event=event,
                        scenario_metadata=scenario_metadata,
                        execute_scenario_by_name_func=self._execute_scenario_by_name_wrapper
                    )
                    if result == 'error':
                        name = (scenario_metadata.get('scenario_index') or {}).get(scenario_id, {}).get('data', {}).get('name', scenario_id)
                        self.logger.warning(f"Ошибка выполнения сценария '%s' (id=%s)", name, scenario_id)
                    return result

                await asyncio.gather(*(run_one(sid) for sid in scenario_ids))

            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки события: {e}")
            return False
    
    async def _execute_scenario_by_name_wrapper(self, scenario_name: str, data: Dict[str, Any], scenario_metadata: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Обёртка для выполнения сценария по имени. Используется для передачи в ScenarioExecutor для переходов jump_to_scenario"""
        return await self.executor.execute_scenario_by_name(
            scenario_name=scenario_name,
            data=data,
            scenario_metadata=scenario_metadata,
            execute_scenario_func=self._execute_scenario_wrapper
        )
    
    async def _execute_scenario_wrapper(self, scenario_id: int, event: Dict[str, Any], scenario_metadata: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Обёртка для выполнения сценария по ID. Используется для передачи в ScenarioExecutor"""
        return await self.executor.execute_scenario(
            scenario_id=scenario_id,
            event=event,
            scenario_metadata=scenario_metadata,
            execute_scenario_by_name_func=self._execute_scenario_by_name_wrapper
        )
    
    async def execute_scenario_by_name(self, scenario_name: str, data: Dict[str, Any], scenario_metadata: Dict[str, Any] = None) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Поиск и выполнение сценария по имени. Публичный метод для внешнего использования"""
        if scenario_metadata is None:
            # Если метаданные не предоставлены, получить их
            scenario_metadata = self.cache.get_scenario_metadata()
            if not scenario_metadata:
                self.logger.warning("Не удалось получить метаданные сценариев")
                return ('error', None)
        
        return await self.executor.execute_scenario_by_name(
            scenario_name=scenario_name,
            data=data,
            scenario_metadata=scenario_metadata,
            execute_scenario_func=self._execute_scenario_wrapper
        )
    
    async def reload_scenarios(self) -> bool:
        """Перезагрузка кэша сценариев"""
        try:
            # Очистка кэша
            self.cache.clear_cache()
            
            # Перезагрузка
            cache_data = await self.loader.load_scenarios()
            self.cache.set_cache(cache_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка перезагрузки сценариев: {e}")
            return False
    
    def get_scheduled_scenarios(self) -> list:
        """Получение списка scheduled-сценариев"""
        return self.cache.get_scheduled_scenarios()
