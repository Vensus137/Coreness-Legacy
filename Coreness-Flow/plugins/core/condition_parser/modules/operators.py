"""Функции операторов для компиляции условий."""

import re
from typing import Any, Optional


def regex_match(field_value: Any, pattern: str) -> bool:
    """Проверка совпадения значения с регулярным выражением."""
    if field_value is None:
        return False
    try:
        return bool(re.search(pattern, str(field_value)))
    except Exception:
        return False


def is_null(value: Any) -> bool:
    """Проверка на null (None, пустая строка или строка \"null\")."""
    return value is None or value == '' or (isinstance(value, str) and value.lower() == 'null')


def not_is_null(value: Any) -> bool:
    """Проверка на не-null (инверсия is_null)."""
    return not is_null(value)


def safe_eq(left: Any, right: Any) -> bool:
    """Безопасное сравнение с автоматическим приведением типов."""
    if left is None or right is None:
        return left is right
    
    # Пробуем привести строки к числам для сравнения
    if isinstance(left, str) and isinstance(right, (int, float)):
        try:
            if '.' in left:
                left = float(left)
            else:
                left = int(left)
        except (ValueError, TypeError):
            pass
    
    if isinstance(right, str) and isinstance(left, (int, float)):
        try:
            if '.' in right:
                right = float(right)
            else:
                right = int(right)
        except (ValueError, TypeError):
            pass
    
    return left == right


def safe_ne(left: Any, right: Any) -> bool:
    """Безопасное неравенство."""
    return not safe_eq(left, right)


def safe_gt(left: Any, right: Any) -> bool:
    """Безопасное сравнение >."""
    if left is None or right is None:
        return False
    
    left = _try_convert_to_number(left)
    right = _try_convert_to_number(right)
    
    if left is None or right is None:
        return False
    
    return left > right


def safe_lt(left: Any, right: Any) -> bool:
    """Безопасное сравнение <."""
    if left is None or right is None:
        return False
    
    left = _try_convert_to_number(left)
    right = _try_convert_to_number(right)
    
    if left is None or right is None:
        return False
    
    return left < right


def safe_gte(left: Any, right: Any) -> bool:
    """Безопасное сравнение >=."""
    if left is None or right is None:
        return False
    
    left = _try_convert_to_number(left)
    right = _try_convert_to_number(right)
    
    if left is None or right is None:
        return False
    
    return left >= right


def safe_lte(left: Any, right: Any) -> bool:
    """Безопасное сравнение <=."""
    if left is None or right is None:
        return False
    
    left = _try_convert_to_number(left)
    right = _try_convert_to_number(right)
    
    if left is None or right is None:
        return False
    
    return left <= right


def _try_convert_to_number(value: Any) -> Optional[float]:
    """Пытается привести значение к числу."""
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            pass
    
    return None


def get_operator_functions() -> dict:
    """Возвращает словарь функций операторов для компиляции."""
    return {
        'regex': regex_match,
        'is_null': is_null,
        'not_is_null': not_is_null,
        'safe_eq': safe_eq,
        'safe_ne': safe_ne,
        'safe_gt': safe_gt,
        'safe_lt': safe_lt,
        'safe_gte': safe_gte,
        'safe_lte': safe_lte,
    }
