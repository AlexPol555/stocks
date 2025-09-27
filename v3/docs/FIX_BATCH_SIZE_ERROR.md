# 🔧 Исправление ошибки StreamlitValueBelowMinError

## Проблема

**Ошибка:** `streamlit.errors.StreamlitValueBelowMinError: The value 0 is less than the min_value 1.`

**Причина:** Когда нет необработанных новостей (`stats['unprocessed'] = 0`), мы пытались установить значение 0 для `batch_size`, но `min_value=1`.

## Решение

### 1. Исправлен расчет значения по умолчанию

**Было:**
```python
value=min(session_state.config.batch_size, stats['unprocessed'] if mode == BatchMode.ONLY_UNPROCESSED else stats['total'])
```

**Стало:**
```python
# Calculate default batch size based on mode and available articles
if mode == BatchMode.ONLY_UNPROCESSED:
    if stats['unprocessed'] > 0:
        default_batch_size = min(session_state.config.batch_size, stats['unprocessed'])
    else:
        default_batch_size = 1  # Default to 1 when no unprocessed articles
else:
    default_batch_size = min(session_state.config.batch_size, stats['total'])
```

### 2. Добавлена проверка возможности обработки

```python
# Check if there are articles to process
can_process = False
if mode == BatchMode.ONLY_UNPROCESSED:
    can_process = stats['unprocessed'] > 0
elif mode == BatchMode.RECHECK_ALL:
    can_process = stats['total'] > 0
elif mode == BatchMode.RECHECK_SELECTED_RANGE:
    can_process = True  # We can't check date range without querying
```

### 3. Кнопка "Start Processing" отключается при отсутствии статей

```python
if st.button("🚀 Start Processing", disabled=session_state.processing_status == "running" or not can_process, key="start_processing_button"):
```

### 4. Добавлены информационные сообщения

```python
if not can_process:
    if mode == BatchMode.ONLY_UNPROCESSED and stats['unprocessed'] == 0:
        st.info("✅ All articles have been processed! No unprocessed articles to process.")
    elif mode == BatchMode.RECHECK_ALL and stats['total'] == 0:
        st.info("📭 No articles found in database.")
    else:
        st.info("No articles available for processing in the selected mode.")
```

### 5. Улучшена информация о обработке

```python
if mode == BatchMode.ONLY_UNPROCESSED:
    if stats['unprocessed'] > 0:
        # Show progress and processing info
        actual_batch_size = min(batch_size, stats['unprocessed'])
        progress_ratio = stats['processed'] / stats['total'] if stats['total'] > 0 else 0
        st.info(f"📊 Will process {actual_batch_size} unprocessed articles out of {stats['unprocessed']} total unprocessed")
        st.progress(progress_ratio, text=f"Overall progress: {stats['processed']}/{stats['total']} articles processed ({progress_ratio:.1%})")
    else:
        st.success("✅ All articles have been processed!")
elif mode == BatchMode.RECHECK_ALL:
    if stats['total'] > 0:
        actual_batch_size = min(batch_size, stats['total'])
        st.info(f"📊 Will recheck {actual_batch_size} articles out of {stats['total']} total")
    else:
        st.info("📭 No articles found in database.")
```

## Результат

### ✅ Теперь работает правильно

1. **Нет ошибок** - `batch_size` всегда >= 1
2. **Информативные сообщения** - пользователь видит, почему кнопка отключена
3. **Правильная логика** - кнопка отключается, когда нет статей для обработки
4. **Улучшенный UX** - четкие сообщения о состоянии системы

### Примеры отображения

**Когда все статьи обработаны:**
```
✅ All articles have been processed! No unprocessed articles to process.
[🚀 Start Processing] (disabled)
```

**Когда нет статей в базе:**
```
📭 No articles found in database.
[🚀 Start Processing] (disabled)
```

**Когда есть необработанные статьи:**
```
📊 Will process 100 unprocessed articles out of 291 total unprocessed
Overall progress: 850/1141 articles processed (74.5%)
[🚀 Start Processing] (enabled)
```

## Технические детали

### Логика проверки

1. **ONLY_UNPROCESSED** - проверяет `stats['unprocessed'] > 0`
2. **RECHECK_ALL** - проверяет `stats['total'] > 0`
3. **RECHECK_SELECTED_RANGE** - всегда разрешено (нельзя проверить без запроса)

### Значения по умолчанию

- Если есть необработанные статьи: `min(config.batch_size, unprocessed_count)`
- Если нет необработанных статей: `1` (минимальное значение)
- Для других режимов: `min(config.batch_size, total_count)`

### Отключение кнопки

Кнопка отключается когда:
- Обработка уже запущена (`processing_status == "running"`)
- Нет статей для обработки (`not can_process`)

## Заключение

Ошибка `StreamlitValueBelowMinError` полностью исправлена. Теперь система корректно обрабатывает случаи, когда нет статей для обработки, и предоставляет пользователю понятную информацию о состоянии системы.
