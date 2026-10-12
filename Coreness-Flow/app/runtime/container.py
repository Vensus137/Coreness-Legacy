"""Сканирует plugins/, загружает конфиги, создаёт плагины (config, context), запускает run() где есть."""

import asyncio
import dataclasses
import importlib.util
import os
from pathlib import Path
from typing import Any, Dict, List

from app.settings import Settings, _deep_merge
from .context import AppContext

DEFAULT_PLUGINS_DIR = "plugins"


def _discover_plugin_dirs(plugins_root: Path) -> List[Path]:
    """Возвращает список каталогов с config.json (рекурсивно под plugins/)."""
    found: List[Path] = []
    for root, _dirs, _files in os.walk(plugins_root):
        if (Path(root) / "config.json").exists():
            found.append(Path(root))
    return found


def _plugin_name_from_config(plugin_config: dict, plugin_path: Path) -> str:
    """Имя плагина из config.metadata.name или из имени папки."""
    meta = plugin_config.get("metadata") or {}
    name = meta.get("name") or plugin_config.get("name")
    if name and isinstance(name, str):
        return name.strip()
    return plugin_path.name


def _find_plugin_class(module: Any, plugin_name: str) -> type | None:
    """Ищет главный класс плагина в модуле: CamelCase от plugin_name или первый не встроенный класс."""
    class_name = plugin_name.replace("_", " ").title().replace(" ", "")
    if hasattr(module, class_name):
        attr = getattr(module, class_name)
        if isinstance(attr, type):
            return attr
    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and getattr(attr, "__module__", "") == getattr(module, "__name__", ""):
            if attr.__module__.startswith(("builtins", "typing")):
                continue
            return attr
    return None


def _load_plugin_module(plugin_path: Path, plugin_name: str, project_root: Path) -> tuple:
    """Загружает Python-модуль плагина: plugin_name.py или первый .py в каталоге."""
    candidates = [plugin_path / f"{plugin_name}.py"]
    if not candidates[0].exists():
        candidates = sorted(plugin_path.glob("*.py"), key=lambda p: p.name)
        candidates = [p for p in candidates if not p.name.startswith("__")]
    if not candidates:
        return None, None
    mod_path = candidates[0]
    spec = importlib.util.spec_from_file_location(f"plugin_{plugin_name}", mod_path)
    if not spec or not spec.loader:
        return None, None
    module = importlib.util.module_from_spec(spec)
    try:
        rel = plugin_path.resolve().relative_to(project_root.resolve())
        package = str(rel).replace("\\", ".")
    except ValueError:
        package = f"plugin_{plugin_name}"
    module.__package__ = package
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        # Пробрасываем исключение с контекстом для логирования
        raise ImportError(f"Ошибка импорта модуля плагина {plugin_name} из {mod_path}: {e}") from e
    klass = _find_plugin_class(module, plugin_name)
    return module, klass


