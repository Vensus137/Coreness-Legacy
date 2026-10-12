"""
Плагин обработки плейсхолдеров: полная реализация.
Интеграция с API Bus (async); в payload: data/text, values, опционально max_depth.
"""

import re
from typing import Any, Dict, List

from .modules.object_utils import deep_merge
from .modules.payload_validator import PayloadValidator
from .modules.placeholder_replacer import PlaceholderReplacer
from .modules.type_utils import determine_result_type
from .modules.modifiers_arithmetic import ArithmeticModifiers
from .modules.modifiers_array import ArrayModifiers
from .modules.modifiers_async import AsyncModifiers
from .modules.modifiers_basic import BasicModifiers
from .modules.modifiers_conditional import ConditionalModifiers
from .modules.modifiers_datetime import DatetimeModifiers
from .modules.modifiers_formatting import FormattingModifiers


class PlaceholderProcessor:
    """Обработчик плейсхолдеров: модификаторы, вложенные пути, литералы, expand. Действия API Bus — async."""

    def __init__(self, config: dict, context):
        self.config = config
        self.api_bus = context.api_bus
        self.logger = context.logger
        settings = config.get("settings") or {}
        self.max_nesting_depth = settings.get("max_nesting_depth", 10)
        self.substitution_result_max_depth = settings.get("substitution_result_max_depth", 1)

        self.placeholder_pattern = re.compile(r"\{((?:[^{}]|\{[^{}]*\})+)\}")
        
        # Инициализация компонентов
        self.replacer = PlaceholderReplacer(self.logger, self.max_nesting_depth)
        self._init_modifiers()
        
        self.logger.info("PlaceholderProcessor инициализирован")

    async def process_text_placeholders(self, payload: dict) -> dict:
        """Обработка плейсхолдеров в строке. Payload: text, values, опционально max_depth."""
        try:
            text, values, max_depth = PayloadValidator.validate_text_payload(payload, self.max_nesting_depth)
            result_text = self._process_text_placeholders_internal(text, values, max_depth)
            return {"result": "success", "response_data": {"text": result_text}}
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Ошибка валидации в process_text_placeholders: {e}")
            return {"result": "error", "error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        except Exception as e:
            self.logger.error(f"Ошибка в process_text_placeholders: {e}", exc_info=True)
            return {"result": "error", "error": {"code": "INTERNAL_ERROR", "message": str(e)}}

    async def process_placeholders(self, payload: dict) -> dict:
        """Обработка плейсхолдеров в dict/list/str. Payload: data, values, опционально max_depth."""
        try:
            data, values, max_depth = PayloadValidator.validate_data_payload(payload, self.max_nesting_depth)
            result_data = self._process_placeholders_internal(data, values, max_depth)
            return {"result": "success", "response_data": {"data": result_data}}
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Ошибка валидации в process_placeholders: {e}")
            return {"result": "error", "error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        except Exception as e:
            self.logger.error(f"Ошибка в process_placeholders: {e}", exc_info=True)
            return {"result": "error", "error": {"code": "INTERNAL_ERROR", "message": str(e)}}

    async def process_placeholders_full(self, payload: dict) -> dict:
        """Обработка плейсхолдеров с возвратом полного объекта. Payload: data, values, опционально max_depth."""
        try:
            data, values, max_depth = PayloadValidator.validate_data_payload(payload, self.max_nesting_depth)
            result_data = self._process_placeholders_full_internal(data, values, max_depth)
            return {"result": "success", "response_data": {"data": result_data}}
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Ошибка валидации в process_placeholders_full: {e}")
            return {"result": "error", "error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        except Exception as e:
            self.logger.error(f"Ошибка в process_placeholders_full: {e}", exc_info=True)
            return {"result": "error", "error": {"code": "INTERNAL_ERROR", "message": str(e)}}

    def _process_text_placeholders_internal(self, text: str, values_dict: Dict, max_depth: int) -> str:
        self.replacer.max_nesting_depth = max_depth
        if not self.replacer._has_placeholders_fast(text):
            return text
        result = self.replacer.process_string(text, values_dict, 0)
        return str(result) if result is not None else text

    def _process_placeholders_internal(self, data_with_placeholders: Dict, values_dict: Dict, max_depth: int) -> Dict:
        self.max_nesting_depth = max_depth
        try:
            return self._process_object_optimized(
                data_with_placeholders, values_dict, self.substitution_result_max_depth
            )
        except Exception as e:
            self.logger.error(f"Ошибка обработки плейсхолдеров: {e}")
            return data_with_placeholders

    def _process_placeholders_full_internal(self, data_with_placeholders: Dict, values_dict: Dict, max_depth: int) -> Dict:
        self.max_nesting_depth = max_depth
        try:
            processed_data = self._process_object_optimized(
                data_with_placeholders, values_dict, self.substitution_result_max_depth
            )
            return deep_merge(data_with_placeholders, processed_data)
        except Exception as e:
            self.logger.error(f"Ошибка обработки плейсхолдеров (режим full): {e}")
            return data_with_placeholders

    def _init_modifiers(self):
        basic = BasicModifiers(self.logger)
        arithmetic = ArithmeticModifiers(self.logger)
        formatting = FormattingModifiers(self.logger)
        conditional = ConditionalModifiers(self.logger)
        datetime_mods = DatetimeModifiers(self.logger)
        array_mods = ArrayModifiers(self.logger)
        async_mods = AsyncModifiers(self.logger)

        modifiers = {
            "fallback": self._modifier_fallback,
            "/": arithmetic.modifier_divide,
            "+": arithmetic.modifier_add,
            "-": arithmetic.modifier_subtract,
            "*": arithmetic.modifier_multiply,
            "%": arithmetic.modifier_modulo,
            "upper": basic.modifier_upper,
            "lower": basic.modifier_lower,
            "title": basic.modifier_title,
            "capitalize": basic.modifier_capitalize,
            "truncate": basic.modifier_truncate,
            "length": basic.modifier_length,
            "case": basic.modifier_case,
            "regex": basic.modifier_regex,
            "code": basic.modifier_code,
            "format": formatting.modifier_format,
            "tags": formatting.modifier_tags,
            "list": formatting.modifier_list,
            "comma": formatting.modifier_comma,
            "equals": conditional.modifier_equals,
            "in_list": conditional.modifier_in_list,
            "true": conditional.modifier_true,
            "value": conditional.modifier_value,
            "exists": conditional.modifier_exists,
            "is_null": conditional.modifier_is_null,
            "shift": datetime_mods.modifier_shift,
            "seconds": datetime_mods.modifier_seconds,
            "to_date": datetime_mods.modifier_to_date,
            "to_hour": datetime_mods.modifier_to_hour,
            "to_minute": datetime_mods.modifier_to_minute,
            "to_second": datetime_mods.modifier_to_second,
            "to_week": datetime_mods.modifier_to_week,
            "to_month": datetime_mods.modifier_to_month,
            "to_year": datetime_mods.modifier_to_year,
            "expand": array_mods.modifier_expand,
            "keys": array_mods.modifier_keys,
            "not_ready": async_mods.modifier_not_ready,
            "ready": async_mods.modifier_ready,
        }
        
        # Передача модификаторов в replacer
        self.replacer.set_modifiers(modifiers)


    def _process_object_optimized(self, obj: Any, values_dict: Dict, result_recurse_remaining: int = 0):
        if isinstance(obj, dict):
            return self._process_dict_optimized(obj, values_dict, result_recurse_remaining)
        elif isinstance(obj, list):
            return self._process_list_optimized(obj, values_dict, result_recurse_remaining)
        elif isinstance(obj, str):
            return self.replacer.process_string(obj, values_dict, 0)
        return {}

    def _process_dict_optimized(self, obj: Dict, values_dict: Dict, result_recurse_remaining: int = 0) -> Dict:
        result = {}
        for key, value in obj.items():
            if isinstance(value, str):
                if not self.replacer._has_placeholders_fast(value):
                    continue
                processed_value = self.replacer.process_string(value, values_dict, 0)
                if processed_value != value or type(processed_value) is not type(value):
                    if result_recurse_remaining > 0 and isinstance(processed_value, dict):
                        inner = self._process_dict_optimized(processed_value, values_dict, result_recurse_remaining - 1)
                        result[key] = {**processed_value, **inner}
                    elif result_recurse_remaining > 0 and isinstance(processed_value, list):
                        result[key] = self._process_list_optimized(processed_value, values_dict, result_recurse_remaining - 1)
                    else:
                        result[key] = processed_value
            elif isinstance(value, dict):
                processed_dict = self._process_dict_optimized(value, values_dict, result_recurse_remaining)
                result[key] = {**value, **processed_dict}
            elif isinstance(value, list):
                processed_list = self._process_list_optimized(value, values_dict, result_recurse_remaining)
                if processed_list is not value:
                    result[key] = processed_list
            else:
                result[key] = value
        return result

    def _process_list_optimized(self, obj: List, values_dict: Dict, result_recurse_remaining: int = 0) -> List:
        result = []
        has_changes = False
        for item in obj:
            if isinstance(item, str):
                if not self.replacer._has_placeholders_fast(item):
                    result.append(item)
                    continue
                has_expand_modifier = "|expand" in item or item.endswith("|expand}")
                processed_item = self.replacer.process_string(item, values_dict, 0)
                if processed_item != item or type(processed_item) is not type(item):
                    has_changes = True
                    if result_recurse_remaining > 0 and isinstance(processed_item, list):
                        result.extend(self._process_list_optimized(processed_item, values_dict, result_recurse_remaining - 1))
                    elif result_recurse_remaining > 0 and isinstance(processed_item, dict):
                        inner = self._process_dict_optimized(processed_item, values_dict, result_recurse_remaining - 1)
                        result.append({**processed_item, **inner})
                    elif has_expand_modifier and isinstance(processed_item, list):
                        if processed_item and all(isinstance(subitem, list) for subitem in processed_item):
                            result.extend(processed_item)
                        else:
                            result.append(processed_item)
                    elif isinstance(processed_item, list) and self.replacer._is_entire_placeholder(item):
                        result.extend(processed_item)
                    else:
                        result.append(processed_item)
                else:
                    result.append(item)
            elif isinstance(item, dict):
                processed_dict = self._process_dict_optimized(item, values_dict, result_recurse_remaining)
                merged_dict = {**item, **processed_dict}
                if merged_dict != item:
                    has_changes = True
                result.append(merged_dict)
            elif isinstance(item, list):
                processed_list = self._process_list_optimized(item, values_dict, result_recurse_remaining)
                if processed_list is not item:
                    has_changes = True
                    result.append(processed_list)
                else:
                    result.append(item)
        return result if has_changes else obj


    def _modifier_fallback(self, value: Any, param: str) -> Any:
        if value is not None and value != "":
            return value
        if param is None:
            return None
        return determine_result_type(param.strip())
