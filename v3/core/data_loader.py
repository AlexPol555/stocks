import os
import pandas as pd
import streamlit as st
import logging

logger = logging.getLogger(__name__)

@st.cache_data(ttl=3600)
def load_csv_data(folder_path: str) -> pd.DataFrame:
    """
    Загружает CSV файлы из указанной папки и объединяет их в один DataFrame.
    """
    try:
        files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        if not files:
            logger.warning("CSV файлы не найдены в указанной папке")
            return pd.DataFrame()
        all_data = pd.concat(
            [pd.read_csv(os.path.join(folder_path, f), index_col=0) for f in files],
            ignore_index=True
        )
        # Предобработка: корректировка тикеров и преобразование даты
        all_data['Contract Code'] = all_data['Contract Code'].str.split('-').str[0]
        all_data['Date'] = pd.to_datetime(all_data['Date'])
        return all_data
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()
