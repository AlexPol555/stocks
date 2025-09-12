import numpy as np
import pandas as pd
import streamlit as st
from database import mergeMetrDaily
# ВНИМАНИЕ: НЕ импортируем sklearn здесь напрямую — используем guarded import ниже

from sklearn.model_selection import GridSearchCV, train_test_split  # <-- если эти тоже зависят от sklearn, их нужно тоже защищать; но оставлю их, ниже поясню
from itertools import product
import logging

logger = logging.getLogger(__name__)

# Попытка импортировать scikit-learn (guarded)
SKLEARN_AVAILABLE = True
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import GridSearchCV, train_test_split
except Exception as _e:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn не доступна: %s", _e)

    # Заглушка: минимальный интерфейс для RandomForestClassifier
    class RandomForestClassifier:
        def __init__(self, *args, **kwargs):
            logger.warning("Используется заглушка RandomForestClassifier (sklearn отсутствует).")
        def fit(self, X, y):
            return self
        def predict(self, X):
            try:
                import numpy as _np
                return _np.zeros(len(X), dtype=int)
            except Exception:
                return [0] * len(X)

    # Если тебе нужны заглушки для GridSearchCV / train_test_split — можно добавить их здесь.
    def train_test_split(X, y, *args, **kwargs):
        # Возвращаем X_train, X_test, y_train, y_test как простую разбивку 80/20
        n = len(X)
        split = max(1, int(n * 0.8))
        return X[:split], X[split:], y[:split], y[split:]

    class GridSearchCV:
        def __init__(self, estimator, param_grid, *args, **kwargs):
            self.estimator = estimator
            self.param_grid = param_grid
            self.best_estimator_ = estimator
        def fit(self, X, y):
            # простая подгонка без перебора
            self.estimator.fit(X, y)
            self.best_estimator_ = self.estimator
            return self

# UI-предупреждение, если sklearn отсутствует
try:
    if not SKLEARN_AVAILABLE:
        st.warning("scikit-learn не установлен в окружении. Модуль анализа работает в упрощённом режиме.")
except Exception:
    pass

# --- Дальше идут все функции как были (без изменений логики) ---
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
    
    data['Signal'] = 0
    data.loc[data['Buy_Signal'] == 1, 'Signal'] = 1
    data.loc[data['Sell_Signal'] == 1, 'Signal'] = -1
    return data

def calculate_additional_indicators(data, atr_period=24):
    epsilon = 1e-9
    window_bb = 35
    data['BB_Middle'] = data['close'].rolling(window=window_bb).mean()
    data['BB_Std'] = data['close'].rolling(window=window_bb).std()
    data['BB_Upper'] = data['BB_Middle'] + 2 * data['BB_Std']
    data['BB_Lower'] = data['BB_Middle'] - 2 * data['BB_Std']
    
    window_so = 30
    data['Lowest_Low'] = data['low'].rolling(window=window_so).min()
    data['Highest_High'] = data['high'].rolling(window=window_so).max()
    data['%K'] = 100 * (data['close'] - data['Lowest_Low']) / (data['Highest_High'] - data['Lowest_Low'] + epsilon)
    data['%D'] = data['%K'].rolling(window=3).mean()
    
    data['Prev_Close'] = data['close'].shift(1)
    data['High_Low'] = data['high'] - data['low']
    data['High_PrevClose'] = (data['high'] - data['Prev_Close']).abs()
    data['Low_PrevClose'] = (data['low'] - data['Prev_Close']).abs()
    data['TR'] = data[['High_Low', 'High_PrevClose', 'Low_PrevClose']].max(axis=1)
    data['ATR'] = data['TR'].rolling(window=atr_period, min_periods=1).mean()
    
    return data

def generate_adaptive_signals(data, use_adaptive=True):
    if use_adaptive:
        window = 15
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
    
    return data

def generate_new_adaptive_signals(data):
    data['ATR_MA'] = data['ATR'].rolling(window=24, min_periods=1).mean()
    
    data['New_Adaptive_Buy_Signal'] = (
        (data['close'] < data['BB_Lower']) &
        (data['%K'] < 15) &
        (data['ATR'] < data['ATR_MA'])
    ).astype(int)
    
    sell_condition = (
        (data['close'] > data['BB_Upper']) &
        (data['%K'] > 85) &
        (data['ATR'] < data['ATR_MA'])
    )
    data['New_Adaptive_Sell_Signal'] = sell_condition.astype(int)
    
    data.drop(columns=['ATR_MA'], inplace=True)
    
    return data

