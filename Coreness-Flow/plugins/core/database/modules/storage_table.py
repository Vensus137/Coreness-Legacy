"""CRUD для таблицы storage: композитный ключ (group_key, key) -> value (JSON), processed_at (ISO)."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


def _serialize(value: Any) -> str:
    """Сериализация значения в JSON для хранения."""
    return json.dumps(value, ensure_ascii=False)


def _deserialize(raw: Optional[str]) -> Any:
    """Десериализация значения из JSON."""
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def _now_iso() -> str:
    """Текущее время в ISO 8601 (UTC)."""
    return datetime.now(timezone.utc).isoformat()


def get(conn: sqlite3.Connection, group_key: Optional[str] = None, key: Optional[str] = None,
        group_key_pattern: Optional[str] = None, key_pattern: Optional[str] = None, limit: int = 100
        ) -> Tuple[Any, Any]:
    """
    Чтение: точные group_key/key имеют приоритет; иначе — фильтр по паттернам LIKE (%, _).
    limit — жёсткий лимит числа записей.
    Возвращает (data, processed_at): data — значение/группа/словарь; processed_at — та же структура с датами (ISO).
    """
    # Одно значение по точному ключу
    if group_key is not None and key is not None and not group_key_pattern and not key_pattern:
        row = conn.execute(
            "SELECT value, processed_at FROM storage WHERE group_key = ? AND key = ?",
            (group_key, key),
        ).fetchone()
        if not row:
            return None, None
        return _deserialize(row[0]), (row[1] if row[1] else None)

    # Одна группа (точный group_key), опционально фильтр ключей по key_pattern
    if group_key is not None and not group_key_pattern:
        if key_pattern:
            rows = conn.execute(
                "SELECT key, value, processed_at FROM storage WHERE group_key = ? AND key LIKE ? ORDER BY key LIMIT ?",
                (group_key, key_pattern, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT key, value, processed_at FROM storage WHERE group_key = ? ORDER BY key LIMIT ?",
                (group_key, limit),
            ).fetchall()
        data = {r[0]: _deserialize(r[1]) for r in rows}
        pts = {r[0]: (r[2] or None) for r in rows}
        return data, pts

    # Поиск по паттернам (или полная выгрузка при обоих паттернах пустых)
    g_pattern = group_key_pattern if group_key_pattern else "%"
    k_pattern = key_pattern if key_pattern else "%"
    rows = conn.execute(
        "SELECT group_key, key, value, processed_at FROM storage WHERE group_key LIKE ? AND key LIKE ? ORDER BY group_key, key LIMIT ?",
        (g_pattern, k_pattern, limit),
    ).fetchall()
    result: Dict[str, Dict[str, Any]] = {}
    pts_result: Dict[str, Dict[str, Optional[str]]] = {}
    for g, k, v, pt in rows:
        result.setdefault(g, {})[k] = _deserialize(v)
        pts_result.setdefault(g, {})[k] = pt if pt else None
    return result, pts_result


def set_one(conn: sqlite3.Connection, group_key: str, key: str, value: Any) -> None:
    """Запись одной пары (group_key, key) -> value с обновлением processed_at."""
    conn.execute(
        "INSERT OR REPLACE INTO storage (group_key, key, value, processed_at) VALUES (?, ?, ?, ?)",
        (group_key, key, _serialize(value), _now_iso()),
    )


def set_many(conn: sqlite3.Connection, values: Dict[str, Any], group_key: Optional[str] = None) -> None:
    """
    Запись нескольких значений. values: либо {key: value} при заданном group_key, либо {group_key: {key: value}}.
    """
    if group_key is not None:
        for k, v in values.items():
            set_one(conn, group_key, k, v)
        return
    for g, pairs in values.items():
        if isinstance(pairs, dict):
            for k, v in pairs.items():
                set_one(conn, g, k, v)
        else:
            set_one(conn, g, "__value", pairs)


def delete(conn: sqlite3.Connection, group_key: str, key: Optional[str] = None) -> int:
    """Удаление: при key=None — вся группа, иначе одна запись. Возвращает число удалённых строк."""
    if key is not None:
        cur = conn.execute("DELETE FROM storage WHERE group_key = ? AND key = ?", (group_key, key))
    else:
        cur = conn.execute("DELETE FROM storage WHERE group_key = ?", (group_key,))
    return cur.rowcount


