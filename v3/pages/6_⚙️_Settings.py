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

st.subheader("DB health")
try:
    conn = utils.open_database_connection()
    utils.db_health_check(conn)
    conn.close()
except Exception as e:
    st.warning(f"DB check skipped: {e}")
