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

import os
import streamlit as st
from core import utils
from core import demo_trading

st.title("⚙️ Settings")

st.subheader("Page visibility")
default_visibility = {
    "Debug": True,
    "Dashboard": True,
    "Analyzer": True,
    "Data_Load": True,
    "Auto_Update": True,
    "Orders": True,
}
vis = st.session_state.get("page_visibility", default_visibility.copy())
cols = st.columns(3)
names = list(default_visibility.keys())
for idx, name in enumerate(names):
    with cols[idx % 3]:
        vis[name] = st.checkbox(name.replace("_", " "), value=vis.get(name, True), key=f"vis_{name}")
st.session_state["page_visibility"] = vis

st.subheader("Secrets")
try:
    sd = utils._secrets_dict()
    if sd:
        st.success("secrets.toml found")
        st.write("Keys:", ", ".join(sd.keys()))
    else:
        st.info("No secrets file (ok if you use ENV).")
except Exception as e:
    st.error(f"Secrets error: {e}")

st.subheader("Environment")
env_api = os.getenv("TINKOFF_API_KEY")
env_db = os.getenv("DB_PATH")
st.write("TINKOFF_API_KEY in ENV:", "yes" if env_api else "no")
st.write("DB_PATH in ENV:", env_db or "no")

st.subheader("Database")
db_path = utils.read_db_path()
st.write("DB path:", db_path)
try:
    st.write("DB size (bytes):", os.path.getsize(db_path))
except Exception:
    st.write("DB: not found or not created yet")

st.subheader("Demo счёт")
conn_demo = None
try:
    conn_demo = utils.open_database_connection()
    snapshot = demo_trading.get_account_snapshot(conn_demo)
    account_info = demo_trading.get_account(conn_demo)
    currency = account_info.get("currency", "RUB")

    def _fmt(value: float) -> str:
        return format(float(value), ',.2f').replace(',', ' ')

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Свободный баланс", f"{_fmt(snapshot['balance'])} {currency}")
    col_b.metric("Инвестировано", f"{_fmt(snapshot['invested_value'])} {currency}")
    col_c.metric("Текущая стоимость", f"{_fmt(snapshot['market_value'])} {currency}")
    col_d.metric("Equity", f"{_fmt(snapshot['equity'])} {currency}")

    col_pl1, col_pl2, col_pl3 = st.columns(3)
    col_pl1.metric("Нереализ. P/L", f"{_fmt(snapshot['unrealized_pl'])} {currency}")
    col_pl2.metric("Реализ. P/L", f"{_fmt(snapshot['realized_pl'])} {currency}")
    col_pl3.metric("Итоговый P/L", f"{_fmt(snapshot['total_pl'])} {currency}")
    st.caption("Баланс и доходности указаны в валюте счёта.")

    with st.form("demo_balance_adjust"):
        left, right = st.columns(2)
        with left:
            delta = st.number_input("Сумма", min_value=0.0, step=100.0, format="%.2f")
        with right:
            action = st.selectbox("Действие", ("Пополнить", "Списать"))
        submit_adjust = st.form_submit_button("Применить изменение")
        if submit_adjust:
            if delta <= 0:
                st.warning("Введите сумму больше 0.")
            else:
                signed = delta if action == "Пополнить" else -delta
                try:
                    new_balance = demo_trading.adjust_balance(conn_demo, signed)
                    st.success(f"Баланс обновлён: {_fmt(new_balance)} {currency}")
                    st.experimental_rerun()
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"Не удалось обновить баланс: {exc}")

    with st.form("demo_reset_account"):
        new_balance = st.number_input(
            "Новый стартовый баланс",
            min_value=0.0,
            value=float(snapshot['initial_balance']),
            step=100.0,
            format="%.2f",
        )
        confirm = st.checkbox("Очистить сделки и позиции", value=False)
        submit_reset = st.form_submit_button("Сбросить счёт")
        if submit_reset:
            if not confirm:
                st.warning("Подтвердите очистку истории, установив галочку.")
            else:
                try:
                    demo_trading.reset_account(conn_demo, new_balance)
                    st.success("Демо счёт сброшен.")
                    st.experimental_rerun()
                except Exception as exc:
                    st.error(f"Не удалось сбросить счёт: {exc}")
except Exception as exc:
    st.warning(f"Demo счёт недоступен: {exc}")
finally:
    if conn_demo is not None:
        conn_demo.close()

st.subheader("DB health")
try:
    conn = utils.open_database_connection()
    utils.db_health_check(conn)
    conn.close()
except Exception as e:
    st.warning(f"DB check skipped: {e}")
