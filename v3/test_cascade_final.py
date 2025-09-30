#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы Cascade_Analyzer_Final.
"""

import asyncio
import logging
from core.cascade_analyzer import CascadeAnalyzer
from core.multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
from core.ml import create_fallback_ml_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cascade_analyzer():
    """Тестирование каскадного анализатора."""
    try:
        print("🚀 Инициализация Cascade Analyzer...")
        
        # Создаем анализаторы
        multi_analyzer = EnhancedMultiTimeframeStockAnalyzer(api_key=None)
        ml_manager = create_fallback_ml_manager()
        
        # Создаем каскадный анализатор
        cascade_analyzer = CascadeAnalyzer(
            multi_analyzer=multi_analyzer,
            ml_manager=ml_manager,
            demo_trading=None
        )
        
        print("✅ Cascade Analyzer инициализирован")
        
        # Получаем доступные символы
        print("📊 Получение доступных символов...")
        available_symbols = cascade_analyzer.get_available_symbols_with_1d_data()
        print(f"✅ Найдено {len(available_symbols)} символов с данными 1d")
        
        if not available_symbols:
            print("⚠️ Нет доступных символов, используем тестовые")
            available_symbols = ['SBER', 'GAZP', 'LKOH', 'NVTK', 'ROSN']
        
        # Выполняем первый ML анализ
        print("🤖 Выполнение первого ML анализа...")
        ml_results = await cascade_analyzer.perform_initial_ml_analysis(available_symbols[:5])
        print(f"✅ ML анализ завершен для {len(ml_results)} символов")
        
        # Показываем результаты ML анализа
        if ml_results:
            print("\n📊 Результаты ML анализа:")
            for symbol, signals in ml_results.items():
                print(f"  {symbol}: {signals.get('ml_ensemble_signal', 'HOLD')} "
                      f"(уверенность: {signals.get('ml_price_confidence', 0):.1%})")
        
        # Выбираем перспективные символы для каскадного анализа
        promising_symbols = []
        for symbol, signals in ml_results.items():
            ensemble_signal = signals.get('ml_ensemble_signal', 'HOLD')
            confidence = signals.get('ml_price_confidence', 0)
            if ensemble_signal in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL'] and confidence >= 0.5:
                promising_symbols.append(symbol)
        
        print(f"\n🎯 Найдено {len(promising_symbols)} перспективных символов: {promising_symbols}")
        
        # Выполняем каскадный анализ для перспективных символов
        if promising_symbols:
            print("\n🔄 Выполнение каскадного анализа...")
            cascade_results = await cascade_analyzer.analyze_multiple_symbols(promising_symbols[:3])
            
            successful_results = cascade_analyzer.get_successful_signals(cascade_results)
            rejected_results = cascade_analyzer.get_rejected_signals(cascade_results)
            
            print(f"✅ Каскадный анализ завершен:")
            print(f"  - Успешных сигналов: {len(successful_results)}")
            print(f"  - Отклоненных сигналов: {len(rejected_results)}")
            
            # Показываем успешные сигналы
            if successful_results:
                print("\n🎯 Успешные каскадные сигналы:")
                for result in successful_results:
                    print(f"  {result.symbol}: {result.final_signal} "
                          f"(уверенность: {result.confidence:.1%}, "
                          f"цена входа: {result.entry_price:.2f} RUB)")
            
            # Показываем отклоненные сигналы
            if rejected_results:
                print("\n❌ Отклоненные сигналы:")
                for result in rejected_results:
                    print(f"  {result.symbol}: отклонен на этапе {result.rejected_at_stage} "
                          f"({result.rejection_reason})")
        else:
            print("⚠️ Нет перспективных символов для каскадного анализа")
        
        print("\n✅ Тестирование завершено успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка тестирования: {e}")
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_cascade_analyzer())




