"""Generate "What happened yesterday" summaries."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

from .normalize import to_msk_interval
from .storage import Storage


def build_clusters(rows: Sequence[dict]) -> List[dict]:
    clusters: Dict[str, dict] = {}
    for row in rows:
        key = row.get("hash") or row.get("title")
        if key not in clusters:
            clusters[key] = {
                "headline": row.get("title"),
                "sources_count": 0,
                "tickers": set(),
                "summary": (row.get("body") or "")[:200],
                "links": [],
            }
        cluster = clusters[key]
        cluster["sources_count"] += 1
        if row.get("url"):
            cluster["links"].append(row["url"])
        for ticker in row.get("tickers", []):
            cluster["tickers"].add(ticker)
    final_clusters = []
    for cluster in clusters.values():
        final_clusters.append(
            {
                "headline": cluster["headline"],
                "sources_count": cluster["sources_count"],
                "tickers": sorted(cluster["tickers"]),
                "summary": cluster["summary"],
                "links": cluster["links"][:3],
            }
        )
    return sorted(final_clusters, key=lambda x: (-x["sources_count"], x["headline"].lower()))


def generate_summary(storage: Storage, date: datetime) -> dict:
    start, end = to_msk_interval(date)
    rows = []
    for row in storage.fetch_articles_between(start, end):
        ticker_ids = row["ticker_ids"].split(",") if row["ticker_ids"] else []
        rows.append(
            {
                "id": row["id"],
                "title": row["title"],
                "body": row["body"],
                "url": row["url"],
                "hash": row["hash"],
                "tickers": [ticker for ticker in ticker_ids if ticker],
            }
        )
    counter = Counter(ticker for row in rows for ticker in row["tickers"])
    top_mentions = [
        {"ticker": ticker, "mentions": count}
        for ticker, count in counter.most_common(5)
    ]
    summary = {
        "date": date.date().isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "top_mentions": top_mentions,
        "clusters": build_clusters(rows),
    }
    return summary


def write_summary_to_file(summary: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"yesterday_summary_{summary['date']}.json"
    filename.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return filename


__all__ = ["generate_summary", "write_summary_to_file"]
