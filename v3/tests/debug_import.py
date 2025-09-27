#!/usr/bin/env python3
"""
Отладка импорта StreamlitProgressReporter
"""

print("=== Отладка импорта StreamlitProgressReporter ===")
print()

# Тест 1: Импорт модуля progress
print("1. Тестирование импорта модуля progress...")
try:
    from core.news_pipeline.progress import StreamlitProgressReporter
    print("✅ StreamlitProgressReporter импортирован из progress.py")
except ImportError as e:
    print(f"❌ Ошибка импорта из progress.py: {e}")
    import traceback
    traceback.print_exc()
print()

# Тест 2: Импорт из __init__.py
print("2. Тестирование импорта из __init__.py...")
try:
    from core.news_pipeline import StreamlitProgressReporter
    print("✅ StreamlitProgressReporter импортирован из __init__.py")
except ImportError as e:
    print(f"❌ Ошибка импорта из __init__.py: {e}")
    import traceback
    traceback.print_exc()
print()

# Тест 3: Проверка атрибутов класса
print("3. Проверка атрибутов класса...")
try:
    from core.news_pipeline.progress import StreamlitProgressReporter
    
    # Проверяем, что класс существует
    print(f"✅ Класс StreamlitProgressReporter найден: {StreamlitProgressReporter}")
    
    # Проверяем методы класса
    methods = [method for method in dir(StreamlitProgressReporter) if not method.startswith('_')]
    print(f"✅ Методы класса: {methods}")
    
    # Проверяем, что класс можно инстанцировать
    try:
        instance = StreamlitProgressReporter(None, None)
        print("✅ Экземпляр класса создан успешно")
    except Exception as e:
        print(f"⚠️  Не удалось создать экземпляр: {e}")
        
except Exception as e:
    print(f"❌ Ошибка при проверке класса: {e}")
    import traceback
    traceback.print_exc()
print()

# Тест 4: Проверка наследования
print("4. Проверка наследования...")
try:
    from core.news_pipeline.progress import StreamlitProgressReporter, ProgressReporter
    
    # Проверяем наследование
    if issubclass(StreamlitProgressReporter, ProgressReporter):
        print("✅ StreamlitProgressReporter наследуется от ProgressReporter")
    else:
        print("❌ StreamlitProgressReporter НЕ наследуется от ProgressReporter")
        
    # Проверяем MRO
    mro = StreamlitProgressReporter.__mro__
    print(f"✅ MRO: {[cls.__name__ for cls in mro]}")
    
except Exception as e:
    print(f"❌ Ошибка при проверке наследования: {e}")
    import traceback
    traceback.print_exc()
print()

# Тест 5: Проверка импорта всех необходимых модулей
print("5. Проверка импорта всех необходимых модулей...")
modules_to_test = [
    ("core.news_pipeline", "Основной модуль пайплайна"),
    ("core.news_pipeline.progress", "Модуль прогресса"),
    ("core.news_pipeline.models", "Модели данных"),
    ("core.news_pipeline.repository", "Репозиторий"),
    ("core.news_pipeline.processor", "Процессор"),
    ("core.news_pipeline.config", "Конфигурация"),
]

for module_name, description in modules_to_test:
    try:
        __import__(module_name)
        print(f"✅ {module_name} - {description}")
    except ImportError as e:
        print(f"❌ {module_name} - {description}")
        print(f"   Ошибка: {e}")
    except Exception as e:
        print(f"⚠️  {module_name} - {description}")
        print(f"   Неожиданная ошибка: {e}")

print()
print("=== Отладка завершена ===")
