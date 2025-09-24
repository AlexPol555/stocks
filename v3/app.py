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

from core import ui

st.set_page_config(
    page_title="Stocks Studio",
    page_icon="📈",
    layout="wide",
    menu_items={
        "About": "Stocks Studio — лёгкое рабочее место для анализа и торговли инструментами из базы проекта.",
    },
)

ui.inject_base_theme()

st.sidebar.markdown("## Stocks Studio")
st.sidebar.caption("Навигация по разделам приложения")

_default_visibility = {
    "Dashboard": True,
    "Analyzer": True,
    "Data_Load": True,
    "Auto_Update": True,
    "Orders": True,
    "Demo_Stats": True,
    "Lightweight_Chart": True,
    "Settings": True,
    "Debug": False,
}
_session_visibility = st.session_state.get("page_visibility")
if isinstance(_session_visibility, dict):
    _default_visibility.update(_session_visibility)
visibility = _default_visibility

NAV_GROUPS = [
    (
        "Основное",
        [
            ("Dashboard", "📊 Дашборд", "pages/1_📊_Dashboard.py"),
            ("Analyzer", "🧮 Аналитика", "pages/2_🧮_Analyzer.py"),
            ("Data_Load", "📥 Загрузка данных", "pages/3_📥_Data_Load.py"),
            ("Auto_Update", "🔁 Автообновление", "pages/4_🔁_Auto_Update.py"),
            ("Orders", "🛒 Ордеры", "pages/5_🛒_Orders.py"),
        ],
    ),
    (
        "Демо-счёт",
        [
            ("Demo_Stats", "📈 Статистика демо", "pages/7_📈_Demo_Stats.py"),
            ("Lightweight_Chart", "📈 Лёгкие графики", "pages/7_📈_Lightweight_Chart.py"),
        ],
    ),
    (
        "Служебное",
        [
            ("Settings", "⚙️ Настройки", "pages/6_⚙️_Settings.py"),
            ("Debug", "🧰 Отладка", "pages/0_🧰_Debug.py"),
        ],
    ),
]

for group_title, links in NAV_GROUPS:
    st.sidebar.markdown(f"### {group_title}")
    for key, label, path in links:
        if visibility.get(key, True):
            st.sidebar.page_link(path, label=label)
    st.sidebar.divider()

st.sidebar.markdown("**Подсказки**")
st.sidebar.caption("• Обновите расчёты на вкладке 'Автообновление'\n• Управляйте доступом к страницам через настройки")

ui.page_header(
    "Stocks Studio",
    "Лаконичный рабочий стол: сигналы, сделки и сервисные инструменты в одном месте.",
    icon="📈",
)

st.write(
    "Подберите подходящий раздел: главный дашборд для ежедневного обзора, аналитика для деталей,"
    " загрузка/обновление данных для пополнения базы, а в демо-режиме — тестируйте идеи без риска."
)

ui.section_title("Быстрые действия")
quick_left, quick_right = st.columns(2)
with quick_left:
    st.markdown(
        "- Перейдите в раздел **📊 Дашборд**, чтобы посмотреть свежие сигналы и позиции.\n"
        "- Используйте **🧮 Аналитику**, чтобы углубиться в показатели индикаторов." 
    )
with quick_right:
    st.markdown(
        "- Внесите новые данные через **📥 Загрузку**, затем запустите **🔁 Автообновление**.\n"
        "- Настройте доступность страниц и параметры демо-счёта в **⚙️ Настройках**."
    )

st.divider()
ui.section_title("Состояние приложения", "краткий чек-лист")
status_cols = st.columns(3)
status_cols[0].info("Данные хранятся в SQLite — убедитесь, что файл БД на месте.")
status_cols[1].info("API-ключ Tinkoff нужен для отправки реальных ордеров.")
status_cols[2].info("Демо-модуль позволяет тестировать сделки без рисков.")

st.caption("Готово! Выберите страницу в сайдбаре, чтобы продолжить работу.")
