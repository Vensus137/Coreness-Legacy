"""Фасад логгера: один файл с лимитом 2 MB (при переполнении оставляем последние 500 строк), именованные логгеры для плагинов."""

import logging
from pathlib import Path
from typing import Any

_LOG_NAME = "app"
_LOG_FILENAME = "app.log"
# Один файл: при достижении размера оставляем последние N строк, остальное отбрасываем
_LOG_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_LOG_KEEP_LINES = 200             # при переполнении оставляем последние столько строк


class _TruncatingFileHandler(logging.FileHandler):
    """Файловый handler: при превышении max_bytes оставляем последние keep_lines строк, остальное отбрасываем."""

    def __init__(
        self,
        filename: str | Path,
        max_bytes: int,
        keep_lines: int = _LOG_KEEP_LINES,
        encoding: str | None = None,
    ) -> None:
        super().__init__(filename, mode="a", encoding=encoding or "utf-8")
        self._max_bytes = max_bytes
        self._keep_lines = max(1, keep_lines)

    def emit(self, record: logging.LogRecord) -> None:
        if self.stream is not None and self.stream.tell() >= self._max_bytes:
            self.stream.close()
            self.stream = None
            path = self.baseFilename
            enc = self.encoding
            try:
                with open(path, "r", encoding=enc) as f:
                    lines = f.readlines()
                tail = lines[-self._keep_lines:] if len(lines) > self._keep_lines else lines
                with open(path, "w", encoding=enc) as f:
                    f.writelines(tail)
            except OSError:
                pass
            self.stream = self._open()
        super().emit(record)


def _setup_root(data_dir: Path) -> logging.Logger:
    """Настраивает корневой логгер приложения: один файловый handler в каталоге данных приложения (data_dir)."""
    file_path = (data_dir / _LOG_FILENAME).resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger(_LOG_NAME)
    root.setLevel(logging.DEBUG)
    root.propagate = False

    if not root.handlers:
        handler = _TruncatingFileHandler(
            file_path,
            max_bytes=_LOG_MAX_BYTES,
            keep_lines=_LOG_KEEP_LINES,
            encoding="utf-8",
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        root.addHandler(handler)

    return root


class _AppLoggerFacade:
    """Фасад корневого логгера приложения и get_logger(name) для именованных дочерних логгеров."""

    def __init__(self, root: logging.Logger) -> None:
        self._root = root

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._root.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._root.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._root.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._root.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._root.exception(msg, *args, **kwargs)

    def get_logger(self, name: str) -> logging.Logger:
        """Возвращает именованный дочерний логгер (например имя плагина); пишет в тот же файл."""
        return logging.getLogger(f"{_LOG_NAME}.{name}")


def create_logger(data_dir: Path) -> _AppLoggerFacade:
    """Создаёт логгер приложения: один файл в каталоге данных приложения (data_dir), лимит 2 MB (при переполнении — последние 200 строк)."""
    root = _setup_root(data_dir)
    return _AppLoggerFacade(root)
