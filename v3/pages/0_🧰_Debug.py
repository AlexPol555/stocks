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

import importlib.util
from typing import Iterable

import streamlit as st

from core import ui

ui.page_header("Отладка", "Проверка путей, модулей и конфигурации проекта.", icon="🧰")

root = Path(__file__).resolve().parents[1]
st.write("Корневая директория:", root)

ui.section_title("Проверка ключевых файлов")
TARGETS = (
    "core/database.py",
    "core/analyzer.py",
    "core/populate.py",
    "core/indicators/__init__.py",
    "core/visualization.py",
    "core/jobs/auto_update.py",
    "core/orders/service.py",
    "core/data_loader.py",
)

for rel_path in TARGETS:
    exists = (root / rel_path).exists()
    st.write(f"{rel_path}:", "✅" if exists else "⚠️ отсутствует")

ui.section_title("Проверка импорта")
MODULES: Iterable[str] = (
    "core.database",
    "core.analyzer",
    "core.populate",
    "core.indicators",
    "core.visualization",
    "core.jobs.auto_update",
    "core.orders.service",
    "core.data_loader",
)

status_rows = []
for module_name in MODULES:
    spec = importlib.util.find_spec(module_name)
    status_rows.append((module_name, "ОК" if spec else "NOT FOUND"))

st.table(status_rows)

ui.section_title("sys.path первые 10 записей")
st.code("\n".join(sys.path[:10]), language="text")
