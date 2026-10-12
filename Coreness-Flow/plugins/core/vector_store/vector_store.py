"""Плагин VectorStore: локальный RAG с BGE-M3 и Qdrant для индексации и поиска чанков."""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict

from .modules.actions import add_chunks_action, delete_chunks_action, list_chunks_action, search_chunks_action
from .modules.embedding_manager import EmbeddingManager
from .modules.qdrant_manager import QdrantManager
from .modules.text_chunker import TextChunker


class VectorStore:
    """
    Плагин для работы с векторным хранилищем.
    Использует BGE-M3 ONNX INT8 для эмбеддингов (dense + learned sparse),
    Qdrant для хранения, гибридный поиск (RRF).
    Модель эмбеддингов загружается в run_blocking() до показа основного окна.
    """

    def __init__(self, config: dict, context: Any) -> None:
        """Инициализация плагина VectorStore (только конфиг и пути; модель — в run_blocking())."""
        self.config = config
        self.logger = context.logger
        self.api_bus = context.api_bus
        app_meta = config["app_metadata"]
        project_root = Path(app_meta["project_root"])
        data_path = Path(app_meta["data_path"])
        settings = config.get("settings") or {}

        db_path_raw = settings.get("db_path", "qdrant_db")
        db_path = str(data_path / db_path_raw) if not os.path.isabs(db_path_raw) and not db_path_raw.startswith("~") else db_path_raw
        collection_name = settings.get("collection_name", "documents")
        model_path_raw = settings.get("model_path", "models/bge-m3-onnx-int8")
        model_path = str(project_root / model_path_raw) if not os.path.isabs(model_path_raw) and not model_path_raw.startswith("~") else model_path_raw

        self._project_root = project_root
        self._db_path = db_path
        self._collection_name = collection_name
        self._model_path = model_path
        self._batch_size = settings.get("embedding_batch_size", 4)
        self._num_threads = settings.get("onnx_num_threads", 4)

        self._embedding_manager: Any = None
        self._qdrant_manager: Any = None
        self._text_chunker: Any = None

        self._plugin_id = (config.get("metadata") or {}).get("name")
        context.api_bus.subscribe(f"plugin:settings_changed:{self._plugin_id}", self._on_settings_changed)

        self.logger.info("VectorStore плагин инициализирован")

    def _on_settings_changed(self, data: dict) -> None:
        """Обновляет настройки при изменении из UI (событие plugin:settings_changed:{plugin_id})."""
        settings = data.get("settings") or {}
        self.config["settings"] = dict(settings)
        self._collection_name = settings.get("collection_name", self._collection_name)
        model_path_raw = settings.get("model_path", "models/bge-m3-onnx-int8")
        self._model_path = str(self._project_root / model_path_raw) if not os.path.isabs(model_path_raw) and not model_path_raw.startswith("~") else model_path_raw
        self._batch_size = settings.get("embedding_batch_size", self._batch_size)
        self._num_threads = settings.get("onnx_num_threads", self._num_threads)
        if any(k in settings for k in ("model_path", "embedding_batch_size", "onnx_num_threads")):
            self._embedding_manager = None
        if "collection_name" in settings:
            self._qdrant_manager = None
        self.logger.info("Настройки vector_store обновлены из UI")

    def run_blocking(self, progress_callback=None) -> None:
        """Блокирующая загрузка модели до показа основного окна (контракт плагинов). Вызывается контейнером, пока крутится splash."""
        if progress_callback:
            progress_callback(88, "Загрузка модели RAG...")
        try:
            self._get_embedding_manager().ensure_model_loaded()
            self.logger.info("Модель эмбеддингов загружена (run_blocking)")
        except Exception as e:
            self.logger.warning("Не удалось загрузить модель эмбеддингов при инициализации: %s", e)
        if progress_callback:
            progress_callback(90, "Плагины готовы")

    def _get_embedding_manager(self) -> EmbeddingManager:
        """Создание EmbeddingManager при первом обращении (ленивая инициализация)."""
        if self._embedding_manager is None:
            self._embedding_manager = EmbeddingManager(
                model_path=self._model_path,
                logger=self.logger,
                batch_size=self._batch_size,
                num_threads=self._num_threads,
            )
        return self._embedding_manager

    def _get_qdrant_manager(self) -> QdrantManager:
        """Создание QdrantManager при первом обращении (ленивая инициализация)."""
        if self._qdrant_manager is None:
            self._qdrant_manager = QdrantManager(
                db_path=self._db_path,
                collection_name=self._collection_name,
                logger=self.logger,
            )
        return self._qdrant_manager

    def _get_chunker(self) -> TextChunker:
        """Получение экземпляра TextChunker (lazy loading)."""
        if self._text_chunker is None:
            tokenizer = self._get_embedding_manager().get_tokenizer()
            self._text_chunker = TextChunker(tokenizer=tokenizer, logger=self.logger)
        return self._text_chunker

    async def run(self) -> None:
        """Запуск плагина: проверка/создание коллекции Qdrant в пуле потоков."""
        try:
            loop = asyncio.get_event_loop()
            qdrant = self._get_qdrant_manager()
            await loop.run_in_executor(None, qdrant.ensure_collection)
            self.logger.info("VectorStore плагин запущен")
        except Exception as e:
            self.logger.error(f"Ошибка запуска VectorStore: {e}")

    async def add_chunks(self, payload: dict) -> Dict[str, Any]:
        """Добавление текста с разбиением на чанки и генерацией эмбеддингов."""
        return await add_chunks_action(self, payload)

    async def search_chunks(self, payload: dict) -> Dict[str, Any]:
        """Семантический поиск чанков (гибридный dense + sparse + RRF)."""
        return await search_chunks_action(self, payload)

    async def delete_chunks(self, payload: dict) -> Dict[str, Any]:
        """Удаление чанков по document_id или по фильтрам метаданных."""
        return await delete_chunks_action(self, payload)

    async def list_chunks(self, payload: dict) -> Dict[str, Any]:
        """Список чанков в коллекции (постранично) для просмотра и управления."""
        return await list_chunks_action(self, payload)
