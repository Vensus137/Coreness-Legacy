"""Работа с деревом поиска (search tree) для быстрого поиска по условиям."""

from typing import Any, List


class TreeManager:
    """Управление деревом поиска для быстрого поиска значений по условиям."""
    
    def __init__(self, logger):
        self.logger = logger
    
    def add_to_tree(
        self,
        search_tree: dict,
        parsed_condition: dict,
        item_name: str,
        item_value: Any
    ) -> bool:
        """Добавление элемента в дерево поиска."""
        search_path = parsed_condition['search_path']
        compiled_function = parsed_condition['compiled_function']
        if not search_path:
            if 'conditions' not in search_tree:
                search_tree['conditions'] = []
            
            condition_hash = parsed_condition.get('condition_hash')
            new_item = {
                item_name: item_value,
                'compiled_function': compiled_function,
                'condition_hash': condition_hash
            }
            
            is_duplicate = any(
                existing_item.get('condition_hash') == condition_hash and 
                existing_item.get(item_name) == item_value
                for existing_item in search_tree['conditions']
            )
            
            if not is_duplicate:
                search_tree['conditions'].append(new_item)
                return True
            else:
                return False
        current_level = search_tree
        sorted_fields = sorted(search_path.items())
        for field_name, field_value in sorted_fields:
            if field_name not in current_level:
                current_level[field_name] = {}
            current_level = current_level[field_name]
            
            if field_value not in current_level:
                current_level[field_value] = {}
            current_level = current_level[field_value]
        if 'conditions' not in current_level:
            current_level['conditions'] = []
        
        condition_hash = parsed_condition.get('condition_hash')
        new_item = {
            item_name: item_value,
            'compiled_function': compiled_function,
            'condition_hash': condition_hash
        }
        
        is_duplicate = any(
            existing_item.get('condition_hash') == condition_hash and 
            existing_item.get(item_name) == item_value
            for existing_item in current_level['conditions']
        )
        
        if not is_duplicate:
            current_level['conditions'].append(new_item)
            return True
        else:
            return False
    
    def search_in_tree(self, search_tree: dict, data: dict) -> List[Any]:
        """Быстрый поиск значений в дереве по данным события."""
        found_values = []
        self._search_tree_by_path(search_tree, data, found_values)
        return found_values

    def _search_tree_by_path(self, tree_node: dict, data: dict, found_values: List[Any]):
        """Обход дерева с проверкой условий в каждом узле."""
        if 'conditions' in tree_node:
            self._check_items(tree_node['conditions'], data, found_values)
        for key, value in tree_node.items():
            if key == 'conditions':
                continue
            
            if isinstance(value, dict):
                if key in data:
                    data_value = data[key]
                    if data_value in value:
                        self._search_tree_by_path(value[data_value], data, found_values)
    
    def _check_items(self, items: List[dict], data: dict, found_values: List[Any]):
        """Проверка элементов списка на совпадение с условием."""
        for item in items:
            if isinstance(item, dict):
                compiled_function = item.get('compiled_function')
                if compiled_function:
                    try:
                        if compiled_function(data):
                            for item_key, item_value in item.items():
                                if item_key not in ['compiled_function', 'condition_hash']:
                                    if item_value not in found_values:
                                        found_values.append(item_value)
                    except Exception as e:
                        self.logger.error(f"Ошибка проверки условия: {e}")
