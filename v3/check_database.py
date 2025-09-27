#!/usr/bin/env python3
"""Simple database check script."""

import sqlite3
from pathlib import Path

def check_database():
    """Check database contents."""
    db_path = Path("stock_data.db")
    if not db_path.exists():
        print("❌ Database not found!")
        return
    
    print("🔍 Checking database contents...")
    print("=" * 50)
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    try:
        # Check tables
        tables = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """).fetchall()
        
        print(f"Tables: {[row[0] for row in tables]}")
        
        # Check news pipeline tables
        pipeline_tables = ['articles', 'sources', 'tickers', 'news_tickers', 'processing_runs']
        for table in pipeline_tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"{table}: {count} rows")
            except Exception as e:
                print(f"{table}: ERROR - {e}")
        
        # Check confirmed tickers
        try:
            confirmed_count = conn.execute("""
                SELECT COUNT(*) FROM news_tickers WHERE confirmed = 1
            """).fetchone()[0]
            print(f"Confirmed tickers: {confirmed_count}")
            
            if confirmed_count > 0:
                # Show some examples
                examples = conn.execute("""
                    SELECT a.title, t.ticker, nt.score, nt.method
                    FROM news_tickers nt
                    JOIN articles a ON a.id = nt.news_id
                    JOIN tickers t ON t.id = nt.ticker_id
                    WHERE nt.confirmed = 1
                    LIMIT 5
                """).fetchall()
                
                print("\nExamples of confirmed tickers:")
                for row in examples:
                    print(f"  {row['title'][:50]}... -> {row['ticker']} (score: {row['score']}, method: {row['method']})")
                    
        except Exception as e:
            print(f"Confirmed tickers: ERROR - {e}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_database()
