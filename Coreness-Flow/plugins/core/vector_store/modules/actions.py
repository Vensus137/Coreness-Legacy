"""Обработчики действий плагина VectorStore: add_chunks, search_chunks, delete_chunks."""

import asyncio
from typing import Any, Dict, List, Optional

from .chunk_operations import (
    build_document_id,
    format_search_results,
    index_document,
)


def _normalize_collections(
    raw: Any,
    default: Optional[List[str]] = None,
) -> Optional[List[str]]:
    """Приводит collection к списку строк или None. Строка → [s], массив → список непустых строк, иначе default."""
    if raw is None:
        return default
    if isinstance(raw, str):
        return [raw] if raw.strip() else default
    if isinstance(raw, (list, tuple)):
        out = [c for c in raw if isinstance(c, str) and c.strip()]
        return out if out else default
    return default


async def add_chunks_action(store: Any, payload: dict) -> Dict[str, Any]:
    """Добавление текста с разбиением на чанки и генерацией эмбеддингов."""
    try:
        text = payload.get("text", "")
        if not text:
            return {
                "result": "error",
                "error": {"code": "VALIDATION_ERROR", "message": "Параметр text обязателен"},
            }

        _settings = store.config.get("settings") or {}
        collection = payload.get("collection") or _settings.get("collection_name", "documents")
        document_id = build_document_id(text, payload.get("document_id"))
        metadata = payload.get("metadata", {})
        chunk_size = payload.get("chunk_size", _settings.get("chunk_size", 512))
        chunk_overlap = payload.get("chunk_overlap", _settings.get("chunk_overlap", 100))
        min_chunk_size = payload.get("min_chunk_size", _settings.get("min_chunk_size", 50))
        replace_document = payload.get("replace_document", False)
        text_length = len(text)
        store.logger.info(
            f"Начинаем индексацию документа {document_id}: "
            f"длина текста {text_length} символов, chunk_size={chunk_size}, overlap={chunk_overlap}, коллекция={collection}"
        )
        max_chunks_per_batch = _settings.get("max_chunks_per_batch", 8)

        def _do_index() -> tuple:
            qdrant = store._get_qdrant_manager()
            qdrant.ensure_collection(collection)
            if replace_document:
                success = qdrant.delete_by_filter({"original_id": document_id}, collection_name=collection)
                if success:
                    store.logger.info(
                        f"Удалены старые чанки документа {document_id}, начинаем индексацию"
                    )
                else:
                    store.logger.warning(
                        f"Не удалось удалить старые чанки документа {document_id}, добавляем поверх"
                    )
            chunker = store._get_chunker()
            return index_document(
                text=text,
                document_id=document_id,
                metadata=metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                min_chunk_size=min_chunk_size,
                chunker=chunker,
                embedding_manager=store._get_embedding_manager(),
                qdrant_manager=qdrant,
                logger=store.logger,
                max_chunks_per_batch=max_chunks_per_batch,
                collection_name=collection,
            )

        added_count, total_tokens = await asyncio.to_thread(_do_index)

        if added_count == 0:
            return {
                "result": "error",
                "error": {
                    "code": "CHUNKING_ERROR",
                    "message": "Не удалось создать чанки или сохранить в хранилище",
                },
            }

        store.logger.info(
            f"Документ {document_id}: индексация завершена - "
            f"{added_count} чанков, {total_tokens} токенов"
        )
        store.api_bus.emit("vector_store:chunks_changed", {})
        return {
            "result": "success",
            "response_data": {
                "document_id": document_id,
                "chunks_count": added_count,
                "total_tokens": total_tokens,
            },
        }
    except Exception as e:
        store.logger.exception(f"Ошибка добавления чанков: {e}")
        return {"result": "error", "error": {"code": "ADD_CHUNKS_ERROR", "message": str(e)}}


