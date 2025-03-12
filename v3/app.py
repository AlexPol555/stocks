# app.py
import streamlit as st
import pandas as pd
import numpy as np

# Импорт необходимых функций из ваших модулей
from database import get_connection, create_tables, load_data_from_db, load_daily_data_from_db, mergeMetrDaily
from populate_database import bulk_populate_database_from_csv, incremental_populate_database_from_csv
from stock_analyzer import StockAnalyzer
from auto_update import auto_update_all_tickers, normalize_ticker, update_missing_market_data
from visualization import plot_daily_analysis, plot_stock_analysis, plot_interactive_chart
from indicators import get_calculated_data
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from orders import create_order

# Настройка страницы
st.set_page_config(page_title="Анализ акций", layout="wide")

# Функция с кэшированием расчётов технических индикаторов
@st.cache_data(show_spinner=True)
def get_calculated_data_cached(_conn):
    # Аргумент с ведущим подчеркиванием не будет учитываться при хэшировании
    return get_calculated_data(_conn)

def clearCachGet_calculated_data():
    get_calculated_data_cached.clear()

def main_page(conn, analyzer, api_key):
    
    # Получаем данные с кэшированием
    df_all = get_calculated_data_cached(conn)
    
    # Настройки фильтрации: по дате, по тикеру или без фильтрации
    unique_dates = sorted(df_all["date"].unique(), reverse=True)
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
    
    # Фильтруем строки с сигналами
    signals_filter = (
        (filtered_df['Adaptive_Buy_Signal'] == 1) |
        (filtered_df['Adaptive_Sell_Signal'] == 1) |
        (filtered_df['New_Adaptive_Buy_Signal'] == 1) |
        (filtered_df['New_Adaptive_Sell_Signal'] == 1)
    )
    # cols_to_show = [
    #     'contract_code', 'date', 'Adaptive_Buy_Signal', 'Adaptive_Sell_Signal', 
    #     'New_Adaptive_Buy_Signal', 'New_Adaptive_Sell_Signal', 
    #     'Profit_Adaptive_Buy', 'Profit_Adaptive_Sell', 
    #     'Profit_New_Adaptive_Buy', 'Profit_New_Adaptive_Sell'
    # ]
    filtered_df = filtered_df.loc[signals_filter]
    filtered_df = filtered_df.drop_duplicates()
    
    # Отображаем таблицу с помощью AgGrid
    gb = GridOptionsBuilder.from_dataframe(filtered_df)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gridOptions = gb.build()
    grid_response = AgGrid(
        filtered_df,
        gridOptions=gridOptions,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme="alpine"
    )
    
    # Извлекаем выбранную строку
    selected_rows = grid_response.get("selected_rows")
    selected = None
    if selected_rows is not None:
        if isinstance(selected_rows, pd.DataFrame):
            if not selected_rows.empty:
                selected = selected_rows.iloc[0]
        elif isinstance(selected_rows, list):
            if len(selected_rows) > 0:
                selected = selected_rows[0]
    
    if selected is not None:
            # Автоматически выбираем тикер из выбранной строки
        selected_ticker = selected.get("contract_code")
        st.sidebar.write(f"Выбран тикер: {selected_ticker}")
        
        # Загружаем данные для графиков (предполагается, что функция load_data_from_db уже импортирована)
        data = load_data_from_db(conn)  # 'conn' должен быть доступен в области видимости
        if data.empty:
            st.error("Нет данных для построения графика. Сначала обновите данные.")
        else:
            # Фильтрация данных по выбранному тикеру
            filtered_df = data[data['contract_code'] == selected_ticker]
            filtered_df_1 = filtered_df[filtered_df["metric_type"] == "Изменение"]
            filtered_df_2 = filtered_df[filtered_df["metric_type"] == "Открытые позиции"]
            
            # Разбиваем экран на две колонки для отображения таблиц
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(filtered_df_1)
            with col2:
                st.dataframe(filtered_df_2)
            
            # Отображаем график по тикеру
            st.subheader("График по тикеру")
            fig = plot_stock_analysis(data, selected_ticker)
            st.pyplot(fig)
        # Разбиваем экран на две колонки: левая — информация, правая — ввод заявки
        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown("## Информация о заявке")
            st.write(f"**Тикер:** {selected.get('contract_code')}")
            st.write(f"**Дата:** {selected.get('date')}")
            st.write(f"**Цена закрытия:** {selected.get('close')}")
            # Дополнительные поля с информацией по ценам и показателям
            st.write(f"**Long Fiz 1:** {selected.get('long_fiz_1', 'N/A')}")
            st.write(f"**Short Fiz 2:** {selected.get('short_fiz_2', 'N/A')}")
            st.write(f"**Long Jur 3:** {selected.get('long_jur_3', 'N/A')}")
            st.write(f"**Short Jur 4:** {selected.get('short_jur_4', 'N/A')}")
            st.write(f"**RSI:** {selected.get('RSI', 'N/A')}")
            
            # Расчёт соотношений, если значения заданы
            long_fiz_1 = selected.get('long_fiz_1')
            short_fiz_2 = selected.get('short_fiz_2')
            long_jur_3 = selected.get('long_jur_3')
            short_jur_4 = selected.get('short_jur_4')
            if long_fiz_1 is not None and short_fiz_2 not in (None, 0):
                st.write(f"**Соотношение (Long Fiz 1 / Short Fiz 2):** {long_fiz_1 / short_fiz_2:.2f}")
            if long_jur_3 is not None and short_jur_4 not in (None, 0):
                st.write(f"**Соотношение (Long Jur 3 / Short Jur 4):** {long_jur_3 / short_jur_4:.2f}")
        
        with right_col:
            st.markdown("## Параметры заявки")
            volume = st.number_input("Объём заявки", min_value=1, value=100, step=1)
            order_price = st.number_input("Цена заявки", min_value=0.0, value=float(selected.get("close", 0)))
            
            st.markdown("### Выберите действие")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Купить"):
                    result = create_order(
                        ticker=selected.get("contract_code"),
                        volume=volume,
                        order_price=order_price,
                        order_direction="BUY",
                        analyzer=analyzer,
                        account_id=account_id,
                        api_key=api_key
                    )
                    st.success(result)
            with col2:
                if st.button("Продать"):
                    result = create_order(
                        ticker=selected.get("contract_code"),
                        volume=volume,
                        order_price=order_price,
                        order_direction="SELL",
                        analyzer=analyzer,
                        account_id=account_id,
                        api_key=api_key
                    )
                    st.success(result)
    else:
        st.info("Пожалуйста, выберите заявку из таблицы.")
    
    # Итоговая сводка по сигналам (группировка по тикеру)
    df_signals = df_all[(df_all['Adaptive_Buy_Signal'] == 1) |
                        (df_all['Adaptive_Sell_Signal'] == 1) |
                        (df_all['New_Adaptive_Buy_Signal'] == 1) |
                        (df_all['New_Adaptive_Sell_Signal'] == 1)].copy()
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
    
    # Агрегация по месяцам и неделям
    df_signals['date'] = pd.to_datetime(df_signals['date'])
    df_signals['month'] = df_signals['date'].dt.to_period('M')
    df_signals['week'] = df_signals['date'].dt.to_period('W')
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
    
    st.write("### Сводка по месяцам:")
    st.write(summary_by_month)
    st.write("### Сводка по неделям:")
    st.write(summary_by_week)

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
                    clearCachGet_calculated_data()
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
    data = load_data_from_db(conn)
    data_daily = load_daily_data_from_db(conn)
    if data.empty:
        st.error("Нет данных для анализа. Сначала обновите данные.")
    else:
        view_option = st.sidebar.selectbox("Выберите тип графика:", ["График по дате", "График по тикеру"])
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
            st.pyplot(fig)

def main():
    conn = get_connection()
    create_tables(conn)
    api_key = st.secrets["TINKOFF_API_KEY"]
    analyzer = StockAnalyzer(api_key)
    
    st.sidebar.header("Навигация")
    navigation = st.sidebar.radio("Перейти к", ["Главная", "Обновление данных", "Графики"])
    if navigation == "Главная":
        main_page(conn, analyzer, api_key)
    elif navigation == "Обновление данных":
        update_data_page(conn, analyzer)
    elif navigation == "Графики":
        charts_page(conn)
    
    conn.close()

if __name__ == "__main__":
    main()
