#!/usr/bin/env python3
"""
Data Quality Test.
Тест качества данных в таблице data_1hour.
"""

import sqlite3
from datetime import datetime, timedelta

def test_data_quality():
    """Тест качества данных в таблице data_1hour."""
    print("Тест качества данных в таблице data_1hour...")
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect("stock_data.db")
        cursor = conn.cursor()
        
        # 1. Проверка структуры таблицы
        print("\n1. Проверка структуры таблицы:")
        cursor.execute("PRAGMA table_info(data_1hour)")
        columns = cursor.fetchall()
        
        print("   Колонки таблицы data_1hour:")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        # 2. Подсчет записей
        print("\n2. Подсчет записей:")
        cursor.execute("SELECT COUNT(*) FROM data_1hour")
        total_records = cursor.fetchone()[0]
        print(f"   Всего записей: {total_records}")
        
        if total_records == 0:
            print("   ОШИБКА: Таблица data_1hour пуста!")
            return
        
        # 3. Проверка уникальности ID
        print("\n3. Проверка уникальности ID:")
        cursor.execute("SELECT COUNT(DISTINCT id) FROM data_1hour")
        unique_ids = cursor.fetchone()[0]
        print(f"   Уникальных ID: {unique_ids}")
        
        if unique_ids == total_records:
            print("   OK: Все ID уникальны")
        else:
            print(f"   ОШИБКА: Найдено {total_records - unique_ids} дублированных ID")
        
        # 4. Анализ символов
        print("\n4. Анализ символов:")
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM data_1hour")
        unique_symbols_count = cursor.fetchone()[0]
        print(f"   Уникальных символов: {unique_symbols_count}")
        
        cursor.execute("SELECT symbol, COUNT(*) as count FROM data_1hour GROUP BY symbol ORDER BY count DESC")
        symbol_stats = cursor.fetchall()
        
        print("   Топ-10 символов по количеству записей:")
        for i, (symbol, count) in enumerate(symbol_stats[:10]):
            print(f"   {i+1:2d}. {symbol}: {count} записей")
        
        # 5. Проверка временных данных
        print("\n5. Проверка временных данных:")
        cursor.execute("SELECT MIN(datetime), MAX(datetime) FROM data_1hour")
        time_range = cursor.fetchone()
        print(f"   Период данных: {time_range[0]} - {time_range[1]}")
        
        # Проверяем формат времени
        cursor.execute("SELECT datetime FROM data_1hour LIMIT 5")
        sample_times = cursor.fetchall()
        print("   Примеры времени:")
        for time_val in sample_times:
            print(f"   - {time_val[0]}")
        
        # 6. Проверка ценовых данных
        print("\n6. Проверка ценовых данных:")
        
        # Проверяем, что high >= low
        cursor.execute("SELECT COUNT(*) FROM data_1hour WHERE high < low")
        invalid_hl = cursor.fetchone()[0]
        print(f"   Записей где high < low: {invalid_hl}")
        
        # Проверяем, что high >= open
        cursor.execute("SELECT COUNT(*) FROM data_1hour WHERE high < open")
        invalid_ho = cursor.fetchone()[0]
        print(f"   Записей где high < open: {invalid_ho}")
        
        # Проверяем, что high >= close
        cursor.execute("SELECT COUNT(*) FROM data_1hour WHERE high < close")
        invalid_hc = cursor.fetchone()[0]
        print(f"   Записей где high < close: {invalid_hc}")
        
        # Проверяем, что low <= open
        cursor.execute("SELECT COUNT(*) FROM data_1hour WHERE low > open")
        invalid_lo = cursor.fetchone()[0]
        print(f"   Записей где low > open: {invalid_lo}")
        
        # Проверяем, что low <= close
        cursor.execute("SELECT COUNT(*) FROM data_1hour WHERE low > close")
        invalid_lc = cursor.fetchone()[0]
        print(f"   Записей где low > close: {invalid_lc}")
        
        if invalid_hl == 0 and invalid_ho == 0 and invalid_hc == 0 and invalid_lo == 0 and invalid_lc == 0:
            print("   OK: Все ценовые данные корректны")
        else:
            print("   ОШИБКА: Найдены некорректные ценовые данные")
        
        # 7. Проверка объемов
        print("\n7. Проверка объемов:")
        cursor.execute("SELECT COUNT(*) FROM data_1hour WHERE volume < 0")
        negative_volume = cursor.fetchone()[0]
        print(f"   Записей с отрицательным объемом: {negative_volume}")
        
        cursor.execute("SELECT MIN(volume), MAX(volume), AVG(volume) FROM data_1hour")
        volume_stats = cursor.fetchone()
        print(f"   Минимальный объем: {volume_stats[0]}")
        print(f"   Максимальный объем: {volume_stats[1]}")
        print(f"   Средний объем: {volume_stats[2]:.2f}")
        
        # 8. Проверка пропущенных значений
        print("\n8. Проверка пропущенных значений:")
        
        columns_to_check = ['symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume']
        for col in columns_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM data_1hour WHERE {col} IS NULL")
            null_count = cursor.fetchone()[0]
            if null_count > 0:
                print(f"   ОШИБКА: {col}: {null_count} пропущенных значений")
            else:
                print(f"   OK: {col}: пропущенных значений нет")
        
        # 9. Проверка свежести данных
        print("\n9. Проверка свежести данных:")
        cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM data_1hour")
        created_range = cursor.fetchone()
        print(f"   Создание записей: {created_range[0]} - {created_range[1]}")
        
        # 10. Статистика по символам
        print("\n10. Детальная статистика по символам:")
        cursor.execute("""
            SELECT symbol, 
                   COUNT(*) as records,
                   MIN(datetime) as first_time,
                   MAX(datetime) as last_time,
                   MIN(open) as min_open,
                   MAX(high) as max_high,
                   MIN(low) as min_low,
                   AVG(close) as avg_close,
                   SUM(volume) as total_volume
            FROM data_1hour 
            GROUP BY symbol 
            ORDER BY records DESC
        """)
        
        symbol_details = cursor.fetchall()
        print("   Символ | Записей | Первая запись | Последняя запись | Min Open | Max High | Min Low | Avg Close | Total Volume")
        print("   " + "-" * 100)
        
        for row in symbol_details[:10]:  # Показываем топ-10
            symbol, records, first_time, last_time, min_open, max_high, min_low, avg_close, total_volume = row
            print(f"   {symbol:6s} | {records:7d} | {first_time:12s} | {last_time:12s} | {min_open:8.2f} | {max_high:8.2f} | {min_low:7.2f} | {avg_close:9.2f} | {total_volume:11.0f}")
        
        # 11. Общая оценка качества
        print("\n11. Общая оценка качества:")
        
        quality_score = 0
        max_score = 8
        
        # Проверяем различные аспекты качества
        if unique_ids == total_records:
            quality_score += 1
            print("   OK: ID уникальны")
        else:
            print("   ОШИБКА: Есть дублированные ID")
        
        if invalid_hl == 0:
            quality_score += 1
            print("   OK: High >= Low")
        else:
            print("   ОШИБКА: Есть записи где High < Low")
        
        if invalid_ho == 0 and invalid_hc == 0:
            quality_score += 1
            print("   OK: High >= Open и High >= Close")
        else:
            print("   ОШИБКА: Есть записи где High < Open или High < Close")
        
        if invalid_lo == 0 and invalid_lc == 0:
            quality_score += 1
            print("   OK: Low <= Open и Low <= Close")
        else:
            print("   ОШИБКА: Есть записи где Low > Open или Low > Close")
        
        if negative_volume == 0:
            quality_score += 1
            print("   OK: Объемы неотрицательные")
        else:
            print("   ОШИБКА: Есть отрицательные объемы")
        
        # Проверяем пропущенные значения
        cursor.execute("SELECT COUNT(*) FROM data_1hour WHERE symbol IS NULL OR datetime IS NULL OR open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR volume IS NULL")
        missing_values = cursor.fetchone()[0]
        if missing_values == 0:
            quality_score += 1
            print("   OK: Нет пропущенных значений")
        else:
            print(f"   ОШИБКА: Есть {missing_values} пропущенных значений")
        
        if total_records > 0:
            quality_score += 1
            print("   OK: Есть данные")
        else:
            print("   ОШИБКА: Нет данных")
        
        if unique_symbols_count > 0:
            quality_score += 1
            print("   OK: Есть символы")
        else:
            print("   ОШИБКА: Нет символов")
        
        quality_percentage = (quality_score / max_score) * 100
        
        print(f"\n   Оценка качества: {quality_score}/{max_score} ({quality_percentage:.1f}%)")
        
        if quality_percentage >= 90:
            print("   ОТЛИЧНО: Качество данных превосходное!")
        elif quality_percentage >= 80:
            print("   ХОРОШО: Качество данных хорошее")
        elif quality_percentage >= 70:
            print("   УДОВЛЕТВОРИТЕЛЬНО: Качество данных приемлемое")
        else:
            print("   ПЛОХО: Качество данных требует улучшения")
        
        conn.close()
        print("\nТест качества данных завершен!")
        
    except Exception as e:
        print(f"ОШИБКА тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_quality()
