#!/usr/bin/env python3
"""
Тестовый файл для анализа таблицы data_1d
Проверяет структуру таблицы и анализирует колонку value
"""

import sqlite3
from pathlib import Path
import sys

def check_data_1d_structure():
    """Проверяет структуру таблицы data_1d"""
    print("=" * 60)
    print("АНАЛИЗ ТАБЛИЦЫ data_1d")
    print("=" * 60)
    
    db_path = Path("stock_data.db")
    if not db_path.exists():
        print("ERROR База данных stock_data.db не найдена!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 1. Проверяем структуру таблицы
        print("\n1. СТРУКТУРА ТАБЛИЦЫ data_1d:")
        print("-" * 40)
        cursor.execute("PRAGMA table_info(data_1d)")
        columns = cursor.fetchall()
        
        if not columns:
            print("ERROR Таблица data_1d не существует!")
            return
        
        for col in columns:
            col_id, name, data_type, not_null, default_val, pk = col
            print(f"  {name:15} | {data_type:10} | {'NOT NULL' if not_null else 'NULL':8} | {'PK' if pk else ''}")
        
        # 2. Проверяем количество записей
        print(f"\n2. КОЛИЧЕСТВО ЗАПИСЕЙ:")
        print("-" * 40)
        cursor.execute("SELECT COUNT(*) FROM data_1d")
        total_count = cursor.fetchone()[0]
        print(f"  Всего записей: {total_count:,}")
        
        # 3. Проверяем уникальные символы
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM data_1d")
        unique_symbols = cursor.fetchone()[0]
        print(f"  Уникальных символов: {unique_symbols}")
        
        # 4. Проверяем диапазон дат
        print(f"\n3. ДИАПАЗОН ДАТ:")
        print("-" * 40)
        cursor.execute("SELECT MIN(datetime), MAX(datetime) FROM data_1d")
        min_date, max_date = cursor.fetchone()
        print(f"  От: {min_date}")
        print(f"  До: {max_date}")
        
        # 5. Анализируем колонку value (если существует)
        print(f"\n4. АНАЛИЗ КОЛОНКИ 'value':")
        print("-" * 40)
        
        # Проверяем, есть ли колонка value
        column_names = [col[1] for col in columns]
        if 'value' in column_names:
            print("OK Колонка 'value' найдена!")
            
            # Статистика по колонке value
            cursor.execute("""
                SELECT 
                    COUNT(value) as non_null_count,
                    COUNT(*) - COUNT(value) as null_count,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    AVG(value) as avg_value
                FROM data_1d
            """)
            stats = cursor.fetchone()
            non_null, null_count, min_val, max_val, avg_val = stats
            
            print(f"  Не NULL значений: {non_null:,}")
            print(f"  NULL значений: {null_count:,}")
            print(f"  Минимальное значение: {min_val}")
            print(f"  Максимальное значение: {max_val}")
            print(f"  Среднее значение: {avg_val:.4f}")
            
            # Примеры значений
            print(f"\n  ПРИМЕРЫ ЗНАЧЕНИЙ:")
            cursor.execute("SELECT symbol, datetime, value FROM data_1d WHERE value IS NOT NULL LIMIT 10")
            examples = cursor.fetchall()
            for symbol, date, value in examples:
                print(f"    {symbol} | {date} | {value}")
                
        else:
            print("ERROR Колонка 'value' не найдена в таблице data_1d")
            print("   Доступные колонки:", ", ".join(column_names))
        
        # 6. Проверяем другие колонки с числовыми значениями
        print(f"\n5. АНАЛИЗ ДРУГИХ КОЛОНОК:")
        print("-" * 40)
        
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in column_names:
                cursor.execute(f"""
                    SELECT 
                        COUNT({col}) as non_null_count,
                        MIN({col}) as min_val,
                        MAX({col}) as max_val,
                        AVG({col}) as avg_val
                    FROM data_1d
                """)
                stats = cursor.fetchone()
                non_null, min_val, max_val, avg_val = stats
                print(f"  {col:8}: {non_null:,} записей, мин: {min_val:.2f}, макс: {max_val:.2f}, среднее: {avg_val:.2f}")
        
        # 7. Проверяем дубликаты
        print(f"\n6. ПРОВЕРКА ДУБЛИКАТОВ:")
        print("-" * 40)
        cursor.execute("""
            SELECT symbol, datetime, COUNT(*) as count
            FROM data_1d
            GROUP BY symbol, datetime
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 5
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            print("  Найдены дубликаты:")
            for symbol, date, count in duplicates:
                print(f"    {symbol} | {date} | {count} раз")
        else:
            print("  OK Дубликатов не найдено")
        
        # 8. Примеры данных
        print(f"\n7. ПРИМЕРЫ ДАННЫХ (первые 5 записей):")
        print("-" * 40)
        cursor.execute("SELECT * FROM data_1d ORDER BY datetime DESC LIMIT 5")
        sample_data = cursor.fetchall()
        
        if sample_data:
            # Заголовки колонок
            headers = [col[1] for col in columns]
            print("  " + " | ".join(f"{h:12}" for h in headers))
            print("  " + "-" * (len(headers) * 15))
            
            for row in sample_data:
                formatted_row = []
                for i, val in enumerate(row):
                    if val is None:
                        formatted_row.append("NULL")
                    elif isinstance(val, float):
                        formatted_row.append(f"{val:.2f}")
                    else:
                        formatted_row.append(str(val))
                print("  " + " | ".join(f"{str(v):12}" for v in formatted_row))
        
        conn.close()
        print(f"\nOK Анализ завершен успешно!")
        
    except Exception as e:
        print(f"ERROR Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()

def check_related_tables():
    """Проверяет связанные таблицы"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА СВЯЗАННЫХ ТАБЛИЦ")
    print("=" * 60)
    
    db_path = Path("stock_data.db")
    if not db_path.exists():
        print("ERROR База данных stock_data.db не найдена!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\nНайдено таблиц: {len(tables)}")
        print("Список таблиц:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table:20} | {count:,} записей")
        
        # Проверяем таблицы с данными по времени
        time_tables = [t for t in tables if 'data_' in t]
        if time_tables:
            print(f"\nТаблицы с временными данными:")
            for table in time_tables:
                cursor.execute(f"SELECT COUNT(DISTINCT symbol) FROM {table}")
                symbols = cursor.fetchone()[0]
                print(f"  {table:20} | {symbols} символов")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR Ошибка при проверке таблиц: {e}")

if __name__ == "__main__":
    print("Запуск анализа таблицы data_1d...")
    check_data_1d_structure()
    check_related_tables()
