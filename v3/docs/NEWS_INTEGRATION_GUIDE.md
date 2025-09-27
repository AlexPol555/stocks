# Руководство по интеграции пайплайна новостей

## Проблема

На странице "🗞️ News" не отображаются новости с тикерами, и в сводке за день показывается "За выбранный день нет привязанных тикеров."

## Решение

Интегрированы данные из пайплайна новостей (`news_tickers` таблица) с существующей системой отображения новостей.

## Изменения

### 1. Обновлена функция `fetch_recent_articles` в `core/news.py`

**Проблема:** Функция использовала старую таблицу `article_ticker` вместо новой `news_tickers`.

**Решение:** Добавлена проверка наличия таблиц пайплайна новостей и приоритетное использование данных из `news_tickers`.

```python
def fetch_recent_articles(limit: int = 25) -> List[Dict[str, Any]]:
    # Check if news pipeline tables exist
    has_news_pipeline = _supports_news_pipeline(conn)
    if has_news_pipeline:
        # Use news pipeline data (news_tickers table)
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
            LIMIT ?
        """
    # ... fallback to old system
```

### 2. Обновлена функция `build_summary` в `core/news.py`

**Проблема:** Сводка за день не использовала данные из пайплайна новостей.

**Решение:** Добавлена функция `_build_summary_from_pipeline`, которая использует подтвержденные связи из `news_tickers`.

```python
def build_summary(target_date: Optional[datetime] = None) -> Dict[str, Any]:
    # Try to use news pipeline data first
    if _supports_news_pipeline(storage.connect()):
        return _build_summary_from_pipeline(storage, date)
    else:
        # Fallback to old system
        return _build_summary_legacy(storage, date)
```

### 3. Добавлена функция `_supports_news_pipeline`

```python
def _supports_news_pipeline(conn: sqlite3.Connection) -> bool:
    """Check if news pipeline tables exist."""
    query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name='news_tickers' LIMIT 1"
    try:
        return conn.execute(query).fetchone() is not None
    except sqlite3.DatabaseError:
        return False
```

### 4. Добавлена функция `_build_summary_from_pipeline`

```python
def _build_summary_from_pipeline(storage, date: datetime) -> Dict[str, Any]:
    """Build summary using news pipeline data."""
    conn = storage.connect()
    conn.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT DATE(COALESCE(a.published_at, a.created_at)) as date,
                   COUNT(DISTINCT a.id) as articles_count,
                   COUNT(DISTINCT t.ticker) as tickers_count,
                   GROUP_CONCAT(DISTINCT t.ticker) as ticker_symbols
            FROM articles a
            LEFT JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1
            LEFT JOIN tickers t ON t.id = nt.ticker_id
            WHERE DATE(COALESCE(a.published_at, a.created_at)) = ?
            GROUP BY DATE(COALESCE(a.published_at, a.created_at))
        """
        
        row = conn.execute(sql, (date.strftime('%Y-%m-%d'),)).fetchone()
        
        if row:
            tickers = []
            if row["ticker_symbols"]:
                tickers = [ticker.strip() for ticker in str(row["ticker_symbols"]).split(",") if ticker.strip()]
            
            return {
                "date": date.strftime('%Y-%m-%d'),
                "articles_count": row["articles_count"],
                "tickers_count": row["tickers_count"],
                "tickers": tickers,
                "source": "news_pipeline"
            }
        else:
            return {
                "date": date.strftime('%Y-%m-%d'),
                "articles_count": 0,
                "tickers_count": 0,
                "tickers": [],
                "source": "news_pipeline"
            }
    finally:
        conn.close()
```

### 5. Обновлена страница новостей (`pages/8_🗞️_News.py`)

**Добавлена секция интеграции:**
```python
# News Pipeline Integration Section
st.subheader("🔗 Интеграция с пайплайном новостей")

# Check if news pipeline is supported
if _supports_news_pipeline(storage.connect()):
    st.success("✅ Пайплайн новостей поддерживается")
    
    # Show pipeline status
    with storage.connect() as conn:
        conn.row_factory = sqlite3.Row
        try:
            # Count confirmed tickers
            confirmed_count = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = 1").fetchone()[0]
            st.write(f"**Подтвержденных связей:** {confirmed_count}")
            
            # Show sample confirmed tickers
            if confirmed_count > 0:
                sample_tickers = conn.execute("""
                    SELECT t.ticker, a.title, nt.score
                    FROM news_tickers nt
                    JOIN tickers t ON t.id = nt.ticker_id
                    JOIN articles a ON a.id = nt.news_id
                    WHERE nt.confirmed = 1
                    ORDER BY nt.score DESC
                    LIMIT 3
                """).fetchall()
                
                st.write("**Примеры подтвержденных связей:**")
                for ticker, title, score in sample_tickers:
                    st.write(f"- {ticker}: {title[:50]}... (Score: {score:.2f})")
        except Exception as e:
            st.warning(f"Ошибка при загрузке статуса пайплайна: {e}")
    
    # Integration controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Обновить тикеры"):
            st.rerun()
    with col2:
        if st.button("🔗 Открыть пайплайн"):
            st.switch_page("pages/9_🔍_News_Pipeline.py")
else:
    st.warning("❌ Пайплайн новостей не поддерживается")
    st.write("Убедитесь, что таблицы `news_tickers` и `tickers` существуют в базе данных.")
```

