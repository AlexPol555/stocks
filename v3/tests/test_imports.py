#!/usr/bin/env python3
"""
Тест импортов News Pipeline
Проверяет, что все модули импортируются без ошибок
"""

import sys
import traceback


def test_import(module_name: str, description: str = "") -> bool:
    """Тестировать импорт модуля."""
    try:
        __import__(module_name)
        print(f"✅ {module_name} - {description}")
        return True
    except ImportError as e:
        print(f"❌ {module_name} - {description}")
        print(f"   Ошибка: {e}")
        return False
    except Exception as e:
        print(f"⚠️  {module_name} - {description}")
        print(f"   Неожиданная ошибка: {e}")
        return False


def main():
    """Основная функция тестирования."""
    print("=== Тест импортов News Pipeline ===")
    print()
    
    # Список модулей для тестирования
    modules = [
        # Основные модули
        ("core", "Основной модуль core"),
        ("core.news_pipeline", "Модуль пайплайна новостей"),
        ("core.news_pipeline.config", "Конфигурация пайплайна"),
        ("core.news_pipeline.models", "Модели данных"),
        ("core.news_pipeline.repository", "Репозиторий"),
        ("core.news_pipeline.processor", "Процессор"),
        ("core.news_pipeline.progress", "Прогресс"),
        ("core.news_pipeline.monitoring", "Мониторинг"),
        ("core.news_pipeline.preprocessing", "Предобработка"),
        ("core.news_pipeline.embeddings", "Эмбеддинги"),
        ("core.news_pipeline.workflows", "Рабочие процессы"),
        
        # Генераторы кандидатов
        ("core.news_pipeline.generators", "Генераторы"),
        ("core.news_pipeline.generators.substring", "Substring генератор"),
        ("core.news_pipeline.generators.fuzzy", "Fuzzy генератор"),
        ("core.news_pipeline.generators.ner", "NER генератор"),
        ("core.news_pipeline.generators.semantic", "Semantic генератор"),
        
        # Другие модули
        ("core.database", "База данных"),
        ("core.news", "Новости"),
        ("core.analytics", "Аналитика"),
        ("core.indicators", "Индикаторы"),
        ("core.orders", "Заказы"),
        ("core.parser", "Парсер"),
        ("core.settings", "Настройки"),
        ("core.utils", "Утилиты"),
        ("core.visualization", "Визуализация"),
    ]
    
    # Тестируем импорты
    success_count = 0
    total_count = len(modules)
    
    for module_name, description in modules:
        if test_import(module_name, description):
            success_count += 1
        print()
    
    # Результаты
    print("=" * 50)
    print(f"Результаты: {success_count}/{total_count} модулей импортированы успешно")
    
    if success_count == total_count:
        print("🎉 Все модули импортированы успешно!")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} модулей не удалось импортировать")
        return 1


if __name__ == "__main__":
    sys.exit(main())
