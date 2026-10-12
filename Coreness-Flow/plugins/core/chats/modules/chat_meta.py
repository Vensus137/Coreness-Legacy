"""Работа с метаданными чатов: список, создание, переименование, закрепление, удаление."""

from datetime import datetime
from typing import Any, Dict, List

from .constants import GROUP_CHAT_META, USER_CHAT_ID_MIN, chat_group, now_iso
from . import storage


class ChatMeta:
    """Операции с chat_meta и списком чатов."""

    def __init__(self, plugin):
        self._plugin = plugin

    @property
    def _api_bus(self):
        return self._plugin.api_bus

    @property
    def _logger(self):
        return self._plugin.logger

    async def ensure_chat_zero(self) -> None:
        """Убедиться, что чат 0 есть в chat_meta (дефолтный чат)."""
        existing = await storage.get_storage(self._api_bus, GROUP_CHAT_META, key="0")
        if existing is not None:
            return
        meta = {"id": 0, "title": "Основной", "created_at": now_iso()}
        ok = await storage.set_storage_one(self._api_bus, GROUP_CHAT_META, "0", meta)
        if ok:
            self._logger.info("Инициализирован дефолтный чат (id=0)")

    async def chat_list(self, payload: dict) -> Dict[str, Any]:
        """Список чатов, отсортированный по created_at (новые сверху)."""
        try:
            meta = await storage.get_storage(self._api_bus, GROUP_CHAT_META)
            if meta is None or not isinstance(meta, dict):
                return {"result": "success", "response_data": {"chats": []}}
            chats: List[Dict[str, Any]] = []
            for k, v in meta.items():
                if not isinstance(v, dict):
                    continue
                cid = v.get("id")
                if cid is None:
                    try:
                        cid = int(k)
                    except (TypeError, ValueError):
                        continue
                cid_int = int(cid) if isinstance(cid, (int, float)) else cid
                pinned = cid_int < USER_CHAT_ID_MIN or bool(v.get("pinned", False))
                chats.append({
                    "id": cid_int,
                    "title": v.get("title") or "",
                    "created_at": v.get("created_at") or "",
                    "pinned": pinned,
                })

            def _sort_key(c: dict) -> tuple:
                if c["id"] < USER_CHAT_ID_MIN:
                    return (0, 0, c["id"])
                ts_str = c.get("created_at") or ""
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                except (TypeError, ValueError):
                    ts = 0.0
                return (1, 0 if c["pinned"] else 1, -ts)

            chats.sort(key=_sort_key)
            return {"result": "success", "response_data": {"chats": chats}}
        except Exception as e:
            self._logger.exception("chat_list: %s", e)
            return {"result": "error", "error": {"code": "CHAT_LIST_ERROR", "message": str(e)}}

    async def chat_create(self, payload: dict) -> Dict[str, Any]:
        """Создать чат; id от 10. Опционально title."""
        try:
            title = (payload.get("title") or "").strip() or "Новый чат"
            meta = await storage.get_storage(self._api_bus, GROUP_CHAT_META)
            if meta is None or not isinstance(meta, dict):
                meta = {}
            next_id = USER_CHAT_ID_MIN
            for k in meta:
                try:
                    n = int(k)
                    if n >= USER_CHAT_ID_MIN and n >= next_id:
                        next_id = n + 1
                except (TypeError, ValueError):
                    continue
            created_at = now_iso()
            new_meta = {"id": next_id, "title": title, "created_at": created_at}
            ok = await storage.set_storage_one(self._api_bus, GROUP_CHAT_META, str(next_id), new_meta)
            if not ok:
                return {"result": "error", "error": {"code": "CREATE_FAILED", "message": "Не удалось записать чат"}}
            await storage.set_storage_many(self._api_bus, chat_group(next_id), {"next_msg_index": 0})
            return {"result": "success", "response_data": {"id": next_id, "title": title, "created_at": created_at}}
        except Exception as e:
            self._logger.exception("chat_create: %s", e)
            return {"result": "error", "error": {"code": "CHAT_CREATE_ERROR", "message": str(e)}}

    async def chat_set_title(self, payload: dict) -> Dict[str, Any]:
        """Переименовать чат."""
        try:
            raw = payload.get("app_chat_id")
            title = (payload.get("title") or "").strip()
            if raw is None:
                return {"result": "error", "error": {"code": "MISSING_APP_CHAT_ID", "message": "Нужен app_chat_id"}}
            if not title:
                return {"result": "error", "error": {"code": "MISSING_TITLE", "message": "Нужно название"}}
            try:
                cid = int(raw)
            except (TypeError, ValueError):
                return {"result": "error", "error": {"code": "INVALID_APP_CHAT_ID", "message": "app_chat_id должен быть числом"}}
            existing = await storage.get_storage(self._api_bus, GROUP_CHAT_META, key=str(cid))
            if existing is None or not isinstance(existing, dict):
                return {"result": "error", "error": {"code": "CHAT_NOT_FOUND", "message": "Чат не найден"}}
            updated = {**existing, "title": title}
            ok = await storage.set_storage_one(self._api_bus, GROUP_CHAT_META, str(cid), updated)
            if not ok:
                return {"result": "error", "error": {"code": "SET_TITLE_FAILED", "message": "Не удалось обновить название"}}
            return {"result": "success"}
        except Exception as e:
            self._logger.exception("chat_set_title: %s", e)
            return {"result": "error", "error": {"code": "SET_TITLE_ERROR", "message": str(e)}}

    async def chat_set_pinned(self, payload: dict) -> Dict[str, Any]:
        """Закрепить или открепить чат. Только пользовательские (id >= 10)."""
        try:
            raw = payload.get("app_chat_id")
            pinned = payload.get("pinned", True)
            if raw is None:
                return {"result": "error", "error": {"code": "MISSING_APP_CHAT_ID", "message": "Нужен app_chat_id"}}
            try:
                cid = int(raw)
            except (TypeError, ValueError):
                return {"result": "error", "error": {"code": "INVALID_APP_CHAT_ID", "message": "app_chat_id должен быть числом"}}
            if cid < USER_CHAT_ID_MIN:
                return {"result": "error", "error": {"code": "CANNOT_UNPIN_SYSTEM_CHAT", "message": "Нельзя открепить системный чат (id 0–9)"}}
            existing = await storage.get_storage(self._api_bus, GROUP_CHAT_META, key=str(cid))
            if existing is None or not isinstance(existing, dict):
                return {"result": "error", "error": {"code": "CHAT_NOT_FOUND", "message": "Чат не найден"}}
            updated = {**existing, "pinned": bool(pinned)}
            ok = await storage.set_storage_one(self._api_bus, GROUP_CHAT_META, str(cid), updated)
            if not ok:
                return {"result": "error", "error": {"code": "SET_PINNED_FAILED", "message": "Не удалось обновить"}}
            return {"result": "success"}
        except Exception as e:
            self._logger.exception("chat_set_pinned: %s", e)
            return {"result": "error", "error": {"code": "CHAT_SET_PINNED_ERROR", "message": str(e)}}

    async def chat_delete(self, payload: dict) -> Dict[str, Any]:
        """Удалить чат безвозвратно. Только пользовательские (id >= 10)."""
        try:
            raw = payload.get("app_chat_id")
            if raw is None:
                return {"result": "error", "error": {"code": "MISSING_APP_CHAT_ID", "message": "Нужен app_chat_id"}}
            try:
                cid = int(raw)
            except (TypeError, ValueError):
                return {"result": "error", "error": {"code": "INVALID_APP_CHAT_ID", "message": "app_chat_id должен быть числом"}}
            if cid < USER_CHAT_ID_MIN:
                return {"result": "error", "error": {"code": "CANNOT_DELETE_SYSTEM_CHAT", "message": "Нельзя удалить системный чат (id 0–9)"}}
            group = chat_group(cid)
            await storage.delete_storage(self._api_bus, group)
            await storage.delete_storage(self._api_bus, GROUP_CHAT_META, key=str(cid))
            return {"result": "success"}
        except Exception as e:
            self._logger.exception("chat_delete: %s", e)
            return {"result": "error", "error": {"code": "CHAT_DELETE_ERROR", "message": str(e)}}
