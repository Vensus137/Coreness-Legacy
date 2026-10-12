"""Выполнение сценария или массива сценариев по имени."""

from typing import Any, Dict

from ..scenario_engine import ScenarioEngine


async def run_execute_scenario(scenario_engine: ScenarioEngine, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выполнение сценария или массива сценариев по имени.
    Одиночный сценарий: возвращает scenario_result и при return_cache — кэш в response_data.
    Список: выполняет последовательно, мержит кэш в payload['_cache'], при error/abort выходит.
    """
    scenario_param = payload.get("scenario")
    scenario_metadata = payload.get("_scenario_metadata")
    return_cache = payload.get("return_cache", True)
    if not isinstance(return_cache, bool):
        return_cache = True

    if isinstance(scenario_param, str):
        result, cache = await scenario_engine.execute_scenario_by_name(
            scenario_name=scenario_param,
            data=payload,
            scenario_metadata=scenario_metadata,
        )
        response_data = {"scenario_result": result}
        if return_cache and cache:
            response_data.update(cache)
            response_data["scenario_result"] = result
        return {
            "result": "success" if result != "error" else "error",
            "response_data": response_data,
        }

    if isinstance(scenario_param, list):
        last_result = "success"
        if "_cache" not in payload:
            payload["_cache"] = {}
        cache_manager = scenario_engine.executor.cache_manager
        for scenario_name in scenario_param:
            result, cache = await scenario_engine.execute_scenario_by_name(
                scenario_name=scenario_name,
                data=payload,
                scenario_metadata=scenario_metadata,
            )
            if cache:
                cache_manager.deep_merge_into(payload["_cache"], cache)
            if result == "error":
                return {"result": "error"}
            if result == "abort":
                return {"result": "success", "response_data": {"scenario_result": result}}
            last_result = result
        return {"result": "success", "response_data": {"scenario_result": last_result}}

    return {
        "result": "error",
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "scenario должен быть строкой или массивом",
        },
    }
