"""Логика замены плейсхолдеров в строках."""

import re
from datetime import datetime
from typing import Any, Callable, Dict

# Встроенный ключ: текущее время как Unix timestamp (секунды с эпохи UTC), удобен для сортировки и JSON
BUILTIN_NOW_KEY = "now"

from .path_parser import extract_literal_or_get_value, get_nested_value
from .type_utils import determine_result_type


class PlaceholderReplacer:
    """Обработчик замен плейсхолдеров в строках с поддержкой модификаторов."""

    def __init__(self, logger, max_nesting_depth: int):
        self.logger = logger
        self.max_nesting_depth = max_nesting_depth

        self.placeholder_pattern = re.compile(r"\{((?:[^{}]|\{[^{}]*\})+)\}")
        self.modifiers: Dict[str, Callable] = {}

    def set_modifiers(self, modifiers: Dict[str, Callable]):
        """Установка словаря модификаторов."""
        self.modifiers = modifiers

    def process_placeholder_chain(self, placeholder: str, values_dict: Dict, depth: int = 0):
        """Обработка цепочки модификаторов для плейсхолдера."""
        if depth >= self.max_nesting_depth:
            self.logger.warning(f"Достигнута максимальная глубина рекурсии ({self.max_nesting_depth}) для плейсхолдера: {placeholder}")
            return f"{{{placeholder}}}"
        
        # Обработка вложенных плейсхолдеров
        if self._has_placeholders_fast(placeholder):
            try:
                def _inner_repl(m):
                    inner_content = m.group(1).strip()
                    return str(self.process_placeholder_chain(inner_content, values_dict, depth + 1))
                placeholder = self.placeholder_pattern.sub(_inner_repl, placeholder)
            except Exception as e:
                self.logger.warning(f"Ошибка обработки вложенных плейсхолдеров: {e}")
        
        # Разделение на поле и модификаторы
        parts = placeholder.split("|")
        field_name = parts[0].strip()
        value = extract_literal_or_get_value(field_name, values_dict, get_nested_value)
        # Встроенный плейсхолдер: текущее время как Unix timestamp (секунды с эпохи UTC)
        if value is None and field_name == BUILTIN_NOW_KEY:
            value = int(datetime.now().timestamp())
        # Для арифметических модификаторов: если путь не найден, поле может быть числом (результат вложенного плейсхолдера)
        if value is None and len(parts) > 1:
            first_mod = parts[1].strip()
            if first_mod and first_mod[0] in ["/", "+", "-", "*", "%"]:
                numeric = self._try_parse_numeric_field(field_name)
                if numeric is not None:
                    value = numeric
        
        # Рекурсивная обработка строковых значений с плейсхолдерами
        if isinstance(value, str) and self._has_placeholders_fast(value):
            value = self.process_string(value, values_dict, depth + 1)
        
        # Применение модификаторов
        for modifier in parts[1:]:
            value = self._apply_modifier(value, modifier.strip())
        
        if value is not None:
            return determine_result_type(value)
        return f"{{{placeholder}}}"

    def process_string(self, text: str, values_dict: Dict, depth: int = 0):
        """Обработка строки с плейсхолдерами."""
        if not self._has_placeholders_fast(text):
            return text
        
        if self._is_simple_replacement(text):
            return self._simple_replace(text, values_dict, depth)
        return self._complex_replace(text, values_dict, depth)

    def _has_placeholders_fast(self, text: str) -> bool:
        """Быстрая проверка наличия плейсхолдеров."""
        return "{" in text and "}" in text

    def _try_parse_numeric_field(self, field_name: str):
        """Если поле — числовая строка (напр. результат вложенного плейсхолдера), вернуть int/float, иначе None."""
        if not field_name or not isinstance(field_name, str):
            return None
        s = field_name.strip()
        if not s:
            return None
        m = re.match(r"-?\d+(?:\.\d+)?$", s)
        if not m:
            return None
        try:
            return int(s) if "." not in s else float(s)
        except (ValueError, TypeError):
            return None

    def _is_simple_replacement(self, text: str) -> bool:
        """Проверка, является ли замена простой (без модификаторов в плейсхолдерах)."""
        if "|" not in text:
            return True
        matches = self.placeholder_pattern.findall(text)
        for match in matches:
            if "|" in match:
                return False
        return True

    def _simple_replace(self, text: str, values_dict: Dict, depth: int = 0):
        """Простая замена без модификаторов."""
        def replace_simple(match):
            field_name = match.group(1).strip()
            
            # Обработка вложенных плейсхолдеров в имени поля
            if self._has_placeholders_fast(field_name):
                def _inner_repl(m):
                    inner_content = m.group(1).strip()
                    inner_value = self.process_placeholder_chain(inner_content, values_dict, depth + 1)
                    if isinstance(inner_value, str) and inner_value.startswith("{") and inner_value.endswith("}"):
                        return inner_value
                    return str(inner_value)
                field_name = self.placeholder_pattern.sub(_inner_repl, field_name)
            
            value = extract_literal_or_get_value(field_name, values_dict, get_nested_value)
            if value is None and field_name == BUILTIN_NOW_KEY:
                value = int(datetime.now().timestamp())
            return str(determine_result_type(value)) if value is not None else match.group(0)

        if not self.placeholder_pattern.search(text):
            return text
        
        # Если вся строка — один плейсхолдер, возвращаем типизированное значение
        if self._is_entire_placeholder(text):
            field_name = text[1:-1].strip()
            
            if self._has_placeholders_fast(field_name):
                value = self.process_placeholder_chain(field_name, values_dict, depth)
                if value is not None:
                    value_str = str(value)
                    if not (value_str.startswith("{") and value_str.endswith("}") and field_name in value_str):
                        return determine_result_type(value)
                return text
            
            value = extract_literal_or_get_value(field_name, values_dict, get_nested_value)
            if value is None and field_name == BUILTIN_NOW_KEY:
                value = int(datetime.now().timestamp())
            return determine_result_type(value) if value is not None else text
        
        return self.placeholder_pattern.sub(replace_simple, text)

    def _complex_replace(self, text: str, values_dict: Dict, depth: int = 0):
        """Сложная замена с модификаторами."""
        def replace_complex(match):
            placeholder_content = match.group(1).strip()
            result = self.process_placeholder_chain(placeholder_content, values_dict, depth)
            return str(result)

        if self._is_entire_placeholder(text):
            placeholder_content = text[1:-1].strip()
            result = self.process_placeholder_chain(placeholder_content, values_dict, depth)
            if result is not None:
                value_str = str(result)
                if not (value_str.startswith("{") and value_str.endswith("}") and placeholder_content in value_str):
                    return result
            return text
        
        # Итеративная замена до стабилизации
        while True:
            if not self.placeholder_pattern.search(text):
                return text
            new_text = self.placeholder_pattern.sub(replace_complex, text)
            if new_text == text:
                return new_text
            text = new_text

    def _is_entire_placeholder(self, text: str) -> bool:
        """Проверка, является ли вся строка одним плейсхолдером."""
        if not text or text[0] != "{" or text[-1] != "}":
            return False
        
        depth = 0
        for i, ch in enumerate(text):
            if ch == "{":
                depth += 1
                if depth == 1 and i != 0:
                    return False
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    return False
                if depth == 0 and i != len(text) - 1:
                    return False
        return depth == 0

    def _strip_quotes(self, text: str) -> str:
        """Удаление кавычек из параметров модификаторов."""
        if not text:
            return text
        text_stripped = text.strip()
        if len(text_stripped) >= 2:
            first_char = text_stripped[0]
            last_char = text_stripped[-1]
            if (first_char == "'" and last_char == "'") or (first_char == '"' and last_char == '"'):
                return text_stripped[1:-1]
        return text_stripped

    def _apply_modifier(self, value: Any, modifier: str) -> Any:
        """Применение модификатора к значению."""
        # Обработка арифметических операторов
        if modifier and modifier[0] in ["/", "+", "-", "*", "%"]:
            mod_name = modifier[0]
            mod_param = modifier[1:] if len(modifier) > 1 else None
            if mod_param:
                mod_param = self._strip_quotes(mod_param)
        elif ":" in modifier:
            mod_name, mod_param = modifier.split(":", 1)
            if mod_param:
                mod_param = self._strip_quotes(mod_param)
        else:
            mod_name, mod_param = modifier, None
        
        modifier_func = self.modifiers.get(mod_name)
        if modifier_func:
            try:
                return modifier_func(value, mod_param)
            except Exception as e:
                self.logger.warning(f"Ошибка применения модификатора {mod_name}: {e}")
                return value
        return value
