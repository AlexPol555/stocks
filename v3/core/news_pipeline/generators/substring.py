from __future__ import annotations

import re
from typing import Dict, List, Sequence

try:
    from rapidfuzz.string_metric import jaro_winkler
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    jaro_winkler = None

from ..config import PipelineConfig
from ..models import CandidateSignal, NewsItem, TickerRecord
from ..preprocessing import normalize_text
from .base import CandidateGenerator


class SubstringGenerator(CandidateGenerator):
    name = "substring"

    def __init__(self, *, weight: float = 1.0):
        super().__init__(weight=weight)
        self._normalized_aliases: Dict[int, List[str]] = {}
        self._regex_map: Dict[int, List[re.Pattern[str]]] = {}

    def prepare(self, tickers: Sequence[TickerRecord], *, config: PipelineConfig) -> None:  # noqa: ARG002
        alias_map: Dict[int, List[str]] = {}
        regex_map: Dict[int, List[re.Pattern[str]]] = {}
        for ticker in tickers:
            names: List[str] = []
            if ticker.ticker:
                names.append(ticker.ticker)
            if ticker.name:
                names.append(ticker.name)
            names.extend(list(ticker.aliases))
            normed = [normalize_text(name) for name in names if name]
            alias_map[ticker.id] = [value for value in normed if value]
            regex_map[ticker.id] = [
                re.compile(rf"\b{re.escape(name.lower())}\b", re.IGNORECASE)
                for name in names
                if name
            ]
        self._normalized_aliases = alias_map
        self._regex_map = regex_map

    def generate(
        self,
        news_item: NewsItem,
        tickers: Sequence[TickerRecord],
        *,
        config: PipelineConfig,
        **context,
    ) -> Dict[int, CandidateSignal]:
        haystack = normalize_text(news_item.text)
        results: Dict[int, CandidateSignal] = {}
        for ticker in tickers:
            aliases = self._normalized_aliases.get(ticker.id, [])
            raw_patterns = self._regex_map.get(ticker.id, [])
            if not aliases and not raw_patterns:
                continue
            score = 0.0
            matched_alias: str | None = None
            for alias in aliases:
                if alias and alias in haystack:
                    score = max(score, 1.0)
                    matched_alias = alias
                    break
            if score == 0.0:
                text = news_item.text.lower()
                for pattern in raw_patterns:
                    if pattern.search(text):
                        # degrade score depending on fuzzy closeness to normalized alias
                        candidate = pattern.pattern.strip("\\b")
                        if RAPIDFUZZ_AVAILABLE and aliases:
                            alias_score = max(jaro_winkler(candidate, alias) for alias in aliases)
                        else:
                            alias_score = 0.8
                        score = max(score, min(1.0, 0.8 + 0.2 * alias_score))
                        matched_alias = candidate
                        break
            if score > 0.0:
                results[ticker.id] = CandidateSignal(
                    score=score * self.weight,
                    method=self.name,
                    metadata={"alias": matched_alias or ticker.ticker},
                )
        return results


__all__ = ["SubstringGenerator"]
