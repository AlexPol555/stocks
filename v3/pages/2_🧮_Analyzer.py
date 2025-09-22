# bootstrap
from pathlib import Path
import sys
def _add_paths():
    here = Path(__file__).resolve()
    root = here.parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    for sub in ("core", "services"):
        ep = root / sub
        if ep.exists() and str(ep) not in sys.path:
            sys.path.insert(0, str(ep))
    parent = root.parent
    if parent and str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
_add_paths()
# -----

import pandas as pd
import streamlit as st

from core import database
from core.indicators import calculate_technical_indicators
from core.utils import open_database_connection

st.title("🧮 Analyzer")

conn = open_database_connection()
source = database.mergeMetrDaily(conn)

if source.empty:
    st.warning("В базе нет данных для анализа. Загрузите котировки на странице Data Load.")
    st.stop()

tickers = sorted(source["contract_code"].dropna().unique())
selected_ticker = st.selectbox("Тикер", tickers)

ticker_data = source[source["contract_code"] == selected_ticker].copy()
if ticker_data.empty:
    st.info("Для выбранного тикера нет строк.")
    st.stop()

ticker_data["date"] = pd.to_datetime(ticker_data["date"])
calculated = calculate_technical_indicators(ticker_data)

st.subheader("Последние значения индикаторов")
st.dataframe(calculated.sort_values("date").tail(30), use_container_width=True)

st.subheader("RSI / ATR динамика")
metrics = calculated.set_index("date")[["RSI", "ATR"]].dropna()
if metrics.empty:
    st.info("Недостаточно данных для построения графиков.")
else:
    st.line_chart(metrics)
