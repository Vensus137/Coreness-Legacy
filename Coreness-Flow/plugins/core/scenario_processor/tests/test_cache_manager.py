"""Тесты CacheManager: _namespace и _response_key."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def api_bus():
    from app.runtime.api_bus import ApiBus
    return ApiBus()


@pytest.fixture
def cache_manager(mock_logger, api_bus):
    from plugins.core.scenario_processor.modules.cache_manager import CacheManager
    return CacheManager(mock_logger, api_bus)


def test_merge_response_data_flat(cache_manager):
    """Плоское кэширование: response_data мержится в _cache."""
    data = {}
    cache_manager.merge_response_data(
        response_data={"key1": 1, "key2": 2},
        data=data,
        action_name="test_action",
        params={}
    )
    assert data["_cache"] == {"key1": 1, "key2": 2}


def test_merge_response_data_namespace(cache_manager):
    """С _namespace данные попадают в _cache[namespace]."""
    data = {}
    cache_manager.merge_response_data(
        response_data={"value": 42},
        data=data,
        action_name="test_action",
        params={"_namespace": "my_ns"}
    )
    assert data["_cache"]["my_ns"] == {"value": 42}


def test_merge_response_data_namespace_merge(cache_manager):
    """Повторный merge в тот же _namespace глубоко сливается."""
    data = {"_cache": {"my_ns": {"a": 1}}}
    cache_manager.merge_response_data(
        response_data={"b": 2},
        data=data,
        action_name="test_action",
        params={"_namespace": "my_ns"}
    )
    assert data["_cache"]["my_ns"]["a"] == 1
    assert data["_cache"]["my_ns"]["b"] == 2


def test_merge_response_data_response_key_requires_config(cache_manager, api_bus):
    """_response_key подменяет ключ replaceable поля, если конфиг действия есть."""
    api_bus.set_action_config("get_value", {
        "output": {
            "response_data": {
                "properties": {
                    "storage_values": {"replaceable": True},
                }
            }
        }
    })
    data = {}
    cache_manager.merge_response_data(
        response_data={"storage_values": "secret"},
        data=data,
        action_name="get_value",
        params={"_response_key": "api_key"}
    )
    assert data["_cache"]["api_key"] == "secret"


def test_extract_cache(cache_manager):
    """extract_cache возвращает _cache из data."""
    data = {"_cache": {"a": 1}}
    assert cache_manager.extract_cache(data) == {"a": 1}
    assert cache_manager.extract_cache({}) is None
    assert cache_manager.extract_cache({"_cache": None}) is None
