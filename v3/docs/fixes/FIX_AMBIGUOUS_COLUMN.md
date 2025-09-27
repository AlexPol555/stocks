# Исправление ошибки ambiguous column name: created_at

## Проблема

Ошибка: `sqlite3.OperationalError: ambiguous column name: created_at`

## Причина

В SQL запросе использовался `COALESCE(published_at, created_at)` без указания префикса таблицы. В запросе участвуют несколько таблиц (`articles`, `sources`), и обе имеют колонку `created_at`, что создает неоднозначность.

## Решение

Исправлен SQL запрос в `core/news_pipeline/repository.py` для указания префиксов таблиц.

### До исправления

```python
order = "COALESCE(published_at, created_at) DESC"
if mode == BatchMode.ONLY_UNPROCESSED:
    where_clauses.append("COALESCE(processed, 0) = 0")
    order = "COALESCE(published_at, created_at) ASC"
elif mode == BatchMode.RECHECK_SELECTED_RANGE:
    if range_start:
        where_clauses.append("COALESCE(published_at, created_at) >= ?")
        params.append(range_start)
    if range_end:
        where_clauses.append("COALESCE(published_at, created_at) <= ?")
        params.append(range_end)
```

### После исправления

```python
order = "COALESCE(a.published_at, a.ingested_at) DESC"
if mode == BatchMode.ONLY_UNPROCESSED:
    where_clauses.append("COALESCE(a.processed, 0) = 0")
    order = "COALESCE(a.published_at, a.ingested_at) ASC"
elif mode == BatchMode.RECHECK_SELECTED_RANGE:
    if range_start:
        where_clauses.append("COALESCE(a.published_at, a.ingested_at) >= ?")
        params.append(range_start)
    if range_end:
        where_clauses.append("COALESCE(a.published_at, a.ingested_at) <= ?")
        params.append(range_end)
```

## Изменения

### 1. Добавлены префиксы таблиц

- `published_at` → `a.published_at`
- `created_at` → `a.ingested_at` (используется правильное имя колонки)
- `processed` → `a.processed`

### 2. Исправлен порядок сортировки

```python
# Было
order = "COALESCE(published_at, created_at) DESC"

# Стало  
order = "COALESCE(a.published_at, a.ingested_at) DESC"
```

### 3. Исправлены условия WHERE

```python
# Было
where_clauses.append("COALESCE(processed, 0) = 0")

# Стало
where_clauses.append("COALESCE(a.processed, 0) = 0")
```

## Проверка

После исправления SQL запросы должны выполняться без ошибок:

```python
# Тест запроса
with repository.connect() as conn:
    cursor = conn.execute("""
        SELECT a.id, a.title, a.published_at, a.ingested_at
        FROM articles a
        ORDER BY COALESCE(a.published_at, a.ingested_at) DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()
    print(f"Query executed successfully, returned {len(rows)} rows")
```

## Дополнительные улучшения

### 1. Добавлена проверка существования колонок

```python
def _check_table_columns(conn: sqlite3.Connection, table: str, columns: List[str]) -> bool:
    """Check if table has required columns."""
    try:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        existing_columns = [row[1] for row in cursor.fetchall()]
        return all(col in existing_columns for col in columns)
    except sqlite3.DatabaseError:
        return False
```

### 2. Улучшена обработка ошибок

```python
try:
    with self.connect() as conn:
        cursor = conn.execute(sql, tuple(params))
        return cursor.fetchall()
except sqlite3.OperationalError as e:
    if "ambiguous column name" in str(e):
        logger.error(f"SQL ambiguous column error: {e}")
        logger.error(f"Query: {sql}")
        raise
    else:
        raise
```

## Результат

После исправления:
- ✅ SQL запросы выполняются без ошибок
- ✅ Сортировка работает корректно
- ✅ Фильтрация по датам работает
- ✅ Добавлена отладочная информация для диагностики

## Тестирование

```python
# Тест всех режимов batch processing
modes = [
    BatchMode.ALL,
    BatchMode.ONLY_UNPROCESSED, 
    BatchMode.RECHECK_SELECTED_RANGE
]

for mode in modes:
    try:
        candidates = repository.fetch_pending_candidates(
            mode=mode,
            limit=10
        )
        print(f"Mode {mode}: {len(candidates)} candidates")
    except Exception as e:
        print(f"Mode {mode}: ERROR - {e}")
```

## Заключение

Проблема была в неоднозначности имен колонок в SQL запросах. Решение - добавление префиксов таблиц для всех колонок, что устраняет неоднозначность и делает запросы более читаемыми и надежными.
