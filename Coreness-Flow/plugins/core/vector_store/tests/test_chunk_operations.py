"""Тесты модуля chunk_operations."""

from unittest.mock import MagicMock

from plugins.core.vector_store.modules.chunk_operations import (
    build_document_id,
    format_search_results,
    index_document,
)


class TestBuildDocumentId:
    """Тесты генерации document_id."""

    def test_returns_given_id(self):
        assert build_document_id("any text", "my-doc-123") == "my-doc-123"

    def test_generates_deterministic_hash(self):
        text = "Один и тот же текст"
        id1 = build_document_id(text, None)
        id2 = build_document_id(text, None)
        assert id1 == id2
        assert len(id1) == 16
        assert id1.isalnum()

    def test_different_text_different_id(self):
        id1 = build_document_id("Текст A", None)
        id2 = build_document_id("Текст B", None)
        assert id1 != id2


class TestFormatSearchResults:
    """Тесты форматирования результатов поиска."""

    def test_empty_results(self):
        assert format_search_results([], 0.7) == []

    def test_filters_by_score_threshold(self):
        results = [
            {"doc_id": "a_0", "text": "Hi", "score": 0.9, "metadata": {"document_id": "a", "chunk_index": 0}},
            {"doc_id": "b_0", "text": "Lo", "score": 0.5, "metadata": {"document_id": "b", "chunk_index": 0}},
        ]
        out = format_search_results(results, score_threshold=0.7)
        assert len(out) == 1
        assert out[0]["chunk_id"] == "a_0"
        assert out[0]["score"] == 0.9

    def test_output_structure(self):
        results = [
            {
                "doc_id": "doc_0",
                "text": "Chunk text",
                "score": 0.85,
                "metadata": {
                    "document_id": "doc",
                    "chunk_index": 0,
                    "chunk_tokens": 10,
                    "source": "file.pdf",
                },
            },
        ]
        out = format_search_results(results, score_threshold=0.5)
        assert len(out) == 1
        item = out[0]
        assert item["chunk_id"] == "doc_0"
        assert item["document_id"] == "doc"
        assert item["chunk_index"] == 0
        assert item["text"] == "Chunk text"
        assert item["score"] == 0.85
        assert item["metadata"] == {"source": "file.pdf"}
        assert "chunk_tokens" not in item["metadata"]


class TestIndexDocumentWithMocks:
    """Тесты index_document с моками embedding_manager и qdrant_manager (без модели и БД)."""

    def test_index_empty_text_returns_zero(self, mock_logger, mock_tokenizer):
        from plugins.core.vector_store.modules.text_chunker import TextChunker
        from plugins.core.vector_store.modules.chunk_operations import index_document
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        mock_embed = MagicMock()
        mock_qdrant = MagicMock()
        added, tokens = index_document(
            text="   \n  ", document_id="doc1", metadata={},
            chunk_size=512, chunk_overlap=100, min_chunk_size=50,
            chunker=chunker, embedding_manager=mock_embed, qdrant_manager=mock_qdrant,
            logger=mock_logger, max_chunks_per_batch=8,
        )
        assert added == 0
        assert tokens == 0
        mock_embed.encode.assert_not_called()

    def test_index_document_calls_embed_and_qdrant(self, mock_logger, mock_tokenizer):
        from plugins.core.vector_store.modules.text_chunker import TextChunker
        from plugins.core.vector_store.modules.chunk_operations import index_document
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        mock_embed = MagicMock()
        mock_embed.encode.side_effect = lambda texts: (
            [__import__("numpy").zeros(1024) for _ in texts],
            [{"tok_1": 0.5} for _ in texts],
        )
        mock_embed.convert_sparse_to_indices.return_value = ([1, 2], [0.5, 0.5])
        mock_qdrant = MagicMock()
        mock_qdrant.add_document.return_value = True
        text = "Один абзац. " * 30
        added, total_tokens = index_document(
            text=text, document_id="test-doc", metadata={"source": "test"},
            chunk_size=20, chunk_overlap=5, min_chunk_size=5,
            chunker=chunker, embedding_manager=mock_embed, qdrant_manager=mock_qdrant,
            logger=mock_logger, max_chunks_per_batch=8,
        )
        assert added >= 1
        assert total_tokens >= 1
        assert mock_embed.encode.called
        assert mock_qdrant.add_document.called
