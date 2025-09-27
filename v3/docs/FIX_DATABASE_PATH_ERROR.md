# 🔧 Исправление ошибки 'PipelineConfig' object has no attribute 'database_path'

## Проблема

**Ошибка:** `'PipelineConfig' object has no attribute 'database_path'`

**Причина:** В коде пытались получить `database_path` из `PipelineConfig`, но этот атрибут не существует в классе `PipelineConfig`.

## Анализ

### Структура PipelineConfig

```python
@dataclass(frozen=True)
class PipelineConfig:
    batch_size: int = 100
    chunk_size: int = 100
    auto_apply_threshold: float = 0.85
    # ... другие параметры
    extra: Dict[str, Any] = field(default_factory=dict)
    # НЕТ database_path!
```

### Структура NewsPipelineRepository

```python
class NewsPipelineRepository:
    def __init__(self, db_path: Optional[Path | str] = None):
        settings = get_settings()
        if db_path is None:
            db_path = settings.database_path  # Получает из settings
        self.db_path = Path(db_path).expanduser().resolve()
```

## Решение

### Было (неправильно):
```python
from core.news_pipeline.repository import NewsPipelineRepository
from core.news_pipeline.config import load_pipeline_config

config = load_pipeline_config()
repository = NewsPipelineRepository(config.database_path)  # ❌ Ошибка!
```

### Стало (правильно):
```python
from core.news_pipeline.repository import NewsPipelineRepository

# Create repository (it will get database path from settings)
repository = NewsPipelineRepository()  # ✅ Правильно!
```

## Объяснение

1. **`PipelineConfig`** содержит только параметры конфигурации пайплайна (размеры батчей, пороги, модели и т.д.)
2. **`NewsPipelineRepository`** получает путь к базе данных из `settings.database_path`
3. **`settings`** - это глобальные настройки приложения, которые содержат путь к базе данных

## Логика работы

```python
class NewsPipelineRepository:
    def __init__(self, db_path: Optional[Path | str] = None):
        settings = get_settings()  # Получаем настройки приложения
        if db_path is None:
            db_path = settings.database_path  # Используем путь из настроек
        self.db_path = Path(db_path).expanduser().resolve()
```

## Проверка других файлов

Проверены файлы на наличие аналогичных ошибок:
- ✅ `pages/9_🔍_News_Pipeline.py` - нет проблем
- ✅ `pages/10_🔗_Integration_Test.py` - нет проблем
- ✅ `pages/8_🗞️_News.py` - исправлено

## Результат

✅ **Ошибка исправлена!**

Теперь:
- `NewsPipelineRepository()` создается без параметров
- Путь к базе данных получается из `settings.database_path`
- Кнопка "🔄 Обновить тикеры" работает корректно
- Нет ошибок при обновлении тикеров

## Использование

```python
# Правильный способ создания repository
from core.news_pipeline.repository import NewsPipelineRepository

repository = NewsPipelineRepository()  # Автоматически получит путь из settings
```

## Заключение

Ошибка была вызвана неправильным пониманием архитектуры:
- **`PipelineConfig`** - для параметров пайплайна
- **`settings`** - для путей к файлам и базе данных
- **`NewsPipelineRepository`** - получает путь из `settings`, а не из `PipelineConfig`

Теперь код работает корректно и использует правильную архитектуру!
