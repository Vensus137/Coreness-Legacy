"""
Basic PlaceholderProcessor tests (payload API).
"""
import re

import pytest

from conftest import assert_equal, process_data, process_text


@pytest.mark.asyncio
async def test_builtin_now_placeholder(processor):
    """Встроенный плейсхолдер {now} возвращает Unix timestamp; process_text отдаёт строку, модификаторы format:* — читаемый вывод."""
    result = await process_text(processor, "{now}", {})
    assert result is not None
    ts = int(result) if isinstance(result, str) and result.isdigit() else result
    assert isinstance(ts, int), "now должен быть int или строка из цифр (Unix timestamp)"
    assert 1_000_000_000 <= ts <= 2_200_000_000, "timestamp в разумном диапазоне (2001–2030+)"
    result_time = await process_text(processor, "{now|format:time}", {})
    assert re.match(r"^\d{2}:\d{2}$", result_time), "now|format:time должен быть HH:MM"
    result_datetime = await process_text(processor, "{now|format:datetime}", {})
    assert re.search(r"\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}", result_datetime), "now|format:datetime — dd.mm.yyyy HH:MM"


@pytest.mark.asyncio
async def test_builtin_now_overridden_by_values(processor):
    """Если в values передан ключ now, используется он, а не встроенное значение."""
    result = await process_text(processor, "{now}", {"now": "2024-01-15 12:00:00"})
    assert "2024-01-15" in str(result) or "15.01.2024" in str(result)


@pytest.mark.asyncio
async def test_process_text_placeholders_simple(processor):
    """Simple {key} substitution in text."""
    result = await process_text(processor, "Hello {name}", {"name": "World"})
    assert result == "Hello World"


@pytest.mark.asyncio
async def test_process_text_placeholders_multiple(processor):
    """Multiple placeholders in one string."""
    result = await process_text(
        processor, "Hello {name}, age {age}", {"name": "John", "age": 30}
    )
    assert result == "Hello John, age 30"


@pytest.mark.asyncio
async def test_process_text_placeholders_unresolved(processor):
    """Unresolved placeholder remains in output."""
    result = await process_text(processor, "Hello {unknown}", {"name": "World"})
    assert "{unknown}" in result


@pytest.mark.asyncio
async def test_process_text_placeholders_missing_text(processor):
    """Missing text returns error."""
    resp = await processor.process_text_placeholders({"values": {"name": "World"}})
    assert resp["result"] == "error" and "error" in resp


@pytest.mark.asyncio
async def test_process_text_placeholders_missing_values(processor):
    """Missing values returns error."""
    resp = await processor.process_text_placeholders({"text": "Hello {name}"})
    assert resp["result"] == "error" and "error" in resp


@pytest.mark.asyncio
async def test_process_placeholders_dict(processor):
    """Placeholders in dict values."""
    data = {"greeting": "Hello {name}", "count": 1}
    result = await process_data(processor, data, {"name": "User"})
    assert result["greeting"] == "Hello User"
    assert result["count"] == 1


@pytest.mark.asyncio
async def test_process_placeholders_nested_dict(processor):
    """Placeholders in nested dict."""
    data = {"inner": {"msg": "Hi {who}"}}
    result = await process_data(processor, data, {"who": "Alice"})
    assert result["inner"]["msg"] == "Hi Alice"


@pytest.mark.asyncio
async def test_basic_placeholders_flat(processor):
    """Basic flat placeholders (string results)."""
    values_dict = {
        "name": "John",
        "age": 30,
        "active": True,
        "count": 0,
        "empty": "",
        "none": None,
    }
    result = await process_text(processor, "{name}", values_dict)
    assert result == "John"

    result = await process_text(processor, "{age}", values_dict)
    assert_equal(result, 30, "Simple number replacement")

    result = await process_text(processor, "{active}", values_dict)
    assert_equal(result, True, "Simple boolean replacement")

    result = await process_text(processor, "{nonexistent}", values_dict)
    assert "{nonexistent}" in str(result)

    result = await process_text(processor, "Hello {name}, age {age}", values_dict)
    assert result == "Hello John, age 30"

    result = await process_text(processor, "{empty}", values_dict)
    assert_equal(result, "", "Empty value")

    result = await process_text(processor, "{none}", values_dict)
    assert "{none}" in str(result)

    result = await process_text(processor, "{count}", values_dict)
    assert_equal(result, 0, "Zero as valid value")


@pytest.mark.asyncio
async def test_nested_access(processor):
    """Dot notation and nested access."""
    values_dict = {
        "user": {"name": "John", "profile": {"age": 30, "settings": {"theme": "dark"}}},
        "data": {"items": [1, 2, 3], "meta": {"count": 42}},
    }
    result = await process_text(processor, "{user.name}", values_dict)
    assert_equal(result, "John", "Simple dot notation")
    result = await process_text(processor, "{user.profile.age}", values_dict)
    assert_equal(result, 30, "Deep nesting")
    result = await process_text(processor, "{user.profile.settings.theme}", values_dict)
    assert_equal(result, "dark", "Very deep nesting")
    result = await process_text(processor, "{user.nonexistent}", values_dict)
    assert "{user.nonexistent}" in str(result)
    result = await process_text(processor, "{data.meta.count}", values_dict)
    assert_equal(result, 42, "Nested access in dictionary")


@pytest.mark.asyncio
async def test_array_access(processor):
    """Array access by index."""
    values_dict = {
        "items": [10, 20, 30, 40, 50],
        "users": [{"name": "John", "id": 1}, {"name": "Jane", "id": 2}, {"name": "Bob", "id": 3}],
        "matrix": [[1, 2], [3, 4]],
        "empty": [],
    }
    result = await process_text(processor, "{items[0]}", values_dict)
    assert_equal(result, 10, "Access by positive index")
    result = await process_text(processor, "{items[2]}", values_dict)
    assert_equal(result, 30, "Access by middle index")
    result = await process_text(processor, "{items[-1]}", values_dict)
    assert_equal(result, 50, "Access by negative index (-1)")
    result = await process_text(processor, "{items[-2]}", values_dict)
    assert_equal(result, 40, "Access by negative index (-2)")
    result = await process_text(processor, "{users[0].name}", values_dict)
    assert_equal(result, "John", "Access to object field in array")
    result = await process_text(processor, "{users[-1].id}", values_dict)
    assert_equal(result, 3, "Access to last object field")
    result = await process_text(processor, "{matrix[0][1]}", values_dict)
    assert_equal(result, 2, "Multiple indices")
    result = await process_text(processor, "{items[10]}", values_dict)
    assert "{items[10]}" in str(result)
    result = await process_text(processor, "{empty[0]}", values_dict)
    assert "{empty[0]}" in str(result)
