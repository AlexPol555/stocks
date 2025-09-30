#!/usr/bin/env python3
"""
Check available symbols for cascade analyzer.
Проверка доступных символов для каскадного анализатора.
"""

import sqlite3
from pathlib import Path

def check_available_symbols():
    """Проверка доступных символов."""
    
    db_path = Path("stock_data.db")
    if not db_path.exists():
        print("Database not found!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("Available symbols for cascade analysis:")
        print("=" * 50)
        
        # Проверяем символы из таблицы companies
        cursor.execute("SELECT ticker, figi FROM companies WHERE figi IS NOT NULL AND figi != '' ORDER BY ticker")
        companies = cursor.fetchall()
        
        print(f"Companies in database: {len(companies)}")
        for ticker, figi in companies[:10]:  # Показываем первые 10
            print(f"  {ticker}: {figi}")
        if len(companies) > 10:
            print(f"  ... and {len(companies) - 10} more")
        
        print("\nSymbols with data in different timeframes:")
        
        # Проверяем символы с данными в разных таймфреймах
        timeframes = ['1d', '1hour', '1min', '5min', '15min']
        
        for tf in timeframes:
            table_name = f"data_{tf}"
            cursor.execute(f"SELECT DISTINCT symbol, COUNT(*) as count FROM {table_name} GROUP BY symbol ORDER BY symbol")
            symbols = cursor.fetchall()
            
            print(f"\n{table_name}: {len(symbols)} symbols with data")
            for symbol, count in symbols[:5]:  # Показываем первые 5
                print(f"  {symbol}: {count} records")
            if len(symbols) > 5:
                print(f"  ... and {len(symbols) - 5} more")
        
        # Рекомендуемые символы для тестирования
        print("\nRecommended symbols for testing:")
        recommended = ['VSMO', 'UNAC', 'CNRU', 'VKCO', 'MGNT', 'SBER', 'GAZP', 'LKOH', 'NVTK', 'ROSN']
        
        for symbol in recommended:
            # Проверяем наличие данных
            cursor.execute("SELECT COUNT(*) FROM data_1d WHERE symbol = ?", (symbol,))
            count_1d = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM data_1hour WHERE symbol = ?", (symbol,))
            count_1h = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM data_1min WHERE symbol = ?", (symbol,))
            count_1m = cursor.fetchone()[0]
            
            if count_1d > 0 and count_1h > 0 and count_1m > 0:
                print(f"  {symbol}: READY (1d:{count_1d}, 1h:{count_1h}, 1m:{count_1m})")
            elif count_1d > 0:
                print(f"  {symbol}: PARTIAL (1d:{count_1d}, 1h:{count_1h}, 1m:{count_1m})")
            else:
                print(f"  {symbol}: NO DATA")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Основная функция."""
    
    print("Cascade Analyzer - Available Symbols Check")
    print("=" * 60)
    
    check_available_symbols()
    
    print("\nInstructions:")
    print("1. Select symbols marked as 'READY' for best results")
    print("2. Symbols marked as 'PARTIAL' may work but with limited data")
    print("3. Start with 3-5 symbols for testing")

if __name__ == "__main__":
    main()




