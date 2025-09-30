#!/usr/bin/env python3
"""
Data 1Hour Quality Test.
Тест качества данных в таблице data_1hour.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_data_1hour_quality():
    """Тест качества данных в таблице data_1hour."""
    print("🔍 Тест качества данных в таблице data_1hour...")
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect("stock_data.db")
        
        # Загружаем данные из таблицы data_1hour
        print("\n📊 Загрузка данных из таблицы data_1hour...")
        query = """
        SELECT * FROM data_1hour 
        ORDER BY symbol, time
        """
        
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("❌ Таблица data_1hour пуста!")
            return
        
        print(f"✅ Загружено {len(df)} записей")
        
        # 1. Проверка структуры данных
        print("\n🔍 1. Проверка структуры данных:")
        expected_columns = ['id', 'symbol', 'time', 'open', 'high', 'low', 'close', 'volume', 'created_at']
        actual_columns = df.columns.tolist()
        
        print(f"   Ожидаемые колонки: {expected_columns}")
        print(f"   Фактические колонки: {actual_columns}")
        
        missing_columns = set(expected_columns) - set(actual_columns)
        extra_columns = set(actual_columns) - set(expected_columns)
        
        if missing_columns:
            print(f"   ❌ Отсутствующие колонки: {missing_columns}")
        else:
            print("   ✅ Все ожидаемые колонки присутствуют")
            
        if extra_columns:
            print(f"   ⚠️ Дополнительные колонки: {extra_columns}")
        
        # 2. Проверка типов данных
        print("\n🔍 2. Проверка типов данных:")
        print(f"   ID: {df['id'].dtype}")
        print(f"   Symbol: {df['symbol'].dtype}")
        print(f"   Time: {df['time'].dtype}")
        print(f"   Open: {df['open'].dtype}")
        print(f"   High: {df['high'].dtype}")
        print(f"   Low: {df['low'].dtype}")
        print(f"   Close: {df['close'].dtype}")
        print(f"   Volume: {df['volume'].dtype}")
        print(f"   Created_at: {df['created_at'].dtype}")
        
        # 3. Проверка на пропущенные значения
        print("\n🔍 3. Проверка на пропущенные значения:")
        missing_data = df.isnull().sum()
        for col, missing_count in missing_data.items():
            if missing_count > 0:
                print(f"   ❌ {col}: {missing_count} пропущенных значений")
            else:
                print(f"   ✅ {col}: пропущенных значений нет")
        
        # 4. Проверка уникальности ID
        print("\n🔍 4. Проверка уникальности ID:")
        duplicate_ids = df['id'].duplicated().sum()
        if duplicate_ids > 0:
            print(f"   ❌ Найдено {duplicate_ids} дублированных ID")
        else:
            print("   ✅ Все ID уникальны")
        
        # 5. Проверка символов
        print("\n🔍 5. Анализ символов:")
        unique_symbols = df['symbol'].unique()
        print(f"   Уникальных символов: {len(unique_symbols)}")
        print(f"   Символы: {sorted(unique_symbols)}")
        
        # Проверяем, что все символы из базы данных companies
        companies_query = "SELECT DISTINCT ticker FROM companies WHERE asset_type = 'shares'"
        companies_df = pd.read_sql_query(companies_query, conn)
        companies_symbols = set(companies_df['ticker'].tolist())
        data_symbols = set(unique_symbols)
        
        unknown_symbols = data_symbols - companies_symbols
        if unknown_symbols:
            print(f"   ⚠️ Неизвестные символы в данных: {unknown_symbols}")
        else:
            print("   ✅ Все символы соответствуют базе данных companies")
        
        # 6. Проверка временных рядов
        print("\n🔍 6. Проверка временных рядов:")
        
        # Конвертируем время в datetime
        df['time'] = pd.to_datetime(df['time'])
        
        for symbol in unique_symbols[:5]:  # Проверяем первые 5 символов
            symbol_data = df[df['symbol'] == symbol].sort_values('time')
            
            print(f"\n   📈 Символ {symbol}:")
            print(f"      Записей: {len(symbol_data)}")
            
            if len(symbol_data) > 1:
                # Проверяем последовательность времени
                time_diffs = symbol_data['time'].diff().dropna()
                expected_diff = pd.Timedelta(hours=1)
                
                # Проверяем, что интервалы близки к 1 часу (допускаем небольшие отклонения)
                valid_intervals = (time_diffs >= pd.Timedelta(minutes=55)) & (time_diffs <= pd.Timedelta(minutes=65))
                invalid_intervals = (~valid_intervals).sum()
                
                if invalid_intervals > 0:
                    print(f"      ⚠️ {invalid_intervals} нерегулярных интервалов времени")
                else:
                    print(f"      ✅ Временные интервалы корректны")
                
                # Проверяем диапазон времени
                time_range = symbol_data['time'].max() - symbol_data['time'].min()
                print(f"      Период: {symbol_data['time'].min()} - {symbol_data['time'].max()}")
                print(f"      Длительность: {time_range}")
        
        # 7. Проверка ценовых данных
        print("\n🔍 7. Проверка ценовых данных:")
        
        # Проверяем, что high >= low
        invalid_hl = (df['high'] < df['low']).sum()
        if invalid_hl > 0:
            print(f"   ❌ {invalid_hl} записей где high < low")
        else:
            print("   ✅ Все записи: high >= low")
        
        # Проверяем, что high >= open и high >= close
        invalid_ho = (df['high'] < df['open']).sum()
        invalid_hc = (df['high'] < df['close']).sum()
        if invalid_ho > 0:
            print(f"   ❌ {invalid_ho} записей где high < open")
        if invalid_hc > 0:
            print(f"   ❌ {invalid_hc} записей где high < close")
        if invalid_ho == 0 and invalid_hc == 0:
            print("   ✅ Все записи: high >= open и high >= close")
        
        # Проверяем, что low <= open и low <= close
        invalid_lo = (df['low'] > df['open']).sum()
        invalid_lc = (df['low'] > df['close']).sum()
        if invalid_lo > 0:
            print(f"   ❌ {invalid_lo} записей где low > open")
        if invalid_lc > 0:
            print(f"   ❌ {invalid_lc} записей где low > close")
        if invalid_lo == 0 and invalid_lc == 0:
            print("   ✅ Все записи: low <= open и low <= close")
        
        # 8. Проверка объемов
        print("\n🔍 8. Проверка объемов:")
        negative_volume = (df['volume'] < 0).sum()
        if negative_volume > 0:
            print(f"   ❌ {negative_volume} записей с отрицательным объемом")
        else:
            print("   ✅ Все объемы неотрицательные")
        
        # 9. Статистика по символам
        print("\n🔍 9. Статистика по символам:")
        symbol_stats = df.groupby('symbol').agg({
            'id': 'count',
            'time': ['min', 'max'],
            'open': ['min', 'max', 'mean'],
            'close': ['min', 'max', 'mean'],
            'volume': ['min', 'max', 'mean', 'sum']
        }).round(2)
        
        print(symbol_stats.head(10))
        
        # 10. Проверка свежести данных
        print("\n🔍 10. Проверка свежести данных:")
        df['created_at'] = pd.to_datetime(df['created_at'])
        latest_created = df['created_at'].max()
        oldest_created = df['created_at'].min()
        
        print(f"   Самая старая запись: {oldest_created}")
        print(f"   Самая новая запись: {latest_created}")
        
        # Проверяем, что данные не слишком старые
        now = datetime.now()
        data_age = now - latest_created
        if data_age > timedelta(days=1):
            print(f"   ⚠️ Данные устарели на {data_age}")
        else:
            print(f"   ✅ Данные свежие (возраст: {data_age})")
        
        # 11. Общая оценка качества
        print("\n🎯 11. Общая оценка качества:")
        
        quality_score = 0
        max_score = 10
        
        # Проверяем различные аспекты качества
        if len(missing_columns) == 0:
            quality_score += 1
        if missing_data.sum() == 0:
            quality_score += 1
        if duplicate_ids == 0:
            quality_score += 1
        if len(unknown_symbols) == 0:
            quality_score += 1
        if invalid_hl == 0:
            quality_score += 1
        if invalid_ho == 0 and invalid_hc == 0:
            quality_score += 1
        if invalid_lo == 0 and invalid_lc == 0:
            quality_score += 1
        if negative_volume == 0:
            quality_score += 1
        if data_age <= timedelta(days=1):
            quality_score += 1
        if len(df) > 0:
            quality_score += 1
        
        quality_percentage = (quality_score / max_score) * 100
        
        print(f"   Оценка качества: {quality_score}/{max_score} ({quality_percentage:.1f}%)")
        
        if quality_percentage >= 90:
            print("   🏆 Отличное качество данных!")
        elif quality_percentage >= 80:
            print("   ✅ Хорошее качество данных")
        elif quality_percentage >= 70:
            print("   ⚠️ Удовлетворительное качество данных")
        else:
            print("   ❌ Плохое качество данных")
        
        conn.close()
        print("\n✅ Тест качества данных завершен!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_1hour_quality()
