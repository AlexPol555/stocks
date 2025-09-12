# app.py
import streamlit as st
import pandas as pd
import numpy as np
import database
import logging
import os
from typing import Optional
from pprint import pprint
import sqlite3

logger = logging.getLogger(__name__)

# попытка импортировать matplotlib для отрисовки графиков (устойчивая заглушка)
try:
    import matplotlib.pyplot as plt
except Exception as _e:
    plt = None
    logger.warning("matplotlib не найден: %s", _e)

# Импорт необходимых функций из ваших модулей
from populate_database import bulk_populate_database_from_csv, incremental_populate_database_from_csv
from stock_analyzer import StockAnalyzer
from auto_update import auto_update_all_tickers, normalize_ticker, update_missing_market_data
from visualization import plot_daily_analysis, plot_stock_analysis, plot_grafik_candle_days
from indicators import get_calculated_data, clear_get_calculated_data
from orders import create_order

# Настройка страницы
st.set_page_config(page_title="Анализ акций", layout="wide")

# guarded import для st_aggrid — если пакет не установлен, используем fallback (st.dataframe)
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
    ST_AGGRID_AVAILABLE = True
except Exception as _e:
    ST_AGGRID_AVAILABLE = False
    logger.warning("st_aggrid не найден: %s", _e)

    # Простая заглушка: отобразить DataFrame через st.dataframe и вернуть структуру с selected_rows
    def AgGrid(df, gridOptions=None, height=400, fit_columns_on_grid_load=True, **kwargs):
        st.dataframe(df)
        # возвращаем структуру, похожую на AgGrid response
        return {"selected_rows": []}

    class GridOptionsBuilder:
        def __init__(self, df=None):
            self.df = df
            self._opts = {}

        @staticmethod
        def from_dataframe(df):
            return GridOptionsBuilder(df)

        def configure_selection(self, **kwargs):
            self._opts['selection'] = kwargs
            return self

        def build(self):
            return self._opts

    GridUpdateMode = type("GridUpdateMode", (), {"SELECTION_CHANGED": None})
    DataReturnMode = type("DataReturnMode", (), {"FILTERED_AND_SORTED": None})

# Функция с кэшированием расчётов технических индикаторов
def get_calculated_data_cached(_conn):
    data = get_calculated_data(_conn)
    return data

# Вспомогательная функция: безопасно открыть БД, поддерживая разные имена функций в модуле database
def open_database_connection():
    for name in ("get_connection", "get_conn", "get_connection"):
        if hasattr(database, name):
            try:
                return getattr(database, name)()
            except TypeError:
                # если функция ожидает аргументы — вызов без аргументов мог бы упасть, попробуем без
                try:
                    return getattr(database, name)(None)
                except Exception:
                    continue
            except Exception as e:
                logger.exception("Ошибка при вызове database.%s: %s", name, e)
    # если не удалось — попробуем прямой коннект по пути DB_PATH, если есть
    if hasattr(database, "DB_PATH"):
        path = getattr(database, "DB_PATH")
        try:
            return sqlite3.connect(path, check_same_thread=False)
        except Exception as e:
            logger.exception("Не удалось подключиться к DB_PATH %s: %s", path, e)
    raise RuntimeError("Не удалось открыть соединение с БД. Проверьте модуль database.")

