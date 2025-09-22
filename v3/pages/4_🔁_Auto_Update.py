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
from core.utils import run_api_update_job

st.title("🔁 Auto Update")

col1, col2 = st.columns(2)
with col1:
    if st.button("Full Update"):
        logs = run_api_update_job(full_update=True)
        st.success("Full update finished")
        st.write(logs)
with col2:
    if st.button("Incremental Update"):
        logs = run_api_update_job(full_update=False)
        st.success("Incremental update finished")
        st.write(logs)
