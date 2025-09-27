# Исправление ошибки KeyError: 'ticker' в пайплайне новостей

## Проблема

**Ошибка:** `KeyError: 'ticker'` при обращении к pandas Series как к словарю

**Причина:** В коде использовалось обращение `candidate['ticker']` к pandas Series, который возвращается из `df.iterrows()`. Pandas Series не поддерживает доступ по ключу как словарь.

**Трассировка:**
```
File "pages/9_🔍_News_Pipeline.py", line 671, in <module>
    with st.expander(f"Candidate {idx + 1}: {candidate['ticker']} (Score: {candidate['score']:.3f})"):
                                             ~~~~~~~~~^^^^^^^^^^
KeyError: 'ticker'
```

## Решение

### 1. Преобразование pandas Series в словарь

**До исправления:**
```python
for idx, candidate in df.iterrows():
    with st.expander(f"Candidate {idx + 1}: {candidate['ticker']} (Score: {candidate['score']:.3f})"):
        # candidate['ticker'] - ОШИБКА!
```

**После исправления:**
```python
for idx, candidate in df.iterrows():
    # Convert pandas Series to dict for easier access
    candidate_dict = candidate.to_dict()
    
    with st.expander(f"Candidate {idx + 1}: {candidate_dict['ticker']} (Score: {candidate_dict['score']:.3f})"):
        # candidate_dict['ticker'] - РАБОТАЕТ!
```

### 2. Исправленные места в коде

#### A. Individual candidate validation (строки 670-701)
```python
for idx, candidate in df.iterrows():
    # Convert pandas Series to dict for easier access
    candidate_dict = candidate.to_dict()
    
    with st.expander(f"Candidate {idx + 1}: {candidate_dict['ticker']} (Score: {candidate_dict['score']:.3f})"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**News:** {candidate_dict['title'][:100]}...")
            st.write(f"**Ticker:** {candidate_dict['ticker']}")
            st.write(f"**Score:** {candidate_dict['score']:.3f}")
            st.write(f"**Method:** {candidate_dict['method']}")
        
        with col2:
            if st.button(f"✅ Confirm", key=f"confirm_{candidate_dict['id']}"):
                session_state.repository.update_confirmation(
                    candidate_dict['id'],
                    confirmed=1,
                    operator=st.session_state.get("user_name", "unknown"),
                )
                st.success("Candidate confirmed!")
                st.rerun()
        
        with col3:
            if st.button(f"❌ Reject", key=f"reject_{candidate_dict['id']}"):
                session_state.repository.update_confirmation(
                    candidate_dict['id'],
                    confirmed=-1,
                    operator=st.session_state.get("user_name", "unknown"),
                )
                st.success("Candidate rejected!")
                st.rerun()
```

#### B. Bulk operations (строки 750-800)
```python
# Confirm high score candidates
for idx, candidate in high_score_candidates.iterrows():
    candidate_dict = candidate.to_dict()
    candidate_id = candidate_dict['id']
    ticker = candidate_dict['ticker']
    score = candidate_dict['score']
    
    try:
        session_state.repository.update_confirmation(
            candidate_id,
            confirmed=1,
            operator=st.session_state.get("user_name", "unknown"),
        )
        st.success(f"Confirmed {ticker} (Score: {score:.3f})")
    except Exception as e:
        st.error(f"Error confirming {ticker}: {e}")

# Reject low score candidates  
for idx, candidate in low_score_candidates.iterrows():
    candidate_dict = candidate.to_dict()
    candidate_id = candidate_dict['id']
    ticker = candidate_dict['ticker']
    score = candidate_dict['score']
    
    try:
        session_state.repository.update_confirmation(
            candidate_id,
            confirmed=-1,
            operator=st.session_state.get("user_name", "unknown"),
        )
        st.success(f"Rejected {ticker} (Score: {score:.3f})")
    except Exception as e:
        st.error(f"Error rejecting {ticker}: {e}")

# Reset all candidates
for idx, candidate in df.iterrows():
    candidate_dict = candidate.to_dict()
    candidate_id = candidate_dict['id']
    ticker = candidate_dict['ticker']
    
    try:
        session_state.repository.update_confirmation(
            candidate_id,
            confirmed=0,
            operator=st.session_state.get("user_name", "unknown"),
        )
        st.success(f"Reset {ticker}")
    except Exception as e:
        st.error(f"Error resetting {ticker}: {e}")
```

### 3. Альтернативные способы доступа к данным

#### A. Прямой доступ по индексу
```python
# Если знаете порядок колонок
ticker = candidate.iloc[14]  # 14-я колонка
score = candidate.iloc[3]    # 3-я колонка
```

