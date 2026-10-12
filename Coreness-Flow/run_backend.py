"""Точка входа backend-процесса для Electron: ядро + плагины + WebSocket-сервер (без Qt)."""

import argparse
import sys
from pathlib import Path

from app.backend_runner import init_core_without_ui
from app.ws_server import run_ws_server


def main() -> int:
    """Инициализация ядра, загрузка плагинов, запуск WebSocket-сервера."""
    parser = argparse.ArgumentParser(description="Coreness Flow backend (WebSocket)")
    parser.add_argument("--port", type=int, default=29773, help="Порт WebSocket-сервера")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Хост")
    parser.add_argument("--project-root", type=str, default=None, help="Корень проекта (для сборки Electron)")
    args = parser.parse_args()
    project_root = Path(args.project_root) if args.project_root else None
    try:
        context, container, app_config = init_core_without_ui(project_root=project_root)
        context.logger.info("Backend инициализирован, запуск WebSocket-сервера")
        run_ws_server(context, container, app_config, host=args.host, port=args.port)
        return 0
    except Exception as e:
        print(f"Ошибка запуска backend: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
