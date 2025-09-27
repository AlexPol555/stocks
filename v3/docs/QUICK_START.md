# Быстрый старт News Pipeline

## Проблема с зависимостями

Если вы получили ошибку `ModuleNotFoundError: No module named 'sentence_transformers'`, это означает, что не установлены все зависимости.

## Решение

### Вариант 1: Установка всех зависимостей

```bash
pip install -r requirements.txt
```

### Вариант 2: Минимальная установка

```bash
pip install -r requirements-minimal.txt
```

### Вариант 3: Пошаговая установка

```bash
# Базовые зависимости (обязательные)
pip install streamlit pandas numpy pyyaml

# Опциональные зависимости (для полной функциональности)
pip install sentence-transformers  # для эмбеддингов
pip install rapidfuzz              # для fuzzy matching
pip install pymorphy3              # для русской морфологии
pip install razdel                 # для токенизации
pip install spacy                  # для NER

# spaCy модели
python -m spacy download ru_core_news_sm
python -m spacy download en_core_web_sm
```

### Вариант 4: Автоматическая установка

```bash
# Windows
scripts/install.bat

# Linux/macOS
python install_dependencies.py
```

## Запуск без всех зависимостей

Система теперь поддерживает работу без опциональных зависимостей:

- **Без sentence-transformers**: эмбеддинги отключены
- **Без rapidfuzz**: fuzzy matching отключен
- **Без pymorphy3**: простая токенизация
- **Без spacy**: только pattern matching для NER

### Минимальный запуск

```bash
# Установить только базовые зависимости
pip install streamlit pandas numpy pyyaml

# Запустить интерфейс
streamlit run pages/9_🔍_News_Pipeline.py
```

## Проверка установки

```bash
# Проверить, что базовые зависимости установлены
python -c "import streamlit, pandas, numpy, yaml; print('✅ Базовые зависимости установлены')"

# Проверить опциональные зависимости
python -c "import sentence_transformers; print('✅ sentence-transformers установлен')" 2>/dev/null || echo "❌ sentence-transformers не установлен"
python -c "import rapidfuzz; print('✅ rapidfuzz установлен')" 2>/dev/null || echo "❌ rapidfuzz не установлен"
python -c "import pymorphy3; print('✅ pymorphy3 установлен')" 2>/dev/null || echo "❌ pymorphy3 не установлен"
```

## Функциональность по уровням

### Уровень 1: Базовый (только streamlit, pandas, numpy, pyyaml)
- ✅ Substring matching
- ✅ Базовая токенизация
- ✅ Интерфейс валидации
- ❌ Fuzzy matching
- ❌ Эмбеддинги
- ❌ Продвинутая морфология
- ❌ NER

### Уровень 2: Расширенный (+ rapidfuzz, pymorphy3, razdel)
- ✅ Substring matching
- ✅ Fuzzy matching
- ✅ Русская морфология
- ✅ Продвинутая токенизация
- ❌ Эмбеддинги
- ❌ NER

### Уровень 3: Полный (+ sentence-transformers, spacy)
- ✅ Все функции
- ✅ Эмбеддинги
- ✅ NER
- ✅ Семантический поиск

## Рекомендации

1. **Для тестирования**: Уровень 1 (базовый)
2. **Для продакшена**: Уровень 3 (полный)
3. **Для разработки**: Уровень 2 (расширенный)

## Troubleshooting

### Ошибка "No module named 'sentence_transformers'"
```bash
pip install sentence-transformers
```

### Ошибка "No module named 'rapidfuzz'"
```bash
pip install rapidfuzz
```

### Ошибка "No module named 'pymorphy3'"
```bash
pip install pymorphy3
```

### Ошибка "No module named 'spacy'"
```bash
pip install spacy
python -m spacy download ru_core_news_sm
```

### Ошибка "Can't find model 'ru_core_news_sm'"
```bash
python -m spacy download ru_core_news_sm
python -m spacy download en_core_web_sm
```

## Демонстрация

После установки зависимостей:

```bash
# Демонстрация в консоли
python tests/demo_news_pipeline.py

# Веб-интерфейс
streamlit run pages/9_🔍_News_Pipeline.py
```

## Поддержка

Если у вас остались проблемы:

1. Проверьте версию Python: `python --version` (требуется 3.8+)
2. Обновите pip: `python -m pip install --upgrade pip`
3. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```
4. Установите зависимости заново
