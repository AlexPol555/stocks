# import numpy as np
# import pandas as pd
# import itertools

# def setup_indicators(data, rsi_period, macd_fast_period, macd_slow_period, macd_signal_period, bb_period, bb_std_multiplier):
#     # Здесь рассчитываются индикаторы с заданными параметрами
#     # Пример расчёта RSI:
#     data['delta'] = data['close'].diff()
#     gain = data['delta'].clip(lower=0)
#     loss = -data['delta'].clip(upper=0)
#     avg_gain = gain.ewm(alpha=1/rsi_period, adjust=False).mean()
#     avg_loss = loss.ewm(alpha=1/rsi_period, adjust=False).mean()
#     RS = avg_gain / (avg_loss + 1e-9)
#     data['RSI'] = 100 - (100 / (1 + RS))
    
#     # Пример расчёта MACD:
#     data['EMA_fast'] = data['close'].ewm(span=macd_fast_period, adjust=False).mean()
#     data['EMA_slow'] = data['close'].ewm(span=macd_slow_period, adjust=False).mean()
#     data['MACD'] = data['EMA_fast'] - data['EMA_slow']
#     data['Signal_Line'] = data['MACD'].ewm(span=macd_signal_period, adjust=False).mean()
    
#     # Пример расчёта Bollinger Bands:
#     data['BB_Middle'] = data['close'].rolling(window=bb_period).mean()
#     data['BB_Std'] = data['close'].rolling(window=bb_period).std()
#     data['BB_Upper'] = data['BB_Middle'] + bb_std_multiplier * data['BB_Std']
#     data['BB_Lower'] = data['BB_Middle'] - bb_std_multiplier * data['BB_Std']
    
#     # Можно добавить и другие индикаторы по необходимости
#     return data

# def generate_signals(data, rsi_threshold_buy, rsi_threshold_sell):
#     # Пример генерации сигналов с использованием RSI и MACD
#     data['Signal'] = 0
#     # Сигнал покупки, если RSI меньше порога и MACD выше сигнальной линии
#     data.loc[(data['RSI'] < rsi_threshold_buy) & (data['MACD'] > data['Signal_Line']), 'Signal'] = 1
#     # Сигнал продажи, если RSI выше порога и MACD ниже сигнальной линии
#     data.loc[(data['RSI'] > rsi_threshold_sell) & (data['MACD'] < data['Signal_Line']), 'Signal'] = -1
#     return data

# def vectorized_dynamic_profit(data, signal_col, profit_col, exit_date_col, exit_price_col,
#                               max_holding_days, stop_loss_multiplier, take_profit_multiplier, is_short=False):
#     close = data['close'].values
#     atr = data['ATR'].values  # Предполагается, что ATR уже рассчитан
#     signals = data[signal_col].values
#     n = len(data)
    
#     profits = np.full(n, np.nan, dtype=float)
#     exit_dates = np.array([None] * n)
#     exit_prices = np.full(n, np.nan, dtype=float)
    
#     for i in np.where(signals != 0)[0]:
#         entry_price = close[i]
#         atr_value = atr[i]
#         if atr_value == 0 or np.isnan(atr_value):
#             continue
        
#         if not is_short:
#             stop_loss = entry_price - stop_loss_multiplier * atr_value
#             take_profit = entry_price + take_profit_multiplier * atr_value
#         else:
#             stop_loss = entry_price + stop_loss_multiplier * atr_value
#             take_profit = entry_price - take_profit_multiplier * atr_value

#         exit_price = None
#         exit_date = None
        
#         for j in range(i+1, min(i+1+max_holding_days, n)):
#             day_low = data.iloc[j]['low']
#             day_high = data.iloc[j]['high']
            
#             if not is_short:
#                 if day_low <= stop_loss:
#                     exit_price = stop_loss
#                     exit_date = data.iloc[j]['date']
#                     break
#                 if day_high >= take_profit:
#                     exit_price = take_profit
#                     exit_date = data.iloc[j]['date']
#                     break
#             else:
#                 if day_high >= stop_loss:
#                     exit_price = stop_loss
#                     exit_date = data.iloc[j]['date']
#                     break
#                 if day_low <= take_profit:
#                     exit_price = take_profit
#                     exit_date = data.iloc[j]['date']
#                     break
        
#         if exit_price is None:
#             exit_index = min(i+max_holding_days, n-1)
#             exit_price = close[exit_index]
#             exit_date = data.iloc[exit_index]['date']
        
#         if not is_short:
#             profit = (exit_price - entry_price) / entry_price * 100
#         else:
#             profit = (entry_price - exit_price) / entry_price * 100
        
#         profits[i] = profit
#         exit_dates[i] = exit_date
#         exit_prices[i] = exit_price

#     data[profit_col] = profits
#     data[exit_date_col] = exit_dates
#     data[exit_price_col] = exit_prices

#     return data

