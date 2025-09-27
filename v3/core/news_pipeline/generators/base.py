from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Sequence

from ..config import PipelineConfig
from ..models import CandidateSignal, NewsItem, TickerRecord


class CandidateGenerator(ABC):
    name: str

    def __init__(self, *, weight: float = 1.0):
        self.weight = weight

    def prepare(self, tickers: Sequence[TickerRecord], *, config: PipelineConfig) -> None:
        del tickers
        del config

    @abstractmethod
    def generate(
        self,
        news_item: NewsItem,
        tickers: Sequence[TickerRecord],
        *,
        config: PipelineConfig,
        **context,
    ) -> Dict[int, CandidateSignal]:
        raise NotImplementedError


__all__ = ["CandidateGenerator"]
