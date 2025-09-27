# Интеграция существующих тикеров из таблицы companies

## Проблема

Пайплайн новостей использовал только тестовые тикеры, игнорируя существующие тикеры из таблицы `companies` в базе данных.

## Решение

Добавлена функция `load_existing_tickers()` для автоматической загрузки тикеров из таблицы `companies` в таблицу `tickers` пайплайна новостей.

### 1. Функция загрузки тикеров

```python
def load_existing_tickers(repository):
    """Load existing tickers from companies table."""
    try:
        with repository.connect() as conn:
            # Check if companies table exists and has data
            try:
                companies_count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
                if companies_count > 0:
                    st.info(f"Found {companies_count} existing companies in database")
                    
                    # Load all companies
                    companies = conn.execute("""
                        SELECT contract_code, name, isin, figi 
                        FROM companies 
                        WHERE contract_code IS NOT NULL AND contract_code != ''
                        ORDER BY contract_code
                    """).fetchall()
                    
                    # Insert into tickers table
                    inserted_count = 0
                    for contract_code, name, isin, figi in companies:
                        # Create aliases from contract_code and name
                        aliases = [contract_code]
                        if name:
                            aliases.append(name)
                            # Add common variations
                            if "ПАО" in name:
                                aliases.append(name.replace("ПАО ", ""))
                            if "ООО" in name:
                                aliases.append(name.replace("ООО ", ""))
                        
                        # Insert into tickers table
                        conn.execute("""
                            INSERT OR IGNORE INTO tickers 
                            (ticker, name, aliases, isin, exchange, description)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            contract_code, 
                            name or contract_code, 
                            json.dumps(aliases, ensure_ascii=False), 
                            isin, 
                            "MOEX", 
                            f"Loaded from companies table: {name or contract_code}"
                        ))
                        inserted_count += 1
                    
                    conn.commit()
                    st.success(f"Loaded {inserted_count} tickers from companies table")
                    return True
                else:
                    st.warning("No companies found in database")
                    return False
                    
            except Exception as e:
                st.warning(f"Could not load from companies table: {e}")
                return False
                
    except Exception as exc:
        st.warning(f"Could not load existing tickers: {exc}")
        return False
```

### 2. Интеграция в пайплайн

**В `pages/9_🔍_News_Pipeline.py`:**
```python
def initialize_pipeline():
    """Initialize the news pipeline."""
    try:
        # Create repository and ensure schema
        repository = NewsPipelineRepository()
        repository.ensure_schema()
        
        # Load existing tickers from companies table
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
        return None
```

## Особенности реализации

### 1. Безопасная загрузка

- Проверка существования таблицы `companies`
- Проверка наличия данных в таблице
- Обработка ошибок без прерывания работы

### 2. Создание алиасов

- Основной тикер: `contract_code`
- Полное название: `name`
- Вариации названия: без "ПАО", "ООО"
- JSON формат для хранения алиасов

### 3. Обратная совместимость

- Использование `INSERT OR IGNORE` для избежания дублирования
- Сохранение существующих тикеров
- Добавление новых тикеров из `companies`

## Структура данных

### Таблица companies
```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_code TEXT UNIQUE,
    name TEXT,
    isin TEXT,
    figi TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица tickers (после загрузки)
```sql
CREATE TABLE tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT UNIQUE,
    name TEXT,
    aliases TEXT,  -- JSON array
    isin TEXT,
    exchange TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Пример загрузки

### Исходные данные в companies
```
contract_code | name                    | isin      | figi
SBER         | ПАО Сбербанк            | RU0009029540 | BBG004730N88
GAZP         | ПАО Газпром             | RU0007661625 | BBG004730ZJ9
LKOH         | ПАО Лукойл              | RU0009024277 | BBG004730JJ5
```

### Результат в tickers
```
ticker | name           | aliases                                    | exchange | description
SBER   | ПАО Сбербанк   | ["SBER", "ПАО Сбербанк", "Сбербанк"]     | MOEX     | Loaded from companies table: ПАО Сбербанк
GAZP   | ПАО Газпром    | ["GAZP", "ПАО Газпром", "Газпром"]       | MOEX     | Loaded from companies table: ПАО Газпром
LKOH   | ПАО Лукойл     | ["LKOH", "ПАО Лукойл", "Лукойл"]         | MOEX     | Loaded from companies table: ПАО Лукойл
```

## Последовательность выполнения

1. **Проверка таблицы companies**: Существование и наличие данных
2. **Загрузка данных**: SELECT из таблицы companies
3. **Создание алиасов**: Формирование списка алиасов для каждого тикера
4. **Вставка в tickers**: Сохранение в таблицу пайплайна
5. **Подтверждение**: Уведомление о количестве загруженных тикеров

## Обработка ошибок

### 1. Ошибки загрузки
```python
try:
    companies = conn.execute(query).fetchall()
except Exception as e:
    st.warning(f"Could not load from companies table: {e}")
    return False
```

### 2. Ошибки вставки
```python
try:
    conn.execute(insert_query, values)
    inserted_count += 1
except Exception as e:
    logger.warning(f"Could not insert ticker {contract_code}: {e}")
```

### 3. Общие ошибки
```python
except Exception as exc:
    st.warning(f"Could not load existing tickers: {exc}")
    return False
```

## Проверка

### 1. Проверить данные в companies
```sql
SELECT COUNT(*) FROM companies;
SELECT contract_code, name FROM companies LIMIT 5;
```

### 2. Проверить загрузку в tickers
```sql
SELECT COUNT(*) FROM tickers;
SELECT ticker, name, aliases FROM tickers LIMIT 5;
```

### 3. Проверить алиасы
```python
import json

# Проверить алиасы
ticker = conn.execute("SELECT aliases FROM tickers WHERE ticker = 'SBER'").fetchone()
aliases = json.loads(ticker[0])
print(f"SBER aliases: {aliases}")
```

## Дополнительные улучшения

### 1. Логирование загрузки
```python
logger.info(f"Loading {len(companies)} companies from database")
logger.info(f"Successfully loaded {inserted_count} tickers")
```

### 2. Проверка дублирования
```python
# Проверить существующие тикеры
existing_tickers = conn.execute("SELECT ticker FROM tickers").fetchall()
existing_set = {row[0] for row in existing_tickers}

if contract_code in existing_set:
    logger.info(f"Ticker {contract_code} already exists, skipping")
    continue
```

### 3. Валидация данных
```python
def validate_company_data(contract_code, name, isin, figi):
    """Validate company data before insertion."""
    if not contract_code or contract_code.strip() == "":
        return False, "Empty contract_code"
    
    if not name or name.strip() == "":
        return False, "Empty name"
    
    return True, "Valid"
```

## Заключение

Интеграция существующих тикеров обеспечивает:

- **Использование реальных данных** вместо тестовых
- **Автоматическую загрузку** тикеров из существующей базы
- **Создание алиасов** для улучшения поиска
- **Обратную совместимость** с существующими данными
- **Безопасную обработку** ошибок

**Ключевые преимущества:**
- Пайплайн использует реальные тикеры из базы данных
- Улучшается качество поиска благодаря алиасам
- Обеспечивается совместимость с существующей системой
- Автоматизируется процесс загрузки тикеров

Пайплайн новостей теперь готов к работе с реальными данными.
