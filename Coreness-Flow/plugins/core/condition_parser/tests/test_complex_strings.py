"""
Tests for complex strings with hyphens and special characters (tokens, UUIDs, etc.)
"""
import pytest

from conftest import check_match


class TestComplexStrings:
    """Tests for complex strings with hyphens and special characters"""

    @pytest.mark.asyncio
    async def test_string_with_hyphens(self, parser):
        """Check string with hyphens (OpenRouter token)"""
        token = "sk-or-v1-1a2b3c4d5e6f7g8h9i0j"
        result = await check_match(parser, f'{token} == "{token}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_colon(self, parser):
        """Check string with colon (token format: number:string)"""
        token = "123:abc-def-ghi"
        result = await check_match(parser, f'{token} == "{token}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_and_colon(self, parser):
        """Check string with hyphens and colon"""
        token = "123:sk-or-v1-token"
        result = await check_match(parser, f'{token} == "{token}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_comparison(self, parser):
        """Check comparison of string with hyphens"""
        token = "sk-or-v1-token"
        result = await check_match(parser, f'{token} == "sk-or-v1-token"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_not_equal(self, parser):
        """Check inequality of string with hyphens"""
        token = "sk-or-v1-token"
        result = await check_match(parser, f'{token} == "other-token"', {})
        assert result is False

    @pytest.mark.asyncio
    async def test_string_with_hyphens_and_field(self, parser):
        """Check comparison of string with hyphens with field"""
        token = "sk-or-v1-token"
        result = await check_match(parser, f"$field == {token}", {"field": token})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_or_condition(self, parser):
        """Check or condition for strings with hyphens"""
        token1 = "sk-or-v1-token"
        token2 = "sk-or-v2-token"
        result = await check_match(
            parser, f'{token1} == "{token1}" or {token2} == "{token2}"', {}
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_and_condition(self, parser):
        """Check and condition for strings with hyphens"""
        token = "sk-or-v1-token"
        result = await check_match(parser, f'{token} == "{token}" and "test" == "test"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_lowercase_comparison(self, parser):
        """Check comparison of string with hyphens after lower (as in real scenario)"""
        token = "sk-or-v1-token"
        result = await check_match(parser, f'{token} == "null"', {})
        assert result is False

    @pytest.mark.asyncio
    async def test_string_with_hyphens_lowercase_none_comparison(self, parser):
        """Check comparison of string with hyphens with none (as in real scenario)"""
        token = "sk-or-v1-token"
        result = await check_match(parser, f'{token} == "none"', {})
        assert result is False

    @pytest.mark.asyncio
    async def test_string_with_hyphens_or_null_none(self, parser):
        """Check or null or none condition for string with hyphens (as in real scenario)"""
        token = "sk-or-v1-token"
        result = await check_match(parser, f'{token} == "null" or {token} == "none"', {})
        assert result is False

    @pytest.mark.asyncio
    async def test_string_with_hyphens_or_null_none_true(self, parser):
        """Check or null or none condition for null string (should be true)"""
        token = "null"
        result = await check_match(parser, f'{token} == "null" or {token} == "none"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_or_null_none_true_none(self, parser):
        """Check or null or none condition for none string (should be true)"""
        token = "none"
        result = await check_match(parser, f'{token} == "null" or {token} == "none"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_uuid_like_string(self, parser):
        """Check UUID-like string with hyphens"""
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = await check_match(parser, f'{uuid} == "{uuid}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_multiple_hyphens(self, parser):
        """Check string with multiple hyphens"""
        token = "a-b-c-d-e-f-g"
        result = await check_match(parser, f'{token} == "{token}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_and_numbers(self, parser):
        """Check string with hyphens and numbers"""
        token = "token-123-456-789"
        result = await check_match(parser, f'{token} == "{token}"', {})
        assert result is True