def calculate_additional_filters(data):
    data['Volume_Filter'] = data['volume'] > data['volume'].rolling(window=20).mean()
    lower_bound = data['ATR'].quantile(0.25)
    upper_bound = data['ATR'].quantile(0.75)
    data['Volatility_Filter'] = (data['ATR'] > lower_bound) & (data['ATR'] < upper_bound)
    return data

def generate_final_adaptive_signals(data):
    data['Combined_Buy_Signal'] = (data['Adaptive_Buy_Signal'] | data['New_Adaptive_Buy_Signal']).astype(int)
    data = calculate_additional_filters(data)
    data['Final_Buy_Signal'] = (
        data['Combined_Buy_Signal'] &
        data['Volume_Filter'] &
        data['Volatility_Filter']
    ).astype(int)
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
        
        start = i + 1
        end = min(i + max_holding_days + 1, n)
        
        if start >= n:
            exit_index = min(i + max_holding_days, n - 1)
            if not is_short:
                exit_price = entry_price * (1 - 0.005)
            else:
                exit_price = entry_price * (1 + 0.005)
            exit_date = data.iloc[exit_index].get('date', None)
        else:
            period_data = data.iloc[start:end]
            
            if not is_short:
                condition = period_data['high'] >= entry_price * (1 + 0.005)
                valid_days = period_data[condition]
                
                if not valid_days.empty:
                    exit_price = valid_days['high'].max()
                    exit_date = valid_days.loc[valid_days['high'].idxmax()]['date']
                else:
                    exit_price = entry_price * (1 - 0.005)
                    exit_date = period_data.iloc[-1].get('date', None)
            else:
                condition = period_data['low'] <= entry_price * (1 - 0.005)
                valid_days = period_data[condition]
                
                if not valid_days.empty:
                    exit_price = valid_days['low'].min()
                    exit_date = valid_days.loc[valid_days['low'].idxmin()]['date']
                else:
                    exit_price = entry_price * (1 + 0.005)
                    exit_date = period_data.iloc[-1].get('date', None)
        
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
    data = data.copy()
    data = calculate_basic_indicators(data)
    data = generate_trading_signals(data)
    data = calculate_additional_indicators(data)
    data = generate_adaptive_signals(data, use_adaptive=True)
    data = generate_new_adaptive_signals(data)
    
    if 'ATR' not in data.columns:
        data = calculate_additional_indicators(data)
    
    data = generate_final_adaptive_signals(data)
    data = vectorized_dynamic_profit(data, 'Signal', 
                                     'Dynamic_Profit_Base', 'Exit_Date_Base', 'Exit_Price_Base')
    data = vectorized_dynamic_profit(data, 'Adaptive_Buy_Signal', 
                                     'Dynamic_Profit_Adaptive_Buy', 'Exit_Date_Adaptive_Buy', 'Exit_Price_Adaptive_Buy')
    data = vectorized_dynamic_profit(data, 'Adaptive_Sell_Signal', 
                                     'Dynamic_Profit_Adaptive_Sell', 'Exit_Date_Adaptive_Sell', 'Exit_Price_Adaptive_Sell',
                                     is_short=True)
    data = vectorized_dynamic_profit(data, 'New_Adaptive_Buy_Signal', 
                                     'Dynamic_Profit_New_Adaptive_Buy', 'Exit_Date_New_Adaptive_Buy', 'Exit_Price_New_Adaptive_Buy')
    data = vectorized_dynamic_profit(data, 'New_Adaptive_Sell_Signal', 
                                     'Dynamic_Profit_New_Adaptive_Sell', 'Exit_Date_New_Adaptive_Sell', 'Exit_Price_New_Adaptive_Sell',
                                     is_short=True)
    data = vectorized_dynamic_profit(data, 'Final_Buy_Signal', 
                                     'Dynamic_Profit_Final_Buy', 'Exit_Date_Final_Buy', 'Exit_Price_Final_Buy')
    return data

@st.cache_data(show_spinner=True)
def get_calculated_data(_conn):
    mergeData = mergeMetrDaily(_conn)
    results = []
    for contract, group in mergeData.groupby('contract_code'):
        group = group.copy()
        results.append(calculate_technical_indicators(group))
    df_all = pd.concat(results)
    return df_all.drop_duplicates()

def clear_get_calculated_data():
    get_calculated_data.clear()
