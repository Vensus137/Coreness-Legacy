"""Загрузка storage из YAML и применение к БД: парсинг конфигов, объединение групп, синхронизация."""

from pathlib import Path
from typing import Any, Dict

import yaml

from .storage_table import delete, set_many


def load_from_yaml(storage_dir: Path, logger) -> Dict[str, Dict[str, Any]]:
    """Читает все *.yaml и *.yml из storage_dir рекурсивно, объединяет в {group_key: {key: value}}."""
    result: Dict[str, Dict[str, Any]] = {}
    if not storage_dir.is_dir():
        return result
    paths = sorted(storage_dir.rglob("*.yaml")) + sorted(storage_dir.rglob("*.yml"))
    for path in paths:
        if not path.is_file():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                continue
            for group_key, content in data.items():
                if not isinstance(content, dict):
                    continue
                result.setdefault(group_key, {}).update(content)
        except Exception as e:
            logger.warning("sync_storage: не удалось загрузить %s: %s", path, e)
    return result


def apply_sync(conn, merged: Dict[str, Dict[str, Any]]) -> int:
    """Для каждой группы удаляет её в БД и записывает данные из merged. Коммит не выполняет."""
    for group_key, values in merged.items():
        delete(conn, group_key=group_key)
        set_many(conn, values, group_key=group_key)
    return len(merged)
