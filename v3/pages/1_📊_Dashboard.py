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

import streamlit as st
import pandas as pd
import numpy as np

import core.database as database
from core.indicators import clear_get_calculated_data, get_calculated_data
from core.utils import extract_selected_rows
from core.visualization import plot_daily_analysis, plot_stock_analysis

st.title("📊 Dashboard")

# AgGrid guard
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
except Exception:
    def AgGrid(df, gridOptions=None, height=400, fit_columns_on_grid_load=True, **kwargs):
        st.dataframe(df, use_container_width=True, height=height)
        return {"selected_rows": []}
    class GridOptionsBuilder:
        def __init__(self, df=None): self._opts = {}
        @staticmethod
        def from_dataframe(df): return GridOptionsBuilder(df)
        def configure_selection(self, **kwargs): return self
        def build(self): return self._opts
    class _Enum: pass
    GridUpdateMode = _Enum(); GridUpdateMode.SELECTION_CHANGED = None
    DataReturnMode = _Enum(); DataReturnMode.FILTERED_AND_SORTED = None

# DB connect
conn = None
try:
    conn = database.get_connection()
except Exception:
    try:
        conn = database.get_conn()
    except Exception:
        pass
if not conn:
    st.error("No database connection. Check database.py get_connection/get_conn.")
    st.stop()

df_all = get_calculated_data(conn)
st.button("Очистить кэш индикаторов", on_click=clear_get_calculated_data)

if df_all is None or df_all.empty:
    st.info("Нет данных."); st.stop()

# Фильтры
unique_dates = sorted(list(df_all["date"].unique()), reverse=True)
tickers = df_all["contract_code"].unique()

filter_type = st.sidebar.radio("Фильтровать по:", ("По дате", "По тикеру", "Без фильтра"))
if filter_type == "По дате":
    selected_date = st.sidebar.selectbox("Дата", unique_dates)
    filtered_df = df_all[df_all["date"] == selected_date].copy()
elif filter_type == "По тикеру":
    selected_ticker = st.sidebar.selectbox("Тикер", tickers)
    filtered_df = df_all[df_all["contract_code"] == selected_ticker].copy()
else:
    filtered_df = df_all.copy()

# Чекбоксы сигналов
col1, col2, col3, col4 = st.columns(4)
adaptive_buy = col1.checkbox("Adaptive Buy", value=True)
adaptive_sell = col2.checkbox("Adaptive Sell", value=True)
new_adaptive_buy = col3.checkbox("New Adaptive Buy", value=True)
new_adaptive_sell = col4.checkbox("New Adaptive Sell", value=True)

mask = pd.Series(False, index=filtered_df.index)
if adaptive_buy and 'Adaptive_Buy_Signal' in filtered_df.columns:
    mask |= (filtered_df['Adaptive_Buy_Signal'] == 1)
if adaptive_sell and 'Adaptive_Sell_Signal' in filtered_df.columns:
    mask |= (filtered_df['Adaptive_Sell_Signal'] == 1)
if new_adaptive_buy and 'New_Adaptive_Buy_Signal' in filtered_df.columns:
    mask |= (filtered_df['New_Adaptive_Buy_Signal'] == 1)
if new_adaptive_sell and 'New_Adaptive_Sell_Signal' in filtered_df.columns:
    mask |= (filtered_df['New_Adaptive_Sell_Signal'] == 1)
if mask.any():
    filtered_df = filtered_df[mask]

# Таблица
gb = GridOptionsBuilder.from_dataframe(filtered_df)
try:
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gridOptions = gb.build()
except Exception:
    gridOptions = {}

filtered_df = filtered_df.drop_duplicates()
grid_response = AgGrid(
    filtered_df,
    gridOptions=gridOptions,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    theme="alpine",
    height=520,
)

# Детали выбранной строки
selected_rows_raw = extract_selected_rows(grid_response)
selected = None
if selected_rows_raw is not None:
    if isinstance(selected_rows_raw, pd.DataFrame) and not selected_rows_raw.empty:
        selected = selected_rows_raw.iloc[0].to_dict()
    elif isinstance(selected_rows_raw, list) and len(selected_rows_raw) > 0:
        first = selected_rows_raw[0]
        if isinstance(first, pd.Series): selected = first.to_dict()
        elif isinstance(first, dict): selected = first
        else:
            try: selected = dict(first)
            except Exception: selected = None
    elif isinstance(selected_rows_raw, dict):
        selected = selected_rows_raw