# --- Утилиты для диагностики БД (используется в debug / sidebar) ---
def db_health_check(conn):
    with conn:
        def q(sql, params=()):
            try:
                return pd.read_sql_query(sql, conn, params=params)
            except Exception as e:
                return f"SQL error: {e}"

        st.subheader("Таблицы в базе")
        tables = q("SELECT name FROM sqlite_master WHERE type='table';")
        st.write(tables)

        st.subheader("Counts")
        for t in ['companies','daily_data','metrics','company_parameters']:
            try:
                cnt = pd.read_sql_query(f"SELECT COUNT(*) AS cnt FROM {t};", conn).iloc[0]['cnt']
            except Exception:
                cnt = "no table"
            st.write(f"{t}: {cnt}")

        st.subheader("Sample companies")
        st.write(q("SELECT * FROM companies LIMIT 10;"))

        st.subheader("Sample daily_data")
        st.write(q("SELECT * FROM daily_data LIMIT 10;"))

        st.subheader("Sample metrics")
        st.write(q("SELECT * FROM metrics LIMIT 10;"))

        st.subheader("Join sample (daily_data <-> metrics)")
        st.write(q("""
            SELECT dd.company_id, dd.date, m.metric_type
            FROM daily_data dd
            JOIN metrics m ON dd.company_id = m.company_id AND dd.date = m.date
            LIMIT 20;
        """))

# --- Безопасное извлечение selected_rows из ответа AgGrid ---
def _extract_selected_rows(grid_response):
    """
    Попытки извлечь выбранные строки в нескольких форматах:
      - dict (-> 'selected_rows' / 'data')
      - объект с атрибутом .selected_rows или .data
      - list
    Возвращает либо DataFrame, либо list, либо dict, либо None.
    """
    try:
        # dict-like
        if isinstance(grid_response, dict):
            return grid_response.get("selected_rows", grid_response.get("data", None))

        # объект с атрибутами
        if hasattr(grid_response, "selected_rows"):
            return getattr(grid_response, "selected_rows")
        if hasattr(grid_response, "data"):
            return getattr(grid_response, "data")

        # list-like
        if isinstance(grid_response, list):
            return grid_response

    except Exception as e:
        logger.exception("Ошибка при извлечении selected_rows: %s", e)
    return None

