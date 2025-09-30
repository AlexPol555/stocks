#!/usr/bin/env python3
"""
Debug Database.
Отладка базы данных.
"""

import sqlite3
import os

def debug_database():
    """Отладка базы данных."""
    db_path = "stock_data.db"
    
    if not os.path.exists(db_path):
        print("Database not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("Tables:")
        for table in tables:
            print(f"  {table[0]}")
        
        # Проверяем таблицы данных
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'data_%'")
        data_tables = cursor.fetchall()
        
        print("\nData tables:")
        for table in data_tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  {table_name}: {count} records")
        
        # Проверяем компании
        cursor.execute("SELECT COUNT(*) FROM companies")
        companies_count = cursor.fetchone()[0]
        print(f"\nCompanies: {companies_count}")
        
        # Проверяем структуру companies
        cursor.execute("PRAGMA table_info(companies)")
        columns = cursor.fetchall()
        print("\nCompanies columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    debug_database()
