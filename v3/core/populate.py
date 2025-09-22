"""Helpers for filling the SQLite database from CSV files."""
from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "Contract Code",
    "Metric",
    "Value1",
    "Value2",
    "Value3",
    "Value4",
    "Value5",
    "Date",
}


def _read_csv(csv_path_or_buffer: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path_or_buffer)
    except Exception as exc:
        raise ValueError(f"Ошибка при чтении CSV: {exc}") from exc

    first_column = df.columns[0]
    if first_column.startswith("Unnamed"):
        df = df.drop(columns=first_column)
    return df


def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if not REQUIRED_COLUMNS.issubset(df.columns):
        missing = REQUIRED_COLUMNS - set(df.columns)
        raise ValueError(f"Отсутствуют обязательные столбцы: {missing}")

    df = df.copy()
    df["Contract Code"] = df["Contract Code"].str.split("-").str[0]
    df["Date"] = pd.to_datetime(df["Date"]) - pd.Timedelta(days=1)
    return df[df["Date"].dt.weekday < 5]


def _ensure_companies(conn, companies: Iterable[str]) -> dict:
    cursor = conn.cursor()
    for code in companies:
        cursor.execute("INSERT OR IGNORE INTO companies (contract_code) VALUES (?)", (code,))
    conn.commit()

    cursor.execute("SELECT id, contract_code FROM companies")
    return {row[1]: row[0] for row in cursor.fetchall()}


def _insert_metrics(conn, df: pd.DataFrame, comp_map: dict) -> None:
    cursor = conn.cursor()
    for _, row in df.iterrows():
        company_id = comp_map.get(row["Contract Code"])
        if company_id is None:
            continue
        cursor.execute(
            """
            INSERT INTO metrics (company_id, metric_type, value1, value2, value3, value4, value5, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_id,
                row["Metric"],
                row["Value1"],
                row["Value2"],
                row["Value3"],
                row["Value4"],
                row["Value5"],
                row["Date"].strftime("%Y-%m-%d"),
            ),
        )
    conn.commit()


def bulk_populate_database_from_csv(csv_path_or_buffer: str, conn) -> None:
    df = _prepare_dataframe(_read_csv(csv_path_or_buffer))
    comp_map = _ensure_companies(conn, df["Contract Code"].unique())
    logger.debug("Карта компаний: %s", comp_map)
    _insert_metrics(conn, df, comp_map)


def incremental_populate_database_from_csv(csv_path_or_buffer: str, conn) -> None:
    df = _prepare_dataframe(_read_csv(csv_path_or_buffer))
    comp_map = _ensure_companies(conn, df["Contract Code"].unique())
    logger.debug("Карта компаний: %s", comp_map)
    _insert_metrics(conn, df, comp_map)
