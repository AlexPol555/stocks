from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from core.settings import get_settings

from .config import BatchMode, PipelineConfig
from .models import (
    CandidateComparison,
    CandidateRecord,
    ExistingCandidate,
    NewsItem,
    ProcessingMetrics,
    TickerRecord,
)

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _utc_now() -> str:
    return datetime.utcnow().strftime(_TIMESTAMP_FORMAT)


class NewsPipelineRepository:
    def __init__(self, db_path: Optional[Path | str] = None):
        settings = get_settings()
        if db_path is None:
            db_path = settings.database_path
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path.as_posix(), timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def ensure_schema(self) -> None:
        with self.connect() as conn:
            self._ensure_sources_table(conn)
            self._ensure_articles_table(conn)
            self._ensure_articles_columns(conn)
            self._ensure_tickers_table(conn)
            self._ensure_news_tickers_table(conn)
            self._ensure_processing_runs(conn)

    def _column_exists(self, conn: sqlite3.Connection, table: str, column: str) -> bool:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cur.fetchall())

    def _ensure_sources_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rss_url TEXT,
                website TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()

    def _ensure_articles_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                url TEXT,
                published_at TEXT,
                title TEXT,
                body TEXT,
                language TEXT DEFAULT 'ru',
                ingested_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE SET NULL
            )
            """
        )
        conn.commit()

    def _ensure_articles_columns(self, conn: sqlite3.Connection) -> None:
        columns = {
            "ingested_at": "TEXT",
            "processed": "INTEGER DEFAULT 0",
            "processed_at": "TEXT",
            "last_batch_id": "TEXT",
            "last_processed_version": "TEXT",
        }
        for column, ddl in columns.items():
            if not self._column_exists(conn, "articles", column):
                conn.execute(f"ALTER TABLE articles ADD COLUMN {column} {ddl}")
        conn.commit()
        
        # Update ingested_at with current timestamp for existing rows
        if "ingested_at" in columns and not self._column_exists(conn, "articles", "ingested_at_updated"):
            try:
                conn.execute("UPDATE articles SET ingested_at = datetime('now') WHERE ingested_at IS NULL")
                conn.execute("ALTER TABLE articles ADD COLUMN ingested_at_updated INTEGER DEFAULT 1")
                conn.commit()
            except Exception as e:
                # If update fails, continue without error
                pass

    def _ensure_tickers_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                name TEXT,
                aliases TEXT,
                isin TEXT,
                exchange TEXT,
                description TEXT,
                embed_blob TEXT,
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()

    def _ensure_news_tickers_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news_tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id INTEGER NOT NULL,
                ticker_id INTEGER NOT NULL,
                score REAL NOT NULL,
                method TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                confirmed INTEGER DEFAULT 0,
                confirmed_by TEXT,
                confirmed_at TEXT,
                batch_id TEXT,
                auto_suggest INTEGER DEFAULT 0,
                history TEXT,
                metadata TEXT,
                FOREIGN KEY(news_id) REFERENCES articles(id) ON DELETE CASCADE,
                FOREIGN KEY(ticker_id) REFERENCES tickers(id) ON DELETE CASCADE,
                UNIQUE(news_id, ticker_id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_tickers_news ON news_tickers(news_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_tickers_confirmed ON news_tickers(confirmed)")
        conn.commit()

    def _ensure_processing_runs(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processing_runs (
                batch_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                batch_size_requested INTEGER,
                batch_size_actual INTEGER,
                started_at TEXT,
                finished_at TEXT,
                status TEXT,
                metrics TEXT,
                operator TEXT,
                chunk_count INTEGER,
                version TEXT,
                resume_token TEXT
            )
            """
        )
        conn.commit()

    def load_tickers(self) -> List[TickerRecord]:
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id, ticker, name, aliases, isin, exchange, description, embed_blob FROM tickers"
            )
            rows = cur.fetchall()
        tickers: List[TickerRecord] = []
        for row in rows:
            aliases: Sequence[str] = []
            alias_raw = row["aliases"]
            if alias_raw:
                try:
                    parsed = json.loads(alias_raw)
                    if isinstance(parsed, list):
                        aliases = [str(item) for item in parsed if item]
                    elif isinstance(parsed, str):
                        aliases = [parsed]
                except json.JSONDecodeError:
                    aliases = [alias_raw]
            embed_vector = None
            embed_blob = row["embed_blob"]
            if embed_blob:
                try:
                    parsed = json.loads(embed_blob)
                    if isinstance(parsed, list):
                        embed_vector = [float(value) for value in parsed]
                except json.JSONDecodeError:
                    embed_vector = None
            tickers.append(
                TickerRecord(
                    id=row["id"],
                    ticker=row["ticker"],
                    name=row["name"],
                    aliases=aliases,
                    isin=row["isin"],
                    exchange=row["exchange"],
                    description=row["description"],
                    embed_vector=embed_vector,
                )
            )
        return tickers

    def store_ticker_embedding(self, ticker_id: int, vector: Sequence[float]) -> None:
        payload = json.dumps(list(vector))
        with self.connect() as conn:
            conn.execute(
                "UPDATE tickers SET embed_blob = ?, updated_at = datetime('now') WHERE id = ?",
                (payload, ticker_id),
            )
            conn.commit()

    def fetch_news_batch(
        self,
        *,
        mode: BatchMode,
        batch_size: int,
        range_start: Optional[str] = None,
        range_end: Optional[str] = None,
        selected_ids: Optional[Sequence[int]] = None,
    ) -> List[NewsItem]:
        where_clauses: List[str] = []
        params: List[object] = []
        
        # Check if ingested_at column exists
        with self.connect() as conn:
            cursor = conn.execute("PRAGMA table_info(articles)")
            columns = [row[1] for row in cursor.fetchall()]
            has_ingested_at = "ingested_at" in columns
        
        # Build order clause based on available columns
        if has_ingested_at:
            order = "COALESCE(a.published_at, a.ingested_at) DESC"
            date_field = "COALESCE(a.published_at, a.ingested_at)"
        else:
            order = "a.published_at DESC"
            date_field = "a.published_at"
        
        if mode == BatchMode.ONLY_UNPROCESSED:
            where_clauses.append("COALESCE(a.processed, 0) = 0")
            if has_ingested_at:
                order = "COALESCE(a.published_at, a.ingested_at) ASC"
            else:
                order = "a.published_at ASC"
        elif mode == BatchMode.RECHECK_SELECTED_RANGE:
            if range_start:
                where_clauses.append(f"{date_field} >= ?")
                params.append(range_start)
            if range_end:
                where_clauses.append(f"{date_field} <= ?")
                params.append(range_end)
        if selected_ids:
            placeholders = ",".join("?" for _ in selected_ids)
            where_clauses.append(f"a.id IN ({placeholders})")
            params.extend(selected_ids)

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        sql = f"""
            SELECT a.id, a.title, a.body, a.language, a.published_at, s.name AS source,
                   COALESCE(a.processed, 0) AS processed,
                   a.processed_at, a.last_batch_id, a.last_processed_version
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            {where_sql}
            ORDER BY {order}
            LIMIT ?
        """
        params.append(batch_size)
        with self.connect() as conn:
            cur = conn.execute(sql, tuple(params))
            rows = cur.fetchall()
        return [
            NewsItem(
                id=row["id"],
                title=row["title"],
                body=row["body"] or "",
                language=row["language"],
                published_at=row["published_at"],
                source=row["source"],
                processed=bool(row["processed"]),
                processed_at=row["processed_at"],
                last_batch_id=row["last_batch_id"],
                last_processed_version=row["last_processed_version"],
            )
            for row in rows
        ]

    def mark_news_processed(
        self,
        news_ids: Sequence[int],
        *,
        batch_id: str,
        version: str,
    ) -> None:
        if not news_ids:
            return
        placeholders = ",".join("?" for _ in news_ids)
        now = _utc_now()
        sql = (
            f"UPDATE articles SET processed = 1, processed_at = ?, last_batch_id = ?, last_processed_version = ? "
            f"WHERE id IN ({placeholders})"
        )
        with self.connect() as conn:
            conn.execute(sql, (now, batch_id, version, *news_ids))
            conn.commit()

    def reset_processed_flags(self, news_ids: Sequence[int]) -> None:
        if not news_ids:
            return
        placeholders = ",".join("?" for _ in news_ids)
        sql = f"UPDATE articles SET processed = 0 WHERE id IN ({placeholders})"
        with self.connect() as conn:
            conn.execute(sql, tuple(news_ids))
            conn.commit()

    def load_existing_candidates(self, news_id: int) -> Dict[int, ExistingCandidate]:
        with self.connect() as conn:
            cur = conn.execute(
                """
                SELECT id, news_id, ticker_id, score, method, confirmed, updated_at, history
                FROM news_tickers
                WHERE news_id = ?
                """,
                (news_id,),
            )
            rows = cur.fetchall()
        existing: Dict[int, ExistingCandidate] = {}
        for row in rows:
            history_payload: List[Dict[str, str]] = []
            if row["history"]:
                try:
                    history_payload = json.loads(row["history"]) or []
                    if not isinstance(history_payload, list):
                        history_payload = []
                except json.JSONDecodeError:
                    history_payload = []
            existing[row["ticker_id"]] = ExistingCandidate(
                id=row["id"],
                news_id=row["news_id"],
                ticker_id=row["ticker_id"],
                score=row["score"],
                method=row["method"],
                confirmed=int(row["confirmed"] or 0),
                updated_at=row["updated_at"],
                history=history_payload,
            )
        return existing

    def upsert_candidate(
        self,
        candidate: CandidateRecord,
        *,
        config: PipelineConfig,
    ) -> CandidateComparison:
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id, score, method, confirmed, history FROM news_tickers WHERE news_id = ? AND ticker_id = ?",
                (candidate.news_id, candidate.ticker_id),
            )
            row = cur.fetchone()
            if row:
                existing_confirmed = int(row["confirmed"] or 0)
                existing_score = float(row["score"] or 0.0)
                history_payload = []
                if row["history"]:
                    try:
                        history_payload = json.loads(row["history"]) or []
                        if not isinstance(history_payload, list):
                            history_payload = []
                    except json.JSONDecodeError:
                        history_payload = []
                if existing_confirmed == 1 and not config.allow_confirmed_overwrite:
                    return CandidateComparison(
                        news_id=candidate.news_id,
                        ticker_id=candidate.ticker_id,
                        existing_score=existing_score,
                        new_score=candidate.score,
                        should_update=False,
                        reason="confirmed_locked",
                    )
                if candidate.score > existing_score:
                    history_payload.append(
                        {
                            "prev_score": existing_score,
                            "new_score": candidate.score,
                            "method": candidate.method,
                            "updated_at": _utc_now(),
                        }
                    )
                    trimmed_history = history_payload[-config.history_keep_max :]
                    conn.execute(
                        """
                        UPDATE news_tickers
                        SET score = ?, method = ?, updated_at = datetime('now'),
                            auto_suggest = ?, batch_id = ?, metadata = ?, history = ?
                        WHERE id = ?
                        """,
                        (
                            candidate.score,
                            candidate.method,
                            int(candidate.auto_suggest),
                            candidate.batch_id,
                            json.dumps(candidate.metadata),
                            json.dumps(trimmed_history),
                            row["id"],
                        ),
                    )
                    conn.commit()
                    return CandidateComparison(
                        news_id=candidate.news_id,
                        ticker_id=candidate.ticker_id,
                        existing_score=existing_score,
                        new_score=candidate.score,
                        should_update=True,
                        reason="score_improved",
                    )
                return CandidateComparison(
                    news_id=candidate.news_id,
                    ticker_id=candidate.ticker_id,
                    existing_score=existing_score,
                    new_score=candidate.score,
                    should_update=False,
                    reason="score_not_improved",
                )
            conn.execute(
                """
                INSERT INTO news_tickers
                    (news_id, ticker_id, score, method, created_at, updated_at, confirmed,
                     confirmed_by, confirmed_at, batch_id, auto_suggest, history, metadata)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.news_id,
                    candidate.ticker_id,
                    candidate.score,
                    candidate.method,
                    candidate.confirmed if candidate.confirmed is not None else 0,
                    candidate.confirmed_by,
                    candidate.confirmed_at,
                    candidate.batch_id,
                    int(candidate.auto_suggest),
                    json.dumps([
                        {
                            "prev_score": None,
                            "new_score": candidate.score,
                            "method": candidate.method,
                            "updated_at": _utc_now(),
                        }
                    ]),
                    json.dumps(candidate.metadata),
                ),
            )
            conn.commit()
            return CandidateComparison(
                news_id=candidate.news_id,
                ticker_id=candidate.ticker_id,
                existing_score=0.0,
                new_score=candidate.score,
                should_update=True,
                reason="inserted",
            )

    def update_confirmation(
        self,
        candidate_id: int,
        *,
        confirmed: int,
        operator: Optional[str],
    ) -> None:
        now = _utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE news_tickers
                SET confirmed = ?, confirmed_by = ?, confirmed_at = ?
                WHERE id = ?
                """,
                (confirmed, operator, now, candidate_id),
            )
            conn.commit()

    def fetch_pending_candidates(
        self,
        *,
        min_score: Optional[float] = None,
        only_unconfirmed: bool = True,
        limit: int = 200,
    ) -> List[sqlite3.Row]:
        where: List[str] = []
        params: List[object] = []
        if only_unconfirmed:
            where.append("COALESCE(confirmed, 0) = 0")
        if min_score is not None:
            where.append("score >= ?")
            params.append(min_score)
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        sql = (
            "SELECT nt.*, t.ticker, t.name, a.title, a.published_at FROM news_tickers nt "
            "LEFT JOIN tickers t ON t.id = nt.ticker_id "
            "LEFT JOIN articles a ON a.id = nt.news_id "
            f"{where_sql} ORDER BY score DESC LIMIT ?"
        )
        params.append(limit)
        with self.connect() as conn:
            cur = conn.execute(sql, tuple(params))
            return cur.fetchall()

    def create_processing_run(
        self,
        *,
        mode: BatchMode,
        requested: int,
        actual: int,
        version: str,
        operator: Optional[str] = None,
    ) -> str:
        batch_id = uuid.uuid4().hex
        now = _utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO processing_runs
                    (batch_id, mode, batch_size_requested, batch_size_actual,
                     started_at, status, operator, chunk_count, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (batch_id, mode.value, requested, actual, now, "running", operator, version),
            )
            conn.commit()
        return batch_id

    def complete_processing_run(
        self,
        batch_id: str,
        *,
        status: str,
        metrics: ProcessingMetrics,
        chunk_count: int,
        resume_token: Optional[str] = None,
    ) -> None:
        now = _utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE processing_runs
                SET status = ?, finished_at = ?, metrics = ?, chunk_count = ?, resume_token = ?
                WHERE batch_id = ?
                """,
                (
                    status,
                    now,
                    json.dumps(metrics.as_dict()),
                    chunk_count,
                    resume_token,
                    batch_id,
                ),
            )
            conn.commit()


__all__ = ["NewsPipelineRepository"]
