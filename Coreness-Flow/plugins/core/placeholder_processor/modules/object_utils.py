"""Утилиты для работы с объектами (словари, списки)."""
from typing import Dict


def deep_merge(base: Dict, updates: Dict) -> Dict:
    """Рекурсивное слияние двух словарей; поля base дополняются/перезаписываются из updates."""
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result
