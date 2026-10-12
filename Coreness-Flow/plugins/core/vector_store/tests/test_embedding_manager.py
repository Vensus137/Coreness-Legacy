"""Тесты EmbeddingManager с моками (без реальной ONNX модели)."""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from plugins.core.vector_store.modules.embedding_manager import EmbeddingManager


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def mock_session():
    """Мок ONNX InferenceSession: run(output_names, feed_dict) возвращает dense и token_weights."""
    sess = MagicMock()
    def run_output(output_names, feed_dict):
        batch_size = feed_dict["input_ids"].shape[0]
        seq_len = feed_dict["input_ids"].shape[1]
        dense = np.random.randn(batch_size, 1024).astype(np.float32)
        token_weights = np.random.rand(batch_size, seq_len).astype(np.float32)
        return [dense, token_weights[:, :, np.newaxis]]
    sess.run = run_output
    return sess


@pytest.fixture
def mock_tokenizer():
    """Мок токенайзера: encode, decode, get_vocab, pad_token_id и т.д."""
    tok = MagicMock()
    tok.encode.return_value = [1, 2, 3]
    tok.decode.side_effect = lambda ids: " ".join(str(i) for i in ids)
    tok.get_vocab.return_value = {"word": 100, "hello": 101, "world": 102}
    tok.pad_token_id = 0
    tok.cls_token_id = 1
    tok.eos_token_id = 2
    tok.unk_token_id = 3
    tok.convert_ids_to_tokens.side_effect = lambda ids: [f"tok_{i}" for i in ids]
    # Для вызова tokenizer(texts, padding=..., return_tensors='np')
    def tokenizer_call(texts, **kwargs):
        batch = texts if isinstance(texts, list) else [texts]
        max_len = kwargs.get("max_length", 128)
        seq_len = min(max_len, max(8, sum(len(t) // 4 for t in batch)))
        n = len(batch)
        return {
            "input_ids": np.zeros((n, seq_len), dtype=np.int64),
            "attention_mask": np.ones((n, seq_len), dtype=np.int64),
        }
    tok.side_effect = tokenizer_call
    return tok


class TestEmbeddingManagerWithMocks:
    """Тесты без загрузки реальной модели."""

    def test_encode_empty_returns_empty(self, mock_logger):
        mgr = EmbeddingManager(model_path="/fake", logger=mock_logger)
        dense, sparse = mgr.encode([])
        assert dense == []
        assert sparse == []

    def test_encode_returns_dense_and_sparse_structure(
        self, mock_logger, mock_session, mock_tokenizer
    ):
        """Проверка структуры ответа encode при подставленных session и tokenizer."""
        mock_tokenizer.side_effect = None
        mock_tokenizer.return_value = {
            "input_ids": np.zeros((2, 8), dtype=np.int64),
            "attention_mask": np.ones((2, 8), dtype=np.int64),
        }
        mgr = EmbeddingManager(model_path="/fake", logger=mock_logger, batch_size=2)
        mgr._session = mock_session
        mgr._tokenizer = mock_tokenizer
        mgr._model_loaded = True
        mgr._tokenize_texts = MagicMock(return_value={
            "input_ids": np.zeros((2, 8), dtype=np.int64),
            "attention_mask": np.ones((2, 8), dtype=np.int64),
        })
        dense_vecs, sparse_dicts = mgr.encode(["Hello world.", "Another sentence."], max_length=128)
        assert len(dense_vecs) == 2
        assert len(sparse_dicts) == 2
        for vec in dense_vecs:
            assert isinstance(vec, np.ndarray)
            assert vec.shape == (1024,)
        for s in sparse_dicts:
            assert isinstance(s, dict)

    def test_convert_sparse_to_indices_empty(self, mock_logger):
        mgr = EmbeddingManager(model_path="/fake", logger=mock_logger)
        indices, values = mgr.convert_sparse_to_indices({})
        assert indices == []
        assert values == []

    def test_convert_sparse_to_indices_with_vocab(self, mock_logger, mock_tokenizer):
        mock_tokenizer.get_vocab.return_value = {"hello": 10, "world": 20}
        mgr = EmbeddingManager(model_path="/fake", logger=mock_logger)
        mgr._tokenizer = mock_tokenizer
        mgr._model_loaded = True
        indices, values = mgr.convert_sparse_to_indices({"hello": 0.5, "world": 0.3, "unknown": 0.1})
        assert len(indices) == 2
        assert len(values) == 2
        assert set(indices) == {10, 20}
        assert 0.5 in values and 0.3 in values

    def test_is_loaded_false_before_load(self, mock_logger):
        mgr = EmbeddingManager(model_path="/fake", logger=mock_logger)
        assert mgr.is_loaded() is False

    def test_cleanup_clears_state(self, mock_logger):
        mgr = EmbeddingManager(model_path="/fake", logger=mock_logger)
        mgr._session = MagicMock()
        mgr._tokenizer = MagicMock()
        mgr._model_loaded = True
        mgr.cleanup()
        assert mgr._session is None
        assert mgr._tokenizer is None
        assert mgr._model_loaded is False
