"""Базовые модификаторы для работы со строками."""
from typing import Any


class BasicModifiers:
    """Class with basic modifiers for working with strings"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_upper(self, value: Any, param: str) -> str:
        """Верхний регистр: {field|upper}"""
        return str(value).upper() if value is not None else ""
    
    def modifier_lower(self, value: Any, param: str) -> str:
        """Нижний регистр: {field|lower}"""
        return str(value).lower() if value is not None else ""
    
    def modifier_title(self, value: Any, param: str) -> str:
        """Регистр по словам: {field|title}"""
        return str(value).title() if value is not None else ""
    
    def modifier_capitalize(self, value: Any, param: str) -> str:
        """Первая буква заглавная: {field|capitalize}"""
        return str(value).capitalize() if value is not None else ""
    
    def modifier_truncate(self, value: Any, param: str) -> str:
        """Обрезка текста: {field|truncate:length}"""
        if not value or not param:
            return str(value) if value is not None else ""
        try:
            length = int(param)
            text = str(value)
            if len(text) <= length:
                return text
            return text[:length-3] + "..."
        except (ValueError, TypeError):
            return str(value)
    
    def modifier_length(self, value: Any, param: str) -> int:
        """Длина строки или массива: {field|length}"""
        if value is None:
            return 0
        # Для массивов — количество элементов
        if isinstance(value, list):
            return len(value)
        # Для строк и прочих типов — длина строкового представления
        return len(str(value))
    
    def modifier_case(self, value: Any, param: str) -> str:
        """Смена регистра: {field|case:type}"""
        if not value or not param:
            return str(value) if value is not None else ""
        
        text = str(value)
        if param == 'upper':
            return text.upper()
        elif param == 'lower':
            return text.lower()
        elif param == 'title':
            return text.title()
        elif param == 'capitalize':
            return text.capitalize()
        
        return text
    
    def modifier_regex(self, value: Any, param: str) -> str:
        """Извлечение по регулярному выражению: {field|regex:pattern}"""
        if not value or not param:
            return str(value) if value is not None else ""
        
        try:
            import re

            # Компиляция регулярного выражения
            pattern = re.compile(param)
            
            # Поиск совпадения
            match = pattern.search(str(value))
            
            if match:
                # Первая группа (group 1), если есть, иначе вся строка (group 0)
                if match.groups():
                    return match.group(1)
                else:
                    return match.group(0)
            else:
                # Совпадение не найдено — пустая строка
                return ""
                
        except Exception as e:
            self.logger.warning(f"Ошибка применения модификатора regex с шаблоном '{param}': {e}")
            return str(value)
    
    def modifier_code(self, value: Any, param: str) -> str:
        """
        Оборачивание значения в блок кода: {field|code}. Возвращает значение в <code>...</code>.
        Порядок модификаторов важен:
        - {items|list|code} - first list, then wrap: <code>• a\n• b</code>
        - {items|code|list} - first wrap each element, then list: • <code>a</code>\n• <code>b</code>
        """
        if value is None:
            return '<code></code>'
        if isinstance(value, list):
            # Список — обрабатываем каждый элемент
            return '\n'.join(f'<code>{str(item)}</code>' for item in value)
        return f'<code>{str(value)}</code>'
