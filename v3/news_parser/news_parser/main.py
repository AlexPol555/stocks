"""CLI entrypoint for the news parser."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .config import load_config
from .jobs import run_once
from .storage import Storage
from .summary import generate_summary, write_summary_to_file


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="News parser CLI")
    parser.add_argument("--config", help="Path to JSON config file", default=None)
    parser.add_argument("--once", action="store_true", help="Run one fetching job")
    parser.add_argument("--summary", action="store_true", help="Generate yesterday summary")
    parser.add_argument("--date", help="Date for summary (YYYY-MM-DD)")
    parser.add_argument("--output", help="Output directory for summary JSON", default="output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = load_config(args.config)
    if args.once:
        run_once(config)
        return
    if args.summary:
        target_date = datetime.utcnow()
        if args.date:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        storage = Storage(config.db_path)
        storage.migrate()
        summary = generate_summary(storage, target_date)
        write_summary_to_file(summary, Path(args.output))
        return
    raise SystemExit("No action specified. Use --once or --summary")


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
