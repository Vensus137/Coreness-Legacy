"""Фикстуры для тестов database."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture
def mock_logger():
    """Минимальный мок логгера."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.exception = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def temp_db_path():
    """Временный файл для SQLite (удаляется после теста)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def db_conn(temp_db_path):
    """Подключение к временной БД с созданной схемой."""
    from plugins.core.database.modules.connection import ensure_db
    conn = ensure_db(temp_db_path)
    yield conn
    conn.close()
