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

import pandas as pd
import streamlit as st

import core.database as database
from core import demo_trading


def _fmt_money(value) -> str:
    try:
        return format(float(value), ',.2f').replace(',', ' ')
    except Exception:
        return str(value)


def _fmt_percent(value) -> str:
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


st.title("📈 Демо статистика")

conn = None
try:
    conn = database.get_connection()
except Exception:
    try:
        conn = database.get_conn()
    except Exception:
        conn = None

if not conn:
    st.error("Нет соединения с базой данных.")
    st.stop()

try:
    account_snapshot = demo_trading.get_account_snapshot(conn)
    account_info = demo_trading.get_account(conn)
    currency = account_info.get("currency", "RUB")

    trades_df = demo_trading.get_trades(conn)
    positions_df = demo_trading.get_positions(conn)
finally:
    conn.close()

col_metrics = st.columns(4)
col_metrics[0].metric("Свободный баланс", f"{_fmt_money(account_snapshot['balance'])} {currency}")
col_metrics[1].metric("Инвестировано", f"{_fmt_money(account_snapshot['invested_value'])} {currency}")
col_metrics[2].metric("Рыночная стоимость", f"{_fmt_money(account_snapshot['market_value'])} {currency}")
col_metrics[3].metric("Equity", f"{_fmt_money(account_snapshot['equity'])} {currency}")

col_pl = st.columns(3)
col_pl[0].metric("Реализованный P/L", f"{_fmt_money(account_snapshot['realized_pl'])} {currency}")
col_pl[1].metric("Нереализованный P/L", f"{_fmt_money(account_snapshot['unrealized_pl'])} {currency}")
col_pl[2].metric("Итоговый P/L", f"{_fmt_money(account_snapshot['total_pl'])} {currency}")

st.divider()

trades_aug = pd.DataFrame()
stats_cols = st.columns(4)
if trades_df.empty:
    stats_cols[0].metric("Сделок", "0")
    stats_cols[1].metric("Win rate", "-")
    stats_cols[2].metric("Общий объём", "0")
    stats_cols[3].metric("Реализованный P/L", "0")
else:
    trades_aug = trades_df.copy()
    trades_aug["executed_at"] = pd.to_datetime(trades_aug["executed_at"], errors="coerce")
    trades_aug = trades_aug.sort_values("executed_at")

    total_trades = len(trades_aug)
    realized_total = trades_aug["realized_pl"].sum()
    gross_volume = trades_aug["value"].abs().sum()
    avg_volume = trades_aug["value"].abs().mean()
    win_rate = 0.0
    if total_trades:
        win_rate = (trades_aug["realized_pl"] > 0).sum() / total_trades * 100

    stats_cols[0].metric("Сделок", str(total_trades))
    stats_cols[1].metric("Win rate", _fmt_percent(win_rate))
    stats_cols[2].metric("Общий объём", f"{_fmt_money(gross_volume)} {currency}")
    stats_cols[3].metric("Реализованный P/L", f"{_fmt_money(realized_total)} {currency}")

    extra_cols = st.columns(2)
    extra_cols[0].metric("Средний объём сделки", f"{_fmt_money(avg_volume)} {currency}")
    extra_cols[1].metric("Лучшая сделка", f"{_fmt_money(trades_aug['realized_pl'].max())} {currency}")

    trades_aug["cum_realized"] = trades_aug["realized_pl"].cumsum()
    st.markdown("### Динамика реализованного P/L")
    try:
        import plotly.graph_objects as go  # type: ignore

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trades_aug["executed_at"],
            y=trades_aug["cum_realized"],
            mode="lines+markers",
            name="Реализованный P/L",
            line=dict(color="#0f766e")
        ))
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320, yaxis_title=f"P/L ({currency})")
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.line_chart(trades_aug.set_index("executed_at")["cum_realized"])

    st.markdown("### P/L по тикерам")
    summary = trades_aug.groupby("contract_code", as_index=False)[["quantity", "value", "realized_pl"]].sum()
    summary["value"] = summary["value"].abs()
    st.dataframe(summary.rename(columns={
        "contract_code": "Тикер",
        "quantity": "Объём",
        "value": "Нотионал",
        "realized_pl": "Реализованный P/L",
    }), use_container_width=True)

st.divider()

st.markdown("### Текущие позиции")
if positions_df.empty:
    st.info("Открытых позиций нет.")
else:
    positions_view = positions_df.copy()
    numeric_cols = ["quantity", "avg_price", "invested_value", "market_price", "market_value", "unrealized_pl", "realized_pl"]
    for col in numeric_cols:
        if col in positions_view.columns:
            positions_view[col] = positions_view[col].astype(float)
    st.dataframe(positions_view, use_container_width=True)

    st.markdown("#### Распределение портфеля")
    try:
        import plotly.express as px  # type: ignore

        pie_df = positions_view[positions_view["market_value"].notna()].copy()
        if pie_df.empty:
            st.info("Нет данных о рыночной стоимости для построения диаграммы.")
        else:
            fig = px.pie(pie_df, names="contract_code", values="market_value", title="Структура портфеля")
            fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=320)
            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("Не удалось построить диаграмму структуры портфеля.")

st.divider()

st.markdown("### Журнал сделок")
if trades_aug.empty:
    st.info("Нет сделок для отображения.")
else:
    history_view = trades_aug.copy()
    history_view["executed_at"] = history_view["executed_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(history_view.sort_values("executed_at", ascending=False), use_container_width=True)
