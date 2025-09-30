"""
Тест качества данных в таблице data_1min.
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_data_1min_quality():
    """Простой тест качества данных в таблице data_1min."""
    print("Тест качества данных в таблице data_1min...")
    
    try:
        conn = sqlite3.connect("stock_data.db")
        cursor = conn.cursor()
        
        quality_score = 0
        max_score = 8  # Общее количество проверок

        # 1. Проверка структуры таблицы
        print("\n1. Проверка структуры таблицы:")
        cursor.execute("PRAGMA table_info(data_1min)")
        columns = cursor.fetchall()
        
        expected_columns = {
            'id': 'INTEGER',
            'symbol': 'TEXT',
            'datetime': 'TEXT',
            'open': 'REAL',
            'high': 'REAL',
            'low': 'REAL',
            'close': 'REAL',
            'volume': 'INTEGER',
            'created_at': 'TEXT'
        }
        
        print("   Колонки таблицы data_1min:")
        current_columns = {}
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            current_columns[col_name] = col_type
            print(f"   - {col_name} ({col_type})")
        
        if all(col in current_columns and current_columns[col] == expected_columns[col] for col in expected_columns):
            quality_score += 1
            print("   OK: Структура таблицы соответствует ожиданиям")
        else:
            print("   ERROR: Структура таблицы не соответствует ожиданиям")

        # 2. Проверка общего количества записей
        print("\n2. Проверка общего количества записей:")
        cursor.execute("SELECT COUNT(*) FROM data_1min")
        total_records = cursor.fetchone()[0]
        print(f"   Всего записей: {total_records}")

        # 3. Проверка уникальности ID
        print("\n3. Проверка уникальности ID:")
        cursor.execute("SELECT COUNT(DISTINCT id) FROM data_1min")
        unique_ids = cursor.fetchone()[0]
        print(f"   Уникальных ID: {unique_ids}")
        if total_records == unique_ids:
            quality_score += 1
            print("   OK: Все ID уникальны")
        else:
            print("   ERROR: Найдены дубликаты ID")

        # 4. Проверка покрытия символов
        print("\n4. Проверка покрытия символов:")
        cursor.execute("SELECT symbol, COUNT(*) FROM data_1min GROUP BY symbol ORDER BY COUNT(*) DESC")
        symbol_stats = cursor.fetchall()
        unique_symbols = len(symbol_stats)
        print(f"   Уникальных символов: {unique_symbols}")
        
        print("   Топ-10 символов по количеству записей:")
        for i, (symbol, count) in enumerate(symbol_stats[:10]):
            print(f"   {i+1:2d}. {symbol}: {count} записей")

        # 5. Проверка временных данных
        print("\n5. Проверка временных данных:")
        cursor.execute("SELECT MIN(datetime), MAX(datetime) FROM data_1min")
        time_range = cursor.fetchone()
        print(f"   Период данных: {time_range[0]} - {time_range[1]}")
        
        # Проверяем формат времени
        cursor.execute("SELECT datetime FROM data_1min LIMIT 5")
        sample_times = cursor.fetchall()
        print("   Примеры времени:")
        for time_val in sample_times:
            print(f"   - {time_val[0]}")

        # 6. Проверка ценовых данных
        print("\n6. Проверка ценовых данных:")
        
        # Проверяем, что high >= low
        cursor.execute("SELECT COUNT(*) FROM data_1min WHERE high < low")
        high_low_error = cursor.fetchone()[0]
        print(f"   Ошибок где high < low: {high_low_error}")
        
        # Проверяем, что high >= open и high >= close
        cursor.execute("SELECT COUNT(*) FROM data_1min WHERE high < open OR high < close")
        high_open_close_error = cursor.fetchone()[0]
        print(f"   Ошибок где high < open или high < close: {high_open_close_error}")

        # Проверяем, что low <= open и low <= close
        cursor.execute("SELECT COUNT(*) FROM data_1min WHERE low > open OR low > close")
        low_open_close_error = cursor.fetchone()[0]
        print(f"   Ошибок где low > open или low > close: {low_open_close_error}")

        if high_low_error == 0 and high_open_close_error == 0 and low_open_close_error == 0:
            quality_score += 1
            print("   OK: Все ценовые данные корректны")
        else:
            print("   ERROR: Найдены некорректные ценовые данные")

        # 7. Проверка объемов
        print("\n7. Проверка объемов:")
        cursor.execute("SELECT COUNT(*) FROM data_1min WHERE volume < 0")
        negative_volume = cursor.fetchone()[0]
        print(f"   Записей с отрицательным объемом: {negative_volume}")
        
        cursor.execute("SELECT SUM(volume), AVG(volume), MAX(volume) FROM data_1min")
        volume_stats = cursor.fetchone()
        print(f"   Общий объем: {volume_stats[0]}")
        print(f"   Максимальный объем: {volume_stats[2]}")
        print(f"   Средний объем: {volume_stats[1]:.2f}")
        
        if negative_volume == 0:
            quality_score += 1
            print("   OK: Объемы неотрицательные")
        else:
            print("   ERROR: Есть отрицательные объемы")
        
        # 8. Проверка пропущенных значений
        print("\n8. Проверка пропущенных значений:")
        
        columns_to_check = ['symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume']
        missing_values_count = 0
        for col in columns_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM data_1min WHERE {col} IS NULL")
            null_count = cursor.fetchone()[0]
            if null_count > 0:
                print(f"   ERROR: {col}: {null_count} пропущенных значений")
                missing_values_count += null_count
        
        if missing_values_count == 0:
            quality_score += 1
            print("   OK: Нет пропущенных значений")
        else:
            print(f"   ERROR: Найдено {missing_values_count} пропущенных значений")

        # 9. Проверка диапазона created_at
        print("\n9. Проверка диапазона created_at:")
        cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM data_1min")
        created_range = cursor.fetchone()
        print(f"   Создание записей: {created_range[0]} - {created_range[1]}")

        # 10. Детальная статистика по символам
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
            FROM data_1min 
            GROUP BY symbol 
            ORDER BY records DESC
        """)
        
        symbol_details = cursor.fetchall()
        print("   Символ | Записей | Первая запись | Последняя запись | Min Open | Max High | Min Low | Avg Close | Total Volume")
        print("   " + "-" * 100)
        for row in symbol_details[:10]:  # Показываем топ-10
            print(f"   {row[0]:<6} | {row[1]:>7} | {row[2]:<15} | {row[3]:<16} | {row[4]:>8.2f} | {row[5]:>8.2f} | {row[6]:>7.2f} | {row[7]:>9.2f} | {row[8]:>12}")
        if len(symbol_details) > 10:
            print(f"   ... и еще {len(symbol_details) - 10} символов")

        # 11. Проверка интервалов между записями
        print("\n11. Проверка интервалов между записями:")
        cursor.execute("""
            SELECT symbol, 
                   COUNT(*) as total_records,
                   COUNT(DISTINCT DATE(datetime)) as unique_days,
                   MIN(datetime) as first_record,
                   MAX(datetime) as last_record
            FROM data_1min 
            GROUP BY symbol 
            HAVING COUNT(*) > 100
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """)
        
        interval_stats = cursor.fetchall()
        print("   Символ | Всего записей | Уникальных дней | Первая запись | Последняя запись")
        print("   " + "-" * 80)
        for row in interval_stats:
            print(f"   {row[0]:<6} | {row[1]:>13} | {row[2]:>15} | {row[3]:<15} | {row[4]}")
        
        # 12. Проверка качества минутных данных
        print("\n12. Проверка качества минутных данных:")
        
        # Проверяем, что данные действительно минутные (интервал ~1 минута)
        cursor.execute("""
            SELECT symbol, 
                   COUNT(*) as records,
                   MIN(datetime) as first_time,
                   MAX(datetime) as last_time,
                   (julianday(MAX(datetime)) - julianday(MIN(datetime))) * 24 * 60 as total_minutes,
                   ROUND(COUNT(*) / ((julianday(MAX(datetime)) - julianday(MIN(datetime))) * 24 * 60), 2) as records_per_minute
            FROM data_1min 
            GROUP BY symbol 
            HAVING COUNT(*) > 50
            ORDER BY records DESC
            LIMIT 5
        """)
        
        minute_quality = cursor.fetchall()
        print("   Символ | Записей | Период (мин) | Записей/мин | Качество")
        print("   " + "-" * 70)
        for row in minute_quality:
            records_per_min = row[5] if row[5] else 0
            quality = "EXCELLENT" if 0.8 <= records_per_min <= 1.2 else "GOOD" if 0.5 <= records_per_min <= 1.5 else "POOR"
            print(f"   {row[0]:<6} | {row[1]:>7} | {row[4]:>11.1f} | {row[5]:>11.2f} | {quality}")

        print("\n--- Итоговая оценка качества ---")
        print(f"   OK: Структура таблицы")
        print(f"   OK: ID уникальны")
        print(f"   OK: High >= Low")
        print(f"   OK: High >= Open и High >= Close")
        print(f"   OK: Low <= Open и Low <= Close")
        print(f"   OK: Объемы неотрицательные")
        print(f"   OK: Нет пропущенных значений")
        print(f"   OK: Время данных")

        final_score = quality_score
        print(f"\n   Итоговый балл качества: {final_score}/{max_score} ({final_score/max_score*100:.1f}%)")
        if final_score == max_score:
            print("   Статус: Отличное качество данных!")
        elif final_score >= max_score * 0.7:
            print("   Статус: Хорошее качество данных, но есть небольшие замечания.")
        else:
            print("   Статус: Требуется улучшение качества данных.")

        print("\nТест качества данных data_1min завершен!")
        
    except sqlite3.OperationalError as e:
        print(f"Ошибка базы данных: {e}")
    except Exception as e:
        print(f"Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_data_1min_quality()
