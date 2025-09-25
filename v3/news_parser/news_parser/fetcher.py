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


DEFAULT_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


class Fetcher:
    """Fetch RSS feeds and article HTML content."""

    def __init__(self, user_agent: str, timeout: int = 20, delay: float = 1.0):
        self.user_agent = user_agent or DEFAULT_BROWSER_UA
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

    def _headers(self, agent: str) -> dict:
        return {
            "User-Agent": agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
        }

    def fetch_html(self, url: str) -> str:
        errors: List[str] = []
        agents: List[str] = []
        seen: set[str] = set()
        for candidate in (self.user_agent, DEFAULT_BROWSER_UA):
            if candidate and candidate not in seen:
                agents.append(candidate)
                seen.add(candidate)

        last_response = None
        for agent in agents:
            try:
                response = requests.get(
                    url,
                    headers=self._headers(agent),
                    timeout=self.timeout,
                    allow_redirects=True,
                )
            except requests.RequestException as exc:  # pragma: no cover - network failure
                errors.append(str(exc))
                continue
            last_response = response
            if response.status_code < 400:
                time.sleep(self.delay)
                return response.text
            errors.append(f"HTTP {response.status_code} (UA={agent})")

        if last_response is not None and last_response.text:
            if 'kommersant.ru' in url.lower():
                time.sleep(self.delay)
                return last_response.text
            snippet = last_response.text[:600].lower()
            keywords = ("<article", "<p", "<!doctype")
            if any(key in snippet for key in keywords):
                time.sleep(self.delay)
                return last_response.text

        raise FetchError(f"Failed to fetch {url}: {'; '.join(errors)}")


__all__ = ["FeedEntry", "FetchError", "Fetcher"]
