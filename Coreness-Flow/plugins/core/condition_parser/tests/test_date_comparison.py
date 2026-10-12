"""
Date comparison tests in conditions
Checks correct handling of dates in dd.mm.yyyy format (after placeholder expansion)
"""
import pytest

from conftest import check_match


class TestDateComparison:
    """Tests for date comparison in dd.mm.yyyy format"""

    @pytest.mark.asyncio
    async def test_date_equals_date_without_quotes(self, parser):
        """Check date comparison without quotes (as after placeholder expansion)"""
        result = await check_match(parser, "02.12.2012 == 02.12.2012", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_date_equals_date_from_field(self, parser):
        """Check date from field comparison with date without quotes"""
        result = await check_match(
            parser, "$date_field == 02.12.2012", {"date_field": "02.12.2012"}
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_date_not_equals_different_date(self, parser):
        """Check != operator for different dates"""
        result = await check_match(parser, "02.12.2012 != 03.12.2012", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_datetime_format(self, parser):
        """Check date comparison with time (format:datetime)"""
        result = await check_match(parser, "25.12.2024 15:30 == 25.12.2024 15:30", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_datetime_full_format(self, parser):
        """Check date comparison with full time (format:datetime_full)"""
        result = await check_match(
            parser, "25.12.2024 15:30:45 == 25.12.2024 15:30:45", {}
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_ip_address_comparison(self, parser):
        """Check IP address comparison"""
        result = await check_match(parser, "192.168.1.1 == 192.168.1.1", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_version_comparison(self, parser):
        """Check version comparison"""
        result = await check_match(parser, "1.2.3.4 == 1.2.3.4", {})
        assert result is True
