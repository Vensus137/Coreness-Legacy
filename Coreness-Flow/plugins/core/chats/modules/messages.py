"""Работа с сообщениями чата: чтение, добавление, пометки, история, очистка."""

from typing import Any, Dict, List

from .constants import MSG_KEY_PREFIX, chat_group, now_iso, payload_app_chat_id, msg_key
from . import storage


class ChatMessages:
    """Операции с сообщениями чата (storage + ключи msg_*)."""

    def __init__(self, plugin):
        self._plugin = plugin

    @property
    def _api_bus(self):
        return self._plugin.api_bus

    @property
    def _logger(self):
        return self._plugin.logger

    async def chat_get_messages(self, payload: dict) -> Dict[str, Any]:
        """Все сообщения чата (от старых к новым)."""
        try:
            raw = payload.get("app_chat_id")
            if raw is None:
                return {"result": "error", "error": {"code": "MISSING_APP_CHAT_ID", "message": "Нужен app_chat_id"}}
            try:
                cid = int(raw)
            except (TypeError, ValueError):
                return {"result": "error", "error": {"code": "INVALID_APP_CHAT_ID", "message": "app_chat_id должен быть числом"}}
            group = chat_group(cid)
            data = await storage.get_storage(self._api_bus, group, key_pattern=f"{MSG_KEY_PREFIX}%")
            if data is None or not isinstance(data, dict):
                return {"result": "success", "response_data": {"messages": []}}
            keys_sorted = sorted(k for k in data if k.startswith(MSG_KEY_PREFIX))
            messages = []
            for k in keys_sorted:
                try:
                    idx = int(k[len(MSG_KEY_PREFIX):])
                except (ValueError, TypeError):
                    continue
                val = data.get(k)
                if isinstance(val, dict):
                    messages.append({**val, "message_index": idx, "is_new": val.get("is_new", False)})
            return {"result": "success", "response_data": {"messages": messages}}
        except Exception as e:
            self._logger.exception("chat_get_messages: %s", e)
            return {"result": "error", "error": {"code": "GET_MESSAGES_ERROR", "message": str(e)}}

    async def chat_get_message(self, payload: dict) -> Dict[str, Any]:
        """Одно сообщение чата по message_index (для отрисовки по событию)."""
        try:
            raw = payload.get("app_chat_id")
            message_index = payload.get("message_index")
            if raw is None:
                return {"result": "error", "error": {"code": "MISSING_APP_CHAT_ID", "message": "Нужен app_chat_id"}}
            if message_index is None:
                return {"result": "error", "error": {"code": "MISSING_MESSAGE_INDEX", "message": "Нужен message_index"}}
            try:
                cid = int(raw)
                idx = int(message_index)
            except (TypeError, ValueError):
                return {"result": "error", "error": {"code": "INVALID_PARAMS", "message": "app_chat_id и message_index должны быть числами"}}
            group = chat_group(cid)
            key = msg_key(idx)
            val = await storage.get_storage(self._api_bus, group, key=key)
            if val is None or not isinstance(val, dict):
                return {"result": "error", "error": {"code": "NOT_FOUND", "message": "Сообщение не найдено"}}
            return {"result": "success", "response_data": {"message": {**val, "message_index": idx, "is_new": val.get("is_new", False)}}}
        except Exception as e:
            self._logger.exception("chat_get_message: %s", e)
            return {"result": "error", "error": {"code": "GET_MESSAGE_ERROR", "message": str(e)}}

    async def chat_mark_message_drawn(self, payload: dict) -> Dict[str, Any]:
        """Пометить сообщение как отрисованное (is_new=False). Вызывается перед анимацией."""
        try:
            raw = payload.get("app_chat_id")
            message_index = payload.get("message_index")
            if raw is None or message_index is None:
                return {"result": "error", "error": {"code": "MISSING_PARAMS", "message": "Нужны app_chat_id и message_index"}}
            try:
                cid = int(raw)
                idx = int(message_index)
            except (TypeError, ValueError):
                return {"result": "error", "error": {"code": "INVALID_PARAMS", "message": "app_chat_id и message_index должны быть числами"}}
            group = chat_group(cid)
            key = msg_key(idx)
            val = await storage.get_storage(self._api_bus, group, key=key)
            if val is None or not isinstance(val, dict):
                return {"result": "error", "error": {"code": "NOT_FOUND", "message": "Сообщение не найдено"}}
            updated = {**val, "is_new": False}
            ok = await storage.set_storage_one(self._api_bus, group, key, updated)
            if not ok:
                return {"result": "error", "error": {"code": "UPDATE_FAILED", "message": "Не удалось обновить"}}
            return {"result": "success"}
        except Exception as e:
            self._logger.exception("chat_mark_message_drawn: %s", e)
            return {"result": "error", "error": {"code": "MARK_DRAWN_ERROR", "message": str(e)}}

    async def chat_claim_message(self, payload: dict) -> Dict[str, Any]:
        """Пометить сообщение как не новое и вернуть данные (один источник правды для отображения по событию)."""
        try:
            raw = payload.get("app_chat_id")
            message_index = payload.get("message_index")
            if raw is None or message_index is None:
                return {"result": "error", "error": {"code": "MISSING_PARAMS", "message": "Нужны app_chat_id и message_index"}}
            try:
                cid = int(raw)
                idx = int(message_index)
            except (TypeError, ValueError):
                return {"result": "error", "error": {"code": "INVALID_PARAMS", "message": "app_chat_id и message_index должны быть числами"}}
            group = chat_group(cid)
            key = msg_key(idx)
            val = await storage.get_storage(self._api_bus, group, key=key)
            if val is None or not isinstance(val, dict):
                return {"result": "error", "error": {"code": "NOT_FOUND", "message": "Сообщение не найдено"}}
            updated = {**val, "is_new": False}
            ok = await storage.set_storage_one(self._api_bus, group, key, updated)
            if not ok:
                return {"result": "error", "error": {"code": "UPDATE_FAILED", "message": "Не удалось обновить"}}
            msg = {**updated, "message_index": idx, "is_new": False}
            return {"result": "success", "response_data": {"message": msg}}
        except Exception as e:
            self._logger.exception("chat_claim_message: %s", e)
            return {"result": "error", "error": {"code": "CLAIM_MESSAGE_ERROR", "message": str(e)}}

    async def append_message(self, payload: dict) -> Dict[str, Any]:
        """Добавить сообщение в чат (одна запись на сообщение, ключ msg_N с паддингом)."""
        try:
            raw = payload.get("app_chat_id")
            text = payload.get("text", "")
            sender = payload.get("sender") or "auto"
            if raw is None:
                return {"result": "error", "error": {"code": "MISSING_APP_CHAT_ID", "message": "Нужен app_chat_id"}}
            try:
                cid = int(raw)
            except (TypeError, ValueError):
                return {"result": "error", "error": {"code": "INVALID_APP_CHAT_ID", "message": "app_chat_id должен быть числом"}}
            group = chat_group(cid)
            next_idx_val = await storage.get_storage(self._api_bus, group, key="next_msg_index")
            if next_idx_val is None:
                idx = 0
            else:
                try:
                    idx = int(next_idx_val)
                except (TypeError, ValueError):
                    idx = 0
            key_msg = msg_key(idx)
            meta = payload.get("meta")
            effect = payload.get("effect")
            msg_value = {"text": text, "sender": sender, "timestamp": now_iso(), "is_new": True}
            if meta is not None and isinstance(meta, dict):
                msg_value["meta"] = meta
            if effect is not None and isinstance(effect, dict):
                msg_value["effect"] = effect
            ok = await storage.set_storage_many(self._api_bus, group, {key_msg: msg_value, "next_msg_index": idx + 1})
            if not ok:
                return {"result": "error", "error": {"code": "APPEND_FAILED", "message": "Не удалось записать сообщение"}}
            return {"result": "success", "response_data": {"message_index": idx}}
        except Exception as e:
            self._logger.exception("_append_message: %s", e)
            return {"result": "error", "error": {"code": "APPEND_MESSAGE_ERROR", "message": str(e)}}

    async def do_remove_message(self, cid: int, message_index: int) -> bool:
        """Удалить одно сообщение из storage и отправить событие в UI."""
        group = chat_group(cid)
        key = msg_key(message_index)
        ok = await storage.delete_storage(self._api_bus, group, key=key)
        if ok:
            self._api_bus.emit("chat:message_removed", {"app_chat_id": cid, "message_index": message_index})
        return ok

    async def change_message(self, payload: dict) -> Dict[str, Any]:
        """Изменить текст, sender, meta и/или effect сообщения по message_index; emit chat:message_changed. transition_effect в payload — только для события (анимация перехода на фронте)."""
        try:
            cid = payload_app_chat_id(payload, 0)
            raw_idx = payload.get("message_index")
            text = payload.get("text")
            sender = payload.get("sender")
            meta = payload.get("meta")
            effect = payload.get("effect")
            transition_effect = payload.get("transition_effect")
            if raw_idx is None:
                return {"result": "error", "error": {"code": "MISSING_MESSAGE_INDEX", "message": "Нужен message_index"}}
            try:
                idx = int(raw_idx)
            except (TypeError, ValueError):
                return {"result": "error", "error": {"code": "INVALID_MESSAGE_INDEX", "message": "message_index должен быть числом"}}
            group = chat_group(cid)
            key = msg_key(idx)
            val = await storage.get_storage(self._api_bus, group, key=key)
            if val is None or not isinstance(val, dict):
                return {"result": "error", "error": {"code": "NOT_FOUND", "message": "Сообщение не найдено"}}
            updated = {**val}
            if text is not None:
                updated["text"] = text
            if sender is not None:
                updated["sender"] = sender
            if meta is not None and isinstance(meta, dict):
                updated["meta"] = meta
            effect_cleared = False
            if "effect" in payload:
                if effect is not None and isinstance(effect, dict):
                    updated["effect"] = effect
                else:
                    updated.pop("effect", None)
                    effect_cleared = True
            ok = await storage.set_storage_one(self._api_bus, group, key, updated)
            if not ok:
                return {"result": "error", "error": {"code": "UPDATE_FAILED", "message": "Не удалось обновить сообщение"}}
            msg_payload = {**updated, "message_index": idx, "is_new": updated.get("is_new", False)}
            if effect_cleared:
                msg_payload["effect"] = None
            self._api_bus.emit("chat:message_changed", {
                "app_chat_id": cid,
                "message_index": idx,
                "message": msg_payload,
                "transition_effect": transition_effect,
            })
            return {"result": "success", "response_data": {"message": msg_payload}}
        except Exception as e:
            self._logger.exception("change_message: %s", e)
            return {"result": "error", "error": {"code": "CHANGE_MESSAGE_ERROR", "message": str(e)}}

    async def chat_get_history(self, payload: dict) -> Dict[str, Any]:
        """Последние N сообщений чата с опциональной обрезкой по символам (для передачи в completion). offset — сдвиг от самого нового (0 = включая текущее сообщение, 1 = без него)."""
        try:
            cid = payload_app_chat_id(payload, 0)
            limit = payload.get("limit", 20)
            offset = payload.get("offset", 0)
            from_index = payload.get("from_index")
            max_chars = payload.get("max_chars")
            extra_roles_raw = payload.get("extra_roles")
            extra_roles: set = set(extra_roles_raw) if isinstance(extra_roles_raw, list) else set()
            allowed_senders = {"user", "assistant"} | extra_roles

            try:
                limit = max(1, int(limit))
            except (TypeError, ValueError):
                limit = 20
            try:
                offset = max(0, int(offset))
            except (TypeError, ValueError):
                offset = 0

            group = chat_group(cid)
            data = await storage.get_storage(self._api_bus, group, key_pattern=f"{MSG_KEY_PREFIX}%")
            if not isinstance(data, dict):
                return {"result": "success", "response_data": {"messages": []}}

            all_messages = []
            for k, v in data.items():
                if not k.startswith(MSG_KEY_PREFIX) or not isinstance(v, dict):
                    continue
                try:
                    idx = int(k[len(MSG_KEY_PREFIX):])
                except (ValueError, TypeError):
                    continue
                all_messages.append({**v, "message_index": idx})

            all_messages.sort(key=lambda m: m["message_index"], reverse=True)

            if from_index is not None:
                try:
                    fi = int(from_index)
                    all_messages = [m for m in all_messages if m["message_index"] <= fi]
                except (TypeError, ValueError):
                    pass

            all_messages = [m for m in all_messages if m.get("sender") in allowed_senders]
            limited = all_messages[offset:offset + limit]

            if max_chars:
                try:
                    char_limit = int(max_chars)
                    total_chars = 0
                    trimmed = []
                    for msg in limited:
                        msg_len = len(msg.get("text", ""))
                        if total_chars + msg_len > char_limit:
                            break
                        total_chars += msg_len
                        trimmed.append(msg)
                    limited = trimmed
                except (TypeError, ValueError):
                    pass

            limited.sort(key=lambda m: m["message_index"])
            messages = [
                {"text": m.get("text", ""), "sender": m.get("sender", ""), "timestamp": m.get("timestamp", ""), "message_index": m["message_index"]}
                for m in limited
            ]
            return {"result": "success", "response_data": {"messages": messages}}
        except Exception as e:
            self._logger.exception("chat_get_history: %s", e)
            return {"result": "error", "error": {"code": "GET_HISTORY_ERROR", "message": str(e)}}

    async def clear_chat(self, payload: dict) -> Dict[str, Any]:
        """Очистить чат: удалить сообщения в storage, сбросить next_msg_index, emit в UI."""
        try:
            cid = payload_app_chat_id(payload, 0)
            group = chat_group(cid)
            data = await storage.get_storage(self._api_bus, group, key_pattern=f"{MSG_KEY_PREFIX}%")
            if isinstance(data, dict):
                for k in data:
                    await storage.delete_storage(self._api_bus, group, key=k)
            await storage.set_storage_one(self._api_bus, group, "next_msg_index", 0)
            self._api_bus.emit("chat:clear", {"app_chat_id": cid})
            return {"result": "success"}
        except Exception as e:
            self._logger.exception("clear_chat: %s", e)
            return {"result": "error", "error": {"code": "CLEAR_FAILED", "message": str(e)}}
