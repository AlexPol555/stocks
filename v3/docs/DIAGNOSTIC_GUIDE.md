# 🔍 Руководство по диагностике интеграции

## Проблема

Интеграция пайплайна новостей работает частично:
- ✅ В базе данных есть 11 подтвержденных связей новостей с тикерами
- ❌ Функция `fetch_recent_articles` не возвращает новости с тикерами
- ❌ На странице "🗞️ News" новости отображаются без тикеров

## Диагностика

### 1. Проверьте страницу "🔗 Integration Test"

Откройте страницу "🔗 Integration Test" в Streamlit и проверьте:

1. **Database Status** - должны быть таблицы `news_tickers`, `tickers`, `articles`
2. **Confirmed Tickers** - должно быть > 0
3. **News pipeline supported** - должно быть `True`
4. **fetch_recent_articles** - должен возвращать новости с тикерами

### 2. Проверьте SQL запросы

**Проблемный запрос (возвращает новости без тикеров):**
```sql
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
```

**Рабочий запрос (возвращает только новости с тикерами):**
```sql
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
```

### 3. Проверьте функцию `_supports_news_pipeline`

```python
def _supports_news_pipeline(conn: sqlite3.Connection) -> bool:
    """Check if news pipeline tables exist."""
    query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name='news_tickers' LIMIT 1"
    try:
        return conn.execute(query).fetchone() is not None
    except sqlite3.DatabaseError:
        return False
```

## Возможные причины

### 1. Функция `_supports_news_pipeline` возвращает `False`

**Причина:** Таблица `news_tickers` не найдена или ошибка в запросе.

**Решение:** Проверьте, что таблица существует:
```sql
SELECT name FROM sqlite_master WHERE type='table' AND name='news_tickers';
```

### 2. LEFT JOIN не работает как ожидается

**Причина:** `LEFT JOIN` возвращает все статьи, даже без тикеров.

**Решение:** Используйте `INNER JOIN` для получения только статей с тикерами.

### 3. Проблемы с GROUP_CONCAT

**Причина:** `GROUP_CONCAT` может возвращать `NULL` для статей без тикеров.

**Решение:** Проверьте обработку `NULL` значений в коде.

## Решения

### Решение 1: Исправить функцию `fetch_recent_articles`

Замените `LEFT JOIN` на `INNER JOIN` для получения только статей с тикерами:

```python
sql = (
    "SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, "
    "s.name AS source_name, "
    "GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols "
    "FROM articles a "
    "LEFT JOIN sources s ON s.id = a.source_id "
    "INNER JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1 "
    "LEFT JOIN tickers t ON t.id = nt.ticker_id "
    "GROUP BY a.id "
    "ORDER BY COALESCE(a.published_at, a.created_at) DESC "
    "LIMIT ?"
)
```

### Решение 2: Добавить фильтрацию по тикерам

Добавьте условие для исключения статей без тикеров:

```python
sql = (
    "SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, "
    "s.name AS source_name, "
    "GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols "
    "FROM articles a "
    "LEFT JOIN sources s ON s.id = a.source_id "
    "LEFT JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1 "
    "LEFT JOIN tickers t ON t.id = nt.ticker_id "
    "GROUP BY a.id "
    "HAVING ticker_symbols IS NOT NULL "
    "ORDER BY COALESCE(a.published_at, a.created_at) DESC "
    "LIMIT ?"
)
```

### Решение 3: Создать отдельную функцию для статей с тикерами

```python
def fetch_recent_articles_with_tickers(limit: int = 25) -> List[Dict[str, Any]]:
    """Fetch recent articles that have confirmed ticker associations."""
    storage = _storage()
    conn = storage.connect()
    conn.row_factory = sqlite3.Row
    try:
        sql = (
            "SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, "
            "s.name AS source_name, "
            "GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols "
            "FROM articles a "
            "LEFT JOIN sources s ON s.id = a.source_id "
            "INNER JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1 "
            "LEFT JOIN tickers t ON t.id = nt.ticker_id "
            "GROUP BY a.id "
            "ORDER BY COALESCE(a.published_at, a.created_at) DESC "
            "LIMIT ?"
        )
        rows = conn.execute(sql, (limit,)).fetchall()
    finally:
        conn.close()
    
    articles: List[Dict[str, Any]] = []
    for row in rows:
        published = row["published_at"] or row["created_at"]
        tickers = []
        if row["ticker_symbols"]:
            tickers = [ticker for ticker in str(row["ticker_symbols"]).split(",") if ticker]
        articles.append({
            "id": row["id"],
            "title": row["title"],
            "url": row["url"],
            "published_at": published,
            "body": row["body"],
            "source": row["source_name"],
            "tickers": tickers,
        })
    return articles
```

## Тестирование

### 1. Проверьте функцию `_supports_news_pipeline`

```python
from core.news import _supports_news_pipeline
from core.database import get_database_path

conn = sqlite3.connect(get_database_path())
print(f"News pipeline supported: {_supports_news_pipeline(conn)}")
conn.close()
```

### 2. Проверьте SQL запрос напрямую

```python
import sqlite3
from core.database import get_database_path

conn = sqlite3.connect(get_database_path())
conn.row_factory = sqlite3.Row

sql = """
    SELECT a.id, a.title, 
           GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols 
    FROM articles a 
    LEFT JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1 
    LEFT JOIN tickers t ON t.id = nt.ticker_id 
    GROUP BY a.id 
    ORDER BY COALESCE(a.published_at, a.created_at) DESC 
    LIMIT 5
"""

rows = conn.execute(sql).fetchall()
for row in rows:
    print(f"{row['title'][:50]}... - {row['ticker_symbols']}")

conn.close()
```

### 3. Проверьте функцию `fetch_recent_articles`

```python
from core.news import fetch_recent_articles

articles = fetch_recent_articles(limit=5)
for article in articles:
    print(f"{article['title'][:50]}... - {article.get('tickers', [])}")
```

## Заключение

Проблема в том, что функция `fetch_recent_articles` использует `LEFT JOIN`, который возвращает все статьи, включая те, у которых нет тикеров. Для решения нужно либо изменить запрос на `INNER JOIN`, либо добавить фильтрацию по наличию тикеров.

Рекомендуется использовать **Решение 1** - заменить `LEFT JOIN` на `INNER JOIN` для получения только статей с подтвержденными тикерами.
