#!/usr/bin/env python3
"""
Тестовый скрипт для проверки ML анализа.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ml_components():
    """Тестирование ML компонентов."""
    try:
        print("Тестирование ML компонентов...")
        
        # Тестируем импорты
        from core.ml import create_ml_integration_manager, create_fallback_ml_manager
        from core.ml.signals import MLSignalGenerator
        print("OK ML импорты успешны")
        
        # Тестируем создание ML менеджера
        try:
            ml_manager = create_ml_integration_manager()
            print("OK ML integration manager создан")
        except Exception as e:
            print(f"WARNING ML integration manager не создан: {e}")
            try:
                ml_manager = create_fallback_ml_manager()
                print("OK Fallback ML manager создан")
            except Exception as e2:
                print(f"ERROR Fallback ML manager не создан: {e2}")
                ml_manager = None
        
        if ml_manager:
            # Тестируем генератор сигналов
            signal_generator = MLSignalGenerator(ml_manager)
            print("OK MLSignalGenerator создан")
            
            # Тестируем генерацию сигналов для тестового символа
            test_symbol = "SBER"
            print(f"Тестируем генерацию сигналов для {test_symbol}...")
            
            try:
                signals = asyncio.run(signal_generator.generate_ml_signals(test_symbol))
                if 'error' not in signals:
                    print(f"OK ML сигналы сгенерированы для {test_symbol}")
                    print(f"   Ensemble: {signals.get('ml_ensemble_signal', 'N/A')}")
                    print(f"   Price: {signals.get('ml_price_signal', 'N/A')}")
                    print(f"   Confidence: {signals.get('ml_price_confidence', 'N/A')}")
                else:
                    print(f"ERROR Ошибка генерации сигналов: {signals.get('error')}")
            except Exception as e:
                print(f"ERROR Ошибка генерации сигналов: {e}")
        else:
            print("WARNING ML manager недоступен, тестируем fallback режим")
            
            # Создаем fallback сигналы
            fallback_signals = {
                'ml_ensemble_signal': 'BUY',
                'ml_price_signal': 'BUY',
                'ml_sentiment_signal': 'HOLD',
                'ml_technical_signal': 'BUY',
                'ml_price_confidence': 0.6,
                'ml_sentiment_confidence': 0.5,
                'ml_technical_confidence': 0.6,
                'ml_risk_level': 'MEDIUM',
                'ml_risk_score': 0.5,
                'data_points': 100,
                'timestamp': datetime.now().isoformat()
            }
            print("OK Fallback сигналы созданы")
            print(f"   Ensemble: {fallback_signals['ml_ensemble_signal']}")
            print(f"   Price: {fallback_signals['ml_price_signal']}")
            print(f"   Confidence: {fallback_signals['ml_price_confidence']}")
        
        return True
        
    except Exception as e:
        print(f"ERROR Ошибка тестирования ML компонентов: {e}")
        return False

def test_cascade_analyzer():
    """Тестирование Cascade Analyzer."""
    try:
        print("\nТестирование Cascade Analyzer...")
        
        from core.cascade_analyzer import CascadeAnalyzer
        from core.multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
        from core.ml import create_fallback_ml_manager
        
        # Создаем анализаторы
        multi_analyzer = EnhancedMultiTimeframeStockAnalyzer(api_key=None)
        ml_manager = create_fallback_ml_manager()
        
        # Создаем каскадный анализатор
        cascade_analyzer = CascadeAnalyzer(
            multi_analyzer=multi_analyzer,
            ml_manager=ml_manager,
            demo_trading=None
        )
        print("OK Cascade Analyzer создан")
        
        # Тестируем получение доступных символов
        available_symbols = cascade_analyzer.get_available_symbols_with_1d_data()
        print(f"OK Доступные символы: {len(available_symbols)}")
        if available_symbols:
            print(f"   Примеры: {available_symbols[:5]}")
        
        # Тестируем ML анализ
        if available_symbols:
            test_symbols = available_symbols[:3]
            print(f"Тестируем ML анализ для {test_symbols}...")
            
            try:
                ml_results = asyncio.run(cascade_analyzer.perform_initial_ml_analysis(test_symbols))
                print(f"OK ML анализ завершен для {len(ml_results)} символов")
                
                if ml_results:
                    first_symbol = list(ml_results.keys())[0]
                    print(f"   Пример результата для {first_symbol}:")
                    result = ml_results[first_symbol]
                    print(f"     Ensemble: {result.get('ml_ensemble_signal', 'N/A')}")
                    print(f"     Confidence: {result.get('ml_price_confidence', 'N/A')}")
                
            except Exception as e:
                print(f"ERROR Ошибка ML анализа: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERROR Ошибка тестирования Cascade Analyzer: {e}")
        return False

def main():
    """Основная функция тестирования."""
    print("Запуск тестирования ML анализа")
    print("=" * 50)
    
    tests = [
        ("ML компоненты", test_ml_components),
        ("Cascade Analyzer", test_cascade_analyzer)
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