# --- Основная страница ---
def main_page(conn, analyzer, api_key):
    # Получаем данные с кэшированием
    df_all = get_calculated_data_cached(conn)
    st.button("Очистить кэш", on_click=clear_get_calculated_data)

    if df_all is None or df_all.empty:
        st.info("Данные не найдены или пусты.")
        return

    # Настройки фильтрации: по дате, по тикеру или без фильтрации
    unique_dates = sorted(list(df_all["date"].unique()), reverse=True)
    tickers = df_all["contract_code"].unique()
    filter_type = st.sidebar.radio("Фильтровать данные по:", ("По дате", "По тикеру", "Без фильтрации"))
    if filter_type == "По дате":
        selected_date = st.sidebar.selectbox("Выберите дату", unique_dates)
        filtered_df = df_all[df_all["date"] == selected_date].copy()
    elif filter_type == "По тикеру":
        selected_ticker = st.sidebar.selectbox("Выберите тикер", tickers)
        filtered_df = df_all[df_all["contract_code"] == selected_ticker].copy()
    else:
        filtered_df = df_all.copy()

    col1, col2, col3, col4 = st.columns(4)
    adaptive_buy = col1.checkbox("Adaptive Buy Signal", value=True)
    adaptive_sell = col2.checkbox("Adaptive Sell Signal", value=True)
    new_adaptive_buy = col3.checkbox("New Adaptive Buy Signal", value=True)
    new_adaptive_sell = col4.checkbox("New Adaptive Sell Signal", value=True)

    # Построение условия фильтрации через mask (без булевой неоднозначности)
    mask = pd.Series(False, index=filtered_df.index)
    if adaptive_buy and 'Adaptive_Buy_Signal' in filtered_df.columns:
        mask |= (filtered_df['Adaptive_Buy_Signal'] == 1)
    if adaptive_sell and 'Adaptive_Sell_Signal' in filtered_df.columns:
        mask |= (filtered_df['Adaptive_Sell_Signal'] == 1)
    if new_adaptive_buy and 'New_Adaptive_Buy_Signal' in filtered_df.columns:
        mask |= (filtered_df['New_Adaptive_Buy_Signal'] == 1)
    if new_adaptive_sell and 'New_Adaptive_Sell_Signal' in filtered_df.columns:
        mask |= (filtered_df['New_Adaptive_Sell_Signal'] == 1)

    if mask.any():
        filtered_df = filtered_df[mask]
    else:
        filtered_df = filtered_df.copy()

    # Конфигурация AgGrid
    gb = GridOptionsBuilder.from_dataframe(filtered_df)
    try:
        gb.configure_selection(selection_mode="single", use_checkbox=False)
        gridOptions = gb.build()
    except Exception:
        gridOptions = {}

    filtered_df = filtered_df.drop_duplicates()

    grid_response = AgGrid(
        filtered_df,
        gridOptions=gridOptions,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme="alpine"
    )

    # --- Извлечение выбранной строки (безопасно) ---
    selected_rows_raw = _extract_selected_rows(grid_response)

    selected = None
    if selected_rows_raw is not None:
        # DataFrame
        if isinstance(selected_rows_raw, pd.DataFrame):
            if not selected_rows_raw.empty:
                selected = selected_rows_raw.iloc[0].to_dict()
        # list (list of dicts / list of Series)
        elif isinstance(selected_rows_raw, list):
            if len(selected_rows_raw) > 0:
                first = selected_rows_raw[0]
                if isinstance(first, pd.Series):
                    selected = first.to_dict()
                elif isinstance(first, dict):
                    selected = first
                else:
                    try:
                        selected = dict(first)
                    except Exception:
                        selected = None
        # dict-like
        elif isinstance(selected_rows_raw, dict):
            selected = selected_rows_raw

    # Если есть выбранная строка — показываем подробности и графики
    if selected is not None:
        selected_ticker = selected.get("contract_code")
        st.sidebar.write(f"Выбран тикер: {selected_ticker}")

        # Загружаем данные для графиков через database
        try:
            data = database.load_data_from_db(conn)
        except Exception:
            data = pd.DataFrame()
        if data.empty:
            st.error("Нет данных для построения графика. Сначала обновите данные.")
        else:
            filtered_df_full = data[data['contract_code'] == selected_ticker]
            filtered_df_1 = filtered_df_full[filtered_df_full["metric_type"] == "Изменение"]
            filtered_df_2 = filtered_df_full[filtered_df_full["metric_type"] == "Открытые позиции"]
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(filtered_df_1)
            with col2:
                st.dataframe(filtered_df_2)

        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown("## Информация о заявке")
            st.write(f"**Тикер:** {selected.get('contract_code')}")
            st.write(f"**Дата:** {selected.get('date')}")
            st.write(f"**Цена закрытия:** {selected.get('close')}")
            st.write(f"**RSI:** {selected.get('RSI', 'N/A')}")
            st.write(f"**ATR:** {selected.get('ATR', 'N/A')}")
            st.write(f"**Final_Buy_Signal:** {selected.get('Final_Buy_Signal', 'N/A')}")

            # Определяем, какие сигналы сработали
            triggered_signals = []
            if selected.get('Signal') == 1:
                triggered_signals.append("Базовый Buy")
            elif selected.get('Signal') == -1:
                triggered_signals.append("Базовый Sell")

            if selected.get('Adaptive_Buy_Signal') == 1:
                triggered_signals.append("Adaptive Buy")
            elif selected.get('Adaptive_Sell_Signal') == 1:
                triggered_signals.append("Adaptive Sell")

            if selected.get('New_Adaptive_Buy_Signal') == 1:
                triggered_signals.append("New Adaptive Buy")
            elif selected.get('New_Adaptive_Sell_Signal') == 1:
                triggered_signals.append("New Adaptive Sell")

            if triggered_signals:
                st.write(f"**Сработавший сигнал:** {', '.join(triggered_signals)}")
            else:
                st.write("**Сработавший сигнал:** Нет")

            # Отображение динамической информации для каждого типа сигнала, если они сработали
            if selected.get('Adaptive_Buy_Signal') == 1:
                st.write(f"**Dynamic Profit (Adaptive Buy):** {selected.get('Dynamic_Profit_Adaptive_Buy', 'N/A')}")
                st.write(f"**Exit Date (Adaptive Buy):** {selected.get('Exit_Date_Adaptive_Buy', 'N/A')}")
                st.write(f"**Exit Price (Adaptive Buy):** {selected.get('Exit_Price_Adaptive_Buy', 'N/A')}")
            if selected.get('Adaptive_Sell_Signal') == 1:
                st.write(f"**Dynamic Profit (Adaptive Sell):** {selected.get('Dynamic_Profit_Adaptive_Sell', 'N/A')}")
                st.write(f"**Exit Date (Adaptive Sell):** {selected.get('Exit_Date_Adaptive_Sell', 'N/A')}")
                st.write(f"**Exit Price (Adaptive Sell):** {selected.get('Exit_Price_Adaptive_Sell', 'N/A')}")
            if selected.get('New_Adaptive_Buy_Signal') == 1:
                st.write(f"**Dynamic Profit (New Adaptive Buy):** {selected.get('Dynamic_Profit_New_Adaptive_Buy', 'N/A')}")
                st.write(f"**Exit Date (New Adaptive Buy):** {selected.get('Exit_Date_New_Adaptive_Buy', 'N/A')}")
                st.write(f"**Exit Price (New Adaptive Buy):** {selected.get('Exit_Price_New_Adaptive_Buy', 'N/A')}")
            if selected.get('New_Adaptive_Sell_Signal') == 1:
                st.write(f"**Dynamic Profit (New Adaptive Sell):** {selected.get('Dynamic_Profit_New_Adaptive_Sell', 'N/A')}")
                st.write(f"**Exit Date (New Adaptive Sell):** {selected.get('Exit_Date_New_Adaptive_Sell', 'N/A')}")
                st.write(f"**Exit Price (New Adaptive Sell):** {selected.get('Exit_Price_New_Adaptive_Sell', 'N/A')}")

        with right_col:
            st.write("Параметры заявки (в разработке)")
            # Здесь можно разместить интерфейс отправки заявки через create_order
    else:
        st.info("Пожалуйста, выберите заявку из таблицы.")

    # Сводка сигналов
    df_signals = df_all[
        (df_all.get('Adaptive_Buy_Signal', 0) == 1) |
        (df_all.get('Adaptive_Sell_Signal', 0) == 1) |
        (df_all.get('New_Adaptive_Buy_Signal', 0) == 1) |
        (df_all.get('New_Adaptive_Sell_Signal', 0) == 1)
    ].copy()

    # безопасные .get при отсутствии колонок
    df_signals['Profit_Adaptive_Buy'] = np.where(
        df_signals.get('Adaptive_Buy_Signal', 0) == 1,
        df_signals.get('Dynamic_Profit_Adaptive_Buy', 0),
        0
    )
    df_signals['Profit_Adaptive_Sell'] = np.where(
        df_signals.get('Adaptive_Sell_Signal', 0) == 1,
        df_signals.get('Dynamic_Profit_Adaptive_Sell', 0),
        0
    )
    df_signals['Profit_New_Adaptive_Buy'] = np.where(
        df_signals.get('New_Adaptive_Buy_Signal', 0) == 1,
        df_signals.get('Dynamic_Profit_New_Adaptive_Buy', 0),
        0
    )
    df_signals['Profit_New_Adaptive_Sell'] = np.where(
        df_signals.get('New_Adaptive_Sell_Signal', 0) == 1,
        df_signals.get('Dynamic_Profit_New_Adaptive_Sell', 0),
        0
    )

    summary = df_signals.groupby('contract_code').agg(
        New_Adaptive_Buy_Signal=('New_Adaptive_Buy_Signal', 'sum'),
        New_Adaptive_Sell_Signal=('New_Adaptive_Sell_Signal', 'sum'),
        Adaptive_Buy_Signal=('Adaptive_Buy_Signal', 'sum'),
        Adaptive_Sell_Signal=('Adaptive_Sell_Signal', 'sum'),
        Profit_Adaptive_Buy=('Profit_Adaptive_Buy', 'sum'),
        Profit_Adaptive_Sell=('Profit_Adaptive_Sell', 'sum'),
        Profit_New_Adaptive_Buy=('Profit_New_Adaptive_Buy', 'sum'),
        Profit_New_Adaptive_Sell=('Profit_New_Adaptive_Sell', 'sum')
    ).reset_index()

    st.write(summary)

    # Агрегация по периодам (без ошибок при отсутствии столбца date)
    if 'date' in df_signals.columns:
        df_signals['date'] = pd.to_datetime(df_signals['date'])
        df_signals['month'] = df_signals['date'].dt.to_period('M')
        df_signals['week'] = df_signals['date'].dt.to_period('W')
        df_signals['year'] = df_signals['date'].dt.to_period('Y')

        summary_by_month = df_signals.groupby('month').agg(
            Adaptive_Buy_Signal=('Adaptive_Buy_Signal', 'sum'),
            Adaptive_Sell_Signal=('Adaptive_Sell_Signal', 'sum'),
            New_Adaptive_Buy_Signal=('New_Adaptive_Buy_Signal', 'sum'),
            New_Adaptive_Sell_Signal=('New_Adaptive_Sell_Signal', 'sum'),
            Profit_Adaptive_Buy=('Profit_Adaptive_Buy', 'sum'),
            Profit_Adaptive_Sell=('Profit_Adaptive_Sell', 'sum'),
            Profit_New_Adaptive_Buy=('Profit_New_Adaptive_Buy', 'sum'),
            Profit_New_Adaptive_Sell=('Profit_New_Adaptive_Sell', 'sum')
        ).reset_index()

        summary_by_week = df_signals.groupby('week').agg(
            Adaptive_Buy_Signal=('Adaptive_Buy_Signal', 'sum'),
            Adaptive_Sell_Signal=('Adaptive_Sell_Signal', 'sum'),
            New_Adaptive_Buy_Signal=('New_Adaptive_Buy_Signal', 'sum'),
            New_Adaptive_Sell_Signal=('New_Adaptive_Sell_Signal', 'sum'),
            Profit_Adaptive_Buy=('Profit_Adaptive_Buy', 'sum'),
            Profit_Adaptive_Sell=('Profit_Adaptive_Sell', 'sum'),
            Profit_New_Adaptive_Buy=('Profit_New_Adaptive_Buy', 'sum'),
            Profit_New_Adaptive_Sell=('Profit_New_Adaptive_Sell', 'sum')
        ).reset_index()

        summary_by_year = df_signals.groupby('year').agg(
            Adaptive_Buy_Signal=('Adaptive_Buy_Signal', 'sum'),
            Adaptive_Sell_Signal=('Adaptive_Sell_Signal', 'sum'),
            New_Adaptive_Buy_Signal=('New_Adaptive_Buy_Signal', 'sum'),
            New_Adaptive_Sell_Signal=('New_Adaptive_Sell_Signal', 'sum'),
            Profit_Adaptive_Buy=('Profit_Adaptive_Buy', 'sum'),
            Profit_Adaptive_Sell=('Profit_Adaptive_Sell', 'sum'),
            Profit_New_Adaptive_Buy=('Profit_New_Adaptive_Buy', 'sum'),
            Profit_New_Adaptive_Sell=('Profit_New_Adaptive_Sell', 'sum')
        ).reset_index()

        st.write("### Сводка по месяцам:")
        st.write(summary_by_month)
        st.write("### Сводка по неделям:")
        st.write(summary_by_week)
        st.write("### Сводка по годам:")
        st.write(summary_by_year)


