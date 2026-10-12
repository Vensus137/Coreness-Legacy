"""
Tests for format modifier with Unix timestamp.
"""
import pytest

from conftest import process_text


@pytest.mark.asyncio
async def test_format_unix_timestamp_to_datetime(processor):
    """Format Unix timestamp to datetime string."""
    values_dict = {"timestamp": 1770689288, "timestamp_str": "1770689288"}
    result = await process_text(processor, "{timestamp|format:datetime}", values_dict)
    assert isinstance(result, str)
    assert "2026" in result or "09.02" in result
    result = await process_text(processor, "{timestamp_str|format:datetime}", values_dict)
    assert isinstance(result, str)
    assert "2026" in result or "09.02" in result


@pytest.mark.asyncio
async def test_format_unix_timestamp_all_formats(processor):
    """All datetime format modifiers with Unix timestamp."""
    values_dict = {"ts": 1640444445}
    result = await process_text(processor, "{ts|format:date}", values_dict)
    assert isinstance(result, str)
    result = await process_text(processor, "{ts|format:time}", values_dict)
    assert isinstance(result, str)
