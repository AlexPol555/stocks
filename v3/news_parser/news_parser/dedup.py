"""Deduplication helpers."""

from __future__ import annotations

import hashlib

from .normalize import normalize_text


def article_hash(title: str, url: str) -> str:
    normalized = normalize_text(title) + "::" + url.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


__all__ = ["article_hash"]
