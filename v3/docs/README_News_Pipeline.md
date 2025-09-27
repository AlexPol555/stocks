# News Pipeline - Масштабируемый пайплайн для генерации кандидатов-тикеров

## Обзор

Масштабируемый и надёжный пайплайн для обработки новостей и генерации кандидатов-тикеров. Система поддерживает обработку партий новостей любой величины, от десятков до сотен и более, с возможностью масштабирования до нескольких тысяч при наличии ресурсов.

## Основные возможности

### 🚀 Batch Processing
- **Конфигурируемый размер партии**: от 10 до N (N может быть >100)
- **Chunking**: автоматическое разбиение больших партий на чанки
- **Идемпотентность**: повторный запуск не создаёт дубликатов
- **Режимы обработки**:
  - `only_unprocessed` - только необработанные новости
  - `recheck_all` - переобработка всех новостей
  - `recheck_selected_range` - переобработка выбранного диапазона

### 🔍 Candidate Generation
- **Substring matching**: точное совпадение тикеров и алиасов
- **Fuzzy matching**: нечёткое совпадение с нормализацией
- **NER (Named Entity Recognition)**: извлечение организаций и персон
- **Semantic embeddings**: векторный поиск по смыслу
- **Hybrid scoring**: комбинирование всех методов

### ✅ Human-in-the-Loop Validation
- **Streamlit интерфейс** для валидации кандидатов
- **Массовые операции**: подтверждение/отклонение по порогам
- **Ручное добавление** тикеров
- **Audit trail**: отслеживание всех изменений

### 📊 Мониторинг и метрики
- **Performance metrics**: время обработки, throughput, ошибки
- **System health**: состояние системы, ресурсы, база данных
- **Alerting**: уведомления о проблемах
- **История обработки**: отслеживание всех запусков

## Архитектура

### Компоненты системы

```
core/news_pipeline/
├── __init__.py              # Основные экспорты
├── config.py                # Конфигурация и настройки
├── models.py                # Модели данных
├── repository.py            # Работа с базой данных
├── processor.py             # Основной процессор
├── progress.py              # Отслеживание прогресса
├── monitoring.py            # Мониторинг и метрики
├── preprocessing.py         # Предобработка текста
├── embeddings.py            # Векторные эмбеддинги
├── generators/              # Генераторы кандидатов
│   ├── __init__.py
│   ├── substring.py         # Substring matching
│   ├── fuzzy.py             # Fuzzy matching
│   ├── ner.py               # Named Entity Recognition
│   └── semantic.py          # Semantic embeddings
└── workflows.py             # Рабочие процессы
```

### Поток данных

```
News Articles → Preprocessing → Candidate Generation → Scoring → Validation → Database
     ↓              ↓                    ↓                ↓           ↓
  Sources      Text Cleaning        Multiple Methods   Hybrid     Confirmed
  Articles     Normalization        Substring         Scoring    Tickers
  Metadata     Tokenization         Fuzzy             Ranking    Rejected
               Language Detection   NER               Filtering  Pending
                                   Semantic
```

## Установка и настройка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка конфигурации

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

### 3. Инициализация базы данных

```python
from core.news_pipeline import NewsPipelineRepository

repository = NewsPipelineRepository()
repository.ensure_schema()
```

## Использование

### 1. Базовое использование

```python
from core.news_pipeline import NewsBatchProcessor, PipelineConfig, load_pipeline_config

# Load configuration
config = load_pipeline_config()

# Create processor
processor = NewsBatchProcessor(repository)
processor.initialize(config)

# Process news batch
request = PipelineRequest(
    mode=BatchMode.ONLY_UNPROCESSED,
    batch_size=100,
    chunk_size=50
)

result = processor.process_batch(request)
print(f"Processed {result.processed_count} articles")
print(f"Generated {result.candidates_count} candidates")
```

### 2. Streamlit интерфейс

```bash
streamlit run pages/9_🔍_News_Pipeline.py
```

### 3. Программное управление

```python
# Check processing status
status = processor.get_processing_status()
print(f"Status: {status.status}")
print(f"Progress: {status.progress_percent}%")

# Get candidates for validation
candidates = repository.fetch_pending_candidates(limit=50)
for candidate in candidates:
    print(f"Ticker: {candidate.ticker}, Score: {candidate.score}")

# Confirm candidates
repository.update_confirmation(
    candidate_id=123,
    confirmed=1,
    operator="user@example.com"
)
```

## Конфигурация

