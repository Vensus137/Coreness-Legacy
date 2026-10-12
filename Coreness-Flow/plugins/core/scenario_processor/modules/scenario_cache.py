"""Кэш сценариев в памяти"""

from typing import Any, Dict, Optional


class ScenarioCache:
    """
    Кэш сценариев в памяти
    - Хранение сценариев в памяти
    - Получение метаданных сценариев для изолированной обработки событий
    - Перезагрузка кэша
    """
    
    def __init__(self, logger):
        self.logger = logger
        self._cache: Optional[Dict[str, Any]] = None
    
    def get_scenario_metadata(self) -> Optional[Dict[str, Any]]:
        """Получение метаданных сценариев для изолированной обработки событий"""
        try:
            if self._cache is None:
                return None
            
            # Использование ссылок на все структуры (не копируем)
            # Безопасно, т.к. все структуры только читаются во время выполнения сценария
            # Изменения происходят только при reload, который удаляет старый кэш
            metadata = {
                'search_tree': self._cache['search_tree'],  # Ссылка
                'scenario_index': self._cache['scenario_index'],  # Ссылка
                'scenario_name_index': self._cache['scenario_name_index']  # Ссылка
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Ошибка получения метаданных сценариев: {e}")
            return None
    
    def get_cache(self) -> Optional[Dict[str, Any]]:
        """Получение кэша"""
        return self._cache
    
    def set_cache(self, cache: Dict[str, Any]) -> None:
        """Установка кэша"""
        self._cache = cache
    
    def has_cache(self) -> bool:
        """Проверка наличия кэша"""
        return self._cache is not None
    
    def clear_cache(self) -> None:
        """Очистка кэша"""
        self._cache = None
    
    def get_scheduled_scenarios(self) -> list:
        """Получение списка scheduled-сценариев"""
        if self._cache is None:
            return []
        
        scheduled = []
        scenario_index = self._cache.get('scenario_index', {})
        
        for scenario_id, scenario_data in scenario_index.items():
            raw_data = scenario_data.get('data', {}).get('raw_data', {})
            schedule = raw_data.get('schedule')
            
            if schedule:
                scheduled.append({
                    'id': scenario_id,
                    'scenario_name': scenario_data.get('data', {}).get('name'),
                    'schedule': schedule
                })
        
        return scheduled