async def search_chunks_action(store: Any, payload: dict) -> Dict[str, Any]:
    """Семантический поиск чанков (гибридный dense + sparse + RRF)."""
    try:
        query = payload.get("query", "")
        if not query:
            return {
                "result": "error",
                "error": {"code": "VALIDATION_ERROR", "message": "Параметр query обязателен"},
            }

        _settings = store.config.get("settings") or {}
        collections = _normalize_collections(payload.get("collection"), default=None)
        top_k = payload.get("top_k", _settings.get("default_top_k", 10))
        score_threshold = payload.get("score_threshold", _settings.get("score_threshold", 0.7))
        filters = payload.get("filters")
        max_chars = payload.get("max_chars")

        def _do_search():
            emb = store._get_embedding_manager()
            dense_vecs, sparse_dicts = emb.encode([query])
            if not dense_vecs or not sparse_dicts:
                return None
            q_sparse_idx, q_sparse_vals = emb.convert_sparse_to_indices(sparse_dicts[0])
            qdrant = store._get_qdrant_manager()

            cols = collections if collections else qdrant.get_all_collections()
            if not cols:
                return []
            if len(cols) == 1:
                results = qdrant.search(
                    query_dense=dense_vecs[0],
                    query_sparse_indices=q_sparse_idx,
                    query_sparse_values=q_sparse_vals,
                    top_k=top_k,
                    use_hybrid=True,
                    filters=filters,
                    collection_name=cols[0],
                )
                return format_search_results(results, score_threshold)

            all_results = []
            for col in cols:
                col_results = qdrant.search(
                    query_dense=dense_vecs[0],
                    query_sparse_indices=q_sparse_idx,
                    query_sparse_values=q_sparse_vals,
                    top_k=top_k,
                    use_hybrid=True,
                    filters=filters,
                    collection_name=col,
                )
                for r in col_results:
                    r["collection"] = col
                all_results.extend(col_results)
            all_results.sort(key=lambda r: r["score"], reverse=True)
            all_results = all_results[:top_k]
            return format_search_results(all_results, score_threshold)

        search_chunks = await asyncio.to_thread(_do_search)
        if search_chunks is None:
            return {
                "result": "error",
                "error": {
                    "code": "EMBEDDING_ERROR",
                    "message": "Не удалось сгенерировать эмбеддинги для запроса",
                },
            }

        # Применяем max_chars: берём чанки по убыванию релевантности, останавливаемся при превышении лимита
        if max_chars:
            try:
                char_limit = int(max_chars)
                total_chars = 0
                trimmed = []
                for chunk in search_chunks:
                    chunk_len = len(chunk.get("text", ""))
                    if total_chars + chunk_len > char_limit:
                        break
                    total_chars += chunk_len
                    trimmed.append(chunk)
                search_chunks = trimmed
            except (TypeError, ValueError):
                pass

        log_col = (
            collections[0] if collections and len(collections) == 1
            else (", ".join(collections) if collections else "все коллекции")
        )
        store.logger.info(
            f"Поиск завершен: найдено {len(search_chunks)} чанков "
            f"(коллекция: {log_col}, порог: {score_threshold})"
        )
        return {
            "result": "success",
            "response_data": {
                "search_chunks": search_chunks,
                "chunks_count": len(search_chunks),
            },
        }
    except Exception as e:
        store.logger.exception(f"Ошибка поиска: {e}")
        return {"result": "error", "error": {"code": "SEARCH_ERROR", "message": str(e)}}


async def delete_chunks_action(store: Any, payload: dict) -> Dict[str, Any]:
    """Удаление чанков по document_id или по фильтрам метаданных."""
    try:
        document_ids = payload.get("document_ids", [])
        filters = payload.get("filters")

        if not document_ids and not filters:
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Необходимо указать document_ids или filters",
                },
            }

        _settings = store.config.get("settings") or {}
        default_col = _settings.get("collection_name", "documents")
        collections = _normalize_collections(
            payload.get("collection"),
            default=[default_col],
        )

        def _do_delete():
            qdrant = store._get_qdrant_manager()
            total_deleted = 0
            for collection in collections:
                if document_ids:
                    for doc_id in document_ids:
                        success = qdrant.delete_by_filter(
                            {"original_id": doc_id}, collection_name=collection
                        )
                        if success:
                            total_deleted += 1
                            store.logger.info(
                                f"Удалены чанки документа {doc_id} (коллекция: {collection})"
                            )
                        else:
                            store.logger.error(f"Ошибка удаления чанков документа {doc_id}")
                if filters:
                    success = qdrant.delete_by_filter(filters, collection_name=collection)
                    if success:
                        total_deleted += 1
                        store.logger.info(
                            f"Удалены чанки по фильтрам: {filters} (коллекция: {collection})"
                        )
                    else:
                        return total_deleted, "Ошибка удаления по фильтрам"
            return total_deleted, None

        total_deleted, delete_error = await asyncio.to_thread(_do_delete)
        if delete_error:
            return {
                "result": "error",
                "error": {"code": "DELETE_ERROR", "message": delete_error},
            }
        store.api_bus.emit("vector_store:chunks_changed", {})
        return {
            "result": "success",
            "response_data": {"deleted_count": total_deleted},
        }
    except Exception as e:
        store.logger.exception(f"Ошибка удаления чанков: {e}")
        return {
            "result": "error",
            "error": {"code": "DELETE_CHUNKS_ERROR", "message": str(e)},
        }


async def list_chunks_action(store: Any, payload: dict) -> Dict[str, Any]:
    """Список чанков в коллекции (постранично) для просмотра и управления."""
    try:
        limit = payload.get("limit", 100)
        limit = max(1, min(500, int(limit))) if isinstance(limit, (int, float)) else 100
        offset = payload.get("offset")
        if offset is not None and not isinstance(offset, str):
            offset = str(offset)

        collections = _normalize_collections(payload.get("collection"), default=None)

        def _do_list():
            qdrant = store._get_qdrant_manager()
            cols = collections if collections else qdrant.get_all_collections()
            if not cols:
                return {"collections": []}, [], None
            if len(cols) == 1:
                col = cols[0]
                qdrant.ensure_collection(col)
                info = qdrant.get_collection_info(col)
                points, next_offset = qdrant.scroll_points(
                    limit=limit, offset=offset, collection_name=col
                )
                for p in points:
                    p["collection"] = col
                return {"collections": [info]}, points, next_offset
            combined_info = {"collections": []}
            all_points = []
            for col in cols:
                info = qdrant.get_collection_info(col)
                combined_info["collections"].append(info)
                col_points, _ = qdrant.scroll_points(limit=limit, collection_name=col)
                for p in col_points:
                    p["collection"] = col
                all_points.extend(col_points)
            return combined_info, all_points, None

        info, points, next_offset = await asyncio.to_thread(_do_list)
        return {
            "result": "success",
            "response_data": {
                "info": info,
                "points": points,
                "next_offset": next_offset,
            },
        }
    except Exception as e:
        store.logger.exception(f"Ошибка list_chunks: {e}")
        return {"result": "error", "error": {"code": "LIST_CHUNKS_ERROR", "message": str(e)}}
