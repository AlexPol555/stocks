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


def calculate_additional_filters(data):
    # Фильтр объёма: сигнал считается, если объём выше 20-дневного среднего
    data['Volume_Filter'] = data['volume'] > data['volume'].rolling(window=20).mean()
    
    # Фильтр волатильности: ограничение по ATR, можно задать через квантиль или фиксированные значения
    lower_bound = data['ATR'].quantile(0.25)  # нижняя граница
    upper_bound = data['ATR'].quantile(0.75)  # верхняя граница
    data['Volatility_Filter'] = (data['ATR'] > lower_bound) & (data['ATR'] < upper_bound)
    
    # Фильтр свечных паттернов: предполагается, что столбец 'Candle_Pattern' уже рассчитан
    valid_patterns = ['bullish_engulfing', 'hammer', 'morning_star']
    # data['Candlestick_Filter'] = data['Candle_Pattern'].isin(valid_patterns)
    
    # Фильтр тренда: используем ADX, сигнал считается, если ADX выше порога, например, 25
    adx_threshold = 25
    # data['Trend_Filter'] = data['ADX'] > adx_threshold
    
    return data

def generate_final_adaptive_signals(data):
    """
    Объединяем адаптивные сигналы с дополнительными фильтрами для уточнения входа.
    """
    # Предполагается, что базовые адаптивные сигналы уже сгенерированы:
    # 'Adaptive_Buy_Signal' и 'New_Adaptive_Buy_Signal'
    # Сначала объединяем их (это можно настроить по желанию)
    data['Combined_Buy_Signal'] = (data['Adaptive_Buy_Signal'] | data['New_Adaptive_Buy_Signal']).astype(int)
    
    # Применяем дополнительные фильтры
    data = calculate_additional_filters(data)
    
    # Финальный сигнал покупки с учетом всех условий
    data['Final_Buy_Signal'] = (
        data['Combined_Buy_Signal'] &
        data['Volume_Filter'] &
        data['Volatility_Filter']
    ).astype(int)
    
    # Аналогично можно создать сигнал продажи, если требуется
    return data

def vectorized_dynamic_profit(data, signal_col, profit_col, exit_date_col, exit_price_col, 
                              max_holding_days=3, is_short=False):

    close = data['close'].values
    n = len(data)
    
    profits = np.full(n, np.nan, dtype=float)
    exit_dates = np.array([None] * n)
    exit_prices = np.full(n, np.nan, dtype=float)
    
    for i in np.where(data[signal_col] != 0)[0]:
        entry_price = close[i]
        exit_price = None
        exit_date = None
        
        # Определяем границы периода для оценки (дни с i+1 по i+max_holding_days)
        start = i + 1
        end = min(i + max_holding_days + 1, n)  # +1, чтобы включить последний день
        
        # Если период пустой (например, сигнал в последнем дне), используем резервный вариант
        if start >= n:
            exit_index = min(i + max_holding_days, n - 1)
            if not is_short:
                exit_price = entry_price * (1 - 0.005)
            else:
                exit_price = entry_price * (1 + 0.005)
            exit_date = data.iloc[exit_index]['date']
        else:
            period_data = data.iloc[start:end]
            
            if not is_short:
                # Длинная позиция: ищем дни, когда high >= entry_price * (1 + 0.005)
                condition = period_data['high'] >= entry_price * (1 + 0.005)
                valid_days = period_data[condition]
                
                if not valid_days.empty:
                    # Берем максимальное значение high за период и соответствующую дату
                    exit_price = valid_days['high'].max()
                    exit_date = valid_days.loc[valid_days['high'].idxmax()]['date']
                else:
                    # Если условия не выполнены, фиксированный выход по цене -0,5%
                    exit_price = entry_price * (1 - 0.005)
                    exit_date = period_data.iloc[-1]['date']
            else:
                # Короткая позиция: ищем дни, когда low <= entry_price * (1 - 0.005)
                condition = period_data['low'] <= entry_price * (1 - 0.005)
                valid_days = period_data[condition]
                
                if not valid_days.empty:
                    # Берем минимальное значение low за период и соответствующую дату
                    exit_price = valid_days['low'].min()
                    exit_date = valid_days.loc[valid_days['low'].idxmin()]['date']
                else:
                    # Если условия не выполнены, фиксированный выход по цене +0,5%
                    exit_price = entry_price * (1 + 0.005)
                    exit_date = period_data.iloc[-1]['date']
        
        # Расчет прибыли
        if exit_price is not None:
            if not is_short:
                profit = (exit_price - entry_price) / entry_price * 100
            else:
                profit = (entry_price - exit_price) / entry_price * 100
            profits[i] = profit
            exit_prices[i] = exit_price
            exit_dates[i] = exit_date

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
    
    # Применяем интеграцию дополнительных фильтров и формируем финальные адаптивные сигналы
    data = generate_final_adaptive_signals(data)
    
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
    
    # Можно добавить расчет динамического профита и для финального сигнала, если потребуется
    data = vectorized_dynamic_profit(data, 'Final_Buy_Signal', 
                                     'Dynamic_Profit_Final_Buy', 'Exit_Date_Final_Buy', 'Exit_Price_Final_Buy')
    
    return data
@st.cache_data(show_spinner=True)
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

def clear_get_calculated_data():
    get_calculated_data.clear()
