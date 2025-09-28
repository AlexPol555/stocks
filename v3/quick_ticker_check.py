#!/usr/bin/env python3
"""Quick check for available tickers."""

import sqlite3
import os

def main():
    db_path = "stock_data.db"
    
    print("🔍 Checking for available tickers...")
    print(f"Database: {db_path}")
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        print("💡 Please run data loading first to populate the database")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if companies table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
        if not cursor.fetchone():
            print("❌ Companies table not found!")
            print("💡 Database structure is incomplete")
            return
        
        # Get tickers
        cursor.execute("SELECT DISTINCT contract_code FROM companies ORDER BY contract_code")
        tickers = [row[0] for row in cursor.fetchall()]
        
        if not tickers:
            print("❌ No tickers found in companies table!")
            print("💡 Please load company data first")
            return
        
        print(f"✅ Found {len(tickers)} tickers:")
        print()
        
        # Display tickers in a nice format
        for i, ticker in enumerate(tickers, 1):
            print(f"{i:2d}. {ticker}")
        
        print()
        print("💡 Usage:")
        print("   - Use these tickers in ML prediction functions")
        print("   - Example: ml_manager.predict_price_movement('SBER')")
        
        # Get some stats
        cursor.execute("SELECT COUNT(*) FROM daily_data")
        data_count = cursor.fetchone()[0]
        print(f"   - Total data points: {data_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
