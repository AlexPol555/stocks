from core.bootstrap import setup_environment

setup_environment()

import streamlit as st

from core import ui
from core.analyzer import StockAnalyzer
from core.orders.service import create_order
from core.utils import open_database_connection, read_api_key

ui.page_header("Ордеры", "Создание заявок через интеграцию с Tinkoff API.", icon="🛒")

with st.form("order_form"):
    col_ticker, col_side, col_qty, col_price = st.columns([1.5, 1, 1, 1.5])
    with col_ticker:
        ticker = st.text_input("Тикер", value="SBER").upper()
    with col_side:
        side = st.selectbox("Направление", ["BUY", "SELL"], index=0)
    with col_qty:
        quantity = st.number_input("Количество", min_value=1, max_value=10_000, value=10)
    with col_price:
        price = st.number_input("Цена", min_value=0.0, step=0.01)

    submitted = st.form_submit_button("Создать ордер", type="primary")

if submitted:
    conn = None
    try:
        conn = open_database_connection()
        analyzer = StockAnalyzer(read_api_key(), db_conn=conn)
        order = create_order(
            ticker=ticker,
            volume=int(quantity),
            order_price=float(price),
            order_direction=side,
            analyzer=analyzer,
        )
        status = order.get("status")
        message = order.get("message", "Нет сообщения от сервиса.")
        if status == "success":
            st.success(message)
        elif status == "skipped":
            st.info(message)
        else:
            st.warning(message)
        st.json(order)
    except Exception as exc:
        st.error(f"Ошибка при отправке ордера: {exc}")
    finally:
        if conn is not None:
            conn.close()

st.caption("API-ключ должен быть настроен в secrets.toml или переменной окружения TINKOFF_API_KEY.")
