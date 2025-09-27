from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

from ..config import PipelineConfig
from ..models import CandidateSignal, NewsItem, TickerRecord
from .base import CandidateGenerator
from .embedding import EmbeddingGenerator
from .fuzzy import FuzzyGenerator
from .ner import NERGenerator
from .substring import SubstringGenerator

logger = logging.getLogger(__name__)


class HybridGenerator(CandidateGenerator):
    name = "hybrid"

    def __init__(self, *, weight: float = 1.0):
        super().__init__(weight=weight)
        self._generators: List[CandidateGenerator] = []
        self._weights: Dict[str, float] = {}

    def prepare(self, tickers: Sequence[TickerRecord], *, config: PipelineConfig) -> None:
        """Initialize and prepare all sub-generators."""
        # Initialize generators with their weights
        generators_config = {
            "substring": {"weight": 1.0, "class": SubstringGenerator},
            "fuzzy": {"weight": 0.8, "class": FuzzyGenerator},
            "ner": {"weight": 0.7, "class": NERGenerator},
            "embedding": {"weight": 0.6, "class": EmbeddingGenerator},
        }
        
        # Override weights from config if available
        if hasattr(config, 'generator_weights') and config.generator_weights:
            generators_config.update(config.generator_weights)
        
        self._generators = []
        self._weights = {}
        
        for name, gen_config in generators_config.items():
            try:
                generator = gen_config["class"](weight=gen_config["weight"])
                generator.prepare(tickers, config=config)
                self._generators.append(generator)
                self._weights[name] = gen_config["weight"]
                logger.info("Initialized %s generator with weight %.2f", name, gen_config["weight"])
            except Exception as exc:
                logger.warning("Failed to initialize %s generator: %s", name, exc)
                continue
        
        logger.info("Hybrid generator prepared with %d sub-generators", len(self._generators))

    def generate(
        self,
        news_item: NewsItem,
        tickers: Sequence[TickerRecord],
        *,
        config: PipelineConfig,
        **context,
    ) -> Dict[int, CandidateSignal]:
        """Generate candidates using all available generators and combine results."""
        if not self._generators:
            logger.warning("No generators available for hybrid generation")
            return {}

        # Collect results from all generators
        all_results: Dict[int, List[CandidateSignal]] = {}
        
        for generator in self._generators:
            try:
                results = generator.generate(news_item, tickers, config=config, **context)
                
                for ticker_id, signal in results.items():
                    if ticker_id not in all_results:
                        all_results[ticker_id] = []
                    all_results[ticker_id].append(signal)
                    
            except Exception as exc:
                logger.warning("Generator %s failed: %s", generator.name, exc)
                continue

        # Combine results using weighted aggregation
        combined_results: Dict[int, CandidateSignal] = {}
        
        for ticker_id, signals in all_results.items():
            if not signals:
                continue
                
            # Calculate weighted average score
            total_weight = 0.0
            weighted_score = 0.0
            methods = []
            metadata = {}
            
            for signal in signals:
                weight = self._weights.get(signal.method, 1.0)
                total_weight += weight
                weighted_score += signal.score * weight
                methods.append(signal.method)
                
                # Merge metadata
                for key, value in signal.metadata.items():
                    if key not in metadata:
                        metadata[key] = []
                    if isinstance(metadata[key], list):
                        metadata[key].append(value)
                    else:
                        metadata[key] = [metadata[key], value]
            
            if total_weight > 0:
                final_score = weighted_score / total_weight
                
                # Apply boosting for multiple method agreement
                method_count = len(set(methods))
                if method_count > 1:
                    # Boost score when multiple methods agree
                    agreement_boost = min(0.2, 0.1 * (method_count - 1))
                    final_score = min(1.0, final_score + agreement_boost)
                
                # Apply confidence adjustment based on method diversity
                confidence_factor = self._calculate_confidence_factor(signals, methods)
                final_score *= confidence_factor
                
                combined_results[ticker_id] = CandidateSignal(
                    score=final_score * self.weight,
                    method="|".join(sorted(set(methods))),
                    metadata={
                        "methods": "|".join(sorted(set(methods))),
                        "method_count": str(method_count),
                        "confidence_factor": str(confidence_factor),
                        **metadata,
                    },
                )
        
        return combined_results

    def batch_generate(
        self,
        news_items: Sequence[NewsItem],
        tickers: Sequence[TickerRecord],
        *,
        config: PipelineConfig,
        **context,
    ) -> List[Dict[int, CandidateSignal]]:
        """Batch processing for better performance."""
        if not self._generators:
            return [{} for _ in news_items]

        # Try to use batch processing for embedding generator
        embedding_gen = None
        other_gens = []
        
        for generator in self._generators:
            if isinstance(generator, EmbeddingGenerator):
                embedding_gen = generator
            else:
                other_gens.append(generator)

        results = []
        
        # Process with embedding generator in batch if available
        if embedding_gen:
            try:
                batch_results = embedding_gen.batch_generate(news_items, tickers, config=config, **context)
            except Exception as exc:
                logger.warning("Batch embedding generation failed: %s", exc)
                batch_results = [{} for _ in news_items]
        else:
            batch_results = [{} for _ in news_items]

        # Process with other generators individually
        for i, news_item in enumerate(news_items):
            item_results = batch_results[i].copy()
            
            for generator in other_gens:
                try:
                    gen_results = generator.generate(news_item, tickers, config=config, **context)
                    
                    # Merge results
                    for ticker_id, signal in gen_results.items():
                        if ticker_id in item_results:
                            # Combine with existing result
                            existing = item_results[ticker_id]
                            combined_score = (existing.score + signal.score) / 2.0
                            combined_method = f"{existing.method}|{signal.method}"
                            
                            item_results[ticker_id] = CandidateSignal(
                                score=combined_score * self.weight,
                                method=combined_method,
                                metadata={
                                    **existing.metadata,
                                    **signal.metadata,
                                },
                            )
                        else:
                            item_results[ticker_id] = CandidateSignal(
                                score=signal.score * self.weight,
                                method=signal.method,
                                metadata=signal.metadata,
                            )
                            
                except Exception as exc:
                    logger.warning("Generator %s failed for item %d: %s", generator.name, i, exc)
                    continue
            
            results.append(item_results)
        
        return results

    def _calculate_confidence_factor(self, signals: List[CandidateSignal], methods: List[str]) -> float:
        """Calculate confidence factor based on signal agreement and method diversity."""
        if not signals:
            return 0.0
        
        # Base confidence
        confidence = 1.0
        
        # Boost for multiple methods
        unique_methods = len(set(methods))
        if unique_methods > 1:
            confidence += 0.1 * (unique_methods - 1)
        
        # Boost for high individual scores
        avg_score = sum(signal.score for signal in signals) / len(signals)
        if avg_score > 0.8:
            confidence += 0.1
        elif avg_score > 0.6:
            confidence += 0.05
        
        # Penalty for very low scores
        if avg_score < 0.3:
            confidence *= 0.8
        
        return min(1.2, confidence)  # Cap at 1.2


__all__ = ["HybridGenerator"]
