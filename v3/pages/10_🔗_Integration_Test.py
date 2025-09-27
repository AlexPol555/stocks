"""Integration test page for news pipeline."""

import streamlit as st
from datetime import datetime
import sqlite3
from pathlib import Path

st.set_page_config(
    page_title="Integration Test",
    page_icon="🔗",
    layout="wide"
)

st.title("🔗 News Pipeline Integration Test")

# Database path
db_path = Path("stock_data.db")

if not db_path.exists():
    st.error("❌ Database not found!")
    st.stop()

# Connect to database
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

try:
    # Check tables
    st.header("📊 Database Status")
    
    tables = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """).fetchall()
    
    st.write(f"**Tables found:** {len(tables)}")
    for table in tables:
        st.write(f"• {table[0]}")
    
    # Check pipeline tables
    st.header("🔍 News Pipeline Tables")
    
    pipeline_tables = ['articles', 'sources', 'tickers', 'news_tickers', 'processing_runs']
    col1, col2 = st.columns(2)
    
    with col1:
        for table in pipeline_tables[:3]:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                st.metric(table, count)
            except Exception as e:
                st.error(f"{table}: {e}")
    
    with col2:
        for table in pipeline_tables[3:]:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                st.metric(table, count)
            except Exception as e:
                st.error(f"{table}: {e}")
    
    # Check confirmed tickers
    st.header("✅ Confirmed Tickers")
    
    confirmed_count = conn.execute("""
        SELECT COUNT(*) FROM news_tickers WHERE confirmed = 1
    """).fetchone()[0]
    
    st.metric("Confirmed Tickers", confirmed_count)
    
    if confirmed_count > 0:
        st.success(f"✅ Found {confirmed_count} confirmed ticker associations!")
        
        # Show examples
        examples = conn.execute("""
            SELECT a.title, t.ticker, nt.score, nt.method, nt.confirmed
            FROM news_tickers nt
            JOIN articles a ON a.id = nt.news_id
            JOIN tickers t ON t.id = nt.ticker_id
            WHERE nt.confirmed = 1
            ORDER BY nt.score DESC
            LIMIT 10
        """).fetchall()
        
        st.write("**Top confirmed associations:**")
        for i, row in enumerate(examples, 1):
            st.write(f"{i}. **{row['ticker']}** (score: {row['score']:.2f}) - {row['title'][:60]}...")
    else:
        st.warning("⚠️ No confirmed ticker associations found!")
    
    # Test fetch_recent_articles query
    st.header("📰 Test fetch_recent_articles Query")
    
    try:
        # First, test the exact query from fetch_recent_articles
        sql = """
            SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, 
                   s.name AS source_name, 
                   GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols 
            FROM articles a 
            LEFT JOIN sources s ON s.id = a.source_id 
            LEFT JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1 
            LEFT JOIN tickers t ON t.id = nt.ticker_id 
            GROUP BY a.id 
            ORDER BY COALESCE(a.published_at, a.created_at) DESC 
            LIMIT 5
        """
        
        rows = conn.execute(sql).fetchall()
        st.write(f"**Query returned {len(rows)} articles:**")
        
        for i, row in enumerate(rows, 1):
            tickers = []
            if row["ticker_symbols"]:
                tickers = [t.strip() for t in str(row["ticker_symbols"]).split(",") if t.strip()]
            
            st.write(f"{i}. **{row['title'][:50]}...**")
            st.write(f"   Source: {row['source_name']}")
            st.write(f"   Tickers: {tickers if tickers else 'None'}")
            st.write(f"   Published: {row['published_at']}")
            st.divider()
        
        # Now test with only articles that have confirmed tickers
        st.subheader("📰 Articles WITH Confirmed Tickers")
        
        sql_with_tickers = """
            SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, 
                   s.name AS source_name, 
                   GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols 
            FROM articles a 
            LEFT JOIN sources s ON s.id = a.source_id 
            INNER JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1 
            LEFT JOIN tickers t ON t.id = nt.ticker_id 
            GROUP BY a.id 
            ORDER BY COALESCE(a.published_at, a.created_at) DESC 
            LIMIT 5
        """
        
        rows_with_tickers = conn.execute(sql_with_tickers).fetchall()
        st.write(f"**Articles with confirmed tickers: {len(rows_with_tickers)}**")
        
        for i, row in enumerate(rows_with_tickers, 1):
            tickers = []
            if row["ticker_symbols"]:
                tickers = [t.strip() for t in str(row["ticker_symbols"]).split(",") if t.strip()]
            
            st.write(f"{i}. **{row['title'][:50]}...**")
            st.write(f"   Source: {row['source_name']}")
            st.write(f"   Tickers: {tickers}")
            st.write(f"   Published: {row['published_at']}")
            st.divider()
            
    except Exception as e:
        st.error(f"Query failed: {e}")
    
    # Test summary query
    st.header("📈 Test Summary Query")
    
    try:
        today = datetime.now().date()
        start_date = datetime.combine(today, datetime.min.time())
        end_date = datetime.combine(today, datetime.max.time())
        
        summary_sql = """
            SELECT a.id, a.title, a.body, a.url, a.published_at,
                   GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols
            FROM articles a
            LEFT JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1
            LEFT JOIN tickers t ON t.id = nt.ticker_id
            WHERE a.published_at >= ? AND a.published_at <= ?
            GROUP BY a.id
            ORDER BY a.published_at DESC
        """
        
        summary_rows = conn.execute(summary_sql, (start_date.isoformat(), end_date.isoformat())).fetchall()
        st.write(f"**Summary query for today returned {len(summary_rows)} articles:**")
        
        if summary_rows:
            # Count ticker mentions
            from collections import Counter
            all_tickers = []
            for row in summary_rows:
                if row["ticker_symbols"]:
                    tickers = [t.strip() for t in str(row["ticker_symbols"]).split(",") if t.strip()]
                    all_tickers.extend(tickers)
            
            counter = Counter(all_tickers)
            top_mentions = counter.most_common(5)
            
            st.write("**Top ticker mentions today:**")
            for ticker, count in top_mentions:
                st.write(f"• {ticker}: {count} mentions")
        else:
            st.info("No articles found for today")
            
    except Exception as e:
        st.error(f"Summary query failed: {e}")
    
    # Test fetch_recent_articles function
    st.header("🔧 Test fetch_recent_articles Function")
    
    try:
        from core.news import fetch_recent_articles, _supports_news_pipeline
        
        # Check if news pipeline is supported
        has_news_pipeline = _supports_news_pipeline(conn)
        st.write(f"**News pipeline supported: {has_news_pipeline}**")
        
        articles = fetch_recent_articles(limit=5)
        st.write(f"**fetch_recent_articles returned {len(articles)} articles:**")
        
        articles_with_tickers = [a for a in articles if a.get("tickers")]
        st.write(f"**Articles with tickers: {len(articles_with_tickers)}**")
        
        for i, article in enumerate(articles, 1):
            st.write(f"{i}. **{article['title'][:50]}...**")
            st.write(f"   Source: {article.get('source', 'Unknown')}")
            st.write(f"   Tickers: {article.get('tickers', [])}")
            st.write(f"   Published: {article.get('published_at', 'Unknown')}")
            st.divider()
            
    except Exception as e:
        st.error(f"fetch_recent_articles failed: {e}")
        import traceback
        st.write("**Full error:**")
        st.code(traceback.format_exc())
    
    # Test build_summary function
    st.header("📈 Test build_summary Function")
    
    try:
        from core.news import build_summary
        
        summary = build_summary()
        st.write(f"**build_summary returned:**")
        st.write(f"  Date: {summary.get('date')}")
        st.write(f"  Top mentions: {len(summary.get('top_mentions', []))}")
        st.write(f"  Clusters: {len(summary.get('clusters', []))}")
        
        if summary.get('top_mentions'):
            st.write("**Top ticker mentions:**")
            for mention in summary['top_mentions'][:5]:
                st.write(f"  • {mention['ticker']}: {mention['mentions']} mentions")
        else:
            st.write("**No ticker mentions found**")
            
    except Exception as e:
        st.error(f"build_summary failed: {e}")
        import traceback
        st.write("**Full error:**")
        st.code(traceback.format_exc())
    
    # Integration status
    st.header("🔗 Integration Status")
    
    if confirmed_count > 0:
        st.success("✅ **Integration is READY!**")
        st.write("News should display with tickers on the News page.")
        st.write("Daily summary should show ticker mentions.")
    else:
        st.error("❌ **Integration is NOT READY!**")
        st.write("Steps to fix:")
        st.write("1. Go to '🔍 News Pipeline' page")
        st.write("2. Run batch processing")
        st.write("3. Confirm some candidates")
        st.write("4. Return to this page to verify")

finally:
    conn.close()
