# Отладка отображения кандидатов

## Проблема

**Симптомы:** Кандидаты отображаются с fallback значениями:
- Ticker: Unknown
- Score: 0.000
- Method: Unknown
- News: No title...

**Причина:** Данные из базы данных не содержат ожидаемых полей или содержат NULL значения.

## Диагностика

### 1. Добавлена отладочная информация

```python
# Debug: Show column names and sample data
st.write("**Debug Info:**")
st.write(f"Columns: {list(df.columns)}")
st.write(f"DataFrame shape: {df.shape}")
if len(df) > 0:
    st.write("Sample row:", df.iloc[0].to_dict())
    st.write("Data types:", df.dtypes.to_dict())
    st.write("Null values:", df.isnull().sum().to_dict())
```

### 2. Добавлена проверка состояния базы данных

```python
# Database status check
with session_state.repository.connect() as conn:
    news_tickers_count = conn.execute("SELECT COUNT(*) FROM news_tickers").fetchone()[0]
    tickers_count = conn.execute("SELECT COUNT(*) FROM tickers").fetchone()[0]
    articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    
    st.write("**Database Status:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("News-Tickers", news_tickers_count)
    with col2:
        st.metric("Tickers", tickers_count)
    with col3:
        st.metric("Articles", articles_count)
```

### 3. Добавлена функция создания тестовых данных

```python
def create_test_candidates(repository):
    """Create test candidates for demonstration."""
    # Создает тестовые статьи, тикеры и кандидаты
    # если база данных пустая
```

## Возможные причины

### 1. Пустая база данных
- Таблица `news_tickers` пустая
- Таблица `tickers` пустая
- Таблица `articles` пустая

### 2. Проблемы с SQL запросом
```sql
SELECT nt.*, t.ticker, t.name, a.title, a.published_at 
FROM news_tickers nt 
LEFT JOIN tickers t ON t.id = nt.ticker_id 
LEFT JOIN articles a ON a.id = nt.news_id 
WHERE COALESCE(confirmed, 0) = 0 
ORDER BY score DESC 
LIMIT ?
```

**Проблемы:**
- LEFT JOIN может возвращать NULL для `t.ticker`
- LEFT JOIN может возвращать NULL для `a.title`
- Поля могут отсутствовать в результате

### 3. Проблемы с маппингом полей
- Поля в SQL запросе не соответствуют ожидаемым
- Имена колонок в DataFrame отличаются от ожидаемых

## Решения

### 1. Создание тестовых данных
```python
# Если база пустая, создать тестовые данные
if news_tickers_count == 0:
    st.warning("No candidates found in database. You may need to run batch processing first.")
    if st.button("🧪 Create Test Data"):
        create_test_candidates(session_state.repository)
```

### 2. Улучшенная обработка NULL значений
```python
# Safe access to fields with fallbacks
ticker = candidate_dict.get('ticker', 'Unknown')
score = candidate_dict.get('score', 0.0)
title = candidate_dict.get('title', 'No title')
method = candidate_dict.get('method', 'Unknown')
candidate_id = candidate_dict.get('id', 0)
```

### 3. Проверка SQL запроса
```python
# Добавить проверку результата SQL запроса
candidates = session_state.repository.fetch_pending_candidates(...)
if candidates:
    # Проверить структуру данных
    st.write("Raw candidates:", candidates[:2])  # Первые 2 записи
```

## Пошаговая диагностика

### Шаг 1: Проверить состояние базы данных
1. Открыть страницу "🔍 News Pipeline"
2. Перейти на вкладку "✅ Candidate Validation"
3. Посмотреть на метрики "Database Status"
4. Если все счетчики = 0, нажать "🧪 Create Test Data"

### Шаг 2: Проверить отладочную информацию
1. Нажать "🔄 Refresh Candidates"
2. Посмотреть на "Debug Info"
3. Проверить:
   - Какие колонки есть в DataFrame
   - Какие данные в sample row
   - Сколько NULL значений

### Шаг 3: Проверить SQL запрос
```python
# Добавить в fetch_pending_candidates отладочный вывод
def fetch_pending_candidates(self, ...):
    # ... существующий код ...
    with self.connect() as conn:
        cur = conn.execute(sql, tuple(params))
        rows = cur.fetchall()
        print(f"SQL query returned {len(rows)} rows")
        if rows:
            print(f"First row: {rows[0]}")
        return rows
```

### Шаг 4: Проверить JOIN'ы
```sql
-- Проверить каждый JOIN отдельно
SELECT COUNT(*) FROM news_tickers;  -- Должно быть > 0
SELECT COUNT(*) FROM tickers;       -- Должно быть > 0
SELECT COUNT(*) FROM articles;      -- Должно быть > 0

-- Проверить JOIN'ы
SELECT nt.id, t.ticker, a.title 
FROM news_tickers nt 
LEFT JOIN tickers t ON t.id = nt.ticker_id 
LEFT JOIN articles a ON a.id = nt.news_id 
LIMIT 5;
```

## Ожидаемые результаты

### После создания тестовых данных:
- **Database Status:** News-Tickers: 3, Tickers: 3, Articles: 3
- **Debug Info:** 
  - Columns: ['id', 'news_id', 'ticker_id', 'score', 'method', 'ticker', 'name', 'title', 'published_at']
  - Sample row: {'id': 1, 'ticker': 'SBER', 'score': 0.85, 'method': 'fuzzy', 'title': 'Test News 1'}

### После исправления:
- Кандидаты отображаются с реальными данными
- Ticker: SBER, GAZP, LKOH
- Score: 0.85, 0.75, 0.65
- Method: fuzzy, substring, ner
- News: Test News 1, Test News 2, Test News 3

## Заключение

Проблема с отображением fallback значений решается:

1. **Диагностикой** - отладочная информация показывает реальную структуру данных
2. **Созданием тестовых данных** - если база пустая
3. **Проверкой SQL запросов** - убедиться, что JOIN'ы работают корректно
4. **Обработкой NULL значений** - безопасное обращение к полям с fallback

После выполнения этих шагов кандидаты должны отображаться с реальными данными из базы.
