"""Фикстуры для тестов ai_service."""

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
def ai_service_plugin(mock_logger):
    """Экземпляр AiService без api_key (для тестов ошибок валидации и MISSING_API_KEY)."""
    from app.runtime.context import AppContext
    from plugins.core.ai_service.ai_service import AiService

    cwd = Path.cwd()
    config = {
        "metadata": {},
        "settings": {
            "api_key": "sk-test",
            "base_url": "https://test.invalid",
            "default_model": None,
        },
        "actions": {},
        "contributes": {},
        "app_metadata": {"project_root": str(cwd), "data_path": str(cwd / "data")},
    }
    api_bus = MagicMock()
    context = AppContext(api_bus=api_bus, logger=mock_logger)
    return AiService(config=config, context=context)
