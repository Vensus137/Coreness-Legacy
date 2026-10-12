"""Тесты подстановки плейсхолдеров для аргументов инструментов (execution.tool)."""

import pytest

from conftest import process_text, process_data_full, processor


@pytest.mark.asyncio
async def test_cache_execution_tool_url_resolves(processor):
    """Аргументы тула лежат в _cache.execution.tool; плейсхолдер _cache.execution.tool.url подставляется в URL."""
    values = {
        "_cache": {
            "execution": {
                "tool": {"url": "https://raw.githubusercontent.com/Vensus137/Coreness/main/README_EN.md"},
            },
        },
    }
    result = await process_text(processor, "Загружаю файл: {_cache.execution.tool.url}", values)
    assert result == "Загружаю файл: https://raw.githubusercontent.com/Vensus137/Coreness/main/README_EN.md"

    result_url = await process_text(processor, "{_cache.execution.tool.url}", values)
    assert result_url == "https://raw.githubusercontent.com/Vensus137/Coreness/main/README_EN.md"


@pytest.mark.asyncio
async def test_cache_tool_url_unresolved_when_path_missing(processor):
    """При отсутствии _cache.tool плейсхолдер _cache.tool.url не разрешается — остаётся строка (не подставляется в URL)."""
    values = {
        "_cache": {
            "execution": {
                "tool": {"url": "https://example.com/file.md"},
            },
        },
    }
    result = await process_text(processor, "{_cache.tool.url}", values)
    assert result == "{_cache.tool.url}", "Путь _cache.tool отсутствует — плейсхолдер должен остаться буквальной строкой"
