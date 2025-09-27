# Исправление дублирующихся ID элементов Streamlit

## Проблема

Ошибка: `StreamlitDuplicateElementId: There are multiple number_input elements with the same auto-generated ID`

## Причина

В Streamlit каждый элемент должен иметь уникальный ID. Когда элементы создаются с одинаковыми параметрами, Streamlit автоматически генерирует одинаковые ID, что приводит к конфликту.

## Решение

Добавлены уникальные ключи (`key`) для всех элементов Streamlit в файле `pages/9_🔍_News_Pipeline.py`:

### 1. Number Input элементы

```python
# Было
batch_size = st.number_input("Batch Size", ...)

# Стало
batch_size = st.number_input("Batch Size", ..., key="batch_size_input")
```

### 2. Slider элементы

```python
# Было
min_score = st.slider("Minimum Score", ...)

# Стало
min_score = st.slider("Minimum Score", ..., key="validation_min_score_slider")
```

### 3. Button элементы

```python
# Было
if st.button("🚀 Start Processing"):

# Стало
if st.button("🚀 Start Processing", key="start_processing_button"):
```

### 4. Checkbox элементы

```python
# Было
only_unconfirmed = st.checkbox("Only Unconfirmed", ...)

# Стало
only_unconfirmed = st.checkbox("Only Unconfirmed", ..., key="validation_only_unconfirmed_checkbox")
```

### 5. Selectbox элементы

```python
# Было
mode = st.selectbox("Processing Mode", ...)

# Стало
mode = st.selectbox("Processing Mode", ..., key="processing_mode_selectbox")
```

### 6. Date Input элементы

```python
# Было
range_start = st.date_input("Start Date", ...)

# Стало
range_start = st.date_input("Start Date", ..., key="range_start_date_input")
```

## Список добавленных ключей

### Batch Processing
- `processing_mode_selectbox` - выбор режима обработки
- `batch_size_input` - размер партии
- `chunk_size_input` - размер чанка
- `dry_run_checkbox` - режим dry run
- `range_start_date_input` - начальная дата
- `range_end_date_input` - конечная дата
- `start_processing_button` - кнопка запуска
- `stop_processing_button` - кнопка остановки
- `reset_status_button` - кнопка сброса статуса

### Candidate Validation
- `validation_min_score_slider` - минимальный score
- `validation_only_unconfirmed_checkbox` - только неподтвержденные
- `candidates_limit_input` - лимит кандидатов
- `refresh_candidates_button` - обновить кандидатов
- `confirm_all_high_score_button` - подтвердить все с высоким score
- `reject_all_low_score_button` - отклонить все с низким score
- `reset_all_button` - сбросить все
- `reset_all_confirm_checkbox` - подтверждение сброса
- `confirm_high_score_threshold_slider` - порог для подтверждения
- `reject_low_score_threshold_slider` - порог для отклонения

### Statistics
- `refresh_statistics_button` - обновить статистику

### Configuration
- `config_batch_size_input` - размер партии в конфигурации
- `config_chunk_size_input` - размер чанка в конфигурации
- `config_auto_apply_threshold_slider` - порог авто-применения
- `config_review_lower_threshold_slider` - нижний порог для review
- `config_fuzzy_threshold_input` - порог fuzzy matching
- `config_cos_candidate_threshold_slider` - порог cosine для кандидатов
- `config_cos_auto_threshold_slider` - порог cosine для авто-применения
- `config_auto_apply_confirm_checkbox` - авто-подтверждение
- `save_configuration_button` - сохранить конфигурацию
- `export_configuration_button` - экспорт конфигурации
- `apply_imported_configuration_button` - применить импортированную конфигурацию

## Проверка

После исправления:

1. **Запустить Streamlit:**
   ```bash
   streamlit run pages/9_🔍_News_Pipeline.py
   ```

2. **Проверить в браузере:**
   - Открыть http://localhost:8501
   - Перейти на страницу "🔍 News Pipeline"
   - Убедиться, что нет ошибок дублирующихся ID

## Дополнительные рекомендации

### 1. Именование ключей
- Использовать описательные имена
- Группировать по функциональности (например, `config_`, `validation_`)
- Избегать слишком длинных имен

### 2. Структура ключей
```
{section}_{element_type}_{purpose}
```
Примеры:
- `config_batch_size_input`
- `validation_min_score_slider`
- `processing_start_button`

### 3. Избежание конфликтов
- Всегда добавлять ключи для элементов в циклах
- Использовать уникальные ключи для динамических элементов
- Проверять уникальность ключей при добавлении новых элементов

## Если проблема сохраняется

1. Очистить кэш Streamlit:
   ```bash
   # Удалить папку .streamlit
   rm -rf .streamlit
   ```

2. Перезапустить Streamlit:
   ```bash
   # Остановить (Ctrl+C) и запустить заново
   streamlit run pages/9_🔍_News_Pipeline.py
   ```

3. Проверить логи:
   - Открыть Developer Tools в браузере
   - Проверить консоль на ошибки

4. Обновить Streamlit:
   ```bash
   pip install --upgrade streamlit
   ```
