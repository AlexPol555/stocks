# auto_update.py
import re
import pandas as pd
from database import update_technical_indicators
from indicators import parse_technical_indicators
from stock_analyzer import StockAnalyzer
from datetime import datetime, timedelta, timezone
import streamlit as st

def normalize_ticker(ticker: str) -> str:
    """
    Удаляет суффикс вида '-12.24' или '-3.25' из тикера.
    Например, 'AFLT-12.24' превращается в 'AFLT'.
    """
    normalized = re.sub(r'-\d+(\.\d+)?$', '', ticker)  # удаляем суффикс в конце строки
    return normalized

def update_missing_market_data(analyzer, conn, ticker, stock_data):
    """
    Обновляет записи в таблице daily_data для заданного тикера, у которых рыночные данные (open, low, high, close, volume)
    отсутствуют (NULL). Если для записи отсутствуют технические индикаторы, рассчитывает их и вставляет в technical_indicators.
    Возвращает список логов.
    """
    cursor = conn.cursor()
    log = []
    
    normalized_ticker = normalize_ticker(ticker)
    log.append(f"Обновление для тикера: оригинал '{ticker}', нормализованный '{normalized_ticker}'.")
    
    cursor.execute("SELECT id, contract_code FROM companies WHERE contract_code LIKE ?", (normalized_ticker + '%',))
    company_rows = cursor.fetchall()
    if not company_rows:
        log.append(f"Компания с нормализованным тикером '{normalized_ticker}' не найдена в базе.")
        return log
    company_id, db_ticker = company_rows[0]
    log.append(f"Найдена компания: {db_ticker} (id={company_id}).")
    
    cursor.execute("""
        SELECT id, date 
        FROM daily_data 
        WHERE company_id = ? AND open IS NULL
    """, (company_id,))
    records = cursor.fetchall()
    if not records:
        log.append(f"Для {ticker} (id={company_id}) нет записей с отсутствующими рыночными данными.")
        return log

    if 'date_obj' not in stock_data.columns:
        stock_data['date_obj'] = pd.to_datetime(stock_data['time']).dt.date

    for rec in records:
        daily_data_id, date_str = rec
        try:
            daily_date = pd.to_datetime(date_str).date()
        except Exception as ex:
            log.append(f"Ошибка преобразования даты '{date_str}': {ex}")
            continue
        
        matching_rows = stock_data[stock_data['date_obj'] == daily_date]
        if matching_rows.empty:
            log.append(f"Нет рыночных данных для {ticker} на {daily_date}.")
            continue

        row = matching_rows.iloc[0]
        open_val = row.get('open')
        low_val = row.get('low')
        high_val = row.get('high')
        close_val = row.get('close')
        volume_val = row.get('volume')
        
        cursor.execute("""
            UPDATE daily_data
            SET open = ?, low = ?, high = ?, close = ?, volume = ?
            WHERE id = ?
        """, (open_val, low_val, high_val, close_val, volume_val, daily_data_id))
        conn.commit()
        log.append(f"Обновлены рыночные данные для {ticker} на {daily_date}.")

        # cursor.execute("SELECT id FROM technical_indicators WHERE daily_data_id = ?", (daily_data_id,))
        # tech_record = cursor.fetchone()
        # if tech_record is None:
        #     try:
        #         indicators = analyzer.calculate_technical_indicators(matching_rows['close'])
        #     except Exception as calc_e:
        #         log.append(f"Ошибка расчёта технических индикаторов для {ticker} на {daily_date}: {calc_e}")
        #         continue
        #     sma_val = indicators["sma"].iloc[-1] if not indicators["sma"].empty else None
        #     ema_val = indicators["ema"].iloc[-1] if not indicators["ema"].empty else None
        #     rsi_val = indicators["rsi"].iloc[-1] if not indicators["rsi"].empty else None
        #     macd_val = indicators["macd"].iloc[-1] if not indicators["macd"].empty else None
        #     macd_signal_val = indicators["macd_signal"].iloc[-1] if not indicators["macd_signal"].empty else None
        #     bb_upper_val = indicators["bb_upper"].iloc[-1] if not indicators["bb_upper"].empty else None
        #     bb_middle_val = indicators["bb_middle"].iloc[-1] if not indicators["bb_middle"].empty else None
        #     bb_lower_val = indicators["bb_lower"].iloc[-1] if not indicators["bb_lower"].empty else None
        #     cursor.execute("""
        #         INSERT INTO technical_indicators 
        #         (daily_data_id, sma, ema, rsi, macd, macd_signal, bb_upper, bb_middle, bb_lower)
        #         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        #     """, (daily_data_id, sma_val, ema_val, rsi_val, macd_val, macd_signal_val, bb_upper_val, bb_middle_val, bb_lower_val))
        #     conn.commit()
        #     log.append(f"Вставлены технические индикаторы для {ticker} на {daily_date}.")
        # else:
        #     log.append(f"Технические индикаторы для {ticker} на {daily_date} уже заполнены.")
    return log
