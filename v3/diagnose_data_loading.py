#!/usr/bin/env python3
"""
Diagnose Data Loading.
Диагностика загрузки данных.
"""

import sqlite3
import os
from datetime import datetime, timedelta

def diagnose_data_loading():
    """Диагностика загрузки данных."""
    db_path = "stock_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔍 Диагностика загрузки данных...")
        print("=" * 60)
        
        # 1. Проверяем количество компаний
        cursor.execute("SELECT COUNT(*) FROM companies")
        companies_count = cursor.fetchone()[0]
        print(f"📊 Всего компаний в БД: {companies_count}")
        
        # 2. Проверяем таблицы данных
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'data_%'")
        data_tables = cursor.fetchall()
        
        print(f"\n📈 Таблицы данных: {len(data_tables)}")
        
        total_records = 0
        for table in data_tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            total_records += count
            
            # Получаем информацию о символах
            cursor.execute(f"SELECT COUNT(DISTINCT symbol) FROM {table_name}")
            symbols_count = cursor.fetchone()[0]
            
            # Получаем последнюю запись
            cursor.execute(f"SELECT MAX(datetime) FROM {table_name}")
            last_record = cursor.fetchone()[0]
            
            print(f"   - {table_name}:")
            print(f"     * Записей: {count}")
            print(f"     * Символов: {symbols_count}")
            print(f"     * Последняя запись: {last_record}")
            
            # Показываем примеры символов
            if symbols_count > 0:
                cursor.execute(f"SELECT DISTINCT symbol FROM {table_name} LIMIT 5")
                symbols = [row[0] for row in cursor.fetchall()]
                print(f"     * Примеры символов: {', '.join(symbols)}")
        
        print(f"\n📊 Общее количество записей: {total_records}")
        
        # 3. Проверяем, есть ли данные по разным таймфреймам
        print(f"\n⏰ Анализ по таймфреймам:")
        timeframes = ['1d', '1h', '1m', '5m', '15m']
        
        for tf in timeframes:
            table_name = f"data_{tf.replace('m', 'min').replace('h', 'hour')}"
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if cursor.fetchone():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                cursor.execute(f"SELECT COUNT(DISTINCT symbol) FROM {table_name}")
                symbols = cursor.fetchone()[0]
                print(f"   - {tf}: {count} записей, {symbols} символов")
            else:
                print(f"   - {tf}: таблица не существует")
        
        # 4. Проверяем распределение данных по символам
        print(f"\n📊 Распределение данных по символам:")
        for table in data_tables:
            table_name = table[0]
            cursor.execute(f"""
                SELECT symbol, COUNT(*) as count 
                FROM {table_name} 
                GROUP BY symbol 
                ORDER BY count DESC 
                LIMIT 10
            """)
            top_symbols = cursor.fetchall()
            
            if top_symbols:
                print(f"   {table_name} (топ-10):")
                for symbol, count in top_symbols:
                    print(f"     - {symbol}: {count} записей")
        
        # 5. Проверяем временной диапазон данных
        print(f"\n📅 Временной диапазон данных:")
        for table in data_tables:
            table_name = table[0]
            cursor.execute(f"SELECT MIN(datetime), MAX(datetime) FROM {table_name}")
            min_date, max_date = cursor.fetchone()
            if min_date and max_date:
                print(f"   - {table_name}: {min_date} - {max_date}")
        
        # 6. Рекомендации
        print(f"\n💡 Рекомендации:")
        
        if companies_count == 0:
            print("   ❌ Нет компаний в БД. Запустите загрузку данных.")
        elif total_records == 0:
            print("   ❌ Нет данных в таблицах. Запустите обновление данных.")
        elif total_records < companies_count * 10:
            print("   ⚠️ Мало данных. Возможно, обновление не завершено.")
            print("   💡 Запустите обновление данных для всех таймфреймов.")
        else:
            print("   ✅ Данные загружены успешно!")
        
        if len(data_tables) < 5:
            print("   ⚠️ Не все таймфреймы загружены.")
            print("   💡 Запустите обновление для всех таймфреймов.")
        
    except Exception as e:
        print(f"❌ Ошибка диагностики: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    diagnose_data_loading()
