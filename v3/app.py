# bootstrap
from pathlib import Path
import sys
def _add_paths():
    here = Path(__file__).resolve()
    root = here.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    for sub in ("core", "services"):
        ep = root / sub
        if ep.exists() and str(ep) not in sys.path:
            sys.path.insert(0, str(ep))
_add_paths()
# -----

import streamlit as st

st.set_page_config(page_title="Stocks", layout="wide")
st.sidebar.success("Навигация: выбери страницу слева →")
st.write("Открой страницу слева: Dashboard, Analyzer, Data Load, Auto Update, Orders, Settings.")
