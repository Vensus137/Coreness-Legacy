"""Плагин загрузки файлов по URL и извлечения текста (PDF, DOCX, TXT, MD, HTML, CSV)."""

import asyncio
from pathlib import Path
from typing import Any, Dict

from .modules.cleanup_manager import CleanupManager
from .modules.downloader import Downloader
from .modules.file_detector import FileDetector
from .modules.text_extractor import TextExtractor


class DownloadService:
    """
    Загрузка файлов по URL и извлечение текста. Поддержка PDF, DOCX, TXT, MD, HTML, CSV.
    Автоопределение типа по magic bytes / Content-Type / расширению, управление очисткой.
    """

    def __init__(self, config: dict, context) -> None:
        self.config = config
        self.logger = context.logger
        app_meta = config["app_metadata"]
        data_path = Path(app_meta["data_path"])
        settings = config.get("settings") or {}

        downloads_path_raw = settings.get("downloads_path", "downloads")
        self.downloads_path = (data_path / downloads_path_raw) if not Path(downloads_path_raw).is_absolute() else Path(downloads_path_raw)
        self.downloads_path.mkdir(parents=True, exist_ok=True)

        self.max_file_size_mb = settings.get("max_file_size_mb", 10)
        self.download_timeout_seconds = settings.get("download_timeout_seconds", 60)
        self.auto_cleanup_enabled = settings.get("auto_cleanup_enabled", True)
        self.supported_formats = settings.get(
            "supported_formats", ["pdf", "docx", "txt", "md", "html", "csv"]
        )

        self.downloader = Downloader(
            logger=self.logger,
            downloads_path=self.downloads_path,
        )
        self.file_detector = FileDetector(
            logger=self.logger,
            supported_formats=self.supported_formats,
        )
        self.text_extractor = TextExtractor(logger=self.logger)

        self.cleanup_manager = CleanupManager(
            logger=self.logger,
            downloads_path=self.downloads_path,
            max_age_seconds=settings.get("file_max_age_seconds", 86400),
            enabled=settings.get("background_cleanup_enabled", True),
            cleanup_interval_seconds=settings.get("cleanup_interval_seconds", 300),
        )

        self._cleanup_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._plugin_id = (config.get("metadata") or {}).get("name")
        context.api_bus.subscribe(f"plugin:settings_changed:{self._plugin_id}", self._on_settings_changed)
        self.logger.info("Download Service инициализирован. Путь загрузок: %s", self.downloads_path)

    async def run(self) -> None:
        """Сохраняет loop и запускает фоновую очистку только если она включена в настройках."""
        self._loop = asyncio.get_running_loop()
        if self.cleanup_manager.enabled:
            self._start_cleanup_task()
            self.logger.info("Фоновая очистка download_service запущена")
        else:
            self.logger.info("Фоновая очистка download_service выключена (запуск при включении в настройках)")

    def _start_cleanup_task(self) -> None:
        """Запускает задачу фоновой очистки, если включена и задача ещё не крутится. Вызывать с loop (run или call_soon_threadsafe)."""
        if not self.cleanup_manager.enabled:
            return
        if self._cleanup_task is not None and not self._cleanup_task.done():
            return
        self._cleanup_task = asyncio.create_task(self.cleanup_manager.run())
        self.logger.info("Фоновая очистка download_service запущена")

    def _stop_cleanup_task(self) -> None:
        """Останавливает задачу фоновой очистки. Безопасно вызывать из любого потока (cancel thread-safe)."""
        if self._cleanup_task is None:
            return
        if not self._cleanup_task.done():
            self._cleanup_task.cancel()
        self._cleanup_task = None
        self.logger.info("Фоновая очистка download_service остановлена")

    def _on_settings_changed(self, data: dict) -> None:
        """Обновляет атрибуты при изменении настроек из UI (событие plugin:settings_changed:{plugin_id})."""
        settings = data.get("settings") or {}
        if "max_file_size_mb" in settings:
            self.max_file_size_mb = settings["max_file_size_mb"]
        if "download_timeout_seconds" in settings:
            self.download_timeout_seconds = settings["download_timeout_seconds"]
        if "auto_cleanup_enabled" in settings:
            self.auto_cleanup_enabled = settings["auto_cleanup_enabled"]
        if "supported_formats" in settings:
            self.supported_formats = settings["supported_formats"]
        if "file_max_age_seconds" in settings:
            self.cleanup_manager.max_age_seconds = settings["file_max_age_seconds"]
        if "background_cleanup_enabled" in settings:
            new_enabled = settings["background_cleanup_enabled"]
            self.cleanup_manager.enabled = new_enabled
            if new_enabled:
                if self._loop is not None:
                    self._loop.call_soon_threadsafe(self._start_cleanup_task)
            else:
                self._stop_cleanup_task()
        if "cleanup_interval_seconds" in settings:
            self.cleanup_manager.cleanup_interval_seconds = settings["cleanup_interval_seconds"]
        self.logger.info("Настройки download_service обновлены из UI")

    def shutdown(self) -> None:
        """Остановка фоновой очистки при завершении приложения."""
        self._stop_cleanup_task()
        self.cleanup_manager.stop()

    async def download_and_extract(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Загрузить файл по URL и извлечь текст. Параметры в payload."""
        file_path = None
        try:
            url = payload.get("url")
            file_type_hint = payload.get("file_type")
            keep_file = payload.get("keep_file", False)
            max_size_mb = payload.get("max_file_size_mb", self.max_file_size_mb)
            timeout_seconds = payload.get("download_timeout_seconds", self.download_timeout_seconds)

            if not url:
                return {
                    "result": "error",
                    "error": {"code": "VALIDATION_ERROR", "message": "Параметр 'url' обязателен"},
                }

            if file_type_hint and file_type_hint not in self.supported_formats:
                return {
                    "result": "error",
                    "error": {
                        "code": "UNSUPPORTED_FORMAT",
                        "message": f"Тип '{file_type_hint}' не поддерживается. Доступны: {', '.join(self.supported_formats)}",
                    },
                }

            download_result = await self.downloader.download_file(
                url=url,
                max_size_mb=max_size_mb,
                timeout_seconds=timeout_seconds,
            )

            if download_result.get("result") == "error":
                return download_result

            file_path = download_result["file_path"]
            file_size = download_result["file_size"]
            content_type = download_result.get("content_type")
            download_timestamp = download_result["download_timestamp"]

            detected_type = await self.file_detector.detect_file_type(
                file_path=file_path,
                url=url,
                content_type=content_type,
                file_type_hint=file_type_hint,
            )

            if detected_type.get("result") == "error":
                if self.auto_cleanup_enabled and file_path:
                    self.cleanup_manager.cleanup_file(file_path)
                return detected_type

            file_type = detected_type["file_type"]

            extraction_result = await self.text_extractor.extract_text(
                file_path=file_path,
                file_type=file_type,
            )

            if extraction_result.get("result") == "error":
                if self.auto_cleanup_enabled and file_path:
                    self.cleanup_manager.cleanup_file(file_path)
                return extraction_result

            extracted_text = extraction_result["text"]
            extraction_metadata = extraction_result.get("metadata", {})

            response_data = {
                "file_text": extracted_text,
                "file_path": str(file_path) if keep_file else None,
                "file_metadata": {
                    "source_url": url,
                    "file_type": file_type,
                    "file_size_bytes": file_size,
                    "download_timestamp": download_timestamp,
                    **extraction_metadata,
                },
            }

            if self.auto_cleanup_enabled and not keep_file:
                self.cleanup_manager.cleanup_file(file_path)

            return {"result": "success", "response_data": response_data}

        except asyncio.TimeoutError:
            if self.auto_cleanup_enabled and file_path:
                self.cleanup_manager.cleanup_file(file_path)
            self.logger.error("Таймаут загрузки: %s", payload.get("url"))
            return {
                "result": "error",
                "error": {"code": "TIMEOUT", "message": "Превышен таймаут загрузки"},
            }
        except Exception as e:
            if self.auto_cleanup_enabled and file_path:
                self.cleanup_manager.cleanup_file(file_path)
            self.logger.exception("Ошибка download_and_extract: %s", e)
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            }
