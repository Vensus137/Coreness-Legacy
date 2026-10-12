"""Локальные фикстуры для тестов condition_parser. Без зависимости от tests/conftest."""
import sys
from pathlib import Path

import pytest

# Корень проекта в path при запуске тестов из папки плагина
_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture
def mock_logger():
    """Минимальный мок логгера для плагина."""
    class Logger:
        def info(self, msg, *args, **kwargs): pass
        def warning(self, msg, *args, **kwargs): pass
        def error(self, msg, *args, **kwargs): pass
        def debug(self, msg, *args, **kwargs): pass
        def get_logger(self, name): return self
    return Logger()


@pytest.fixture
def api_bus():
    """Real ApiBus for registration."""
    from app.runtime.api_bus import ApiBus
    return ApiBus()


@pytest.fixture
def parser(mock_logger, api_bus):
    """ConditionParser instance with config and context."""
    from app.runtime.context import AppContext
    from plugins.core.condition_parser.condition_parser import ConditionParser

    cwd = Path.cwd()
    config = {"metadata": {}, "settings": {}, "actions": {}, "contributes": {}, "app_metadata": {"project_root": str(cwd), "data_path": str(cwd / "data")}}
    context = AppContext(api_bus=api_bus, logger=mock_logger)
    return ConditionParser(config=config, context=context)


async def check_match(parser, condition: str, data: dict) -> bool:
    """Call parser.check_match with payload; return response_data['matched']; assert success."""
    resp = await parser.check_match({"condition": condition, "data": data})
    assert resp.get("result") == "success", resp.get("error", resp)
    return resp["response_data"]["matched"]


async def build_condition(parser, configs: list) -> str:
    """Call parser.build_condition with payload; return response_data['condition_string']."""
    resp = await parser.build_condition({"configs": configs})
    assert resp.get("result") == "success", resp.get("error", resp)
    return resp["response_data"]["condition_string"]


async def parse_condition(parser, condition: str) -> dict:
    """Call parser.parse_condition with payload; return response_data."""
    resp = await parser.parse_condition({"condition": condition})
    assert resp.get("result") == "success", resp.get("error", resp)
    return resp["response_data"]
