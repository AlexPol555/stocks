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

import streamlit as st, importlib.util

st.title("🧰 Deep Debug")

ROOT = Path(__file__).resolve().parents[1]
st.write("ROOT =", ROOT)

targets = [
    "core/database.py",
    "core/analyzer.py",
    "core/populate.py",
    "core/indicators/__init__.py",
    "core/visualization.py",
    "core/jobs/auto_update.py",
    "core/orders/service.py",
    "core/data_loader.py",
]
for name in targets:
    st.write(f"{name} exists @ ROOT:", (ROOT / name).exists())

st.subheader("Import check")
modules = [
    "core.database",
    "core.analyzer",
    "core.populate",
    "core.indicators",
    "core.visualization",
    "core.jobs.auto_update",
    "core.orders.service",
    "core.data_loader",
]
for m in modules:
    spec = importlib.util.find_spec(m)
    st.write(f"{m:>20}: ", "OK" if spec else "NOT FOUND")

st.subheader("sys.path (top 10)")
st.code("\n".join(sys.path[:10]), language="text")
