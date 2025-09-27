from __future__ import annotations

import logging
from typing import Iterable, List, Sequence

import numpy as np

from .config import PipelineConfig
from .exceptions import EmbeddingBackendError
from .models import NewsItem, TickerRecord
from .repository import NewsPipelineRepository

LOGGER = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, config: PipelineConfig, repository: NewsPipelineRepository):
        self.config = config
        self.repository = repository
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency guard
            raise EmbeddingBackendError("sentence-transformers is required for embedding pipeline") from exc
        try:
            self._model = SentenceTransformer(self.config.embedding_model)
        except Exception as exc:  # pragma: no cover - model load failure
            raise EmbeddingBackendError(f"Failed to load embedding model: {exc}") from exc
        return self._model

    def encode_news(self, news_items: Sequence[NewsItem]) -> np.ndarray:
        texts = [item.text for item in news_items]
        model = self._load_model()
        return np.asarray(model.encode(texts, batch_size=min(len(texts), 16), convert_to_numpy=True))

    def ensure_ticker_embeddings(self, tickers: Sequence[TickerRecord]) -> np.ndarray:
        missing: List[TickerRecord] = [ticker for ticker in tickers if not ticker.embed_vector]
        if missing:
            model = self._load_model()
            descriptions = [" ".join(ticker.all_names()) for ticker in missing]
            vectors = np.asarray(
                model.encode(descriptions, batch_size=min(len(descriptions), 16), convert_to_numpy=True)
            )
            for ticker, vector in zip(missing, vectors):
                if self.config.cache_embeddings:
                    try:
                        self.repository.store_ticker_embedding(ticker.id, vector.tolist())
                    except Exception:  # pragma: no cover - logging only
                        LOGGER.exception("Failed to persist ticker embedding for %s", ticker.ticker)
                ticker.embed_vector = vector.tolist()
        matrix = np.asarray(
            [
                ticker.embed_vector if ticker.embed_vector is not None else np.zeros(384)
                for ticker in tickers
            ]
        )
        return matrix

    def cosine_similarity(self, news_vectors: np.ndarray, ticker_vectors: np.ndarray) -> np.ndarray:
        news_norm = np.linalg.norm(news_vectors, axis=1, keepdims=True)
        ticker_norm = np.linalg.norm(ticker_vectors, axis=1, keepdims=True)
        denom = np.maximum(news_norm, 1e-8)
        news_unit = news_vectors / denom
        ticker_unit = ticker_vectors / np.maximum(ticker_norm, 1e-8)
        return news_unit @ ticker_unit.T

    def faiss_topk(
        self,
        news_vectors: np.ndarray,
        ticker_vectors: np.ndarray,
        *,
        top_k: int = 10,
    ) -> List[List[tuple[int, float]]]:
        if not self.config.use_faiss:
            return []
        try:
            import faiss  # type: ignore
        except ImportError:  # pragma: no cover - optional dependency
            LOGGER.warning("FAISS not available, falling back to cosine matrix multiply")
            return []
        dimension = ticker_vectors.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(ticker_vectors.astype("float32"))
        scores, indices = index.search(news_vectors.astype("float32"), top_k)
        top: List[List[tuple[int, float]]] = []
        for row_scores, row_indices in zip(scores, indices):
            top.append([(int(idx), float(score)) for idx, score in zip(row_indices, row_scores)])
        return top


__all__ = ["EmbeddingService"]
