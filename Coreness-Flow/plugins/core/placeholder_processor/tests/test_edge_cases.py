"""
Edge cases for current implementation.
"""
import pytest

from conftest import assert_equal, process_text


@pytest.mark.asyncio
async def test_edge_cases_flat(processor):
    """Edge cases supported by current implementation."""
    values_dict = {
        "empty": "",
        "zero": 0,
        "false": False,
        "none": None,
        "empty_list": [],
        "empty_dict": {},
    }
    result = await process_text(processor, "{empty}", values_dict)
    assert_equal(result, "", "Empty string")

    result = await process_text(processor, "{zero}", values_dict)
    assert_equal(result, 0, "Zero")

    result = await process_text(processor, "{false}", values_dict)
    assert_equal(result, False, "False")

    result = await process_text(processor, "{none}", values_dict)
    assert "{none}" in str(result), "None returns placeholder"

    result = await process_text(processor, "{empty_list}", values_dict)
    assert result == "[]", "Empty list as string"

    result = await process_text(processor, "{empty_dict}", values_dict)
    assert result == "{}", "Empty dict as string"

    result = await process_text(processor, "Just text", values_dict)
    assert result == "Just text", "Text without placeholders"


@pytest.mark.asyncio
async def test_edge_cases_braces(processor):
    """Only brace / empty placeholder (no crash)."""
    result = await process_text(processor, "{", {})
    assert result == "{", "Only opening brace"

    result = await process_text(processor, "}", {})
    assert result == "}", "Only closing brace"

    result = await process_text(processor, "{}", {})
    assert result is not None, "Empty placeholder"


@pytest.mark.asyncio
async def test_edge_cases_advanced(processor):
    """Advanced edge cases: modifier chains, nesting, fallback."""
    values_dict = {"text": "hello world"}
    result = await process_text(processor, "{text|upper|truncate:5|code}", values_dict)
    assert "<code>" in result

    result = await process_text(processor, "{|fallback:default}", {})
    assert_equal(result, "default", "Empty placeholder with fallback")

    values_dict = {"unicode": "Hello 世界 🌍"}
    result = await process_text(processor, "{unicode|upper}", values_dict)
    assert "HELLO" in result
