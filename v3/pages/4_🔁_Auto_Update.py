from core.bootstrap import setup_environment

setup_environment()

import streamlit as st

from core import ui
from core.utils import run_api_update_job, run_parser_incremental_job

ui.page_header("Автообновление", "Пересчёт котировок и парсинг из внешних источников.", icon="🔁")

col_full, col_increment, col_parser = st.columns(3)

with col_full:
    if st.button("Полный пересчёт", use_container_width=True):
        with st.spinner("Получаем данные по всем тикерам..."):
            try:
                logs = run_api_update_job(full_update=True)
            except Exception as exc:
                st.error(f"Ошибка при полном обновлении: {exc}")
            else:
                st.success("Полное обновление завершено.")
                if logs:
                    st.write(logs)

with col_increment:
    if st.button("Дополнить пропуски", use_container_width=True):
        with st.spinner("Получаем только недостающие бары..."):
            try:
                logs = run_api_update_job(full_update=False)
            except Exception as exc:
                st.error(f"Ошибка при инкрементальном обновлении: {exc}")
            else:
                st.success("Инкрементальное обновление завершено.")
                if logs:
                    st.write(logs)

with col_parser:
    if st.button("Парсер MOEX", use_container_width=True):
        with st.spinner("Запускаем сбор данных по MOEX..."):
            try:
                logs = run_parser_incremental_job()
            except Exception as exc:
                st.error(f"Ошибка при парсинге MOEX: {exc}")
            else:
                st.success("Инкрементальный парсер MOEX завершил работу.")
                if logs:
                    st.write(logs)

st.caption("После обновления переходите на дашборд, чтобы убедиться в свежести сигналов.")
