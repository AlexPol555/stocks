# Исправление миграции таблицы companies

## Проблема

Ошибка: `Could not load from companies table: no such column: name`

## Причина

Таблица `companies` была создана в старой версии без колонок `name`, `isin`, `figi`, `created_at`.

## Решение

Добавлена функция миграции `migrate_companies_table()` для автоматического добавления недостающих колонок.

### 1. Функция миграции

```python
def migrate_companies_table(conn):
    """Add missing columns to companies table if needed."""
    try:
        cursor = conn.execute("PRAGMA table_info(companies)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Add missing columns
        if "name" not in existing_columns:
            conn.execute("ALTER TABLE companies ADD COLUMN name TEXT")
        if "isin" not in existing_columns:
            conn.execute("ALTER TABLE companies ADD COLUMN isin TEXT")
        if "figi" not in existing_columns:
            conn.execute("ALTER TABLE companies ADD COLUMN figi TEXT")
        if "created_at" not in existing_columns:
            conn.execute("ALTER TABLE companies ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        conn.commit()
        return True
    except Exception as e:
        st.warning(f"Could not migrate companies table: {e}")
        return False
```

### 2. Обновленная функция загрузки тикеров

```python
def load_existing_tickers(repository):
    """Load existing tickers from companies table."""
    try:
        with repository.connect() as conn:
            # Migrate companies table first
            migrate_companies_table(conn)
            
            # Check if companies table exists and has data
            try:
                companies_count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
                if companies_count > 0:
                    st.info(f"Found {companies_count} existing companies in database")
                    
                    # Check table structure first
                    cursor = conn.execute("PRAGMA table_info(companies)")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    # Build query based on available columns
                    select_fields = ["contract_code"]
                    if "name" in columns:
                        select_fields.append("name")
                    if "isin" in columns:
                        select_fields.append("isin")
                    if "figi" in columns:
                        select_fields.append("figi")
                    
                    query = f"""
                        SELECT {', '.join(select_fields)}
                        FROM companies 
                        WHERE contract_code IS NOT NULL AND contract_code != ''
                        ORDER BY contract_code
                    """
                    
                    companies = conn.execute(query).fetchall()
                    
                    # Insert into tickers table
                    inserted_count = 0
                    for row in companies:
                        # Extract fields based on available columns
                        contract_code = row[0]
                        name = row[1] if len(row) > 1 and "name" in columns else None
                        isin = row[2] if len(row) > 2 and "isin" in columns else None
                        figi = row[3] if len(row) > 3 and "figi" in columns else None
                        
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
                    
            except Exception as e:
                st.warning(f"Could not load from companies table: {e}")
                return False
                
    except Exception as exc:
        st.warning(f"Could not load existing tickers: {exc}")
        return False
```

## Особенности реализации

### 1. Безопасная миграция

- Проверка существования колонок перед добавлением
- Использование `ALTER TABLE ADD COLUMN` только для отсутствующих колонок
- Обработка ошибок без прерывания работы

### 2. Адаптивный запрос

- Динамическое построение SELECT запроса
- Проверка доступных колонок через `PRAGMA table_info`
- Безопасное извлечение данных из результата

### 3. Обратная совместимость

- Работает с таблицами старого формата
- Автоматическое добавление недостающих колонок
- Сохранение существующих данных

## Структура таблицы companies

### До миграции (старая версия)
```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_code TEXT UNIQUE
);
```

### После миграции (новая версия)
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

## Последовательность выполнения

1. **Миграция таблицы**: Добавление недостающих колонок
2. **Проверка структуры**: Определение доступных колонок
3. **Построение запроса**: Динамический SELECT на основе колонок
4. **Загрузка данных**: Безопасное извлечение полей
5. **Создание алиасов**: Формирование списка алиасов
6. **Вставка в tickers**: Сохранение в таблицу пайплайна

## Обработка ошибок

### 1. Ошибки миграции
```python
except Exception as e:
    st.warning(f"Could not migrate companies table: {e}")
    return False
```

### 2. Ошибки загрузки
```python
except Exception as e:
    st.warning(f"Could not load from companies table: {e}")
    return False
```

### 3. Общие ошибки
```python
except Exception as exc:
    st.warning(f"Could not load existing tickers: {exc}")
    return False
```

## Проверка

### 1. Проверить структуру таблицы
```sql
PRAGMA table_info(companies);
```

### 2. Проверить данные
```sql
SELECT contract_code, name, isin, figi FROM companies LIMIT 5;
```

### 3. Проверить загрузку тикеров
```sql
SELECT COUNT(*) FROM tickers;
SELECT ticker, name FROM tickers LIMIT 5;
```

## Дополнительные улучшения

### 1. Логирование миграции
```python
if "name" not in existing_columns:
    conn.execute("ALTER TABLE companies ADD COLUMN name TEXT")
    logger.info("Added 'name' column to companies table")
```

### 2. Проверка версии схемы
```python
def get_schema_version(conn):
    try:
        cursor = conn.execute("SELECT value FROM schema_version WHERE key = 'companies'")
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

Миграция таблицы `companies` обеспечивает:
- **Совместимость** с существующими данными
- **Безопасность** операций миграции
- **Адаптивность** к разным версиям схемы
- **Надежность** обработки ошибок

Пайплайн новостей теперь корректно работает с таблицей `companies` независимо от её версии.