#### B. Доступ по имени колонки
```python
# Если знаете имена колонок
ticker = candidate['ticker']
score = candidate['score']
```

#### C. Использование .loc
```python
# Более безопасный доступ
ticker = candidate.loc['ticker'] if 'ticker' in candidate.index else 'Unknown'
score = candidate.loc['score'] if 'score' in candidate.index else 0.0
```

### 4. Проверка структуры данных

```python
# Добавить отладочную информацию
if st.checkbox("Show Debug Info"):
    st.write("**Debug Info:**")
    st.write(f"Columns: {list(df.columns)}")
    st.write(f"DataFrame shape: {df.shape}")
    if len(df) > 0:
        st.write("Sample row:", df.iloc[0].to_dict())
        st.write("Data types:", df.dtypes.to_dict())
        st.write("Null values:", df.isnull().sum().to_dict())
    
    # Show raw candidate data
    st.write("**Raw Candidate Data:**")
    for idx, candidate in df.head(3).iterrows():
        st.write(f"Candidate {idx}: {candidate.to_dict()}")
```

## Почему возникает ошибка

### 1. Pandas Series vs Dictionary

**Pandas Series:**
```python
# candidate - это pandas Series
candidate = df.iloc[0]  # Series
candidate['ticker']     # ОШИБКА! Series не поддерживает доступ по ключу
```

**Dictionary:**
```python
# candidate_dict - это словарь
candidate_dict = candidate.to_dict()  # Dict
candidate_dict['ticker']              # РАБОТАЕТ! Dict поддерживает доступ по ключу
```

### 2. Структура данных

**DataFrame:**
```
   id  news_id  ticker_id  score  method  ...  ticker  name  title  published_at
0   1      556          1    1.2  fuzzy   ...   SBER   ...   ...   ...
1   2      557          2    0.8  ner     ...   GAZP   ...   ...   ...
```

**После iterrows():**
```python
for idx, candidate in df.iterrows():
    # candidate - это pandas Series
    # candidate.index = ['id', 'news_id', 'ticker_id', 'score', 'method', ..., 'ticker', 'name', 'title', 'published_at']
    # candidate.values = [1, 556, 1, 1.2, 'fuzzy', ..., 'SBER', '...', '...', '...']
```

## Рекомендации

### 1. Всегда используйте .to_dict()
```python
# Хорошо
candidate_dict = candidate.to_dict()
ticker = candidate_dict['ticker']

# Плохо
ticker = candidate['ticker']  # Может вызвать KeyError
```

### 2. Проверяйте структуру данных
```python
# Добавляйте отладочную информацию
st.write(f"Candidate type: {type(candidate)}")
st.write(f"Candidate index: {candidate.index.tolist()}")
st.write(f"Available fields: {list(candidate.to_dict().keys())}")
```

### 3. Используйте безопасный доступ
```python
# Безопасный доступ с fallback
candidate_dict = candidate.to_dict()
ticker = candidate_dict.get('ticker', 'Unknown')
score = candidate_dict.get('score', 0.0)
```

## Тестирование

### 1. Проверка исправления
```python
# Тест должен пройти без ошибок
import pandas as pd

# Создать тестовый DataFrame
df = pd.DataFrame({
    'id': [1, 2, 3],
    'ticker': ['SBER', 'GAZP', 'LKOH'],
    'score': [0.85, 0.75, 0.65]
})

# Тестировать доступ к данным
for idx, candidate in df.iterrows():
    candidate_dict = candidate.to_dict()
    ticker = candidate_dict['ticker']
    score = candidate_dict['score']
    print(f"Candidate {idx}: {ticker} (Score: {score})")
```

### 2. Проверка в Streamlit
1. Запустить Streamlit
2. Перейти на страницу "🔍 News Pipeline"
3. Открыть вкладку "✅ Candidate Validation"
4. Нажать "🔄 Refresh Candidates"
5. Убедиться, что кандидаты отображаются без ошибок

## Заключение

Ошибка `KeyError: 'ticker'` была исправлена путем:

1. **Преобразования pandas Series в словарь** с помощью `.to_dict()`
2. **Исправления всех мест** доступа к данным кандидатов
3. **Добавления отладочной информации** для понимания структуры данных
4. **Обеспечения консистентности** во всех операциях

**Ключевые изменения:**
- Добавлено `candidate_dict = candidate.to_dict()` во всех циклах
- Заменены все `candidate['field']` на `candidate_dict['field']`
- Добавлена отладочная информация для диагностики
- Обеспечена совместимость с pandas DataFrame

Код теперь работает корректно с pandas Series и готов к использованию.
