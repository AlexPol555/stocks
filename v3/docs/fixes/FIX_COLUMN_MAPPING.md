# Исправление маппинга колонок в DataFrame

## Проблема

**Симптомы:** DataFrame использовал числовые индексы колонок (0, 1, 2, ...) вместо имен колонок, что приводило к отображению fallback значений.

**Причина:** `fetch_pending_candidates` возвращает `sqlite3.Row` объекты, которые при преобразовании в pandas DataFrame не сохраняют имена колонок.

**Отладочная информация показала:**
```
Columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
DataFrame shape: (100, 18)
Sample row: {
  "0": 21,           # id
  "1": 556,          # news_id  
  "2": 1,            # ticker_id
  "3": 1.2,          # score
  "4": "fuzzy|ner|substring",  # method
  "14": "SBER",      # ticker
  "15": "Сбербанк",  # name
  "16": "Банки отметили взрывной рост операций по платежным стикерам",  # title
  "17": "2025-09-23T05:49:30Z"  # published_at
}
```

## Решение

### 1. Установка правильных имен колонок

```python
# Convert to DataFrame with proper column names
df = pd.DataFrame(candidates)

# Set proper column names based on SQL query structure
column_names = [
    'id', 'news_id', 'ticker_id', 'score', 'method', 'created_at', 'updated_at',
    'confirmed', 'confirmed_by', 'confirmed_at', 'batch_id', 'auto_suggest',
    'history', 'metadata', 'ticker', 'name', 'title', 'published_at'
]
df.columns = column_names
```

### 2. Маппинг полей по SQL запросу

SQL запрос в `fetch_pending_candidates`:
```sql
SELECT nt.*, t.ticker, t.name, a.title, a.published_at 
FROM news_tickers nt 
LEFT JOIN tickers t ON t.id = nt.ticker_id 
LEFT JOIN articles a ON a.id = nt.news_id 
```

**Структура колонок:**
- `nt.*` (news_tickers): id, news_id, ticker_id, score, method, created_at, updated_at, confirmed, confirmed_by, confirmed_at, batch_id, auto_suggest, history, metadata
- `t.ticker, t.name` (tickers): ticker, name  
- `a.title, a.published_at` (articles): title, published_at

**Итоговый порядок колонок:**
```
[0:id, 1:news_id, 2:ticker_id, 3:score, 4:method, 5:created_at, 6:updated_at, 
 7:confirmed, 8:confirmed_by, 9:confirmed_at, 10:batch_id, 11:auto_suggest,
 12:history, 13:metadata, 14:ticker, 15:name, 16:title, 17:published_at]
```

### 3. Исправление доступа к полям

**До исправления:**
```python
# Неправильно - использовались числовые индексы
ticker = candidate_dict.get('14', 'Unknown')
score = candidate_dict.get('3', 0.0)
title = candidate_dict.get('16', 'No title')
```

**После исправления:**
```python
# Правильно - используются имена колонок
ticker = candidate_dict.get('ticker', 'Unknown')
score = candidate_dict.get('score', 0.0)
title = candidate_dict.get('title', 'No title')
```

### 4. Исправление фильтрации

**До исправления:**
```python
high_score_candidates = df[df[3] >= high_score_threshold]  # Числовой индекс
```

**После исправления:**
```python
high_score_candidates = df[df['score'] >= high_score_threshold]  # Имя колонки
```

## Полный код исправления

### 1. Создание DataFrame с именами колонок
```python
if candidates:
    # Convert to DataFrame with proper column names
    df = pd.DataFrame(candidates)
    
    # Set proper column names based on SQL query structure
    column_names = [
        'id', 'news_id', 'ticker_id', 'score', 'method', 'created_at', 'updated_at',
        'confirmed', 'confirmed_by', 'confirmed_at', 'batch_id', 'auto_suggest',
        'history', 'metadata', 'ticker', 'name', 'title', 'published_at'
    ]
    df.columns = column_names
```

### 2. Отображение кандидатов
```python
for idx, candidate in df.iterrows():
    candidate_dict = candidate.to_dict()
    
    # Safe access to fields with fallbacks
    ticker = candidate_dict.get('ticker', 'Unknown')
    score = candidate_dict.get('score', 0.0)
    title = candidate_dict.get('title', 'No title')
    method = candidate_dict.get('method', 'Unknown')
    candidate_id = candidate_dict.get('id', 0)
    
    with st.expander(f"Candidate {idx + 1}: {ticker} (Score: {score:.3f})"):
        # ... отображение данных
```

### 3. Bulk операции
```python
# Confirm high score candidates
high_score_candidates = df[df['score'] >= high_score_threshold]
for idx, candidate in high_score_candidates.iterrows():
    candidate_dict = candidate.to_dict()
    candidate_id = candidate_dict.get('id', 0)
    # ... обновление статуса

# Reject low score candidates  
low_score_candidates = df[df['score'] < low_score_threshold]
for idx, candidate in low_score_candidates.iterrows():
    candidate_dict = candidate.to_dict()
    candidate_id = candidate_dict.get('id', 0)
    # ... обновление статуса
```

## Результат

### До исправления:
- **Ticker:** Unknown
- **Score:** 0.000
- **Method:** Unknown
- **News:** No title...

### После исправления:
- **Ticker:** SBER
- **Score:** 1.200
- **Method:** fuzzy|ner|substring
- **News:** Банки отметили взрывной рост операций по платежным стикерам

## Альтернативные решения

### 1. Использование sqlite3.Row.keys()
```python
# Получить имена колонок из первого row
if candidates:
    first_row = candidates[0]
    column_names = list(first_row.keys())
    df = pd.DataFrame(candidates, columns=column_names)
```

### 2. Использование pandas.read_sql_query()
```python
# Прямое создание DataFrame из SQL
df = pd.read_sql_query(sql, conn, params=params)
# Автоматически получает имена колонок
```

### 3. Использование описания курсора
```python
# Получить имена колонок из описания курсора
cursor = conn.execute(sql, params)
column_names = [description[0] for description in cursor.description]
df = pd.DataFrame(cursor.fetchall(), columns=column_names)
```

## Рекомендации

### 1. Всегда устанавливайте имена колонок
```python
# Хорошо
df.columns = ['col1', 'col2', 'col3']

# Плохо
df = pd.DataFrame(data)  # Без имен колонок
```

### 2. Документируйте структуру данных
```python
# Добавляйте комментарии о структуре
# Columns: [id, news_id, ticker_id, score, method, ...]
```

### 3. Используйте осмысленные имена
```python
# Хорошо
ticker = candidate_dict.get('ticker', 'Unknown')

# Плохо
ticker = candidate_dict.get('14', 'Unknown')
```

## Тестирование

### 1. Проверка исправления
```python
# Тест должен показать реальные данные
df = pd.DataFrame(candidates)
df.columns = column_names
print(df[['ticker', 'score', 'title']].head())
```

### 2. Проверка в Streamlit
1. Запустить Streamlit
2. Перейти на страницу "🔍 News Pipeline"
3. Открыть вкладку "✅ Candidate Validation"
4. Нажать "🔄 Refresh Candidates"
5. Убедиться, что кандидаты отображаются с реальными данными

## Заключение

Проблема с маппингом колонок была решена путем:

1. **Установки правильных имен колонок** для DataFrame
2. **Использования имен колонок** вместо числовых индексов
3. **Исправления всех мест** доступа к полям данных
4. **Обеспечения консистентности** во всех операциях

Теперь кандидаты отображаются с реальными данными из базы, а не с fallback значениями.