def update_data_page(conn, analyzer):
    st.header("Обновление данных")
    update_mode = st.sidebar.selectbox("Выберите режим обновления:", ["Загрузить CSV", "API price"])
    if update_mode == "Загрузить CSV":
        csv_upload_mode = st.sidebar.selectbox("Выберите тип загрузки CSV:", ["Массовая загрузка (Bulk)", "Инкрементальная загрузка"])
        if "csv_data" not in st.session_state:
            st.session_state.csv_data = None
        uploaded_file = st.file_uploader("Выберите CSV файл", type="csv")
        if uploaded_file is not None:
            st.session_state.csv_data = uploaded_file
        if st.session_state.csv_data is not None:
            try:
                st.session_state.csv_data.seek(0)
                df_csv = pd.read_csv(st.session_state.csv_data, encoding="utf-8-sig")
                df_csv.columns = df_csv.columns.str.strip()
                st.write("Найденные столбцы:", df_csv.columns.tolist())
                if "Contract Code" not in df_csv.columns:
                    st.error("Столбец 'Contract Code' не найден.")
                else:
                    st.write("Предварительный просмотр CSV (5 строк):", df_csv.head())
                    st.write("Размер DataFrame:", df_csv.shape)
                    st.session_state.csv_data.seek(0)
                    if csv_upload_mode == "Массовая загрузка (Bulk)":
                        bulk_populate_database_from_csv(st.session_state.csv_data, conn)
                        st.success("Массовая загрузка выполнена успешно!")
                    else:
                        incremental_populate_database_from_csv(st.session_state.csv_data, conn)
                        st.success("Инкрементальная загрузка выполнена успешно!")
            except Exception as e:
                st.error(f"Ошибка при загрузке CSV: {e}")
        else:
            st.info("Ожидается загрузка CSV файла.")
    elif update_mode == "API price":
        st.write("Обновление данных через Tinkoff API для тикеров из базы.")
        api_update_mode = st.sidebar.selectbox("Выберите тип обновления через API:", ["Полное обновление", "Обновить только недостающие рыночные данные"])
        if st.button("Запустить обновление через API"):
            with st.spinner("Обновление данных через API..."):
                if api_update_mode == "Полное обновление":
                    log_messages = auto_update_all_tickers(analyzer, conn)
                else:
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT contract_code FROM companies")
                    tickers = [row[0] for row in cursor.fetchall()]
                    log_messages = []
                    figi_mapping = analyzer.get_figi_mapping()
                    for ticker in tickers:
                        st.write(f"Проверяем {ticker}...")
                        norm_ticker = normalize_ticker(ticker)
                        if norm_ticker not in figi_mapping:
                            log_messages.append(f"FIGI для {ticker} не найден.")
                            continue
                        figi = figi_mapping[norm_ticker]
                        stock_data = analyzer.get_stock_data(figi)
                        if stock_data is None or stock_data.empty:
                            log_messages.append(f"Нет рыночных данных для {ticker}.")
                            continue
                        update_log = update_missing_market_data(analyzer, conn, ticker, stock_data)
                        log_messages.extend(update_log)
                for msg in log_messages:
                    st.write(msg)
            st.success("Обновление через API завершено!")


