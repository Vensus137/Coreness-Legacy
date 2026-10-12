"""
Универсальный парсер условий для сценариев.
Async-обёртка для интеграции с API Bus.
"""

from typing import Any, Dict, List, Union

from .modules.builder import ConditionBuilder
from .modules.checker import ConditionChecker
from .modules.compiler import ConditionCompiler
from .modules.extractor import ConditionExtractor
from .modules.tokenizer import ConditionTokenizer
from .modules.tree import TreeManager


class ConditionParser:
    """Универсальный парсер выражений условий с интеграцией в API Bus."""

    def __init__(self, config: dict, context):
        self.config = config
        self.api_bus = context.api_bus
        self.logger = context.logger

        # Инициализация компонентов
        self.tokenizer = ConditionTokenizer()
        self.compiler = ConditionCompiler(self.logger, self.tokenizer)
        self.extractor = ConditionExtractor()
        self.checker = ConditionChecker(self.logger)
        self.builder = ConditionBuilder()
        self.tree_manager = TreeManager(self.logger)
        
        # Действия регистрируются по config (register_plugin)
        self.logger.info("ConditionParser инициализирован")
    
    # === API Bus Actions ===
    
    async def parse_condition(self, payload: dict) -> dict:
        try:
            condition = payload.get("condition")
            if not condition:
                raise ValueError("Поле 'condition' отсутствует или пусто")
            
            if not isinstance(condition, str):
                raise TypeError(f"'condition' должен быть строкой, получен {type(condition).__name__}")
            
            parsed = self._parse_condition_internal(condition)
            
            return {
                "result": "success",
                "response_data": parsed
            }
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Ошибка валидации в parse_condition: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e)
                }
            }
        except Exception as e:
            self.logger.error(f"Ошибка в parse_condition: {e}", exc_info=True)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def check_match(self, payload: dict) -> dict:
        try:
            condition = payload.get("condition")
            data = payload.get("data")
            if condition is None:
                raise ValueError("Поле 'condition' отсутствует")
            
            if data is None:
                raise ValueError("Поле 'data' отсутствует")
            
            if not isinstance(data, dict):
                raise TypeError(f"'data' должен быть dict, получен {type(data).__name__}")
            
            matched = self.checker.check_match(condition, data, self._parse_condition_internal)
            
            return {
                "result": "success",
                "response_data": {
                    "matched": matched
                }
            }
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Ошибка валидации в check_match: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e)
                }
            }
        except Exception as e:
            self.logger.error(f"Ошибка в check_match: {e}", exc_info=True)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def build_condition(self, payload: dict) -> dict:
        try:
            configs = payload.get("configs")
            if configs is None:
                raise ValueError("Поле 'configs' отсутствует")
            
            if not isinstance(configs, list):
                raise TypeError(f"'configs' должен быть list, получен {type(configs).__name__}")
            
            condition_string = self.builder.build_condition(configs)
            
            return {
                "result": "success",
                "response_data": {
                    "condition_string": condition_string
                }
            }
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Ошибка валидации в build_condition: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e)
                }
            }
        except Exception as e:
            self.logger.error(f"Ошибка в build_condition: {e}", exc_info=True)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def add_to_tree(self, payload: dict) -> dict:
        try:
            search_tree = payload.get("search_tree")
            parsed_condition = payload.get("parsed_condition")
            item_name = payload.get("item_name")
            item_value = payload.get("item_value")
            if search_tree is None:
                raise ValueError("Поле 'search_tree' отсутствует")
            
            if parsed_condition is None:
                raise ValueError("Поле 'parsed_condition' отсутствует")
            
            if item_name is None:
                raise ValueError("Поле 'item_name' отсутствует")
            
            if item_value is None:
                raise ValueError("Поле 'item_value' отсутствует")
            
            if not isinstance(search_tree, dict):
                raise TypeError(f"'search_tree' должен быть dict, получен {type(search_tree).__name__}")
            
            if not isinstance(parsed_condition, dict):
                raise TypeError(f"'parsed_condition' должен быть dict, получен {type(parsed_condition).__name__}")
            
            if not isinstance(item_name, str):
                raise TypeError(f"'item_name' должен быть str, получен {type(item_name).__name__}")
            
            added = self.tree_manager.add_to_tree(search_tree, parsed_condition, item_name, item_value)
            
            return {
                "result": "success",
                "response_data": {
                    "added": added
                }
            }
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Ошибка валидации в add_to_tree: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e)
                }
            }
        except Exception as e:
            self.logger.error(f"Ошибка в add_to_tree: {e}", exc_info=True)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def search_in_tree(self, payload: dict) -> dict:
        try:
            search_tree = payload.get("search_tree")
            data = payload.get("data")
            if search_tree is None:
                raise ValueError("Поле 'search_tree' отсутствует")
            
            if data is None:
                raise ValueError("Поле 'data' отсутствует")
            
            if not isinstance(search_tree, dict):
                raise TypeError(f"'search_tree' должен быть dict, получен {type(search_tree).__name__}")
            
            if not isinstance(data, dict):
                raise TypeError(f"'data' должен быть dict, получен {type(data).__name__}")
            
            found_values = self.tree_manager.search_in_tree(search_tree, data)
            
            return {
                "result": "success",
                "response_data": {
                    "found_values": found_values
                }
            }
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Ошибка валидации в search_in_tree: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e)
                }
            }
        except Exception as e:
            self.logger.error(f"Ошибка в search_in_tree: {e}", exc_info=True)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    # === Internal Methods ===
    
    def _parse_condition_internal(self, condition_string: str) -> dict:
        """Парсинг строки условия; внутренний метод, может бросать исключения."""
        result = {
            'search_path': {},
            'compiled_function': None,
            'condition_hash': None
        }
        equal_conditions = self.extractor.extract_equal_conditions(condition_string)
        sorted_conditions = dict(sorted(equal_conditions.items()))
        result['search_path'] = sorted_conditions
        
        compiled_func = self.compiler.compile(condition_string)
        if compiled_func is None:
            raise RuntimeError(f"Не удалось скомпилировать условие: {condition_string}")
        result['compiled_function'] = compiled_func
        result['condition_hash'] = hash(condition_string.strip())
        
        return result
