"""SQLite storage layer for the news parser."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set, Tuple

from .config import SourceConfig
from .utils import acquire_db_lock, release_db_lock

MIGRATION_FILE = Path(__file__).resolve().parent.parent / "migrations" / "sqlite" / "001_create_news_tables.sql"


@dataclass
class ArticleRecord:
    title: str
    body: str
    url: str
    published_at: Optional[str]
    source_id: int
    hash: str
    language: Optional[str] = None
    sentiment: Optional[int] = None


class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

    def migrate(self) -> None:
        sql = MIGRATION_FILE.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(sql)

    def ensure_sources(self, sources: Sequence[SourceConfig]) -> dict[str, int]:
        mapping: dict[str, int] = {}
        with self.connect() as conn:
            for src in sources:
                conn.execute(
                    "INSERT OR IGNORE INTO sources (name, rss_url, website) VALUES (?, ?, ?)",
                    (src.name, src.rss_url, src.website),
                )
            conn.commit()
            for src in sources:
                cur = conn.execute("SELECT id FROM sources WHERE name = ?", (src.name,))
                row = cur.fetchone()
                if row:
                    mapping[src.name] = row[0]
        return mapping

    def insert_articles(self, articles: Iterable[ArticleRecord]) -> Tuple[List[int], int]:
        ids: List[int] = []
        duplicates = 0
        with self.connect() as conn:
            cur = conn.cursor()
            for article in articles:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO articles
                    (title, body, url, published_at, source_id, hash, language, sentiment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article.title,
                        article.body,
                        article.url,
                        article.published_at,
                        article.source_id,
                        article.hash,
                        article.language,
                        article.sentiment,
                    ),
                )
                if cur.rowcount:
                    ids.append(cur.lastrowid)
                else:
                    duplicates += 1
            conn.commit()
        return ids, duplicates

    def insert_ticker_mentions(
        self, article_id: int, matches: Sequence[tuple[int, str, float, Optional[str]]]
    ) -> None:
        if not matches:
            return
        with self.connect() as conn:
            for ticker_id, mention_type, confidence, mention_text in matches:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO article_ticker
                    (article_id, ticker_id, mention_type, confidence, mention_text)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (article_id, ticker_id, mention_type, confidence, mention_text),
                )
            conn.commit()

    def fetch_tickers(self) -> List[dict]:
        with self.connect() as conn:
            try:
                cur = conn.execute(
                    "SELECT id, ticker, short_name, full_name, aliases FROM tickers"
                )
            except sqlite3.OperationalError:
                return []
            result = []
            for row in cur.fetchall():
                aliases = []
                if row[4]:
                    try:
                        aliases = json.loads(row[4])
                    except json.JSONDecodeError:
                        aliases = [row[4]]
                names = [
                    name
                    for name in [row[1], row[2], row[3]]
                    if name
                ]
                result.append(
                    {
                        "id": row[0],
                        "ticker": row[1],
                        "names": list({n for n in names if n}) + aliases,
                    }
                )
            return result

    def fetch_articles_between(self, start_iso: str, end_iso: str) -> List[sqlite3.Row]:
        conn = self.connect()
        conn.row_factory = sqlite3.Row
        with conn:
            cur = conn.execute(
                """
                SELECT a.*, GROUP_CONCAT(at.ticker_id) as ticker_ids
                FROM articles a
                LEFT JOIN article_ticker at ON at.article_id = a.id
                WHERE a.published_at BETWEEN ? AND ?
                GROUP BY a.id
                ORDER BY a.published_at ASC
                """,
                (start_iso, end_iso),
            )
            return cur.fetchall()

    def find_existing_hashes(self, hashes: Sequence[str]) -> Set[str]:
        if not hashes:
            return set()
        placeholders = ",".join("?" for _ in hashes)
        query = f"SELECT hash FROM articles WHERE hash IN ({placeholders})"
        with self.connect() as conn:
            cur = conn.execute(query, tuple(hashes))
            return {row[0] for row in cur.fetchall()}

    def log_job_start(self, job_type: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO jobs_log (job_type, started_at, status) VALUES (?, datetime('now'), ?)",
                (job_type, "started"),
            )
            conn.commit()
            return cur.lastrowid

    def log_job_end(
        self,
        job_id: int,
        *,
        status: str,
        new_articles: int,
        duplicates: int,
        log: str = "",
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE jobs_log
                SET finished_at = datetime('now'), status = ?, new_articles = ?, duplicates = ?, log = ?
                WHERE id = ?
                """,
                (status, new_articles, duplicates, log, job_id),
            )
            conn.commit()

    def acquire_lock(self) -> None:
        with self.connect() as conn:
            acquire_db_lock(conn)

    def release_lock(self) -> None:
        with self.connect() as conn:
            release_db_lock(conn)


__all__ = ["ArticleRecord", "Storage"]
