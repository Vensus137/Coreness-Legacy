"""Проверка условий на соответствие данным."""

from typing import Dict, Union


class ConditionChecker:
    """Проверка условий на соответствие данным."""
    
    def __init__(self, logger):
        self.logger = logger
    
    def check_match(self, condition: Union[str, dict], data: dict, parse_func) -> bool:
        """Проверка совпадения; может бросать исключения."""
        if isinstance(condition, str):
            parsed_condition = parse_func(condition)
            return self._check_parsed_condition(parsed_condition, data)
        elif isinstance(condition, dict):
            return self._check_parsed_condition(condition, data)
        else:
            raise TypeError(f"Неподдерживаемый тип условия: {type(condition).__name__}")
    
    def _check_parsed_condition(self, parsed_condition: dict, data: dict) -> bool:
        """Проверка распарсенного условия по данным."""
        compiled_function = parsed_condition.get('compiled_function')
        if compiled_function:
            try:
                return compiled_function(data)
            except Exception as e:
                self.logger.error(f"Ошибка выполнения условия: {e}")
                return False
        
        return True
