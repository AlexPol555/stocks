"""Fetching utilities for RSS feeds and article pages."""

from __future__ import annotations

import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import List, Optional

try:  # pragma: no cover - optional dependency during tests
    import feedparser  # type: ignore
except ImportError:  # pragma: no cover - fallback for minimal environments
    feedparser = SimpleNamespace(parse=lambda url: SimpleNamespace(entries=[]))

try:  # pragma: no cover
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    class _DummyRequests:
        class RequestException(Exception):
            pass

        def get(self, *args, **kwargs):
            raise self.RequestException("requests library is not installed")

    requests = _DummyRequests()  # type: ignore

from .normalize import normalize_whitespace, parse_date


@dataclass
class FeedEntry:
    title: str
    url: str
    published: Optional[str]
    summary: Optional[str]


class FetchError(RuntimeError):
    pass


class Fetcher:
    """Fetch RSS feeds and article HTML content."""

    def __init__(self, user_agent: str, timeout: int = 20, delay: float = 1.0):
        self.user_agent = user_agent
        self.timeout = timeout
        self.delay = delay

    def fetch_feed(self, url: str) -> List[FeedEntry]:
        parsed = feedparser.parse(url)
        entries: List[FeedEntry] = []
        for entry in parsed.entries:
            title = normalize_whitespace(entry.get("title", ""))
            link = entry.get("link") or entry.get("id")
            if not link:
                continue
            published = (
                entry.get("published")
                or entry.get("updated")
                or entry.get("pubDate")
            )
            summary = entry.get("summary") or entry.get("description")
            entries.append(FeedEntry(title=title, url=link, published=parse_date(published), summary=summary))
        return entries

    def fetch_html(self, url: str) -> str:
        headers = {"User-Agent": self.user_agent}
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise FetchError(str(exc)) from exc
        if response.status_code >= 400:
            raise FetchError(f"Failed to fetch {url}: HTTP {response.status_code}")
        time.sleep(self.delay)
        return response.text


__all__ = ["FeedEntry", "FetchError", "Fetcher"]
