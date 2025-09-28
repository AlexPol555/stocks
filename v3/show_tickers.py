#!/usr/bin/env python3
"""Show available tickers using Streamlit."""

import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

def main():
    st.title("📊 Available Tickers in Database")
    
    db_path = "stock_data.db"
    
    if not Path(db_path).exists():
        st.error(f"Database file {db_path} not found")
        st.info("Please run data loading first to populate the database")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Get tickers
        query = "SELECT DISTINCT contract_code FROM companies ORDER BY contract_code"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            st.warning("No tickers found in database")
            st.info("Try running data loading first")
            return
        
        st.success(f"Found {len(df)} tickers in database")
        
        # Display tickers
        st.subheader("📋 Ticker List")
        
        # Create columns for better display
        cols = st.columns(3)
        for i, ticker in enumerate(df['contract_code']):
            with cols[i % 3]:
                st.write(f"{i+1:2d}. {ticker}")
        
        # Get additional statistics
        stats_query = """
            SELECT 
                COUNT(DISTINCT c.contract_code) as total_tickers,
                COUNT(dd.id) as total_data_points,
                MIN(dd.date) as earliest_date,
                MAX(dd.date) as latest_date
            FROM companies c
            LEFT JOIN daily_data dd ON c.id = dd.company_id
        """
        
        stats_df = pd.read_sql_query(stats_query, conn)
        stats = stats_df.iloc[0]
        
        st.subheader("📊 Database Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tickers", stats['total_tickers'])
        with col2:
            st.metric("Data Points", stats['total_data_points'] or 0)
        with col3:
            st.metric("Earliest Date", stats['earliest_date'] or 'N/A')
        with col4:
            st.metric("Latest Date", stats['latest_date'] or 'N/A')
        
        # Show detailed ticker info
        st.subheader("📈 Detailed Ticker Information")
        
        detail_query = """
            SELECT 
                c.contract_code as Ticker,
                c.name as Name,
                COUNT(dd.id) as Data_Points,
                MIN(dd.date) as First_Date,
                MAX(dd.date) as Last_Date
            FROM companies c
            LEFT JOIN daily_data dd ON c.id = dd.company_id
            GROUP BY c.id, c.contract_code, c.name
            ORDER BY c.contract_code
        """
        
        detail_df = pd.read_sql_query(detail_query, conn)
        st.dataframe(detail_df, use_container_width=True)
        
        # Usage instructions
        st.subheader("💡 Usage Instructions")
        st.info("""
        **For ML modules:**
        - Use any of these tickers in ML prediction functions
        - Example: `ml_manager.predict_price_movement('SBER')`
        - Example: `ml_manager.analyze_market_sentiment()`
        """)
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error accessing database: {e}")

if __name__ == "__main__":
    main()
