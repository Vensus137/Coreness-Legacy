"""Тесты модуля text_chunker."""

import pytest

from plugins.core.vector_store.modules.text_chunker import TextChunker


class TestTextChunkerCleanText:
    """Тесты очистки текста."""

    def test_clean_empty(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        assert chunker.clean_text("") == ""

    def test_clean_strips_whitespace(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        assert chunker.clean_text("  hello  ") == "hello"

    def test_clean_normalizes_line_breaks(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        text = "a\r\nb\rc\n"
        assert "\r" not in chunker.clean_text(text)
        assert chunker.clean_text(text) == "a\nb\nc"

    def test_clean_removes_double_spaces(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        assert chunker.clean_text("a  b   c") == "a b c"

    def test_clean_removes_html_tags(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        assert chunker.clean_text("<p>hello</p>") == "hello"


class TestTextChunkerCountTokens:
    """Тесты подсчёта токенов."""

    def test_count_empty(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        assert chunker.count_tokens("") == 0

    def test_count_non_empty(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        # mock: len(text)//4 токенов
        assert chunker.count_tokens("a" * 8) == 2
        assert chunker.count_tokens("a" * 100) == 25


class TestTextChunkerDetectContentType:
    """Тесты определения типа контента."""

    def test_detect_text(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        assert chunker.detect_content_type("Обычный текст без разметки.") == "text"

    def test_detect_table(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        assert chunker.detect_content_type(text) == "table"

    def test_detect_code(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        assert chunker.detect_content_type("```python\nx=1\n```") == "code"

    def test_detect_list(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        text = "- Пункт один\n- Пункт два\n- Пункт три\nЧетвертый пункт списка."
        assert chunker.detect_content_type(text) == "list"


class TestTextChunkerSplitIntoChunks:
    """Тесты разбиения на чанки."""

    def test_split_empty_returns_empty(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        assert chunker.split_into_chunks("", 512, 100) == []

    def test_split_short_text_returns_one_chunk(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        text = "Короткий текст."
        chunks = chunker.split_into_chunks(
            text, chunk_size=512, chunk_overlap=100, min_chunk_size=0
        )
        assert len(chunks) == 1
        assert chunks[0].strip() == text

    def test_split_long_text_returns_multiple_chunks(self, mock_logger, mock_tokenizer):
        chunker = TextChunker(tokenizer=mock_tokenizer, logger=mock_logger)
        # Текст ~300 символов -> ~75 токенов по моку; chunk_size=20 -> несколько чанков
        text = "Абзац один. " * 25
        chunks = chunker.split_into_chunks(text, chunk_size=20, chunk_overlap=5, min_chunk_size=5)
        assert len(chunks) >= 2
        assert all(isinstance(c, str) and len(c) > 0 for c in chunks)
