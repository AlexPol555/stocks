#!/usr/bin/env python3
"""
Простая демонстрация концепции улучшенного каскадного анализатора.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any

class SimpleStage1dResult:
    """Простой результат этапа 1d."""
    
    def __init__(self, symbol: str, signal: str, confidence: float):
        self.symbol = symbol
        self.signal = signal
        self.confidence = confidence
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'signal': self.signal,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat()
        }

class SimpleEnhancedCascadeAnalyzer:
    """Простая версия улучшенного каскадного анализатора."""
    
    def __init__(self):
        self.stage1d_cache = {}
        
    async def prefilter_symbols_stage1d(self, symbols: List[str]) -> Dict[str, SimpleStage1dResult]:
        """Предварительная фильтрация символов по этапу 1d."""
        results = {}
        
        for symbol in symbols:
            # Симулируем анализ ML сигналов
            await asyncio.sleep(0.1)  # Имитируем время обработки
            
            # Простая логика для демонстрации
            if symbol in ['SBER', 'GAZP', 'LKOH']:
                signal = 'BUY'
                confidence = 0.75
            elif symbol in ['NVTK', 'ROSN']:
                signal = 'SELL'
                confidence = 0.70
            else:
                signal = 'HOLD'
                confidence = 0.45
            
            result = SimpleStage1dResult(symbol, signal, confidence)
            results[symbol] = result
            
            print(f"  {symbol}: {signal} | Уверенность: {confidence:.1%}")
        
        return results
    
    def get_passed_symbols(self, stage1d_results: Dict[str, SimpleStage1dResult]) -> List[str]:
        """Получить символы, прошедшие этап 1d."""
        return [symbol for symbol, result in stage1d_results.items() 
                if result.signal in ['BUY', 'SELL'] and result.confidence >= 0.6]
    
    def get_buy_candidates(self, stage1d_results: Dict[str, SimpleStage1dResult]) -> List[SimpleStage1dResult]:
        """Получить кандидатов на покупку."""
        return [result for result in stage1d_results.values() 
                if result.signal == 'BUY' and result.confidence >= 0.6]
    
    def get_sell_candidates(self, stage1d_results: Dict[str, SimpleStage1dResult]) -> List[SimpleStage1dResult]:
        """Получить кандидатов на продажу."""
        return [result for result in stage1d_results.values() 
                if result.signal == 'SELL' and result.confidence >= 0.6]
    
    def get_top_candidates(self, stage1d_results: Dict[str, SimpleStage1dResult], limit: int = 5) -> List[SimpleStage1dResult]:
        """Получить топ кандидатов по уверенности."""
        candidates = [result for result in stage1d_results.values() 
                     if result.signal in ['BUY', 'SELL'] and result.confidence >= 0.6]
        
        # Сортируем по уверенности (по убыванию)
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        return candidates[:limit]
    
    async def analyze_prefiltered_symbols(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Анализ предварительно отфильтрованных символов."""
        results = []
        
        for symbol in symbols:
            # Симулируем каскадный анализ (этапы 1h, 1m, 1s)
            await asyncio.sleep(0.2)  # Имитируем время обработки
            
            # Простая логика для демонстрации
            if symbol == 'SBER':
                result = {
                    'symbol': symbol,
                    'final_signal': 'BUY',
                    'confidence': 0.85,
                    'entry_price': 250.50,
                    'stop_loss': 245.00,
                    'take_profit': 260.00,
                    'risk_reward': 2.0,
                    'auto_trade_enabled': True
                }
            elif symbol == 'GAZP':
                result = {
                    'symbol': symbol,
                    'final_signal': 'BUY',
                    'confidence': 0.80,
                    'entry_price': 180.25,
                    'stop_loss': 175.00,
                    'take_profit': 190.00,
                    'risk_reward': 1.9,
                    'auto_trade_enabled': True
                }
            else:
                result = {
                    'symbol': symbol,
                    'final_signal': None,
                    'confidence': 0.0,
                    'entry_price': 0.0,
                    'stop_loss': 0.0,
                    'take_profit': 0.0,
                    'risk_reward': 0.0,
                    'auto_trade_enabled': False,
                    'rejection_reason': 'Failed at stage 1h'
                }
            
            results.append(result)
        
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша."""
        total = len(self.stage1d_cache)
        passed = len([r for r in self.stage1d_cache.values() if r.signal in ['BUY', 'SELL']])
        buy_signals = len([r for r in self.stage1d_cache.values() if r.signal == 'BUY'])
        sell_signals = len([r for r in self.stage1d_cache.values() if r.signal == 'SELL'])
        
        return {
            'total_cached': total,
            'passed_stage1d': passed,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'cache_hit_rate': f"{passed/total*100:.1f}%" if total > 0 else "0%"
        }

async def demo_enhanced_cascade():
    """Демонстрация работы улучшенного каскадного анализатора."""
    
    print("Демонстрация улучшенного каскадного анализатора")
    print("=" * 60)
    
    try:
        # Создаем простой анализатор
        enhanced_analyzer = SimpleEnhancedCascadeAnalyzer()
        
        print("Анализатор успешно создан")
        
        # Тестовые символы
        test_symbols = ['SBER', 'GAZP', 'LKOH', 'NVTK', 'ROSN', 'MGNT', 'YNDX', 'VKCO']
        
        print(f"\nТестируем предварительную фильтрацию для {len(test_symbols)} символов:")
        print("Символы:", ", ".join(test_symbols))
        
        # Запускаем предварительную фильтрацию
        print("\nВыполняется предварительная фильтрация по этапу 1d...")
        print("Результаты этапа 1d:")
        
        stage1d_results = await enhanced_analyzer.prefilter_symbols_stage1d(test_symbols)
        
        print(f"\nФильтрация завершена! Обработано {len(stage1d_results)} символов")
        
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
            successful_results = [r for r in results if r['final_signal'] is not None]
            if successful_results:
                print(f"\nУспешные сигналы ({len(successful_results)}):")
                for result in successful_results:
                    print(f"  - {result['symbol']}: {result['final_signal']} | Уверенность: {result['confidence']:.1%}")
                    print(f"    Цена входа: {result['entry_price']:.2f} RUB | R/R: {result['risk_reward']:.1f}")
            else:
                print("Нет успешных сигналов после полного каскадного анализа")
        
        print("\nДемонстрация завершена успешно!")
        print("\nКонцепция работы:")
        print("1. При загрузке страницы запускается предварительная фильтрация по этапу 1d")
        print("2. Пользователь видит только кандидатов, прошедших ML фильтрацию")
        print("3. При нажатии 'Запустить анализ' выполняется только этапы 1h, 1m, 1s")
        print("4. Это значительно ускоряет процесс и улучшает качество результатов")
        
    except Exception as e:
        print(f"Ошибка демонстрации: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_enhanced_cascade())