class Container:
    """Обнаруживает плагины, загружает конфиг, создаёт экземпляры плагинов, запускает их."""

    def __init__(self, settings: Settings, context: AppContext, plugins_dir: str | None = None) -> None:
        self._settings = settings
        self._context = context
        self._logger = context.logger
        self._plugins_dir = plugins_dir if plugins_dir is not None else DEFAULT_PLUGINS_DIR
        self._project_root = settings.project_root
        self._plugin_instances: List[Any] = []
        self._plugin_configs: Dict[str, dict] = {}
        self._plugin_paths: Dict[str, Path] = {}
        self._plugin_settings_schemas: Dict[str, dict] = {}
        self._background_tasks: List[asyncio.Task] = []

    def discover_plugins(self) -> List[Path]:
        """Возвращает список каталогов плагинов (с config.json)."""
        plugins_root = self._project_root / self._plugins_dir
        if not plugins_root.exists():
            return []
        return _discover_plugin_dirs(plugins_root)

    def load_plugin(self, plugin_path: Path) -> bool:
        """Загружает и инициализирует один плагин; возвращает True при успехе."""
        plugin_path = Path(plugin_path)
        plugin_config_raw = self._settings.load_plugin_config(str(plugin_path))
        if not plugin_config_raw:
            self._logger.warning(f"Плагин {plugin_path}: не найден config.json")
            return False
        plugin_name = _plugin_name_from_config(plugin_config_raw, plugin_path)
        config = self._settings.merge_config(plugin_config_raw, plugin_name)
        plugin_logger = (
            self._logger.get_logger(plugin_name)
            if hasattr(self._logger, "get_logger")
            else self._logger
        )
        plugin_context = dataclasses.replace(self._context, logger=plugin_logger)
        try:
            module, klass = _load_plugin_module(plugin_path, plugin_name, self._project_root)
        except Exception as e:
            self._logger.error(f"Ошибка загрузки модуля плагина {plugin_name} из {plugin_path}: {e}", exc_info=True)
            return False
        if not module:
            self._logger.warning(f"Плагин {plugin_name} из {plugin_path}: модуль не найден или пуст")
            return False
        try:
            if klass is not None:
                instance = klass(config=config, context=plugin_context)
            else:
                if not callable(getattr(module, "create_plugin", None)):
                    self._logger.warning(f"Плагин {plugin_name}: не найден класс и функция create_plugin")
                    return False
                instance = module.create_plugin(config=config, context=plugin_context)
        except Exception as e:
            self._logger.error(f"Ошибка создания экземпляра плагина {plugin_name}: {e}", exc_info=True)
            return False
        self._context.api_bus.register_plugin(instance, config.get("actions", {}))
        self._plugin_instances.append(instance)
        self._plugin_configs[plugin_name] = config
        self._plugin_paths[plugin_name] = plugin_path
        self._plugin_settings_schemas[plugin_name] = plugin_config_raw.get("settings") or {}
        return True

    def run_blocking_phase(self, progress_callback=None) -> None:
        """Запуск run_blocking() у плагинов. Выполняется до показа основного окна (пока крутится splash). После — контейнер запускает run() в фоне."""
        for instance in self._plugin_instances:
            run_blocking = getattr(instance, "run_blocking", None)
            if callable(run_blocking):
                run_blocking(progress_callback)

    def load_all(self) -> None:
        """Обнаруживает и загружает все плагины."""
        for path in self.discover_plugins():
            self.load_plugin(path)
        self._register_contributions_action()
        self._register_plugin_settings_actions()

    def _get_all_contributions(self) -> Dict[str, Any]:
        """Собирает контрибьюты в режиме pass-through: pluginId + объект из config без разбора полей."""
        workspace_list: List[dict] = []
        settings_list: List[dict] = []
        sidebar_list: List[dict] = []
        menus_merged: Dict[str, List[dict]] = {}

        for plugin_id, config in self._plugin_configs.items():
            contributes = config.get("contributes") or {}

            ws = contributes.get("workspace")
            if ws and isinstance(ws, dict) and ws.get("id") is not None:
                workspace_list.append({"pluginId": plugin_id, **dict(ws)})

            st = contributes.get("settings")
            if st and isinstance(st, dict) and st.get("fields") is not None:
                settings_list.append({"pluginId": plugin_id, **dict(st)})

            sb = contributes.get("sidebar")
            if sb and isinstance(sb, dict):
                items = sb.get("items")
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict) and it.get("id") is not None and it.get("label") is not None:
                            sidebar_list.append({"pluginId": plugin_id, **dict(it)})

            menus = contributes.get("menus")
            if menus and isinstance(menus, dict):
                for menu_id, menu_items in menus.items():
                    if not isinstance(menu_items, list):
                        continue
                    if menu_id not in menus_merged:
                        menus_merged[menu_id] = []
                    for it in menu_items:
                        if isinstance(it, dict) and it.get("id") is not None and it.get("label") is not None:
                            menus_merged[menu_id].append({"pluginId": plugin_id, **dict(it)})

        return {
            "workspace": workspace_list,
            "settings": settings_list,
            "sidebar": sidebar_list,
            "menus": menus_merged,
        }

    def _action_get_contributions(self, payload: dict) -> dict:
        """Обработчик действия get_contributions: возвращает все контрибьюты для UI (workspace и др.)."""
        contributions = self._get_all_contributions()
        return {"result": "success", "response_data": {"contributions": contributions}}

    def _register_contributions_action(self) -> None:
        """Регистрирует действие get_contributions в API Bus."""
        self._context.api_bus.register("get_contributions", self._action_get_contributions)

    _SECRET_PLACEHOLDER = "••••••••"

    def _action_get_plugin_settings(self, payload: dict) -> dict:
        """Возвращает схему и текущие значения настроек плагина для UI. Секреты отдаются как есть — маскировка и показ по кнопке на фронте."""
        plugin_id = payload.get("plugin_id")
        if not plugin_id or plugin_id not in self._plugin_paths:
            return {"result": "error", "error": {"code": "NOT_FOUND", "message": f"Плагин '{plugin_id}' не найден"}}
        path = self._plugin_paths[plugin_id]
        raw = self._settings.load_plugin_config(str(path))
        merged = self._settings.merge_config(raw, plugin_id)
        schema = self._plugin_settings_schemas.get(plugin_id) or {}
        values = dict(merged.get("settings") or {})
        return {"result": "success", "response_data": {"schema": schema, "values": values}}

    def _action_set_plugin_settings(self, payload: dict) -> dict:
        """Сохраняет переопределения настроек плагина в user_settings и эмитит plugin:settings_changed:{plugin_id}. Плейсхолдер секретов не перезаписывает значение."""
        plugin_id = payload.get("plugin_id")
        settings = payload.get("settings")
        if not plugin_id or plugin_id not in self._plugin_paths:
            return {"result": "error", "error": {"code": "NOT_FOUND", "message": f"Плагин '{plugin_id}' не найден"}}
        if not isinstance(settings, dict):
            return {"result": "error", "error": {"code": "INVALID_PAYLOAD", "message": "settings должен быть объектом"}}
        schema = self._plugin_settings_schemas.get(plugin_id) or {}
        raw = self._settings.load_plugin_config(str(self._plugin_paths[plugin_id]))
        merged = self._settings.merge_config(raw, plugin_id)
        merged_settings = merged.get("settings") or {}
        settings = dict(settings)
        for key, spec in schema.items():
            if isinstance(spec, dict) and spec.get("secret") and settings.get(key) == self._SECRET_PLACEHOLDER:
                settings[key] = merged_settings.get(key)
        user = self._settings.load_user_settings()
        current = user.get(plugin_id) or {}
        if not isinstance(current, dict):
            current = {}
        from app.settings import _deep_merge
        user[plugin_id] = _deep_merge(current, settings)
        self._settings.save_user_settings(user)
        raw = self._settings.load_plugin_config(str(self._plugin_paths[plugin_id]))
        merged = self._settings.merge_config(raw, plugin_id)
        new_values = merged.get("settings") or {}
        event_name = f"plugin:settings_changed:{plugin_id}"
        self._context.api_bus.emit(event_name, {"plugin_id": plugin_id, "settings": new_values})
        return {"result": "success"}

    def _register_plugin_settings_actions(self) -> None:
        """Регистрирует get_plugin_settings и set_plugin_settings в API Bus."""
        self._context.api_bus.register("get_plugin_settings", self._action_get_plugin_settings)
        self._context.api_bus.register("set_plugin_settings", self._action_set_plugin_settings)

    def run(self) -> None:
        """Запускает async run() у плагинов, у которых он есть."""
        for instance in self._plugin_instances:
            if hasattr(instance, "run") and callable(instance.run):
                if asyncio.iscoroutinefunction(instance.run):
                    task = asyncio.create_task(instance.run())
                    self._background_tasks.append(task)
                    self._logger.info(f"Запущена фоновая задача для {instance.__class__.__name__}")
                else:
                    try:
                        instance.run()
                        self._logger.info(f"Вызван синхронный run() для {instance.__class__.__name__}")
                    except Exception as e:
                        self._logger.error(f"Ошибка в синхронном run() для {instance.__class__.__name__}: {e}")

    def _get_shutdown_config(self) -> dict:
        """Читает секцию shutdown из конфига приложения (app)."""
        app_config = self._settings.get_app_config()
        return app_config.get("shutdown") or {}

    async def shutdown(self) -> None:
        """Корректное завершение: вызов shutdown у плагинов, отмена фоновых задач, остановка API Bus."""
        shutdown_cfg = self._get_shutdown_config()
        di_timeout = float(shutdown_cfg.get("di_container_timeout", 5.0))
        plugin_timeout = float(shutdown_cfg.get("plugin_timeout", 3.0))
        tasks_timeout = float(shutdown_cfg.get("background_tasks_timeout", 2.0))

        async def _do_shutdown() -> None:
            # 1. Shutdown плагинов с таймаутом (синхронный метод в отдельном потоке)
            for instance in self._plugin_instances:
                if hasattr(instance, "shutdown") and callable(instance.shutdown):
                    try:
                        await asyncio.wait_for(
                            asyncio.to_thread(instance.shutdown),
                            timeout=plugin_timeout,
                        )
                    except asyncio.TimeoutError:
                        self._logger.warning(
                            f"shutdown плагина {instance.__class__.__name__} не завершился за {plugin_timeout} с"
                        )
                    except Exception as e:
                        self._logger.error(f"Ошибка shutdown плагина {instance.__class__.__name__}: {e}")

            # 2. Отмена фоновых задач и ожидание с таймаутом
            if self._background_tasks:
                self._logger.info(f"Отмена {len(self._background_tasks)} фоновых задач...")
                for task in self._background_tasks:
                    task.cancel()
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._background_tasks, return_exceptions=True),
                        timeout=tasks_timeout,
                    )
                except asyncio.TimeoutError:
                    self._logger.warning(f"Фоновые задачи не завершились за {tasks_timeout} с")
                self._logger.info("Фоновые задачи остановлены")

            # 3. Остановка API Bus ThreadPoolExecutor
            await asyncio.to_thread(self._context.api_bus.shutdown)
            self._logger.info("API Bus остановлен")

        try:
            await asyncio.wait_for(_do_shutdown(), timeout=di_timeout)
        except asyncio.TimeoutError:
            self._logger.warning(f"Shutdown не завершился за {di_timeout} с")
        self._logger.info("Контейнер остановлен")
