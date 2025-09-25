"""Normalization utilities for text and dates."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from dateutil import parser as date_parser

WHITESPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def normalize_text(text: str) -> str:
    lowered = text.lower()
    no_punct = PUNCT_RE.sub(" ", lowered)
    return normalize_whitespace(no_punct)


def to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        dt = date_parser.parse(value)
    except (ValueError, TypeError):
        return None
    return to_utc_iso(dt)


def parse_date_default(value: Optional[str], default: datetime) -> str:
    parsed = parse_date(value)
    if parsed:
        return parsed
    return to_utc_iso(default)


def yesterday_range(reference: Optional[datetime] = None) -> tuple[datetime, datetime]:
    ref = reference or datetime.now(timezone.utc)
    start = (ref.astimezone(timezone.utc) - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = start.replace(hour=23, minute=59, second=59)
    return start, end


def to_msk_interval(date: datetime) -> tuple[str, str]:
    """Return UTC ISO interval for MSK day of provided datetime."""

    from dateutil import tz

    msk = tz.gettz("Europe/Moscow")
    local = date.astimezone(msk)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(hour=23, minute=59, second=59)
    return to_utc_iso(start.astimezone(timezone.utc)), to_utc_iso(end.astimezone(timezone.utc))


__all__ = [
    "normalize_text",
    "normalize_whitespace",
    "parse_date",
    "parse_date_default",
    "to_msk_interval",
    "to_utc_iso",
]
