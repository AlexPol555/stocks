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
from streamlit_lightweight_charts import renderLightweightCharts  # type: ignore

import core.database as database
from core.indicators import clear_get_calculated_data, get_calculated_data
from core.utils import extract_selected_rows
from core.visualization import plot_daily_analysis, plot_stock_analysis
from core import demo_trading

def _fmt_money(value) -> str:
    try:
        return format(float(value), ',.2f').replace(',', ' ')
    except Exception:
        return str(value)

st.title("📊 Dashboard")

# AgGrid guard
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
except Exception:
    def AgGrid(df, gridOptions=None, height=400, fit_columns_on_grid_load=True, **kwargs):
        st.dataframe(df, use_container_width=True, height=height)
        return {"selected_rows": []}
    class GridOptionsBuilder:
        def __init__(self, df=None): self._opts = {}
        @staticmethod
        def from_dataframe(df): return GridOptionsBuilder(df)
        def configure_selection(self, **kwargs): return self
        def configure_pagination(self, **kwargs): return self
        def configure_default_column(self, **kwargs): return self
        def configure_column(self, *args, **kwargs): return self
        def build(self): return self._opts
    class _Enum: pass
    GridUpdateMode = _Enum(); GridUpdateMode.SELECTION_CHANGED = None
    DataReturnMode = _Enum(); DataReturnMode.FILTERED_AND_SORTED = None
    def JsCode(x): return x

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

if df_all is None or df_all.empty:
    st.info("Нет данных."); st.stop()

account_snapshot = demo_trading.get_account_snapshot(conn)
account_info_demo = demo_trading.get_account(conn)
account_currency = account_info_demo.get("currency", "RUB")

acct_cols = st.columns(4)
acct_cols[0].metric("Свободный баланс", f"{_fmt_money(account_snapshot['balance'])} {account_currency}")
acct_cols[1].metric("Инвестировано", f"{_fmt_money(account_snapshot['invested_value'])} {account_currency}")
acct_cols[2].metric("Рыночная стоимость", f"{_fmt_money(account_snapshot['market_value'])} {account_currency}")
acct_cols[3].metric("Equity", f"{_fmt_money(account_snapshot['equity'])} {account_currency}")

pl_cols = st.columns(3)
pl_cols[0].metric("Реализованный P/L", f"{_fmt_money(account_snapshot['realized_pl'])} {account_currency}")
pl_cols[1].metric("Нереализованный P/L", f"{_fmt_money(account_snapshot['unrealized_pl'])} {account_currency}")
pl_cols[2].metric("Итоговый P/L", f"{_fmt_money(account_snapshot['total_pl'])} {account_currency}")
st.caption("Показатели демо счёта обновляются при каждой сделке.")

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

# Таблица (минималистичный вид, сортировка по дате, пагинация)
display_columns = [
    "date",
    "contract_code",
    "close",
    "RSI",
    "ATR",
    "Signal",
    "Adaptive_Buy_Signal",
    "Adaptive_Sell_Signal",
    "New_Adaptive_Buy_Signal",
    "New_Adaptive_Sell_Signal",
]
present_columns = [c for c in display_columns if c in filtered_df.columns]
df_display = filtered_df[present_columns].copy()
if "date" in df_display.columns:
    try:
        df_display["date"] = pd.to_datetime(df_display["date"]).dt.date
        df_display = df_display.sort_values("date", ascending=False)
    except Exception:
        pass
df_display = df_display.drop_duplicates()

