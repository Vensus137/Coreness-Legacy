"""Обращение к storage через api_bus (плагин database)."""

from typing import Any, Dict


async def get_storage(api_bus: Any, group_key: str, key: str = None, key_pattern: str = None) -> Any:
    """Чтение из storage. Возвращает storage_values или None при ошибке."""
    payload = {"group_key": group_key}
    if key is not None:
        payload["key"] = key
    if key_pattern is not None:
        payload["key_pattern"] = key_pattern
    result = await api_bus.call("get_storage", payload)
    if result.get("result") != "success":
        return None
    return result.get("response_data", {}).get("storage_values")


async def set_storage_one(api_bus: Any, group_key: str, key: str, value: Any) -> bool:
    """Записать одну запись в storage."""
    result = await api_bus.call("set_storage", {"group_key": group_key, "key": key, "value": value})
    return result.get("result") == "success"


async def set_storage_many(api_bus: Any, group_key: str, values: Dict[str, Any]) -> bool:
    """Записать несколько записей в группу."""
    result = await api_bus.call("set_storage", {"group_key": group_key, "values": values})
    return result.get("result") == "success"


async def delete_storage(api_bus: Any, group_key: str, key: str = None) -> bool:
    """Удалить запись или всю группу (key=None)."""
    payload = {"group_key": group_key}
    if key is not None:
        payload["key"] = key
    result = await api_bus.call("delete_storage", payload)
    return result.get("result") == "success"