# def auto_update_all_tickers(analyzer, conn):
#     """
#     Автоматически обновляет базу данных через API для тикеров, присутствующих в базе.
#     Для каждого тикера производится нормализация, затем вызывается функция update_missing_market_data.
#     """

#     cursor = conn.cursor()
#     # Извлекаем тикеры из таблицы companies
#     cursor.execute("SELECT contract_code FROM companies")
#     existing_tickers = [row[0] for row in cursor.fetchall()]
#     additional_mapping = {
#     'SBER': 'BBG004730N88',
#     'SBERF': 'FUTSBERF0000',
#     'GAZP': 'BBG004730RP0',
#     'ABIO': 'TCS10A0JNAB6',
#     'TRNFP': 'BBG00475KHX6',
#     'BELU': 'BBG000TY1CD1',
#     'T': 'BBG000BSJK37',
#     'SNGS': 'BBG0047315D0',
#     'SNGSP': 'BBG004S681M2',
#     'NVTK': 'BBG00475KKY8',
#     'MTSS': 'BBG004S681W1',
#     'TATN': 'BBG004RVFFC0',
#     'TATNP': 'BBG004S68829',
#     }
#     figi_mapping = analyzer.get_figi_mapping()
#     filtered_mapping = {ticker: figi for ticker, figi in figi_mapping.items() if ticker in existing_tickers}
#     filtered_mapping.update(additional_mapping)
#     log_messages = []
#     count = 0
#     for norm_ticker, figi in filtered_mapping.items():
#         count += 1
#         st.write(f"[{count}/{len(filtered_mapping)}] Обновляем данные для {norm_ticker}...")
#         log_messages.append(f"Обновление для {norm_ticker} начато.")
#         stock_data = analyzer.get_stock_data(figi)
#         if stock_data is not None and not stock_data.empty:
#             update_log = update_missing_market_data(analyzer, conn, norm_ticker, stock_data)
#             log_messages.extend(update_log)
#         else:
#             log_messages.append(f"Нет данных для {norm_ticker}.")
#     return log_messages


