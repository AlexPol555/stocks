#!/usr/bin/env python3
"""
Check Shares Integration.
Проверка интеграции акций в базе данных.
"""

import sqlite3
import os
from pathlib import Path

def check_shares_integration():
    """Проверить интеграцию акций в базе данных."""
    db_path = "stock_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, есть ли колонка asset_type
        cursor.execute("PRAGMA table_info(companies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'asset_type' not in columns:
            print("❌ Колонка asset_type не найдена")
            print("💡 Запустите интеграцию акций")
            return
        
        # Получаем статистику по типам активов
        cursor.execute("""
            SELECT 
                COALESCE(asset_type, 'unknown') as asset_type,
                COUNT(*) as count
            FROM companies 
            GROUP BY asset_type
            ORDER BY count DESC
        """)
        
        stats = cursor.fetchall()
        
        print("📊 Статистика активов в базе данных:")
        total = 0
        for asset_type, count in stats:
            print(f"   - {asset_type}: {count}")
            total += count
        
        print(f"📊 Всего активов: {total}")
        
        # Проверяем акции
        cursor.execute("SELECT COUNT(*) FROM companies WHERE asset_type = 'shares'")
        shares_count = cursor.fetchone()[0]
        
        if shares_count > 0:
            print(f"✅ Акции интегрированы: {shares_count}")
            
            # Показываем примеры акций
            cursor.execute("""
                SELECT contract_code, name 
                FROM companies 
                WHERE asset_type = 'shares' 
                LIMIT 5
            """)
            examples = cursor.fetchall()
            
            print("📈 Примеры акций:")
            for ticker, name in examples:
                print(f"   - {ticker}: {name}")
        else:
            print("⚠️ Акции не найдены")
            print("💡 Запустите интеграцию акций")
        
        # Проверяем фьючерсы
        cursor.execute("SELECT COUNT(*) FROM companies WHERE asset_type = 'futures' OR asset_type IS NULL")
        futures_count = cursor.fetchone()[0]
        
        if futures_count > 0:
            print(f"✅ Фьючерсы найдены: {futures_count}")
        else:
            print("⚠️ Фьючерсы не найдены")
        
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_shares_integration()
