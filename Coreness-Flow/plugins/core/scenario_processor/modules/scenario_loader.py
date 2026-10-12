"""Загрузчик сценариев из YAML файлов"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List

import yaml


class ScenarioLoader:
    """
    Загрузчик сценариев из YAML файлов
    - Загрузка сценариев из config/scenarios/
    - Построение структуры для кэширования
    """
    
    def __init__(self, logger, api_bus, scenarios_path: str):
        self.logger = logger
        self.api_bus = api_bus
        self.scenarios_path = Path(scenarios_path)
    
    async def load_scenarios(self) -> Dict[str, Any]:
        """Загрузка всех сценариев из YAML. Возвращает структуру кэша с ключами search_tree, scenario_index, scenario_name_index"""
        try:
            # Инициализация структуры кэша
            cache = {
                'search_tree': {},
                'scenario_index': {},
                'scenario_name_index': {}
            }
            
            # Проверка существования папки
            if not self.scenarios_path.exists():
                self.logger.warning(f"Папка сценариев не найдена: {self.scenarios_path}")
                return cache
            
            # Загрузка всех YAML файлов рекурсивно
            scenario_id = 1  # Генерация ID для сценариев
            
            for yaml_file in self.scenarios_path.rglob("*.yaml"):
                file_scenarios = await self._parse_scenario_file(yaml_file)
                
                for scenario_data in file_scenarios:
                    scenario_name = scenario_data['scenario_name']
                    
                    # Создание записи сценария в индексе
                    cache['scenario_index'][scenario_id] = {
                        'data': {
                            'id': scenario_id,
                            'name': scenario_name,
                            'raw_data': scenario_data
                        },
                        'trigger': (),  # Будет заполнено после загрузки триггеров
                        'step': ()      # Будет заполнено после загрузки шагов
                    }
                    
                    # Добавление в индекс для быстрого поиска по имени
                    cache['scenario_name_index'][scenario_name] = scenario_id
                    
                    # Загрузка триггеров сценария
                    await self._load_scenario_trigger(scenario_id, scenario_data, cache)
                    
                    # Загрузка шагов сценария
                    await self._load_scenario_step(scenario_id, scenario_data, cache)
                    
                    scenario_id += 1
            
            self.logger.info(f"Загружено {scenario_id - 1} сценариев из {self.scenarios_path}")
            return cache
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки сценариев: {e}")
            return {
                'search_tree': {},
                'scenario_index': {},
                'scenario_name_index': {}
            }
    
    async def _parse_scenario_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Парсинг файла сценария"""
        scenarios = []
        
        try:
            loop = asyncio.get_event_loop()
            with open(file_path, 'r', encoding='utf-8') as f:
                content = await loop.run_in_executor(None, f.read)
            
            yaml_content = yaml.safe_load(content) or {}
            
            # Обработка каждого сценария в файле
            for scenario_name, scenario_data in yaml_content.items():
                if isinstance(scenario_data, dict):
                    scenario = {
                        "scenario_name": scenario_name,
                        "description": scenario_data.get("description"),
                        "schedule": scenario_data.get("schedule"),  # Cron выражение для scheduled-сценариев
                        "trigger": scenario_data.get("trigger", []),
                        "step": scenario_data.get("step", [])
                    }
                    scenarios.append(scenario)
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга файла сценария {file_path}: {e}")
        
        return scenarios
    
    async def _load_scenario_trigger(self, scenario_id: int, scenario_data: Dict[str, Any], cache: Dict[str, Any]) -> None:
        """Загрузка триггеров сценария"""
        try:
            trigger = scenario_data.get('trigger', [])
            
            trigger_list = []
            for trigger_idx, trigger_data in enumerate(trigger):
                # Построение условия через condition_parser
                result = await self.api_bus.call('build_condition', {
                    'configs': [trigger_data]
                })
                
                if result.get('result') != 'success':
                    self.logger.error(f"Ошибка построения условия для триггера {trigger_idx} сценария {scenario_id}")
                    continue
                
                response_data = result.get('response_data', {})
                condition_expression = response_data.get('condition_string', '')
                
                # Парсинг условия
                parse_result = await self.api_bus.call('parse_condition', {
                    'condition': condition_expression
                })
                
                if parse_result.get('result') != 'success':
                    self.logger.error(f"Ошибка парсинга условия для триггера {trigger_idx} сценария {scenario_id}")
                    continue
                
                parsed_condition = parse_result.get('response_data', {})
                
                # Добавление триггера в search tree
                if parsed_condition and parsed_condition.get('search_path'):
                    add_result = await self.api_bus.call('add_to_tree', {
                        'search_tree': cache['search_tree'],
                        'parsed_condition': parsed_condition,
                        'item_name': 'scenario_id',
                        'item_value': scenario_id
                    })
                    
                    if add_result.get('result') != 'success':
                        self.logger.warning(f"Не удалось добавить триггер в search tree для сценария {scenario_id}")
                
                # Добавление триггера в список
                trigger_list.append({
                    'trigger_id': trigger_idx,
                    'condition': parsed_condition,
                    'raw_data': trigger_data
                })
            
            # Преобразование списка в tuple (неизменяемый) для безопасного shallow copy
            cache['scenario_index'][scenario_id]['trigger'] = tuple(trigger_list)
                
        except Exception as e:
            self.logger.error(f"Ошибка загрузки триггеров для сценария {scenario_id}: {e}")
    
    async def _load_scenario_step(self, scenario_id: int, scenario_data: Dict[str, Any], cache: Dict[str, Any]) -> None:
        """Загрузка шагов сценария"""
        try:
            step = scenario_data.get('step', [])
            
            step_list = []
            for step_order, step_data in enumerate(step):
                # Взять params как есть (dict)
                params = step_data.get("params", {})
                
                step_list.append({
                    'step_id': step_order,
                    'step_order': step_order,
                    'action_name': step_data.get("action") or step_data.get("action_name"),
                    'params': params,
                    'async': step_data.get("async", False),
                    'action_id': step_data.get("action_id"),
                    'transition': step_data.get("transition", []),
                    'raw_data': step_data
                })
            
            # Преобразование списка в tuple (неизменяемый) для безопасного shallow copy
            cache['scenario_index'][scenario_id]['step'] = tuple(step_list)
                
        except Exception as e:
            self.logger.error(f"Ошибка загрузки шагов для сценария {scenario_id}: {e}")
