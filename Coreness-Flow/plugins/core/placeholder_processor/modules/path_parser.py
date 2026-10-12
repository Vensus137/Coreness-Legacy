"""Утилиты для разбора путей и извлечения значений."""
from typing import Any, List, Union


def parse_path_with_arrays(path: str) -> List[Union[str, int]]:
    """
    Разбор пути с поддержкой массивов и словарей.
    'attachment[0].file_id' -> ['attachment', 0, 'file_id']
    'predictions[key].field' -> ['predictions', 'key', 'field'] — строковый ключ словаря.
    """
    parts = []
    current = ""
    i = 0
    
    while i < len(path):
        char = path[i]
        
        if char == '.':
            if current:
                parts.append(current)
                current = ""
            i += 1
        elif char == '[':
            if current:
                parts.append(current)
                current = ""
            i += 1
            index_str = ""
            while i < len(path) and path[i] != ']':
                index_str += path[i]
                i += 1
            
            if i >= len(path) or path[i] != ']':
                return []
            
            try:
                parts.append(int(index_str))
            except ValueError:
                parts.append(index_str)
            
            i += 1
        else:
            current += char
            i += 1
    
    if current:
        parts.append(current)
    
    return parts


def get_nested_value(obj: Any, path: str) -> Any:
    """
    Получение значения по пути с поддержкой массивов:
    'field.subfield', 'field[0].subfield', 'field[-1].subfield' и т.д.
    """
    try:
        parts = parse_path_with_arrays(path)
        
        if not parts:
            return None
        
        for part in parts:
            if obj is None:
                return None
                
            if isinstance(part, str):
                if isinstance(obj, dict):
                    found_value = obj.get(part)
                    if found_value is None:
                        if part.isdigit() or (part.startswith('-') and part[1:].isdigit()):
                            try:
                                num_key = int(part)
                                found_value = obj.get(num_key)
                            except ValueError:
                                pass
                        elif '.' in part:
                            try:
                                float_key = float(part)
                                found_value = obj.get(float_key)
                            except ValueError:
                                pass
                    obj = found_value
                    if obj is None:
                        return None
                elif hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return None
            elif isinstance(part, int):
                if isinstance(obj, list):
                    if part < 0:
                        if abs(part) <= len(obj):
                            obj = obj[part]
                        else:
                            return None
                    else:
                        if part < len(obj):
                            obj = obj[part]
                        else:
                            return None
                elif isinstance(obj, dict):
                    obj = obj.get(part)
                    if obj is None:
                        return None
                else:
                    return None
            else:
                return None
        
        return obj
    except Exception:
        return None


def extract_literal_or_get_value(field_name: str, values_dict: dict, get_nested_func) -> Any:
    """
    Извлекает литерал из кавычек или значение из values_dict по пути.
    Поддержка: одинарные/двойные кавычки, экранирование \\' и \\".
    Если field_name в кавычках — возвращает содержимое без кавычек; иначе — значение по пути через get_nested_func.
    """
    field_name = field_name.strip()
    
    if len(field_name) >= 2 and field_name[0] == "'" and field_name[-1] == "'":
        literal_value = field_name[1:-1]
        literal_value = literal_value.replace("\\'", "'")
        return literal_value
    
    if len(field_name) >= 2 and field_name[0] == '"' and field_name[-1] == '"':
        literal_value = field_name[1:-1]
        literal_value = literal_value.replace('\\"', '"')
        return literal_value
    
    return get_nested_func(values_dict, field_name)
