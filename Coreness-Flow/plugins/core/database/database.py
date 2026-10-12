"""Плагин работы с базой данных: SQLite, таблица storage (group_key + key -> value)."""

import asyncio
from pathlib import Path
from typing import Any, Dict

from .modules.connection import ensure_db, get_connection, init_schema
from .modules.storage_sync import apply_sync, load_from_yaml
from .modules.storage_table import delete, get, set_many, set_one


class Database:
    """
    Плагин БД: одна таблица storage с композитным ключом (group_key, key) и значением value (JSON).
    В перспективе возможны другие таблицы без изменения названия плагина.
    """

    def __init__(self, config: dict, context):
        self.config = config
        self.api_bus = context.api_bus
        self.logger = context.logger
        app_meta = config["app_metadata"]
        project_root = Path(app_meta["project_root"])
        data_path = Path(app_meta["data_path"])
        settings = config.get("settings") or {}

        self._project_root = project_root
        db_path_raw = settings.get("db_path", "app.db")
        self._db_path = str(data_path / db_path_raw) if not Path(db_path_raw).is_absolute() else db_path_raw
        self._storage_limit = max(1, int(settings.get("storage_limit", 100)))

        # Папка с YAML-конфигами storage (относительно корня проекта)
        storage_config_dir = settings.get("storage_config_dir", "config/storage")
        path = Path(storage_config_dir)
        self._storage_dir = path if path.is_absolute() else project_root / path

        self._plugin_id = (config.get("metadata") or {}).get("name")
        context.api_bus.subscribe(f"plugin:settings_changed:{self._plugin_id}", self._on_settings_changed)

        # Инициализация БД при старте (создание файла и таблиц)
        conn = ensure_db(self._db_path)
        conn.close()
        self.logger.info("Database плагин инициализирован")

    def _on_settings_changed(self, data: dict) -> None:
        """Обновляет атрибуты при изменении настроек из UI (событие plugin:settings_changed:{plugin_id})."""
        settings = data.get("settings") or {}
        if "storage_limit" in settings:
            self._storage_limit = max(1, int(settings["storage_limit"]))
        if "storage_config_dir" in settings:
            path = Path(settings["storage_config_dir"])
            self._storage_dir = path if path.is_absolute() else self._project_root / path
        self.logger.info("Настройки database обновлены из UI")

    def _conn(self):
        """Подключение к БД для одного запроса (закрывать после использования)."""
        conn = get_connection(self._db_path)
        init_schema(conn)
        return conn

    def _sync_storage_blocking(self) -> int:
        """Синхронная синхронизация storage (для вызова в executor, без блокировки UI). Возвращает число синхронизированных групп."""
        merged = load_from_yaml(self._storage_dir, self.logger)
        if not merged:
            return 0
        conn = self._conn()
        try:
            apply_sync(conn, merged)
            conn.commit()
            return len(merged)
        finally:
            conn.close()

    async def run(self) -> None:
        """При запуске плагина выполняет синхронизацию storage в пуле потоков, без блокировки UI."""
        try:
            loop = asyncio.get_event_loop()
            count = await loop.run_in_executor(None, self._sync_storage_blocking)
            if count > 0:
                self.logger.info("sync_storage: синхронизировано групп %d", count)
        except Exception as e:
            self.logger.exception("sync_storage: %s", e)

    async def sync_storage(self, payload: dict) -> Dict[str, Any]:
        """Синхронизация storage из YAML: для каждой группы из конфига — удалить группу в БД, загрузить данные."""
        try:
            merged = load_from_yaml(self._storage_dir, self.logger)
            if not merged:
                return {"result": "success", "response_data": {"synced_groups": 0}}
            conn = self._conn()
            try:
                apply_sync(conn, merged)
                conn.commit()
            finally:
                conn.close()
            self.logger.info("sync_storage: синхронизировано групп %d", len(merged))
            return {"result": "success", "response_data": {"synced_groups": len(merged)}}
        except Exception as e:
            self.logger.exception("sync_storage: %s", e)
            return {
                "result": "error",
                "error": {"code": "SYNC_STORAGE_ERROR", "message": str(e)},
            }


    async def get_storage(self, payload: dict) -> Dict[str, Any]:
        """Получить значение, группу или данные по паттернам. Лимит — жёсткий, из конфига."""
        try:
            group_key = payload.get("group_key")
            key = payload.get("key")
            group_key_pattern = payload.get("group_key_pattern") or None
            key_pattern = payload.get("key_pattern") or None
            conn = self._conn()
            try:
                data, processed_at = get(
                    conn,
                    group_key=group_key,
                    key=key,
                    group_key_pattern=group_key_pattern,
                    key_pattern=key_pattern,
                    limit=self._storage_limit,
                )
            finally:
                conn.close()

            return {
                "result": "success",
                "response_data": {"storage_values": data, "storage_processed_at": processed_at},
            }
        except Exception as e:
            self.logger.exception("get_storage: %s", e)
            return {
                "result": "error",
                "error": {"code": "GET_STORAGE_ERROR", "message": str(e)},
            }

    async def set_storage(self, payload: dict) -> Dict[str, Any]:
        """Записать значение или группу в storage."""
        try:
            group_key = payload.get("group_key")
            key = payload.get("key")
            value = payload.get("value")
            values = payload.get("values")

            conn = self._conn()
            try:
                if group_key is not None and key is not None and value is not None:
                    set_one(conn, group_key, key, value)
                    out = value
                    scope = ("one", group_key, key)
                elif group_key is not None and values is not None:
                    set_many(conn, values, group_key=group_key)
                    out = values
                    scope = ("group", group_key, None)
                elif values is not None:
                    set_many(conn, values, group_key=None)
                    out = values
                    scope = ("full", None, None)
                else:
                    conn.close()
                    return {
                        "result": "error",
                        "error": {
                            "code": "INVALID_PARAMS",
                            "message": "Нужны (group_key, key, value) или (group_key, values) или (values)",
                        },
                    }
                conn.commit()
                # Возвращаем processed_at в той же структуре, что и get_storage
                kind, gk, k = scope
                if kind == "one":
                    _, processed_at = get(conn, group_key=gk, key=k)
                elif kind == "group":
                    _, processed_at = get(conn, group_key=gk)
                else:
                    data, pts = get(conn, limit=self._storage_limit)
                    processed_at = {g: pts[g] for g in values if g in pts} if isinstance(values, dict) else {}
            finally:
                conn.close()

            return {
                "result": "success",
                "response_data": {"storage_values": out, "storage_processed_at": processed_at},
            }
        except Exception as e:
            self.logger.exception("set_storage: %s", e)
            return {
                "result": "error",
                "error": {"code": "SET_STORAGE_ERROR", "message": str(e)},
            }

    async def delete_storage(self, payload: dict) -> Dict[str, Any]:
        """Удалить значение или группу из storage."""
        try:
            group_key = payload.get("group_key")
            key = payload.get("key")
            if not group_key:
                return {
                    "result": "error",
                    "error": {"code": "INVALID_PARAMS", "message": "group_key обязателен"},
                }

            conn = self._conn()
            try:
                deleted = delete(conn, group_key=group_key, key=key)
                conn.commit()
            finally:
                conn.close()

            return {"result": "success", "response_data": {"deleted_count": deleted}}
        except Exception as e:
            self.logger.exception("delete_storage: %s", e)
            return {
                "result": "error",
                "error": {"code": "DELETE_STORAGE_ERROR", "message": str(e)},
            }

