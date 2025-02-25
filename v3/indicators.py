# indicators.py
from dataclasses import dataclass, asdict
import pandas as pd
import streamlit as st

def calculate_technical_indicators(data):
    # Расчет SMA (50 и 200 дней)
    merged_data = data.sort_values('date').copy()
    merged_data['SMA_50'] = merged_data['close'].rolling(window=50).mean()
    merged_data['SMA_200'] = merged_data['close'].rolling(window=200).mean()

    # Расчет EMA (50 и 200 дней)
    merged_data['EMA_50'] = merged_data['close'].ewm(span=50, adjust=False).mean()
    merged_data['EMA_200'] = merged_data['close'].ewm(span=200, adjust=False).mean()

    # Расчет RSI (14) с защитой от деления на ноль
    epsilon = 1e-9
    delta = merged_data['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    RS = avg_gain / (avg_loss + epsilon)
    merged_data['RSI'] = 100 - (100 / (1 + RS))
    # Расчет MACD (12 EMA, 26 EMA, сигнальная 9 EMA)
    merged_data['12_ema'] = merged_data['close'].ewm(span=12, adjust=False).mean()
    merged_data['26_ema'] = merged_data['close'].ewm(span=26, adjust=False).mean()
    merged_data['MACD'] = merged_data['12_ema'] - merged_data['26_ema']
    merged_data['Signal_Line'] = merged_data['MACD'].ewm(span=9, adjust=False).mean()
    # Пример логики Buy/Sell, комбинирующей SMA и EMA
    # Вы можете усложнять, комбинируя отдельные условия на SMA/EMA в разных временных диапазонах
    merged_data['Buy_Signal'] = (
        (merged_data['SMA_50'] > merged_data['SMA_200']) &
        (merged_data['EMA_50'] > merged_data['EMA_200']) &
        (merged_data['RSI'] < 35) &
        (merged_data['MACD'] > merged_data['Signal_Line'])
    )
    merged_data['Sell_Signal'] = (
        (merged_data['SMA_50'] < merged_data['SMA_200']) &
        (merged_data['EMA_50'] < merged_data['EMA_200']) &
        (merged_data['RSI'] > 65) &
        (merged_data['MACD'] < merged_data['Signal_Line']) 
    )
    merged_data['Buy_Target_Price'] = calculate_target_price(merged_data, signal_type='Buy')
    merged_data['Sell_Target_Price'] = calculate_target_price(merged_data, signal_type='Sell')

    merged_data = merged_data[merged_data['date'] == '2025-02-25']
    return (merged_data[['contract_code', 'date', 'SMA_50','EMA_50', 'RSI','MACD', 'Buy_Signal', 'Sell_Signal', 'Buy_Target_Price', 'Sell_Target_Price']])

def calculate_target_price(merged_data, signal_type='Buy', window=90, multiplier=0.5):
    """
    Функция вычисляет целевой уровень цены для сигнала покупки или продажи.
    :param merged_data: DataFrame с данными, содержащий колонку 'close'
    :param signal_type: 'Buy' для покупки, 'Sell' для продажи
    :param window: период для расчета недавнего диапазона цен (например, 14 дней)
    :param multiplier: множитель для диапазона (можно настроить)
    :return: Series с целевыми уровнями цены
    """
    recent_high = merged_data['close'].rolling(window=window).max()
    recent_low = merged_data['close'].rolling(window=window).min()
    price_range = recent_high - recent_low

    if signal_type == 'Buy':
        target_price = merged_data['close'] + multiplier * price_range
    elif signal_type == 'Sell':
        target_price = merged_data['close'] - multiplier * price_range
    else:
        target_price = merged_data['close']
    
    return target_price

def parse_technical_indicators(api_response):
    """
    Парсит ответ от API Tinkoff и возвращает данные в формате словаря.
    """
    try:
        data = api_response.get("indicators", [])
        if not data:
            return None

        indicators = {
            "sma": data.get("sma", None),
            "ema": data.get("ema", None),
            "rsi": data.get("rsi", None),
            "macd": data.get("macd", None),
            "macd_signal": data.get("macd_signal", None),
            "bb_upper": data.get("bb_upper", None),
            "bb_middle": data.get("bb_middle", None),
            "bb_lower": data.get("bb_lower", None),
        }
        return indicators
    except Exception as e:
        print(f"Ошибка парсинга индикаторов: {e}")
        return None
