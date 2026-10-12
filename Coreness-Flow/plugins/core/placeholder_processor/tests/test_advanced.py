"""
Complex scenarios: expand, combinations, async modifiers, deep nesting.
"""
import pytest

from conftest import assert_equal, process_data, process_text


@pytest.mark.asyncio
async def test_modifiers_expand_detailed(processor):
    """Expand modifier (array of arrays)."""
    values_dict = {"keyboard": [[{"Button 1": "action1"}, {"Button 2": "action2"}], [{"Button 3": "action3"}]]}
    data = {"inline": ["{keyboard|expand}", {"Back": "back"}]}
    result = await process_data(processor, data, values_dict)
    inline_result = result.get("inline", [])
    assert isinstance(inline_result, list)
    assert len(inline_result) == 3
    assert isinstance(inline_result[0], list)


@pytest.mark.asyncio
async def test_complex_combinations(processor):
    """Complex modifier combinations."""
    values_dict = {"price": 1000, "discount": 0.1, "status": "active", "field": None}
    result = await process_text(processor, "{price|*{discount}|format:currency|code}", values_dict)
    assert "<code>" in result and "₽" in result
    result = await process_text(processor, "{field|is_null|value:Empty|fallback:Filled}", values_dict)
    assert_equal(result, "Empty", "is_null with conditional")


@pytest.mark.asyncio
async def test_deep_nesting(processor):
    """Deep placeholder nesting."""
    values_dict = {"a": 10, "b": 5, "c": 2, "field1": "price", "price": 1000}
    result = await process_text(processor, "{a|+{b}|*{c}}", values_dict)
    assert_equal(result, 30, "Multilevel nesting in arithmetic")


@pytest.mark.asyncio
async def test_real_world_scenarios(processor):
    """Real-world usage scenarios."""
    values_dict = {"price": 1000, "discount": 0.15}
    result = await process_text(processor, "{price|*{discount}|format:currency}", values_dict)
    assert "₽" in result
    values_dict = {"user": {"profile": {"name": "John"}}}
    result = await process_text(processor, "{user.profile.name|fallback:Unknown}", values_dict)
    assert_equal(result, "John", "Safe access to nested fields")
