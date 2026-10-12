"""Тесты CRUD таблицы storage."""

import pytest

from plugins.core.database.modules.storage_table import delete, get, set_many, set_one


def test_set_one_get_one(db_conn):
    """Одна запись: set_one и get по group_key+key."""
    set_one(db_conn, "g1", "k1", 42)
    db_conn.commit()
    data, pt = get(db_conn, group_key="g1", key="k1")
    assert data == 42
    assert pt is not None and "T" in pt  # ISO дата


def test_set_one_overwrite(db_conn):
    """Перезапись одной записи."""
    set_one(db_conn, "g1", "k1", 1)
    set_one(db_conn, "g1", "k1", 2)
    db_conn.commit()
    data, _ = get(db_conn, group_key="g1", key="k1")
    assert data == 2


def test_get_missing(db_conn):
    """Запрос отсутствующей записи возвращает None."""
    data, pt = get(db_conn, group_key="g1", key="k1")
    assert data is None
    assert pt is None


def test_get_group(db_conn):
    """Получение группы целиком."""
    set_one(db_conn, "g1", "a", 1)
    set_one(db_conn, "g1", "b", "two")
    db_conn.commit()
    data, pts = get(db_conn, group_key="g1")
    assert data == {"a": 1, "b": "two"}
    assert set(pts) == {"a", "b"} and all(pts[k] and "T" in pts[k] for k in pts)


def test_get_all(db_conn):
    """Получение всех групп."""
    set_one(db_conn, "g1", "k1", 1)
    set_one(db_conn, "g2", "k2", 2)
    db_conn.commit()
    all_data, all_pts = get(db_conn, limit=100)
    assert all_data == {"g1": {"k1": 1}, "g2": {"k2": 2}}
    assert set(all_pts) == {"g1", "g2"} and all_pts["g1"]["k1"] and "T" in all_pts["g1"]["k1"]


def test_set_many_group(db_conn):
    """set_many с указанным group_key."""
    set_many(db_conn, {"a": 1, "b": 2}, group_key="g1")
    db_conn.commit()
    data, _ = get(db_conn, group_key="g1")
    assert data == {"a": 1, "b": 2}


def test_set_many_full(db_conn):
    """set_many полная структура {group_key: {key: value}}."""
    set_many(db_conn, {"g1": {"a": 1}, "g2": {"b": 2}})
    db_conn.commit()
    data1, _ = get(db_conn, group_key="g1")
    data2, _ = get(db_conn, group_key="g2")
    assert data1 == {"a": 1}
    assert data2 == {"b": 2}


def test_delete_one(db_conn):
    """Удаление одной записи."""
    set_one(db_conn, "g1", "k1", 1)
    db_conn.commit()
    n = delete(db_conn, "g1", key="k1")
    db_conn.commit()
    assert n == 1
    data, pt = get(db_conn, group_key="g1", key="k1")
    assert data is None and pt is None


def test_delete_group(db_conn):
    """Удаление всей группы."""
    set_one(db_conn, "g1", "a", 1)
    set_one(db_conn, "g1", "b", 2)
    db_conn.commit()
    n = delete(db_conn, "g1")
    db_conn.commit()
    assert n == 2
    data, pts = get(db_conn, group_key="g1")
    assert data == {} and pts == {}


def test_get_with_key_pattern(db_conn):
    """Получение группы с фильтром ключей по паттерну."""
    set_one(db_conn, "g1", "a", 1)
    set_one(db_conn, "g1", "ab", 2)
    set_one(db_conn, "g1", "b", 3)
    db_conn.commit()
    data, _ = get(db_conn, group_key="g1", key_pattern="a%", limit=10)
    assert data == {"a": 1, "ab": 2}


def test_get_with_group_key_pattern(db_conn):
    """Получение по паттерну группы."""
    set_one(db_conn, "settings", "x", 1)
    set_one(db_conn, "limits", "y", 2)
    set_one(db_conn, "set_extra", "z", 3)
    db_conn.commit()
    data, _ = get(db_conn, group_key_pattern="set%", limit=10)
    assert "settings" in data and "set_extra" in data
    assert "limits" not in data


def test_json_value(db_conn):
    """Значение — список и вложенный объект."""
    set_one(db_conn, "g1", "k1", [1, 2, {"x": "y"}])
    db_conn.commit()
    data, _ = get(db_conn, group_key="g1", key="k1")
    assert data == [1, 2, {"x": "y"}]
