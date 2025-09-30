#!/usr/bin/env python3
"""
Demo script для демонстрации работы улучшенного каскадного анализатора.
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def demo_enhanced_cascade():
    """Демонстрация работы улучшенного каскадного анализатора."""
    
    print("Демонстрация улучшенного каскадного анализатора")
    print("=" * 60)
    
    try:
        # Импортируем необходимые модули
        from core.cascade_analyzer_enhanced import EnhancedCascadeAnalyzer
        from core.cascade_analyzer import CascadeAnalyzer
        from core.multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
        
        print("Модули успешно импортированы")
        
        # Создаем базовый анализатор (без API ключа для демо)
        multi_analyzer = EnhancedMultiTimeframeStockAnalyzer(api_key=None)
        cascade_analyzer = CascadeAnalyzer(
            multi_analyzer=multi_analyzer,
            ml_manager=None,
            demo_trading=None
        )
        
        # Создаем улучшенный анализатор
        enhanced_analyzer = EnhancedCascadeAnalyzer(cascade_analyzer)
        
        print("Анализаторы успешно созданы")
        
        # Тестовые символы
        test_symbols = ['SBER', 'GAZP', 'LKOH', 'NVTK', 'ROSN', 'MGNT', 'YNDX', 'VKCO']
        
        print(f"\nТестируем предварительную фильтрацию для {len(test_symbols)} символов:")
        print("Символы:", ", ".join(test_symbols))
        
        # Запускаем предварительную фильтрацию
        print("\nВыполняется предварительная фильтрация по этапу 1d...")
        
        stage1d_results = await enhanced_analyzer.prefilter_symbols_stage1d(test_symbols)
        
        print(f"Фильтрация завершена! Обработано {len(stage1d_results)} символов")
        
        # Анализируем результаты
        passed_symbols = enhanced_analyzer.get_passed_symbols(stage1d_results)
        buy_candidates = enhanced_analyzer.get_buy_candidates(stage1d_results)
        sell_candidates = enhanced_analyzer.get_sell_candidates(stage1d_results)
        top_candidates = enhanced_analyzer.get_top_candidates(stage1d_results, limit=5)
        
        print("\nРезультаты предварительной фильтрации:")
        print(f"  - Всего проверено: {len(stage1d_results)}")
        print(f"  - Прошли этап 1d: {len(passed_symbols)}")
        print(f"  - Кандидаты BUY: {len(buy_candidates)}")
        print(f"  - Кандидаты SELL: {len(sell_candidates)}")
        
        # Показываем детальные результаты
        print("\nДетальные результаты:")
        for symbol, result in stage1d_results.items():
            status = "ПРОШЕЛ" if result.signal in ['BUY', 'SELL'] else "ОТКЛОНЕН"
            print(f"  {symbol}: {result.signal} | Уверенность: {result.confidence:.1%} | {status}")
        
        # Показываем топ кандидатов
        if top_candidates:
            print(f"\nТоп-{len(top_candidates)} кандидатов:")
            for i, result in enumerate(top_candidates, 1):
                print(f"  {i}. {result.symbol}: {result.signal} | Уверенность: {result.confidence:.1%}")
        
        # Статистика кэша
        cache_stats = enhanced_analyzer.get_cache_stats()
        print(f"\nСтатистика кэша:")
        print(f"  - Всего в кэше: {cache_stats['total_cached']}")
        print(f"  - Прошли этап 1d: {cache_stats['passed_stage1d']}")
        print(f"  - BUY сигналы: {cache_stats['buy_signals']}")
        print(f"  - SELL сигналы: {cache_stats['sell_signals']}")
        print(f"  - Процент прохождения: {cache_stats['cache_hit_rate']}")
        
        # Демонстрация работы с предварительно отфильтрованными символами
        if passed_symbols:
            print(f"\nДемонстрация анализа предварительно отфильтрованных символов:")
            print(f"Анализируем {len(passed_symbols[:3])} символов из прошедших этап 1d...")
            
            # Берем только первые 3 символа для демо
            demo_symbols = passed_symbols[:3]
            
            # Запускаем анализ (это будет быстрее, так как этап 1d уже пройден)
            results = await enhanced_analyzer.analyze_prefiltered_symbols(demo_symbols)
            
            print(f"Анализ завершен! Обработано {len(results)} символов")
            
            # Показываем результаты
            successful_results = [r for r in results if r.final_signal is not None]
            if successful_results:
                print(f"\nУспешные сигналы ({len(successful_results)}):")
                for result in successful_results:
                    print(f"  - {result.symbol}: {result.final_signal} | Уверенность: {result.confidence:.1%}")
                    print(f"    Цена входа: {result.entry_price:.2f} RUB | R/R: {result.risk_reward:.1f}")
            else:
                print("Нет успешных сигналов после полного каскадного анализа")
        
        print("\nДемонстрация завершена успешно!")
        
    except Exception as e:
        print(f"Ошибка демонстрации: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_enhanced_cascade())
