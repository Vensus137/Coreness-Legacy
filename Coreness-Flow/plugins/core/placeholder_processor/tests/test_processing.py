"""
Structure processing: nested placeholders, dict/list.
"""
import pytest

from conftest import assert_equal, process_data, process_data_full, process_text


@pytest.mark.asyncio
async def test_nested_placeholders(processor):
    """Nested placeholders in arithmetic and fallback."""
    values_dict = {"a": 10, "b": 5, "field": "price", "price": 1000, "format": "currency"}
    result = await process_text(processor, "{a|+{b}}", values_dict)
    assert_equal(result, 15, "Nested placeholder in arithmetic")
    result = await process_text(processor, "{nonexistent|fallback:{field}}", values_dict)
    assert_equal(result, "price", "Nested placeholder in fallback")


@pytest.mark.asyncio
async def test_dict_processing_flat(processor):
    """Dictionary processing with flat placeholders."""
    values_dict = {"name": "John", "age": 30}
    data = {"text": "Hello {name}", "number": "{age}"}
    result = await process_data(processor, data, values_dict)
    assert result["text"] == "Hello John"
    assert_equal(result["number"], 30, "Number in dict")

    data = {"user": {"greeting": "Hello {name}", "info": {"age": "{age}"}}}
    result = await process_data(processor, data, values_dict)
    assert result["user"]["greeting"] == "Hello John"
    assert_equal(result["user"]["info"]["age"], 30, "Deep nesting in dictionary")


@pytest.mark.asyncio
async def test_process_placeholders_full(processor):
    """process_placeholders_full preserves static fields."""
    data = {"text": "Hello {name}", "static": "unchanged"}
    values_dict = {"name": "User"}
    result = await process_data_full(processor, data, values_dict)
    assert result.get("text") == "Hello User"
    assert result.get("static") == "unchanged"


@pytest.mark.asyncio
async def test_list_processing_flat(processor):
    """List of strings and list of dicts with flat placeholders."""
    values_dict = {"name": "John", "items": [1, 2, 3]}
    data = ["Hello {name}", "World"]
    result = await process_data(processor, {"list": data}, values_dict)
    assert result["list"][0] == "Hello John"
    assert result["list"][1] == "World"

    data = [{"text": "Hello {name}"}, {"text": "Static"}]
    result = await process_data(processor, {"items": data}, values_dict)
    assert result["items"][0]["text"] == "Hello John"
    assert result["items"][1]["text"] == "Static"


@pytest.mark.asyncio
async def test_list_processing_expand(processor):
    """Expand modifier for array of arrays."""
    values_dict = {"keyboard": [[{"Button 1": "action1"}], [{"Button 3": "action3"}]], "name": "John"}
    data = {"inline": ["{keyboard|expand}", {"Back": "back"}]}
    result = await process_data(processor, data, values_dict)
    inline_result = result.get("inline", [])
    assert isinstance(inline_result, list)
    if len(inline_result) > 0:
        assert isinstance(inline_result[0], list)
