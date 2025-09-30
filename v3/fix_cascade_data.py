#!/usr/bin/env python3
"""
Fix Cascade Analyzer data issues.
Исправление проблем с данными в каскадном анализаторе.
"""

import sqlite3
from pathlib import Path

def fix_daily_data():
    """Добавить данные daily_data для проблемных символов."""
    
    db_path = Path("stock_data.db")
    if not db_path.exists():
        print("Database not found!")
        return
    
    symbols = ['VSMO', 'UNAC', 'CNRU', 'VKCO', 'MGNT']
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("Adding daily_data entries for symbols...")
        
        for symbol in symbols:
            # Получаем company_id
            cursor.execute("SELECT id FROM companies WHERE ticker = ?", (symbol,))
            company = cursor.fetchone()
            if not company:
                print(f"  ERROR {symbol}: Company not found")
                continue
            
            company_id = company[0]
            
            # Проверяем, есть ли уже данные
            cursor.execute("SELECT COUNT(*) FROM daily_data WHERE company_id = ?", (company_id,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"  OK {symbol}: Already has {count} daily_data entries")
                continue
            
            # Добавляем пустые записи для последних 30 дней
            print(f"  ADDING {symbol}: Adding daily_data entries...")
            
            from datetime import datetime, timedelta
            today = datetime.now().date()
            
            for i in range(30):  # 30 дней назад
                date = today - timedelta(days=i)
                
                cursor.execute("""
                    INSERT OR IGNORE INTO daily_data 
                    (company_id, date, open, close, high, low, volume)
                    VALUES (?, ?, NULL, NULL, NULL, NULL, NULL)
                """, (company_id, date))
            
            print(f"  OK {symbol}: Added 30 daily_data entries")
        
        conn.commit()
        conn.close()
        print("Daily data entries added successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

def check_fix():
    """Проверить исправление."""
    
    db_path = Path("stock_data.db")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        symbols = ['VSMO', 'UNAC', 'CNRU', 'VKCO', 'MGNT']
        
        print("\nChecking fix results:")
        for symbol in symbols:
            cursor.execute("""
                SELECT COUNT(*) FROM daily_data dd 
                JOIN companies c ON dd.company_id = c.id 
                WHERE c.ticker = ?
            """, (symbol,))
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  OK {symbol}: {count} daily_data entries")
            else:
                print(f"  ERROR {symbol}: Still no data")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking: {e}")

def main():
    """Основная функция."""
    
    print("Fixing Cascade Analyzer data issues")
    print("=" * 50)
    
    fix_daily_data()
    check_fix()
    
    print("\n💡 Next steps:")
    print("1. Run auto_update.py to populate with real data")
    print("2. Test cascade analyzer again")
    print("3. Check Tinkoff API key if data still missing")

if __name__ == "__main__":
    main()
