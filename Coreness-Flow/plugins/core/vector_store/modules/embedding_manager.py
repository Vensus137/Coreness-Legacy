"""Менеджер эмбеддингов: BGE-M3 ONNX INT8 (dense + learned sparse)."""

import gc
import os
from typing import Any, Dict, List, Tuple

import numpy as np


class EmbeddingManager:
    """
    Dense + Sparse эмбеддинги через BGE-M3 ONNX INT8.
    Модель выдаёт: dense (1024) + sparse logits (learned sparse, не BM25).
    Оптимизирована для работы в треде (без multiprocessing).
    """

    def __init__(self, model_path: str, logger: Any, batch_size: int = 4, num_threads: int = 4) -> None:
        """Инициализация менеджера эмбеддингов (lazy загрузка модели)."""
        self._model_path = model_path
        self._logger = logger
        self._batch_size = batch_size
        self._num_threads = num_threads
        self._session = None
        self._tokenizer = None
        self._model_loaded = False
        self._batch_count = 0  # для периодического gc после батчей

    def _load_model(self) -> None:
        """Загрузка ONNX-модели и токенайзера (lazy loading при первом использовании)."""
        if self._model_loaded:
            return

        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer

            onnx_path = os.path.join(self._model_path, "model_quantized.onnx")
            if not os.path.isfile(onnx_path):
                raise FileNotFoundError(
                    "Модель эмбеддингов не установлена. Убедитесь, что приложение установлено корректно."
                )

            # Настройка ONNX Runtime: оптимизация графа, переиспользование буферов, арена
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = self._num_threads
            sess_options.inter_op_num_threads = 1
            sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            if getattr(sess_options, "enable_mem_pattern", None) is not None:
                sess_options.enable_mem_pattern = True
            if getattr(sess_options, "enable_cpu_mem_arena", None) is not None:
                sess_options.enable_cpu_mem_arena = True

            providers = ["CPUExecutionProvider"]
            self._session = ort.InferenceSession(onnx_path, sess_options=sess_options, providers=providers)

            # Загрузка токенайзера (use_fast=True если есть быстрый токенайзер — меньше памяти/быстрее)
            try:
                self._tokenizer = AutoTokenizer.from_pretrained(
                    self._model_path, local_files_only=True, use_fast=True
                )
            except (ValueError, OSError):
                self._tokenizer = AutoTokenizer.from_pretrained(
                    self._model_path, local_files_only=True
                )

            self._model_loaded = True
            self._logger.info(
                f"BGE-M3 ONNX модель загружена: {self._model_path} "
                f"(threads={self._num_threads}, batch_size={self._batch_size})"
            )

        except Exception as e:
            self._logger.error(f"Ошибка загрузки ONNX модели: {e}")
            raise RuntimeError(f"Не удалось загрузить ONNX модель из {self._model_path}") from e

    def _tokenize_texts(self, texts: List[str], max_length: int = 8192) -> dict:
        """Токенизация списка текстов; возвращает NumPy arrays для ONNX."""
        if not self._model_loaded:
            self._load_model()

        inputs = self._tokenizer(
            texts, padding=True, truncation=True, max_length=max_length, return_tensors="np"
        )
        return inputs

    def _encode_dense_and_sparse(self, texts: List[str], max_length: int = 8192) -> Tuple[List[np.ndarray], List[Dict[str, float]]]:
        """Генерация dense и sparse эмбеддингов через ONNX модель."""
        if not self._model_loaded:
            self._load_model()

        all_dense = []
        all_sparse = []

        # Обработка батчами
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            inputs = self._tokenize_texts(batch, max_length=max_length)

            # Конвертация в int64 для ONNX
            onnx_inputs = {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64),
            }

            # Inference
            outputs = self._session.run(None, onnx_inputs)

            # outputs[0]: dense (batch_size, 1024); outputs[1]: token_weights (batch_size, seq_len) или (batch_size, seq_len, 1)
            dense = outputs[0]
            token_weights = np.squeeze(outputs[1], axis=-1)  # (batch_size, seq_len)

            # Нормализация dense для cosine similarity
            dense = dense / np.linalg.norm(dense, axis=1, keepdims=True)

            # Подготовка набора игнорируемых токенов
            pad_id = self._tokenizer.pad_token_id
            if pad_id is None:
                pad_id = getattr(self._tokenizer, "pad_token_id", None)
            unused = {
                self._tokenizer.cls_token_id,
                self._tokenizer.eos_token_id,
                pad_id,
                self._tokenizer.unk_token_id,
            }
            unused.discard(None)

            # Обработка каждого элемента батча (.copy() чтобы не держать ссылку на outputs)
            for batch_idx in range(len(batch)):
                all_dense.append(np.array(dense[batch_idx], copy=True))

                sparse_dict = {}
                ids = inputs["input_ids"][batch_idx]
                mask = inputs["attention_mask"][batch_idx]
                weights = token_weights[batch_idx]

                for pos, (tid, m) in enumerate(zip(ids, mask)):
                    if m == 0 or tid in unused:
                        continue
                    w = float(weights[pos])
                    if w > 1e-6:
                        token = self._tokenizer.convert_ids_to_tokens([int(tid)])[0]
                        if token not in sparse_dict or w > sparse_dict[token]:
                            sparse_dict[token] = w

                all_sparse.append(sparse_dict)

            # Очистка после батча: освободить тензоры, снизить пиковую память
            del outputs
            del inputs
            del onnx_inputs
            self._batch_count += 1
            if self._batch_count % 10 == 0:
                gc.collect()

        return all_dense, all_sparse

    def encode(self, texts: List[str], max_length: int = 8192) -> Tuple[List[np.ndarray], List[Dict[str, float]]]:
        """Генерация dense и sparse эмбеддингов через ONNX модель BGE-M3 INT8."""
        if not texts:
            return [], []

        dense_vecs, sparse_dicts = self._encode_dense_and_sparse(texts, max_length=max_length)
        return dense_vecs, sparse_dicts

    def convert_sparse_to_indices(self, sparse_dict: Dict[str, float]) -> Tuple[List[int], List[float]]:
        """Конвертация sparse словаря {token: weight} в формат Qdrant (indices, values)."""
        if not sparse_dict:
            return [], []

        if not self._model_loaded:
            self._load_model()

        vocab = self._tokenizer.get_vocab()
        indices = []
        values = []

        for token, weight in sparse_dict.items():
            if token not in vocab:
                continue
            idx = vocab[token]
            indices.append(idx)
            values.append(weight)

        return indices, values

    def get_tokenizer(self):
        """Получить токенайзер (для чанкера и convert_sparse)."""
        if self._tokenizer is None:
            self._load_model()
        return self._tokenizer

    def is_loaded(self) -> bool:
        """Проверка, загружена ли модель."""
        return self._model_loaded

    def ensure_model_loaded(self) -> None:
        """Явная загрузка модели при первом вызове (для прогрева в фоне при старте)."""
        if not self._model_loaded:
            self._load_model()

    def cleanup(self) -> None:
        """Очистка ресурсов и освобождение памяти."""
        if self._session:
            del self._session
            self._session = None
        if self._tokenizer:
            del self._tokenizer
            self._tokenizer = None
        self._model_loaded = False
        self._logger.debug("EmbeddingManager ресурсы очищены")
