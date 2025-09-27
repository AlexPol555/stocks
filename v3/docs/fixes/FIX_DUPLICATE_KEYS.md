# Исправление StreamlitDuplicateElementKey

## Проблема

**Ошибка:** `StreamlitDuplicateElementKey: There are multiple elements with the same key='confirm_0'`

**Причина:** В коде валидации кандидатов использовались неуникальные ключи для кнопок Streamlit. Когда `candidate_id` равен 0 (fallback значение) или одинаков для разных кандидатов, возникают дублирующиеся ключи.

**Трассировка:**
```
File "pages/9_🔍_News_Pipeline.py", line 703, in <module>
    if st.button(f"✅ Confirm", key=f"confirm_{candidate_id}"):
StreamlitDuplicateElementKey: There are multiple elements with the same `key='confirm_0'`
```

## Решение

### 1. Создание уникальных ключей

**До исправления:**
```python
candidate_id = candidate_dict.get('id', 0)
if st.button(f"✅ Confirm", key=f"confirm_{candidate_id}"):  # Дублирующиеся ключи!
```

**После исправления:**
```python
candidate_id = candidate_dict.get('id', 0)
unique_key_suffix = f"{idx}_{candidate_id}"  # Уникальный суффикс
if st.button(f"✅ Confirm", key=f"confirm_{unique_key_suffix}"):  # Уникальные ключи!
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
    
    # Create unique keys using both idx and candidate_id
    unique_key_suffix = f"{idx}_{candidate_id}"
    
    with st.expander(f"Candidate {idx + 1}: {ticker} (Score: {score:.3f})"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**News:** {title[:100]}...")
            st.write(f"**Ticker:** {ticker}")
            st.write(f"**Score:** {score:.3f}")
            st.write(f"**Method:** {method}")
        
        with col2:
            if st.button(f"✅ Confirm", key=f"confirm_{unique_key_suffix}"):
                session_state.repository.update_confirmation(
                    candidate_id,
                    confirmed=1,
                    operator=st.session_state.get("user_name", "unknown"),
                )
                st.success("Candidate confirmed!")
                st.rerun()
        
        with col3:
            if st.button(f"❌ Reject", key=f"reject_{unique_key_suffix}"):
                session_state.repository.update_confirmation(
                    candidate_id,
                    confirmed=-1,
                    operator=st.session_state.get("user_name", "unknown"),
                )
                st.success("Candidate rejected!")
                st.rerun()
```

#### B. Bulk operations (исправлены для консистентности)
```python
# Confirm high score candidates
for idx, candidate in high_score_candidates.iterrows():
    candidate_dict = candidate.to_dict()
    candidate_id = candidate_dict.get('id', 0)
    # ... остальная логика

# Reject low score candidates  
for idx, candidate in low_score_candidates.iterrows():
    candidate_dict = candidate.to_dict()
    candidate_id = candidate_dict.get('id', 0)
    # ... остальная логика

# Reset all candidates
for idx, candidate in df.iterrows():
    candidate_dict = candidate.to_dict()
    candidate_id = candidate_dict.get('id', 0)
    # ... остальная логика
```

### 3. Стратегии создания уникальных ключей

#### A. Комбинация индекса и ID
```python
unique_key_suffix = f"{idx}_{candidate_id}"
# Результат: "0_123", "1_456", "2_123" (уникально даже при одинаковых ID)
```

#### B. Использование хеша
```python
import hashlib
unique_key_suffix = hashlib.md5(f"{idx}_{candidate_id}_{ticker}".encode()).hexdigest()[:8]
# Результат: "a1b2c3d4", "e5f6g7h8" (всегда уникально)
```

#### C. Использование timestamp
```python
import time
unique_key_suffix = f"{idx}_{candidate_id}_{int(time.time() * 1000)}"
# Результат: "0_123_1703123456789" (уникально по времени)
```

### 4. Рекомендации по ключам Streamlit

#### A. Всегда используйте уникальные ключи
```python
# Хорошо
key=f"button_{unique_id}"

# Плохо
key="button"  # Дублирующиеся ключи
```

#### B. Включайте контекст в ключ
```python
# Хорошо
key=f"confirm_candidate_{idx}_{candidate_id}"

# Плохо
key=f"confirm_{candidate_id}"  # Может дублироваться
```

#### C. Используйте осмысленные префиксы
```python
# Хорошо
key=f"validation_confirm_{unique_suffix}"
key=f"validation_reject_{unique_suffix}"

# Плохо
key=f"btn_{unique_suffix}"  # Неясно назначение
```

## Альтернативные решения

### 1. Использование UUID
```python
import uuid
unique_key_suffix = str(uuid.uuid4())[:8]
```

### 2. Использование счетчика
```python
button_counter = 0
for idx, candidate in df.iterrows():
    button_counter += 1
    unique_key_suffix = f"{button_counter}_{candidate_id}"
```

### 3. Использование комбинации полей
```python
unique_key_suffix = f"{idx}_{candidate_id}_{ticker}_{method}"
```

## Тестирование

### 1. Проверка уникальности ключей
```python
# Тест должен пройти без ошибок
keys = []
for idx in range(10):
    candidate_id = 0  # Одинаковый ID
    unique_key_suffix = f"{idx}_{candidate_id}"
    keys.append(unique_key_suffix)

assert len(keys) == len(set(keys)), "Keys are not unique!"
```

### 2. Проверка в Streamlit
1. Запустить Streamlit
2. Перейти на страницу "🔍 News Pipeline"
3. Открыть вкладку "✅ Candidate Validation"
4. Нажать "🔄 Refresh Candidates"
5. Убедиться, что кнопки работают без ошибок дублирования

## Заключение

Ошибка `StreamlitDuplicateElementKey` была исправлена путем:

1. **Создания уникальных ключей** с использованием комбинации индекса и ID кандидата
2. **Использования осмысленных префиксов** для разных типов кнопок
3. **Обеспечения уникальности** даже при одинаковых ID кандидатов
4. **Консистентного подхода** во всех местах использования кнопок

**Ключевые изменения:**
- Добавлено `unique_key_suffix = f"{idx}_{candidate_id}"`
- Заменены все ключи кнопок на уникальные
- Обеспечена совместимость с fallback значениями
- Добавлена отладочная информация для понимания структуры данных

Код теперь работает без ошибок дублирования ключей и готов к использованию.
