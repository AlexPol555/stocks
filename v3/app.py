# app.py
import streamlit as st
import pandas as pd
from database import get_connection, create_tables, load_data_from_db, load_daily_data_from_db, mergeMetrDaily
from populate_database import bulk_populate_database_from_csv, incremental_populate_database_from_csv
from stock_analyzer import StockAnalyzer
from auto_update import auto_update_all_tickers, \
    update_missing_technical_indicators  # и функция update_missing_market_data уже импортирована внутри auto_update
from visualization import plot_daily_analysis, plot_stock_analysis, plot_interactive_chart
import os
from auto_update import normalize_ticker, update_missing_market_data
from indicators import get_calculated_data
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode


# Настройка страницы
st.set_page_config(page_title="Анализ акций", layout="wide")
st.title("Анализ и отбор акций для покупки/продажи")


def main():
    # Путь к данным и API-ключ
    api_key = st.secrets["TINKOFF_API_KEY"]

    # Инициализация StockAnalyzer
    analyzer = StockAnalyzer(api_key)

    # Устанавливаем соединение и создаём таблицы, если их нет
    conn = get_connection()
    create_tables(conn)

    # Боковая панель навигации

    st.sidebar.header("Навигация")
    navigation = st.sidebar.radio("Перейти к", ["Главная", "Обновление данных", "Графики"])
    if navigation == "Главная":
        st.header("Добро пожаловать!")
        st.write("Используйте боковую панель для выбора раздела.")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT contract_code FROM companies")
        tickers = [row[0] for row in cursor.fetchall()]

        df_all = get_calculated_data(conn)

        unique_dates = sorted(df_all["date"].unique(), reverse=True)
        tickers = df_all["contract_code"].unique()

        # Выбор типа фильтрации через радиокнопки
        filter_type = st.sidebar.radio("Фильтровать данные по:", ("По дате", "По тикеру", "Без фильтрации"))

        if filter_type == "По дате":
            selected_date = st.sidebar.selectbox("Выберите дату", unique_dates)
            filtered_df = df_all[df_all["date"] == selected_date]
        elif filter_type == "По тикеру":
            selected_ticker = st.sidebar.selectbox("Выберите тикер", tickers)
            filtered_df = df_all[df_all['contract_code'] == selected_ticker]
        else:
            filtered_df = df_all

        signals_filter = (
            (df_all['Adaptive_Buy_Signal'] == 1) |
            (df_all['Adaptive_Sell_Signal'] == 1) |
            (df_all['New_Adaptive_Buy_Signal'] == 1) |
            (df_all['New_Adaptive_Sell_Signal'] == 1)
        )
        cols_to_show = [
            'contract_code', 'date', 'Adaptive_Buy_Signal', 'Adaptive_Sell_Signal', 
            'New_Adaptive_Buy_Signal', 'New_Adaptive_Sell_Signal', 
            'Profit_Adaptive_Buy', 'Profit_Adaptive_Sell', 
            'Profit_New_Adaptive_Buy', 'Profit_New_Adaptive_Sell'
        ]
        filtered_df = filtered_df.loc[signals_filter]

        if filtered_df.duplicated().any():
            filtered_df = filtered_df.drop_duplicates()

        # Настройка AgGrid для отображения таблицы с выбором одной строки
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

        # Получаем выбранные строки
        selected_rows = grid_response.get("selected_rows")

        # Обработка выбранной строки с проверкой на пустоту
        selected = None
        if selected_rows is not None:
            if isinstance(selected_rows, pd.DataFrame):
                if not selected_rows.empty:
                    selected = selected_rows.iloc[0]
            elif isinstance(selected_rows, list):
                if len(selected_rows) > 0:
                    selected = selected_rows[0]

        if selected is not None:
            # Разбиваем экран на две колонки: левая для информации, правая для ввода заявки
            left_col, right_col = st.columns(2)
            
            with left_col:
                st.markdown("## Информация о заявке")
                st.write(f"**Тикер:** {selected.get('contract_code')}")
                st.write(f"**Дата:** {selected.get('date')}")
                st.write(f"**Цена закрытия:** {selected.get('close')}")
                
                # Дополнительные данные по ценам и показателям
                st.write(f"**Long Fiz 1:** {selected.get('long_fiz_1', 'N/A')}")
                st.write(f"**Short Fiz 2:** {selected.get('short_fiz_2', 'N/A')}")
                st.write(f"**Long Jur 3:** {selected.get('long_jur_3', 'N/A')}")
                st.write(f"**Short Jur 4:** {selected.get('short_jur_4', 'N/A')}")
                st.write(f"**RSI:** {selected.get('RSI', 'N/A')}")
                
                # Если заданы значения для long_fiz_1 и short_fiz_2, рассчитываем их соотношение
                long_fiz_1 = selected.get('long_fiz_1')
                short_fiz_2 = selected.get('short_fiz_2')
                long_jur_3 = selected.get('long_jur_3')
                short_jur_4 = selected.get('short_jur_4')

                if long_fiz_1 is not None and short_fiz_2 not in (None, 0):
                    st.write(f"**Соотношение (Long Fiz 1 / short_jur_4):** {long_fiz_1 / short_jur_4:.2f}")
                    st.write(f"**Соотношение (short_fiz_2 / long_jur_3):** {short_fiz_2 / long_jur_3:.2f}")
    
            
            with right_col:
                st.markdown("## Параметры заявки")
                volume = st.number_input("Объём заявки", min_value=1, value=100, step=1)
                # По умолчанию цена заявки равна цене закрытия выбранной строки
                order_price = st.number_input("Цена заявки", min_value=0.0, value=float(selected.get("close", 0)))
                
                st.markdown("### Выберите действие")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Купить"):
                        st.success(
                            f"Заявка на покупку отправлена:\n"
                            f"Тикер: {selected.get('contract_code')}\n"
                            f"Объём: {volume} шт.\n"
                            f"Цена: {order_price}"
                        )
                with col2:
                    if st.button("Продать"):
                        st.success(
                            f"Заявка на продажу отправлена:\n"
                            f"Тикер: {selected.get('contract_code')}\n"
                            f"Объём: {volume} шт.\n"
                            f"Цена: {order_price}"
                        )
        else:
            st.info("Пожалуйста, выберите заявку из таблицы.")


        # Фильтруем строки, где сработал хотя бы один из сигналов


        df_signals = df_all[signals_filter]

        # Группируем по тикеру и агрегируем необходимые показатели:

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
        # Фильтруем строки с сработавшими сигналами
        signals_filter = (
            (df_all['Adaptive_Buy_Signal'] == 1) |
            (df_all['Adaptive_Sell_Signal'] == 1) |
            (df_all['New_Adaptive_Buy_Signal'] == 1) |
            (df_all['New_Adaptive_Sell_Signal'] == 1) 
        )
        df_signals = df_all[signals_filter].copy()

        # Преобразуем столбец 'date' в datetime, если это не так
        df_signals['date'] = pd.to_datetime(df_signals['date'])

        # Добавляем столбцы для месяца и недели на основе столбца 'date'
        df_signals['month'] = df_signals['date'].dt.to_period('M')
        df_signals['week'] = df_signals['date'].dt.to_period('W')

        # Группировка по месяцам
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

        # Группировка по неделям
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

        st.write("Агрегированные данные по месяцам:")
        st.write(summary_by_month)

        st.write("Агрегированные данные по неделям:")
        st.write(summary_by_week)

        
        
    elif navigation == "Обновление данных":
        st.header("Обновление данных")
        update_mode = st.sidebar.selectbox("Выберите режим обновления:",
                                           ["Загрузить CSV", "API price", "API indicators"])

        if update_mode == "Загрузить CSV":
            csv_upload_mode = st.sidebar.selectbox("Выберите тип загрузки CSV:",
                                                   ["Массовая загрузка (Bulk)", "Инкрементальная загрузка"])
            if "csv_data" not in st.session_state:
                st.session_state.csv_data = None
            uploaded_file = st.file_uploader("Выберите CSV файл", type="csv")
            if uploaded_file is not None:
                st.session_state.csv_data = uploaded_file

            if st.session_state.csv_data is not None:
                try:
                    st.session_state.csv_data.seek(0)
                    df = pd.read_csv(st.session_state.csv_data, encoding="utf-8-sig")
                    df.columns = df.columns.str.strip()
                    st.write("Найденные столбцы:", df.columns.tolist())
                    if "Contract Code" not in df.columns:
                        st.error("Столбец 'Contract Code' не найден. Найденные столбцы: " + ", ".join(df.columns))
                    else:
                        st.write("Предварительный просмотр CSV (первые 5 строк):", df.head())
                        st.write("Размер DataFrame:", df.shape)
                        st.session_state.csv_data.seek(0)
                        if csv_upload_mode == "Массовая загрузка (Bulk)":
                            bulk_populate_database_from_csv(st.session_state.csv_data, conn)
                            st.success("Массовая загрузка выполнена успешно! CSV можно удалить после проверки.")
                        else:
                            incremental_populate_database_from_csv(st.session_state.csv_data, conn)
                            st.success("Инкрементальная загрузка выполнена успешно!")
                except Exception as e:
                    st.error(f"Ошибка при загрузке CSV: {e}")
            else:
                st.info("Ожидается загрузка CSV файла.")
        elif update_mode == "API price":
            st.write("Автоматическое обновление через Tinkoff API для тикеров, присутствующих в базе.")
            # Дополнительный выбор: полное автообновление или обновление только недостающих рыночных данных
            api_update_mode = st.sidebar.selectbox("Выберите тип обновления через API:",
                                                   ["Полное обновление", "Обновить только недостающие рыночные данные"])
            if st.button("Запустить обновление через API"):
                with st.spinner("Обновление данных через API..."):
                    if api_update_mode == "Полное обновление":
                        log_messages = auto_update_all_tickers(analyzer, conn)
                    else:
                        # Для обновления только недостающих рыночных данных:
                        cursor = conn.cursor()
                        cursor.execute("SELECT DISTINCT contract_code FROM companies")
                        tickers = [row[0] for row in cursor.fetchall()]
                        log_messages = []
                        # Получаем FIGI mapping один раз, чтобы не вызывать его в каждом цикле
                        figi_mapping = analyzer.get_figi_mapping()
                        for ticker in tickers:
                            st.write(f"Проверяем {ticker} на недостающие рыночные данные...")
                            # Нормализуем тикер (например, 'AFLT-3.25' → 'AFLT')
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
        elif update_mode == "API indicators":
            st.write("Автоматическое обновление через Tinkoff API для тикеров, присутствующих в базе.")
            if st.button("Обновить технические индикаторы"):
                with st.spinner("Обновление индикаторов..."):
                    log_messages = []
                    cursor = conn.cursor()
                    cursor.execute("SELECT contract_code FROM companies")
                    tickers = [row[0] for row in cursor.fetchall()]

                    for ticker in tickers:
                        messages = update_missing_technical_indicators(analyzer, conn, ticker,
                                                                       st.secrets["TINKOFF_API_KEY"])
                        log_messages.extend(messages)

                    for msg in log_messages:
                        st.write(msg)
            st.success("Обновление завершено!")

    elif navigation == "Графики":
        st.header("Графики")
        data = load_data_from_db(conn)
        data_daily_data = load_daily_data_from_db(conn)
        if data.empty:
            st.error("Нет данных для анализа. Сначала обновите данные.")
        else:
            view_option = st.sidebar.selectbox("Выберите тип графика:",
                                               ["График по дате", "График по тикеру", "Интерактивный график"])
            if view_option == "График по дате":
                unique_dates = sorted(data["date"].unique(), reverse=True)
                selected_date = st.sidebar.selectbox("Выберите дату", unique_dates)
                st.subheader("График по дате")
                df = pd.DataFrame(data)  # Замените на вашу дату
                # Фильтрация данных по выбранной дате
                filtered_df = df[df['date'] == selected_date]
                filtered_df_1 = filtered_df[df["metric_type"] == "Изменение"]
                filtered_df_2 = filtered_df[df["metric_type"] == "Открытые позиции"]
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
            elif view_option == "Интерактивный график":
                st.dataframe(data_daily_data)
                tickers = data["contract_code"].unique()
                selected_ticker = st.sidebar.selectbox("Выберите тикер для интерактивного графика", tickers)
                st.subheader("Интерактивный график")
                fig = plot_interactive_chart(data, selected_ticker)
                st.plotly_chart(fig)
    conn.close()


if __name__ == "__main__":
    main()
