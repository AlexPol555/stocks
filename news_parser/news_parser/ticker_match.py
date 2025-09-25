"""Ticker matching helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .normalize import normalize_text


@dataclass
class Ticker:
    id: int
    ticker: str
    names: Sequence[str]


@dataclass
class TickerMatch:
    ticker_id: int
    mention_type: str
    confidence: float
    text: str


class TickerMatcher:
    def __init__(self, tickers: Iterable[dict]):
        self.tickers = [
            Ticker(
                id=item["id"],
                ticker=item["ticker"],
                names=[name for name in item.get("names", []) if name],
            )
            for item in tickers
        ]
        self._patterns = {
            ticker.id: re.compile(rf"\b{re.escape(ticker.ticker.lower())}\b")
            for ticker in self.tickers
            if ticker.ticker
        }
        self._name_patterns = {
            ticker.id: [re.compile(rf"\b{re.escape(name.lower())}\b") for name in ticker.names]
            for ticker in self.tickers
        }

    def match(self, text: str) -> List[TickerMatch]:
        normalized = normalize_text(text)
        matches: List[TickerMatch] = []
        for ticker in self.tickers:
            pattern = self._patterns.get(ticker.id)
            if pattern and pattern.search(normalized):
                matches.append(TickerMatch(ticker.id, "symbol", 1.0, ticker.ticker))
                continue
            for compiled, name in zip(self._name_patterns.get(ticker.id, []), ticker.names):
                if compiled.search(normalized):
                    matches.append(TickerMatch(ticker.id, "name", 1.0, name))
                    break
        return matches


__all__ = ["Ticker", "TickerMatch", "TickerMatcher"]
