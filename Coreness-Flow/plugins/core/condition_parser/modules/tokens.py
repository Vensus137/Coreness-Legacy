"""Типы токенов и классы для токенизации условий."""

from enum import Enum


class TokenType(Enum):
    """Типы токенов."""
    FIELD = "field"           # Поле с маркером: $user_id, $message.text
    STRING = "string"         # Строка: "text", 'text'
    NUMBER = "number"         # Число: 123, 45.67
    BOOLEAN = "boolean"       # Булево: True, False, true, false
    NONE = "none"             # None
    OPERATOR = "operator"     # Оператор: ==, !=, >, <, ~, !~, in, regex, is_null и т.д.
    LOGICAL = "logical"       # Логический оператор: and, or, not
    BRACKET = "bracket"       # Скобки: (, ), [, ]
    COMMA = "comma"           # Запятая
    UNKNOWN = "unknown"       # Неизвестный токен


class Token:
    """Токен с типом и значением."""
    
    def __init__(self, token_type: TokenType, value: str, position: int = 0):
        self.type = token_type
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type.value}, {self.value!r}, pos={self.position})"
    
    def __eq__(self, other):
        if not isinstance(other, Token):
            return False
        return self.type == other.type and self.value == other.value