## Структура данных

### Таблица news_tickers
```sql
CREATE TABLE news_tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id INTEGER NOT NULL,
    ticker_id INTEGER NOT NULL,
    score REAL NOT NULL,
    method TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed INTEGER DEFAULT 0,  -- 1=confirmed, -1=rejected, 0=pending
    confirmed_by TEXT,
    confirmed_at TIMESTAMP,
    batch_id TEXT,
    auto_suggest BOOLEAN DEFAULT 0,
    history TEXT,  -- JSON array of changes
    metadata TEXT,  -- JSON object with additional data
    FOREIGN KEY (news_id) REFERENCES articles (id),
    FOREIGN KEY (ticker_id) REFERENCES tickers (id)
);
```

### Таблица tickers
```sql
CREATE TABLE tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT UNIQUE NOT NULL,
    name TEXT,
    aliases TEXT,  -- JSON array
    isin TEXT,
    exchange TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Логика работы

### 1. Проверка поддержки пайплайна

```python
def _supports_news_pipeline(conn: sqlite3.Connection) -> bool:
    """Check if news pipeline tables exist."""
    query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name='news_tickers' LIMIT 1"
    try:
        return conn.execute(query).fetchone() is not None
    except sqlite3.DatabaseError:
        return False
```

### 2. Приоритет данных

1. **Пайплайн новостей** - если таблицы `news_tickers` и `tickers` существуют
2. **Старая система** - если пайплайн не поддерживается

### 3. Фильтрация по статусу

- Используются только подтвержденные связи (`confirmed = 1`)
- Отклоненные связи (`confirmed = -1`) игнорируются
- Неподтвержденные связи (`confirmed = 0`) игнорируются

## Тестирование

### 1. Проверка поддержки пайплайна

```python
# В pages/10_🔗_Integration_Test.py
def test_news_pipeline_support():
    """Test news pipeline support."""
    conn = storage.connect()
    has_support = _supports_news_pipeline(conn)
    conn.close()
    
    st.write(f"**Поддержка пайплайна новостей:** {'✅ Да' if has_support else '❌ Нет'}")
    return has_support
```

### 2. Проверка функции fetch_recent_articles

```python
def test_fetch_recent_articles():
    """Test fetch_recent_articles function."""
    articles = fetch_recent_articles(limit=5)
    
    st.write(f"**Загружено статей:** {len(articles)}")
    
    if articles:
        sample = articles[0]
        st.write("**Пример статьи:**")
        st.write(f"- Заголовок: {sample['title'][:100]}...")
        st.write(f"- Тикеры: {sample.get('tickers', [])}")
        st.write(f"- Источник: {sample.get('source', 'Unknown')}")
    
    return articles
```

### 3. Проверка функции build_summary

```python
def test_build_summary():
    """Test build_summary function."""
    today = datetime.now()
    summary = build_summary(today)
    
    st.write("**Сводка за сегодня:**")
    st.write(f"- Дата: {summary['date']}")
    st.write(f"- Статей: {summary['articles_count']}")
    st.write(f"- Тикеров: {summary['tickers_count']}")
    st.write(f"- Тикеры: {summary['tickers']}")
    st.write(f"- Источник: {summary['source']}")
    
    return summary
```

## Troubleshooting

### 1. Если новости не отображаются с тикерами

**Проверьте:**
- Существуют ли таблицы `news_tickers` и `tickers`
- Есть ли подтвержденные связи (`confirmed = 1`)
- Правильно ли работает SQL запрос

**Решение:**
```python
# Проверить таблицы
conn = storage.connect()
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables: {tables}")

# Проверить подтвержденные связи
cursor = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = 1")
confirmed_count = cursor.fetchone()[0]
print(f"Confirmed tickers: {confirmed_count}")
```

### 2. Если сводка пустая

**Проверьте:**
- Есть ли статьи за выбранную дату
- Правильно ли работает фильтрация по дате
- Есть ли подтвержденные связи для этих статей

**Решение:**
```python
# Проверить статьи за дату
date_str = "2025-01-01"
cursor = conn.execute("""
    SELECT COUNT(*) FROM articles 
    WHERE DATE(COALESCE(published_at, created_at)) = ?
""", (date_str,))
articles_count = cursor.fetchone()[0]
print(f"Articles for {date_str}: {articles_count}")
```

### 3. Если пайплайн не поддерживается

**Проверьте:**
- Существует ли таблица `news_tickers`
- Правильно ли работает функция `_supports_news_pipeline`

**Решение:**
```python
# Создать таблицы пайплайна
from core.news_pipeline.repository import NewsPipelineRepository
repository = NewsPipelineRepository()
repository.ensure_schema()
```

## Заключение

Интеграция пайплайна новостей обеспечивает:

1. **Использование данных пайплайна** для отображения новостей с тикерами
2. **Обратную совместимость** со старой системой
3. **Гибкость** в выборе источника данных
4. **Надежность** с fallback на старую систему

**Ключевые преимущества:**
- Новости отображаются с тикерами
- Сводка показывает реальные данные
- Система работает с подтвержденными связями
- Обеспечивается совместимость с существующим кодом

Интеграция готова к использованию и обеспечивает полную функциональность системы анализа новостей.
