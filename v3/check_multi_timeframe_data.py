#!/usr/bin/env python3
"""
Check multi-timeframe data tables.
Проверка данных в таблицах разных таймфреймов.
"""

import sqlite3
from pathlib import Path

def check_multi_timeframe_tables():
    """Проверка данных в таблицах разных таймфреймов."""
    
    db_path = Path("stock_data.db")
    if not db_path.exists():
        print("Database not found!")
        return
    
    symbols = ['VSMO', 'UNAC', 'CNRU', 'VKCO', 'MGNT']
    timeframes = ['1d', '1hour', '1min', '5min', '15min', '1sec', 'tick']
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("Checking multi-timeframe data tables:")
        print("=" * 50)
        
        for timeframe in timeframes:
            table_name = f"data_{timeframe}"
            
            # Проверяем существование таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                print(f"{table_name}: Table not found")
                continue
            
            # Получаем общее количество записей
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_count = cursor.fetchone()[0]
            print(f"{table_name}: {total_count} total records")
            
            # Проверяем данные для каждого символа
            for symbol in symbols:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE symbol = ?", (symbol,))
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"  {symbol}: {count} records")
                else:
                    print(f"  {symbol}: No data")
            
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

def check_daily_data_fallback():
    """Проверка fallback таблицы daily_data."""
    
    db_path = Path("stock_data.db")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("Checking daily_data fallback table:")
        print("=" * 40)
        
        symbols = ['VSMO', 'UNAC', 'CNRU', 'VKCO', 'MGNT']
        
        for symbol in symbols:
            cursor.execute("""
                SELECT COUNT(*) FROM daily_data dd 
                JOIN companies c ON dd.company_id = c.id 
                WHERE c.ticker = ?
            """, (symbol,))
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  {symbol}: {count} daily_data records")
            else:
                print(f"  {symbol}: No daily_data")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Основная функция."""
    
    print("Multi-Timeframe Data Check")
    print("=" * 60)
    
    check_multi_timeframe_tables()
    print()
    check_daily_data_fallback()
    
    print("\nRecommendations:")
    print("1. If data_1d is empty, use daily_data as fallback")
    print("2. If other timeframes are empty, run data updater")
    print("3. Check data_update_settings table for update configuration")

if __name__ == "__main__":
    main()




