"""Тесты действий плагина Database."""

from pathlib import Path

import pytest

from plugins.core.database.database import Database


@pytest.fixture
def database_plugin(temp_db_path, mock_logger):
    """Экземпляр плагина с временной БД."""
    from unittest.mock import MagicMock

    from app.runtime.context import AppContext

    cwd = Path.cwd()
    config = {
        "metadata": {},
        "settings": {"db_path": temp_db_path, "storage_limit": 100},
        "actions": {},
        "contributes": {},
        "app_metadata": {"project_root": str(cwd), "data_path": str(cwd / "data")},
    }
    api_bus = MagicMock()
    context = AppContext(api_bus=api_bus, logger=mock_logger)
    return Database(config=config, context=context)


@pytest.mark.asyncio
async def test_get_storage_single(database_plugin):
    """get_storage: одно значение по group_key + key."""
    await database_plugin.set_storage({"group_key": "g1", "key": "k1", "value": 42})
    out = await database_plugin.get_storage({"group_key": "g1", "key": "k1"})
    assert out["result"] == "success"
    assert out["response_data"]["storage_values"] == 42


@pytest.mark.asyncio
async def test_get_storage_missing_returns_none(database_plugin):
    """get_storage: запрос несуществующей пары возвращает success и storage_values=None."""
    out = await database_plugin.get_storage({"group_key": "g1", "key": "k1"})
    assert out["result"] == "success"
    assert out["response_data"]["storage_values"] is None


@pytest.mark.asyncio
async def test_get_storage_group(database_plugin):
    """get_storage: вся группа."""
    await database_plugin.set_storage({"group_key": "g1", "values": {"a": 1, "b": 2}})
    out = await database_plugin.get_storage({"group_key": "g1"})
    assert out["result"] == "success"
    assert out["response_data"]["storage_values"] == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_delete_storage(database_plugin):
    """delete_storage: удаление одной записи и группы."""
    await database_plugin.set_storage({"group_key": "g1", "key": "k1", "value": 1})
    out = await database_plugin.delete_storage({"group_key": "g1", "key": "k1"})
    assert out["result"] == "success"
    assert out["response_data"]["deleted_count"] == 1

    await database_plugin.set_storage({"group_key": "g2", "values": {"a": 1, "b": 2}})
    out = await database_plugin.delete_storage({"group_key": "g2"})
    assert out["result"] == "success"
    assert out["response_data"]["deleted_count"] == 2


@pytest.mark.asyncio
async def test_get_storage_with_patterns(database_plugin):
    """get_storage: поиск по group_key_pattern и key_pattern."""
    await database_plugin.set_storage({"group_key": "settings", "key": "a", "value": 1})
    await database_plugin.set_storage({"group_key": "settings", "key": "ab", "value": 2})
    await database_plugin.set_storage({"group_key": "limits", "key": "x", "value": 3})
    out = await database_plugin.get_storage({"group_key_pattern": "set%", "key_pattern": "a%"})
    assert out["result"] == "success"
    assert out["response_data"]["storage_values"] == {"settings": {"a": 1, "ab": 2}}
