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

import numpy as np
import pandas as pd
import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts  # type: ignore

import core.database as database
from core import demo_trading, ui
from core.indicators import clear_get_calculated_data, get_calculated_data
from core.utils import extract_selected_rows


def _fmt_money(value) -> str:
    try:
        return format(float(value), ',.2f').replace(',', ' ')
    except Exception:
        return str(value)


def _fmt_number(value, digits: int = 2) -> str:
    if value is None:
        return "—"
    try:
        value = float(value)
    except Exception:
        return str(value)
    if np.isnan(value):
        return "—"
    fmt = f"{{:.{digits}f}}"
    return fmt.format(value)


ui.page_header(
    "Дашборд",
    "Живой срез сигналов, показателей индикаторов и операций демо-счёта.",
    icon="📊",
)

with st.sidebar:
    st.markdown("Фильтр данных")
    filter_mode = st.radio(
        "Показывать",
        ("По дате", "По тикеру", "Вся история"),
        index=0,
    )

    selected_date = None
    selected_ticker = None
    date_placeholder = st.empty()
    ticker_placeholder = st.empty()

    if filter_mode == "По дате":
        st.caption("Выберите торговый день")
    elif filter_mode == "По тикеру":
        st.caption("Выберите интересующий тикер")

    st.markdown("Сигналы")
    adaptive_buy = st.checkbox("Adaptive Buy", value=True)
    adaptive_sell = st.checkbox("Adaptive Sell", value=True)
    new_adaptive_buy = st.checkbox("New Adaptive Buy", value=True)
    new_adaptive_sell = st.checkbox("New Adaptive Sell", value=True)

    st.divider()
    st.button("Очистить кэш расчётов", on_click=clear_get_calculated_data, use_container_width=True)


conn = None
try:
    conn = database.get_connection()
except Exception:
    try:
        conn = database.get_conn()
    except Exception:
        conn = None

if not conn:
    st.error("Нет подключения к базе данных. Проверьте настройки в core/database.py.")
    st.stop()

df_all = get_calculated_data(conn)
if df_all is None or df_all.empty:
    st.info("Нет рассчитанных данных. Загрузите историю и выполните обновление индикаторов.")
    st.stop()

# populate sidebar selectors now that данные загружены
with st.sidebar:
    unique_dates = sorted(df_all["date"].dropna().unique(), reverse=True)

tickers = sorted(df_all["contract_code"].dropna().unique())
if filter_mode == "По дате" and unique_dates:
    selected_date = date_placeholder.selectbox("Дата", options=unique_dates, index=0)
elif filter_mode == "По тикеру" and tickers:
    selected_ticker = ticker_placeholder.selectbox("Тикер", options=tickers, index=0)

account_snapshot = demo_trading.get_account_snapshot(conn)
account_info = demo_trading.get_account(conn)
account_currency = account_info.get("currency", "RUB")

ui.section_title("Сводка демо-счёта", "метрики обновляются после операций")
acct_cols = st.columns(4)
acct_cols[0].metric("Свободный баланс", f"{_fmt_money(account_snapshot['balance'])} {account_currency}")
acct_cols[1].metric("Инвестировано", f"{_fmt_money(account_snapshot['invested_value'])} {account_currency}")
acct_cols[2].metric("Рыночная стоимость", f"{_fmt_money(account_snapshot['market_value'])} {account_currency}")
acct_cols[3].metric("Equity", f"{_fmt_money(account_snapshot['equity'])} {account_currency}")

pl_cols = st.columns(3)
pl_cols[0].metric("Реализованный P/L", f"{_fmt_money(account_snapshot['realized_pl'])} {account_currency}")
pl_cols[1].metric("Нереализованный P/L", f"{_fmt_money(account_snapshot['unrealized_pl'])} {account_currency}")
pl_cols[2].metric("Итоговый P/L", f"{_fmt_money(account_snapshot['total_pl'])} {account_currency}")
st.caption("Демо-счёт помогает проверить идеи перед реальными сделками.")

# применяем фильтры
filtered_df = df_all.copy()
if filter_mode == "По дате" and selected_date is not None:
    filtered_df = filtered_df[filtered_df["date"] == selected_date]
elif filter_mode == "По тикеру" and selected_ticker is not None:
    filtered_df = filtered_df[filtered_df["contract_code"] == selected_ticker]

