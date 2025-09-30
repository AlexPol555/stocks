#!/usr/bin/env python3
"""
Анализ колонки 'value' в различных таблицах базы данных
"""

import sqlite3
from pathlib import Path

def analyze_value_column():
    """Анализирует колонку value в различных таблицах"""
    print("=" * 80)
    print("АНАЛИЗ КОЛОНКИ 'value' В РАЗЛИЧНЫХ ТАБЛИЦАХ")
    print("=" * 80)
    
    db_path = Path("stock_data.db")
    if not db_path.exists():
        print("ERROR: База данных stock_data.db не найдена!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\nНайдено таблиц: {len(tables)}")
        
        # Ищем таблицы с колонкой 'value'
        tables_with_value = []
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            if 'value' in column_names:
                tables_with_value.append(table)
        
        print(f"\nТаблицы с колонкой 'value': {len(tables_with_value)}")
        for table in tables_with_value:
            print(f"  - {table}")
        
        # Анализируем каждую таблицу с колонкой value
        for table in tables_with_value:
            print(f"\n" + "=" * 60)
            print(f"АНАЛИЗ ТАБЛИЦЫ: {table}")
            print("=" * 60)
            
            # Получаем структуру таблицы
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            print(f"\nСтруктура таблицы {table}:")
            print("-" * 40)
            for col in columns:
                col_id, name, data_type, not_null, default_val, pk = col
                print(f"  {name:15} | {data_type:10} | {'NOT NULL' if not_null else 'NULL':8} | {'PK' if pk else ''}")
            
            # Статистика по колонке value
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            total_count = cursor.fetchone()[0]
            
            cursor.execute(f"""
                SELECT 
                    COUNT(value) as non_null_count,
                    COUNT(*) - COUNT(value) as null_count,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    AVG(value) as avg_value
                FROM {table}
            """)
            stats = cursor.fetchone()
            non_null, null_count, min_val, max_val, avg_val = stats
            
            print(f"\nСтатистика по колонке 'value':")
            print("-" * 40)
            print(f"  Всего записей: {total_count:,}")
            print(f"  Не NULL значений: {non_null:,}")
            print(f"  NULL значений: {null_count:,}")
            if non_null > 0:
                print(f"  Минимальное значение: {min_val}")
                print(f"  Максимальное значение: {max_val}")
                print(f"  Среднее значение: {avg_val:.4f}")
            
            # Примеры значений
            if non_null > 0:
                print(f"\nПримеры значений (первые 10):")
                print("-" * 40)
                cursor.execute(f"SELECT * FROM {table} WHERE value IS NOT NULL LIMIT 10")
                examples = cursor.fetchall()
                
                if examples:
                    # Заголовки колонок
                    headers = [col[1] for col in columns]
                    print("  " + " | ".join(f"{h:12}" for h in headers))
                    print("  " + "-" * (len(headers) * 15))
                    
                    for row in examples:
                        formatted_row = []
                        for i, val in enumerate(row):
                            if val is None:
                                formatted_row.append("NULL")
                            elif isinstance(val, float):
                                formatted_row.append(f"{val:.2f}")
                            else:
                                formatted_row.append(str(val))
                        print("  " + " | ".join(f"{str(v):12}" for v in formatted_row))
            
            # Анализ уникальных значений value
            if non_null > 0:
                cursor.execute(f"SELECT COUNT(DISTINCT value) FROM {table} WHERE value IS NOT NULL")
                unique_values = cursor.fetchone()[0]
                print(f"\nУникальных значений value: {unique_values:,}")
                
                # Топ-10 наиболее частых значений
                cursor.execute(f"""
                    SELECT value, COUNT(*) as count
                    FROM {table}
                    WHERE value IS NOT NULL
                    GROUP BY value
                    ORDER BY count DESC
                    LIMIT 10
                """)
                top_values = cursor.fetchall()
                
                if top_values:
                    print(f"\nТоп-10 наиболее частых значений:")
                    print("-" * 40)
                    for value, count in top_values:
                        print(f"  {value:12} | {count:,} раз")
        
        # Специальный анализ для таблицы metrics
        if 'metrics' in tables_with_value:
            print(f"\n" + "=" * 60)
            print("СПЕЦИАЛЬНЫЙ АНАЛИЗ ТАБЛИЦЫ metrics")
            print("=" * 60)
            
            # Анализируем типы метрик
            cursor.execute("""
                SELECT metric_type, COUNT(*) as count, 
                       MIN(value1) as min_val, MAX(value1) as max_val, AVG(value1) as avg_val
                FROM metrics 
                WHERE value1 IS NOT NULL
                GROUP BY metric_type
                ORDER BY count DESC
            """)
            metric_types = cursor.fetchall()
            
            print(f"\nТипы метрик в таблице metrics:")
            print("-" * 50)
            for metric_type, count, min_val, max_val, avg_val in metric_types:
                print(f"  {metric_type:20} | {count:,} записей | мин: {min_val:.2f} | макс: {max_val:.2f} | среднее: {avg_val:.2f}")
            
            # Примеры записей metrics
            print(f"\nПримеры записей из metrics:")
            print("-" * 50)
            cursor.execute("SELECT * FROM metrics LIMIT 5")
            examples = cursor.fetchall()
            
            if examples:
                cursor.execute("PRAGMA table_info(metrics)")
                columns = cursor.fetchall()
                headers = [col[1] for col in columns]
                print("  " + " | ".join(f"{h:12}" for h in headers))
                print("  " + "-" * (len(headers) * 15))
                
                for row in examples:
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

if __name__ == "__main__":
    print("Запуск анализа колонки 'value'...")
    analyze_value_column()


