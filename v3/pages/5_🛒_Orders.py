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

from core.analyzer import StockAnalyzer
from core.orders.service import create_order
from core.utils import open_database_connection, read_api_key

st.title("🛒 Orders")

col1, col2, col3, col4 = st.columns(4)
with col1: ticker = st.text_input("Ticker", "SBER")
with col2: side = st.selectbox("Side", ["BUY", "SELL"])
with col3: qty = st.number_input("Qty", 1, 1000, 10)
with col4: price = st.number_input("Price", 0.0, step=0.01)

if st.button("Create Order"):
    conn = None
    try:
        conn = open_database_connection()
        analyzer = StockAnalyzer(read_api_key(), db_conn=conn)
        order = create_order(
            ticker=ticker,
            volume=int(qty),
            order_price=float(price),
            order_direction=side,
            analyzer=analyzer,
        )
        if order.get("status") == "success":
            st.success(order.get("message"))
        elif order.get("status") == "skipped":
            st.info(order.get("message"))
        else:
            st.warning(order.get("message"))
        st.json(order)
    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        if conn is not None:
            conn.close()
