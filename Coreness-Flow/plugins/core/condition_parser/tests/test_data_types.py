"""
Edge case tests with data types
"""
import pytest

from conftest import check_match


class TestNumericTypes:
    """Numeric type tests"""

    @pytest.mark.asyncio
    async def test_data_type_equals_zero(self, parser):
        """Check comparison with zero"""
        result = await check_match(parser, "$value == 0", {"value": 0})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_equals_zero_not_equal(self, parser):
        """Check comparison with zero - not equal"""
        result = await check_match(parser, "$value == 0", {"value": 1})
        assert result is False

    @pytest.mark.asyncio
    async def test_data_type_greater_than_negative(self, parser):
        """Check comparison with negative number"""
        result = await check_match(parser, "$value > -1", {"value": 0})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_int_equals_float(self, parser):
        """Check int comparison with float (auto conversion)"""
        result = await check_match(parser, "$value == 0.0", {"value": 0})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_float_equals_int(self, parser):
        """Check float comparison with int (auto conversion)"""
        result = await check_match(parser, "$value == 0", {"value": 0.0})
        assert result is True


class TestStringTypes:
    """String type tests"""

    @pytest.mark.asyncio
    async def test_data_type_equals_empty_string(self, parser):
        """Check comparison with empty string"""
        result = await check_match(parser, "$text == ''", {"text": ""})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_equals_empty_string_with_space(self, parser):
        """Check comparison with empty string - space"""
        result = await check_match(parser, "$text == ''", {"text": " "})
        assert result is False

    @pytest.mark.asyncio
    async def test_data_type_contains_empty_string(self, parser):
        """Check contains empty string (always True)"""
        result = await check_match(parser, "$text ~ ''", {"text": "anything"})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_not_contains_empty_string(self, parser):
        """Check not contains empty string (always False)"""
        result = await check_match(parser, "$text !~ ''", {"text": "anything"})
        assert result is False


class TestBooleanTypes:
    """Boolean type tests"""

    @pytest.mark.asyncio
    async def test_data_type_boolean_true(self, parser):
        """Check Boolean True"""
        result = await check_match(parser, "$flag == True", {"flag": True})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_boolean_false(self, parser):
        """Check Boolean False"""
        result = await check_match(parser, "$flag == False", {"flag": False})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_boolean_true_lowercase(self, parser):
        """Check Boolean true (lowercase)"""
        result = await check_match(parser, "$flag == true", {"flag": True})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_boolean_false_lowercase(self, parser):
        """Check Boolean false (lowercase)"""
        result = await check_match(parser, "$flag == false", {"flag": False})
        assert result is True


class TestNoneType:
    """None type tests"""

    @pytest.mark.asyncio
    async def test_data_type_equals_none(self, parser):
        """Check comparison with None"""
        result = await check_match(parser, "$field == None", {"field": None})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_not_equals_none(self, parser):
        """Check inequality with None"""
        result = await check_match(parser, "$field != None", {"field": None})
        assert result is False

    @pytest.mark.asyncio
    async def test_data_type_not_equals_none_has_value(self, parser):
        """Check inequality with None - has value"""
        result = await check_match(parser, "$field != None", {"field": "value"})
        assert result is True


class TestTypeConversion:
    """Automatic type conversion tests"""

    @pytest.mark.asyncio
    async def test_data_type_number_equals_string(self, parser):
        """Check number comparison with string (auto conversion)"""
        result = await check_match(parser, "$value == '123'", {"value": 123})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_string_equals_number(self, parser):
        """Check string comparison with number (auto conversion)"""
        result = await check_match(parser, "$value == 123", {"value": "123"})
        assert result is True
