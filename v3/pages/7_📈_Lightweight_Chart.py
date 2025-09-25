from pathlib import Path

from core.bootstrap import setup_environment

setup_environment()

import json

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html

from core import ui

ui.page_header("Лёгкие графики", "Эксперименты с библиотекой lightweight-charts.", icon="📈")

DATA_DIR = Path("bar_data")


def load_bar_data(symbol: str, timeframe: str) -> pd.DataFrame:
    csv_path = DATA_DIR / f"{symbol}_{timeframe}.csv"
    if not csv_path.exists():
        st.warning(f"Файл не найден: {csv_path}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_path)
        cols = {c.lower(): c for c in df.columns}
        for required in ["time", "open", "high", "low", "close"]:
            if required not in cols:
                alt = "date" if required == "time" else required
                if alt in cols:
                    cols[required] = cols[alt]
        time_col = cols.get("time")
        if not time_col:
            st.error("В CSV отсутствует столбец с датой/временем.")
            return pd.DataFrame()
        out = pd.DataFrame({
            "time": pd.to_datetime(df[cols.get("time", time_col)]).dt.strftime("%Y-%m-%d"),
            "open": df[cols.get("open", "open")].astype(float),
            "high": df[cols.get("high", "high")].astype(float),
            "low": df[cols.get("low", "low")].astype(float),
            "close": df[cols.get("close", "close")].astype(float),
        })
        return out.dropna()
    except Exception as exc:
        st.error(f"Ошибка чтения CSV: {exc}")
        return pd.DataFrame()


col_chart, col_controls = st.columns([2, 1])

with col_controls:
    symbol = st.text_input("Тикер", value="TSLA").upper()
    timeframe = st.selectbox("Таймфрейм", ("1min", "5min", "30min"), index=1)
    max_points = st.slider("Количество свечей", 20, 500, 180)
    st.caption("Поместите CSV в каталог ar_data/ с именем <TICKER>_<TF>.csv.")

with col_chart:
    df = load_bar_data(symbol, timeframe)
    if df.empty:
        st.info("Загрузите CSV с баровыми данными, чтобы увидеть график.")
    else:
        df = df.sort_values("time").tail(max_points)
        chart_html = f"""
        <div id='lwc_container' style='height:480px;'></div>
        <script src='https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js'></script>
        <script>
          const container = document.getElementById('lwc_container');
          const chart = LightweightCharts.createChart(container, {{
            width: container.clientWidth,
            height: 480,
            layout: {{ background: {{ type: 'solid', color: '#ffffff' }}, textColor: '#1f2933' }},
            grid: {{ vertLines: {{ visible: false }}, horzLines: {{ color: '#e5e7eb' }} }},
            rightPriceScale: {{ borderVisible: false }},
            timeScale: {{ timeVisible: true, secondsVisible: false }}
          }});
          const series = chart.addCandlestickSeries({{
            upColor: '#22c55e', downColor: '#ef4444',
            borderUpColor: '#16a34a', borderDownColor: '#b91c1c',
            wickUpColor: '#16a34a', wickDownColor: '#b91c1c'
          }});
          series.setData({json.dumps(df.to_dict(orient='records'))});
          new ResizeObserver(entries => {{
            for (const entry of entries) {{
              chart.applyOptions({{ width: entry.contentRect.width }});
            }}
          }}).observe(container);
        </script>
        """
        html(chart_html, height=500, scrolling=False)
