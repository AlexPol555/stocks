"""Тест импортов планировщика."""

def test_scheduler_imports():
    """Тест импорта всех компонентов планировщика."""
    try:
        # Тест основных импортов
        from core.scheduler import TaskScheduler, TaskStatus, TradingCalendar, Market
        print("✅ Основные классы импортированы успешно")
        
        # Тест интеграции
        from core.scheduler import SchedulerIntegration, RealSchedulerIntegration
        print("✅ Классы интеграции импортированы успешно")
        
        # Тест создания экземпляров
        calendar = TradingCalendar()
        print("✅ TradingCalendar создан успешно")
        
        scheduler = TaskScheduler(calendar)
        print("✅ TaskScheduler создан успешно")
        
        # Тест статусов
        print(f"✅ TaskStatus.PENDING: {TaskStatus.PENDING}")
        print(f"✅ TaskStatus.RUNNING: {TaskStatus.RUNNING}")
        print(f"✅ TaskStatus.COMPLETED: {TaskStatus.COMPLETED}")
        
        # Тест рынков
        print(f"✅ Market.MOEX: {Market.MOEX}")
        print(f"✅ Market.NYSE: {Market.NYSE}")
        print(f"✅ Market.NASDAQ: {Market.NASDAQ}")
        
        print("\n🎉 Все импорты работают корректно!")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_page_imports():
    """Тест импортов для страницы планировщика."""
    try:
        # Имитируем импорты страницы
        import streamlit as st
        from datetime import datetime, timedelta
        from typing import Optional, Dict, Any
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        
        from core.scheduler import TaskScheduler, TaskStatus, TradingCalendar, Market, SchedulerIntegration, RealSchedulerIntegration
        from core import ui
        
        print("✅ Все импорты страницы планировщика работают")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта страницы: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка страницы: {e}")
        return False


if __name__ == "__main__":
    print("Тестирование импортов планировщика...")
    print("=" * 50)
    
    success1 = test_scheduler_imports()
    print("\n" + "=" * 50)
    success2 = test_page_imports()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 Все тесты прошли успешно!")
        print("Планировщик готов к использованию!")
    else:
        print("❌ Некоторые тесты не прошли")
        print("Проверьте ошибки выше")
