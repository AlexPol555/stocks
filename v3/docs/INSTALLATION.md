# Установка и настройка News Pipeline

## Системные требования

- Python 3.8+
- 4+ GB RAM (рекомендуется 16+ GB для больших объёмов)
- 2+ CPU cores (рекомендуется 8+ cores для больших объёмов)
- 10+ GB свободного места на диске

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd stocks/v3
```

### 2. Создание виртуального окружения

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Установка spaCy моделей (опционально)

```bash
# Русская модель
python -m spacy download ru_core_news_sm

# Английская модель (fallback)
python -m spacy download en_core_web_sm
```

### 5. Настройка конфигурации

Создайте файл `config/news_pipeline.yml`:

```yaml
# Batch processing settings
batch_size: 100
chunk_size: 50

# Scoring thresholds
auto_apply_threshold: 0.85
review_lower_threshold: 0.60

# Fuzzy matching
fuzzy_threshold: 65

# Cosine similarity thresholds
cos_candidate_threshold: 0.60
cos_auto_threshold: 0.80

# Embedding model
embedding_model: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Performance settings
use_faiss: false
cache_embeddings: true
auto_apply_confirm: true
```

## Запуск

### 1. Демонстрация

```bash
# Windows
scripts/run_demo.bat

# Linux/macOS
./scripts/run_demo.sh

# Или напрямую
python tests/demo_news_pipeline.py
```

### 2. Streamlit интерфейс

```bash
streamlit run pages/9_🔍_News_Pipeline.py
```

### 3. Тестирование

```bash
# Все тесты
python -m pytest tests/

# Только unit тесты
python -m pytest tests/test_news_pipeline.py

# Только integration тесты
python -m pytest tests/test_integration.py

# С покрытием
python -m pytest --cov=core.news_pipeline tests/
```

## Настройка для продакшена

### 1. Переменные окружения

```bash
# Windows
set NEWS_PIPELINE_CONFIG=config/production.yml
set DATABASE_PATH=data/production.db

# Linux/macOS
export NEWS_PIPELINE_CONFIG=config/production.yml
export DATABASE_PATH=data/production.db
```

### 2. Конфигурация для больших объёмов

```yaml
# config/production.yml
batch_size: 500
chunk_size: 200
use_faiss: true
cache_embeddings: true

# Мониторинг
monitoring:
  enabled: true
  metrics_retention_days: 90
  health_check_interval: 300

# Логирование
logging:
  level: INFO
  file: "logs/news_pipeline.log"
  max_size: 52428800  # 50MB
  backup_count: 10
```

### 3. Системные требования для продакшена

| Объём данных | CPU | RAM | Время обработки |
|--------------|-----|-----|-----------------|
| 1K новостей | 4 cores | 16GB | ~5-10 минут |
| 10K новостей | 8 cores | 32GB | ~30-60 минут |
| 100K+ новостей | 16+ cores | 64GB+ | ~2-6 часов |

## Troubleshooting

### Частые проблемы

1. **Ошибка загрузки модели эмбеддингов**
   ```
   RuntimeError: sentence-transformers model not found
   ```
   **Решение:**
   ```bash
   pip install sentence-transformers
   ```

2. **Медленная обработка**
   **Решение:**
   ```yaml
   # Увеличить chunk_size и использовать FAISS
   chunk_size: 200
   use_faiss: true
   ```

3. **Высокое использование памяти**
   **Решение:**
   ```yaml
   # Уменьшить batch_size и chunk_size
   batch_size: 50
   chunk_size: 25
   ```

4. **Ошибки в NER**
   ```
   OSError: Can't find model 'ru_core_news_sm'
   ```
   **Решение:**
   ```bash
   python -m spacy download ru_core_news_sm
   ```

5. **Проблемы с SQLite при больших объёмах**
   **Решение:**
   - Переход на PostgreSQL
   - Использование batch-транзакций
   - Партиционирование таблиц

### Логи и отладка

Логи сохраняются в:
- `logs/news_pipeline.log` - основные логи
- `metrics/performance_metrics.jsonl` - метрики производительности
- `metrics/system_health.jsonl` - метрики здоровья системы

Для отладки включите детальное логирование:

```yaml
logging:
  level: DEBUG
  format: "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
```

## Производительность

### Оптимизация для больших объёмов

1. **Использование FAISS для векторного поиска**
   ```yaml
   use_faiss: true
   ```

2. **GPU ускорение для эмбеддингов**
   ```bash
   pip install faiss-gpu torch
   ```

3. **Увеличение размера чанков**
   ```yaml
   chunk_size: 200
   ```

4. **Кэширование эмбеддингов**
   ```yaml
   cache_embeddings: true
   ```

5. **Параллельная обработка**
   ```yaml
   # В будущих версиях
   parallel_processing: true
   max_workers: 4
   ```

### Мониторинг производительности

Система автоматически собирает метрики:
- Время обработки
- Throughput (новостей в секунду)
- Использование памяти
- Загрузка CPU
- Процент ошибок

Метрики доступны в Streamlit интерфейсе на вкладке "Statistics".

## Безопасность

### Рекомендации

1. **Ограничение доступа к базе данных**
   - Используйте файловые разрешения
   - Не храните базу в публичных директориях

2. **Валидация входных данных**
   - Система автоматически валидирует конфигурацию
   - Проверяет корректность данных в базе

3. **Логирование операций**
   - Все операции логируются
   - Audit trail для изменений кандидатов

4. **Резервное копирование**
   - Регулярно создавайте бэкапы базы данных
   - Сохраняйте конфигурационные файлы

## Поддержка

### Получение помощи

1. **Документация**: `docs/README_News_Pipeline.md`
2. **Демонстрация**: `tests/demo_news_pipeline.py`
3. **Тесты**: `tests/`
4. **Логи**: `logs/news_pipeline.log`

### Сообщение об ошибках

При сообщении об ошибке приложите:
- Версию Python
- Версии зависимостей (`pip list`)
- Конфигурационный файл
- Логи ошибки
- Шаги для воспроизведения

### Вклад в развитие

1. Fork репозитория
2. Создайте feature branch
3. Добавьте тесты
4. Создайте pull request
