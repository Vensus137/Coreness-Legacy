"""Утилиты для разбора дат и временных интервалов."""
import re
from datetime import datetime
from typing import Dict, Optional, Tuple


def parse_datetime_value(value) -> Tuple[Optional[datetime], bool]:
    """Приводит произвольный формат даты к datetime."""
    if value is None:
        return None, False
    
    if isinstance(value, datetime):
        has_time = value.hour != 0 or value.minute != 0 or value.second != 0
        return value, has_time
    
    value_str = str(value).strip()
    
    if not value_str:
        return None, False
    
    if value_str.isdigit():
        try:
            return datetime.fromtimestamp(int(value_str)), True
        except (ValueError, OSError):
            pass
    
    if 'T' in value_str:
        try:
            dt = datetime.fromisoformat(value_str.replace('Z', '+00:00'))
            return dt, True
        except (ValueError, AttributeError):
            pass
    
    formats = [
        ('%Y-%m-%d %H:%M:%S', True),
        ('%Y-%m-%d %H:%M', True),
        ('%Y-%m-%d', False),
        ('%d.%m.%Y %H:%M:%S', True),
        ('%d.%m.%Y %H:%M', True),
        ('%d.%m.%Y', False),
        ('%Y-%m-%dT%H:%M:%S', True),
        ('%Y-%m-%dT%H:%M', True),
    ]
    
    for fmt, has_time in formats:
        try:
            dt = datetime.strptime(value_str, fmt)
            return dt, has_time
        except ValueError:
            continue
    
    return None, False


def parse_interval_string(interval: str) -> Dict[str, int]:
    """Разбор интервала в стиле PostgreSQL."""
    pattern = r'(\d+)\s+(year|years|y|month|months|mon|week|weeks|w|day|days|d|hour|hours|h|minute|minutes|min|m|second|seconds|sec|s)\b'
    
    result = {
        'years': 0,
        'months': 0,
        'weeks': 0,
        'days': 0,
        'hours': 0,
        'minutes': 0,
        'seconds': 0
    }
    
    matches = re.findall(pattern, interval, re.IGNORECASE)
    
    if not matches:
        return result
    
    for value, unit in matches:
        value = int(value)
        unit_lower = unit.lower()
        
        if unit_lower in ['year', 'years', 'y']:
            result['years'] += value
        elif unit_lower in ['month', 'months', 'mon']:
            result['months'] += value
        elif unit_lower in ['week', 'weeks', 'w']:
            result['weeks'] += value
        elif unit_lower in ['day', 'days', 'd']:
            result['days'] += value
        elif unit_lower in ['hour', 'hours', 'h']:
            result['hours'] += value
        elif unit_lower in ['minute', 'minutes', 'min', 'm']:
            result['minutes'] += value
        elif unit_lower in ['second', 'seconds', 'sec', 's']:
            result['seconds'] += value
    
    return result
