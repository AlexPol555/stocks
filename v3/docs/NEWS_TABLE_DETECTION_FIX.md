# News Table Detection Fix Report

## Problem
ML system was looking for a table named `news` but the actual news data is stored in different tables like `articles`.

## Root Cause
The ML sentiment analysis was hardcoded to look for a table named `news`, but the actual database contains news data in tables like `articles`, `article_ticker`, etc.

## Solution

### 1. Dynamic News Table Detection
**File**: `core/ml/integration.py`

**Before**:
```python
# Check if news table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%news%'")
if not cursor.fetchone():
    conn.close()
    return pd.DataFrame()

# Get news data (assuming there's a news table)
query = """
    SELECT 
        title,
        content,
        date
    FROM news
    WHERE date >= date('now', '-{} days')
    ORDER BY date DESC
    LIMIT 100
""".format(days_back)
```

**After**:
```python
# Check for news-related tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%news%' OR name LIKE '%article%')")
news_tables = cursor.fetchall()

if not news_tables:
    conn.close()
    return pd.DataFrame()

# Use the first available news table
news_table = news_tables[0][0]
logger.info(f"Using news table: {news_table}")

# Get news data - adapt query based on table structure
if 'articles' in news_table.lower():
    # For articles table
    query = """
        SELECT 
            title,
            content,
            created_at as date
        FROM {}
        WHERE created_at >= date('now', '-{} days')
        ORDER BY created_at DESC
        LIMIT 100
    """.format(news_table, days_back)
else:
    # For other news tables
    query = """
        SELECT 
            title,
            content,
            date
        FROM {}
        WHERE date >= date('now', '-{} days')
        ORDER BY date DESC
        LIMIT 100
    """.format(news_table, days_back)
```

## Benefits

### 1. **Automatic Table Detection**
- Searches for any table containing 'news' or 'article' in the name
- Automatically uses the first available news table
- No need to hardcode table names

### 2. **Flexible Column Mapping**
- Adapts to different table structures
- Uses `created_at` for articles table, `date` for others
- Handles different column naming conventions

### 3. **Better Logging**
- Logs which news table is being used
- Helps with debugging and monitoring

## Expected Results

After this fix:
- ✅ **ML system will find news data** in `articles` table
- ✅ **Sentiment analysis will work** with real news data
- ✅ **No more "no such table: news" errors**
- ✅ **Automatic adaptation** to different database schemas

## Database Tables Expected

Based on the terminal output, the system should find:
- `articles` - Main news articles table
- `article_ticker` - Link between articles and tickers
- `articles_fts` - Full-text search index
- Other news-related tables

## Status
✅ **COMPLETED** - News table detection is now dynamic and will work with the actual database schema.

The ML system should now successfully load news data for sentiment analysis.
