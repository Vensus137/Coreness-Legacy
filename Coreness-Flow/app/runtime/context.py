"""Единый объект зависимостей для плагинов: api_bus, logger. Метаданные приложения — через действие get_app_metadata."""

from dataclasses import dataclass
from typing import Any

from .api_bus import ApiBus


@dataclass(frozen=True)
class AppContext:
    """
    Контейнер ссылок на общие зависимости приложения.
    Передаётся плагинам; каждый плагин использует только нужные поля (api_bus, logger).
    Метаданные приложения (project_root и др.) — через api_bus.call("get_app_metadata", {}).
    """
    api_bus: ApiBus
    logger: Any  # _AppLoggerFacade или logging.Logger