signal_mask = pd.Series(False, index=filtered_df.index)
if adaptive_buy and 'Adaptive_Buy_Signal' in filtered_df.columns:
    signal_mask |= filtered_df['Adaptive_Buy_Signal'] == 1
if adaptive_sell and 'Adaptive_Sell_Signal' in filtered_df.columns:
    signal_mask |= filtered_df['Adaptive_Sell_Signal'] == 1
if new_adaptive_buy and 'New_Adaptive_Buy_Signal' in filtered_df.columns:
    signal_mask |= filtered_df['New_Adaptive_Buy_Signal'] == 1
if new_adaptive_sell and 'New_Adaptive_Sell_Signal' in filtered_df.columns:
    signal_mask |= filtered_df['New_Adaptive_Sell_Signal'] == 1
if signal_mask.any():
    filtered_df = filtered_df[signal_mask]

ui.section_title("Лента сигналов", "таблица поддерживает сортировку и поиск")

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
except Exception:
    def AgGrid(df, gridOptions=None, height=400, fit_columns_on_grid_load=True, **kwargs):  # type: ignore
        st.dataframe(df, use_container_width=True, height=height)
        return {"selected_rows": []}
    class GridOptionsBuilder:  # type: ignore
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
df_display = filtered_df[present_columns].drop_duplicates().copy()
if "date" in df_display.columns:
    try:
        df_display["date"] = pd.to_datetime(df_display["date"]).dt.date
        df_display = df_display.sort_values("date", ascending=False)
    except Exception:
        pass

column_titles = {
    "date": "Дата",
    "contract_code": "Тикер",
    "close": "Цена закрытия",
    "RSI": "RSI",
    "ATR": "ATR",
    "Signal": "Финальный сигнал",
    "Adaptive_Buy_Signal": "Adaptive Buy",
    "Adaptive_Sell_Signal": "Adaptive Sell",
    "New_Adaptive_Buy_Signal": "New Adaptive Buy",
    "New_Adaptive_Sell_Signal": "New Adaptive Sell",
}

gb = GridOptionsBuilder.from_dataframe(df_display)
try:
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)
    gb.configure_default_column(groupable=False, filter=True, resizable=True, sortable=True)
    format_js = JsCode(
        """function(params){
            if(params.value === null || params.value === undefined) return '—';
            const v = Number(params.value);
            if(isNaN(v)) return params.value;
            return v.toFixed(2);
        }"""
    )
    for key, title in column_titles.items():
        if key in df_display.columns:
            if key in ("close", "RSI", "ATR"):
                gb.configure_column(key, headerName=title, valueFormatter=format_js, type=["numericColumn"])
            else:
                gb.configure_column(key, headerName=title)
    highlight_js = JsCode(
        """function(params){
            if(params.value === 1){return {backgroundColor:'#dcfce7', color:'#166534', fontWeight:'600'};}
            if(params.value === -1){return {backgroundColor:'#fee2e2', color:'#b91c1c', fontWeight:'600'};}
            return {};
        }"""
    )
    for col in [c for c in column_titles if 'Signal' in c and c in df_display.columns]:
        gb.configure_column(col, cellStyle=highlight_js)
    grid_options = gb.build()
except Exception:
    grid_options = {}

grid_response = AgGrid(
    df_display,
    gridOptions=grid_options,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    theme="alpine",
    allow_unsafe_jscode=True,
    height=520,
)

selected_rows = extract_selected_rows(grid_response)
selected_row = None
if selected_rows is not None:
    if isinstance(selected_rows, pd.DataFrame) and not selected_rows.empty:
        selected_row = selected_rows.iloc[0].to_dict()
    elif isinstance(selected_rows, list) and selected_rows:
        first = selected_rows[0]
        if isinstance(first, pd.Series):
            selected_row = first.to_dict()
        elif isinstance(first, dict):
            selected_row = first
        else:
            try:
                selected_row = dict(first)
            except Exception:
                selected_row = None
    elif isinstance(selected_rows, dict):
        selected_row = selected_rows