def charts_page(conn):
    st.header("Графики")
    data = database.load_data_from_db(conn)
    data_daily = database.load_daily_data_from_db(conn)
    if data.empty:
        st.error("Нет данных для анализа. Сначала обновите данные.")
        return

    view_option = st.sidebar.selectbox("Выберите тип графика:", ["График по дате", "График по тикеру"])
    daily_sums = data.groupby('date')[['value1', 'value2', 'value3', 'value4']].sum()
    st.dataframe(daily_sums)
    st.subheader("График сумм по дням")

    if plt is None:
        st.warning("matplotlib не установлен — графики matplotlib недоступны.")
    else:
        fig, ax = plt.subplots(figsize=(10, 5))
        for column in ['value1', 'value2', 'value3', 'value4']:
            ax.plot(daily_sums.index, daily_sums[column], marker='o', label=column)
        ax.set_title("Суммы по дням для value1 - value4")
        ax.set_xlabel("Дата")
        ax.set_ylabel("Сумма")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

    if view_option == "График по дате":
        unique_dates = sorted(data["date"].unique(), reverse=True)
        selected_date = st.sidebar.selectbox("Выберите дату", unique_dates)
        st.subheader("График по дате")
        df = pd.DataFrame(data)
        filtered_df = df[df['date'] == selected_date]
        filtered_df_1 = filtered_df[filtered_df["metric_type"] == "Изменение"]
        filtered_df_2 = filtered_df[filtered_df["metric_type"] == "Открытые позиции"]
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(filtered_df_1)
        with col2:
            st.dataframe(filtered_df_2)
        fig = plot_daily_analysis(data, selected_date)
        if fig is not None:
            st.pyplot(fig)
    elif view_option == "График по тикеру":
        tickers = data["contract_code"].unique()
        selected_ticker = st.sidebar.selectbox("Выберите тикер", tickers)
        filtered_df = data[data['contract_code'] == selected_ticker]
        filtered_df_1 = filtered_df[filtered_df["metric_type"] == "Изменение"]
        filtered_df_2 = filtered_df[filtered_df["metric_type"] == "Открытые позиции"]
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(filtered_df_1)
        with col2:
            st.dataframe(filtered_df_2)
        st.subheader("График по тикеру")
        fig = plot_stock_analysis(data, selected_ticker)
        if fig is not None:
            st.pyplot(fig)


