"""Менеджер кэша данных сценария между шагами"""

from typing import Any, Dict, Optional


class CacheManager:
    """
    Менеджер кэша данных сценария
    - Слияние response_data в _cache
    - Обработка response_key для замены заменяемых полей
    - Глубокое слияние словарей
    """
    
    def __init__(self, logger, api_bus):
        self.logger = logger
        self.api_bus = api_bus
    
    def merge_response_data(self, response_data: Dict[str, Any], data: Dict[str, Any], action_name: str, params: Dict[str, Any]) -> None:
        """Слияние response_data в _cache с учётом namespace и response_key"""
        if not response_data:
            return
        
        # Инициализация _cache если не существует
        if '_cache' not in data:
            data['_cache'] = {}
        
        # Исключение: _async_action должен быть доступен в плоских данных для координации async-действий
        async_action_data = response_data.pop('_async_action', None)
        if async_action_data is not None:
            # Слияние _async_action в data для координации
            if '_async_action' not in data:
                data['_async_action'] = {}
            if isinstance(async_action_data, dict):
                data['_async_action'].update(async_action_data)
        
        # Обработка _response_key для подмены ключа replaceable поля
        response_key = params.get('_response_key')
        if response_key and action_name and response_data:
            try:
                action_config = self.api_bus.get_action_config(action_name)
                if action_config:
                    output_config = action_config.get('output', {})
                    replaceable_field = self._find_replaceable_field(output_config)
                    if replaceable_field and replaceable_field in response_data:
                        value = response_data.pop(replaceable_field)
                        response_data[response_key] = value
                    elif replaceable_field:
                        self.logger.warning(
                            f"[Action-{action_name}] Поле '{replaceable_field}' с replaceable: true в конфиге, но отсутствует в response_data"
                        )
            except Exception as e:
                self.logger.warning(f"[Action-{action_name}] Ошибка обработки _response_key: {e}")
        
        # Сохранение данных в _cache
        if response_data:  # Если данные остались после извлечения _async_action
            namespace = params.get('_namespace')
            if namespace:
                # Вложенное кэширование - в _cache[namespace] (для контроля перезаписи)
                if namespace in data['_cache']:
                    # Слияние с существующими данными в этом ключе
                    data['_cache'][namespace] = self.deep_merge(data['_cache'][namespace], response_data)
                else:
                    # Просто сохранить если ключ не существует
                    data['_cache'][namespace] = response_data
            else:
                # Плоское кэширование по умолчанию - слияние напрямую в _cache
                data['_cache'] = self.deep_merge(data.get('_cache', {}), response_data)
    
    def extract_cache(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Извлечение кэша из данных сценария"""
        return data.get('_cache') if isinstance(data.get('_cache'), dict) else None
    
    def _find_replaceable_field(self, output_config: Dict[str, Any]) -> Optional[str]:
        """Найти поле с флагом replaceable: true в конфиге output действия."""
        try:
            response_data = output_config.get('response_data', {})
            if not isinstance(response_data, dict):
                return None
            properties = response_data.get('properties', {})
            if not isinstance(properties, dict):
                return None
            for field_name, field_config in properties.items():
                if isinstance(field_config, dict) and field_config.get('replaceable', False):
                    return field_name
            return None
        except Exception as e:
            self.logger.warning(f"Ошибка поиска replaceable поля: {e}")
            return None
    
    def deep_merge(self, base_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Глубокое слияние словарей: override_dict переопределяет base_dict"""
        result = base_dict.copy()
        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def deep_merge_into(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Глубокое слияние source в target (изменяет target)."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self.deep_merge_into(target[key], value)
            else:
                target[key] = value
