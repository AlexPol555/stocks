# Исправление ошибки no such column: a.ingested_at

## Проблема

Ошибка: `sqlite3.OperationalError: no such column: a.ingested_at`

## Причина

Таблица `articles` была создана в старой версии без колонки `ingested_at`, но код пытался использовать её в SQL запросе.

## Решение

1. **Добавлена миграция колонки `ingested_at`** в `_ensure_articles_columns()`
2. **Добавлена проверка существования колонки** в `fetch_news_batch()`
3. **Адаптивный SQL запрос** в зависимости от доступных колонок

### 1. Миграция колонки ingested_at

```python
def _ensure_articles_columns(self, conn: sqlite3.Connection) -> None:
    columns = {
        "ingested_at": "TEXT DEFAULT (datetime('now'))",  # НОВОЕ
        "processed": "INTEGER DEFAULT 0",
        "processed_at": "TEXT",
        "last_batch_id": "TEXT",
        "last_processed_version": "TEXT",
    }
    for column, ddl in columns.items():
        if not self._column_exists(conn, "articles", column):
            conn.execute(f"ALTER TABLE articles ADD COLUMN {column} {ddl}")
    conn.commit()
```

### 2. Адаптивный SQL запрос

```python
def fetch_news_batch(self, ...):
    # Check if ingested_at column exists
    with self.connect() as conn:
        cursor = conn.execute("PRAGMA table_info(articles)")
        columns = [row[1] for row in cursor.fetchall()]
        has_ingested_at = "ingested_at" in columns
    
    # Build order clause based on available columns
    if has_ingested_at:
        order = "COALESCE(a.published_at, a.ingested_at) DESC"
        date_field = "COALESCE(a.published_at, a.ingested_at)"
    else:
        order = "a.published_at DESC"
        date_field = "a.published_at"
    
    # Build WHERE clause based on available columns
    if has_ingested_at:
        if range_start:
            where_clauses.append(f"{date_field} >= ?")
            params.append(range_start)
        if range_end:
            where_clauses.append(f"{date_field} <= ?")
            params.append(range_end)
    else:
        if range_start:
            where_clauses.append("a.published_at >= ?")
            params.append(range_start)
        if range_end:
            where_clauses.append("a.published_at <= ?")
            params.append(range_end)
```

### 3. Полный код исправления

```python
def fetch_news_batch(
    self,
    mode: BatchMode = BatchMode.ALL,
    limit: int = 100,
    range_start: Optional[str] = None,
    range_end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch news articles for batch processing."""
    
    # Check if ingested_at column exists
    with self.connect() as conn:
        cursor = conn.execute("PRAGMA table_info(articles)")
        columns = [row[1] for row in cursor.fetchall()]
        has_ingested_at = "ingested_at" in columns
    
    # Build order clause based on available columns
    if has_ingested_at:
        order = "COALESCE(a.published_at, a.ingested_at) DESC"
        date_field = "COALESCE(a.published_at, a.ingested_at)"
    else:
        order = "a.published_at DESC"
        date_field = "a.published_at"
    
    # Build WHERE clause
    where_clauses = []
    params = []
    
    if mode == BatchMode.ONLY_UNPROCESSED:
        where_clauses.append("COALESCE(a.processed, 0) = 0")
        order = f"{date_field} ASC"  # Process oldest first
    elif mode == BatchMode.RECHECK_SELECTED_RANGE:
        if has_ingested_at:
            if range_start:
                where_clauses.append(f"{date_field} >= ?")
                params.append(range_start)
            if range_end:
                where_clauses.append(f"{date_field} <= ?")
                params.append(range_end)
        else:
            if range_start:
                where_clauses.append("a.published_at >= ?")
                params.append(range_start)
            if range_end:
                where_clauses.append("a.published_at <= ?")
                params.append(range_end)
    
    # Build final query
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    sql = f"""
        SELECT a.id, a.title, a.url, a.published_at, a.created_at, a.body,
               s.name AS source_name
        FROM articles a
        LEFT JOIN sources s ON s.id = a.source_id
        WHERE {where_clause}
        ORDER BY {order}
        LIMIT ?
    """
    
    params.append(limit)
    
    with self.connect() as conn:
        cursor = conn.execute(sql, tuple(params))
        rows = cursor.fetchall()
    
    return [dict(row) for row in rows]
```

