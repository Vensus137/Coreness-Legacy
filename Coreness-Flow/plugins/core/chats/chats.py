"""Плагин чатов: список, создание, сообщения, переименование, удаление. Хранение в database (storage)."""

from typing import Any, Dict

from .modules.constants import payload_app_chat_id
from .modules.chat_meta import ChatMeta
from .modules.messages import ChatMessages


class ChatsPlugin:
    """Управление чатами через storage (плагин database)."""

    def __init__(self, config: dict, context):
        self.config = config
        self.api_bus = context.api_bus
        self.logger = context.logger
        self._chat_meta = ChatMeta(self)
        self._messages = ChatMessages(self)
        self.logger.info("Плагин чатов инициализирован")

    async def run(self) -> None:
        """При старте — наличие чата 0 в chat_meta."""
        await self._chat_meta.ensure_chat_zero()

    # ——— Метаданные чатов ———

    async def chat_list(self, payload: dict) -> Dict[str, Any]:
        return await self._chat_meta.chat_list(payload)

    async def chat_create(self, payload: dict) -> Dict[str, Any]:
        return await self._chat_meta.chat_create(payload)

    async def chat_set_title(self, payload: dict) -> Dict[str, Any]:
        return await self._chat_meta.chat_set_title(payload)

    async def chat_set_pinned(self, payload: dict) -> Dict[str, Any]:
        return await self._chat_meta.chat_set_pinned(payload)

    async def chat_delete(self, payload: dict) -> Dict[str, Any]:
        return await self._chat_meta.chat_delete(payload)

    # ——— Сообщения ———

    async def chat_get_messages(self, payload: dict) -> Dict[str, Any]:
        return await self._messages.chat_get_messages(payload)

    async def chat_get_message(self, payload: dict) -> Dict[str, Any]:
        return await self._messages.chat_get_message(payload)

    async def chat_mark_message_drawn(self, payload: dict) -> Dict[str, Any]:
        return await self._messages.chat_mark_message_drawn(payload)

    async def chat_claim_message(self, payload: dict) -> Dict[str, Any]:
        return await self._messages.chat_claim_message(payload)

    async def _append_message(self, payload: dict) -> Dict[str, Any]:
        return await self._messages.append_message(payload)

    async def chat_get_history(self, payload: dict) -> Dict[str, Any]:
        return await self._messages.chat_get_history(payload)

    async def clear_chat(self, payload: dict) -> Dict[str, Any]:
        return await self._messages.clear_chat(payload)

    # ——— Отправка и сценарии ———

    async def chat_submit_message(self, payload: dict) -> Dict[str, Any]:
        """Отправка сообщения пользователя: сохранить в storage, затем передать событие в сценарии."""
        try:
            event_type = payload.get("event_type")
            text = (payload.get("event_text") or "").strip()
            cid = payload_app_chat_id(payload, 0)
            if event_type == "message" and text:
                append_result = await self._append_message({
                    "app_chat_id": cid,
                    "text": text,
                    "sender": "user",
                })
                if append_result.get("result") != "success":
                    return append_result
                message_index = append_result.get("response_data", {}).get("message_index")
                if message_index is not None:
                    self.api_bus.emit("chat:new_message", {"app_chat_id": cid, "last_message_index": message_index})
                    payload = {**payload, "app_message_index": message_index}
            return await self.api_bus.call_nowait("process_scenario_event", payload)
        except Exception as e:
            self.logger.exception("chat_submit_message: %s", e)
            return {"result": "error", "error": {"code": "SUBMIT_FAILED", "message": str(e)}}

    async def send_chat_message(self, payload: dict) -> Dict[str, Any]:
        """Записать или заменить сообщение в чате и отправить событие в UI. Если передан message_index и сообщение есть — заменяется (chat:message_changed), иначе добавляется новое (chat:new_message). Всегда возвращает message_index."""
        try:
            raw_idx = payload.get("message_index")
            text = payload.get("text")
            text_stripped = (text or "").strip() if text is not None else ""
            sender = payload.get("sender") or "auto"
            meta = payload.get("meta")
            effect = payload.get("effect")
            transition_effect = payload.get("transition_effect")
            cid = payload_app_chat_id(payload, 0)

            if raw_idx is not None:
                try:
                    idx = int(raw_idx)
                except (TypeError, ValueError):
                    idx = None
                else:
                    change_payload = {"app_chat_id": cid, "message_index": idx, "sender": sender, "transition_effect": transition_effect}
                    if text is not None:
                        change_payload["text"] = text
                    if "meta" in payload:
                        change_payload["meta"] = meta
                    # При замене: передан effect — применить, не передан — снять предыдущий
                    change_payload["effect"] = effect if (effect is not None and isinstance(effect, dict)) else None
                    change_result = await self._messages.change_message(change_payload)
                    if change_result.get("result") == "success":
                        return {"result": "success", "response_data": {"message_index": idx}}

            if not text_stripped:
                return {"result": "error", "error": {"code": "EMPTY_TEXT", "message": "Текст сообщения не может быть пустым"}}
            append_payload = {"app_chat_id": cid, "text": text_stripped, "sender": sender}
            if meta is not None and isinstance(meta, dict):
                append_payload["meta"] = meta
            if effect is not None and isinstance(effect, dict):
                append_payload["effect"] = effect
            append_result = await self._append_message(append_payload)
            if append_result.get("result") != "success":
                err = append_result.get("error", {})
                return {"result": "error", "error": {"code": err.get("code", "APPEND_FAILED"), "message": err.get("message", "Не удалось записать сообщение")}}
            last_index = append_result.get("response_data", {}).get("message_index")
            self.api_bus.emit("chat:new_message", {"app_chat_id": cid, "last_message_index": last_index})
            return {"result": "success", "response_data": {"message_index": last_index}}
        except Exception as e:
            self.logger.exception("send_chat_message: %s", e)
            return {"result": "error", "error": {"code": "SEND_FAILED", "message": str(e)}}

    async def remove_chat_message(self, payload: dict) -> Dict[str, Any]:
        """Удалить одно сообщение из чата (storage + UI)."""
        try:
            cid = payload_app_chat_id(payload, 0)
            raw_idx = payload.get("message_index")
            if raw_idx is None:
                return {"result": "error", "error": {"code": "MISSING_MESSAGE_INDEX", "message": "Нужен message_index"}}
            try:
                message_index = int(raw_idx)
            except (TypeError, ValueError):
                return {"result": "error", "error": {"code": "INVALID_MESSAGE_INDEX", "message": "message_index должен быть числом"}}
            ok = await self._messages.do_remove_message(cid, message_index)
            if not ok:
                return {"result": "error", "error": {"code": "REMOVE_FAILED", "message": "Не удалось удалить сообщение"}}
            return {"result": "success"}
        except Exception as e:
            self.logger.exception("remove_chat_message: %s", e)
            return {"result": "error", "error": {"code": "REMOVE_FAILED", "message": str(e)}}
