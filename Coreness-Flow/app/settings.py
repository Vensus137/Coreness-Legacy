"""Единый модуль настроек: загрузка/сохранение user_settings, app.json, конфиги плагинов; действие get_app_metadata через api_bus."""

import json
import os
import sys
import tempfile
from functools import cache
from pathlib import Path
from typing import Any

APP_CONFIG_FILENAME = "app.json"
USER_SETTINGS_FILENAME = "user_settings.json"
USER_DATA_DIR_NAME = "CorenessFlow"


# Конфиг действия get_app_metadata (тот же формат, что в config.json плагинов: type, description, properties).
# response_data: paths — для внутреннего использования (плагины), about — для UI «О приложении» (массив {label, value?, href?}).
GET_APP_METADATA_ACTION = {
    "name": "get_app_metadata",
    "description": "Метаданные приложения (пути и данные для блока «О приложении»).",
    "input": {},
    "output": {
        "result": {"type": "string", "description": "success / error"},
        "error": {
            "type": "object",
            "optional": True,
            "properties": {
                "code": {"type": "string", "description": "Код ошибки"},
                "message": {"type": "string", "description": "Сообщение об ошибке"},
            },
        },
        "response_data": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "object",
                    "description": "Пути для внутреннего использования (плагины): project_root, data_path.",
                    "properties": {
                        "project_root": {"type": "string", "description": "Корень проекта (абсолютный путь)"},
                        "data_path": {"type": "string", "description": "Каталог данных приложения (логи, БД, загрузки; напр. %%APPDATA%%\\CorenessFlow)"},
                    },
                },
                "about": {
                    "type": "array",
                    "description": "Пункты для отображения в «О приложении»: [{label, value?, href?}].",
                    "items": {"type": "object", "properties": {"label": {}, "value": {}, "href": {}}},
                },
            },
        },
    },
}


_BACKEND_EXE_NAMES = ("coreness-backend.exe", "coreness-backend")


def is_valid_project_root(path: Path) -> bool:
    """Проверяет, что путь является корнем проекта: должны существовать папки config и plugins."""
    if not path or not path.exists() or not path.is_dir():
        return False
    return (path / "config").is_dir() and (path / "plugins").is_dir()


@cache
def find_project_root() -> Path:
    """Определяет корень проекта: ищет папку с config и plugins, поднимаясь вверх по дереву."""
    exe_path = Path(sys.executable).resolve()
    if exe_path.name in _BACKEND_EXE_NAMES:
        # Запуск из собранного backend: exe в resources/backend/ → корень = resources (config/, plugins/)
        candidate = exe_path.parent.parent
        if is_valid_project_root(candidate):
            return candidate
    start = Path(__file__).resolve().parent.parent
    current = start
    while current != current.parent:
        if is_valid_project_root(current):
            return current
        current = current.parent
    return start


def _deep_merge(base: dict, override: dict) -> dict:
    """Глубокий мерж: override перекрывает base."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _defaults_from_schema(schema: dict) -> dict:
    """Извлекает значения default из схемы настроек (формат plugin_id.json)."""
    out = {}
    for key, spec in schema.items():
        if isinstance(spec, dict) and "default" in spec:
            out[key] = spec["default"]
        else:
            out[key] = spec
    return out


@cache
def get_user_data_dir() -> Path:
    """Каталог данных приложения (создаётся при первом обращении). Windows: %APPDATA%\\CorenessFlow. Результат кэшируется."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    path = Path(base) / USER_DATA_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path

