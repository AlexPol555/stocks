import numpy as np
import pandas as pd
import streamlit as st
from database import mergeMetrDaily
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, train_test_split
from itertools import product

def calculate_basic_indicators(data):
    epsilon = 1e-9
    # Скользящие средние
    data['SMA_50'] = data['close'].rolling(window=50).mean()
    data['SMA_200'] = data['close'].rolling(window=200).mean()
    # EMA
    data['EMA_50'] = data['close'].ewm(span=50, adjust=False).mean()
    data['EMA_200'] = data['close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = data['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    RS = avg_gain / (avg_loss + epsilon)
    data['RSI'] = 100 - (100 / (1 + RS))
    
    # MACD и сигнальная линия
    data['EMA_12'] = data['close'].ewm(span=12, adjust=False).mean()
    data['EMA_26'] = data['close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = data['EMA_12'] - data['EMA_26']
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
    
    return data

def generate_trading_signals(data):
    # Базовые сигналы
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
    
    # Объединённый сигнал: 1 - покупка, -1 - продажа, 0 - отсутствие сигнала
    data['Signal'] = 0
    data.loc[data['Buy_Signal'] == 1, 'Signal'] = 1
    data.loc[data['Sell_Signal'] == 1, 'Signal'] = -1
    return data

def calculate_additional_indicators(data, atr_period=24):
    epsilon = 1e-9
    # Bollinger Bands
    window_bb = 35
    data['BB_Middle'] = data['close'].rolling(window=window_bb).mean()
    data['BB_Std'] = data['close'].rolling(window=window_bb).std()
    data['BB_Upper'] = data['BB_Middle'] + 2 * data['BB_Std']
    data['BB_Lower'] = data['BB_Middle'] - 2 * data['BB_Std']
    
    # Stochastic Oscillator
    window_so = 30
    data['Lowest_Low'] = data['low'].rolling(window=window_so).min()
    data['Highest_High'] = data['high'].rolling(window=window_so).max()
    data['%K'] = 100 * (data['close'] - data['Lowest_Low']) / (data['Highest_High'] - data['Lowest_Low'] + epsilon)
    data['%D'] = data['%K'].rolling(window=3).mean()
    
    # ATR (Average True Range)
    data['Prev_Close'] = data['close'].shift(1)
    data['High_Low'] = data['high'] - data['low']
    data['High_PrevClose'] = (data['high'] - data['Prev_Close']).abs()
    data['Low_PrevClose'] = (data['low'] - data['Prev_Close']).abs()
    data['TR'] = data[['High_Low', 'High_PrevClose', 'Low_PrevClose']].max(axis=1)
    data['ATR'] = data['TR'].rolling(window=atr_period, min_periods=1).mean()
    
    return data

def generate_adaptive_signals(data, use_adaptive=True):
    if use_adaptive:
        window = 15  # период для расчета адаптивных значений
        data['RSI_mean'] = data['RSI'].rolling(window=window, min_periods=1).mean()
        data['RSI_std'] = data['RSI'].rolling(window=window, min_periods=1).std()
        adaptive_buy_threshold = data['RSI_mean'] - data['RSI_std']
        adaptive_sell_threshold = data['RSI_mean'] + data['RSI_std']
        
        data['Adaptive_Buy_Signal'] = (
            (data['SMA_50'] > data['SMA_200']) &
            (data['EMA_50'] > data['EMA_200']) &
            (data['RSI'] < adaptive_buy_threshold) &
            (data['MACD'] > data['Signal_Line'])
        ).astype(int)

        data['Adaptive_Sell_Signal'] = (
            (data['SMA_50'] < data['SMA_200']) &
            (data['EMA_50'] < data['EMA_200']) &
            (data['RSI'] > adaptive_sell_threshold) &
            (data['MACD'] < data['Signal_Line'])
        ).astype(int)
    else:
        print('hi')
        # data['Adaptive_Buy_Signal'] = data['Buy_Signal']
        # data['Adaptive_Sell_Signal'] = data['Sell_Signal']
    
    return data

def generate_new_adaptive_signals(data):
    data['ATR_MA'] = data['ATR'].rolling(window=24, min_periods=1).mean()
    
    data['New_Adaptive_Buy_Signal'] = (
        (data['close'] < data['BB_Lower']) &
        (data['%K'] < 15) &
        (data['ATR'] < data['ATR_MA'])
    ).astype(int)
    
    # Сигнал продажи теперь равен 1, если условие выполняется
    sell_condition = (
        (data['close'] > data['BB_Upper']) &
        (data['%K'] > 85) &
        (data['ATR'] < data['ATR_MA'])
    )
    data['New_Adaptive_Sell_Signal'] = sell_condition.astype(int)
    
    data.drop(columns=['ATR_MA'], inplace=True)
    
    return data


def vectorized_dynamic_profit(data, signal_col, profit_col, exit_date_col, exit_price_col,
                              max_holding_days=3, stop_loss_multiplier=0.6, take_profit_multiplier=1.3,
                              is_short=False):
    close = data['close'].values
    max1 = data['high'].values
    min1 = data['low'].values
    atr = data['ATR'].values
    signals = data[signal_col].values
    n = len(data)
    
    profits = np.full(n, np.nan, dtype=float)
    exit_dates = np.array([None] * n)
    exit_prices = np.full(n, np.nan, dtype=float)
    
    for i in np.where(signals != 0)[0]:
        entry_price = close[i]
        atr_value = atr[i]
        if atr_value == 0 or np.isnan(atr_value):
            continue
        
        # Если позиция короткая, определяем стоп-лосс и тейк-профит для продажи
        if is_short:
            stop_loss = entry_price + stop_loss_multiplier * atr_value
            take_profit = entry_price - take_profit_multiplier * atr_value
        else:
            stop_loss = entry_price - stop_loss_multiplier * atr_value
            take_profit = entry_price + take_profit_multiplier * atr_value

        exit_price = None
        exit_date = None
        
        # Перебираем последующие дни до max_holding_days
        for j in range(i+1, min(i+1+max_holding_days, n)):
            day_low = data.iloc[j]['low']
            day_high = data.iloc[j]['high']
            
            if not is_short:  # длинная позиция
                if day_low <= stop_loss:
                    exit_price = stop_loss
                    exit_date = data.iloc[j]['date']
                    break
                if day_high >= take_profit:
                    exit_price = take_profit
                    exit_date = data.iloc[j]['date']
                    break
            else:  # короткая позиция
                if day_high >= stop_loss:
                    exit_price = stop_loss
                    exit_date = data.iloc[j]['date']
                    break
                if day_low <= take_profit:
                    exit_price = take_profit
                    exit_date = data.iloc[j]['date']
                    break
        
        # Если ни одно условие не сработало, берем цену последнего дня в периоде
        if exit_price is None:
            exit_index = min(i+max_holding_days, n-1)
            exit_price = max1[exit_index]
            exit_date = data.iloc[exit_index]['date']
        
        # Расчет прибыли
        if not is_short:
            profit = (exit_price - entry_price) / entry_price * 100
        else:
            profit = (entry_price - exit_price) / entry_price * 100
        
        profits[i] = profit
        exit_dates[i] = exit_date
        exit_prices[i] = exit_price

    data[profit_col] = profits
    data[exit_date_col] = exit_dates
    data[exit_price_col] = exit_prices

    return data

def calculate_technical_indicators(data):
    # Создаем копию данных
    data = data.copy()
    
    # Рассчитываем базовые индикаторы
    data = calculate_basic_indicators(data)
    data = generate_trading_signals(data)
    data = calculate_additional_indicators(data)
    
    # Генерируем адаптивные сигналы
    data = generate_adaptive_signals(data, use_adaptive=True)
    data = generate_new_adaptive_signals(data)
    
    # Если ATR по какой-то причине не рассчитан, пересчитываем дополнительные индикаторы
    if 'ATR' not in data.columns:
        data = calculate_additional_indicators(data)
    
    # Вычисляем динамический профит для базового сигнала
    data = vectorized_dynamic_profit(data, 'Signal', 
                                     'Dynamic_Profit_Base', 'Exit_Date_Base', 'Exit_Price_Base')
    # Вычисляем динамический профит для адаптивных сигналов (покупка и продажа)
    data = vectorized_dynamic_profit(data, 'Adaptive_Buy_Signal', 
                                     'Dynamic_Profit_Adaptive_Buy', 'Exit_Date_Adaptive_Buy', 'Exit_Price_Adaptive_Buy')
    data = vectorized_dynamic_profit(data, 'Adaptive_Sell_Signal', 
                                     'Dynamic_Profit_Adaptive_Sell', 'Exit_Date_Adaptive_Sell', 'Exit_Price_Adaptive_Sell',
                                 is_short=True)
    # Вычисляем динамический профит для новых адаптивных сигналов (покупка и продажа)
    data = vectorized_dynamic_profit(data, 'New_Adaptive_Buy_Signal', 
                                     'Dynamic_Profit_New_Adaptive_Buy', 'Exit_Date_New_Adaptive_Buy', 'Exit_Price_New_Adaptive_Buy')
    data = vectorized_dynamic_profit(data, 'New_Adaptive_Sell_Signal', 
                                 'Dynamic_Profit_New_Adaptive_Sell', 'Exit_Date_New_Adaptive_Sell', 'Exit_Price_New_Adaptive_Sell',
                                 is_short=True)
    
    return data

# @st.cache_data(show_spinner=True)
def get_calculated_data(_conn):
    """
    Функция получает данные, группирует их по контракту и для каждой группы рассчитывает индикаторы.
    Благодаря групповому подходу, расчёт динамического профита и точек выхода (Exit_Date_Base, Exit_Price_Base)
    будет корректным для каждого контракта отдельно.
    """
    mergeData = mergeMetrDaily(_conn)
    results = []
    # Группируем данные по коду контракта
    for contract, group in mergeData.groupby('contract_code'):
        group = group.copy()  # копия группы для безопасности
        results.append(calculate_technical_indicators(group))
    df_all = pd.concat(results)
    
    return df_all.drop_duplicates()
