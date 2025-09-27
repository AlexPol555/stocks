#!/usr/bin/env python3
"""
Простой тест импорта
Проверяет базовые импорты без сложных зависимостей
"""

import sys


def test_basic_imports():
    """Тест базовых импортов."""
    print("🔍 Тестирование базовых импортов...")
    
    try:
        # Стандартные библиотеки
        import sqlite3
        import json
        import logging
        import tempfile
        from pathlib import Path
        from typing import List, Dict, Any, Optional
        print("✅ Стандартные библиотеки импортированы")
        
        # Основные модули проекта
        import core
        print("✅ Модуль core импортирован")
        
        # Модули базы данных
        from core.database import get_database_path
        print("✅ Модуль database импортирован")
        
        # Модули новостей
        from core.news import fetch_recent_articles, build_summary
        print("✅ Модуль news импортирован")
        
        # Модули пайплайна
        from core.news_pipeline import NewsPipelineRepository
        print("✅ Модуль news_pipeline импортирован")
        
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def test_database_connection():
    """Тест подключения к базе данных."""
    print("\n🔌 Тестирование подключения к базе данных...")
    
    try:
        from core.database import get_database_path
        import sqlite3
        
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print("✅ Подключение к базе данных успешно")
            return True
        else:
            print("❌ Ошибка подключения к базе данных")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        return False


def test_news_functions():
    """Тест функций новостей."""
    print("\n📰 Тестирование функций новостей...")
    
    try:
        from core.news import fetch_recent_articles, build_summary
        from datetime import datetime
        
        # Тест fetch_recent_articles
        articles = fetch_recent_articles(limit=1)
        print(f"✅ fetch_recent_articles работает: {len(articles)} статей")
        
        # Тест build_summary
        today = datetime.now()
        summary = build_summary(today)
        print(f"✅ build_summary работает: {summary['date']}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка функций новостей: {e}")
        return False


def test_pipeline_repository():
    """Тест репозитория пайплайна."""
    print("\n🏪 Тестирование репозитория пайплайна...")
    
    try:
        from core.news_pipeline import NewsPipelineRepository
        
        repository = NewsPipelineRepository()
        print("✅ Репозиторий создан")
        
        with repository.connect() as conn:
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
        
        if result:
            print("✅ Подключение к репозиторию успешно")
            return True
        else:
            print("❌ Ошибка подключения к репозиторию")
            return False
    except Exception as e:
        print(f"❌ Ошибка репозитория пайплайна: {e}")
        return False


def main():
    """Основная функция тестирования."""
    print("🧪 Простой тест импорта")
    print("=" * 40)
    
    tests = [
        ("Базовые импорты", test_basic_imports),
        ("Подключение к БД", test_database_connection),
        ("Функции новостей", test_news_functions),
        ("Репозиторий пайплайна", test_pipeline_repository),
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
        return 0
    else:
        print(f"⚠️  {total_count - success_count} тестов не пройдено")
        return 1


if __name__ == "__main__":
    sys.exit(main())
