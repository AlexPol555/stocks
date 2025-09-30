#!/usr/bin/env python3
"""
Enhanced Cascade Multi-Timeframe Analyzer.
Улучшенный каскадный анализатор с предварительной фильтрацией по этапу 1d.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class Stage1dResult:
    """Результат этапа 1d для предварительной фильтрации."""
    
    def __init__(self, symbol: str, signal: str, confidence: float, ensemble_signal: str, price_signal: str):
        self.symbol = symbol
        self.signal = signal
        self.confidence = confidence
        self.ensemble_signal = ensemble_signal
        self.price_signal = price_signal
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать результат в словарь."""
        return {
            'symbol': self.symbol,
            'signal': self.signal,
            'confidence': self.confidence,
            'ensemble_signal': self.ensemble_signal,
            'price_signal': self.price_signal,
            'timestamp': self.timestamp.isoformat()
        }


class EnhancedCascadeAnalyzer:
    """Улучшенный каскадный анализатор с предварительной фильтрацией."""
    
    def __init__(self, cascade_analyzer):
        """Инициализация с базовым каскадным анализатором."""
        self.cascade_analyzer = cascade_analyzer
        self.stage1d_cache = {}  # Кэш результатов этапа 1d
        
    async def prefilter_symbols_stage1d(self, symbols: List[str]) -> Dict[str, Stage1dResult]:
        """
        Предварительная фильтрация символов по этапу 1d (ML сигналы).
        
        Args:
            symbols: Список символов для проверки
            
        Returns:
            Dict[str, Stage1dResult]: Словарь с результатами этапа 1d для каждого символа
        """
        results = {}
        
        for symbol in symbols:
            try:
                # Проверяем кэш
                if symbol in self.stage1d_cache:
                    cache_result = self.stage1d_cache[symbol]
                    # Проверяем, не устарел ли кэш (больше 1 часа)
                    if (datetime.now() - cache_result.timestamp).seconds < 3600:
                        results[symbol] = cache_result
                        continue
                
                # Выполняем этап 1d
                stage1_result = await self.cascade_analyzer._analyze_stage_1d(symbol)
                
                # Создаем результат
                stage1d_result = Stage1dResult(
                    symbol=symbol,
                    signal=stage1_result.get('signal', 'HOLD'),
                    confidence=stage1_result.get('confidence', 0.0),
                    ensemble_signal=stage1_result.get('ensemble_signal', 'HOLD'),
                    price_signal=stage1_result.get('price_signal', 'HOLD')
                )
                
                # Кэшируем результат
                self.stage1d_cache[symbol] = stage1d_result
                
                results[symbol] = stage1d_result
                
                if stage1_result['proceed']:
                    logger.info(f"{symbol} passed stage 1d: {stage1d_result.signal} (confidence: {stage1d_result.confidence:.2f})")
                else:
                    logger.info(f"{symbol} rejected at stage 1d: {stage1_result['reason']}")
                    
            except Exception as e:
                logger.error(f"Error in stage 1d prefilter for {symbol}: {e}")
                # В случае ошибки создаем результат с HOLD
                stage1d_result = Stage1dResult(
                    symbol=symbol,
                    signal='HOLD',
                    confidence=0.0,
                    ensemble_signal='HOLD',
                    price_signal='HOLD'
                )
                results[symbol] = stage1d_result
        
        return results
    
    def get_passed_symbols(self, stage1d_results: Dict[str, Stage1dResult]) -> List[str]:
        """Получить символы, прошедшие этап 1d."""
        return [symbol for symbol, result in stage1d_results.items() 
                if result.signal in ['BUY', 'SELL'] and result.confidence >= 0.6]
    
    def get_buy_candidates(self, stage1d_results: Dict[str, Stage1dResult]) -> List[Stage1dResult]:
        """Получить кандидатов на покупку."""
        return [result for result in stage1d_results.values() 
                if result.signal == 'BUY' and result.confidence >= 0.6]
    
    def get_sell_candidates(self, stage1d_results: Dict[str, Stage1dResult]) -> List[Stage1dResult]:
        """Получить кандидатов на продажу."""
        return [result for result in stage1d_results.values() 
                if result.signal == 'SELL' and result.confidence >= 0.6]
    
    def get_top_candidates(self, stage1d_results: Dict[str, Stage1dResult], limit: int = 20) -> List[Stage1dResult]:
        """Получить топ кандидатов по уверенности."""
        candidates = [result for result in stage1d_results.values() 
                     if result.signal in ['BUY', 'SELL'] and result.confidence >= 0.6]
        
        # Сортируем по уверенности (по убыванию)
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        return candidates[:limit]
    
    async def analyze_prefiltered_symbols(self, symbols: List[str]) -> List:
        """
        Анализ предварительно отфильтрованных символов (начинаем с этапа 1h).
        
        Args:
            symbols: Список символов, уже прошедших этап 1d
            
        Returns:
            List: Результаты каскадного анализа
        """
        results = []
        
        for symbol in symbols:
            try:
                # Поскольку символы уже прошли этап 1d, начинаем с этапа 1h
                result = await self.cascade_analyzer.analyze_symbol_cascade(symbol)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing prefiltered symbol {symbol}: {e}")
                # Создаем результат с ошибкой
                from core.cascade_analyzer import CascadeSignalResult
                error_result = CascadeSignalResult()
                error_result.symbol = symbol
                error_result.rejected_at_stage = 'error'
                error_result.rejection_reason = str(e)
                results.append(error_result)
        
        return results
    
    def clear_cache(self):
        """Очистить кэш результатов этапа 1d."""
        self.stage1d_cache.clear()
        logger.info("Stage 1d cache cleared")
    
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




