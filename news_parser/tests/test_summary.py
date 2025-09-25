from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from news_parser.storage import Storage
from news_parser.summary import generate_summary


@pytest.fixture()
def temp_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "news.db"
    storage = Storage(db_path)
    storage.migrate()
    with storage.connect() as conn:
        conn.execute(
            "INSERT INTO sources (id, name) VALUES (?, ?)",
            (1, "Test"),
        )
        conn.execute(
            "INSERT INTO articles (title, body, url, published_at, source_id, hash) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "Газпром отчитался",
                "Газпром (GAZP) опубликовал отчет",
                "https://example.com/1",
                "2024-05-01T10:00:00Z",
                1,
                "hash1",
            ),
        )
        conn.execute(
            "INSERT INTO article_ticker (article_id, ticker_id, mention_text, mention_type) VALUES (?, ?, ?, ?)",
            (1, 1, "GAZP", "symbol"),
        )
        conn.commit()
    return db_path


def test_generate_summary(temp_db: Path):
    storage = Storage(temp_db)
    summary = generate_summary(storage, datetime(2024, 5, 1))
    assert summary["date"] == "2024-05-01"
    assert summary["top_mentions"][0]["ticker"] == "1"
    assert summary["clusters"][0]["sources_count"] == 1
