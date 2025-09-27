#!/usr/bin/env python3
"""
Тест импорта Streamlit
Проверяет импорт Streamlit и связанных модулей
"""

import sys


def test_streamlit_import():
    """Тест импорта Streamlit."""
    print("🔍 Тестирование импорта Streamlit...")
    
    try:
        import streamlit as st
        print(f"✅ Streamlit импортирован: версия {st.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта Streamlit: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def test_streamlit_components():
    """Тест импорта компонентов Streamlit."""
    print("\n🧩 Тестирование компонентов Streamlit...")
    
    try:
        import streamlit as st
        from streamlit import session_state
        print("✅ Основные компоненты Streamlit импортированы")
        
        # Тест создания простого элемента
        # (не запускаем Streamlit, просто проверяем импорт)
        print("✅ Streamlit готов к использованию")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта компонентов Streamlit: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def test_pandas_import():
    """Тест импорта pandas."""
    print("\n🐼 Тестирование импорта pandas...")
    
    try:
        import pandas as pd
        print(f"✅ Pandas импортирован: версия {pd.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта pandas: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def test_numpy_import():
    """Тест импорта numpy."""
    print("\n🔢 Тестирование импорта numpy...")
    
    try:
        import numpy as np
        print(f"✅ NumPy импортирован: версия {np.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта numpy: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def test_yaml_import():
    """Тест импорта yaml."""
    print("\n📄 Тестирование импорта yaml...")
    
    try:
        import yaml
        print("✅ PyYAML импортирован")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта yaml: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def test_optional_imports():
    """Тест опциональных импортов."""
    print("\n🔧 Тестирование опциональных импортов...")
    
    optional_modules = [
        ("sentence_transformers", "Sentence Transformers"),
        ("rapidfuzz", "RapidFuzz"),
        ("pymorphy3", "PyMorphy3"),
        ("razdel", "Razdel"),
        ("spacy", "spaCy"),
        ("faiss", "FAISS"),
    ]
    
    success_count = 0
    total_count = len(optional_modules)
    
    for module_name, description in optional_modules:
        try:
            __import__(module_name)
            print(f"✅ {description} импортирован")
            success_count += 1
        except ImportError:
            print(f"⚠️  {description} не установлен (опционально)")
        except Exception as e:
            print(f"❌ Ошибка импорта {description}: {e}")
    
    print(f"\n📊 Опциональные модули: {success_count}/{total_count} установлены")
    return True


def test_project_imports():
    """Тест импорта модулей проекта."""
    print("\n🏗️  Тестирование импорта модулей проекта...")
    
    try:
        # Основные модули
        import core
        from core.database import get_database_path
        from core.news import fetch_recent_articles, build_summary
        print("✅ Основные модули импортированы")
        
        # Модули пайплайна
        from core.news_pipeline import NewsPipelineRepository
        from core.news_pipeline.models import NewsItem, TickerRecord
        print("✅ Модули пайплайна импортированы")
        
        # Модули страниц
        import pages
        print("✅ Модули страниц импортированы")
        
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта модулей проекта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def test_streamlit_pages():
    """Тест импорта страниц Streamlit."""
    print("\n📄 Тестирование импорта страниц Streamlit...")
    
    try:
        # Импортируем страницы (без запуска)
        import pages
        print("✅ Модуль pages импортирован")
        
        # Проверяем существование файлов страниц
        import os
        pages_dir = "pages"
        if os.path.exists(pages_dir):
            page_files = [f for f in os.listdir(pages_dir) if f.endswith('.py')]
            print(f"✅ Найдено {len(page_files)} страниц Streamlit")
            
            # Показываем список страниц
            for page_file in page_files:
                print(f"   - {page_file}")
        else:
            print("⚠️  Папка pages не найдена")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта страниц: {e}")
        return False


def main():
    """Основная функция тестирования."""
    print("🧪 Тест импорта Streamlit")
    print("=" * 40)
    
    tests = [
        ("Streamlit", test_streamlit_import),
        ("Компоненты Streamlit", test_streamlit_components),
        ("Pandas", test_pandas_import),
        ("NumPy", test_numpy_import),
        ("YAML", test_yaml_import),
        ("Опциональные модули", test_optional_imports),
        ("Модули проекта", test_project_imports),
        ("Страницы Streamlit", test_streamlit_pages),
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            success_count += 1
    
    print("\n" + "=" * 40)
    print(f"Результаты: {success_count}/{total_count} тестов пройдено")
    
    if success_count == total_count:
        print("🎉 Все тесты пройдены успешно!")
        print("✅ Streamlit готов к использованию")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} тестов не пройдено")
        return 1


if __name__ == "__main__":
    sys.exit(main())
