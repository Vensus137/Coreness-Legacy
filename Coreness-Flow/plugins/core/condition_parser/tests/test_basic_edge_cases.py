"""
Edge case tests
"""
import pytest

from conftest import check_match


class TestSimpleValues:
    """Simple value tests"""

    @pytest.mark.asyncio
    async def test_edge_case_simple_true(self, parser):
        """Check simple True"""
        result = await check_match(parser, "True", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_simple_false(self, parser):
        """Check simple False"""
        result = await check_match(parser, "False", {})
        assert result is False


class TestFieldEqualsItself:
    """Tests for field comparison with itself"""

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_string(self, parser):
        """Check field comparison with itself - string"""
        result = await check_match(parser, "$event_type == $event_type", {"event_type": "message"})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_number(self, parser):
        """Check number comparison with itself"""
        result = await check_match(parser, "$user_id == $user_id", {"user_id": 123})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_none(self, parser):
        """Check None comparison with itself"""
        result = await check_match(parser, "$field == $field", {"field": None})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_empty_string(self, parser):
        """Check empty string comparison with itself"""
        result = await check_match(parser, "$field == $field", {"field": ""})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_zero(self, parser):
        """Check zero comparison with itself"""
        result = await check_match(parser, "$field == $field", {"field": 0})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_false(self, parser):
        """Check False comparison with itself"""
        result = await check_match(parser, "$field == $field", {"field": False})
        assert result is True
