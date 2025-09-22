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
from orders import create_order

st.title("🛒 Orders")

col1, col2, col3, col4 = st.columns(4)
with col1: ticker = st.text_input("Ticker", "SBER")
with col2: side = st.selectbox("Side", ["BUY", "SELL"])
with col3: qty = st.number_input("Qty", 1, 1000, 10)
with col4: price = st.number_input("Price", 0.0, step=0.01)

if st.button("Create Order"):
    try:
        order = create_order(ticker, side, int(qty), float(price))
        st.success(f"Created: {order}")
    except Exception as e:
        st.error(f"Error: {e}")
