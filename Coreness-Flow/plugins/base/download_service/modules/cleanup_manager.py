"""Немедленное удаление файлов и фоновая очистка по возрасту."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path


class CleanupManager:
    """Немедленная очистка после извлечения текста и фоновая очистка старых файлов (интервал и возраст в секундах)."""

    def __init__(self, logger, downloads_path: Path, max_age_seconds: int, enabled: bool,
                 cleanup_interval_seconds: int) -> None:
        self.logger = logger
        self.downloads_path = downloads_path
        self.max_age_seconds = max_age_seconds
        self.enabled = enabled
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.is_running = False

    def cleanup_file(self, file_path: Path) -> bool:
        """Удалить один файл. Возвращает True при успехе."""
        try:
            if file_path and file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            self.logger.error("Ошибка удаления файла %s: %s", file_path, e)
            return False

    async def cleanup_old_files(self) -> int:
        """Удалить файлы старше max_age_seconds. Возвращает количество удалённых."""
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.max_age_seconds)
            deleted_count = 0

            if not self.downloads_path.exists():
                return 0

            for file_path in self.downloads_path.iterdir():
                if not file_path.is_file():
                    continue
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff_time:
                    if self.cleanup_file(file_path):
                        deleted_count += 1

            if deleted_count > 0:
                self.logger.info("Фоновая очистка: удалено файлов %d", deleted_count)
            return deleted_count
        except Exception as e:
            self.logger.error("Ошибка фоновой очистки: %s", e)
            return 0

    async def run(self) -> None:
        """Фоновая задача: периодическая очистка старых файлов. Запускается/останавливается снаружи (вкл/выкл в настройках)."""
        self.is_running = True
        self.logger.info(
            "Фоновая очистка: интервал=%d с, макс. возраст файла=%d с",
            self.cleanup_interval_seconds,
            self.max_age_seconds,
        )
        while self.is_running:
            try:
                await self.cleanup_old_files()
                await asyncio.sleep(self.cleanup_interval_seconds)
            except asyncio.CancelledError:
                self.logger.info("Фоновая очистка отменена")
                self.is_running = False
                break
            except Exception as e:
                self.logger.error("Ошибка в задаче очистки: %s", e)
                await asyncio.sleep(60)

    def stop(self) -> None:
        """Остановить фоновую задачу очистки."""
        self.is_running = False
