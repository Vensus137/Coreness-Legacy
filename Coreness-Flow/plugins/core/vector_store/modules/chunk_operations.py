"""
Операции индексации и форматирования результатов поиска.
"""

import hashlib
from typing import Any, Dict, List, Tuple

from .embedding_manager import EmbeddingManager
from .qdrant_manager import QdrantManager
from .text_chunker import TextChunker


def build_document_id(text: str, document_id: str | None) -> str:
    """Генерация или возврат document_id."""
    if document_id:
        return document_id
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def index_document(
    text: str, document_id: str, metadata: Dict[str, Any],
    chunk_size: int, chunk_overlap: int, min_chunk_size: int,
    chunker: TextChunker, embedding_manager: EmbeddingManager, qdrant_manager: QdrantManager,
    logger: Any, max_chunks_per_batch: int = 8, collection_name: str = None,
) -> Tuple[int, int]:
    """Разбиение текста на чанки, генерация эмбеддингов и сохранение в Qdrant. Возвращает (added_count, total_tokens)."""
    # Очистка и разбиение текста
    cleaned_text = chunker.clean_text(text)
    if not cleaned_text:
        logger.warning(f"Документ {document_id}: текст пустой после очистки")
        return 0, 0

    chunks = chunker.split_into_chunks(
        text=cleaned_text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=min_chunk_size,
    )

    if not chunks:
        logger.warning(f"Документ {document_id}: не создано ни одного чанка")
        return 0, 0

    total_chunks = len(chunks)
    logger.info(f"Документ {document_id}: создано {total_chunks} чанков для индексации")

    total_tokens = 0
    added_count = 0

    # Обрабатываем чанки батчами для оптимизации памяти
    for batch_start in range(0, total_chunks, max_chunks_per_batch):
        batch_end = min(batch_start + max_chunks_per_batch, total_chunks)
        chunk_batch = chunks[batch_start:batch_end]

        # Генерация эмбеддингов для батча
        dense_vecs, sparse_dicts = embedding_manager.encode(chunk_batch)

        if len(dense_vecs) != len(chunk_batch) or len(sparse_dicts) != len(chunk_batch):
            logger.error(
                f"Документ {document_id}: несоответствие количества эмбеддингов и чанков "
                f"({len(dense_vecs)}/{len(chunk_batch)})"
            )
            continue

        # Добавление чанков в Qdrant
        for i, chunk_text in enumerate(chunk_batch):
            chunk_index = batch_start + i
            chunk_tokens = chunker.count_tokens(chunk_text)
            total_tokens += chunk_tokens

            # Конвертация sparse в формат Qdrant
            sparse_indices, sparse_values = embedding_manager.convert_sparse_to_indices(
                sparse_dicts[i]
            )

            # Подготовка метаданных чанка
            chunk_metadata = {
                **metadata,
                "document_id": document_id,
                "chunk_index": chunk_index,
                "chunk_tokens": chunk_tokens,
            }

            chunk_id = f"{document_id}_{chunk_index}"

            success = qdrant_manager.add_document(
                doc_id=chunk_id,
                text=chunk_text,
                dense_vec=dense_vecs[i],
                sparse_indices=sparse_indices,
                sparse_values=sparse_values,
                metadata=chunk_metadata,
                collection_name=collection_name,
            )

            if success:
                added_count += 1
            else:
                logger.warning(f"Документ {document_id}: не удалось добавить чанк {chunk_index}")

        logger.debug(
            f"Документ {document_id}: обработан батч {batch_start+1}-{batch_end} "
            f"({added_count}/{batch_end} чанков добавлено)"
        )

    logger.info(
        f"Документ {document_id}: индексация завершена - "
        f"{added_count}/{total_chunks} чанков, {total_tokens} токенов"
    )

    return added_count, total_tokens


def format_search_results(results: List[Dict[str, Any]], score_threshold: float) -> List[Dict[str, Any]]:
    """Фильтрация по score_threshold и форматирование ответа поиска."""
    filtered = [r for r in results if r["score"] >= score_threshold]

    search_chunks = []
    for r in filtered:
        chunk_metadata = r.get("metadata", {})
        chunk: Dict[str, Any] = {
            "chunk_id": r["doc_id"],
            "document_id": chunk_metadata.get("document_id", ""),
            "chunk_index": chunk_metadata.get("chunk_index", 0),
            "text": r["text"],
            "score": r["score"],
            "metadata": {
                k: v
                for k, v in chunk_metadata.items()
                if k not in ["document_id", "chunk_index", "chunk_tokens"]
            },
        }
        if "collection" in r:
            chunk["collection"] = r["collection"]
        search_chunks.append(chunk)

    return search_chunks
