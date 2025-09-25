from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from news_parser.news_parser.config import Config, load_config
from news_parser.news_parser.jobs import run_once
from news_parser.news_parser.storage import Storage
from news_parser.news_parser.utils import acquire_db_lock as _acquire_lock_util
from news_parser.news_parser.summary import generate_summary
from news_parser.news_parser.utils import LockError, release_db_lock

from .settings import get_settings

LOGGER = logging.getLogger(__name__)

_DEFAULT_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


@lru_cache(maxsize=1)
def _default_config_path() -> Optional[Path]:
    env_path = os.getenv("NEWS_PARSER_CONFIG")
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return candidate.resolve()
    config_dir = get_settings().config_dir
    candidate = config_dir / "news_parser.json"
    if candidate.exists():
        return candidate.resolve()
    return None


def load_app_config(config_path: Optional[Path | str] = None) -> Config:
    """Load parser config and align storage with the main app database."""

    cfg_path = config_path or _default_config_path()
    config = load_config(str(cfg_path) if cfg_path else None)
    config.db_path = get_settings().database_path
    override_ua = os.getenv("NEWS_PARSER_USER_AGENT")
    default_ua = override_ua or _DEFAULT_BROWSER_UA
    if not (config.user_agent or "").strip() or config.user_agent.startswith("NewsParserBot"):
        config.user_agent = default_ua
    config.ensure_directories()
    return config


def _storage(config: Optional[Config] = None) -> Storage:
    cfg = config or load_app_config()
    storage = Storage(Path(cfg.db_path))
    storage.migrate()
    return storage


def ensure_schema(config: Optional[Config] = None) -> None:
    _storage(config)


def run_fetch_job(
    config: Optional[Config] = None,
    progress_callback: Optional[Callable[[str, Dict[str, object]], None]] = None,
) -> Dict[str, Any]:
    """Execute a single RSS fetch cycle and report stats."""

    cfg = config or load_app_config()
    try:
        if progress_callback is None:
            stats = run_once(cfg)
        else:
            stats = run_once(cfg, progress=progress_callback)
        return {"status": "success", "stats": stats}
    except LockError as exc:
        LOGGER.warning("News parser lock is engaged: %s", exc)
        return {"status": "locked", "error": str(exc)}
    except Exception as exc:  # pragma: no cover - surfaced in UI
        LOGGER.exception("News parser job failed")
        return {"status": "error", "error": str(exc)}


def release_parser_lock(config: Optional[Config] = None) -> bool:
    """Force reset application-level lock flag.

    Returns True when the lock was engaged before the reset.
    """

    cfg = config or load_app_config()
    storage = _storage(cfg)
    conn = storage.connect()
    conn.row_factory = sqlite3.Row
    try:
        try:
            row = conn.execute("SELECT locked FROM jobs_lock WHERE id = 1").fetchone()
        except sqlite3.DatabaseError:
            row = None
        was_locked = bool(row and row["locked"])
        release_db_lock(conn)
        return was_locked
    finally:
        conn.close()


def _supports_tickers(conn: sqlite3.Connection) -> bool:
    query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tickers' LIMIT 1"
    try:
        return conn.execute(query).fetchone() is not None
    except sqlite3.DatabaseError:
        return False


def fetch_recent_articles(limit: int = 25) -> List[Dict[str, Any]]:
    storage = _storage()
    conn = storage.connect()
    conn.row_factory = sqlite3.Row
    try:
        has_tickers = _supports_tickers(conn)
        if has_tickers:
            sql = (
                "SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, "
                "s.name AS source_name, "
                "GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols "
                "FROM articles a "
                "LEFT JOIN sources s ON s.id = a.source_id "
                "LEFT JOIN article_ticker at ON at.article_id = a.id "
                "LEFT JOIN tickers t ON t.id = at.ticker_id "
                "GROUP BY a.id "
                "ORDER BY COALESCE(a.published_at, a.created_at) DESC "
                "LIMIT ?"
            )
        else:
            sql = (
                "SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, "
                "s.name AS source_name, NULL AS ticker_symbols "
                "FROM articles a "
                "LEFT JOIN sources s ON s.id = a.source_id "
                "ORDER BY COALESCE(a.published_at, a.created_at) DESC "
                "LIMIT ?"
            )
        rows = conn.execute(sql, (limit,)).fetchall()
    finally:
        conn.close()
    articles: List[Dict[str, Any]] = []
    for row in rows:
        published = row["published_at"] or row["created_at"]
        tickers = []
        if row["ticker_symbols"]:
            tickers = [ticker for ticker in str(row["ticker_symbols"]).split(",") if ticker]
        articles.append(
            {
                "id": row["id"],
                "title": row["title"],
                "url": row["url"],
                "published_at": published,
                "body": row["body"],
                "source": row["source_name"],
                "tickers": tickers,
            }
        )
    return articles


def fetch_sources() -> List[Dict[str, Any]]:
    storage = _storage()
    conn = storage.connect()
    conn.row_factory = sqlite3.Row
    try:
        sql = (
            "SELECT id, name, rss_url, website, created_at "
            "FROM sources ORDER BY name"
        )
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def fetch_jobs(limit: int = 10) -> List[Dict[str, Any]]:
    storage = _storage()
    conn = storage.connect()
    conn.row_factory = sqlite3.Row
    try:
        sql = (
            "SELECT id, job_type, started_at, finished_at, status, new_articles, duplicates, log "
            "FROM jobs_log ORDER BY started_at DESC LIMIT ?"
        )
        rows = conn.execute(sql, (limit,)).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def build_summary(target_date: Optional[datetime] = None) -> Dict[str, Any]:
    storage = _storage()
    date = target_date or datetime.utcnow()
    summary = generate_summary(storage, date)
    return summary


__all__ = [
    "build_summary",
    "ensure_schema",
    "release_parser_lock",
    "fetch_jobs",
    "fetch_recent_articles",
    "fetch_sources",
    "load_app_config",
    "run_fetch_job",
]
