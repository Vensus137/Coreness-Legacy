"""Целевые тесты: кэш при execute_scenario (одиночный и список сценариев)."""

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture
def cache_scenarios_dir(tmp_path):
    """Временная папка со сценариями, которые пишут в _cache (loading, system, tools)."""
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    (scenarios_dir / "cache_test.yaml").write_text("""
# Сценарий: один шаг, пишет в _cache.loading
scenario_loading:
  step:
    - action: "mock_loading"
      params:
        _namespace: "loading"

# Сценарий: два шага get_storage → _cache.system и _cache.tools
scenario_settings:
  step:
    - action: "mock_get_storage"
      params:
        group_key: "system"
        _response_key: "system"
    - action: "mock_get_storage"
      params:
        group_key: "tools"
        _response_key: "tools"

# Одиночный сценарий для проверки возврата кэша
scenario_single_cache:
  step:
    - action: "mock_loading"
      params:
        _namespace: "single_ns"

# Сценарий, который завершается ошибкой (для теста list + error)
scenario_fails:
  step:
    - action: "mock_fail"
      params:
        _namespace: "failed_ns"

# Сценарий, который возвращает abort (response_data.scenario_result)
scenario_aborts:
  step:
    - action: "mock_abort"
      params:
        _namespace: "aborted_ns"
""", encoding="utf-8")
    return str(scenarios_dir)


@pytest.fixture
def processor_with_cache_actions(mock_logger, api_bus_full, cache_scenarios_dir):
    """Processor с моками действий, которые возвращают response_data для кэша."""
    from app.runtime.context import AppContext
    from plugins.core.scenario_processor.scenario_processor import ScenarioProcessor

    cwd = Path.cwd()
    config = {
        "metadata": {},
        "settings": {
            "scenarios_path": str(cache_scenarios_dir),
            "step_timeout": 0,
            "scenario_timeout": 0,
            "scheduled_timeout": 0,
        },
        "actions": {},
        "contributes": {},
        "app_metadata": {"project_root": str(cwd), "data_path": str(cwd / "data")},
    }
    context = AppContext(api_bus=api_bus_full, logger=mock_logger)
    proc = ScenarioProcessor(config=config, context=context)

    async def mock_loading(payload):
        return {"result": "success", "response_data": {"loading_message_index": 42}}
    api_bus_full.register("mock_loading", mock_loading)

    async def mock_get_storage(payload):
        group = payload.get("group_key", "")
        return {
            "result": "success",
            "response_data": {
                "storage_values": {"routing_messages": 5} if group == "system" else {"response_general": {}},
                "storage_processed_at": {},
            },
        }
    api_bus_full.register("mock_get_storage", mock_get_storage)
    api_bus_full.set_action_config("mock_get_storage", {
        "output": {
            "response_data": {
                "properties": {
                    "storage_values": {"replaceable": True},
                }
            }
        }
    })

    async def mock_fail(payload):
        return {"result": "error", "error": {"code": "MOCK_ERROR", "message": "Тестовая ошибка"}}
    api_bus_full.register("mock_fail", mock_fail)

    async def mock_abort(payload):
        return {"result": "success", "response_data": {"scenario_result": "abort", "aborted_key": 1}}
    api_bus_full.register("mock_abort", mock_abort)
    return proc


@pytest.mark.asyncio
async def test_execute_scenario_single_returns_cache_in_response(processor_with_cache_actions):
    """Одиночный execute_scenario возвращает кэш подсценария в response_data (return_cache=True)."""
    proc = processor_with_cache_actions
    await proc.sync_scenarios({"force_reload": True})
    out = await proc.execute_scenario({
        "scenario": "scenario_single_cache",
        "return_cache": True,
        "_scenario_metadata": proc.scenario_engine.cache.get_scenario_metadata(),
    })
    assert out["result"] == "success"
    # Кэш должен быть в response_data (и потом смержится в data родителя шагом)
    assert "single_ns" in out.get("response_data", {}), "Ожидается кэш в response_data при одиночном сценарии"


@pytest.mark.asyncio
async def test_execute_scenario_list_preserves_cache_in_payload(processor_with_cache_actions):
    """
    execute_scenario со списком сценариев: кэш от всех подсценариев должен оказаться в переданном payload.
    Передаём payload с _cache и проверяем, что после вызова в нём есть данные от первого и второго сценария.
    """
    proc = processor_with_cache_actions
    await proc.sync_scenarios({"force_reload": True})
    meta = proc.scenario_engine.cache.get_scenario_metadata()
    assert meta is not None, "Метаданные сценариев должны быть после sync"

    payload = {
        "scenario": ["scenario_loading", "scenario_settings"],
        "_scenario_metadata": meta,
        "_cache": {},
    }
    out = await proc.execute_scenario(payload)
    assert out["result"] == "success", f"Ожидается success, получено: {out}"

    cache = payload.get("_cache") or {}
    assert "loading" in cache, (
        f"Ожидается _cache.loading после первого сценария в списке. Ключи кэша: {list(cache.keys())}"
    )
    assert "system" in cache, (
        f"Ожидается _cache.system после второго сценария в списке. Ключи кэша: {list(cache.keys())}"
    )
    assert "tools" in cache, (
        f"Ожидается _cache.tools после второго сценария в списке. Ключи кэша: {list(cache.keys())}"
    )