def load_app_config(project_root: Path | None = None) -> dict:
    """Загружает и мержит app.json + user_settings['app'] без создания Settings (для bootstrap: api_bus max_workers и т.д.)."""
    path = get_user_data_dir() / USER_SETTINGS_FILENAME
    user = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            user = data.get("app") or {}
        except Exception:
            pass
    if not isinstance(user, dict):
        user = {}
    root = project_root if project_root is not None else find_project_root()
    app_json_path = root / "config" / APP_CONFIG_FILENAME
    defaults = {}
    if app_json_path.exists():
        try:
            with open(app_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            schema = data.get("settings") or {}
            defaults = _defaults_from_schema(schema)
        except Exception:
            pass
    return _deep_merge(defaults, user)


class Settings:
    """Загрузка и сохранение настроек (app + плагины), мерж defaults и user overrides. Регистрирует действие get_app_metadata в api_bus."""

    def __init__(self, project_root: Path, api_bus: Any, user_data_dir: Path | None = None) -> None:
        self._project_root = project_root
        self._api_bus = api_bus
        self._user_data_dir = user_data_dir if user_data_dir is not None else get_user_data_dir()
        self._user_settings: dict | None = None
        self._app_config: dict | None = None
        self._register_actions()

    @property
    def project_root(self) -> Path:
        """Корневая директория проекта."""
        return self._project_root

    def _register_actions(self) -> None:
        """Регистрирует get_app_metadata в api_bus."""
        name = GET_APP_METADATA_ACTION["name"]
        config = {k: v for k, v in GET_APP_METADATA_ACTION.items() if k != "name"}
        self._api_bus.register(name, self._action_get_app_metadata)
        self._api_bus.set_action_config(name, config)

    def _get_app_paths(self) -> dict:
        """Пути приложения для плагинов (project_root, data_path). data_path = каталог пользовательских данных (логи, БД, загрузки)."""
        return {
            "project_root": str(self._project_root),
            "data_path": str(self._user_data_dir),
        }

    def _get_about_list(self) -> list:
        """Список пунктов для блока «О приложении» из app-конфига (about)."""
        app_cfg = self.get_app_config()
        about = app_cfg.get("about")
        if isinstance(about, list):
            return [item for item in about if isinstance(item, dict) and item.get("label")]
        return []

    def _get_app_metadata_response(self) -> dict:
        """Полный ответ get_app_metadata для фронта: paths (внутренние пути) и about (для UI)."""
        return {
            "paths": self._get_app_paths(),
            "about": self._get_about_list(),
        }

    def _action_get_app_metadata(self, payload: dict) -> dict:
        """Обработчик действия get_app_metadata."""
        return {"result": "success", "response_data": self._get_app_metadata_response()}

    def _user_settings_path(self) -> Path:
        return self._user_data_dir / USER_SETTINGS_FILENAME

    def _app_json_path(self) -> Path:
        return self._project_root / "config" / APP_CONFIG_FILENAME

    def _load_user_settings_raw(self) -> dict:
        """Читает user_settings.json; при отсутствии или ошибке — пустой dict."""
        path = self._user_settings_path()
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def load_user_settings(self) -> dict:
        """Возвращает кэш user_settings или загружает с диска. При первом запуске создаёт user_settings.json, если файла нет."""
        if self._user_settings is not None:
            return self._user_settings
        path = self._user_settings_path()
        self._user_settings = self._load_user_settings_raw()
        if not path.exists():
            self.save_user_settings(self._user_settings)
        return self._user_settings

    def save_user_settings(self, data: dict) -> None:
        """Атомарная запись user_settings.json (временный файл + rename)."""
        path = self._user_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = None
        try:
            fd = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
                suffix=".tmp",
            )
            tmp_path = Path(fd.name)
            json.dump(data, fd, ensure_ascii=False, indent=2)
            fd.close()
            tmp_path.replace(path)
        except Exception:
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise
        self._user_settings = data

    def _load_app_defaults(self) -> dict:
        """Загружает app.json: значения по умолчанию из settings и массив about для «О приложении»."""
        path = self._app_json_path()
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {}
        schema = data.get("settings") or {}
        defaults = _defaults_from_schema(schema)
        about = data.get("about")
        if isinstance(about, list):
            defaults["about"] = about
        return defaults

    def get_app_config(self) -> dict:
        """Мерж дефолтов app.json и user_settings['app']."""
        if self._app_config is not None:
            return self._app_config
        defaults = self._load_app_defaults()
        user = self.load_user_settings().get("app") or {}
        if not isinstance(user, dict):
            user = {}
        self._app_config = _deep_merge(defaults, user)
        return self._app_config

    def load_plugin_config(self, plugin_path: str) -> dict:
        """Загружает config.json из каталога плагина."""
        if not plugin_path:
            return {}
        path = Path(plugin_path)
        if not path.is_absolute():
            path = self._project_root / path
        config_file = path / "config.json"
        if not config_file.exists():
            return {}
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return raw if isinstance(raw, dict) else {}
        except Exception:
            return {}

    def merge_config(self, plugin_config: dict, plugin_name: str) -> dict:
        """Мерж: дефолты плагина + user_settings[plugin_name]. Конфиг — структура metadata, settings, actions, contributes, app_metadata (без раскрытия во флэт)."""
        user_settings = self.load_user_settings()
        plugin_overrides = user_settings.get(plugin_name) or {}
        if not isinstance(plugin_overrides, dict):
            plugin_overrides = {}
        settings_base = plugin_config.get("settings", {})
        settings_defaults = _defaults_from_schema(settings_base) if isinstance(settings_base, dict) else {}
        merged_settings = _deep_merge(settings_defaults, plugin_overrides)
        return {
            "metadata": plugin_config.get("metadata") or {},
            "settings": merged_settings or {},
            "actions": plugin_config.get("actions") or {},
            "contributes": plugin_config.get("contributes") or {},
            "app_metadata": self._get_app_paths(),
        }
