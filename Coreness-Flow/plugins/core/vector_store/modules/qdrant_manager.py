"""Менеджер Qdrant: работа с векторной БД в embedded режиме."""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class QdrantManager:
    """
    Управление Qdrant в embedded режиме (без отдельного сервера).
    Поддержка гибридного поиска (dense + sparse) с RRF fusion.
    """

    def __init__(self, db_path: str, collection_name: str, logger: Any) -> None:
        """Инициализация менеджера Qdrant (lazy инициализация клиента)."""
        self._db_path = os.path.expanduser(db_path)
        self._collection_name = collection_name
        self._logger = logger
        self._client = None
        self._initialized = False

    def _resolve_collection(self, collection_name: Optional[str] = None) -> str:
        """Возвращает имя коллекции: переданное или дефолтное из настроек."""
        return collection_name or self._collection_name

    def _init_client(self) -> None:
        """Инициализация клиента Qdrant (lazy loading при первом использовании)."""
        if self._initialized:
            return

        try:
            from qdrant_client import QdrantClient

            # Создание директории если не существует
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

            self._logger.info(f"Инициализация Qdrant: {self._db_path}")
            self._client = QdrantClient(path=self._db_path)
            self._initialized = True
            self._logger.info("Qdrant клиент успешно инициализирован")

        except ImportError as e:
            self._logger.error(f"Не удалось импортировать qdrant-client: {e}")
            raise RuntimeError(
                "qdrant-client не установлен. Выполните: pip install qdrant-client"
            ) from e
        except Exception as e:
            self._logger.error(f"Ошибка инициализации Qdrant: {e}")
            raise RuntimeError(f"Не удалось инициализировать Qdrant: {e}") from e

    def ensure_collection(self, collection_name: Optional[str] = None) -> None:
        """Проверка и создание коллекции если не существует (dense + sparse)."""
        if not self._initialized:
            self._init_client()

        col = self._resolve_collection(collection_name)

        try:
            from qdrant_client import models

            collections = self._client.get_collections().collections
            collection_exists = any(c.name == col for c in collections)

            if collection_exists:
                return

            self._logger.info(f"Создание коллекции '{col}'")
            self._client.create_collection(
                collection_name=col,
                vectors_config={
                    "dense": models.VectorParams(size=1024, distance=models.Distance.COSINE)
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )
            self._logger.info(f"Коллекция '{col}' успешно создана")

        except Exception as e:
            self._logger.error(f"Ошибка создания коллекции: {e}")
            raise RuntimeError(f"Не удалось создать коллекцию: {e}") from e

    def _string_to_uuid(self, string_id: str) -> str:
        """Конвертация строкового ID в детерминированный UUID v5."""
        namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace
        return str(uuid.uuid5(namespace, string_id))

    def add_document(self, doc_id: str, text: str, dense_vec: np.ndarray,
                     sparse_indices: List[int], sparse_values: List[float], metadata: Dict[str, Any],
                     collection_name: Optional[str] = None) -> bool:
        """Добавление документа в коллекцию. True при успехе, False при ошибке."""
        if not self._initialized:
            self._init_client()

        col = self._resolve_collection(collection_name)

        try:
            from qdrant_client import models

            point_uuid = self._string_to_uuid(doc_id)

            indexed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            payload = {"text": text, "original_id": doc_id, **metadata, "indexed_at": indexed_at}

            sparse_vector = models.SparseVector(indices=sparse_indices, values=sparse_values)

            self._client.upsert(
                collection_name=col,
                points=[
                    models.PointStruct(
                        id=point_uuid,
                        vector={"dense": dense_vec.tolist(), "sparse": sparse_vector},
                        payload=payload,
                    )
                ],
            )

            self._logger.debug(f"Документ {doc_id} успешно добавлен в Qdrant (коллекция: {col})")
            return True

        except Exception as e:
            self._logger.error(f"Ошибка добавления документа {doc_id}: {e}")
            return False

    def search(self, query_dense: np.ndarray, query_sparse_indices: List[int], query_sparse_values: List[float],
               top_k: int = 10, use_hybrid: bool = True, filters: Optional[Dict[str, Any]] = None,
               collection_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Поиск документов по запросу (гибридный dense + sparse + RRF)."""
        if not self._initialized:
            self._init_client()

        col = self._resolve_collection(collection_name)

        try:
            from qdrant_client import models

            query_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        models.FieldCondition(key=key, match=models.MatchValue(value=value))
                    )
                if conditions:
                    query_filter = models.Filter(must=conditions)

            if use_hybrid:
                sparse_vector = models.SparseVector(
                    indices=query_sparse_indices, values=query_sparse_values
                )

                results = self._client.query_points(
                    collection_name=col,
                    prefetch=[
                        models.Prefetch(query=query_dense.tolist(), using="dense", limit=top_k * 10),
                        models.Prefetch(query=sparse_vector, using="sparse", limit=top_k * 10),
                    ],
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=top_k,
                    query_filter=query_filter,
                )
            else:
                results = self._client.query_points(
                    collection_name=col,
                    query=query_dense.tolist(),
                    using="dense",
                    limit=top_k,
                    query_filter=query_filter,
                )

            formatted_results = []
            for hit in results.points:
                original_id = hit.payload.get("original_id", str(hit.id))
                formatted_results.append(
                    {
                        "doc_id": original_id,
                        "text": hit.payload.get("text", ""),
                        "score": hit.score,
                        "metadata": {
                            k: v for k, v in hit.payload.items() if k not in ["text", "original_id"]
                        },
                    }
                )

            self._logger.debug(f"Поиск завершен: найдено {len(formatted_results)} документов (коллекция: {col})")
            return formatted_results

        except Exception as e:
            self._logger.error(f"Ошибка поиска: {e}")
            return []

    def delete_documents(self, doc_ids: List[str], collection_name: Optional[str] = None) -> bool:
        """Удаление документов по списку ID. True при успехе, False при ошибке."""
        if not self._initialized:
            self._init_client()

        if not doc_ids:
            return True

        col = self._resolve_collection(collection_name)

        try:
            from qdrant_client import models

            point_uuids = [self._string_to_uuid(doc_id) for doc_id in doc_ids]

            self._client.delete(
                collection_name=col,
                points_selector=models.PointIdsList(points=point_uuids),
            )

            self._logger.debug(f"Удалено {len(doc_ids)} документов (коллекция: {col})")
            return True

        except Exception as e:
            self._logger.error(f"Ошибка удаления документов: {e}")
            return False

    def delete_by_filter(self, filters: Dict[str, Any], collection_name: Optional[str] = None) -> bool:
        """Удаление документов по фильтрам метаданных. True при успехе, False при ошибке."""
        if not self._initialized:
            self._init_client()

        if not filters:
            return True

        col = self._resolve_collection(collection_name)

        try:
            from qdrant_client import models

            conditions = []
            for key, value in filters.items():
                conditions.append(
                    models.FieldCondition(key=key, match=models.MatchValue(value=value))
                )

            if not conditions:
                return True

            query_filter = models.Filter(must=conditions)

            self._client.delete(
                collection_name=col,
                points_selector=models.FilterSelector(filter=query_filter),
            )

            self._logger.debug(f"Удалены документы по фильтрам: {filters} (коллекция: {col})")
            return True

        except Exception as e:
            self._logger.error(f"Ошибка удаления по фильтрам: {e}")
            return False

    def scroll_points(self, limit: int = 100, offset: Optional[str] = None,
                      collection_name: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Постраничный обход точек коллекции без векторов. Возвращает (список точек, next_offset или None)."""
        if not self._initialized:
            self._init_client()

        col = self._resolve_collection(collection_name)

        try:
            result, next_offset = self._client.scroll(
                collection_name=col,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points = []
            for rec in result:
                points.append({
                    "point_id": str(rec.id),
                    "payload": rec.payload or {},
                })
            next_str = str(next_offset) if next_offset is not None else None
            return points, next_str
        except Exception as e:
            self._logger.error(f"Ошибка scroll_points: {e}")
            return [], None

    def get_collection_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Получение информации о коллекции."""
        if not self._initialized:
            self._init_client()

        col = self._resolve_collection(collection_name)

        try:
            info = self._client.get_collection(collection_name=col)
            return {
                "collection_name": col,
                "points_count": getattr(info, "points_count", None),
                "vectors_count": getattr(info, "vectors_count", None),
                "indexed_vectors_count": getattr(info, "indexed_vectors_count", None),
            }
        except Exception as e:
            self._logger.error(f"Ошибка получения информации о коллекции: {e}")
            return {"collection_name": col, "error": str(e)}

    def get_all_collections(self) -> List[str]:
        """Возвращает список имён всех коллекций в БД."""
        if not self._initialized:
            self._init_client()
        try:
            collections = self._client.get_collections().collections
            return [c.name for c in collections]
        except Exception as e:
            self._logger.error(f"Ошибка получения списка коллекций: {e}")
            return []

    def is_initialized(self) -> bool:
        """Проверка, инициализирован ли клиент."""
        return self._initialized
