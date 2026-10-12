"""Тесты погружения в результат подстановки (substitution_result_max_depth): список/словарь после подстановки обрабатываются один раз."""
import pytest
from pathlib import Path
import sys

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from conftest import process_data_full, processor


@pytest.mark.asyncio
async def test_substitution_result_list_resolved(processor):
    """Плейсхолдер даёт список строк-плейсхолдеров — при глубине 1 элементы разрешаются (кейс routing_tools)."""
    values = {
        "_cache": {
            "system": {
                "routing_tools": ["{_cache.tools.response_general|fallback:}", "{_cache.tools.response_default|fallback:}"],
            },
            "tools": {
                "response_general": {"type": "function", "function": {"name": "response_general", "description": "Ответ общий"}},
                "response_default": {"type": "function", "function": {"name": "response_default", "description": "Ответ по умолчанию"}},
            },
        },
    }
    data = {"tools": "{_cache.system.routing_tools|fallback:}"}
    result = await process_data_full(processor, data, values)
    assert "tools" in result
    tools = result["tools"]
    assert isinstance(tools, list)
    assert len(tools) == 2
    assert tools[0] == {"type": "function", "function": {"name": "response_general", "description": "Ответ общий"}}
    assert tools[1] == {"type": "function", "function": {"name": "response_default", "description": "Ответ по умолчанию"}}


@pytest.mark.asyncio
async def test_substitution_result_depth_zero_no_resolve(mock_logger, api_bus):
    """При substitution_result_max_depth=0 элементы списка после подстановки не разрешаются."""
    from app.runtime.context import AppContext
    from plugins.core.placeholder_processor.placeholder_processor import PlaceholderProcessor

    config = {
        "metadata": {},
        "settings": {"max_nesting_depth": 10, "substitution_result_max_depth": 0},
        "actions": {},
        "contributes": {},
        "app_metadata": {"project_root": str(Path.cwd()), "data_path": str(Path.cwd() / "data")},
    }
    context = AppContext(api_bus=api_bus, logger=mock_logger)
    proc = PlaceholderProcessor(config=config, context=context)

    values = {
        "ref_list": ["{tool_a|fallback:}"],
        "tool_a": {"name": "a"},
    }
    data = {"tools": "{ref_list|fallback:}"}
    result = await process_data_full(proc, data, values)
    assert result["tools"] == ["{tool_a|fallback:}"]


@pytest.mark.asyncio
async def test_list_in_input_unchanged(processor):
    """Список во входных данных (не результат подстановки) обрабатывается как раньше — плейсхолдеры в элементах разрешаются."""
    values = {"name": "John"}
    data = {"items": ["Hello {name}", "World"]}
    result = await process_data_full(processor, data, values)
    assert result["items"][0] == "Hello John"
    assert result["items"][1] == "World"
