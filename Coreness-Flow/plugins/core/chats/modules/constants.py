"""Константы и чистые утилиты плагина чатов (ключи storage, форматирование)."""

from datetime import datetime, timezone

GROUP_CHAT_META = "chat_meta"
MSG_KEY_PREFIX = "msg_"
MSG_KEY_PADDING = 10
USER_CHAT_ID_MIN = 10


def chat_group(chat_id: int) -> str:
    """Группа storage для сообщений чата."""
    return f"chat_{chat_id}"


def now_iso() -> str:
    """Текущее время ISO 8601 (UTC)."""
    return datetime.now(timezone.utc).isoformat()


def payload_app_chat_id(payload: dict, default: int = 0) -> int:
    """Из payload: app_chat_id (формат источник_id)."""
    raw = payload.get("app_chat_id")
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def msg_key(message_index: int) -> str:
    """Ключ storage для сообщения по индексу."""
    return f"{MSG_KEY_PREFIX}{message_index:0{MSG_KEY_PADDING}d}"
