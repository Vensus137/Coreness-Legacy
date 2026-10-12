"""Инициализация ядра и плагинов без Qt — для запуска backend-процесса (Electron)."""

import sys
from pathlib import Path

from app.runtime.api_bus import ApiBus
from app.runtime.container import Container
from app.runtime.context import AppContext
from app.runtime.logger import create_logger
from app.settings import find_project_root, get_user_data_dir, load_app_config, Settings


def init_core_without_ui(project_root: Path | None = None) -> tuple[AppContext, Container, dict]:
    """
    Инициализация ядра и плагинов без Qt и splash.
    Возвращает (context, container, app_config). project_root задаётся при сборке (Electron).
    """
    root = project_root if project_root is not None else find_project_root()
    
    # Добавляем корень проекта в sys.path для работы импортов плагинов (особенно важно в frozen exe)
    root_str = str(root.resolve())
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    
    app_config = load_app_config(project_root=root)
    logger = create_logger(data_dir=get_user_data_dir())
    api_bus_cfg = app_config.get("api_bus") or {}
    max_workers = int(api_bus_cfg.get("max_workers", 5))
    api_bus = ApiBus(max_workers=max_workers)
    settings = Settings(project_root=root, api_bus=api_bus)
    context = AppContext(api_bus=api_bus, logger=logger)
    container = Container(settings=settings, context=context)

    container.load_all()
    container.run_blocking_phase()

    return context, container, app_config
