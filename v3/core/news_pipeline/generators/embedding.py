from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

from ..config import PipelineConfig
from ..models import CandidateSignal, NewsItem, TickerRecord
from .base import CandidateGenerator

logger = logging.getLogger(__name__)


class EmbeddingGenerator(CandidateGenerator):
    name = "embedding"

    def __init__(self, *, weight: float = 1.0):
        super().__init__(weight=weight)
        self._model: Optional[SentenceTransformer] = None
        self._ticker_embeddings: Dict[int, np.ndarray] = {}
        self._ticker_names: Dict[int, List[str]] = {}

    def prepare(self, tickers: Sequence[TickerRecord], *, config: PipelineConfig) -> None:
        """Load model and precompute ticker embeddings."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers not available, embedding generator will be disabled")
            return
            
        try:
            self._model = SentenceTransformer(config.embedding_model)
            logger.info("Loaded embedding model: %s", config.embedding_model)
        except Exception as exc:
            logger.error("Failed to load embedding model %s: %s", config.embedding_model, exc)
            raise

        # Prepare ticker names and embeddings
        ticker_names: Dict[int, List[str]] = {}
        ticker_embeddings: Dict[int, np.ndarray] = {}
        
        for ticker in tickers:
            names = ticker.all_names()
            if not names:
                continue
                
            ticker_names[ticker.id] = names
            
            # Check if we have cached embeddings
            if config.cache_embeddings and ticker.embed_vector:
                try:
                    embedding = np.array(ticker.embed_vector, dtype=np.float32)
                    ticker_embeddings[ticker.id] = embedding
                    continue
                except Exception as exc:
                    logger.warning("Failed to use cached embedding for ticker %s: %s", ticker.ticker, exc)
            
            # Compute new embedding
            try:
                # Use the first name as primary, others as context
                primary_name = names[0]
                context = " ".join(names[1:]) if len(names) > 1 else ""
                text_to_embed = f"{primary_name} {context}".strip()
                
                embedding = self._model.encode([text_to_embed], convert_to_numpy=True)[0]
                ticker_embeddings[ticker.id] = embedding.astype(np.float32)
                
                logger.debug("Computed embedding for ticker %s", ticker.ticker)
            except Exception as exc:
                logger.warning("Failed to compute embedding for ticker %s: %s", ticker.ticker, exc)
                continue

        self._ticker_names = ticker_names
        self._ticker_embeddings = ticker_embeddings
        logger.info("Prepared embeddings for %d tickers", len(ticker_embeddings))

    def generate(
        self,
        news_item: NewsItem,
        tickers: Sequence[TickerRecord],
        *,
        config: PipelineConfig,
        **context,
    ) -> Dict[int, CandidateSignal]:
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not self._model or not self._ticker_embeddings:
            return {}

        try:
            # Encode news text
            news_embedding = self._model.encode([news_item.text], convert_to_numpy=True)[0]
            news_embedding = news_embedding.astype(np.float32)
            
            results: Dict[int, CandidateSignal] = {}
            
            # Compute similarities
            for ticker in tickers:
                if ticker.id not in self._ticker_embeddings:
                    continue
                    
                ticker_embedding = self._ticker_embeddings[ticker.id]
                
                # Compute cosine similarity
                similarity = np.dot(news_embedding, ticker_embedding) / (
                    np.linalg.norm(news_embedding) * np.linalg.norm(ticker_embedding)
                )
                
                # Apply thresholds
                if similarity >= config.cos_candidate_threshold:
                    # Determine if this should be auto-applied
                    auto_apply = similarity >= config.cos_auto_threshold
                    
                    results[ticker.id] = CandidateSignal(
                        score=float(similarity) * self.weight,
                        method=self.name,
                        metadata={
                            "similarity": str(similarity),
                            "auto_apply": str(auto_apply),
                            "ticker_names": json.dumps(self._ticker_names.get(ticker.id, [])),
                        },
                    )
            
            return results
            
        except Exception as exc:
            logger.error("Failed to generate embedding candidates: %s", exc)
            return {}

    def batch_generate(
        self,
        news_items: Sequence[NewsItem],
        tickers: Sequence[TickerRecord],
        *,
        config: PipelineConfig,
        **context,
    ) -> List[Dict[int, CandidateSignal]]:
        """Batch processing for better performance with large datasets."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not self._model or not self._ticker_embeddings:
            return [{} for _ in news_items]

        try:
            # Encode all news items at once
            news_texts = [item.text for item in news_items]
            news_embeddings = self._model.encode(news_texts, convert_to_numpy=True)
            news_embeddings = news_embeddings.astype(np.float32)
            
            # Prepare ticker embeddings matrix
            ticker_ids = [ticker.id for ticker in tickers if ticker.id in self._ticker_embeddings]
            if not ticker_ids:
                return [{} for _ in news_items]
                
            ticker_embeddings_matrix = np.array([
                self._ticker_embeddings[ticker_id] for ticker_id in ticker_ids
            ])
            
            # Compute similarity matrix
            # Normalize embeddings for cosine similarity
            news_norms = np.linalg.norm(news_embeddings, axis=1, keepdims=True)
            ticker_norms = np.linalg.norm(ticker_embeddings_matrix, axis=1, keepdims=True)
            
            news_embeddings_norm = news_embeddings / news_norms
            ticker_embeddings_norm = ticker_embeddings_matrix / ticker_norms
            
            # Compute cosine similarities: news_embeddings @ ticker_embeddings.T
            similarity_matrix = np.dot(news_embeddings_norm, ticker_embeddings_norm.T)
            
            results = []
            for i, news_item in enumerate(news_items):
                news_results: Dict[int, CandidateSignal] = {}
                
                for j, ticker_id in enumerate(ticker_ids):
                    similarity = float(similarity_matrix[i, j])
                    
                    if similarity >= config.cos_candidate_threshold:
                        auto_apply = similarity >= config.cos_auto_threshold
                        
                        news_results[ticker_id] = CandidateSignal(
                            score=similarity * self.weight,
                            method=self.name,
                            metadata={
                                "similarity": str(similarity),
                                "auto_apply": str(auto_apply),
                                "ticker_names": json.dumps(self._ticker_names.get(ticker_id, [])),
                            },
                        )
                
                results.append(news_results)
            
            return results
            
        except Exception as exc:
            logger.error("Failed to batch generate embedding candidates: %s", exc)
            return [{} for _ in news_items]


__all__ = ["EmbeddingGenerator"]
