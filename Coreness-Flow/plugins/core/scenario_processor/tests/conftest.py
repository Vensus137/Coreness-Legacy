"""Фикстуры для тестов scenario_processor."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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
    logger.debug = MagicMock()
    logger.get_logger = MagicMock(return_value=logger)
    return logger


@pytest.fixture
def api_bus():
    """Реальный ApiBus для регистрации действий."""
    from app.runtime.api_bus import ApiBus
    return ApiBus()


@pytest.fixture
def api_bus_full(api_bus, mock_logger):
    """ApiBus с condition_parser и placeholder_processor для сценариев."""
    from app.runtime.context import AppContext
    from plugins.core.condition_parser.condition_parser import ConditionParser
    from plugins.core.placeholder_processor.placeholder_processor import PlaceholderProcessor

    cwd = Path.cwd()
    config = {"metadata": {}, "settings": {}, "actions": {}, "contributes": {}, "app_metadata": {"project_root": str(cwd), "data_path": str(cwd / "data")}}
    context = AppContext(api_bus=api_bus, logger=mock_logger)
    parser = ConditionParser(config=config, context=context)
    api_bus.register("parse_condition", parser.parse_condition)
    api_bus.register("build_condition", parser.build_condition)
    api_bus.register("add_to_tree", parser.add_to_tree)
    api_bus.register("search_in_tree", parser.search_in_tree)
    api_bus.register("check_match", parser.check_match)
    proc = PlaceholderProcessor(config=config, context=context)
    api_bus.register("process_placeholders_full", proc.process_placeholders_full)
    api_bus.register("process_placeholders", proc.process_placeholders)
    api_bus.register("process_text_placeholders", proc.process_text_placeholders)
    return api_bus
