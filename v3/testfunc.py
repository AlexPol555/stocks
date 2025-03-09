import pandas as pd
import numpy as np

# Пример данных
data = pd.DataFrame({
    'date': pd.to_datetime(['2020-12-25', '2020-12-26', '2020-12-27', '2020-12-28']),
    'open': [154.8, 168.6, 187.1, 217.1],
    'low': [151.9, 168.6, 186.5, 214.4],
    'high': [168.6, 188.6, 230.8, 219.9],
    'close': [168.6, 186.4, 216.0, 216.7]
})

# Предположим, что сигнал продажи сработал в первой строке (индекс 0)
data['Adaptive_Sell_Signal'] = 0
data['New_Adaptive_Sell_Signal'] = 0
data.loc[0, 'Adaptive_Sell_Signal'] = 1
data.loc[0, 'New_Adaptive_Sell_Signal'] = 1

# Сортируем данные по дате (на всякий случай)
data = data.sort_values('date').reset_index(drop=True)

# Вычисляем максимум high и минимум low для следующих 3 дней (без текущего дня)
max_high_next_3 = [data['high'].iloc[i+1:i+4].max() for i in range(len(data))]
min_low_next_3  = [data['low'].iloc[i+1:i+4].min() for i in range(len(data))]
data['max_high_next_3'] = max_high_next_3
data['min_low_next_3'] = min_low_next_3

# Отладочный вывод для строки с сигналом (индекс 0)
signal_idx = 0
entry_price = data.loc[signal_idx, 'close']
print("Дата сигнала:", data.loc[signal_idx, 'date'])
print("Цена входа (close):", entry_price)
print("Данные следующих 3 дней:")
print(data.loc[signal_idx+1:signal_idx+3, ['date', 'open', 'low', 'high', 'close']])
print("Максимум high за следующие 3 дней:", data.loc[signal_idx, 'max_high_next_3'])
print("Минимум low за следующие 3 дней:", data.loc[signal_idx, 'min_low_next_3'])

# Логика расчёта для Sell-сигнала:
# Если за следующие 3 дня цена опустилась ниже цены входа, считаем прибыль как:
#   Profit = (entry - min_low_next_3) / entry * 100
# Иначе (если цена не опускалась ниже или равна entry) – считаем убыток:
#   Profit = (entry - max_high_next_3) / entry * 100
profit_sell = np.where(
    data['min_low_next_3'] < entry_price,
    (entry_price - data['min_low_next_3']) / entry_price * 100,
    (entry_price - data['max_high_next_3']) / entry_price * 100
)

# Применяем рассчитанные значения только там, где сработал сигнал продажи.
data['Profit_Adaptive_Sell'] = pd.Series(profit_sell, index=data.index).where(data['Adaptive_Sell_Signal'] == 1)
data['Profit_New_Adaptive_Sell'] = pd.Series(profit_sell, index=data.index).where(data['New_Adaptive_Sell_Signal'] == 1)

print("\nРасчёт Profit для Sell-сигнала:")
print(data.loc[signal_idx, ['date', 'close', 'max_high_next_3', 'min_low_next_3', 'Profit_Adaptive_Sell']])
