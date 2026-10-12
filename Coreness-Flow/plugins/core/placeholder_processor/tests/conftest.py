"""
Local fixtures for placeholder_processor tests. No dependency on tests/conftest or archive.
"""
import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture
def mock_logger():
    """Minimal logger mock for plugin."""
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
def processor(mock_logger, api_bus):
    """PlaceholderProcessor instance with config and context."""
    from app.runtime.context import AppContext
    from plugins.core.placeholder_processor.placeholder_processor import PlaceholderProcessor

    config = {"metadata": {}, "settings": {"max_nesting_depth": 10}, "actions": {}, "contributes": {}, "app_metadata": {"project_root": str(Path.cwd()), "data_path": str(Path.cwd() / "data")}}
    context = AppContext(api_bus=api_bus, logger=mock_logger)
    return PlaceholderProcessor(config=config, context=context)


# --- Helpers for async payload API (mirror archive API for test porting) ---


async def process_text(processor, text: str, values: dict):
    """Call process_text_placeholders; return response_data['text']; raise if error."""
    payload = {"text": text, "values": values}
    resp = await processor.process_text_placeholders(payload)
    assert resp.get("result") == "success", resp.get("error", resp)
    return resp["response_data"]["text"]


async def process_data(processor, data, values: dict):
    """Call process_placeholders; return response_data['data']; raise if error."""
    payload = {"data": data, "values": values}
    resp = await processor.process_placeholders(payload)
    assert resp.get("result") == "success", resp.get("error", resp)
    return resp["response_data"]["data"]


async def process_data_full(processor, data, values: dict):
    """Call process_placeholders_full; return response_data['data']; raise if error."""
    payload = {"data": data, "values": values}
    resp = await processor.process_placeholders_full(payload)
    assert resp.get("result") == "success", resp.get("error", resp)
    return resp["response_data"]["data"]


def assert_equal(actual, expected, message=""):
    """Equality with type normalization (e.g. actual '30' matches expected 30)."""
    if isinstance(actual, str):
        if isinstance(expected, bool):
            if actual == "True":
                actual = True
            elif actual == "False":
                actual = False
        elif isinstance(expected, (int, float)):
            try:
                actual = float(actual) if isinstance(expected, float) else int(actual)
            except (ValueError, TypeError):
                pass
    assert actual == expected, f"{message}: expected {expected!r}, got {actual!r}"
