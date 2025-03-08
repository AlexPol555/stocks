# indicators.py

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, train_test_split

def calculate_technical_indicators(data):
    window = 60
    multiplier = 0.5
    epsilon = 1e-9

    # Сортировка данных по дате и создание копии
    data = data.sort_values('date').copy()

    # --- Основные индикаторы ---
    # SMA
    data['SMA_50'] = data['close'].rolling(window=50).mean()
    data['SMA_200'] = data['close'].rolling(window=200).mean()
    # EMA
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
    # MACD
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

    # --- Обучение модели на основе выбранных признаков ---
    features = ['SMA_50', 'SMA_200', 'EMA_50', 'EMA_200', 'RSI', 'MACD', 'Signal_Line']
    X = data[features]
    y = data['Signal']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    accuracy = model.score(X_test, y_test)

    # --- Адаптивное вычисление порогов для RSI ---
    adaptive_buy_rsi = data.loc[data['Signal'] == 1, 'RSI']
    adaptive_sell_rsi = data.loc[data['Signal'] == -1, 'RSI']
    adaptive_buy_threshold = adaptive_buy_rsi.mean() - adaptive_buy_rsi.std()
    adaptive_sell_threshold = adaptive_sell_rsi.mean() + adaptive_sell_rsi.std()

    use_adaptive = True  # Переключатель: True – используем адаптивные пороги
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

    # --- Новые адаптивные сигналы по дополнительным индикаторам ---
    # Условие для покупки:
    # - Цена ниже нижней границы Bollinger Bands
    # - Stochastic %K ниже 20 (сигнал перепроданности)
    # - ATR ниже своего 14-периодного скользящего среднего (низкая волатильность)
    data['New_Adaptive_Buy_Signal'] = (
        (data['close'] < data['BB_Lower']) &
        (data['%K'] < 20) &
        (data['ATR'] < data['ATR'].rolling(window=14).mean())
    ).astype(int)

    # Условие для продажи:
    # - Цена выше верхней границы Bollinger Bands
    # - Stochastic %K выше 80 (сигнал перекупленности)
    # - ATR ниже своего 14-периодного скользящего среднего
    data['New_Adaptive_Sell_Signal'] = (
        (data['close'] > data['BB_Upper']) &
        (data['%K'] > 80) &
        (data['ATR'] < data['ATR'].rolling(window=14).mean())
    ).astype(int)

    # Удаление временных колонок для экономии памяти
    data.drop(columns=['BB_Std', 'Lowest_Low', 'Highest_High', 'Prev_Close', 
                       'High_Low', 'High_PrevClose', 'Low_PrevClose', 'TR'], inplace=True)

    return data
# [['contract_code', 'date', 'SMA_50','EMA_50', 'RSI','MACD', 'Signal', 'Adaptive_Buy_Signal','Adaptive_Sell_Signal']]


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
