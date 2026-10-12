"""
Tests for shift modifier (date shifting).
"""
import pytest

from conftest import assert_equal, process_text


@pytest.mark.asyncio
async def test_shift_basic_days(processor):
    """Basic day shifting."""
    result = await process_text(processor, "{'2024-12-25'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "Shift +1 day")
    result = await process_text(processor, "{'2024-12-25'|shift:-1 day}", {})
    assert_equal(result, "2024-12-24", "Shift -1 day")


@pytest.mark.asyncio
async def test_shift_hours_minutes(processor):
    """Hours and minutes shifting."""
    result = await process_text(processor, "{'2024-12-25 15:30:00'|shift:+2 hours}", {})
    assert_equal(result, "2024-12-25 17:30:00", "Shift +2 hours")
