# Исправление проблемы с асинхронностью в Streamlit

## Проблема

При попытке использовать `await` в Streamlit возникает ошибка:
```
SyntaxError: 'await' outside function
```

Это происходит потому, что Streamlit не поддерживает асинхронные функции в основном потоке выполнения.

## Решение

### Вариант 1: Использование asyncio.run_until_complete()

```python
import asyncio

# Создаем новый event loop для операции
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

try:
    # Выполняем асинхронную функцию
    result = loop.run_until_complete(async_function())
finally:
    loop.close()
```

### Вариант 2: Синхронная версия (рекомендуется)

Создать синхронную версию функций для использования в Streamlit:

```python
class SimpleAnalyzer:
    def analyze_symbols_sync(self, symbols):
        """Синхронная версия анализа."""
        results = []
        for symbol in symbols:
            # Синхронная логика анализа
            result = self._analyze_single_symbol(symbol)
            results.append(result)
        return results
    
    def _analyze_single_symbol(self, symbol):
        """Анализ одного символа."""
        # Здесь может быть вызов ML моделей или API
        return {
            'symbol': symbol,
            'signal': 'BUY',
            'confidence': 0.75
        }
```

## Реализованные исправления

### 1. Enhanced версия с asyncio.run_until_complete()

В файле `pages/21_Cascade_Analyzer_Enhanced.py`:

```python
# Запускаем предварительную фильтрацию синхронно
import asyncio

# Создаем новый event loop для этой операции
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

try:
    stage1d_results = loop.run_until_complete(
        enhanced_analyzer.prefilter_symbols_stage1d(all_symbols)
    )
    st.session_state.stage1d_results = stage1d_results
finally:
    loop.close()
```

### 2. Simple версия (полностью синхронная)

В файле `pages/21_Cascade_Analyzer_Simple.py`:

```python
class SimpleEnhancedCascadeAnalyzer:
    def prefilter_symbols_stage1d(self, symbols: List[str]):
        """Предварительная фильтрация (синхронная версия)."""
        results = {}
        
        for symbol in symbols:
            # Синхронная логика анализа
            if symbol in ['SBER', 'GAZP', 'LKOH']:
                signal = 'BUY'
                confidence = 0.75
            else:
                signal = 'HOLD'
                confidence = 0.45
            
            result = SimpleStage1dResult(symbol, signal, confidence)
            results[symbol] = result
        
        return results
```

## Рекомендации

### Для Streamlit приложений:

1. **Используйте синхронные версии** функций, когда это возможно
2. **Если нужна асинхронность**, используйте `asyncio.run_until_complete()`
3. **Кэшируйте результаты** с помощью `@st.cache_resource` или `@st.cache_data`
4. **Показывайте прогресс** с помощью `st.progress()` и `st.spinner()`

### Для интеграции с существующими асинхронными системами:

```python
# Адаптер для асинхронных функций
def sync_wrapper(async_func, *args, **kwargs):
    """Обертка для выполнения асинхронных функций в Streamlit."""
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(async_func(*args, **kwargs))
    finally:
        loop.close()

# Использование
@st.cache_resource
def get_analyzer():
    return sync_wrapper(create_async_analyzer)
```

## Тестирование

### Простая версия (рекомендуется для демонстрации):
```bash
streamlit run pages/21_Cascade_Analyzer_Simple.py --server.port 8503
```

### Enhanced версия (с asyncio):
```bash
streamlit run pages/21_Cascade_Analyzer_Enhanced.py --server.port 8504
```

## Заключение

Проблема с асинхронностью в Streamlit решена двумя способами:

1. **Enhanced версия**: Использует `asyncio.run_until_complete()` для интеграции с существующими асинхронными функциями
2. **Simple версия**: Полностью синхронная реализация, более подходящая для демонстрации и простых случаев

Рекомендуется использовать Simple версию для демонстрации концепции и Enhanced версию для интеграции с реальными ML системами.




