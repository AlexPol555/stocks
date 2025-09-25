"""Utility helpers for logging and concurrency."""

from __future__ import annotations

import logging
import logging.handlers
import os
import pathlib
import sqlite3
import time
from contextlib import contextmanager
from typing import Generator, Iterable, Iterator, Optional

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"


def setup_logging(log_file: Optional[pathlib.Path] = None) -> logging.Logger:
    """Create a configured logger instance."""

    logger = logging.getLogger("news_parser")
    if logger.handlers:  # pragma: no cover - guard for repeated initialisation
        return logger
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


@contextmanager
def sqlite_connection(path: pathlib.Path) -> Iterator[sqlite3.Connection]:
    """Provide a configured SQLite connection."""

    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=30000;")
        yield conn
    finally:
        conn.close()


class LockError(RuntimeError):
    """Raised when lock acquisition fails."""


def acquire_db_lock(conn: sqlite3.Connection, timeout: int = 3600) -> None:
    """Acquire application level lock stored in the ``jobs_lock`` table."""

    cur = conn.execute("SELECT locked, locked_at FROM jobs_lock WHERE id = 1")
    row = cur.fetchone()
    now = int(time.time())
    if row is None:
        conn.execute("INSERT INTO jobs_lock (id, locked, locked_at) VALUES (1, 0, NULL)")
        conn.commit()
        row = (0, None)
    locked, locked_at = row
    if locked:
        if locked_at is None or now - int(locked_at or 0) < timeout:
            raise LockError("Another job is already running")
    conn.execute(
        "UPDATE jobs_lock SET locked = 1, locked_at = ?, pid = ? WHERE id = 1",
        (now, os.getpid()),
    )
    conn.commit()


def release_db_lock(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE jobs_lock SET locked = 0, locked_at = NULL, pid = NULL WHERE id = 1")
    conn.commit()


def chunked(iterable: Iterable, size: int) -> Iterator[list]:
    """Yield successive chunks from *iterable*."""

    chunk: list = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


__all__ = [
    "LockError",
    "acquire_db_lock",
    "chunked",
    "release_db_lock",
    "setup_logging",
    "sqlite_connection",
]
