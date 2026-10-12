"""Поиск сценариев по событиям"""

from typing import Any, Dict, List


class ScenarioFinder:
    """
    Поиск сценариев по событиям
    - Поиск подходящих сценариев через search tree
    """
    
    def __init__(self, logger, api_bus):
        self.logger = logger
        self.api_bus = api_bus
    
    async def find_scenarios_by_event(self, event: Dict[str, Any], scenario_metadata: Dict[str, Any]) -> List[int]:
        """Поиск подходящих сценариев по событию через search tree"""
        try:
            # Использование метаданных сценария для изолированной обработки
            search_tree = scenario_metadata['search_tree']
            
            # Проверка что search tree не пустое
            if not search_tree:
                return []
            
            # Поиск scenario_id в search tree через condition_parser
            result = await self.api_bus.call('search_in_tree', {
                'search_tree': search_tree,
                'data': event
            })
            
            if result.get('result') != 'success':
                self.logger.warning(f"Ошибка поиска в search tree: {result.get('error')}")
                return []
            
            response_data = result.get('response_data', {})
            scenario_ids = response_data.get('found_values', [])
            
            if not scenario_ids:
                return []
            
            # Фильтрация только существующих сценариев
            scenario_index = scenario_metadata['scenario_index']
            existing_scenarios = []
            for scenario_id in scenario_ids:
                if scenario_id in scenario_index:
                    existing_scenarios.append(scenario_id)
                else:
                    self.logger.warning(f"Найден scenario_id {scenario_id} в search tree, но отсутствует в индексе")
            return existing_scenarios
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска сценариев по событию: {e}")
            return []
