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
_add_paths()
# -----

import os
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html

st.title("📈 Lightweight Charts (Demo)")

DATA_DIR = Path("bar_data")

def load_bar_data(symbol: str, timeframe: str) -> pd.DataFrame:
    csv_path = DATA_DIR / f"{symbol}_{timeframe}.csv"
    if not csv_path.exists():
        st.warning(f"Файл не найден: {csv_path}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_path)
        # ожидаемые столбцы: time/open/high/low/close или date/... адаптируемся
        cols = {c.lower(): c for c in df.columns}
        # нормализация имен
        for need in ["time", "open", "high", "low", "close"]:
            if need not in cols:
                # попробуем альтернативы
                alt = "date" if need == "time" else need
                if alt in cols:
                    cols[need] = cols[alt]
        time_col = cols.get("time")
        if not time_col:
            st.error("В CSV отсутствует колонка времени (time/date)")
            return pd.DataFrame()
        out = pd.DataFrame({
            "time": pd.to_datetime(df[time_col]).dt.strftime("%Y-%m-%d"),
            "open": df[cols.get("open", "open")].astype(float),
            "high": df[cols.get("high", "high")].astype(float),
            "low": df[cols.get("low", "low")].astype(float),
            "close": df[cols.get("close", "close")].astype(float),
        })
        return out.dropna()
    except Exception as exc:
        st.error(f"Ошибка чтения CSV: {exc}")
        return pd.DataFrame()


colL, colR = st.columns([2, 1])
with colR:
    symbol = st.text_input("Symbol", value="TSLA")
    timeframe = st.selectbox("Timeframe", ("1min", "5min", "30min"), index=1)
    max_points = st.slider("Баров на графике", 20, 500, 180)

with colL:
    df = load_bar_data(symbol, timeframe)
    if df.empty:
        st.info("Загрузите CSV в папку bar_data в формате <SYMBOL>_<TIMEFRAME>.csv")
    else:
        df = df.sort_values("time").tail(max_points)
        # Генерируем HTML на основе lightweight-charts
        try:
            import json as _json
            data_json = _json.dumps(df.to_dict(orient="records"))
            lwc_html = f"""
            <div id=\"lwc_container\" style=\"height:480px;\"></div>
            <script src=\"https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js\"></script>
            <script>
              const container = document.getElementById('lwc_container');
              const chart = LightweightCharts.createChart(container, {{
                width: container.clientWidth,
                height: 480,
                layout: {{ background: {{ type: 'solid', color: 'white' }}, textColor: '#222' }},
                grid: {{ vertLines: {{ visible: false }}, horzLines: {{ color: '#eee' }} }},
                timeScale: {{ timeVisible: true, secondsVisible: false }},
              }});
              const series = chart.addCandlestickSeries({{
                upColor: '#22c55e', downColor: '#ef4444', borderUpColor: '#16a34a', borderDownColor: '#b91c1c', wickUpColor: '#16a34a', wickDownColor: '#b91c1c'
              }});
              const data = {data_json};
              series.setData(data);
              new ResizeObserver(entries => {{
                for (let entry of entries) {{
                  chart.applyOptions({{ width: entry.contentRect.width }});
                }}
              }}).observe(container);
            </script>
            """
            html(lwc_html, height=500, scrolling=False)
        except Exception as exc:
            st.error(f"Ошибка рендеринга lightweight-charts: {exc}")

st.caption("Файлы CSV ожидаются в `bar_data/` как `<SYMBOL>_<TIMEFRAME>.csv`.")



