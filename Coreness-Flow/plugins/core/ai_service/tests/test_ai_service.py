"""Тесты действий плагина ai_service (completion). Эмбеддинги вынесены в vector_store (add_chunks)."""

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_completion_missing_api_key(ai_service_plugin):
    """completion при пустом api_key возвращает CONFIG_ERROR."""
    ai_service_plugin._client.api_key = ""
    out = await ai_service_plugin.completion({"prompt": "Привет"})
    assert out["result"] == "error"
    assert out["error"]["code"] == "CONFIG_ERROR"
    # Сообщение о ненастроенном профиле (api_key/base_url) — единое для всех CONFIG_ERROR клиента
    msg = out["error"]["message"].lower()
    assert "api_key" in msg or "профиль" in msg or "настроен" in msg


@pytest.mark.asyncio
async def test_completion_missing_base_url_returns_config_error(mock_logger):
    """completion при отсутствии base_url (клиент не создан) возвращает CONFIG_ERROR."""
    from app.runtime.context import AppContext
    from plugins.core.ai_service.ai_service import AiService
    from unittest.mock import MagicMock

    cwd = Path.cwd()
    config = {"metadata": {}, "settings": {"api_key": "sk-test", "base_url": None}, "actions": {}, "contributes": {}, "app_metadata": {"project_root": str(cwd), "data_path": str(cwd / "data")}}
    api_bus = MagicMock()
    context = AppContext(api_bus=api_bus, logger=mock_logger)
    plugin = AiService(config=config, context=context)
    out = await plugin.completion({"prompt": "Привет"})
    assert out["result"] == "error"
    assert out["error"]["code"] == "CONFIG_ERROR"
    msg = out["error"]["message"].lower()
    assert "base_url" in msg or "api_key" in msg or "профиль" in msg or "настроен" in msg


@pytest.mark.asyncio
async def test_completion_missing_prompt(ai_service_plugin):
    """completion без prompt возвращает VALIDATION_ERROR."""
    out = await ai_service_plugin.completion({"prompt": ""})
    assert out["result"] == "error"
    assert out["error"]["code"] == "VALIDATION_ERROR"
    assert "prompt" in out["error"]["message"].lower()


@pytest.mark.asyncio
async def test_completion_success_mocked(ai_service_plugin):
    """completion при успешном ответе агрегатора возвращает success и response_data (мок клиента)."""
    async def mock_completion(*args, **kwargs):
        return {
            "result": "success",
            "response_data": {
                "response_completion": "Ответ модели",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "model": "test-model",
            },
        }
    ai_service_plugin._client.completion = mock_completion
    out = await ai_service_plugin.completion({"prompt": "Привет", "model": "test-model"})
    assert out["result"] == "success"
    assert out["response_data"]["response_completion"] == "Ответ модели"
    assert out["response_data"]["total_tokens"] == 15


@pytest.mark.asyncio
async def test_completion_tool_calls_arguments_parsed_as_dict(ai_service_plugin):
    """tool_calls.arguments из API (JSON-строка) парсится в dict; структура без лишнего экранирования."""
    from unittest.mock import MagicMock, AsyncMock

    expected_url = "https://raw.githubusercontent.com/Vensus137/Coreness/main/README_EN.md"
    msg = MagicMock()
    msg.content = ""
    msg.usage = MagicMock(prompt_tokens=1, completion_tokens=1, total_tokens=2)
    fn = MagicMock()
    fn.name = "tool_download_and_save_to_rag"
    fn.arguments = f'{{"url": "{expected_url}"}}'
    tc = MagicMock(id="imwaYNPer", function=fn)
    msg.tool_calls = [tc]
    choice = MagicMock(message=msg)
    response = MagicMock(choices=[choice])
    response.usage = MagicMock(prompt_tokens=1, completion_tokens=1, total_tokens=2)

    ai_service_plugin._client._client = MagicMock()
    ai_service_plugin._client._client.chat.completions.create = AsyncMock(return_value=response)

    out = await ai_service_plugin.completion({
        "prompt": "test",
        "model": "test-model",
        "messages": [],
        "tools": [{"type": "function", "function": {"name": "tool_download_and_save_to_rag", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}}}}],
        "tool_choice": "required",
    })
    assert out["result"] == "success", out.get("error", out)
    assert "tool_calls" in out.get("response_data", {}), out
    tool_calls = out["response_data"]["tool_calls"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "tool_download_and_save_to_rag"
    args = tool_calls[0]["arguments"]
    assert isinstance(args, dict), "arguments должен быть dict, не строка"
    assert args.get("url") == expected_url, f"url в arguments: {args!r}"


