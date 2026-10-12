"""Утилиты для определения типов значений."""
import json
from typing import Any


def determine_result_type(value: Any) -> Any:
    """Универсальное определение типа результата; возвращает значение в наиболее подходящем типе."""
    if value is None:
        return None
    
    # Не строка — возвращаем как есть
    if not isinstance(value, str):
        return value
    
    # Оптимизация: strip() один раз
    value_stripped = value.strip()
    
    # Пустая строка — как есть
    if not value_stripped:
        return value
    
    # Проверка на JSON-массивы и объекты (начинаются с [ или {)
    if value_stripped.startswith('[') and value_stripped.endswith(']'):
        try:
            parsed = json.loads(value_stripped)
            if isinstance(parsed, (list, dict)):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    
    value_lower = value_stripped.lower()
    
    # Булевы значения
    if value_lower == 'true':
        return True
    elif value_lower == 'false':
        return False
    
    # Числа (в т.ч. с форматированием)
    try:
        if '₽' in value or '%' in value:
            return value
        
        # Строка с подчёркиванием не считается числом (идентификаторы)
        if '_' in value:
            return value
        
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        pass
    
    # По умолчанию — строка
    return value
