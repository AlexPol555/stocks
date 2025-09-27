from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    fuzz = None

import logging

from ..config import PipelineConfig
from ..models import CandidateSignal, NewsItem, TickerRecord
from .base import CandidateGenerator

logger = logging.getLogger(__name__)


class FuzzyGenerator(CandidateGenerator):
    name = "fuzzy"

    def __init__(self, *, weight: float = 1.0):
        super().__init__(weight=weight)
        self._alias_map: Dict[int, List[str]] = {}

    def prepare(self, tickers: Sequence[TickerRecord], *, config: PipelineConfig) -> None:  # noqa: ARG002
        alias_map: Dict[int, List[str]] = {}
        for ticker in tickers:
            alias_map[ticker.id] = ticker.all_names()
        self._alias_map = alias_map

    def generate(
        self,
        news_item: NewsItem,
        tickers: Sequence[TickerRecord],
        *,
        config: PipelineConfig,
    ) -> Dict[int, CandidateSignal]:
        if not RAPIDFUZZ_AVAILABLE:
            logger.warning("rapidfuzz not available, fuzzy generator will be disabled")
            return {}
            
        results: Dict[int, CandidateSignal] = {}
        haystack = news_item.text
        for ticker in tickers:
            aliases = self._alias_map.get(ticker.id, [])
            best: Tuple[float, str] = (0.0, "")
            for alias in aliases:
                if not alias:
                    continue
                score = fuzz.token_set_ratio(haystack, alias) / 100.0
                if score > best[0]:
                    best = (score, alias)
            if best[0] >= config.review_lower_threshold:
                results[ticker.id] = CandidateSignal(
                    score=best[0] * self.weight,
                    method=self.name,
                    metadata={"alias": best[1]},
                )
        return results


__all__ = ["FuzzyGenerator"]
