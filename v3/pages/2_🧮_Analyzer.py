from core.bootstrap import setup_environment

setup_environment()

import pandas as pd
import streamlit as st

from core import database, ui
from core.indicators import calculate_technical_indicators
from core.utils import open_database_connection

ui.page_header("Аналитика", "Просмотр рассчитанных технических индикаторов.", icon="🧮")

conn = open_database_connection()
source = database.mergeMetrDaily(conn)

if source.empty:
    st.warning("В базе нет рассчитанных данных. Загрузите историю и выполните обновление индикаторов.")
    st.stop()

source["date"] = pd.to_datetime(source["date"], errors="coerce")
source = source.sort_values(["contract_code", "date"])

st.sidebar.markdown("### Тикер")
tickers = sorted(source["contract_code"].dropna().unique())
selected_ticker = st.sidebar.selectbox("Выберите инструмент", options=tickers)

st.sidebar.caption("Набор данных берётся из таблицы metric_daily.")

ticker_data = source[source["contract_code"] == selected_ticker].copy()
if ticker_data.empty:
    st.info("Нет строк для выбранного тикера.")
    st.stop()

calculated = calculate_technical_indicators(ticker_data, contract_code=selected_ticker)
calculated = calculated.sort_values("date")

ui.section_title("Последние значения", "30 последних строк")
st.dataframe(calculated.tail(30), use_container_width=True)

ui.section_title("RSI и ATR")
metrics = calculated.set_index("date")[[col for col in ("RSI", "ATR") if col in calculated.columns]].dropna(how="all")
if metrics.empty:
    st.info("Для выбранного тикера нет данных RSI/ATR.")
else:
    try:
        st.line_chart(metrics)
    except Exception:
        st.dataframe(metrics.tail(30), use_container_width=True)

ui.section_title("Сырые данные")
st.dataframe(ticker_data.tail(30), use_container_width=True)
