"""Действия с кэшем сценария: set_cache, delete_cache."""

from typing import Any, Dict


async def run_set_cache(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Запись данных в _cache: возвращает cache из payload для мержа через merge_response_data (с учётом _namespace)."""
    cache = payload.get("cache")
    if cache is None:
        cache = {}
    return {"result": "success", "response_data": cache if isinstance(cache, dict) else {}}


async def run_delete_cache(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Удаление неймспейса/пути из _cache. Вложенность через точку (tools.ai_agent).
    Префикс _cache. в значении отбрасывается.
    """
    namespace = payload.get("namespace")
    if not namespace or not isinstance(namespace, str):
        return {
            "result": "error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Укажите namespace (строка) — путь в _cache для удаления, при вложенности через точку (например tools.ai_agent)",
            },
        }
    path_str = namespace.strip()
    if path_str.lower().startswith("_cache."):
        path_str = path_str[7:].strip(".")
    if not path_str:
        return {
            "result": "error",
            "error": {"code": "VALIDATION_ERROR", "message": "namespace не может быть только _cache"},
        }
    path = [p for p in path_str.split(".") if p]
    if not path:
        return {
            "result": "error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Укажите непустой путь (например tools или tools.ai_agent)",
            },
        }
    _cache = payload.get("_cache")
    if not isinstance(_cache, dict):
        return {"result": "success"}
    parent = _cache
    for key in path[:-1]:
        parent = parent.get(key) if isinstance(parent, dict) else None
        if not isinstance(parent, dict):
            return {"result": "success"}
    if isinstance(parent, dict) and path:
        parent.pop(path[-1], None)
    return {"result": "success"}