# def backtest_strategy(
#     data, 
#     stop_loss_multiplier, 
#     take_profit_multiplier, 
#     max_holding_days, 
#     rsi_period, 
#     macd_fast_period, 
#     macd_slow_period, 
#     macd_signal_period, 
#     bb_period, 
#     bb_std_multiplier,
#     rsi_threshold_buy, 
#     rsi_threshold_sell,
#     is_short=False
# ):
#     # Копия данных
#     data_copy = data.copy()
    
#     # Расчет индикаторов (учитываем ATR отдельно, если ATR не рассчитывается в setup_indicators)
#     # Предположим, что ATR уже добавлен в data_copy
#     data_copy = setup_indicators(
#         data_copy, 
#         rsi_period=rsi_period, 
#         macd_fast_period=macd_fast_period, 
#         macd_slow_period=macd_slow_period, 
#         macd_signal_period=macd_signal_period, 
#         bb_period=bb_period, 
#         bb_std_multiplier=bb_std_multiplier
#     )
    
#     # Генерация сигналов по заданным порогам для RSI
#     data_copy = generate_signals(data_copy, rsi_threshold_buy, rsi_threshold_sell)
    
#     # Расчет динамического профита по сигналам
#     data_copy = vectorized_dynamic_profit(
#         data_copy, 
#         signal_col='Signal', 
#         profit_col='Dynamic_Profit', 
#         exit_date_col='Exit_Date', 
#         exit_price_col='Exit_Price',
#         max_holding_days=max_holding_days,
#         stop_loss_multiplier=stop_loss_multiplier,
#         take_profit_multiplier=take_profit_multiplier,
#         is_short=is_short
#     )
    
#     # Здесь можно рассчитать несколько метрик, например:
#     total_profit = np.nansum(data_copy['Dynamic_Profit'])
#     num_trades = np.sum(data_copy['Signal'] != 0)
#     avg_profit = total_profit / num_trades if num_trades else np.nan
    
#     # Можно вернуть комплексный результат
#     return {
#         'total_profit': total_profit,
#         'num_trades': num_trades,
#         'avg_profit': avg_profit,
#         'data': data_copy  # для детального анализа
#     }

# # Пример диапазонов для grid search по расширенному набору параметров
# stop_loss_range = np.arange(0.3, 1.1, 0.1)
# take_profit_range = np.arange(1.5, 3.1, 0.5)
# holding_days_range = range(3, 11)
# rsi_period_range = range(10, 21, 5)
# macd_fast_range = range(10, 21, 5)
# macd_slow_range = range(20, 41, 10)
# macd_signal_range = range(5, 11, 2)
# bb_period_range = range(15, 26, 5)
# bb_std_multiplier_range = np.arange(1.5, 3.1, 0.5)
# rsi_threshold_buy_range = range(20, 41, 10)    # например, 20, 30, 40
# rsi_threshold_sell_range = range(60, 81, 10)     # например, 60, 70, 80

# # Список всех комбинаций параметров
# param_grid = list(itertools.product(
#     stop_loss_range,
#     take_profit_range,
#     holding_days_range,
#     rsi_period_range,
#     macd_fast_range,
#     macd_slow_range,
#     macd_signal_range,
#     bb_period_range,
#     bb_std_multiplier_range,
#     rsi_threshold_buy_range,
#     rsi_threshold_sell_range
# ))

# results = []

# # Предполагаем, что historical_data - DataFrame с данными для конкретного тикера
# for params in param_grid:
#     (sl, tp, hd, rsi_p, macd_fast, macd_slow, macd_signal, bb_p, bb_std, rsi_buy, rsi_sell) = params
    
#     result = backtest_strategy(
#         historical_data, 
#         stop_loss_multiplier=sl,
#         take_profit_multiplier=tp,
#         max_holding_days=hd,
#         rsi_period=rsi_p,
#         macd_fast_period=macd_fast,
#         macd_slow_period=macd_slow,
#         macd_signal_period=macd_signal,
#         bb_period=bb_p,
#         bb_std_multiplier=bb_std,
#         rsi_threshold_buy=rsi_buy,
#         rsi_threshold_sell=rsi_sell,
#         is_short=False  # можно делать и для коротких позиций отдельно
#     )
    
#     results.append({
#         'stop_loss_multiplier': sl,
#         'take_profit_multiplier': tp,
#         'max_holding_days': hd,
#         'rsi_period': rsi_p,
#         'macd_fast_period': macd_fast,
#         'macd_slow_period': macd_slow,
#         'macd_signal_period': macd_signal,
#         'bb_period': bb_p,
#         'bb_std_multiplier': bb_std,
#         'rsi_threshold_buy': rsi_buy,
#         'rsi_threshold_sell': rsi_sell,
#         'total_profit': result['total_profit'],
#         'num_trades': result['num_trades'],
#         'avg_profit': result['avg_profit']
#     })

# results_df = pd.DataFrame(results)
# best_params = results_df.loc[results_df['total_profit'].idxmax()]

# print("Лучшие параметры:")
# print(best_params)
# print("\nПолная таблица результатов (отсортирована по total_profit):")
# print(results_df.sort_values('total_profit', ascending=False))
