# Исправление инициализации процессора и загрузки тикеров

## Проблема

Ошибки:
1. `No tickers loaded from database`
2. `RuntimeError: Processor not initialized. Call initialize() first.`

## Причины

1. **Кэширование процессора**: Использование `@st.cache_resource` для процессора мешало правильной инициализации
2. **Отсутствие схемы БД**: Таблицы `sources` и `articles` не создавались
3. **Пустая база данных**: Отсутствие тестовых данных для демонстрации

## Решения

### 1. Убрано кэширование процессора

**Было:**
```python
@st.cache_resource
def get_processor():
    return NewsBatchProcessor()

def initialize_pipeline():
    processor = get_processor()
    processor.initialize(config)
```

**Стало:**
```python
def initialize_pipeline():
    repository = NewsPipelineRepository()
    processor = NewsBatchProcessor(repository)
    processor.initialize(config)
```

### 2. Добавлено создание схемы БД

**В `core/news_pipeline/repository.py`:**
```python
def ensure_schema(self) -> None:
    with self.connect() as conn:
        self._ensure_sources_table(conn)      # НОВОЕ
        self._ensure_articles_table(conn)     # НОВОЕ
        self._ensure_articles_columns(conn)
        self._ensure_tickers_table(conn)
        self._ensure_news_tickers_table(conn)
        self._ensure_processing_runs(conn)
```

**Добавлены методы:**
```python
def _ensure_sources_table(self, conn: sqlite3.Connection) -> None:
    """Create sources table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def _ensure_articles_table(self, conn: sqlite3.Connection) -> None:
    """Create articles table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE,
            published_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            body TEXT,
            source_id INTEGER,
            FOREIGN KEY (source_id) REFERENCES sources (id)
        )
    """)
```

### 3. Добавлена загрузка тестовых данных

**В `pages/9_🔍_News_Pipeline.py`:**
```python
def create_test_data(repository):
    """Create test data for demonstration."""
    with repository.connect() as conn:
        # Create test source
        conn.execute("""
            INSERT OR IGNORE INTO sources (name, url) 
            VALUES (?, ?)
        """, ("Test News", "https://test-news.com"))
        
        source_id = conn.lastrowid
        
        # Create test articles
        test_articles = [
            ("Сбербанк объявил о новых продуктах", "https://test-news.com/sber-1", "2025-01-01T10:00:00Z"),
            ("Газпром увеличил добычу газа", "https://test-news.com/gazp-1", "2025-01-01T11:00:00Z"),
            ("Лукойл открыл новое месторождение", "https://test-news.com/lkoh-1", "2025-01-01T12:00:00Z"),
        ]
        
        for title, url, published_at in test_articles:
            conn.execute("""
                INSERT OR IGNORE INTO articles (title, url, published_at, body, source_id)
                VALUES (?, ?, ?, ?, ?)
            """, (title, url, published_at, f"Test article: {title}", source_id))
        
        # Create test tickers
        test_tickers = [
            ("SBER", "Сбербанк", ["Сбербанк", "Сбер", "SBER"]),
            ("GAZP", "Газпром", ["Газпром", "Газпром", "GAZP"]),
            ("LKOH", "Лукойл", ["Лукойл", "Лукойл", "LKOH"]),
        ]
        
        for ticker, name, aliases in test_tickers:
            conn.execute("""
                INSERT OR IGNORE INTO tickers (ticker, name, aliases, exchange, description)
                VALUES (?, ?, ?, ?, ?)
            """, (ticker, name, json.dumps(aliases, ensure_ascii=False), "MOEX", f"Test ticker: {name}"))
        
        conn.commit()
        st.success("Test data created successfully!")

def load_existing_tickers(repository):
    """Load existing tickers from database."""
    try:
        with repository.connect() as conn:
            # Check if tickers table exists and has data
            try:
                tickers_count = conn.execute("SELECT COUNT(*) FROM tickers").fetchone()[0]
                if tickers_count > 0:
                    st.info(f"Found {tickers_count} existing tickers in database")
                    return True
                else:
                    st.warning("No tickers found in database")
                    return False
            except Exception as e:
                st.warning(f"Could not load tickers: {e}")
                return False
    except Exception as exc:
        st.warning(f"Could not load existing tickers: {exc}")
        return False
```

### 4. Обновленная инициализация