gb = GridOptionsBuilder.from_dataframe(df_display)
try:
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)
    gb.configure_default_column(groupable=False, filter=True, resizable=True, sortable=True)
    # Заголовки без переименования колонок в DataFrame
    headers = {
        "date": "Дата",
        "contract_code": "Тикер",
        "close": "Цена",
        "RSI": "RSI",
        "ATR": "ATR",
        "Signal": "Базовый сигнал",
        "Adaptive_Buy_Signal": "Adaptive Buy",
        "Adaptive_Sell_Signal": "Adaptive Sell",
        "New_Adaptive_Buy_Signal": "New Adaptive Buy",
        "New_Adaptive_Sell_Signal": "New Adaptive Sell",
    }
    for key, title in headers.items():
        if key in df_display.columns:
            if key in ("close", "RSI", "ATR"):
                gb.configure_column(key, headerName=title, type=["numericColumn", "numberColumnFilter"], valueFormatter=JsCode("""function(params){
                    if(params.value === null || params.value === undefined) return '-';
                    var v = Number(params.value); return isNaN(v)? String(params.value): v.toFixed(2);
                }"""))
            else:
                gb.configure_column(key, headerName=title)
    # Подсветка сигналов
    highlight_js = JsCode("""function(params){
        if(params.value === 1){ return {backgroundColor:'#dcfce7', color:'#166534', fontWeight:'600'}; }
        if(params.value === -1){ return {backgroundColor:'#fee2e2', color:'#991b1b', fontWeight:'600'}; }
        return {};
    }""")
    for col in [c for c in ["Signal","Adaptive_Buy_Signal","Adaptive_Sell_Signal","New_Adaptive_Buy_Signal","New_Adaptive_Sell_Signal"] if c in df_display.columns]:
        gb.configure_column(col, cellStyle=highlight_js, width=140)
    gridOptions = gb.build()
except Exception:
    gridOptions = {}

