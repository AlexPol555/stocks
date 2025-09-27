# 📊 Статистика Batch Processing

## Добавленные возможности

### 1. Статистика новостей

На странице "🚀 Batch Processing" теперь отображается:

- **Total Articles** - общее количество статей в базе
- **Processed** - количество обработанных статей
- **Unprocessed** - количество необработанных статей
- **With Tickers** - количество статей с подтвержденными тикерами

### 2. Улучшенный выбор режима обработки

Режимы обработки теперь показывают количество статей:

- **Only Unprocessed News (X of Y)** - показывает количество необработанных из общего числа
- **Recheck All News (Y total)** - показывает общее количество статей
- **Recheck Selected Range** - для выбранного диапазона дат

### 3. Информация о предстоящей обработке

- Показывает, сколько статей будет обработано в текущем батче
- Для режима "Only Unprocessed" показывает прогресс-бар общего прогресса
- Автоматически ограничивает размер батча количеством доступных статей

### 4. Обновленная статистика после обработки

После завершения обработки показывается:

- **Updated Statistics** - обновленная статистика базы данных
- **Processing Results** - результаты текущей обработки

### 5. Кнопка обновления статистики

- Кнопка "🔄" для обновления статистики без перезапуска обработки

## Примеры отображения

### Статистика
```
Total Articles: 1141    Processed: 850    Unprocessed: 291    With Tickers: 45    [🔄]
```

### Режим обработки
```
Only Unprocessed News (291 of 1141)
```

### Информация о обработке
```
📊 Will process 100 unprocessed articles out of 291 total unprocessed
Overall progress: 850/1141 articles processed (74.5%)
```

### Результаты обработки
```
📊 Updated Statistics
Total Articles: 1141    Processed: 950    Unprocessed: 191    With Tickers: 67

🚀 Processing Results
Total News: 100    Processed: 100    Candidates Generated: 245    Auto Applied: 23
```

## Технические детали

### Функция `get_news_statistics()`

```python
def get_news_statistics(repository):
    """Get news processing statistics."""
    with repository.connect() as conn:
        # Total articles
        total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        
        # Processed articles
        processed_articles = conn.execute("SELECT COUNT(*) FROM articles WHERE processed = 1").fetchone()[0]
        
        # Unprocessed articles
        unprocessed_articles = total_articles - processed_articles
        
        # Articles with confirmed tickers
        articles_with_tickers = conn.execute("""
            SELECT COUNT(DISTINCT a.id) 
            FROM articles a 
            INNER JOIN news_tickers nt ON nt.news_id = a.id AND nt.confirmed = 1
        """).fetchone()[0]
        
        return {
            'total': total_articles,
            'processed': processed_articles,
            'unprocessed': unprocessed_articles,
            'with_tickers': articles_with_tickers
        }
```

### Автоматическое ограничение размера батча

```python
batch_size = st.number_input(
    "Batch Size",
    min_value=1,
    max_value=10000,
    value=min(session_state.config.batch_size, stats['unprocessed'] if mode == BatchMode.ONLY_UNPROCESSED else stats['total']),
    help="Number of news items to process in this batch",
    key="batch_size_input"
)
```

### Прогресс-бар

```python
if stats['unprocessed'] > 0:
    progress_ratio = stats['processed'] / stats['total'] if stats['total'] > 0 else 0
    st.progress(progress_ratio, text=f"Overall progress: {stats['processed']}/{stats['total']} articles processed ({progress_ratio:.1%})")
```

## Преимущества

1. **Прозрачность** - пользователь видит, сколько статей будет обработано
2. **Контроль** - можно отслеживать прогресс обработки
3. **Эффективность** - автоматическое ограничение размера батча
4. **Мониторинг** - обновленная статистика после обработки
5. **Удобство** - кнопка обновления статистики

## Использование

1. Откройте страницу "🔍 News Pipeline"
2. Перейдите на вкладку "🚀 Batch Processing"
3. Просмотрите статистику новостей
4. Выберите режим обработки (с учетом количества статей)
5. Настройте размер батча
6. Запустите обработку
7. Просмотрите обновленную статистику после завершения

Теперь пользователь всегда знает, сколько необработанных новостей осталось и сколько будет обработано в текущем батче!
