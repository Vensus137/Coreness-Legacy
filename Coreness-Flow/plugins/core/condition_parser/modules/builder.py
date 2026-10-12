"""Построение строки условия из конфигураций."""

from typing import Any, Dict, List


class ConditionBuilder:
    """Построение строки условия из массива структур."""
    
    def build_condition(self, configs: List[Dict[str, Any]]) -> str:
        """Сборка строки условия из массива структур."""
        all_conditions = []
        for config in configs:
            config_conditions = []
            for field, value in config.items():
                if field == 'condition':
                    continue
                if isinstance(value, str):
                    escaped_value = f"'{value}'"
                else:
                    escaped_value = str(value)
                
                config_conditions.append(f"${field} == {escaped_value}")
            if 'condition' in config:
                custom_condition = config['condition'].strip()
                if custom_condition:
                    config_conditions.append(custom_condition)
            if config_conditions:
                config_condition = " and ".join(config_conditions)
                all_conditions.append(f"({config_condition})")
        if all_conditions:
            return " or ".join(all_conditions)
        else:
            return ""