grid_response = AgGrid(
    df_display,
    gridOptions=gridOptions,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    theme="alpine",
    allow_unsafe_jscode=True,
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
        metrics_df = database.load_data_from_db(conn)
    except Exception:
        metrics_df = pd.DataFrame()

    ticker_metrics = (
        metrics_df[metrics_df["contract_code"] == selected_ticker].copy()
        if isinstance(metrics_df, pd.DataFrame) and not metrics_df.empty
        else pd.DataFrame()
    )

    overview_col, chart_col = st.columns(2)
    with overview_col:
        st.markdown("## Карточка тикера")

        m1, m2, m3 = st.columns(3)
        m1.metric("Тикер", selected.get("contract_code", "-"))
        m2.metric("Дата", str(selected.get("date", "-")))
        m3.metric("Закрытие", f"{selected.get('close', 'N/A')}")

        m4, m5, m6 = st.columns(3)
        rsi_val = selected.get("RSI")
        atr_val = selected.get("ATR")
        fbs = selected.get("Final_Buy_Signal", "N/A")
        m4.metric("RSI", "N/A" if pd.isna(rsi_val) else f"{rsi_val:.2f}" if isinstance(rsi_val, (int, float)) else str(rsi_val))
        m5.metric("ATR", "N/A" if pd.isna(atr_val) else f"{atr_val:.2f}" if isinstance(atr_val, (int, float)) else str(atr_val))
        m6.metric("Final Buy Signal", str(fbs))

        chips = []
        if selected.get('Signal') == 1:
            chips.append(("Основной Buy", "#16a34a"))
        elif selected.get('Signal') == -1:
            chips.append(("Основной Sell", "#dc2626"))
        if selected.get('Adaptive_Buy_Signal') == 1:
            chips.append(("Adaptive Buy", "#0ea5e9"))
        elif selected.get('Adaptive_Sell_Signal') == 1:
            chips.append(("Adaptive Sell", "#f59e0b"))
        if selected.get('New_Adaptive_Buy_Signal') == 1:
            chips.append(("New Adaptive Buy", "#8b5cf6"))
        elif selected.get('New_Adaptive_Sell_Signal') == 1:
            chips.append(("New Adaptive Sell", "#a16207"))

        if chips:
            chips_html = " ".join([
                f"<span style='background:{color};color:white;padding:3px 8px;border-radius:12px;margin-right:6px;font-size:12px;'>{txt}</span>"
                for txt, color in chips
            ])
            st.markdown(f"Сигналы: {chips_html}", unsafe_allow_html=True)
        else:
            st.info("Сигналы отсутствуют для выбранной строки.")

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

        with st.expander("Данные выбранной строки"):
            st.json(selected)

        st.markdown("## Торговая панель (демо)")
        default_price = selected.get("close")
        try:
            default_price = float(default_price)
        except (TypeError, ValueError):
            default_price = 0.0
        available_balance = account_snapshot.get("balance", 0.0)
        st.caption(f"Свободный баланс: {_fmt_money(available_balance)} {account_currency}")
        with st.form(f"demo_trade_form_{selected_ticker}"):
            trade_cols = st.columns(3)
            with trade_cols[0]:
                trade_side = st.radio("Сторона", ("BUY", "SELL"), horizontal=True, key=f"trade_side_{selected_ticker}")
            with trade_cols[1]:
                quantity = st.number_input("Количество", min_value=1, value=1, step=1, key=f"trade_qty_{selected_ticker}")
            with trade_cols[2]:
                trade_price = st.number_input("Цена", min_value=0.0, value=default_price if default_price else 0.0, format="%.2f", key=f"trade_price_{selected_ticker}")
            try:
                estimated_value = float(quantity) * float(trade_price)
            except Exception:
                estimated_value = 0.0
            st.caption(f"Объём сделки: {_fmt_money(estimated_value)} {account_currency}")
            submit_trade = st.form_submit_button("Исполнить сделку")
            if submit_trade:
                if trade_price <= 0:
                    st.warning("Цена должна быть больше 0.")
                else:
                    try:
                        result = demo_trading.place_trade(conn, selected_ticker, trade_side, float(quantity), float(trade_price))
                    except Exception as exc:
                        st.error(f"Не удалось выполнить сделку: {exc}")
                    else:
                        if result.status == "success":
                            st.success(f"Сделка выполнена. Новый баланс: {_fmt_money(result.balance)} {account_currency}")
                            st.experimental_rerun()
                        elif result.status == "error":
                            st.error(result.message)
                        else:
                            st.warning(result.message)

    with chart_col:
        st.markdown("## RSI / ATR динамика")
        try:
            df_ticker = df_all[df_all["contract_code"] == selected_ticker].copy()
            df_ticker["date"] = pd.to_datetime(df_ticker["date"])
            metrics = df_ticker.sort_values("date").tail(360)
            cols = [c for c in ["RSI", "ATR"] if c in metrics.columns]
            if not cols:
                st.info("Недостаточно данных для построения графика.")
            else:
                try:
                    import plotly.graph_objects as go  # type: ignore
                    fig = go.Figure()
                    for col in cols:
                        fig.add_trace(go.Scatter(x=metrics["date"], y=metrics[col], mode="lines", name=col))
                    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    st.line_chart(metrics.set_index("date")[cols])
        except Exception:
            st.info("Недостаточно данных для построения графика.")

        st.markdown("## График цен")
        try:
            ohlc_all = database.load_daily_data_from_db(conn)
            ohlc = ohlc_all[ohlc_all["contract_code"] == selected_ticker].copy() if not ohlc_all.empty else pd.DataFrame()
            if ohlc.empty:
                st.info("Нет OHLC-данных для выбранного тикера.")
            else:
                ohlc["date"] = pd.to_datetime(ohlc["date"])
                ohlc = ohlc.sort_values("date").tail(180)
                candle_data = [
                    {
                        "time": dt.strftime("%Y-%m-%d"),
                        "open": float(op),
                        "high": float(hh),
                        "low": float(ll),
                        "close": float(cl),
                    }
                    for dt, op, hh, ll, cl in zip(ohlc["date"], ohlc["open"], ohlc["high"], ohlc["low"], ohlc["close"])
                ]
                chart_config = [
                    {
                        "chart": {
                            "height": 360,
                            "layout": {"background": {"type": "solid", "color": "#ffffff"}, "textColor": "#1f2933"},
                            "grid": {"vertLines": {"visible": False}, "horzLines": {"color": "#e5e7eb"}},
                            "rightPriceScale": {"borderVisible": False},
                            "timeScale": {"timeVisible": True, "secondsVisible": False},
                        },
                        "series": [
                            {
                                "type": "Candlestick",
                                "data": candle_data,
                                "options": {
                                    "upColor": "#26a69a",
                                    "downColor": "#ef5350",
                                    "wickUpColor": "#26a69a",
                                    "wickDownColor": "#ef5350",
                                    "borderVisible": False,
                                },
                            }
                        ],
                    }
                ]
                try:
                    renderLightweightCharts(chart_config, key=f"lwch_{selected_ticker}")
                except Exception:
                    try:
                        import plotly.graph_objects as go  # type: ignore
                        fig = go.Figure(data=[
                            go.Candlestick(
                                x=ohlc["date"],
                                open=ohlc["open"],
                                high=ohlc["high"],
                                low=ohlc["low"],
                                close=ohlc["close"],
                                name="OHLC"
                            )
                        ])
                        fig.update_layout(xaxis_rangeslider_visible=True, margin=dict(l=0, r=0, t=10, b=0), height=360)
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        st.line_chart(ohlc.set_index("date")[ ["close"] ])
        except Exception:
            st.warning("Не удалось загрузить ценовые данные.")

    if ticker_metrics.empty:
        st.info("Нет записей по метрикам для выбранного тикера.")
    else:
        try:
            ticker_metrics["date"] = pd.to_datetime(ticker_metrics["date"], errors="coerce")
        except Exception:
            pass
        filtered_df_1 = (
            ticker_metrics[ticker_metrics["metric_type"] == "Изменение"]
            .sort_values("date", ascending=False)
            .head(10)
        )
        filtered_df_2 = (
            ticker_metrics[ticker_metrics["metric_type"] == "Открытые позиции"]
            .sort_values("date", ascending=False)
            .head(10)
        )
        colL, colR = st.columns(2)
        with colL:
            st.markdown("### Последние Изменения")
            st.dataframe(filtered_df_1, use_container_width=True)
        with colR:
            st.markdown("### Открытые позиции")
            st.dataframe(filtered_df_2, use_container_width=True)

else:
    st.info("Выбери строку в таблице.")
st.divider()
st.subheader("Демо сделки и позиции")
trades_df = demo_trading.get_trades(conn)
positions_df = demo_trading.get_positions(conn)
tab_trades, tab_positions = st.tabs(["История сделок", "Открытые позиции"])
with tab_trades:
    if trades_df.empty:
        st.info("История сделок пуста.")
    else:
        trades_view = trades_df.copy()
        try:
            trades_view["executed_at"] = pd.to_datetime(trades_view["executed_at"], errors="coerce")
            trades_view["executed_at"] = trades_view["executed_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        st.dataframe(trades_view, use_container_width=True)
        try:
            summary = trades_df.groupby("contract_code", as_index=False)[["quantity", "value", "realized_pl"]].sum()
            summary_cols = st.columns(3)
            summary_cols[0].metric("Сделок", f"{len(trades_df)}")
            summary_cols[1].metric("Общий объём", _fmt_money(summary["value"].sum()))
            summary_cols[2].metric("Реализованный P/L", _fmt_money(trades_df["realized_pl"].sum()))
            st.caption("Сводка по всем тикерам (значения в валюте счёта).")
            st.dataframe(summary, use_container_width=True)
        except Exception:
            pass
with tab_positions:
    if positions_df.empty:
        st.info("Открытые позиции отсутствуют.")
    else:
        positions_view = positions_df.copy()
        numeric_cols = ["quantity", "avg_price", "invested_value", "market_price", "market_value", "unrealized_pl", "realized_pl"]
        for col in numeric_cols:
            if col in positions_view.columns:
                positions_view[col] = positions_view[col].astype(float)
        st.dataframe(positions_view, use_container_width=True)
        st.caption("В колонках показаны оценочные значения демо-портфеля.")


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

st.button("Очистить кэш индикаторов", on_click=clear_get_calculated_data)
st.markdown("## Сводка по тикерам")
st.write(df_signals.groupby('contract_code').sum(numeric_only=True).reset_index())
