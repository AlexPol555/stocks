# News Parser

Проект для агрегации финансовых новостей российских изданий с сохранением в локальную базу SQLite и генерацией ежедневной сводки.

## Возможности

- Парсинг RSS-лент и HTML fallback
- Сохранение новостей в SQLite с FTS5 индексом
- Дедупликация статей по хэшу
- Привязка упоминаний к тикерам
- Генерация JSON сводки «Что случилось вчера»
- Минимальный UI на Streamlit с кнопкой запуска

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка

По умолчанию конфигурация берётся из переменных окружения. Можно передать путь к JSON файлу:

```json
{
  "db_path": "./data/news.db",
  "request_timeout": 20,
  "request_delay": 1.0,
  "sources": [
    {"name": "РБК", "rss_url": "https://rssexport.rbc.ru/rbcnews/news/20/full.rss", "website": "https://www.rbc.ru"}
  ]
}
```

Сохраните файл и передайте его через `--config`.

## Запуск парсера

Одноразовый запуск:

```bash
python -m news_parser.main --once
```

Генерация сводки:

```bash
python -m news_parser.main --summary --date 2024-05-01 --output output
```

## UI

```bash
streamlit run streamlit_app.py
```

## Тесты

```bash
pytest
```

