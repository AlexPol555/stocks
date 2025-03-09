# indicators.py

import numpy as np
import pandas as pd
import streamlit as st
from database import mergeMetrDaily
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, train_test_split

@st.cache_data
def get_calculated_data(_conn):
    mergeData = mergeMetrDaily(_conn)
    results = []
    for contract, group in mergeData.groupby('contract_code'):
        group = group.copy()  # на всякий случай
        results.append(calculate_technical_indicators(group))
    df_all = pd.concat(results)
    return df_all

def calculate_technical_indicators(data):
       # Параметры
    window = 60
    multiplier = 0.5
    epsilon = 1e-9

    # Сортируем данные по дате и создаём копию
    data = data.sort_values('date').copy()

    # --- Основные индикаторы ---
    # SMA и EMA
    data['SMA_50'] = data['close'].rolling(window=50).mean()
    data['SMA_200'] = data['close'].rolling(window=200).mean()
    data['EMA_50'] = data['close'].ewm(span=50, adjust=False).mean()
    data['EMA_200'] = data['close'].ewm(span=200, adjust=False).mean()

    # RSI с защитой от деления на ноль
    delta = data['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    RS = avg_gain / (avg_loss + epsilon)
    data['RSI'] = 100 - (100 / (1 + RS))

    # MACD и сигнальная линия
    data['12_ema'] = data['close'].ewm(span=12, adjust=False).mean()
    data['26_ema'] = data['close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = data['12_ema'] - data['26_ema']
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()

    # --- Сигналы на основе основных индикаторов ---
    data['Buy_Signal'] = (
        (data['SMA_50'] > data['SMA_200']) &
        (data['EMA_50'] > data['EMA_200']) &
        (data['RSI'] < 35) &
        (data['MACD'] > data['Signal_Line'])
    ).astype(int)
    data['Sell_Signal'] = (
        (data['SMA_50'] < data['SMA_200']) &
        (data['EMA_50'] < data['EMA_200']) &
        (data['RSI'] > 65) &
        (data['MACD'] < data['Signal_Line'])
    ).astype(int)

    # Комбинированный сигнал: 1 – покупка, -1 – продажа, 0 – отсутствие сигнала
    data['Signal'] = 0
    data.loc[data['Buy_Signal'] == 1, 'Signal'] = 1
    data.loc[data['Sell_Signal'] == 1, 'Signal'] = -1

    # --- Обучение модели для оценки качества сигналов ---
    features = ['SMA_50', 'SMA_200', 'EMA_50', 'EMA_200', 'RSI', 'MACD', 'Signal_Line']
    X = data[features]
    y = data['Signal']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    accuracy = model.score(X_test, y_test)
    print("Точность модели:", accuracy)

    # --- Адаптивное вычисление порогов для RSI ---
    adaptive_buy_rsi = data.loc[data['Signal'] == 1, 'RSI']
    adaptive_sell_rsi = data.loc[data['Signal'] == -1, 'RSI']
    adaptive_buy_threshold = adaptive_buy_rsi.mean() - adaptive_buy_rsi.std()
    adaptive_sell_threshold = adaptive_sell_rsi.mean() + adaptive_sell_rsi.std()
    print("Адаптивный порог для покупки (RSI):", adaptive_buy_threshold)
    print("Адаптивный порог для продажи (RSI):", adaptive_sell_threshold)

    use_adaptive = True  # Если True – используем адаптивные пороги
    if use_adaptive:
        rsi_buy_threshold = adaptive_buy_threshold
        rsi_sell_threshold = adaptive_sell_threshold
    else:
        rsi_buy_threshold = 35
        rsi_sell_threshold = 65

    recent_high = data['close'].rolling(window=window).max()
    recent_low = data['close'].rolling(window=window).min()
    price_range = recent_high - recent_low
    data['buy_range'] = data['close'] + multiplier * price_range
    data['sell_range'] = data['close'] - multiplier * price_range

    data['Adaptive_Buy_Signal'] = (
        (data['SMA_50'] > data['SMA_200']) &
        (data['EMA_50'] > data['EMA_200']) &
        (data['RSI'] < rsi_buy_threshold) &
        (data['MACD'] > data['Signal_Line'])
    ).astype(int)
    data['Adaptive_Sell_Signal'] = (
        (data['SMA_50'] < data['SMA_200']) &
        (data['EMA_50'] < data['EMA_200']) &
        (data['RSI'] > rsi_sell_threshold) &
        (data['MACD'] < data['Signal_Line'])
    ).astype(int)

    # --- Дополнительные индикаторы ---
    # Bollinger Bands (окно 20, коэффициент 2)
    window_bb = 20
    data['BB_Middle'] = data['close'].rolling(window=window_bb).mean()
    data['BB_Std'] = data['close'].rolling(window=window_bb).std()
    data['BB_Upper'] = data['BB_Middle'] + 2 * data['BB_Std']
    data['BB_Lower'] = data['BB_Middle'] - 2 * data['BB_Std']

    # Stochastic Oscillator (окно 14)
    window_so = 14
    data['Lowest_Low'] = data['low'].rolling(window=window_so).min()
    data['Highest_High'] = data['high'].rolling(window=window_so).max()
    data['%K'] = 100 * (data['close'] - data['Lowest_Low']) / (data['Highest_High'] - data['Lowest_Low'] + epsilon)
    data['%D'] = data['%K'].rolling(window=3).mean()

    # ATR (Average True Range) (окно 14)
    data['Prev_Close'] = data['close'].shift(1)
    data['High_Low'] = data['high'] - data['low']
    data['High_PrevClose'] = (data['high'] - data['Prev_Close']).abs()
    data['Low_PrevClose'] = (data['low'] - data['Prev_Close']).abs()
    data['TR'] = data[['High_Low', 'High_PrevClose', 'Low_PrevClose']].max(axis=1)
    window_atr = 14
    data['ATR'] = data['TR'].rolling(window=window_atr).mean()
    data.drop(columns=['BB_Std', 'Lowest_Low', 'Highest_High', 'Prev_Close', 
                       'High_Low', 'High_PrevClose', 'Low_PrevClose', 'TR'], inplace=True)

    data['New_Adaptive_Buy_Signal'] = (
        (data['close'] < data['BB_Lower']) &
        (data['%K'] < 20) &
        (data['ATR'] < data['ATR'].rolling(window=14).mean())
    ).astype(int)
    data['New_Adaptive_Sell_Signal'] = (
        (data['close'] > data['BB_Upper']) &
        (data['%K'] > 80) &
        (data['ATR'] < data['ATR'].rolling(window=14).mean())
    ).astype(int)

    # --- Расчёт прибыльности сигналов за следующие 3 дня ---
    # Рассчитываем максимум high и минимум low для следующих 3 дней (без текущего дня) с помощью list comprehension
    max_high_next_3 = [data['high'].iloc[i+1:i+4].max() for i in range(len(data))]
    min_low_next_3  = [data['low'].iloc[i+1:i+4].min() for i in range(len(data))]
    data['max_high_next_3'] = max_high_next_3
    data['min_low_next_3'] = min_low_next_3

    # Расчёт прибыли для Buy-сигналов (Adaptive и New Adaptive) – используем максимум high
    profit_buy = (np.array(max_high_next_3) - data['close']) / data['close'] * 100
    data['Profit_Adaptive_Buy'] = profit_buy * data['Adaptive_Buy_Signal']
    data['Profit_New_Adaptive_Buy'] = profit_buy * data['New_Adaptive_Buy_Signal']

    # Расчёт прибыли для Sell-сигналов:
    # Если за следующие 3 дня цена опустилась ниже цены входа, рассчитываем прибыль как:
    #    (entry - min_low) / entry * 100,
    # иначе – считаем максимальный убыток как:
    #    (entry - max_high) / entry * 100.
    profit_sell = np.where(
         np.array(min_low_next_3) < data['close'],
         (data['close'] - np.array(min_low_next_3)) / data['close'] * 100,
         (data['close'] - np.array(max_high_next_3)) / data['close'] * 100
    )
    data['Profit_Adaptive_Sell'] = profit_sell * data['Adaptive_Sell_Signal']
    data['Profit_New_Adaptive_Sell'] = profit_sell * data['New_Adaptive_Sell_Signal']

    return data
# [['contract_code', 'date', 'Adaptive_Buy_Signal','Adaptive_Sell_Signal', 'New_Adaptive_Buy_Signal', 'New_Adaptive_Sell_Signal']]


def calculate_target_price(merged_data, signal_type='Buy', window=10, multiplier=0.5):
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
