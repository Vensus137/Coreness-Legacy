"""Фикстуры для тестов vector_store."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture
def mock_logger():
    """Мок логгера."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.exception = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def mock_tokenizer():
    """
    Мок токенизатора bge-m3: приблизительный подсчёт токенов (~4 символа на токен для ASCII).
    """
    class MockTokenizer:
        def encode(self, text, add_special_tokens=True):
            if not text:
                return []
            # Упрощённая оценка: ~4 символа на токен
            n = max(1, len(text) // 4)
            return list(range(n))

        def decode(self, token_ids):
            return " " * (len(token_ids) * 4)  # Приблизительно

    return MockTokenizer()
