"""Токенизатор условий с поддержкой маркера $name для полей."""

import re
from typing import List, Optional

from .tokens import Token, TokenType


class ConditionTokenizer:
    """Токенизатор условий с поддержкой маркера $name."""
    
    def __init__(self):
        # Паттерны по типам токенов (порядок важен)
        patterns = [
            # Булевы и None — до полей
            (r'\bTrue\b', TokenType.BOOLEAN),
            (r'\bFalse\b', TokenType.BOOLEAN),
            (r'\btrue\b', TokenType.BOOLEAN),
            (r'\bfalse\b', TokenType.BOOLEAN),
            (r'\bNone\b', TokenType.NONE),
            
            # Поля с маркером $name — до строк
            (r'[\$][\w\.]+(?:\[[^\]]+\])+(?:\.[\w]+)*', TokenType.FIELD),  # с массивами
            (r'[\$][\w\.]+(?:\.[\w]+)*', TokenType.FIELD),  # без массивов
            
            # Строки в кавычках
            (r'"[^"]*"', TokenType.STRING),
            (r"'[^']*'", TokenType.STRING),
            
            # Строки с несколькими точками (даты, IP, версии) — до паттерна чисел
            (r'\d+\.\d+\.\d+[.\d\s:]*', TokenType.STRING),
            
            # Строки: цифры + буквы/дефисы/двоеточия (до паттерна чисел)
            (r'\d+[a-zA-Z\-:][a-zA-Z0-9_\-:.]*', TokenType.STRING),
            
            # Числа (в т.ч. отрицательные и с плавающей точкой)
            (r'-?\d+\.\d+', TokenType.NUMBER),
            (r'-?\d+', TokenType.NUMBER),
            
            # Составные операторы с "not" — до простого "not"
            (r'\bnot\s+is_null\b', TokenType.OPERATOR),
            (r'\bnot\s+in\b', TokenType.OPERATOR),
            
            # Логические операторы — до операторов сравнения
            (r'\band\b', TokenType.LOGICAL),
            (r'\bor\b', TokenType.LOGICAL),
            (r'\bnot\b', TokenType.LOGICAL),
            
            # Операторы сравнения и специальные
            (r'>=', TokenType.OPERATOR),
            (r'<=', TokenType.OPERATOR),
            (r'!=', TokenType.OPERATOR),
            (r'==', TokenType.OPERATOR),
            (r'!~', TokenType.OPERATOR),
            (r'~', TokenType.OPERATOR),
            (r'>', TokenType.OPERATOR),
            (r'<', TokenType.OPERATOR),
            
            # Специальные операторы (после ~ и !~)
            (r'\bregex\b', TokenType.OPERATOR),
            (r'\bis_null\b', TokenType.OPERATOR),
            (r'\bin\b', TokenType.OPERATOR),
            
            # Универсальный паттерн строк (идентификаторы, UUID и т.д.) — после всех остальных
            (r'\b[a-zA-Z0-9_][a-zA-Z0-9_\-:.]*\b', TokenType.STRING),
            
            (r'\(', TokenType.BRACKET),
            (r'\)', TokenType.BRACKET),
            (r'\[', TokenType.BRACKET),
            (r'\]', TokenType.BRACKET),
            (r',', TokenType.COMMA),
        ]
        
        # Компиляция паттернов
        self._compiled_patterns = [
            (re.compile(pattern), token_type)
            for pattern, token_type in patterns
        ]
    
    def tokenize(self, expression: str) -> List[Token]:
        """Токенизирует выражение условия."""
        tokens = []
        position = 0
        expression = expression.strip()
        
        while position < len(expression):
            if expression[position].isspace():
                position += 1
                continue
            
            matched = False
            for pattern, token_type in self._compiled_patterns:
                match = pattern.match(expression, position)
                if match:
                    value = match.group(0)
                    end_pos = match.end()
                    
                    # Для строк с несколькими точками ограничиваем длину до следующего оператора/пробела
                    if token_type == TokenType.STRING and value.count('.') >= 2:
                        actual_end = end_pos
                        while actual_end < len(expression) and expression[actual_end].isspace():
                            actual_end += 1
                        
                        while actual_end < len(expression):
                            char = expression[actual_end]
                            if char in ['=', '!', '>', '<', '~', '&', '|', '(', ')', '[', ']', ',']:
                                break
                            if char.isspace():
                                break
                            if char.isdigit() or char in ['.', ':']:
                                actual_end += 1
                            else:
                                break
                        
                        value = expression[position:actual_end].rstrip()
                        end_pos = position + len(value)
                    
                    tokens.append(Token(token_type, value, position))
                    position = end_pos
                    matched = True
                    break
            
            if not matched:
                next_pos = position + 1
                found_next = False
                for pattern, _ in self._compiled_patterns:
                    match = pattern.match(expression, next_pos)
                    if match:
                        unknown_value = expression[position:next_pos]
                        tokens.append(Token(TokenType.UNKNOWN, unknown_value, position))
                        position = next_pos
                        found_next = True
                        break
                
                if not found_next:
                    unknown_value = expression[position:]
                    tokens.append(Token(TokenType.UNKNOWN, unknown_value, position))
                    break
        
        return tokens
    
    def get_field_name(self, token: Token) -> Optional[str]:
        """Извлекает имя поля из токена (убирает маркер $)."""
        if token.type == TokenType.FIELD:
            return token.value[1:]
        return None
