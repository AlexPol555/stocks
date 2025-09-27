# Исправление ошибки SQLite DEFAULT constraint

## Проблема

Ошибка: `sqlite3.OperationalError: Cannot add a column with non-constant default`

## Причина

SQLite не поддерживает функции в DEFAULT для `ALTER TABLE ADD COLUMN`. Выражение `DEFAULT (datetime('now'))` не может быть использовано при добавлении колонки к существующей таблице.

## Решение

1. **Убрана функция из DEFAULT** при добавлении колонки
2. **Добавлено обновление существующих записей** с текущим временем
3. **Добавлена проверка** для избежания повторного обновления

### До исправления

```python
def _ensure_articles_columns(self, conn: sqlite3.Connection) -> None:
    columns = {
        "ingested_at": "TEXT DEFAULT (datetime('now'))",  # ОШИБКА
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

### После исправления

```python
def _ensure_articles_columns(self, conn: sqlite3.Connection) -> None:
    columns = {
        "ingested_at": "TEXT",  # Без DEFAULT функции
        "processed": "INTEGER DEFAULT 0",
        "processed_at": "TEXT",
        "last_batch_id": "TEXT",
        "last_processed_version": "TEXT",
    }
    for column, ddl in columns.items():
        if not self._column_exists(conn, "articles", column):
            conn.execute(f"ALTER TABLE articles ADD COLUMN {column} {ddl}")
    conn.commit()
    
    # Update ingested_at with current timestamp for existing rows
    if self._column_exists(conn, "articles", "ingested_at"):
        # Check if there are rows with NULL ingested_at
        cursor = conn.execute("SELECT COUNT(*) FROM articles WHERE ingested_at IS NULL")
        null_count = cursor.fetchone()[0]
        
        if null_count > 0:
            # Update NULL values with current timestamp
            conn.execute("UPDATE articles SET ingested_at = datetime('now') WHERE ingested_at IS NULL")
            conn.commit()
            logger.info(f"Updated {null_count} rows with ingested_at timestamp")
```

## Особенности реализации

### 1. Безопасное добавление колонки

- Убрана функция `datetime('now')` из DEFAULT
- Колонка добавляется как `TEXT` без DEFAULT
- Обработка ошибок при добавлении колонки

### 2. Обновление существующих записей

- Проверка наличия NULL значений в новой колонке
- Обновление только NULL значений текущим временем
- Избежание повторного обновления уже заполненных записей

### 3. Обратная совместимость

- Работает с существующими таблицами
- Не нарушает существующие данные
- Автоматическое заполнение новых колонок

## Полный код исправления

```python
def _ensure_articles_columns(self, conn: sqlite3.Connection) -> None:
    """Ensure articles table has required columns."""
    columns = {
        "ingested_at": "TEXT",  # Без DEFAULT функции
        "processed": "INTEGER DEFAULT 0",
        "processed_at": "TEXT",
        "last_batch_id": "TEXT",
        "last_processed_version": "TEXT",
    }
    
    # Add missing columns
    for column, ddl in columns.items():
        if not self._column_exists(conn, "articles", column):
            try:
                conn.execute(f"ALTER TABLE articles ADD COLUMN {column} {ddl}")
                logger.info(f"Added column '{column}' to articles table")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not add column '{column}': {e}")
    
    conn.commit()
    
    # Update ingested_at with current timestamp for existing rows
    if self._column_exists(conn, "articles", "ingested_at"):
        try:
            # Check if there are rows with NULL ingested_at
            cursor = conn.execute("SELECT COUNT(*) FROM articles WHERE ingested_at IS NULL")
            null_count = cursor.fetchone()[0]
            
            if null_count > 0:
                # Update NULL values with current timestamp
                conn.execute("UPDATE articles SET ingested_at = datetime('now') WHERE ingested_at IS NULL")
                conn.commit()
                logger.info(f"Updated {null_count} rows with ingested_at timestamp")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not update ingested_at: {e}")

