"""
Tests for to_date, to_hour, to_month, to_year etc.
"""
import pytest

from conftest import assert_equal, process_text


@pytest.mark.asyncio
async def test_to_date(processor):
    """Conversion to start of day."""
    values_dict = {"datetime": "2024-12-25 15:30:45", "date": "2024-12-25", "timestamp": 1735128045}
    result = await process_text(processor, "{datetime|to_date}", values_dict)
    assert "2024-12-25" in result
    result = await process_text(processor, "{timestamp|to_date}", values_dict)
    assert result is not None


@pytest.mark.asyncio
async def test_to_hour_to_minute(processor):
    """Conversion to start of hour/minute."""
    values_dict = {"dt": "2024-12-25 15:30:45"}
    result = await process_text(processor, "{dt|to_hour}", values_dict)
    assert "15:00" in result or "15:00:00" in result
    result = await process_text(processor, "{dt|to_minute}", values_dict)
    assert result is not None
