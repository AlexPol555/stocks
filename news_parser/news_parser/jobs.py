"""Job orchestration for fetching and storing news."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from .config import Config
from .dedup import article_hash
from .fetcher import FetchError, Fetcher
from .parser import extract_article_text
from .storage import ArticleRecord, Storage
from .ticker_match import TickerMatcher
from .utils import setup_logging


def run_once(config: Config) -> dict:
    """Run a single RSS fetching job and return statistics."""

    logger = setup_logging()
    storage = Storage(config.db_path)
    storage.migrate()
    job_id = storage.log_job_start("rss_fetch")
    storage.acquire_lock()
    try:
        source_map = storage.ensure_sources(config.sources)
        fetcher = Fetcher(
            config.user_agent,
            timeout=config.request_timeout,
            delay=config.request_delay,
        )
        new_article_ids: List[int] = []
        duplicates = 0
        for source in config.sources:
            logger.info("Fetching feed for %s", source.name)
            entries = fetcher.fetch_feed(source.rss_url)
            records: List[ArticleRecord] = []
            for entry in entries:
                article_id = article_hash(entry.title or "", entry.url)
                published_at = entry.published or datetime.now(timezone.utc).isoformat()
                body = entry.summary or ""
                try:
                    html = fetcher.fetch_html(entry.url)
                except FetchError:
                    logger.warning("Failed to fetch full article for %s", entry.url)
                else:
                    parsed = extract_article_text(html)
                    if parsed:
                        body = parsed
                records.append(
                    ArticleRecord(
                        title=entry.title,
                        body=body,
                        url=entry.url,
                        published_at=published_at,
                        source_id=source_map.get(source.name, 0),
                        hash=article_id,
                        language="ru",
                        sentiment=None,
                    )
                )
            ids, dup = storage.insert_articles(records)
            new_article_ids.extend(ids)
            duplicates += dup
        matches_total = 0
        tickers = storage.fetch_tickers()
        matcher = TickerMatcher(tickers) if tickers else None
        if matcher:
            for article_id in new_article_ids:
                with storage.connect() as conn:
                    cur = conn.execute("SELECT body FROM articles WHERE id = ?", (article_id,))
                    row = cur.fetchone()
                if not row:
                    continue
                body = row[0] or ""
                matches = matcher.match(body)
                storage.insert_ticker_mentions(
                    article_id,
                    [
                        (match.ticker_id, match.mention_type, match.confidence, match.text)
                        for match in matches
                    ],
                )
                matches_total += len(matches)
        storage.log_job_end(
            job_id,
            status="success",
            new_articles=len(new_article_ids),
            duplicates=duplicates,
            log=f"ticker_matches={matches_total}",
        )
        logger.info(
            "Job finished: %s new articles, %s duplicates", len(new_article_ids), duplicates
        )
        return {
            "new_articles": len(new_article_ids),
            "duplicates": duplicates,
            "ticker_matches": matches_total,
        }
    except Exception as exc:  # pragma: no cover - exceptional path
        logger.exception("Job failed")
        storage.log_job_end(job_id, status="failed", new_articles=0, duplicates=0, log=str(exc))
        raise
    finally:
        storage.release_lock()


__all__ = ["run_once"]