if selected is not None:
    selected_ticker = selected.get("contract_code")
    st.sidebar.write(f"Выбран тикер: {selected_ticker}")

    try:
        data = database.load_data_from_db(conn)
    except Exception:
        data = pd.DataFrame()
    if data.empty:
        st.error("Нет данных для графика.")
    else:
        filtered_df_full = data[data['contract_code'] == selected_ticker].copy()
        # сортировка по дате: новые сначала, показывать только последние 10 строк
        try:
            filtered_df_full["date"] = pd.to_datetime(filtered_df_full["date"])  # безопасно для ISO дат
        except Exception:
            pass
        filtered_df_1 = (
            filtered_df_full[filtered_df_full["metric_type"] == "Изменение"]
            .sort_values("date", ascending=False)
            .head(10)
        )
        filtered_df_2 = (
            filtered_df_full[filtered_df_full["metric_type"] == "Открытые позиции"]
            .sort_values("date", ascending=False)
            .head(10)
        )
        colL, colR = st.columns(2)
        with colL: st.dataframe(filtered_df_1, use_container_width=True)
        with colR: st.dataframe(filtered_df_2, use_container_width=True)

    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown("## Информация о заявке")

        # Верхняя панель метрик
        m1, m2, m3 = st.columns(3)
        m1.metric("Тикер", selected.get("contract_code", "-"))
        m2.metric("Дата", str(selected.get("date", "-")))
        m3.metric("Цена закрытия", f"{selected.get('close', 'N/A')}")

        m4, m5, m6 = st.columns(3)
        rsi_val = selected.get("RSI")
        atr_val = selected.get("ATR")
        fbs = selected.get("Final_Buy_Signal", "N/A")
        m4.metric("RSI", "N/A" if pd.isna(rsi_val) else f"{rsi_val:.2f}" if isinstance(rsi_val, (int, float)) else str(rsi_val))
        m5.metric("ATR", "N/A" if pd.isna(atr_val) else f"{atr_val:.2f}" if isinstance(atr_val, (int, float)) else str(atr_val))
        m6.metric("Final Buy Signal", str(fbs))

        # Бейджи сигналов
        chips = []
        if selected.get('Signal') == 1: chips.append(("Базовый Buy", "#16a34a"))
        elif selected.get('Signal') == -1: chips.append(("Базовый Sell", "#dc2626"))
        if selected.get('Adaptive_Buy_Signal') == 1: chips.append(("Adaptive Buy", "#0ea5e9"))
        elif selected.get('Adaptive_Sell_Signal') == 1: chips.append(("Adaptive Sell", "#f59e0b"))
        if selected.get('New_Adaptive_Buy_Signal') == 1: chips.append(("New Adaptive Buy", "#8b5cf6"))
        elif selected.get('New_Adaptive_Sell_Signal') == 1: chips.append(("New Adaptive Sell", "#a16207"))

        if chips:
            html = " ".join([
                f"<span style='background:{color};color:white;padding:3px 8px;border-radius:12px;margin-right:6px;font-size:12px;'>{txt}</span>"
                for txt, color in chips
            ])
            st.markdown(f"Сигналы: {html}", unsafe_allow_html=True)
        else:
            st.info("Сигналы не сработали для этой строки.")

        # Краткая таблица по профиту/выходам для сработавших сигналов
        rows = []
        for label, flag, pcol, dcol, ecol in [
            ("Adaptive Buy", selected.get('Adaptive_Buy_Signal') == 1, 'Dynamic_Profit_Adaptive_Buy', 'Exit_Date_Adaptive_Buy', 'Exit_Price_Adaptive_Buy'),
            ("Adaptive Sell", selected.get('Adaptive_Sell_Signal') == 1, 'Dynamic_Profit_Adaptive_Sell', 'Exit_Date_Adaptive_Sell', 'Exit_Price_Adaptive_Sell'),
            ("New Adaptive Buy", selected.get('New_Adaptive_Buy_Signal') == 1, 'Dynamic_Profit_New_Adaptive_Buy', 'Exit_Date_New_Adaptive_Buy', 'Exit_Price_New_Adaptive_Buy'),
            ("New Adaptive Sell", selected.get('New_Adaptive_Sell_Signal') == 1, 'Dynamic_Profit_New_Adaptive_Sell', 'Exit_Date_New_Adaptive_Sell', 'Exit_Price_New_Adaptive_Sell'),
        ]:
            if flag:
                rows.append({
                    "Сигнал": label,
                    "Dynamic Profit": selected.get(pcol, 'N/A'),
                    "Exit Date": selected.get(dcol, 'N/A'),
                    "Exit Price": selected.get(ecol, 'N/A'),
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        
        with st.expander("Показать исходные данные строки"):
            st.json(selected)
else:
    st.info("Выбери строку в таблице.")

# Сводка сигналов
df_signals = df_all[
    (df_all.get('Adaptive_Buy_Signal', 0) == 1) |
    (df_all.get('Adaptive_Sell_Signal', 0) == 1) |
    (df_all.get('New_Adaptive_Buy_Signal', 0) == 1) |
    (df_all.get('New_Adaptive_Sell_Signal', 0) == 1)
].copy()

df_signals['Profit_Adaptive_Buy'] = np.where(df_signals.get('Adaptive_Buy_Signal', 0) == 1, df_signals.get('Dynamic_Profit_Adaptive_Buy', 0), 0)
df_signals['Profit_Adaptive_Sell'] = np.where(df_signals.get('Adaptive_Sell_Signal', 0) == 1, df_signals.get('Dynamic_Profit_Adaptive_Sell', 0), 0)
df_signals['Profit_New_Adaptive_Buy'] = np.where(df_signals.get('New_Adaptive_Buy_Signal', 0) == 1, df_signals.get('Dynamic_Profit_New_Adaptive_Buy', 0), 0)
df_signals['Profit_New_Adaptive_Sell'] = np.where(df_signals.get('New_Adaptive_Sell_Signal', 0) == 1, df_signals.get('Dynamic_Profit_New_Adaptive_Sell', 0), 0)

st.markdown("## Сводка по тикерам")
st.write(df_signals.groupby('contract_code').sum(numeric_only=True).reset_index())