def countPosition(conn):
    data = database.load_data_from_db(conn)
    df = pd.DataFrame(data)
    if df.empty:
        return {}
    df['date'] = pd.to_datetime(df['date'])
    last_date = df['date'].max()
    df_last = df[df['date'] == last_date]
    sums = df_last[['value1', 'value2', 'value3', 'value4']].sum()
    return sums


def main():
    # Откроем соединение с БД (поддерживаем несколько имен функции в модуле database)
    try:
        conn = open_database_connection()
    except Exception as e:
        st.error(f"Не удалось открыть БД: {e}")
        return

    # Создаём таблицы (если есть функция)
    try:
        if hasattr(database, "create_tables"):
            database.create_tables(conn)
    except Exception as e:
        logger.exception("Ошибка при create_tables: %s", e)

    # Показ информации о БД в sidebar
    try:
        from database import DB_PATH
        st.sidebar.write("DB path:", DB_PATH)
        try:
            st.sidebar.write("DB size (bytes):", os.path.getsize(DB_PATH))
        except Exception:
            st.sidebar.write("DB: не найден или ещё не создан")
    except Exception:
        # если DB_PATH отсутствует — просто игнорируем
        pass

    # безопасное получение ключа
    api_key = st.secrets.get("TINKOFF_API_KEY") or st.secrets.get("tinkoff", {}).get("api_key") or os.getenv("TINKOFF_API_KEY")
    if not api_key:
        st.warning("TINKOFF API key not found — Tinkoff calls will be disabled. Set st.secrets['TINKOFF_API_KEY'] or env TINKOFF_API_KEY.")
    analyzer = StockAnalyzer(api_key, db_conn=conn)

    st.sidebar.header("Навигация")
    navigation = st.sidebar.radio("Перейти к", ["Главная", "Обновление данных", "Графики", "DB health"])
    if navigation == "Главная":
        main_page(conn, analyzer, api_key)
    elif navigation == "Обновление данных":
        update_data_page(conn, analyzer)
    elif navigation == "Графики":
        charts_page(conn)
    elif navigation == "DB health":
        db_health_check(conn)

    try:
        st.sidebar.bar_chart(countPosition(conn))
    except Exception:
        st.sidebar.info("Невозможно посчитать позиции (нет данных).")

    conn.close()


if __name__ == "__main__":
    main()
