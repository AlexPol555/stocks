#!/usr/bin/env python3
"""List available tickers using project modules."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.utils import open_database_connection
    from core.database import create_tables
    
    def list_tickers():
        """List all available tickers from database."""
        print("📊 Available Tickers in Database")
        print("=" * 50)
        
        try:
            # Open database connection
            conn = open_database_connection()
            
            # Create tables if they don't exist
            create_tables(conn)
            
            cursor = conn.cursor()
            
            # Get tickers from companies table
            cursor.execute("SELECT DISTINCT contract_code FROM companies ORDER BY contract_code")
            tickers = [row[0] for row in cursor.fetchall()]
            
            if not tickers:
                print("❌ No tickers found in database")
                print("💡 Try running data loading first")
                return
            
            print(f"✅ Found {len(tickers)} tickers:")
            print()
            
            # Display tickers in columns
            for i, ticker in enumerate(tickers, 1):
                print(f"{i:2d}. {ticker}")
            
            print()
            print("💡 Usage in ML modules:")
            print("   - Use any of these tickers in ML prediction functions")
            print("   - Example: ml_manager.predict_price_movement('SBER')")
            
            # Get additional statistics
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT c.contract_code) as total_tickers,
                    COUNT(dd.id) as total_data_points,
                    MIN(dd.date) as earliest_date,
                    MAX(dd.date) as latest_date
                FROM companies c
                LEFT JOIN daily_data dd ON c.id = dd.company_id
            """)
            
            stats = cursor.fetchone()
            if stats:
                total_tickers, total_data_points, earliest_date, latest_date = stats
                print()
                print("📊 Database Statistics:")
                print(f"   Total tickers: {total_tickers}")
                print(f"   Total data points: {total_data_points or 0}")
                print(f"   Date range: {earliest_date or 'N/A'} to {latest_date or 'N/A'}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error accessing database: {e}")
            print("💡 Make sure the database file exists and is accessible")
    
    if __name__ == "__main__":
        list_tickers()
        
except ImportError as e:
    print(f"❌ Could not import project modules: {e}")
    print("💡 Make sure you're running from the project root directory")
