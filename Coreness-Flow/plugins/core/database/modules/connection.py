"""Подключение к SQLite: прагмы, создание схемы. Без обёрток ORM."""

import sqlite3
from pathlib import Path
from typing import Optional

# Прагмы для десктопного SQLite: WAL, разумный busy_timeout и synchronous
PRAGMAS = (
    "PRAGMA journal_mode=WAL;",
    "PRAGMA busy_timeout=5000;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;",
)

STORAGE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS storage (
    group_key TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    processed_at TEXT,
    PRIMARY KEY (group_key, key)
);
CREATE INDEX IF NOT EXISTS idx_storage_group_key ON storage(group_key);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Создаёт подключение к БД, применяет прагмы. Путь к файлу создаётся при необходимости."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    for stmt in PRAGMAS:
        conn.execute(stmt)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Создаёт таблицы и индексы, если их ещё нет (идемпотентно). Добавляет processed_at при необходимости."""
    conn.executescript(STORAGE_TABLE_SQL)
    cur = conn.execute("PRAGMA table_info(storage)")
    columns = [row[1] for row in cur.fetchall()]
    if "processed_at" not in columns:
        conn.execute("ALTER TABLE storage ADD COLUMN processed_at TEXT")
    conn.commit()


def ensure_db(db_path: str) -> sqlite3.Connection:
    """Подключение + инициализация схемы. Для старта плагина."""
    conn = get_connection(db_path)
    init_schema(conn)
    return conn
