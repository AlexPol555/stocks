"""HTML parsing utilities for extracting article content."""

from __future__ import annotations

try:  # pragma: no cover - optional dependency
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:  # pragma: no cover - fallback
    class BeautifulSoup:  # type: ignore
        def __init__(self, html: str, parser: str = "lxml"):
            self._text = html

        def find(self, *args, **kwargs):
            return None

        def find_all(self, *args, **kwargs):
            return []

        def get_text(self, separator: str = " ", strip: bool = False):
            return self._text

from .normalize import normalize_whitespace


def extract_article_text(html: str) -> str:
    """Extract readable text from HTML."""

    soup = BeautifulSoup(html, "lxml")
    article = soup.find("article")
    if article:
        target = article
    else:
        target = soup
    texts = []
    for element in target.find_all(["p", "li"]):
        text = element.get_text(separator=" ", strip=True)
        if text:
            texts.append(text)
    if not texts:
        return normalize_whitespace(target.get_text(separator=" ", strip=True))
    return normalize_whitespace(" ".join(texts))


__all__ = ["extract_article_text"]
