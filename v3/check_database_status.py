#!/usr/bin/env python3
"""
Check Database Status.
Проверка статуса базы данных и таблиц.
"""

import sqlite3
import os
from datetime import datetime

def check_database_status():
    """Проверить статус базы данных."""
    db_path = "stock_data.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔍 Проверка базы данных...")
        print("=" * 50)
        
        # 1. Проверяем таблицы данных
        print("📊 Таблицы данных:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'data_%'")
        data_tables = cursor.fetchall()
        
        if data_tables:
            for table in data_tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"   - {table_name}: {count} записей")
        else:
            print("   ❌ Таблицы данных не найдены")
        
        print()
        
        # 2. Проверяем компании
        print("🏢 Компании:")
        cursor.execute("SELECT COUNT(*) FROM companies")
        companies_count = cursor.fetchone()[0]
        print(f"   - Всего компаний: {companies_count}")
        
        if companies_count > 0:
            # Показываем примеры
            cursor.execute("SELECT contract_code, asset_type FROM companies LIMIT 10")
            examples = cursor.fetchall()
            print("   - Примеры:")
            for contract_code, asset_type in examples:
                print(f"     * {contract_code} ({asset_type or 'unknown'})")
        
        print()
        
        # 3. Проверяем структуру таблицы companies
        print("🔧 Структура таблицы companies:")
        cursor.execute("PRAGMA table_info(companies)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        print()
        
        # 4. Проверяем последние обновления
        print("⏰ Последние обновления:")
        for table_name, _ in data_tables:
            try:
                cursor.execute(f"SELECT MAX(datetime) FROM {table_name}")
                last_update = cursor.fetchone()[0]
                if last_update:
                    print(f"   - {table_name}: {last_update}")
                else:
                    print(f"   - {table_name}: нет данных")
            except Exception as e:
                print(f"   - {table_name}: ошибка - {e}")
        
        print()
        
        # 5. Проверяем типы активов
        print("📈 Типы активов:")
        cursor.execute("""
            SELECT 
                COALESCE(asset_type, 'unknown') as asset_type,
                COUNT(*) as count
            FROM companies 
            GROUP BY asset_type
            ORDER BY count DESC
        """)
        asset_stats = cursor.fetchall()
        
        for asset_type, count in asset_stats:
            print(f"   - {asset_type}: {count}")
        
        print()
        print("✅ Проверка завершена")
        
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_database_status()
