#!/usr/bin/env python3
"""
Тест интеграции News Pipeline
Проверяет работу интеграции пайплайна новостей с основной системой
"""

import sqlite3
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from core.database import get_database_path
from core.news import fetch_recent_articles, build_summary, _supports_news_pipeline
from core.news_pipeline.repository import NewsPipelineRepository


def test_database_connection():
    """Тест подключения к базе данных."""
    print("🔌 Тестирование подключения к базе данных...")
    
    try:
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


def test_news_pipeline_support():
    """Тест поддержки пайплайна новостей."""
    print("\n🔍 Тестирование поддержки пайплайна новостей...")
    
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        has_support = _supports_news_pipeline(conn)
        conn.close()
        
        if has_support:
            print("✅ Пайплайн новостей поддерживается")
            return True
        else:
            print("⚠️  Пайплайн новостей не поддерживается")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки поддержки пайплайна: {e}")
        return False


def test_fetch_recent_articles():
    """Тест функции fetch_recent_articles."""
    print("\n📰 Тестирование функции fetch_recent_articles...")
    
    try:
        articles = fetch_recent_articles(limit=5)
        
        if articles:
            print(f"✅ Загружено {len(articles)} статей")
            
            # Показываем пример статьи
            sample = articles[0]
            print(f"   Пример статьи:")
            print(f"   - Заголовок: {sample['title'][:50]}...")
            print(f"   - Тикеры: {sample.get('tickers', [])}")
            print(f"   - Источник: {sample.get('source', 'Unknown')}")
            
            return True
        else:
            print("⚠️  Статьи не найдены")
            return False
    except Exception as e:
        print(f"❌ Ошибка загрузки статей: {e}")
        return False


def test_build_summary():
    """Тест функции build_summary."""
    print("\n📊 Тестирование функции build_summary...")
    
    try:
        from datetime import datetime
        today = datetime.now()
        summary = build_summary(today)
        
        if summary:
            print("✅ Сводка построена успешно")
            print(f"   - Дата: {summary['date']}")
            print(f"   - Статей: {summary['articles_count']}")
            print(f"   - Тикеров: {summary['tickers_count']}")
            print(f"   - Тикеры: {summary['tickers']}")
            print(f"   - Источник: {summary['source']}")
            return True
        else:
            print("⚠️  Сводка пустая")
            return False
    except Exception as e:
        print(f"❌ Ошибка построения сводки: {e}")
        return False


def test_database_tables():
    """Тест существования таблиц базы данных."""
    print("\n🗄️  Тестирование таблиц базы данных...")
    
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        required_tables = ['articles', 'sources', 'tickers', 'news_tickers']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if not missing_tables:
            print("✅ Все необходимые таблицы существуют")
            print(f"   Таблицы: {', '.join(tables)}")
            return True
        else:
            print(f"⚠️  Отсутствуют таблицы: {', '.join(missing_tables)}")
            print(f"   Существующие таблицы: {', '.join(tables)}")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки таблиц: {e}")
        return False


def test_news_tickers_data():
    """Тест данных в таблице news_tickers."""
    print("\n🔗 Тестирование данных в news_tickers...")
    
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        
        # Проверяем существование таблицы
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news_tickers'")
        if not cursor.fetchone():
            print("⚠️  Таблица news_tickers не существует")
            conn.close()
            return False
        
        # Проверяем данные
        cursor = conn.execute("SELECT COUNT(*) FROM news_tickers")
        total_count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = 1")
        confirmed_count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = 0")
        pending_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ Данные в news_tickers:")
        print(f"   - Всего записей: {total_count}")
        print(f"   - Подтвержденных: {confirmed_count}")
        print(f"   - Ожидающих: {pending_count}")
        
        return total_count > 0
    except Exception as e:
        print(f"❌ Ошибка проверки данных news_tickers: {e}")
        return False


def test_repository_operations():
    """Тест операций репозитория."""
    print("\n🏪 Тестирование операций репозитория...")
    
    try:
        repository = NewsPipelineRepository()
        
        # Тест подключения
        with repository.connect() as conn:
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
        
        if result:
            print("✅ Подключение к репозиторию успешно")
            
            # Тест получения кандидатов
            candidates = repository.fetch_pending_candidates(limit=5)
            print(f"✅ Получено {len(candidates)} кандидатов")
            
            return True
        else:
            print("❌ Ошибка подключения к репозиторию")
            return False
    except Exception as e:
        print(f"❌ Ошибка операций репозитория: {e}")
        return False


def main():
    """Основная функция тестирования."""
    print("🧪 Тест интеграции News Pipeline")
    print("=" * 50)
    
    tests = [
        ("Подключение к БД", test_database_connection),
        ("Таблицы БД", test_database_tables),
        ("Поддержка пайплайна", test_news_pipeline_support),
        ("Данные news_tickers", test_news_tickers_data),
        ("Операции репозитория", test_repository_operations),
        ("Загрузка статей", test_fetch_recent_articles),
        ("Построение сводки", test_build_summary),
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"Результаты: {success_count}/{total_count} тестов пройдено")
    
    if success_count == total_count:
        print("🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} тестов не пройдено")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
