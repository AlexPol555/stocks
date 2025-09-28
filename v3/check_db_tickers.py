import sqlite3
import os

def check_tickers():
    db_path = "stock_data.db"
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if companies table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
        if not cursor.fetchone():
            print("Companies table not found")
            return
        
        # Get tickers
        cursor.execute("SELECT DISTINCT contract_code FROM companies ORDER BY contract_code")
        tickers = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(tickers)} tickers:")
        for i, ticker in enumerate(tickers, 1):
            print(f"{i:2d}. {ticker}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_tickers()
