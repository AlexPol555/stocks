"""Configuration helpers for the news parser project."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

DEFAULT_SOURCES = [
    {
        "name": "РБК",
        "rss_url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
        "website": "https://www.rbc.ru",
    },
    {
        "name": "Коммерсантъ",
        "rss_url": "https://www.kommersant.ru/RSS/news.xml",
        "website": "https://www.kommersant.ru",
    },
]


@dataclass
class SourceConfig:
    """Configuration for a single news source."""

    name: str
    rss_url: str
    website: Optional[str] = None

    @classmethod
    def from_mapping(cls, data: dict) -> "SourceConfig":
        return cls(
            name=data.get("name", ""),
            rss_url=data.get("rss_url", ""),
            website=data.get("website"),
        )


@dataclass
class Config:
    """Top-level configuration for the parser."""

    db_path: Path
    sources: List[SourceConfig] = field(default_factory=list)
    user_agent: str = (
        "NewsParserBot/1.0 (+https://github.com/example/news-parser; contact@example.com)"
    )
    request_timeout: int = 20
    request_delay: float = 1.0

    def ensure_directories(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


def _load_sources_from_env() -> List[SourceConfig]:
    raw = os.getenv("NEWS_PARSER_SOURCES")
    if not raw:
        return [SourceConfig.from_mapping(s) for s in DEFAULT_SOURCES]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - configuration error
        raise ValueError("Invalid JSON in NEWS_PARSER_SOURCES") from exc
    return [SourceConfig.from_mapping(item) for item in data]


def load_config(config_path: Optional[os.PathLike[str] | str] = None) -> Config:
    """Load configuration from JSON file or environment variables.

    Parameters
    ----------
    config_path:
        Optional path to a JSON file. When provided the file must contain a
        mapping with keys compatible with :class:`Config`.
    """

    if config_path:
        content = Path(config_path).read_text(encoding="utf-8")
        data = json.loads(content)
        sources = [SourceConfig.from_mapping(item) for item in data.get("sources", [])]
        db_path = Path(data.get("db_path", "news.db")).expanduser().resolve()
        user_agent = data.get("user_agent") or Config.user_agent
        timeout = int(data.get("request_timeout", 20))
        delay = float(data.get("request_delay", 1.0))
        return Config(
            db_path=db_path,
            sources=sources,
            user_agent=user_agent,
            request_timeout=timeout,
            request_delay=delay,
        )

    db_path_env = os.getenv("NEWS_PARSER_DB", "news_parser.db")
    db_path = Path(db_path_env).expanduser().resolve()
    sources = _load_sources_from_env()
    timeout = int(os.getenv("NEWS_PARSER_TIMEOUT", "20"))
    delay = float(os.getenv("NEWS_PARSER_DELAY", "1.0"))
    user_agent = os.getenv("NEWS_PARSER_USER_AGENT", Config.user_agent)

    return Config(
        db_path=db_path,
        sources=sources,
        user_agent=user_agent,
        request_timeout=timeout,
        request_delay=delay,
    )


def iter_source_configs(config: Config) -> Iterable[SourceConfig]:
    """Yield configured sources. Extracted for ease of testing."""

    return list(config.sources)


__all__ = ["Config", "SourceConfig", "iter_source_configs", "load_config"]
