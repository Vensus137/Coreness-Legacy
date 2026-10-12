"""Условные модификаторы."""
from typing import Any


class ConditionalModifiers:
    """Класс условных модификаторов."""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_equals(self, value: Any, param: str) -> bool:
        """Проверка равенства: {field|equals:value}"""
        return str(value) == str(param)
    
    def modifier_in_list(self, value: Any, param: str) -> bool:
        """Проверка вхождения в список: {field|in_list:item1,item2}"""
        if not param:
            return False
        items = [item.strip() for item in param.split(',')]
        return str(value) in items
    
    def modifier_true(self, value: Any, param: str) -> bool:
        """Проверка на истинность: {field|true}"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            # Только строки 'true' и 'false' в булевы
            value_lower = value.lower().strip()
            if value_lower == 'true':
                return True
            if value_lower == 'false':
                return False
            # Остальные строки — по непустоте
            return bool(value.strip())
        elif isinstance(value, (int, float)):
            return value != 0
        return bool(value)
    
    def modifier_value(self, value: Any, param: str) -> str:
        """Возвращает значение при истинности: {field|value:result}"""
        # Работает в связке с другими условными модификаторами
        return str(param) if value else ""
    
    def modifier_exists(self, value: Any, param: str) -> bool:
        """Проверка наличия значения: {field|exists}. Истина, если не None и не пустая строка."""
        return value is not None and value != ''
    
    def modifier_is_null(self, value: Any, param: str) -> bool:
        """Проверка на null: {field|is_null}. Истина, если None, пустая строка или строка \"null\"."""
        return value is None or value == '' or (isinstance(value, str) and value.lower() == 'null')
