"""Модуль чанкирования текста с точным подсчетом токенов."""

import re
from typing import List, Tuple


class TextChunker:
    """
    Чанкирование текста с использованием токенизатора BGE-M3.
    Token-aware подход: разбиение по семантическим границам с подсчетом токенов в реальном времени.
    """

    def __init__(self, tokenizer, logger) -> None:
        """Чанкирование с токенизатором BGE-M3 и логгером."""
        self._tokenizer = tokenizer
        self._logger = logger

        # Адаптивные мультипликаторы для разных типов контента
        # Таблицы, код, списки требуют большего размера для сохранения структуры
        self._content_type_multipliers = {
            "table": 1.3,  # Таблицы - увеличенный размер
            "code": 1.3,  # Код - увеличенный размер
            "list": 1.2,  # Списки - слегка увеличенный размер
            "text": 1.0,  # Обычный текст - базовый размер
        }

    def clean_text(self, text: str) -> str:
        """Очистка текста: удаление HTML/markdown, нормализация, удаление невидимых символов."""
        if not text:
            return ""

        # UTF-8 нормализация (исправление битых кодировок)
        try:
            text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="replace")
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass  # Кодировка уже корректная

        # Удаление HTML тегов и markdown code blocks
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"```+", "\n", text)

        # Нормализация переносов строк
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Нормализация множественных переносов (максимум 2 подряд)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Удаление множественных пробелов
        text = re.sub(r" {2,}", " ", text)

        # Удаление невидимых символов
        text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]", " ", text)

        return text.strip()

    def count_tokens(self, text: str) -> int:
        """Точный подсчёт токенов через токенизатор BGE-M3."""
        if not text:
            return 0
        # Без special tokens для chunking
        return len(self._tokenizer.encode(text, add_special_tokens=False))

    def detect_content_type(self, text: str) -> str:
        """Определение типа контента: table, code, list или text."""
        if not text:
            return "text"

        # Проверка на таблицу (высший приоритет)
        if self._is_markdown_table(text):
            return "table"

        # Проверка на код (блоки с отступами или подсветкой)
        lines = text.split("\n")
        indented_lines = sum(1 for line in lines if line.startswith("    ") and line.strip())
        if "```" in text or (lines and indented_lines > len(lines) * 0.3):
            return "code"

        # Проверка на список
        list_lines = sum(
            1
            for line in lines
            if line.strip()
            and (
                line.strip()[0] in ["-", "*", "+"]
                or (len(line.strip()) > 0 and line.strip()[0].isdigit() and "." in line[:5])
            )
        )
        if list_lines > len(lines) * 0.3:
            return "list"

        return "text"

    def split_into_chunks(self, text: str, chunk_size: int, chunk_overlap: int, min_chunk_size: int = 50) -> List[str]:
        """Разбиение текста на чанки с точным подсчетом токенов."""
        if not text:
            return []

        # Если текст меньше chunk_size - возвращаем один чанк
        text_tokens = self.count_tokens(text)
        if text_tokens <= chunk_size:
            cleaned = text.strip()
            if min_chunk_size > 0 and self.count_tokens(cleaned) < min_chunk_size:
                return []
            return [cleaned] if cleaned else []

        # Адаптивный chunk_size по типу контента
        content_type = self.detect_content_type(text)
        multiplier = self._content_type_multipliers.get(content_type, 1.0)
        actual_chunk_size = int(chunk_size * multiplier)

        self._logger.debug(
            f"Чанкирование текста: {text_tokens} токенов, тип='{content_type}', "
            f"размер чанка={actual_chunk_size} токенов (базовый={chunk_size})"
        )

        # Иерархия сепараторов (от более семантических к менее)
        separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ": ", ", ", " "]

        # Рекурсивное разбиение текста на фрагменты
        splits = self._split_text_recursive(text, separators)

        # Слияние фрагментов в чанки с точным подсчетом токенов
        chunks = self._merge_splits_token_aware(splits, actual_chunk_size)

        # Добавление перекрытия между чанками
        if chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap_token_aware(chunks, chunk_overlap, actual_chunk_size)

        # Финальная фильтрация по min_chunk_size
        if min_chunk_size > 0:
            chunks = [c for c in chunks if self.count_tokens(c) >= min_chunk_size]

        self._logger.debug(f"Создано {len(chunks)} чанков")
        return [c.strip() for c in chunks if c.strip()]

    def _is_markdown_table(self, text: str) -> bool:
        """Проверка наличия Markdown таблицы."""
        if "|" not in text or "\n" not in text:
            return False

        lines = text.split("\n")
        # Ищем строку-разделитель таблицы (содержит | и -)
        for line in lines:
            if line.count("|") >= 2 and line.count("-") >= 3:
                return True

        return False

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Рекурсивное разбиение текста по иерархии сепараторов."""
        if not separators or not text:
            return [text] if text else []

        separator = separators[0]
        new_separators = separators[1:]

        # Если сепаратора нет в тексте - пробуем следующий
        if separator and separator not in text:
            return self._split_text_recursive(text, new_separators)

        # Разбиваем по текущему сепаратору
        if separator:
            splits = text.split(separator)
        else:
            return [text]

        result = []
        for i, split in enumerate(splits):
            if not split:
                continue

            # Восстановление сепаратора (кроме последнего фрагмента)
            if i < len(splits) - 1:
                split = split + separator

            # Рекурсивное разбиение если есть следующие сепараторы
            if new_separators:
                result.extend(self._split_text_recursive(split, new_separators))
            else:
                result.append(split)

        return result

    def _merge_splits_token_aware(self, splits: List[str], chunk_size_tokens: int) -> List[str]:
        """Слияние фрагментов в чанки с кешированием подсчета токенов."""
        if not splits:
            return []

        # Кешируем подсчет токенов для всех splits один раз
        split_tokens: List[Tuple[str, int]] = [(s, self.count_tokens(s)) for s in splits]

        chunks = []
        current_chunk = []
        current_tokens = 0

        for split_text, tokens in split_tokens:
            # Проверяем: влезает ли split в текущий чанк
            if current_tokens + tokens <= chunk_size_tokens:
                # Влезает - добавляем
                current_chunk.append(split_text)
                current_tokens += tokens
            else:
                # Не влезает
                if current_chunk:
                    # Сохраняем текущий чанк
                    chunks.append("".join(current_chunk))

                # Обрабатываем текущий split
                if tokens > chunk_size_tokens:
                    # Split сам по себе больше лимита - режем жестко
                    truncated = self._truncate_to_tokens(split_text, chunk_size_tokens)
                    chunks.append(truncated)
                    # Остаток игнорируем (альтернатива: можно продолжить с остатка)
                    current_chunk = []
                    current_tokens = 0
                else:
                    # Split меньше лимита - начинаем новый чанк с него
                    current_chunk = [split_text]
                    current_tokens = tokens

        # Добавляем последний чанк если есть
        if current_chunk:
            chunks.append("".join(current_chunk))

        return chunks

    def _add_overlap_token_aware(self, chunks: List[str], overlap_tokens: int, max_chunk_tokens: int) -> List[str]:
        """Добавление перекрытия между чанками (из конца предыдущего в начало следующего)."""
        if len(chunks) <= 1 or overlap_tokens <= 0:
            return chunks

        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # Извлекаем overlap из предыдущего чанка (с конца)
            overlap_text = self._extract_overlap_from_end(prev_chunk, overlap_tokens)

            # Добавляем overlap + текущий чанк
            if overlap_text:
                new_chunk = overlap_text + " " + current_chunk
                # Проверяем что не превысили лимит
                if self.count_tokens(new_chunk) <= max_chunk_tokens:
                    result.append(new_chunk)
                else:
                    # Overlap слишком большой - добавляем без него
                    result.append(current_chunk)
            else:
                result.append(current_chunk)

        return result

    def _extract_overlap_from_end(self, text: str, target_tokens: int) -> str:
        """Извлечение последних N токенов для overlap с поиском границы предложения."""
        if not text or target_tokens <= 0:
            return ""

        # Токенизируем текст
        tokens = self._tokenizer.encode(text, add_special_tokens=False)

        # Если текст короче overlap - берем весь текст
        if len(tokens) <= target_tokens:
            return text

        # Берем последние target_tokens токенов
        overlap_tokens = tokens[-target_tokens:]
        overlap_text = self._tokenizer.decode(overlap_tokens)

        # Ищем границу предложения для более чистого разбиения
        sentence_seps = [". ", "! ", "? ", ".\n", "!\n", "?\n", "\n\n"]
        best_split_pos = -1

        for sep in sentence_seps:
            pos = overlap_text.find(sep)
            if pos != -1:
                # Берем текст после разделителя
                candidate_pos = pos + len(sep)
                if candidate_pos > best_split_pos:
                    best_split_pos = candidate_pos

        # Применяем найденную границу
        if best_split_pos > 0 and best_split_pos < len(overlap_text):
            overlap_text = overlap_text[best_split_pos:]

        return overlap_text.strip()

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Жёсткая обрезка текста до max_tokens (для случаев когда split больше лимита)."""
        tokens = self._tokenizer.encode(text, add_special_tokens=False)
        if len(tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[:max_tokens]
        return self._tokenizer.decode(truncated_tokens)