if selected_row is not None:
    selected_ticker = selected_row.get("contract_code")
    ui.section_title("Карточка сигнала", selected_ticker or "—")

    overview_col, chart_col = st.columns([1, 1])
    with overview_col:
        info_cols = st.columns(3)
        info_cols[0].metric("Тикер", selected_row.get("contract_code", "—"))
        info_cols[1].metric("Дата", str(selected_row.get("date", "—")))
        info_cols[2].metric("Цена", _fmt_number(selected_row.get("close")))

        metric_cols = st.columns(3)
        metric_cols[0].metric("RSI", _fmt_number(selected_row.get("RSI")))
        metric_cols[1].metric("ATR", _fmt_number(selected_row.get("ATR")))
        metric_cols[2].metric("Финальный сигнал", str(selected_row.get("Signal", "—")))

        chips: list[tuple[str, str]] = []
        if selected_row.get("Signal") == 1:
            chips.append(("Сигнал: покупка", "positive"))
        elif selected_row.get("Signal") == -1:
            chips.append(("Сигнал: продажа", "negative"))
        if selected_row.get("Adaptive_Buy_Signal") == 1:
            chips.append(("Adaptive Buy", "positive"))
        if selected_row.get("Adaptive_Sell_Signal") == 1:
            chips.append(("Adaptive Sell", "negative"))
        if selected_row.get("New_Adaptive_Buy_Signal") == 1:
            chips.append(("New Adaptive Buy", "positive"))
        if selected_row.get("New_Adaptive_Sell_Signal") == 1:
            chips.append(("New Adaptive Sell", "negative"))
        if chips:
            ui.chip_row(chips)
        else:
            st.info("Для выбранной строки нет активных сигналов.")

        rows = []
        for label, flag, pcol, dcol, ecol in [
            ("Adaptive Buy", selected_row.get('Adaptive_Buy_Signal') == 1, 'Dynamic_Profit_Adaptive_Buy', 'Exit_Date_Adaptive_Buy', 'Exit_Price_Adaptive_Buy'),
            ("Adaptive Sell", selected_row.get('Adaptive_Sell_Signal') == 1, 'Dynamic_Profit_Adaptive_Sell', 'Exit_Date_Adaptive_Sell', 'Exit_Price_Adaptive_Sell'),
            ("New Adaptive Buy", selected_row.get('New_Adaptive_Buy_Signal') == 1, 'Dynamic_Profit_New_Adaptive_Buy', 'Exit_Date_New_Adaptive_Buy', 'Exit_Price_New_Adaptive_Buy'),
            ("New Adaptive Sell", selected_row.get('New_Adaptive_Sell_Signal') == 1, 'Dynamic_Profit_New_Adaptive_Sell', 'Exit_Date_New_Adaptive_Sell', 'Exit_Price_New_Adaptive_Sell'),
        ]:
            if flag:
                rows.append({
                    "Стратегия": label,
                    "Dynamic Profit": _fmt_number(selected_row.get(pcol), digits=1),
                    "Дата выхода": selected_row.get(dcol, "—"),
                    "Цена выхода": _fmt_number(selected_row.get(ecol)),
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

        with st.expander("Детали строки"):
            st.json(selected_row)

        st.markdown("### Сделка в демо-счёте")
        default_price = selected_row.get("close")
        try:
            default_price = float(default_price) if default_price is not None else 0.0
        except Exception:
            default_price = 0.0
        with st.form(f"demo_trade_form_{selected_ticker}"):
            trade_cols = st.columns(3)
            with trade_cols[0]:
                trade_side = st.radio("Направление", ("BUY", "SELL"), horizontal=True)
            with trade_cols[1]:
                quantity = st.number_input("Количество", min_value=1, value=1, step=1)
            with trade_cols[2]:
                trade_price = st.number_input("Цена", min_value=0.0, value=default_price, format="%.2f")
            estimated_value = float(quantity) * float(trade_price)
            st.caption(f"Стоимость сделки: {_fmt_money(estimated_value)} {account_currency}")
            if st.form_submit_button("Создать сделку"):
                if trade_price <= 0:
                    st.warning("Цена должна быть больше нуля.")
                else:
                    try:
                        result = demo_trading.place_trade(conn, selected_ticker, trade_side, float(quantity), float(trade_price))
                    except Exception as exc:
                        st.error(f"Ошибка при создании сделки: {exc}")
                    else:
                        if result.status == "success":
                            st.success(f"Сделка проведена. Баланс: {_fmt_money(result.balance)} {account_currency}")
                            st.experimental_rerun()
                        elif result.status == "error":
                            st.error(result.message)
                        else:
                            st.warning(result.message)

    with chart_col:
        st.markdown("### RSI и ATR")
        try:
            df_ticker = df_all[df_all["contract_code"] == selected_ticker].copy()
            df_ticker["date"] = pd.to_datetime(df_ticker["date"])
            metrics = df_ticker.sort_values("date").tail(360)
            metric_cols = [c for c in ["RSI", "ATR"] if c in metrics.columns]
            if not metric_cols:
                st.info("Нет данных RSI/ATR для отображения.")
            else:
                try:
                    import plotly.graph_objects as go  # type: ignore
                    fig = go.Figure()
                    for col in metric_cols:
                        fig.add_trace(go.Scatter(x=metrics["date"], y=metrics[col], mode="lines", name=col))
                    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    st.line_chart(metrics.set_index("date")[metric_cols])
        except Exception:
            st.info("Не удалось подготовить данные для графика RSI/ATR.")

        st.markdown("### Свечи (180 дней)")
        try:
            ohlc_source = database.load_daily_data_from_db(conn)
            ohlc = ohlc_source[ohlc_source["contract_code"] == selected_ticker].copy() if not ohlc_source.empty else pd.DataFrame()
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
                                name="OHLC",
                            )
                        ])
                        fig.update_layout(xaxis_rangeslider_visible=True, margin=dict(l=0, r=0, t=10, b=0), height=360)
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        st.line_chart(ohlc.set_index("date")["close"])
        except Exception:
            st.warning("График не удалось построить — проверьте корректность исторических данных.")