def auto_update_all_tickers(analyzer, conn, full_update=True):
    """
    Обновляет данные через Tinkoff API:
    - Если full_update=True: очищает таблицу daily_data и загружает новые данные.
    - Если full_update=False: обновляет только записи с NULL значениями.
    """
    log_messages = []
    cursor = conn.cursor()

    # Получаем список тикеров
    cursor.execute("SELECT DISTINCT contract_code FROM companies")
    tickers = [row[0] for row in cursor.fetchall()]

    # Очистка таблицы daily_data при полном обновлении
    if full_update:
        cursor.execute("DELETE FROM daily_data")
        conn.commit()
        log_messages.append("Полное обновление: таблица daily_data очищена.")

    figi_mapping = analyzer.get_figi_mapping()
    # additional_mapping = {
    #     'SBER': 'BBG004730N88',
    #     'SBERF': 'FUTSBERF0000',
    #     'GAZP': 'BBG004730RP0',
    #     'ABIO': 'TCS10A0JNAB6',
    #     'TRNFP': 'BBG00475KHX6',
    #     'BELU': 'BBG000TY1CD1',
    #     'T': 'BBG000BSJK37',
    #     'SNGS': 'BBG0047315D0',
    #     'SNGSP': 'BBG004S681M2',
    #     'NVTK': 'BBG00475KKY8',
    #     'MTSS': 'BBG004S681W1',
    #     'TATN': 'BBG004RVFFC0',
    #     'TATNP': 'BBG004S68829',
    # }
    # figi_mapping.update(additional_mapping)

    for ticker in tickers:
        if ticker not in figi_mapping:
            log_messages.append(f"FIGI для {ticker} не найден.")
            continue

        figi = figi_mapping[ticker]
        stock_data = analyzer.get_stock_data(figi)

        if stock_data.empty:
            log_messages.append(f"Нет рыночных данных для {ticker}.")
            continue

        if full_update:
            # Полная загрузка данных
            for idx, row in stock_data.iterrows():
                cursor.execute(
                    """
                    INSERT INTO daily_data (company_id, date, open, low, high, close, volume)
                    VALUES ((SELECT id FROM companies WHERE contract_code = ?), ?, ?, ?, ?, ?, ?)
                    """,
                    (ticker, pd.to_datetime(row['time']).date(), row['open'], row['low'], row['high'], row['close'], row['volume'])
                )
            conn.commit()
            log_messages.append(f"Полностью обновлены данные для {ticker}.")

        else:
            # Инкрементальное обновление недостающих данных
            cursor.execute(
                """
                SELECT dd.id, dd.date FROM daily_data dd
                JOIN companies c ON dd.company_id = c.id
                WHERE c.contract_code = ? AND (dd.open IS NULL OR dd.low IS NULL OR dd.high IS NULL OR dd.close IS NULL OR dd.volume IS NULL)
                """,
                (ticker,)
            )
            missing_dates = cursor.fetchall()

            for daily_data_id, date_str in missing_dates:
                date_obj = pd.to_datetime(date_str).date()
                matching_data = stock_data[pd.to_datetime(stock_data['time']).dt.date == date_obj]

                if matching_data.empty:
                    log_messages.append(f"Нет рыночных данных для {ticker} на {date_obj}.")
                    continue

                row = matching_data.iloc[0]
                cursor.execute(
                    """
                    UPDATE daily_data
                    SET open = ?, low = ?, high = ?, close = ?, volume = ?
                    WHERE id = ?
                    """,
                    (row['open'], row['low'], row['high'], row['close'], row['volume'], daily_data_id)
                )
            conn.commit()
            log_messages.append(f"Обновлены недостающие данные для {ticker}.")

    conn.commit()
    return log_messages

def update_missing_technical_indicators(analyzer, conn, ticker, token):
    """
    Проверяет и обновляет недостающие технические индикаторы для указанного тикера.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT dd.id, dd.date 
        FROM daily_data dd 
        LEFT JOIN technical_indicators ti ON dd.id = ti.daily_data_id
        WHERE dd.company_id = (SELECT id FROM companies WHERE contract_code = ?) 
        AND ti.id IS NULL
    """, (ticker,))
    
    missing_dates = cursor.fetchall()
    if not missing_dates:
        return [f"Все индикаторы для {ticker} уже загружены."]

    log_messages = []
    figi_mapping = analyzer.get_figi_mapping()
    if ticker not in figi_mapping:
        return [f"FIGI для {ticker} не найден."]

    figi = figi_mapping[ticker]

    for daily_data_id, date_str in missing_dates:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        indicators_data = get_technical_indicators(figi, date_obj, date_obj, token)

        parsed_indicators = parse_technical_indicators(indicators_data)
        if parsed_indicators:
            update_technical_indicators(conn, daily_data_id, parsed_indicators)
            log_messages.append(f"Обновлены индикаторы для {ticker} на {date_str}.")
        else:
            log_messages.append(f"Нет данных индикаторов для {ticker} на {date_str}.")

    return log_messages