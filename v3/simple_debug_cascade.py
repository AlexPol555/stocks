#!/usr/bin/env python3
"""
Simple debug script for Cascade Analyzer data issues.
Простая диагностика проблем с данными в каскадном анализаторе.
"""

import sqlite3
from pathlib import Path

def check_database():
    """Проверка базы данных."""
    
    db_path = Path("stock_data.db")
    if not db_path.exists():
        print("❌ База данных stock_data.db не найдена!")
        return
    
    print("✅ База данных найдена")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Проверяем таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"  - {table}")
        
        # Проверяем companies
        if 'companies' in tables:
            cursor.execute("SELECT COUNT(*) FROM companies")
            company_count = cursor.fetchone()[0]
            print(f"\n🏢 Компаний в БД: {company_count}")
            
            # Проверяем конкретные символы
            symbols = ['VSMO', 'UNAC', 'CNRU', 'VKCO', 'MGNT']
            print("\n🔍 Проверка символов:")
            for symbol in symbols:
                cursor.execute("SELECT id, ticker, figi FROM companies WHERE ticker = ?", (symbol,))
                company = cursor.fetchone()
                if company:
                    print(f"  ✅ {symbol}: ID={company[0]}, FIGI={company[2] if company[2] else 'Нет FIGI'}")
                else:
                    print(f"  ❌ {symbol}: Не найден в БД")
        
        # Проверяем daily_data
        if 'daily_data' in tables:
            cursor.execute("SELECT COUNT(*) FROM daily_data")
            daily_count = cursor.fetchone()[0]
            print(f"\n📈 Записей daily_data: {daily_count}")
            
            # Проверяем данные для конкретных символов
            symbols = ['VSMO', 'UNAC', 'CNRU', 'VKCO', 'MGNT']
            print("\n📊 Проверка daily_data для символов:")
            for symbol in symbols:
                cursor.execute("""
                    SELECT COUNT(*) FROM daily_data dd 
                    JOIN companies c ON dd.company_id = c.id 
                    WHERE c.ticker = ?
                """, (symbol,))
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"  ✅ {symbol}: {count} записей")
                else:
                    print(f"  ❌ {symbol}: Нет данных")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")

def main():
    """Основная функция."""
    
    print("Simple Cascade Analyzer Debug")
    print("=" * 50)
    
    check_database()
    
    print("\nPossible causes:")
    print("1. Symbols not added to database")
    print("2. No daily_data for symbols")
    print("3. Missing FIGI mapping")
    print("4. Tinkoff API key issues")
    
    print("\nSolutions:")
    print("1. Add symbols to DB via populate_database.py")
    print("2. Update data via auto_update.py")
    print("3. Check API key in settings")
    print("4. Run full data update")

if __name__ == "__main__":
    main()