else:
    st.info("Выберите строку в таблице, чтобы увидеть детали сигнала и графики.")

st.divider()
ui.section_title("Демо-операции")
trades_df = demo_trading.get_trades(conn)
positions_df = demo_trading.get_positions(conn)

tab_trades, tab_positions = st.tabs(["Сделки", "Позиции"])
with tab_trades:
    if trades_df.empty:
        st.info("Пока нет совершённых сделок в демо-режиме.")
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
            summary_cols[0].metric("Количество сделок", f"{len(trades_df)}")
            summary_cols[1].metric("Оборот", _fmt_money(summary["value"].sum()))
            summary_cols[2].metric("Реализованный P/L", _fmt_money(trades_df["realized_pl"].sum()))
            st.caption("Сводка по тикерам — полезно оценивать распределение капитала.")
            st.dataframe(summary, use_container_width=True)
        except Exception:
            pass

with tab_positions:
    if positions_df.empty:
        st.info("Открытых позиций нет.")
    else:
        positions_view = positions_df.copy()
        numeric_cols = ["quantity", "avg_price", "invested_value", "market_price", "market_value", "unrealized_pl", "realized_pl"]
        for col in numeric_cols:
            if col in positions_view.columns:
                positions_view[col] = positions_view[col].astype(float)
        st.dataframe(positions_view, use_container_width=True)
        st.caption("Проверяйте рыночную стоимость и плавающий результат, чтобы держать контроль над риском.")

st.divider()
ui.section_title("Сводка по тикерам")
df_signals = df_all[
    (df_all.get('Adaptive_Buy_Signal', 0) == 1)
    | (df_all.get('Adaptive_Sell_Signal', 0) == 1)
    | (df_all.get('New_Adaptive_Buy_Signal', 0) == 1)
    | (df_all.get('New_Adaptive_Sell_Signal', 0) == 1)
].copy()

if df_signals.empty:
    st.info("Активных сигналов по стратегиям Adaptive не обнаружено.")
else:
    df_signals['Profit_Adaptive_Buy'] = np.where(
        df_signals.get('Adaptive_Buy_Signal', 0) == 1,
        df_signals.get('Dynamic_Profit_Adaptive_Buy', 0),
        0,
    )
    df_signals['Profit_Adaptive_Sell'] = np.where(
        df_signals.get('Adaptive_Sell_Signal', 0) == 1,
        df_signals.get('Dynamic_Profit_Adaptive_Sell', 0),
        0,
    )
    df_signals['Profit_New_Adaptive_Buy'] = np.where(
        df_signals.get('New_Adaptive_Buy_Signal', 0) == 1,
        df_signals.get('Dynamic_Profit_New_Adaptive_Buy', 0),
        0,
    )
    df_signals['Profit_New_Adaptive_Sell'] = np.where(
        df_signals.get('New_Adaptive_Sell_Signal', 0) == 1,
        df_signals.get('Dynamic_Profit_New_Adaptive_Sell', 0),
        0,
    )
    st.dataframe(
        df_signals.groupby('contract_code').sum(numeric_only=True).reset_index(),
        use_container_width=True,
    )

st.caption("Если данные выглядят устаревшими, воспользуйтесь кнопкой в сайдбаре, чтобы сбросить кэш расчётов.")