**В `pages/9_🔍_News_Pipeline.py`:**
```python
def initialize_pipeline():
    """Initialize the news pipeline."""
    try:
        # Create repository and ensure schema
        repository = NewsPipelineRepository()
        repository.ensure_schema()
        
        # Load existing tickers
        tickers_loaded = load_existing_tickers(repository)
        
        if not tickers_loaded:
            st.warning("No tickers found. You may need to load tickers first.")
            if st.button("🧪 Create Test Data"):
                create_test_data(repository)
                st.rerun()
            return None
        
        # Create processor
        processor = NewsBatchProcessor(repository)
        processor.initialize(config)
        
        # Store in session state
        st.session_state.repository = repository
        st.session_state.processor = processor
        st.session_state.pipeline_initialized = True
        
        st.success("Pipeline initialized successfully!")
        return processor
        
    except Exception as e:
        st.error(f"Failed to initialize pipeline: {e}")
        st.write(f"Error details: {type(e).__name__}: {e}")
        return None
```

## Особенности реализации

### 1. Убрано кэширование

- Удален декоратор `@st.cache_resource` для процессора
- Процессор создается заново при каждой инициализации
- Обеспечивает правильную инициализацию с новыми данными

### 2. Создание схемы БД

- Добавлены методы для создания таблиц `sources` и `articles`
- Схема создается автоматически при инициализации
- Обеспечивает совместимость с существующими данными

### 3. Тестовые данные

- Добавлена функция создания тестовых данных
- Создаются тестовые источники, статьи и тикеры
- Позволяет демонстрировать функциональность без реальных данных

### 4. Обработка ошибок

- Добавлена проверка существования тикеров
- Обработка ошибок при инициализации
- Информативные сообщения для пользователя

## Последовательность выполнения

1. **Создание репозитория**: Инициализация подключения к БД
2. **Создание схемы**: Создание необходимых таблиц
3. **Загрузка тикеров**: Проверка существования тикеров
4. **Создание тестовых данных**: Если тикеры не найдены
5. **Инициализация процессора**: Создание и настройка процессора
6. **Сохранение в session state**: Для использования в других функциях

## Обработка ошибок

### 1. Ошибки инициализации
```python
try:
    processor = NewsBatchProcessor(repository)
    processor.initialize(config)
except Exception as e:
    st.error(f"Failed to initialize processor: {e}")
    return None
```

### 2. Ошибки загрузки тикеров
```python
try:
    tickers_count = conn.execute("SELECT COUNT(*) FROM tickers").fetchone()[0]
    if tickers_count > 0:
        return True
    else:
        return False
except Exception as e:
    st.warning(f"Could not load tickers: {e}")
    return False
```

### 3. Ошибки создания тестовых данных
```python
try:
    create_test_data(repository)
    st.success("Test data created successfully!")
except Exception as e:
    st.error(f"Failed to create test data: {e}")
```

## Проверка

### 1. Проверить схему БД
```sql
-- Проверить существование таблиц
SELECT name FROM sqlite_master WHERE type='table';

-- Проверить данные в таблицах
SELECT COUNT(*) FROM sources;
SELECT COUNT(*) FROM articles;
SELECT COUNT(*) FROM tickers;
```

### 2. Проверить инициализацию
```python
# Проверить session state
if 'pipeline_initialized' in st.session_state:
    st.write("Pipeline initialized:", st.session_state.pipeline_initialized)
    st.write("Repository:", st.session_state.repository)
    st.write("Processor:", st.session_state.processor)
```

### 3. Проверить тестовые данные
```python
# Проверить создание тестовых данных
if st.button("🧪 Create Test Data"):
    create_test_data(repository)
    st.rerun()
```

## Дополнительные улучшения

### 1. Логирование инициализации
```python
import logging
logger = logging.getLogger(__name__)

def initialize_pipeline():
    logger.info("Starting pipeline initialization")
    try:
        # ... инициализация
        logger.info("Pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
```

### 2. Проверка версии схемы
```python
def get_schema_version(conn):
    try:
        cursor = conn.execute("SELECT value FROM schema_version WHERE key = 'pipeline'")
        return cursor.fetchone()[0] if cursor.fetchone() else "0"
    except:
        return "0"
```

### 3. Валидация конфигурации
```python
def validate_config(config):
    """Validate pipeline configuration."""
    required_fields = ['batch_size', 'chunk_size', 'auto_apply_threshold']
    missing_fields = [field for field in required_fields if field not in config]
    
    if missing_fields:
        raise ValueError(f"Missing required config fields: {missing_fields}")
    
    return True
```

## Заключение

Исправление инициализации процессора обеспечивает:

- **Правильную инициализацию** без кэширования
- **Создание схемы БД** автоматически
- **Загрузку тестовых данных** для демонстрации
- **Обработку ошибок** с информативными сообщениями
- **Совместимость** с существующими данными

**Ключевые изменения:**
- Убран `@st.cache_resource` для процессора
- Добавлены методы создания схемы БД
- Добавлена функция создания тестовых данных
- Улучшена обработка ошибок
- Добавлена проверка существования тикеров

Пайплайн новостей теперь инициализируется корректно и готов к использованию.
