from __future__ import annotations

from types import SimpleNamespace

import pytest

from news_parser.fetcher import Fetcher


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


def test_fetch_feed(monkeypatch):
    feed = SimpleNamespace(
        entries=[
            {
                "title": "Test",
                "link": "https://example.com",
                "published": "2024-05-01T12:00:00Z",
                "summary": "Summary",
            }
        ]
    )

    monkeypatch.setattr("news_parser.fetcher.feedparser.parse", lambda url: feed)

    fetcher = Fetcher("agent", timeout=1, delay=0)
    entries = fetcher.fetch_feed("https://example.com/rss")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.title == "Test"
    assert entry.url == "https://example.com"
    assert entry.summary == "Summary"


def test_fetch_html(monkeypatch):
    response = DummyResponse("<html></html>")
    monkeypatch.setattr("news_parser.fetcher.requests.get", lambda *a, **k: response)
    fetcher = Fetcher("agent", timeout=1, delay=0)
    assert fetcher.fetch_html("https://example.com") == "<html></html>"


def test_fetch_html_error(monkeypatch):
    response = DummyResponse("", status_code=500)
    monkeypatch.setattr("news_parser.fetcher.requests.get", lambda *a, **k: response)
    fetcher = Fetcher("agent", timeout=1, delay=0)
    with pytest.raises(Exception):
        fetcher.fetch_html("https://example.com")
