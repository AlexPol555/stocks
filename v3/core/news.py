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


def _supports_news_pipeline(conn: sqlite3.Connection) -> bool:
    """Check if news pipeline tables exist."""
    query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name='news_tickers' LIMIT 1"
    try:
        return conn.execute(query).fetchone() is not None
    except sqlite3.DatabaseError:
        return False


def fetch_recent_articles(limit: int = 25, include_without_tickers: bool = False) -> List[Dict[str, Any]]:
    storage = _storage()
    conn = storage.connect()
    conn.row_factory = sqlite3.Row
    try:
        # Check if news pipeline tables exist
        has_news_pipeline = _supports_news_pipeline(conn)
        if has_news_pipeline:
            if include_without_tickers:
                # Use news pipeline data (news_tickers table) - all articles
                sql = (
                    "SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, "
                    "s.name AS source_name, "
                    "GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols "
                    "FROM articles a "
                    "LEFT JOIN sources s ON s.id = a.source_id "
                    "LEFT JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1 "
                    "LEFT JOIN tickers t ON t.id = nt.ticker_id "
                    "GROUP BY a.id "
                    "ORDER BY COALESCE(a.published_at, a.created_at) DESC "
                    "LIMIT ?"
                )
            else:
                # Use news pipeline data (news_tickers table) - only articles with confirmed tickers
                sql = (
                    "SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, "
                    "s.name AS source_name, "
                    "GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols "
                    "FROM articles a "
                    "LEFT JOIN sources s ON s.id = a.source_id "
                    "INNER JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1 "
                    "LEFT JOIN tickers t ON t.id = nt.ticker_id "
                    "GROUP BY a.id "
                    "ORDER BY COALESCE(a.published_at, a.created_at) DESC "
                    "LIMIT ?"
                )
        elif _supports_tickers(conn):
            # Fallback to old article_ticker table
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
            # No ticker support
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
    
    # Try to use news pipeline data first
    if _supports_news_pipeline(storage.connect()):
        return _build_summary_from_pipeline(storage, date)
    else:
        # Fallback to original summary generation
        summary = generate_summary(storage, date)
        return summary


def _build_summary_from_pipeline(storage, target_date: datetime) -> Dict[str, Any]:
    """Build summary using news pipeline data."""
    from datetime import time, timezone
    from collections import Counter
    
    # Convert to MSK timezone for date range
    msk_tz = timezone.utc  # Simplified - should use proper MSK timezone
    start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    conn = storage.connect()
    conn.row_factory = sqlite3.Row
    try:
        # Get articles with confirmed tickers for the date range
        sql = """
            SELECT a.id, a.title, a.body, a.url, a.published_at,
                   GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols
            FROM articles a
            LEFT JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1
            LEFT JOIN tickers t ON t.id = nt.ticker_id
            WHERE a.published_at >= ? AND a.published_at <= ?
            GROUP BY a.id
            ORDER BY a.published_at DESC
        """
        rows = conn.execute(sql, (start_date.isoformat(), end_date.isoformat())).fetchall()
        
        # Process articles
        articles = []
        for row in rows:
            tickers = []
            if row["ticker_symbols"]:
                tickers = [ticker.strip() for ticker in str(row["ticker_symbols"]).split(",") if ticker.strip()]
            
            articles.append({
                "id": row["id"],
                "title": row["title"],
                "body": row["body"] or "",
                "url": row["url"],
                "hash": str(row["id"]),  # Use ID as hash
                "tickers": tickers,
            })
        
        # Count ticker mentions
        counter = Counter(ticker for article in articles for ticker in article["tickers"])
        top_mentions = [
            {"ticker": ticker, "mentions": count}
            for ticker, count in counter.most_common(5)
        ]
        
        # Build clusters
        clusters = _build_clusters_from_articles(articles)
        
        summary = {
            "date": target_date.date().isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "top_mentions": top_mentions,
            "clusters": clusters,
        }
        
        return summary
        
    finally:
        conn.close()


def _build_clusters_from_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build clusters from articles data."""
    clusters: Dict[str, Dict[str, Any]] = {}
    
    for article in articles:
        key = article.get("hash") or article.get("title")
        if key not in clusters:
            clusters[key] = {
                "headline": article.get("title"),
                "sources_count": 1,
                "tickers": set(article.get("tickers", [])),
                "summary": (article.get("body") or "")[:200],
                "links": [article["url"]] if article.get("url") else [],
            }
        else:
            cluster = clusters[key]
            cluster["sources_count"] += 1
            cluster["tickers"].update(article.get("tickers", []))
            if article.get("url") and article["url"] not in cluster["links"]:
                cluster["links"].append(article["url"])
    
    # Convert to final format
    final_clusters = []
    for cluster in clusters.values():
        final_clusters.append({
            "headline": cluster["headline"],
            "sources_count": cluster["sources_count"],
            "tickers": sorted(list(cluster["tickers"])),
            "summary": cluster["summary"],
            "links": cluster["links"][:3],
        })
    
    return sorted(final_clusters, key=lambda x: (-x["sources_count"], x["headline"].lower()))


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
