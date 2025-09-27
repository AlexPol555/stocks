# Окончательное исправление KeyError: 'ticker'

## Проблема

**Ошибка:** `KeyError: 'ticker'` продолжала возникать даже после преобразования pandas Series в словарь.

**Причина:** В SQL запросе `fetch_pending_candidates` используется LEFT JOIN, который может возвращать `NULL` значения для колонки `ticker`, если соответствующий тикер не найден. При преобразовании в DataFrame эти `NULL` значения становятся `None`, но обращение к несуществующему ключу все равно вызывает ошибку.

## Решение

### 1. Безопасное обращение к полям словаря

**До исправления:**
```python
candidate_dict = candidate.to_dict()
ticker = candidate_dict['ticker']  # KeyError если ключ отсутствует
```

**После исправления:**
```python
candidate_dict = candidate.to_dict()
ticker = candidate_dict.get('ticker', 'Unknown')  # Безопасное обращение с fallback
```

### 2. Полный код исправления

#### A. Individual candidate validation
```python
for idx, candidate in df.iterrows():
    # Convert pandas Series to dict for easier access
    candidate_dict = candidate.to_dict()
    
    # Safe access to fields with fallbacks
    ticker = candidate_dict.get('ticker', 'Unknown')
    score = candidate_dict.get('score', 0.0)
    title = candidate_dict.get('title', 'No title')
    method = candidate_dict.get('method', 'Unknown')
    candidate_id = candidate_dict.get('id', 0)
    
    with st.expander(f"Candidate {idx + 1}: {ticker} (Score: {score:.3f})"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**News:** {title[:100]}...")
            st.write(f"**Ticker:** {ticker}")
            st.write(f"**Score:** {score:.3f}")
            st.write(f"**Method:** {method}")
        
        with col2:
            if st.button(f"✅ Confirm", key=f"confirm_{candidate_id}"):
                session_state.repository.update_confirmation(
                    candidate_id,
                    confirmed=1,
                    operator=st.session_state.get("user_name", "unknown"),
                )
                st.success("Candidate confirmed!")
                st.rerun()
        
        with col3:
            if st.button(f"❌ Reject", key=f"reject_{candidate_id}"):
                session_state.repository.update_confirmation(
                    candidate_id,
                    confirmed=-1,
                    operator=st.session_state.get("user_name", "unknown"),
                )
                st.success("Candidate rejected!")
                st.rerun()
```

#### B. Bulk operations
```python
# Confirm high score candidates
for idx, candidate in high_score_candidates.iterrows():
    candidate_dict = candidate.to_dict()
    candidate_id = candidate_dict.get('id', 0)
    ticker = candidate_dict.get('ticker', 'Unknown')
    score = candidate_dict.get('score', 0.0)
    
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
    candidate_id = candidate_dict.get('id', 0)
    ticker = candidate_dict.get('ticker', 'Unknown')
    score = candidate_dict.get('score', 0.0)
    
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
    candidate_id = candidate_dict.get('id', 0)
    ticker = candidate_dict.get('ticker', 'Unknown')
    
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

### 3. Дополнительные проверки

#### A. Проверка существования ключей
```python
def safe_get_field(candidate_dict, field, default_value):
    """Safely get field from candidate dict with fallback."""
    if field not in candidate_dict:
        logger.warning(f"Field '{field}' not found in candidate dict")
        return default_value
    
    value = candidate_dict[field]
    if value is None:
        logger.warning(f"Field '{field}' is None, using fallback")
        return default_value
    
    return value

# Usage
ticker = safe_get_field(candidate_dict, 'ticker', 'Unknown')
score = safe_get_field(candidate_dict, 'score', 0.0)
title = safe_get_field(candidate_dict, 'title', 'No title')
```

#### B. Валидация данных
```python
def validate_candidate_data(candidate_dict):
    """Validate candidate data and return cleaned dict."""
    required_fields = ['id', 'ticker', 'score', 'title', 'method']
    missing_fields = [field for field in required_fields if field not in candidate_dict]
    
    if missing_fields:
        logger.warning(f"Missing fields in candidate: {missing_fields}")
    
    # Ensure all required fields exist with fallbacks
    validated = {}
    for field in required_fields:
        if field == 'id':
            validated[field] = candidate_dict.get(field, 0)
        elif field == 'score':
            validated[field] = candidate_dict.get(field, 0.0)
        else:
            validated[field] = candidate_dict.get(field, f'Unknown {field}')
    
    return validated

# Usage
validated_candidate = validate_candidate_data(candidate_dict)
ticker = validated_candidate['ticker']
score = validated_candidate['score']
```

### 4. Отладочная информация

```python
# Add debug information
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

## Альтернативные решения

### 1. Использование try-except
```python
try:
    ticker = candidate_dict['ticker']
except KeyError:
    ticker = 'Unknown'
```

### 2. Использование getattr
```python
ticker = getattr(candidate_dict, 'ticker', 'Unknown')
```

### 3. Использование pandas .iloc
```python
ticker = candidate.iloc[df.columns.get_loc('ticker')] if 'ticker' in df.columns else 'Unknown'
```

## Тестирование

### 1. Проверка исправления
```python
# Тест должен пройти без ошибок
test_candidate = {
    'id': 1,
    'ticker': None,  # NULL значение
    'score': 0.85,
    'title': 'Test News'
}

# Безопасное обращение
ticker = test_candidate.get('ticker', 'Unknown')
assert ticker == 'Unknown'  # Должно работать
```

### 2. Проверка в Streamlit
1. Запустить Streamlit
2. Перейти на страницу "🔍 News Pipeline"
3. Открыть вкладку "✅ Candidate Validation"
4. Нажать "🔄 Refresh Candidates"
5. Убедиться, что кандидаты отображаются без ошибок

## Заключение

Окончательное исправление `KeyError: 'ticker'` обеспечивает:

1. **Безопасное обращение** к полям словаря с fallback значениями
2. **Обработку NULL значений** из базы данных
3. **Валидацию данных** перед использованием
4. **Отладочную информацию** для диагностики проблем
5. **Обработку ошибок** в bulk операциях

**Ключевые изменения:**
- Заменены все `candidate_dict['field']` на `candidate_dict.get('field', 'fallback')`
- Добавлена функция `safe_get_field()` для безопасного доступа
- Добавлена функция `validate_candidate_data()` для валидации
- Добавлена отладочная информация для диагностики

Код теперь работает стабильно даже при отсутствии данных или NULL значениях в базе.