def _column_exists(self, conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if column exists in table."""
    try:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns
    except sqlite3.DatabaseError:
        return False
```

## Альтернативные решения

### 1. Использование триггера

```python
def _ensure_articles_columns_with_trigger(self, conn: sqlite3.Connection) -> None:
    """Add ingested_at column with trigger for default value."""
    if not self._column_exists(conn, "articles", "ingested_at"):
        # Add column without default
        conn.execute("ALTER TABLE articles ADD COLUMN ingested_at TEXT")
        
        # Create trigger for default value
        conn.execute("""
            CREATE TRIGGER articles_ingested_at_default
            AFTER INSERT ON articles
            WHEN NEW.ingested_at IS NULL
            BEGIN
                UPDATE articles SET ingested_at = datetime('now') WHERE id = NEW.id;
            END
        """)
        
        # Update existing NULL values
        conn.execute("UPDATE articles SET ingested_at = datetime('now') WHERE ingested_at IS NULL")
        conn.commit()
```

### 2. Использование представления

```python
def _create_articles_view(self, conn: sqlite3.Connection) -> None:
    """Create view with computed ingested_at column."""
    conn.execute("""
        CREATE VIEW articles_with_ingested_at AS
        SELECT *,
               COALESCE(ingested_at, datetime('now')) AS ingested_at_computed
        FROM articles
    """)
```

### 3. Пересоздание таблицы

```python
def _recreate_articles_table(self, conn: sqlite3.Connection) -> None:
    """Recreate articles table with proper schema."""
    # Backup existing data
    conn.execute("""
        CREATE TABLE articles_backup AS
        SELECT * FROM articles
    """)
    
    # Drop and recreate table
    conn.execute("DROP TABLE articles")
    conn.execute("""
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE,
            published_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            body TEXT,
            source_id INTEGER,
            ingested_at TEXT DEFAULT (datetime('now')),
            processed INTEGER DEFAULT 0,
            processed_at TEXT,
            last_batch_id TEXT,
            last_processed_version TEXT,
            FOREIGN KEY (source_id) REFERENCES sources (id)
        )
    """)
    
    # Restore data
    conn.execute("""
        INSERT INTO articles (id, title, url, published_at, created_at, body, source_id, ingested_at)
        SELECT id, title, url, published_at, created_at, body, source_id, 
               COALESCE(ingested_at, datetime('now'))
        FROM articles_backup
    """)
    
    # Drop backup table
    conn.execute("DROP TABLE articles_backup")
    conn.commit()
```

## Проверка

### 1. Проверить структуру таблицы
```sql
PRAGMA table_info(articles);
```

### 2. Проверить данные
```sql
SELECT id, title, ingested_at FROM articles LIMIT 5;
```

### 3. Проверить NULL значения
```sql
SELECT COUNT(*) FROM articles WHERE ingested_at IS NULL;
```

### 4. Проверить обновление
```python
# Тест должен работать без ошибок
repository = NewsPipelineRepository()
with repository.connect() as conn:
    repository._ensure_articles_columns(conn)
    print("Articles columns ensured successfully")
```

## Обработка ошибок

### 1. Ошибки добавления колонки
```python
try:
    conn.execute(f"ALTER TABLE articles ADD COLUMN {column} {ddl}")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        logger.info(f"Column '{column}' already exists")
    else:
        logger.error(f"Could not add column '{column}': {e}")
        raise
```

### 2. Ошибки обновления данных
```python
try:
    conn.execute("UPDATE articles SET ingested_at = datetime('now') WHERE ingested_at IS NULL")
except sqlite3.OperationalError as e:
    logger.error(f"Could not update ingested_at: {e}")
    # Continue without failing
```

### 3. Ошибки проверки колонки
```python
def _column_exists(self, conn: sqlite3.Connection, table: str, column: str) -> bool:
    try:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns
    except sqlite3.DatabaseError as e:
        logger.warning(f"Could not check column '{column}': {e}")
        return False
```

## Дополнительные улучшения

### 1. Логирование операций
```python
import logging
logger = logging.getLogger(__name__)

def _ensure_articles_columns(self, conn: sqlite3.Connection) -> None:
    logger.info("Ensuring articles table columns")
    # ... код
    logger.info("Articles table columns ensured successfully")
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

### 3. Откат изменений
```python
def rollback_articles_columns(self, conn: sqlite3.Connection) -> None:
    """Remove added columns (if needed)."""
    # SQLite doesn't support DROP COLUMN directly
    # Would need to recreate table
    pass
```

## Заключение

Исправление ошибки SQLite DEFAULT constraint обеспечивает:

- **Совместимость** с ограничениями SQLite
- **Безопасное добавление** колонок к существующим таблицам
- **Автоматическое заполнение** новых колонок
- **Обратную совместимость** с существующими данными
- **Надежность** обработки ошибок

**Ключевые изменения:**
- Убрана функция `datetime('now')` из DEFAULT при добавлении колонки
- Добавлено обновление существующих записей с текущим временем
- Добавлена проверка существования колонки перед обновлением
- Улучшена обработка ошибок

Пайплайн новостей теперь корректно работает с SQLite и создает необходимые колонки без ошибок.