### Основные параметры

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `batch_size` | Размер партии для обработки | 100 |
| `chunk_size` | Размер чанка для обработки | 50 |
| `auto_apply_threshold` | Порог для автоматического подтверждения | 0.85 |
| `review_lower_threshold` | Нижний порог для ручного review | 0.60 |
| `fuzzy_threshold` | Порог для fuzzy matching | 65 |
| `cos_candidate_threshold` | Порог для cosine similarity кандидатов | 0.60 |
| `cos_auto_threshold` | Порог для автоматического подтверждения | 0.80 |

### Настройки производительности

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `use_faiss` | Использовать FAISS для векторного поиска | false |
| `cache_embeddings` | Кэшировать эмбеддинги | true |
| `auto_apply_confirm` | Автоматически подтверждать высокооцененные | true |

### Модели и алгоритмы

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `embedding_model` | Модель для эмбеддингов | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| `ner_model` | Модель для NER | ru_core_news_sm |
| `fuzzy_algorithm` | Алгоритм fuzzy matching | rapidfuzz |

## Мониторинг

### 1. Метрики производительности

```python
# Get performance metrics
metrics = processor.get_performance_metrics()
print(f"Throughput: {metrics.throughput} articles/sec")
print(f"Average processing time: {metrics.avg_processing_time}ms")
print(f"Error rate: {metrics.error_rate}%")
```

### 2. Состояние системы

```python
# Get system health
health = processor.get_system_health()
print(f"CPU usage: {health.cpu_usage}%")
print(f"Memory usage: {health.memory_usage}%")
print(f"Database status: {health.database_status}")
```

### 3. История обработки

```python
# Get processing history
history = repository.get_processing_history(limit=10)
for run in history:
    print(f"Run {run.id}: {run.status} - {run.processed_count} articles")
```

## Troubleshooting

### 1. Медленная обработка

**Проблема:** Обработка занимает слишком много времени.

**Решения:**
- Увеличить `chunk_size` для параллельной обработки
- Включить `use_faiss` для быстрого векторного поиска
- Увеличить `batch_size` для уменьшения overhead

### 2. Высокое использование памяти

**Проблема:** Система использует слишком много памяти.

**Решения:**
- Уменьшить `batch_size` и `chunk_size`
- Отключить `cache_embeddings`
- Использовать более легкую модель эмбеддингов

### 3. Низкое качество кандидатов

**Проблема:** Генерируется много ложных кандидатов.

**Решения:**
- Увеличить пороги (`cos_candidate_threshold`, `fuzzy_threshold`)
- Настроить веса методов в hybrid scoring
- Улучшить качество алиасов в таблице `tickers`

### 4. Ошибки базы данных

**Проблема:** Ошибки при работе с базой данных.

**Решения:**
- Проверить подключение к базе данных
- Убедиться, что схема создана правильно
- Проверить права доступа к базе данных

## Производительность

### Рекомендации по масштабированию

| Объём данных | CPU | RAM | Время обработки |
|--------------|-----|-----|-----------------|
| 1K новостей | 4 cores | 16GB | ~5-10 минут |
| 10K новостей | 8 cores | 32GB | ~30-60 минут |
| 100K+ новостей | 16+ cores | 64GB+ | ~2-6 часов |

### Оптимизация

1. **Использование FAISS** для векторного поиска
2. **GPU ускорение** для эмбеддингов
3. **Параллельная обработка** чанков
4. **Кэширование** эмбеддингов
5. **Batch операции** с базой данных

## Безопасность

### Рекомендации

1. **Ограничение доступа** к базе данных
2. **Валидация входных данных**
3. **Логирование операций**
4. **Резервное копирование**

### Audit Trail

Все операции логируются:
- Создание кандидатов
- Подтверждение/отклонение
- Изменения конфигурации
- Ошибки и исключения

## Поддержка

### Документация

- [Установка и настройка](INSTALLATION.md)
- [Быстрый старт](QUICK_START.md)
- [Руководство по диагностике](DIAGNOSTIC_GUIDE.md)
- [Исправления проблем](fixes/)

### Тестирование

```bash
# Запуск тестов
python -m pytest tests/

# С покрытием
python -m pytest --cov=core.news_pipeline tests/
```

### Логи

Логи сохраняются в:
- `logs/news_pipeline.log` - основные логи
- `metrics/performance_metrics.jsonl` - метрики производительности
- `metrics/system_health.jsonl` - метрики здоровья системы

## Заключение

News Pipeline предоставляет мощный и масштабируемый инструмент для обработки новостей и генерации кандидатов-тикеров. Система спроектирована для работы с большими объёмами данных и может быть легко адаптирована под различные требования.

**Ключевые преимущества:**
- Масштабируемость до тысяч новостей
- Множественные методы генерации кандидатов
- Human-in-the-loop валидация
- Комплексный мониторинг
- Гибкая конфигурация

Система готова к использованию в продакшене и может быть легко интегрирована в существующие рабочие процессы.