@pytest.mark.asyncio
async def test_execute_scenario_list_cache_visible_for_next_step(processor_with_cache_actions):
    """
    Эмуляция родительского сценария: один шаг — execute_scenario([loading, settings]).
    После шага в data родителя должен быть _cache с loading, system, tools (как при вызове из executor).
    """
    proc = processor_with_cache_actions
    await proc.sync_scenarios({"force_reload": True})
    meta = proc.scenario_engine.cache.get_scenario_metadata()

    # Как при шаге: action_data = {**data, **processed_params}; data уже с _cache = {}
    data = {"_cache": {}, "_scenario_metadata": meta}
    step_params = {"scenario": ["scenario_loading", "scenario_settings"]}
    payload = {**data, **step_params}

    out = await proc.execute_scenario(payload)
    assert out["result"] == "success"

    # Тот же объект data (payload) должен содержать накопленный кэш
    assert payload.get("_cache") is data.get("_cache"), "payload и data должны разделять один _cache"
    cache = data.get("_cache") or {}
    assert "loading" in cache, f"Ожидается loading в _cache. Имеется: {list(cache.keys())}"
    assert "system" in cache, f"Ожидается system в _cache. Имеется: {list(cache.keys())}"
    assert "tools" in cache, f"Ожидается tools в _cache. Имеется: {list(cache.keys())}"


@pytest.mark.asyncio
async def test_execute_scenario_single_return_cache_false(processor_with_cache_actions):
    """При return_cache=False кэш не попадает в response_data (только scenario_result)."""
    proc = processor_with_cache_actions
    await proc.sync_scenarios({"force_reload": True})
    out = await proc.execute_scenario({
        "scenario": "scenario_single_cache",
        "return_cache": False,
        "_scenario_metadata": proc.scenario_engine.cache.get_scenario_metadata(),
    })
    assert out["result"] == "success"
    rd = out.get("response_data", {})
    assert "scenario_result" in rd
    assert "single_ns" not in rd, "При return_cache=False кэш не должен быть в response_data"


@pytest.mark.asyncio
async def test_execute_scenario_list_when_second_not_found_cache_from_first_preserved(processor_with_cache_actions):
    """При ошибке второго вызова (сценарий не найден) кэш от первого уже смержен в payload."""
    proc = processor_with_cache_actions
    await proc.sync_scenarios({"force_reload": True})
    meta = proc.scenario_engine.cache.get_scenario_metadata()
    payload = {"scenario": ["scenario_loading", "nonexistent_scenario"], "_scenario_metadata": meta, "_cache": {}}
    out = await proc.execute_scenario(payload)
    assert out["result"] == "error"
    assert "loading" in (payload.get("_cache") or {}), "Кэш от первого сценария должен быть смержен до возврата error"


@pytest.mark.asyncio
async def test_execute_scenario_list_when_second_aborts_returns_abort(processor_with_cache_actions):
    """При abort второго сценария возвращается success с scenario_result=abort."""
    proc = processor_with_cache_actions
    await proc.sync_scenarios({"force_reload": True})
    meta = proc.scenario_engine.cache.get_scenario_metadata()
    payload = {"scenario": ["scenario_loading", "scenario_aborts"], "_scenario_metadata": meta, "_cache": {}}
    out = await proc.execute_scenario(payload)
    assert out["result"] == "success"
    assert out.get("response_data", {}).get("scenario_result") == "abort"


@pytest.mark.asyncio
async def test_execute_scenario_list_empty_returns_success(processor_with_cache_actions):
    """Пустой список сценариев возвращает success и scenario_result."""
    proc = processor_with_cache_actions
    await proc.sync_scenarios({"force_reload": True})
    meta = proc.scenario_engine.cache.get_scenario_metadata()
    payload = {"scenario": [], "_scenario_metadata": meta, "_cache": {}}
    out = await proc.execute_scenario(payload)
    assert out["result"] == "success"
    assert out.get("response_data", {}).get("scenario_result") == "success"


@pytest.mark.asyncio
async def test_execute_scenario_list_three_scenarios_all_caches_merged(processor_with_cache_actions):
    """Три сценария в списке: кэш от всех трёх должен быть в payload."""
    proc = processor_with_cache_actions
    await proc.sync_scenarios({"force_reload": True})
    meta = proc.scenario_engine.cache.get_scenario_metadata()
    payload = {
        "scenario": ["scenario_loading", "scenario_settings", "scenario_single_cache"],
        "_scenario_metadata": meta,
        "_cache": {},
    }
    out = await proc.execute_scenario(payload)
    assert out["result"] == "success"
    cache = payload.get("_cache") or {}
    assert "loading" in cache
    assert "system" in cache
    assert "tools" in cache
    assert "single_ns" in cache
