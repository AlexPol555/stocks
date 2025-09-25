import logging
import os
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from . import database
from .settings import get_settings
from .analyzer import StockAnalyzer
from .jobs.auto_update import auto_update_all_tickers
from .parser import run_moex_parser
from .populate import incremental_populate_database_from_csv

logger = logging.getLogger(__name__)

# -------- secrets/env --------
def _secrets_dict() -> Dict[str, Any]:
    try:
        s = st.secrets
        return dict(s) if isinstance(s, dict) else {k: s[k] for k in list(s.keys())}
    except Exception:
        return {}

def _secret_get(path, default=None):
    d = _secrets_dict()
    if isinstance(path, str):
        return d.get(path, default)
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

def read_api_key() -> Optional[str]:
    return (
        os.getenv("TINKOFF_API_KEY")
        or _secret_get("TINKOFF_API_KEY")
        or _secret_get(["tinkoff", "api_key"])
    )

def read_db_path() -> str:
    return str(get_settings().database_path)

# -------- db connection (WAL) --------
def open_database_connection():
    settings = get_settings()
    conn = database.get_connection(settings.database_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception:
        logger.exception("Failed to configure SQLite pragmas")
    return conn

# -------- jobs (manual trigger only) --------
def run_api_update_job(full_update: bool = True):
    try:
        job_conn = open_database_connection()
        job_analyzer = StockAnalyzer(read_api_key(), db_conn=job_conn)
        logs = auto_update_all_tickers(job_analyzer, job_conn, full_update=full_update)
        job_conn.close()
        return logs
    except Exception as e:
        return [f"Ошибка в run_api_update_job: {e}"]


def run_parser_incremental_job():
    try:
        conn = open_database_connection()
        df = run_moex_parser()
        if df.empty:
            conn.close()
            return ["Парсер не вернул данных (df.empty)."]
        # пишем в БД инкрементально через существующую логику CSV-пайплайна
        # используем временный CSV через буфер
        from io import StringIO
        buffer = StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        incremental_populate_database_from_csv(buffer, conn)
        conn.close()
        return [f"Импортировано строк: {len(df)}"]
    except Exception as e:
        return [f"Ошибка в run_parser_incremental_job: {e}"]

# -------- diagnostics --------
def db_health_check(conn):
    with conn:
        def q(sql, params=()):
            try:
                return pd.read_sql_query(sql, conn, params=params)
            except Exception as e:
                return f"SQL error: {e}"
        st.subheader("Tables")
        st.write(q("SELECT name FROM sqlite_master WHERE type='table';"))
        st.subheader("Counts")
        for t in ['companies','daily_data','metrics','company_parameters']:
            try:
                cnt = pd.read_sql_query(f"SELECT COUNT(*) AS cnt FROM {t};", conn).iloc[0]['cnt']
            except Exception:
                cnt = "no table"
            st.write(f"{t}: {cnt}")

# -------- AgGrid helper --------
def extract_selected_rows(grid_response):
    try:
        if isinstance(grid_response, dict):
            return grid_response.get("selected_rows", grid_response.get("data", None))
        if hasattr(grid_response, "selected_rows"):
            return getattr(grid_response, "selected_rows")
        if hasattr(grid_response, "data"):
            return getattr(grid_response, "data")
        if isinstance(grid_response, list):
            return grid_response
    except Exception as e:
        logger.exception("extract_selected_rows error: %s", e)
    return None
