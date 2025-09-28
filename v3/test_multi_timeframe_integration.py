#!/usr/bin/env python3
"""
Тест интеграции многоуровневых данных.
Проверяет работу MultiTimeframeStockAnalyzer, DataUpdater и ML интеграции.
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_multi_timeframe_analyzer():
    """Тестирует MultiTimeframeStockAnalyzer."""
    logger.info("🧪 Тестирование MultiTimeframeStockAnalyzer...")
    
    try:
        from core.multi_timeframe_analyzer import MultiTimeframeStockAnalyzer
        
        # Создаем анализатор (без API ключа для теста)
        analyzer = MultiTimeframeStockAnalyzer()
        
        # Проверяем доступные таймфреймы
        timeframes = analyzer.get_available_timeframes()
        logger.info(f"✅ Доступные таймфреймы: {timeframes}")
        
        # Проверяем поддержку таймфреймов
        for tf in ['1d', '1h', '1m', '5m', '15m']:
            supported = analyzer.is_timeframe_supported(tf)
            logger.info(f"  {tf}: {'✅' if supported else '❌'}")
        
        # Проверяем маппинг FIGI (должен быть пустой без API ключа)
        figi_mapping = analyzer.get_figi_mapping()
        logger.info(f"✅ FIGI маппинг: {len(figi_mapping)} записей")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования MultiTimeframeStockAnalyzer: {e}")
        return False

def test_data_updater():
    """Тестирует DataUpdater."""
    logger.info("🧪 Тестирование DataUpdater...")
    
    try:
        from core.multi_timeframe_analyzer import DataUpdater
        
        # Создаем обновлятор (без API ключа для теста)
        updater = DataUpdater()
        
        # Проверяем статус
        logger.info(f"✅ Статус обновлятора: {'Активен' if updater.is_running else 'Неактивен'}")
        
        # Проверяем расписание
        logger.info("✅ Расписание обновления:")
        for tf, schedule in updater.update_schedules.items():
            logger.info(f"  {tf}: {schedule}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования DataUpdater: {e}")
        return False

def test_websocket_provider():
    """Тестирует WebSocketDataProvider."""
    logger.info("🧪 Тестирование WebSocketDataProvider...")
    
    try:
        from core.multi_timeframe_analyzer import WebSocketDataProvider
        
        # Создаем провайдер (без API ключа для теста)
        provider = WebSocketDataProvider("")
        
        # Проверяем URL
        logger.info(f"✅ WebSocket URL: {provider.ws_url}")
        
        # Проверяем статус подключения
        logger.info(f"✅ Статус подключения: {'Подключен' if provider.is_connected else 'Не подключен'}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования WebSocketDataProvider: {e}")
        return False

def test_real_time_manager():
    """Тестирует RealTimeDataManager."""
    logger.info("🧪 Тестирование RealTimeDataManager...")
    
    try:
        from core.multi_timeframe_analyzer import RealTimeDataManager
        
        # Создаем менеджер (без API ключа для теста)
        manager = RealTimeDataManager("")
        
        # Проверяем компоненты
        logger.info("✅ Компоненты RealTimeDataManager:")
        logger.info(f"  MultiTimeframeStockAnalyzer: {'✅' if manager.multi_analyzer else '❌'}")
        logger.info(f"  WebSocketDataProvider: {'✅' if manager.ws_provider else '❌'}")
        
        # Проверяем кэш
        logger.info(f"✅ Размер кэша данных: {len(manager.data_cache)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования RealTimeDataManager: {e}")
        return False

def test_ml_integration():
    """Тестирует интеграцию с ML."""
    logger.info("🧪 Тестирование ML интеграции...")
    
    try:
        from core.ml.model_manager import MLModelManager
        from core.ml.storage import ml_storage
        
        # Создаем ML менеджер
        ml_manager = MLModelManager()
        
        # Проверяем конфигурации таймфреймов
        logger.info("✅ Конфигурации таймфреймов ML:")
        for tf, config in ml_manager.timeframe_configs.items():
            logger.info(f"  {tf}: sequence_length={config['sequence_length']}, hidden_size={config['hidden_size']}")
        
        # Проверяем storage
        logger.info(f"✅ ML Storage: models_dir={ml_storage.models_dir}")
        
        # Проверяем доступные тикеры
        try:
            tickers = ml_manager.get_available_tickers()
            logger.info(f"✅ Доступные тикеры: {len(tickers)}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить тикеры: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования ML интеграции: {e}")
        return False

def test_database_tables():
    """Тестирует таблицы базы данных."""
    logger.info("🧪 Тестирование таблиц базы данных...")
    
    try:
        from core.database import get_connection, create_tables
        
        # Подключаемся к БД
        conn = get_connection()
        
        # Создаем таблицы
        create_tables(conn)
        
        # Проверяем таблицы для таймфреймов
        cursor = conn.cursor()
        
        # Проверяем существование таблиц
        expected_tables = [
            'data_1hour', 'data_1min', 'data_5min', 'data_15min',
            'ml_models', 'ml_predictions_cache', 'ml_performance_metrics'
        ]
        
        for table in expected_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            exists = cursor.fetchone() is not None
            logger.info(f"  {table}: {'✅' if exists else '❌'}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования таблиц БД: {e}")
        return False

def main():
    """Основная функция тестирования."""
    logger.info("🚀 Запуск тестирования интеграции многоуровневых данных...")
    
    tests = [
        ("MultiTimeframeStockAnalyzer", test_multi_timeframe_analyzer),
        ("DataUpdater", test_data_updater),
        ("WebSocketDataProvider", test_websocket_provider),
        ("RealTimeDataManager", test_real_time_manager),
        ("ML Integration", test_ml_integration),
        ("Database Tables", test_database_tables),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 Тест: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в тесте {test_name}: {e}")
            results[test_name] = False
    
    # Итоговый отчет
    logger.info(f"\n{'='*50}")
    logger.info("📊 ИТОГОВЫЙ ОТЧЕТ")
    logger.info(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n📈 Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        logger.info("🎉 Все тесты пройдены успешно!")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} тестов провалено")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