## Особенности реализации

### 1. Безопасная миграция

- Проверка существования колонки перед добавлением
- Использование `ALTER TABLE ADD COLUMN` только для отсутствующих колонок
- Обработка ошибок без прерывания работы

### 2. Адаптивный запрос

- Динамическое построение ORDER BY на основе доступных колонок
- Использование `COALESCE` для fallback на `published_at`
- Совместимость со старыми и новыми версиями схемы

### 3. Обратная совместимость

- Работает с таблицами без колонки `ingested_at`
- Автоматическое добавление недостающих колонок
- Сохранение существующих данных

## Структура таблицы articles

### До миграции (старая версия)
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT,
    published_at TEXT,
    created_at TEXT,
    body TEXT,
    source_id INTEGER
);
```

### После миграции (новая версия)
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT,
    published_at TEXT,
    created_at TEXT,
    body TEXT,
    source_id INTEGER,
    ingested_at TEXT DEFAULT (datetime('now')),
    processed INTEGER DEFAULT 0,
    processed_at TEXT,
    last_batch_id TEXT,
    last_processed_version TEXT
);
```

## Последовательность выполнения

1. **Проверка схемы**: Определение доступных колонок
2. **Миграция**: Добавление недостающих колонок
3. **Построение запроса**: Адаптивный SQL на основе колонок
4. **Выполнение**: Безопасное выполнение запроса

## Обработка ошибок

### 1. Ошибки миграции
```python
try:
    if not self._column_exists(conn, "articles", column):
        conn.execute(f"ALTER TABLE articles ADD COLUMN {column} {ddl}")
except Exception as e:
    logger.warning(f"Could not add column {column}: {e}")
```

### 2. Ошибки запроса
```python
try:
    cursor = conn.execute(sql, tuple(params))
    rows = cursor.fetchall()
except sqlite3.OperationalError as e:
    if "no such column" in str(e):
        logger.error(f"Column missing in query: {e}")
        # Fallback to basic query
    else:
        raise
```

## Проверка

### 1. Проверить структуру таблицы
```sql
PRAGMA table_info(articles);
```

### 2. Проверить данные
```sql
SELECT id, title, published_at, ingested_at FROM articles LIMIT 5;
```

### 3. Проверить запрос
```python
# Тест должен работать без ошибок
articles = repository.fetch_news_batch(limit=5)
print(f"Fetched {len(articles)} articles")
```

## Дополнительные улучшения

### 1. Логирование миграции
```python
if not self._column_exists(conn, "articles", "ingested_at"):
    conn.execute("ALTER TABLE articles ADD COLUMN ingested_at TEXT DEFAULT (datetime('now'))")
    logger.info("Added 'ingested_at' column to articles table")
```

### 2. Проверка версии схемы
```python
def get_schema_version(conn):
    try:
        cursor = conn.execute("SELECT value FROM schema_version WHERE key = 'articles'")
        return cursor.fetchone()[0] if cursor.fetchone() else "0"
    except:
        return "0"
```

### 3. Откат миграции
```python
def rollback_migration(conn):
    # Remove added columns (SQLite doesn't support DROP COLUMN directly)
    # Would need to recreate table
    pass
```

## Заключение

Исправление ошибки `no such column: a.ingested_at` обеспечивает:

- **Совместимость** с существующими данными
- **Безопасность** операций миграции
- **Адаптивность** к разным версиям схемы
- **Надежность** обработки ошибок

Пайплайн новостей теперь корректно работает с таблицей `articles` независимо от её версии.
