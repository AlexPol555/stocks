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

import pandas as pd
import streamlit as st

from core import ui
from core.populate import bulk_populate_database_from_csv, incremental_populate_database_from_csv
from core.utils import open_database_connection, run_api_update_job

ui.page_header("Загрузка данных", "Импорт CSV и обновление котировок через API.", icon="📥")

mode = st.radio("Выберите режим", ("CSV-файл", "API котировки"), horizontal=True)

if mode == "CSV-файл":
    upload_col, info_col = st.columns([2, 1])

    with upload_col:
        load_mode = st.selectbox("Тип загрузки", ("Полная загрузка", "Инкрементальная"))
        st.caption("Полная загрузка очищает таблицы перед импортом, инкрементальная дописывает новые записи.")
        uploaded = st.file_uploader("Выберите CSV", type="csv")

        if uploaded is not None:
            st.write("Размер файла:", f"{uploaded.size / 1024:.1f} КБ")
            try:
                uploaded.seek(0)
                df_csv = pd.read_csv(uploaded, encoding="utf-8-sig")
                df_csv.columns = df_csv.columns.str.strip()
                st.dataframe(df_csv.head(), use_container_width=True)
                st.caption(f"Строк в файле: {df_csv.shape[0]}")

                uploaded.seek(0)
                conn = open_database_connection()
                if load_mode == "Полная загрузка":
                    bulk_populate_database_from_csv(uploaded, conn)
                    st.success("Полная загрузка завершена.")
                else:
                    incremental_populate_database_from_csv(uploaded, conn)
                    st.success("Инкрементальная загрузка завершена.")
            except Exception as exc:
                st.error(f"Ошибка при обработке CSV: {exc}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        else:
            st.info("Загрузите CSV-файл в формате UTF-8 (разделитель запятая).")

    with info_col:
        st.markdown("**Требования к CSV**")
        st.markdown("- Обязательные столбцы: date, contract_code, open, high, low, close.\n- Формат даты — ISO (YYYY-MM-DD).\n- Используйте UTF-8 без BOM.")
else:
    st.markdown("Запустите обновление цен по тикерам, которые уже есть в базе данных.")
    api_mode = st.radio("Диапазон обновления", ("Полный период", "Только пропуски"), horizontal=True)
    full_update = api_mode == "Полный период"

    if st.button("Запустить обновление", type="primary"):
        with st.spinner("Выполняем запросы к API..."):
            try:
                logs = run_api_update_job(full_update=full_update)
            except Exception as exc:
                st.error(f"Ошибка при обновлении через API: {exc}")
            else:
                st.success("Обновление завершено.")
                if logs:
                    st.write("Журнал:")
                    st.write(logs)
