from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List
from urllib.parse import urljoin

from dateutil import parser as date_parser
from dateutil import tz

from .config import SourceConfig
from .fetcher import FeedEntry, Fetcher
from .normalize import to_utc_iso

try:  # pragma: no cover - optional dependency
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover - best effort fallback
    BeautifulSoup = None  # type: ignore

LOGGER = logging.getLogger(__name__)
MSK_TZ = tz.gettz("Europe/Moscow")


def fetch_html_entries(fetcher: Fetcher, source: SourceConfig) -> List[FeedEntry]:
    mode = (source.mode or "rss").lower()
    if mode == "smartlab_calendar":
        return _parse_smartlab_table(fetcher, source)
    if mode == "smartlab_economic":
        return _parse_smartlab_table(fetcher, source)
    if mode == "bcs_category":
        return _parse_bcs_category(fetcher, source)
    raise ValueError(f"Unsupported source mode: {source.mode}")


def _parse_smartlab_table(fetcher: Fetcher, source: SourceConfig) -> List[FeedEntry]:
    if BeautifulSoup is None:
        LOGGER.warning("BeautifulSoup is not available; cannot parse Smart-Lab calendar")
        return []
    target = source.page_url or source.rss_url
    if not target:
        return []
    html = fetcher.fetch_html(target)
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table.events tr")
    entries: List[FeedEntry] = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        date_text = cells[0].get_text(" ", strip=True)
        description_cell = cells[2]
        link_tag = description_cell.find("a")
        title = (link_tag.get_text(strip=True) if link_tag else description_cell.get_text(" ", strip=True))
        if not title:
            continue
        href = link_tag.get("href") if link_tag else ""
        url = _resolve_url(source, href, title)
        summary = description_cell.get_text(" ", strip=True)
        published = _parse_calendar_timestamp(date_text)
        entries.append(
            FeedEntry(
                title=title,
                url=url,
                published=published,
                summary=summary,
            )
        )
    return entries


def _parse_calendar_timestamp(raw: str) -> str | None:
    text = (raw or "").replace("\xa0", " ").strip()
    if not text:
        return None
    parts = text.split()
    date_part = parts[0]
    time_part = None
    for item in parts[1:]:
        if ":" in item:
            time_part = item
            break
    try:
        if time_part:
            dt = datetime.strptime(f"{date_part} {time_part}", "%d.%m.%Y %H:%M")
        else:
            dt = datetime.strptime(date_part, "%d.%m.%Y")
    except ValueError:
        return None
    if MSK_TZ is not None:
        dt = dt.replace(tzinfo=MSK_TZ)
    else:
        dt = dt.replace(tzinfo=timezone.utc)
    return to_utc_iso(dt)


def _parse_bcs_category(fetcher: Fetcher, source: SourceConfig) -> List[FeedEntry]:
    target = source.page_url or source.rss_url
    if not target:
        return []
    try:
        markdown = fetcher.fetch_html(f"https://r.jina.ai/{target}")
    except Exception as exc:  # pragma: no cover - network failure
        LOGGER.warning("Failed to fetch BCS Express feed: %s", exc)
        return []
    return _parse_bcs_markdown(markdown)


BULLET_RE = re.compile(r"^\*+\s*(.+)$")
LINK_RE = re.compile(r"^\[(?P<title>.+?)\]\((?P<url>https?://[^)]+)\)")
TIME_RE = re.compile(r"^(Сегодня|Вчера)(.*)$", re.IGNORECASE)
DATE_RE = re.compile(r"^(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)(.*)$", re.IGNORECASE)
DATE_NUM_RE = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}")


def _parse_bcs_markdown(markdown: str) -> List[FeedEntry]:
    lines = [line.strip() for line in markdown.splitlines()]
    entries: List[FeedEntry] = []
    summary_buffer: List[str] = []
    last_timestamp: str | None = None
    current: dict[str, str | None] | None = None
    seen_urls: set[str] = set()

    def flush_current() -> None:
        nonlocal current, summary_buffer
        if not current:
            summary_buffer = []
            return
        summary = ' '.join(summary_buffer).strip() or None
        entries.append(
            FeedEntry(
                title=current['title'],
                url=current['url'],
                published=current['published'],
                summary=summary,
            )
        )
        current = None
        summary_buffer = []

    for line in lines:
        if not line:
            continue
        if line.startswith('!['):
            continue
        if TIME_RE.match(line) or DATE_RE.match(line) or DATE_NUM_RE.match(line):
            flush_current()
            last_timestamp = line
            continue
        link_match = LINK_RE.match(line)
        if link_match:
            title = link_match.group('title').strip()
            url = link_match.group('url').strip()
            if not title or title.startswith('+') or '![' in title:
                continue
            if current and url == current.get('url'):
                continue
            if not last_timestamp or not _is_bcs_article_url(url):
                continue
            if url in seen_urls:
                continue
            flush_current()
            current = {
                'title': title,
                'url': url,
                'published': _parse_bcs_timestamp(last_timestamp),
            }
            seen_urls.add(url)
            summary_buffer = []
            continue
        bullet_match = BULLET_RE.match(line)
        if bullet_match and current:
            summary_buffer.append(bullet_match.group(1).strip())
            continue
        if current and not line.startswith('['):
            summary_buffer.append(line)
    flush_current()
    return entries


def _is_bcs_article_url(url: str) -> bool:
    if not url:
        return False
    if '/novosti-i-analitika/' in url:
        return True
    if '/news/' in url:
        return True
    return False


def _parse_bcs_timestamp(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.replace("\xa0", " ").strip()
    now = datetime.now(MSK_TZ or timezone.utc)
    lower = text.lower()
    try:
        if lower.startswith("сегодня"):
            time_part = lower.split("в", 1)[1].strip() if "в" in lower else ""
            dt = now.replace(hour=_extract_hour(time_part), minute=_extract_minute(time_part), second=0, microsecond=0)
        elif lower.startswith("вчера"):
            time_part = lower.split("в", 1)[1].strip() if "в" in lower else ""
            dt = (now - timedelta(days=1)).replace(hour=_extract_hour(time_part), minute=_extract_minute(time_part), second=0, microsecond=0)
        else:
            dt = date_parser.parse(text, dayfirst=True)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=MSK_TZ or timezone.utc)
        return to_utc_iso(dt)
    except Exception:
        LOGGER.debug("Failed to parse BCS timestamp: %s", text, exc_info=True)
        return None


def _extract_hour(fragment: str) -> int:
    if not fragment or ":" not in fragment:
        return 0
    try:
        return int(fragment.split(":", 1)[0])
    except ValueError:
        return 0


def _extract_minute(fragment: str) -> int:
    if not fragment or ":" not in fragment:
        return 0
    try:
        return int(fragment.split(":", 1)[1].split()[0])
    except ValueError:
        return 0


def _resolve_url(source: SourceConfig, href: str | None, title: str) -> str:
    base = source.page_url or source.rss_url or ""
    if href:
        return urljoin(base, href)
    slug_input = f"{base}-{title}"
    slug = hashlib.md5(slug_input.encode("utf-8")).hexdigest()
    return f"{base.rstrip('/')}/#{slug}"

