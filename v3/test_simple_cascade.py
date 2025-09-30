#!/usr/bin/env python3
"""
Простой тест для проверки базовой функциональности Cascade_Analyzer.
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тестирование импортов."""
    try:
        print("Тестирование импортов...")
        
        # Тестируем базовые импорты
        import pandas as pd
        print("OK pandas импортирован")
        
        import numpy as np
        print("OK numpy импортирован")
        
        import asyncio
        print("OK asyncio импортирован")
        
        # Тестируем импорт из core
        from core.cascade_analyzer import CascadeAnalyzer, CascadeSignalResult
        print("OK CascadeAnalyzer импортирован")
        
        from core.multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
        print("OK EnhancedMultiTimeframeStockAnalyzer импортирован")
        
        from core.ml import create_fallback_ml_manager
        print("OK ML manager импортирован")
        
        print("OK Все импорты успешны!")
        return True
        
    except Exception as e:
        print(f"ERROR Ошибка импорта: {e}")
        return False

def test_basic_functionality():
    """Тестирование базовой функциональности."""
    try:
        print("\nТестирование базовой функциональности...")
        
        # Создаем простой тестовый объект
        from core.cascade_analyzer import CascadeSignalResult
        
        result = CascadeSignalResult()
        result.symbol = "SBER"
        result.final_signal = "BUY"
        result.confidence = 0.75
        result.entry_price = 250.0
        result.stop_loss = 240.0
        result.take_profit = 270.0
        result.risk_reward = 2.0
        
        # Тестируем методы
        result_dict = result.to_dict()
        print(f"OK CascadeSignalResult создан: {result_dict}")
        
        # Тестируем валидацию
        is_valid = result.final_signal is not None
        print(f"OK Валидация результата: {is_valid}")
        
        print("OK Базовая функциональность работает!")
        return True
        
    except Exception as e:
        print(f"ERROR Ошибка функциональности: {e}")
        return False

def test_database_connection():
    """Тестирование подключения к базе данных."""
    try:
        print("\nТестирование подключения к базе данных...")
        
        from core.database import get_connection
        
        conn = get_connection()
        if conn:
            print("OK Подключение к базе данных успешно")
            
            # Проверяем наличие таблиц
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"OK Найдено таблиц: {len(tables)}")
            print(f"   Таблицы: {', '.join(tables[:10])}{'...' if len(tables) > 10 else ''}")
            
            # Проверяем наличие данных
            if 'daily_data' in tables:
                cursor.execute("SELECT COUNT(*) FROM daily_data")
                count = cursor.fetchone()[0]
                print(f"OK Записей в daily_data: {count}")
            
            conn.close()
            return True
        else:
            print("ERROR Не удалось подключиться к базе данных")
            return False
            
    except Exception as e:
        print(f"ERROR Ошибка подключения к БД: {e}")
        return False

def main():
    """Основная функция тестирования."""
    print("Запуск простого теста Cascade Analyzer")
    print("=" * 50)
    
    tests = [
        ("Импорты", test_imports),
        ("Базовая функциональность", test_basic_functionality),
        ("Подключение к БД", test_database_connection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nТест: {test_name}")
        print("-" * 30)
        
        if test_func():
            passed += 1
            print(f"OK {test_name} - ПРОЙДЕН")
        else:
            print(f"ERROR {test_name} - ПРОВАЛЕН")
    
    print("\n" + "=" * 50)
    print(f"Результаты тестирования: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("Все тесты пройдены успешно!")
        return True
    else:
        print("Некоторые тесты провалены")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
