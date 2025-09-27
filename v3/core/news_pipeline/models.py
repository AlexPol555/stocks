from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence


@dataclass
class NewsItem:
    id: int
    title: str
    body: str
    language: Optional[str]
    published_at: Optional[str]
    source: Optional[str]
    processed: bool
    processed_at: Optional[str]
    last_batch_id: Optional[str]
    last_processed_version: Optional[str]

    @property
    def text(self) -> str:
        return f"{self.title or ''}\n{self.body or ''}".strip()


@dataclass
class TickerRecord:
    id: int
    ticker: str
    name: Optional[str]
    aliases: Sequence[str] = field(default_factory=list)
    isin: Optional[str] = None
    exchange: Optional[str] = None
    description: Optional[str] = None
    embed_vector: Optional[Sequence[float]] = None

    def all_names(self) -> List[str]:
        names = [self.ticker]
        if self.name:
            names.append(self.name)
        for alias in self.aliases:
            if alias and alias not in names:
                names.append(alias)
        if self.description:
            names.append(self.description)
        return [value for value in names if value]


@dataclass
class CandidateSignal:
    score: float
    method: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class TickerCandidate:
    ticker: TickerRecord
    aggregate_score: float
    signals: List[CandidateSignal]
    auto_apply: bool = False

    def to_record(self, news_id: int, batch_id: str) -> "CandidateRecord":
        return CandidateRecord(
            news_id=news_id,
            ticker_id=self.ticker.id,
            score=self.aggregate_score,
            method="|".join(signal.method for signal in self.signals),
            auto_suggest=self.auto_apply,
            metadata={signal.method: signal.metadata for signal in self.signals},
            batch_id=batch_id,
        )


@dataclass
class CandidateRecord:
    news_id: int
    ticker_id: int
    score: float
    method: str
    auto_suggest: bool
    metadata: Dict[str, Dict[str, str]]
    batch_id: str
    confirmed: Optional[int] = None
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None


@dataclass
class CandidateComparison:
    news_id: int
    ticker_id: int
    existing_score: float
    new_score: float
    should_update: bool
    reason: str


@dataclass
class ProcessingMetrics:
    total_news: int = 0
    processed_news: int = 0
    candidates_generated: int = 0
    auto_applied: int = 0
    skipped_duplicates: int = 0
    retries: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    chunk_count: int = 0

    def as_dict(self) -> Dict[str, float | int]:
        return {
            "total_news": self.total_news,
            "processed_news": self.processed_news,
            "candidates_generated": self.candidates_generated,
            "auto_applied": self.auto_applied,
            "skipped_duplicates": self.skipped_duplicates,
            "retries": self.retries,
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 3),
            "chunk_count": self.chunk_count,
        }


@dataclass
class ExistingCandidate:
    id: int
    news_id: int
    ticker_id: int
    score: float
    method: str
    confirmed: int
    updated_at: Optional[str]
    history: List[Dict[str, str]] = field(default_factory=list)


__all__ = [
    "CandidateComparison",
    "CandidateRecord",
    "CandidateSignal",
    "ExistingCandidate",
    "NewsItem",
    "ProcessingMetrics",
    "TickerCandidate",
    "TickerRecord",
]
