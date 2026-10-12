"""
Modifier tests.
"""
import pytest

from conftest import assert_equal, process_text


@pytest.mark.asyncio
async def test_modifiers_with_quoted_parameters(processor):
    """Modifiers with quoted parameters."""
    values_dict = {"text": "hello world", "number": 100, "status": "active"}
    result = await process_text(processor, "{nonexistent|fallback:'default'}", values_dict)
    assert_equal(result, "default", "fallback with single quoted parameter")
    result = await process_text(processor, "{text|truncate:'5'}", values_dict)
    assert_equal(result, "he...", "truncate with quoted parameter")
    result = await process_text(processor, "{number|+'50'}", values_dict)
    assert_equal(result, "150", "arithmetic with quoted parameter")


@pytest.mark.asyncio
async def test_modifiers_string(processor):
    """String modifiers: upper, lower, title, capitalize, case."""
    values_dict = {"text": "hello world", "upper": "UPPER", "lower": "lower"}
    result = await process_text(processor, "{text|upper}", values_dict)
    assert_equal(result, "HELLO WORLD", "upper modifier")
    result = await process_text(processor, "{upper|lower}", values_dict)
    assert_equal(result, "upper", "lower modifier")
    result = await process_text(processor, "{text|title}", values_dict)
    assert_equal(result, "Hello World", "title modifier")


@pytest.mark.asyncio
async def test_modifiers_fallback(processor):
    """Fallback modifier."""
    values_dict = {"exists": "value", "empty": "", "zero": 0, "false": False, "none": None}
    result = await process_text(processor, "{nonexistent|fallback:default}", values_dict)
    assert_equal(result, "default", "Fallback for non-existent")
    result = await process_text(processor, "{empty|fallback:default}", values_dict)
    assert_equal(result, "default", "Fallback for empty string")
    result = await process_text(processor, "{exists|fallback:default}", values_dict)
    assert_equal(result, "value", "Fallback does not trigger for existing")
    result = await process_text(processor, "{zero|fallback:default}", values_dict)
    assert_equal(result, 0, "Fallback does not trigger for 0")


@pytest.mark.asyncio
async def test_modifiers_arithmetic(processor):
    """Arithmetic modifiers: +, -, *, /, %."""
    values_dict = {"ten": 10, "five": 5}
    result = await process_text(processor, "{ten|+5}", values_dict)
    assert_equal(result, 15, "add")
    result = await process_text(processor, "{ten|+{five}}", values_dict)
    assert_equal(result, 15, "add with nested placeholder")
    result = await process_text(processor, "{ten|-5}", values_dict)
    assert_equal(result, 5, "subtract")
    result = await process_text(processor, "{ten|*5}", values_dict)
    assert_equal(result, 50, "multiply")
    result = await process_text(processor, "{ten|/5}", values_dict)
    assert_equal(result, 2, "divide")
    # Число как поле (результат вложенного плейсхолдера): при арифметическом модификаторе парсится как число
    result = await process_text(processor, "{0|+1}", {})
    assert_equal(result, 1, "0|+1 when 0 is numeric field (no path)")
    result = await process_text(processor, "{5|-2}", {})
    assert_equal(result, 3, "5|-2 when 5 is numeric field")
    result = await process_text(processor, "{{missing|fallback:0}|+1}", {})
    assert_equal(result, 1, "nested: fallback:0 then +1")
