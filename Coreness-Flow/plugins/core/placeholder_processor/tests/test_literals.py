"""
Tests for literal values in quotes.
"""
import pytest

from conftest import assert_equal, process_text


@pytest.mark.asyncio
async def test_literals_basic(processor):
    """Literal values in single and double quotes."""
    result = await process_text(processor, "{'hello'}", {})
    assert_equal(result, "hello", "Literal in single quotes")
    result = await process_text(processor, '{"world"}', {})
    assert_equal(result, "world", "Literal in double quotes")
    result = await process_text(processor, "{'hello world'}", {})
    assert_equal(result, "hello world", "Literal with spaces")


@pytest.mark.asyncio
async def test_literals_string_modifiers(processor):
    """String modifiers with literals."""
    result = await process_text(processor, "{'hello'|upper}", {})
    assert_equal(result, "HELLO", "Literal with upper")
    result = await process_text(processor, "{'WORLD'|lower}", {})
    assert_equal(result, "world", "Literal with lower")
    result = await process_text(processor, "{'hello world'|title}", {})
    assert_equal(result, "Hello World", "Literal with title")
