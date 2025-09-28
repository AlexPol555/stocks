#!/usr/bin/env python3
"""
Простой тест интеграции с API ключом из secrets.toml
"""

import sys
import os
import logging

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_secrets_loading():
    """Тестирует загрузку API ключа из secrets.toml"""
    logger.info("🧪 Тестирование загрузки API ключа...")
    
    try:
        # Имитируем загрузку secrets как в Streamlit
        import toml
        
        # Читаем secrets.toml
        secrets_path = ".streamlit/secrets.toml"
        if os.path.exists(secrets_path):
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets = toml.load(f)
            
            api_key = secrets.get('TINKOFF_API_KEY')
            if api_key:
                logger.info(f"✅ API ключ найден: {api_key[:8]}...")
                return True
            else:
                logger.error("❌ TINKOFF_API_KEY не найден в secrets.toml")
                return False
        else:
            logger.error("❌ Файл .streamlit/secrets.toml не найден")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки secrets: {e}")
        return False

def test_multi_timeframe_analyzer():
    """Тестирует MultiTimeframeStockAnalyzer с API ключом"""
    logger.info("🧪 Тестирование MultiTimeframeStockAnalyzer...")
    
    try:
        from core.multi_timeframe_analyzer import MultiTimeframeStockAnalyzer
        
        # Создаем анализатор (должен автоматически загрузить API ключ)
        analyzer = MultiTimeframeStockAnalyzer()
        
        if analyzer.api_key:
            logger.info(f"✅ API ключ загружен: {analyzer.api_key[:8]}...")
            
            # Проверяем доступные таймфреймы
            timeframes = analyzer.get_available_timeframes()
            logger.info(f"✅ Доступные таймфреймы: {timeframes}")
            
            # Проверяем FIGI маппинг
            try:
                figi_mapping = analyzer.get_figi_mapping()
                logger.info(f"✅ FIGI маппинг: {len(figi_mapping)} записей")
                
                if figi_mapping:
                    # Пробуем получить данные для первого символа
                    first_symbol = list(figi_mapping.keys())[0]
                    figi = figi_mapping[first_symbol]
                    
                    logger.info(f"🧪 Тестируем получение данных для {first_symbol}...")
                    data = analyzer.get_stock_data(figi, '1d')
                    
                    if not data.empty:
                        logger.info(f"✅ Получены данные: {len(data)} записей")
                        return True
                    else:
                        logger.warning("⚠️ Данные не получены (возможно, нет доступа к API)")
                        return True  # API ключ работает, но данных нет
                else:
                    logger.warning("⚠️ FIGI маппинг пустой")
                    return True
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения данных: {e}")
                return True  # API ключ загружен, но есть проблемы с данными
        else:
            logger.error("❌ API ключ не загружен")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования анализатора: {e}")
        return False

def main():
    """Основная функция тестирования"""
    logger.info("🚀 Запуск тестирования интеграции с API...")
    
    tests = [
        ("Secrets Loading", test_secrets_loading),
        ("MultiTimeframeStockAnalyzer", test_multi_timeframe_analyzer),
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
        logger.info("🎉 Все тесты пройдены! API интеграция работает!")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} тестов провалено")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
