"""Тесты sync_scenarios и execute_scenario с временной папкой сценариев."""

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture
def temp_scenarios_dir(tmp_path):
    """Временная папка с одним YAML-сценарием."""
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    (scenarios_dir / "test.yaml").write_text("""
minimal_scenario:
  description: "Минимальный сценарий для теста"
  trigger:
    - event_type: "test_event"
  step:
    - action: "noop"
      params: {}
""", encoding="utf-8")
    return str(scenarios_dir)


@pytest.fixture
def processor(mock_logger, api_bus_full, temp_scenarios_dir):
    """ScenarioProcessor с временной папкой сценариев и полным api_bus."""
    from app.runtime.context import AppContext
    from plugins.core.scenario_processor.scenario_processor import ScenarioProcessor

    cwd = Path.cwd()
    config = {
        "metadata": {},
        "settings": {"scenarios_path": str(temp_scenarios_dir), "step_timeout": 0, "scenario_timeout": 0, "scheduled_timeout": 0},
        "actions": {},
        "contributes": {},
        "app_metadata": {"project_root": str(cwd), "data_path": str(cwd / "data")},
    }
    context = AppContext(api_bus=api_bus_full, logger=mock_logger)
    proc = ScenarioProcessor(config=config, context=context)
    # Регистрируем фейковое действие, которое вызывается шагом
    async def noop(payload):
        return {"result": "success", "response_data": {}}
    api_bus_full.register("noop", noop)
    return proc


@pytest.mark.asyncio
async def test_sync_scenarios_loads_yaml(processor):
    """sync_scenarios загружает сценарии из YAML и возвращает loaded_count."""
    out = await processor.sync_scenarios({"force_reload": True})
    assert out["result"] == "success"
    assert "response_data" in out
    assert out["response_data"]["loaded_count"] >= 1


@pytest.mark.asyncio
async def test_execute_scenario_by_name_after_sync(processor):
    """После sync_scenarios можно выполнить сценарий по имени."""
    await processor.sync_scenarios({"force_reload": True})
    out = await processor.execute_scenario({"scenario": "minimal_scenario", "return_cache": False})
    assert out["result"] == "success"
    assert out.get("response_data", {}).get("scenario_result") == "success"


@pytest.mark.asyncio
async def test_execute_scenario_unknown_returns_error(processor):
    """Выполнение неизвестного сценария возвращает error."""
    await processor.sync_scenarios({"force_reload": True})
    out = await processor.execute_scenario({"scenario": "nonexistent_scenario"})
    assert out["result"] == "error"


@pytest.mark.asyncio
async def test_execute_scenario_validation_error_when_not_string_or_list(processor):
    """При отсутствии scenario/scenario_name или неверном типе возвращается VALIDATION_ERROR."""
    await processor.sync_scenarios({"force_reload": True})
    out_empty = await processor.execute_scenario({})
    assert out_empty["result"] == "error"
    assert out_empty.get("error", {}).get("code") == "VALIDATION_ERROR"
    assert "строкой или массивом" in (out_empty.get("error", {}).get("message") or "")

    out_wrong_type = await processor.execute_scenario({"scenario": 123})
    assert out_wrong_type["result"] == "error"
    assert out_wrong_type.get("error", {}).get("code") == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_execute_scenario_array_runs_sequentially(processor):
    """Параметр scenario как массив имён выполняет сценарии последовательно."""
    await processor.sync_scenarios({"force_reload": True})
    out = await processor.execute_scenario({
        "scenario": ["minimal_scenario", "minimal_scenario"],
        "return_cache": False,
    })
    assert out["result"] == "success"
    assert out.get("response_data", {}).get("scenario_result") == "success"
