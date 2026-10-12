"""Валидация входящих payload для API методов PlaceholderProcessor."""

from typing import Any, Dict, Tuple


class PayloadValidator:
    """Валидатор payload для API методов обработки плейсхолдеров."""

    @staticmethod
    def validate_text_payload(payload: Dict, default_max_depth: int) -> Tuple[str, Dict, int]:
        """
        Валидация payload для process_text_placeholders.
        
        Возвращает: (text, values, max_depth)
        Выбрасывает: ValueError, TypeError при невалидных данных
        """
        text = payload.get("text")
        values = payload.get("values")
        
        if text is None:
            raise ValueError("Поле 'text' отсутствует")
        if values is None:
            raise ValueError("Поле 'values' отсутствует")
        if not isinstance(values, dict):
            raise TypeError(f"'values' должен быть dict, получен {type(values).__name__}")
        
        max_depth = payload.get("max_depth")
        if max_depth is None:
            max_depth = default_max_depth
        
        return str(text), values, max_depth

    @staticmethod
    def validate_data_payload(payload: Dict, default_max_depth: int) -> Tuple[Any, Dict, int]:
        """
        Валидация payload для process_placeholders и process_placeholders_full.
        
        Возвращает: (data, values, max_depth)
        Выбрасывает: ValueError, TypeError при невалидных данных
        """
        data = payload.get("data")
        values = payload.get("values")
        
        if data is None:
            raise ValueError("Поле 'data' отсутствует")
        if values is None:
            raise ValueError("Поле 'values' отсутствует")
        if not isinstance(values, dict):
            raise TypeError(f"'values' должен быть dict, получен {type(values).__name__}")
        
        max_depth = payload.get("max_depth")
        if max_depth is None:
            max_depth = default_max_depth
        
        return data, values, max_depth
