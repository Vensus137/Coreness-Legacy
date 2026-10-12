"""Фикстуры для тестов download_service. Запуск из корня проекта: pytest plugins/additional/download_service/tests/."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Путь к каталогу плагина для импорта modules
_plugin_dir = Path(__file__).resolve().parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))


@pytest.fixture
def logger():
    """Мок логгера для модулей плагина."""
    return MagicMock()


@pytest.fixture
def temp_downloads_dir(tmp_path):
    """Временный каталог для загрузок."""
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    return downloads_dir
