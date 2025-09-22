"""Routines that keep the local database in sync with market data."""
from __future__ import annotations

import logging
import re
from typing import Iterable, List

import pandas as pd

logger = logging.getLogger(__name__)


def normalize_ticker(ticker: str) -> str:
    """Strip contract month suffixes like ``AFLT-12.24`` → ``AFLT``."""
    return re.sub(r"-\d+(?:\.\d+)?$", "", ticker or "").strip()


def _find_company(cursor, ticker: str):
    cursor.execute(
        "SELECT id, contract_code FROM companies WHERE contract_code LIKE ?",
        (f"{ticker}%",),
    )
    row = cursor.fetchone()
    if row:
        return row[0], row[1]
    return None, None


def update_missing_market_data(analyzer, conn, ticker: str, stock_data: pd.DataFrame) -> List[str]:
    """Populate ``daily_data`` rows that miss OHLCV values."""
    log: List[str] = []
    cursor = conn.cursor()

    normalized = normalize_ticker(ticker)
    log.append(f"Обновление для тикера: оригинал '{ticker}', нормализованный '{normalized}'.")

    company_id, db_ticker = _find_company(cursor, normalized)
    if company_id is None:
        log.append(f"Компания с нормализованным тикером '{normalized}' не найдена в базе.")
        return log

    log.append(f"Найдена компания: {db_ticker} (id={company_id}).")

    cursor.execute(
        "SELECT id, date FROM daily_data WHERE company_id = ? AND open IS NULL",
        (company_id,),
    )
    records = cursor.fetchall()
    if not records:
        log.append(f"Для {ticker} (id={company_id}) нет записей с отсутствующими рыночными данными.")
        return log

    if "date_obj" not in stock_data.columns:
        stock_data = stock_data.copy()
        stock_data["date_obj"] = pd.to_datetime(stock_data["time"]).dt.date

    for daily_data_id, date_str in records:
        try:
            daily_date = pd.to_datetime(date_str).date()
        except Exception as exc:  # pragma: no cover - defensive
            log.append(f"Ошибка преобразования даты '{date_str}': {exc}")
            continue

        matching_rows = stock_data[stock_data["date_obj"] == daily_date]
        if matching_rows.empty:
            log.append(f"Нет рыночных данных для {ticker} на {daily_date}.")
            continue

        row = matching_rows.iloc[0]
        cursor.execute(
            """
            UPDATE daily_data
            SET open = ?, low = ?, high = ?, close = ?, volume = ?
            WHERE id = ?
            """,
            (
                row.get("open"),
                row.get("low"),
                row.get("high"),
                row.get("close"),
                row.get("volume"),
                daily_data_id,
            ),
        )
        conn.commit()
        log.append(f"Обновлены рыночные данные для {ticker} на {daily_date}.")

    return log


def _missing_daily_data(cursor, ticker: str) -> Iterable[tuple[int, str]]:
    cursor.execute(
        """
        SELECT dd.id, dd.date
        FROM daily_data dd
        JOIN companies c ON dd.company_id = c.id
        WHERE c.contract_code = ?
          AND (dd.open IS NULL OR dd.low IS NULL OR dd.high IS NULL OR dd.close IS NULL OR dd.volume IS NULL)
        """,
        (ticker,),
    )
    return cursor.fetchall()


def auto_update_all_tickers(analyzer, conn, full_update: bool = True) -> List[str]:
    """Synchronise ``daily_data`` using :class:`~core.analyzer.StockAnalyzer`."""
    log: List[str] = []
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT contract_code FROM companies")
    tickers = [row[0] for row in cursor.fetchall()]

    if full_update:
        cursor.execute("DELETE FROM daily_data")
        conn.commit()
        log.append("Полное обновление: таблица daily_data очищена.")

    figi_mapping = analyzer.get_figi_mapping()

    for ticker in tickers:
        figi = figi_mapping.get(ticker)
        if not figi:
            log.append(f"FIGI для {ticker} не найден.")
            continue

        stock_data = analyzer.get_stock_data(figi)
        if stock_data.empty:
            log.append(f"Нет рыночных данных для {ticker}.")
            continue

        if full_update:
            for _, row in stock_data.iterrows():
                cursor.execute(
                    """
                    INSERT INTO daily_data (company_id, date, open, low, high, close, volume)
                    VALUES ((SELECT id FROM companies WHERE contract_code = ?), ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ticker,
                        pd.to_datetime(row["time"]).date(),
                        row["open"],
                        row["low"],
                        row["high"],
                        row["close"],
                        row["volume"],
                    ),
                )
            conn.commit()
            log.append(f"Полностью обновлены данные для {ticker}.")
            continue

        for daily_data_id, date_str in _missing_daily_data(cursor, ticker):
            date_obj = pd.to_datetime(date_str).date()
            matching = stock_data[pd.to_datetime(stock_data["time"]).dt.date == date_obj]
            if matching.empty:
                log.append(f"Нет рыночных данных для {ticker} на {date_obj}.")
                continue

            row = matching.iloc[0]
            cursor.execute(
                """
                UPDATE daily_data
                SET open = ?, low = ?, high = ?, close = ?, volume = ?
                WHERE id = ?
                """,
                (
                    row["open"],
                    row["low"],
                    row["high"],
                    row["close"],
                    row["volume"],
                    daily_data_id,
                ),
            )
        conn.commit()
        log.append(f"Обновлены недостающие данные для {ticker}.")

    return log
