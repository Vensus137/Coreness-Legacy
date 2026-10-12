"""Тесты TransitionHandler."""

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture
def mock_logger():
    from unittest.mock import MagicMock
    return MagicMock()


@pytest.fixture
def transition_handler(mock_logger):
    from plugins.core.scenario_processor.modules.transition_handler import TransitionHandler
    return TransitionHandler(mock_logger)


@pytest.mark.asyncio
async def test_process_transitions_continue(transition_handler):
    """Переход continue возвращает action continue."""
    transition = [{"action_result": "success", "transition_action": "continue"}]
    out = await transition_handler.process_transitions("success", transition)
    assert out["action"] == "continue"
    assert out["value"] is None
    

@pytest.mark.asyncio
async def test_process_transitions_any_has_priority(transition_handler):
    """Переход any обрабатывается первым."""
    transition = [
        {"action_result": "any", "transition_action": "break"},
        {"action_result": "success", "transition_action": "continue"},
    ]
    out = await transition_handler.process_transitions("success", transition)
    assert out["action"] == "break"


@pytest.mark.asyncio
async def test_process_transitions_jump_to_scenario(transition_handler):
    """jump_to_scenario с value возвращает value."""
    transition = [
        {"action_result": "success", "transition_action": "jump_to_scenario", "transition_value": "other_scenario"}
    ]
    out = await transition_handler.process_transitions("success", transition)
    assert out["action"] == "jump_to_scenario"
    assert out["value"] == "other_scenario"


@pytest.mark.asyncio
async def test_process_transitions_empty_returns_continue(transition_handler):
    """Пустой список переходов — continue."""
    out = await transition_handler.process_transitions("success", [])
    assert out["action"] == "continue"
