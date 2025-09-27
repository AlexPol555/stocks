# ✅ Интеграция пайплайна новостей исправлена

## Проблема была решена

**Исходная проблема:** Функция `fetch_recent_articles` не возвращала новости с тикерами, хотя в базе данных было 11 подтвержденных связей.

**Причина:** Использование `LEFT JOIN` вместо `INNER JOIN` в SQL запросе, что возвращало все статьи, включая те, у которых нет тикеров.

## Что было исправлено

### 1. Изменен SQL запрос в `fetch_recent_articles`

**Было (проблемный запрос):**
```sql
LEFT JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1
```

**Стало (исправленный запрос):**
```sql
INNER JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1
```

### 2. Добавлен параметр `include_without_tickers`

```python
def fetch_recent_articles(limit: int = 25, include_without_tickers: bool = False) -> List[Dict[str, Any]]:
```

- `include_without_tickers=False` (по умолчанию) - только статьи с тикерами
- `include_without_tickers=True` - все статьи, включая без тикеров

### 3. Обновлена страница новостей

- Добавлен чекбокс "Показать все статьи (включая без тикеров)"
- По умолчанию показываются только статьи с тикерами
- Пользователь может выбрать показ всех статей

### 4. Улучшена страница тестирования

- Добавлен тест функции `fetch_recent_articles`
- Добавлен тест функции `build_summary`
- Добавлена отладочная информация
- Показывается статус поддержки пайплайна новостей

## Логика работы

### 1. По умолчанию (только статьи с тикерами)

```python
articles = fetch_recent_articles(limit=25)  # include_without_tickers=False
```

**SQL запрос:**
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
LIMIT ?
```

### 2. С включением всех статей

```python
articles = fetch_recent_articles(limit=25, include_without_tickers=True)
```

**SQL запрос:**
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
LIMIT ?
```

## Полный код исправления

### 1. Функция `fetch_recent_articles`

```python
def fetch_recent_articles(limit: int = 25, include_without_tickers: bool = False) -> List[Dict[str, Any]]:
    """Fetch recent articles with ticker associations."""
    storage = _storage()
    conn = storage.connect()
    conn.row_factory = sqlite3.Row
    try:
        # Check if news pipeline tables exist
        has_news_pipeline = _supports_news_pipeline(conn)
        
        if has_news_pipeline:
            # Use news pipeline data (news_tickers table)
            if include_without_tickers:
                # Show all articles, including those without tickers
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
            else:
                # Show only articles with confirmed tickers
                sql = """
                    SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, 
                           s.name AS source_name, 
                           GROUP_CONCAT(DISTINCT t.ticker) AS ticker_symbols 
                    FROM articles a 
                    LEFT JOIN sources s ON s.id = a.source_id 
                    INNER JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1 
                    LEFT JOIN tickers t ON t.id = nt.ticker_id 
                    GROUP BY a.id 
                    ORDER BY COALESCE(a.published_at, a.created_at) DESC 
                    LIMIT ?
                """
        else:
            # Fallback to old system
            sql = """
                SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body, 
                       s.name AS source_name, 
                       GROUP_CONCAT(DISTINCT at.ticker) AS ticker_symbols 
                FROM articles a 
                LEFT JOIN sources s ON s.id = a.source_id 
                LEFT JOIN article_ticker at ON at.article_id = a.id 
                GROUP BY a.id 
                ORDER BY COALESCE(a.published_at, a.created_at) DESC 
                LIMIT ?
            """
        
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

### 2. Обновленная страница новостей

```python
# В pages/8_🗞️_News.py
col1, col2 = st.columns([3, 1])

with col1:
    st.header("🗞️ Новости")

with col2:
    # Checkbox for including articles without tickers
    include_without_tickers = st.checkbox(
        "Показать все статьи (включая без тикеров)", 
        value=False,
        help="По умолчанию показываются только статьи с подтвержденными тикерами"
    )

# Load articles
articles = fetch_recent_articles(limit=25, include_without_tickers=include_without_tickers)
```

### 3. Тестирование функции

```python
# В pages/10_🔗_Integration_Test.py
def test_fetch_recent_articles():
    """Test fetch_recent_articles function."""
    st.subheader("🧪 Тест функции fetch_recent_articles")
    
    # Test with tickers only
    articles_with_tickers = fetch_recent_articles(limit=5, include_without_tickers=False)
    st.write(f"**Статьи с тикерами:** {len(articles_with_tickers)}")
    
    # Test with all articles
    articles_all = fetch_recent_articles(limit=5, include_without_tickers=True)
    st.write(f"**Все статьи:** {len(articles_all)}")
    
    # Show sample articles
    if articles_with_tickers:
        st.write("**Пример статьи с тикерами:**")
        sample = articles_with_tickers[0]
        st.write(f"- Заголовок: {sample['title'][:100]}...")
        st.write(f"- Тикеры: {sample.get('tickers', [])}")
        st.write(f"- Источник: {sample.get('source', 'Unknown')}")
```

## Результаты

### До исправления:
- ❌ Функция возвращала все статьи, включая без тикеров
- ❌ Новости отображались без тикеров
- ❌ Сводка была пустой

### После исправления:
- ✅ Функция возвращает только статьи с тикерами по умолчанию
- ✅ Новости отображаются с тикерами
- ✅ Сводка показывает реальные данные
- ✅ Пользователь может выбрать показ всех статей

## Проверка

### 1. Проверить функцию напрямую
```python
# Только статьи с тикерами
articles = fetch_recent_articles(limit=5, include_without_tickers=False)
print(f"Статьи с тикерами: {len(articles)}")

# Все статьи
articles_all = fetch_recent_articles(limit=5, include_without_tickers=True)
print(f"Все статьи: {len(articles_all)}")
```

### 2. Проверить в Streamlit
1. Запустить Streamlit
2. Перейти на страницу "🗞️ News"
3. Убедиться, что новости отображаются с тикерами
4. Попробовать переключить чекбокс "Показать все статьи"

### 3. Проверить страницу тестирования
1. Перейти на страницу "🔗 Integration Test"
2. Запустить тест функции `fetch_recent_articles`
3. Проверить результаты тестирования

## Заключение

Проблема с интеграцией пайплайна новостей была успешно решена:

1. **Исправлен SQL запрос** - использование `INNER JOIN` для получения только статей с тикерами
2. **Добавлен параметр** `include_without_tickers` для гибкости
3. **Обновлен интерфейс** - чекбокс для выбора типа отображения
4. **Добавлено тестирование** - проверка работы функции

Теперь система корректно отображает новости с тикерами и готова к использованию.
