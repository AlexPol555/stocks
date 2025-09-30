#!/usr/bin/env python3
"""
Анализ таблицы metrics и её колонок value1, value2, value3, value4, value5
"""

import sqlite3
from pathlib import Path

def analyze_metrics_table():
    """Анализирует таблицу metrics"""
    print("=" * 80)
    print("АНАЛИЗ ТАБЛИЦЫ metrics")
    print("=" * 80)
    
    db_path = Path("stock_data.db")
    if not db_path.exists():
        print("ERROR: База данных stock_data.db не найдена!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Получаем структуру таблицы metrics
        print("\n1. СТРУКТУРА ТАБЛИЦЫ metrics:")
        print("-" * 50)
        cursor.execute("PRAGMA table_info(metrics)")
        columns = cursor.fetchall()
        
        for col in columns:
            col_id, name, data_type, not_null, default_val, pk = col
            print(f"  {name:15} | {data_type:10} | {'NOT NULL' if not_null else 'NULL':8} | {'PK' if pk else ''}")
        
        # Общая статистика
        print(f"\n2. ОБЩАЯ СТАТИСТИКА:")
        print("-" * 50)
        cursor.execute("SELECT COUNT(*) FROM metrics")
        total_count = cursor.fetchone()[0]
        print(f"  Всего записей: {total_count:,}")
        
        cursor.execute("SELECT COUNT(DISTINCT company_id) FROM metrics")
        unique_companies = cursor.fetchone()[0]
        print(f"  Уникальных компаний: {unique_companies}")
        
        cursor.execute("SELECT COUNT(DISTINCT metric_type) FROM metrics")
        unique_metrics = cursor.fetchone()[0]
        print(f"  Уникальных типов метрик: {unique_metrics}")
        
        # Анализ колонок value1-value5
        print(f"\n3. АНАЛИЗ КОЛОНОК value1-value5:")
        print("-" * 50)
        
        value_columns = ['value1', 'value2', 'value3', 'value4', 'value5']
        for col in value_columns:
            if col in [c[1] for c in columns]:
                cursor.execute(f"""
                    SELECT 
                        COUNT({col}) as non_null_count,
                        COUNT(*) - COUNT({col}) as null_count,
                        MIN({col}) as min_val,
                        MAX({col}) as max_val,
                        AVG({col}) as avg_val
                    FROM metrics
                """)
                stats = cursor.fetchone()
                non_null, null_count, min_val, max_val, avg_val = stats
                
                print(f"\n  {col}:")
                print(f"    Не NULL значений: {non_null:,}")
                print(f"    NULL значений: {null_count:,}")
                if non_null > 0:
                    print(f"    Минимальное: {min_val}")
                    print(f"    Максимальное: {max_val}")
                    print(f"    Среднее: {avg_val:.4f}")
        
        # Анализ типов метрик
        print(f"\n4. АНАЛИЗ ТИПОВ МЕТРИК:")
        print("-" * 50)
        
        cursor.execute("""
            SELECT metric_type, COUNT(*) as count
            FROM metrics
            GROUP BY metric_type
            ORDER BY count DESC
        """)
        metric_types = cursor.fetchall()
        
        for metric_type, count in metric_types:
            print(f"  {metric_type:30} | {count:,} записей")
        
        # Детальный анализ каждого типа метрики
        print(f"\n5. ДЕТАЛЬНЫЙ АНАЛИЗ ТИПОВ МЕТРИК:")
        print("-" * 50)
        
        for metric_type, count in metric_types[:10]:  # Топ-10 типов метрик
            print(f"\n  {metric_type}:")
            print(f"    Количество записей: {count:,}")
            
            # Статистика по value1 для этого типа метрики
            cursor.execute(f"""
                SELECT 
                    COUNT(value1) as non_null_count,
                    MIN(value1) as min_val,
                    MAX(value1) as max_val,
                    AVG(value1) as avg_val
                FROM metrics
                WHERE metric_type = ? AND value1 IS NOT NULL
            """, (metric_type,))
            stats = cursor.fetchone()
            non_null, min_val, max_val, avg_val = stats
            
            if non_null > 0:
                print(f"    value1: {non_null:,} записей, мин: {min_val:.2f}, макс: {max_val:.2f}, среднее: {avg_val:.2f}")
            
            # Примеры записей для этого типа метрики
            cursor.execute(f"""
                SELECT company_id, date, value1, value2, value3, value4, value5
                FROM metrics
                WHERE metric_type = ?
                ORDER BY date DESC
                LIMIT 3
            """, (metric_type,))
            examples = cursor.fetchall()
            
            if examples:
                print(f"    Примеры записей:")
                for row in examples:
                    company_id, date, v1, v2, v3, v4, v5 = row
                    values_str = " | ".join([f"{v:.2f}" if v is not None else "NULL" for v in [v1, v2, v3, v4, v5]])
                    print(f"      ID:{company_id} | {date} | {values_str}")
        
        # Анализ распределения по датам
        print(f"\n6. РАСПРЕДЕЛЕНИЕ ПО ДАТАМ:")
        print("-" * 50)
        
        cursor.execute("""
            SELECT date, COUNT(*) as count
            FROM metrics
            GROUP BY date
            ORDER BY date DESC
            LIMIT 10
        """)
        date_distribution = cursor.fetchall()
        
        for date, count in date_distribution:
            print(f"  {date} | {count:,} записей")
        
        # Анализ компаний с наибольшим количеством метрик
        print(f"\n7. КОМПАНИИ С НАИБОЛЬШИМ КОЛИЧЕСТВОМ МЕТРИК:")
        print("-" * 50)
        
        cursor.execute("""
            SELECT c.contract_code, COUNT(m.id) as metric_count
            FROM metrics m
            JOIN companies c ON m.company_id = c.id
            GROUP BY m.company_id, c.contract_code
            ORDER BY metric_count DESC
            LIMIT 10
        """)
        top_companies = cursor.fetchall()
        
        for contract_code, metric_count in top_companies:
            print(f"  {contract_code:10} | {metric_count:,} метрик")
        
        conn.close()
        print(f"\nOK Анализ таблицы metrics завершен успешно!")
        
    except Exception as e:
        print(f"ERROR Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Запуск анализа таблицы metrics...")
    analyze_metrics_table()


