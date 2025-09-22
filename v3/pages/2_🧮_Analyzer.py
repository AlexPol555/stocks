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
from stock_analyzer import StockAnalyzer
from visualization import plot_stock_analysis

st.title("🧮 Analyzer")

ticker = st.text_input("Ticker", value="SBER")
if st.button("Analyze"):
    idx = pd.date_range("2024-01-01", periods=200, freq="D")
    df = pd.DataFrame({"Close": range(200)}, index=idx)
    analyzer = StockAnalyzer("")
    out = analyzer.analyze(df)
    st.dataframe(out.tail())
    try:
        st.pyplot(plot_stock_analysis(out, title=ticker))
    except Exception:
        st.line_chart(out["Close"])
