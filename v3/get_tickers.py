#!/usr/bin/env python3
"""Script to get list of available tickers from database."""

import sqlite3
import pandas as pd
from pathlib import Path
import sys

def get_database_path():
    """Get database path from environment or use default."""
    try:
        from core.utils import read_db_path
        return read_db_path()
    except ImportError:
        # Fallback to default path
        return "stock_data.db"

def get_tickers_from_db(db_path=None):
    """Get list of tickers from database."""
    if db_path is None:
        db_path = get_database_path()
    
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get tickers from companies table
        cursor.execute("SELECT DISTINCT contract_code FROM companies ORDER BY contract_code")
        tickers = [row[0] for row in cursor.fetchall()]
        
        # Get additional info
        cursor.execute("""
            SELECT 
                c.contract_code,
                c.name,
                COUNT(dd.id) as data_points,
                MIN(dd.date) as first_date,
                MAX(dd.date) as last_date
            FROM companies c
            LEFT JOIN daily_data dd ON c.id = dd.company_id
            GROUP BY c.id, c.contract_code, c.name
            ORDER BY c.contract_code
        """)
        
        ticker_info = cursor.fetchall()
        
        conn.close()
        
        return tickers, ticker_info
        
    except Exception as e:
        print(f"❌ Error reading database: {e}")
        return [], []

def main():
    """Main function to display tickers."""
    print("📊 Available Tickers in Database")
    print("=" * 50)
    
    db_path = get_database_path()
    print(f"Database: {db_path}")
    print()
    
    tickers, ticker_info = get_tickers_from_db(db_path)
    
    if not tickers:
        print("❌ No tickers found in database")
        return
    
    print(f"✅ Found {len(tickers)} tickers:")
    print()
    
    # Display simple list
    print("📋 Ticker List:")
    for i, ticker in enumerate(tickers, 1):
        print(f"{i:2d}. {ticker}")
    
    print()
    
    # Display detailed info if available
    if ticker_info:
        print("📊 Detailed Information:")
        print("-" * 80)
        print(f"{'Ticker':<12} {'Name':<20} {'Data Points':<12} {'First Date':<12} {'Last Date':<12}")
        print("-" * 80)
        
        for row in ticker_info:
            ticker, name, data_points, first_date, last_date = row
            name = (name or 'N/A')[:20]
            first_date = first_date or 'N/A'
            last_date = last_date or 'N/A'
            data_points = data_points or 0
            
            print(f"{ticker:<12} {name:<20} {data_points:<12} {first_date:<12} {last_date:<12}")
    
    print()
    print("💡 Usage in ML modules:")
    print("   - Use any of these tickers in ML prediction functions")
    print("   - Example: ml_manager.predict_price_movement('SBER')")
    
    # Save to file
    try:
        with open('available_tickers.txt', 'w', encoding='utf-8') as f:
            f.write("Available Tickers in Database\n")
            f.write("=" * 50 + "\n\n")
            for i, ticker in enumerate(tickers, 1):
                f.write(f"{i:2d}. {ticker}\n")
        print(f"💾 Ticker list saved to: available_tickers.txt")
    except Exception as e:
        print(f"⚠️ Could not save to file: {e}")

if __name__ == "__main__":
    main()
