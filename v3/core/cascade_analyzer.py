#!/usr/bin/env python3
"""
Cascade Multi-Timeframe Analyzer.
Каскадный анализатор многоуровневых данных с последовательной фильтрацией сигналов.

Workflow:
1. При загрузке страницы - выполняется первый ML анализ по таблице data_1d
2. По кнопке "Запустить анализ" - происходит каскад: 1h → 1m → 1s → торговля
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
import asyncio

from core.ml.cascade_cache import cascade_ml_cache

logger = logging.getLogger(__name__)


class CascadeSignalResult:
    """Результат каскадного анализа сигналов."""
    
    def __init__(self):
        self.symbol = ""
        self.timestamp = datetime.now()
        self.stages = {}  # Результаты каждого этапа
        self.final_signal = None
        self.confidence = 0.0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.risk_reward = 0.0
        self.rejected_at_stage = None
        self.rejection_reason = ""
        self.auto_trade_enabled = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать результат в словарь."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'final_signal': self.final_signal,
            'confidence': self.confidence,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'risk_reward': self.risk_reward,
            'stages': self.stages,
            'rejected_at_stage': self.rejected_at_stage,
            'rejection_reason': self.rejection_reason,
            'auto_trade_enabled': self.auto_trade_enabled,
            'is_valid': self.final_signal is not None
        }


class CascadeAnalyzer:
    """Каскадный анализатор для многоуровневых торговых сигналов.
    
    Workflow:
    1. При загрузке страницы - выполняется первый ML анализ по таблице data_1d
    2. По кнопке "Запустить анализ" - происходит каскад: 1d → 1h → 1m → 1s → торговля
    """
    
    def __init__(self, multi_analyzer, ml_manager=None, demo_trading=None):
        self.multi_analyzer = multi_analyzer
        self.ml_manager = ml_manager
        self.demo_trading = demo_trading
        
        # Кэш для ML результатов первого этапа
        self.initial_ml_cache = {}
        
        print(f"🔧 [CASCADE_INIT] CascadeAnalyzer инициализирован")
        print(f"🔧 [CASCADE_INIT] ML менеджер: {type(self.ml_manager) if self.ml_manager else 'None'}")
        print(f"🔧 [CASCADE_INIT] Multi analyzer: {type(self.multi_analyzer) if self.multi_analyzer else 'None'}")
        print(f"🔧 [CASCADE_INIT] Кэш ML результатов: {len(self.initial_ml_cache)} элементов")
        
        # Настройки каскадной фильтрации
        self.stage_configs = {
            '1d': {
                'min_confidence': 0.6,
                'required_signals': ['ensemble', 'price'],
                'lookback_days': 365
            },
            '1h': {
                'min_confidence': 0.5,
                'required_confirmations': ['trend', 'volume'],
                'lookback_days': 7
            },
            '1m': {
                'min_confidence': 0.4,
                'required_confirmations': ['entry_point', 'risk_reward'],
                'lookback_days': 1
            },
            '1s': {
                'min_confidence': 0.3,
                'required_confirmations': ['execution_quality'],
                'lookback_days': 0.02  # 30 минут
            }
        }
        
        # Настройки автоматической торговли
        self.auto_trade_config = {
            'enabled': False,
            'min_confidence': 0.75,
            'max_position_size': 1000,  # Максимальный размер позиции в рублях
            'risk_per_trade': 0.02,  # 2% риска на сделку
            'max_daily_trades': 5,
            'trading_hours': {'start': 9, 'end': 18}  # Время торговли
        }
    
    def inspect_ml_cache(self) -> Dict[str, Any]:
        """Инспекция содержимого кэша ML результатов."""
        try:
            print(f"🔍 [CACHE_INSPECT] Начинаем инспекцию кэша ML результатов...")
            print(f"🔍 [CACHE_INSPECT] Размер кэша: {len(self.initial_ml_cache)} элементов")
            
            if not self.initial_ml_cache:
                print("⚠️ [CACHE_INSPECT] Кэш пустой")
                return {
                    'cache_size': 0,
                    'symbols': [],
                    'strong_signals': [],
                    'cache_details': {}
                }
            
            # Анализируем содержимое кэша
            symbols = list(self.initial_ml_cache.keys())
            strong_signals = []
            cache_details = {}
            
            print(f"📋 [CACHE_INSPECT] Символы в кэше: {symbols[:10]}{'...' if len(symbols) > 10 else ''}")
            
            for symbol, ml_result in self.initial_ml_cache.items():
                ensemble_signal = ml_result.get('ml_ensemble_signal', 'HOLD')
                confidence = ml_result.get('ml_price_confidence', 0.0)
                
                cache_details[symbol] = {
                    'ensemble_signal': ensemble_signal,
                    'confidence': confidence,
                    'has_error': 'error' in ml_result,
                    'keys': list(ml_result.keys())
                }
                
                # Проверяем сильные сигналы
                if (ensemble_signal in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL'] and 
                    confidence >= 0.5):
                    strong_signals.append({
                        'symbol': symbol,
                        'signal': ensemble_signal,
                        'confidence': confidence
                    })
                
                print(f"  📊 {symbol}: {ensemble_signal} (уверенность: {confidence:.1%})")
            
            print(f"🎯 [CACHE_INSPECT] Сильных сигналов: {len(strong_signals)}")
            print(f"📊 [CACHE_INSPECT] Детали кэша: {len(cache_details)} элементов")
            
            return {
                'cache_size': len(self.initial_ml_cache),
                'symbols': symbols,
                'strong_signals': strong_signals,
                'cache_details': cache_details
            }
            
        except Exception as e:
            print(f"❌ [CACHE_INSPECT] Ошибка инспекции кэша: {e}")
            return {
                'cache_size': 0,
                'symbols': [],
                'strong_signals': [],
                'cache_details': {},
                'error': str(e)
            }
    
    def verify_cache_integrity(self) -> Dict[str, Any]:
        """Проверка целостности кэша ML результатов."""
        try:
            print(f"🔍 [CACHE_VERIFY] Начинаем проверку целостности кэша...")
            
            # Проверяем базовые свойства
            cache_size = len(self.initial_ml_cache)
            print(f"📊 [CACHE_VERIFY] Размер кэша: {cache_size}")
            
            if cache_size == 0:
                print("⚠️ [CACHE_VERIFY] Кэш пустой")
                return {
                    'is_valid': False,
                    'cache_size': 0,
                    'issues': ['Кэш пустой'],
                    'recommendations': ['Запустите ML анализ для заполнения кэша']
                }
            
            # Проверяем структуру данных
            issues = []
            valid_entries = 0
            invalid_entries = 0
            
            for symbol, ml_result in self.initial_ml_cache.items():
                if not isinstance(ml_result, dict):
                    issues.append(f"Символ {symbol}: результат не является словарем")
                    invalid_entries += 1
                    continue
                
                # Проверяем обязательные ключи
                required_keys = ['ml_ensemble_signal', 'ml_price_confidence']
                missing_keys = [key for key in required_keys if key not in ml_result]
                
                if missing_keys:
                    issues.append(f"Символ {symbol}: отсутствуют ключи {missing_keys}")
                    invalid_entries += 1
                    continue
                
                # Проверяем типы значений
                if not isinstance(ml_result.get('ml_ensemble_signal'), str):
                    issues.append(f"Символ {symbol}: ml_ensemble_signal не является строкой")
                    invalid_entries += 1
                    continue
                
                if not isinstance(ml_result.get('ml_price_confidence'), (int, float)):
                    issues.append(f"Символ {symbol}: ml_price_confidence не является числом")
                    invalid_entries += 1
                    continue
                
                valid_entries += 1
            
            # Проверяем наличие ошибок
            error_entries = sum(1 for result in self.initial_ml_cache.values() if 'error' in result)
            
            print(f"✅ [CACHE_VERIFY] Валидных записей: {valid_entries}")
            print(f"❌ [CACHE_VERIFY] Невалидных записей: {invalid_entries}")
            print(f"⚠️ [CACHE_VERIFY] Записей с ошибками: {error_entries}")
            
            # Формируем рекомендации
            recommendations = []
            if invalid_entries > 0:
                recommendations.append("Перезапустите ML анализ для исправления невалидных записей")
            if error_entries > 0:
                recommendations.append("Проверьте логи ML анализа для исправления ошибок")
            if valid_entries == 0:
                recommendations.append("Кэш полностью невалиден, требуется полный перезапуск")
            
            is_valid = invalid_entries == 0 and valid_entries > 0
            
            print(f"🎯 [CACHE_VERIFY] Кэш валиден: {is_valid}")
            if issues:
                print(f"⚠️ [CACHE_VERIFY] Проблемы: {issues[:3]}{'...' if len(issues) > 3 else ''}")
            
            return {
                'is_valid': is_valid,
                'cache_size': cache_size,
                'valid_entries': valid_entries,
                'invalid_entries': invalid_entries,
                'error_entries': error_entries,
                'issues': issues,
                'recommendations': recommendations
            }
            
        except Exception as e:
            print(f"❌ [CACHE_VERIFY] Ошибка проверки целостности: {e}")
            return {
                'is_valid': False,
                'cache_size': 0,
                'issues': [f"Ошибка проверки: {str(e)}"],
                'recommendations': ['Проверьте логи и перезапустите систему']
            }
        
    
    async def analyze_symbol_cascade(self, symbol: str, initial_ml_result: Dict[str, Any] = None) -> CascadeSignalResult:
        """
        Выполнить каскадный анализ для символа.
        
        Args:
            symbol: Торговый символ (например, 'SBER')
            initial_ml_result: Результат предварительного ML анализа (1d)
            
        Returns:
            CascadeSignalResult: Результат каскадного анализа
        """
        result = CascadeSignalResult()
        result.symbol = symbol
        
        try:
            print(f"🔍 [CASCADE_SYMBOL] Начинаем каскадный анализ для {symbol}")
            print(f"🔍 [CASCADE_SYMBOL] initial_ml_result: {initial_ml_result}")
            print(f"🔍 [CASCADE_SYMBOL] Тип initial_ml_result: {type(initial_ml_result)}")
            logger.info(f"Starting cascade analysis for {symbol}")
            
            # Проверяем, есть ли предварительный ML результат
            if not initial_ml_result:
                print(f"📋 [CASCADE_SYMBOL] {symbol}: Получаем ML результат из кэша...")
                print(f"🔍 [CASCADE_SYMBOL] {symbol}: Размер кэша: {len(self.initial_ml_cache)}")
                print(f"🔍 [CASCADE_SYMBOL] {symbol}: Ключи в кэше: {list(self.initial_ml_cache.keys())[:5]}")
                # Если нет предварительного результата, получаем из кэша
                initial_ml_result = self.initial_ml_cache.get(symbol, {})
                print(f"🔍 [CASCADE_SYMBOL] {symbol}: Результат из кэша: {initial_ml_result}")
            
            if not initial_ml_result:
                print(f"❌ [CASCADE_SYMBOL] {symbol}: Нет ML результата")
                result.rejected_at_stage = '1d'
                result.rejection_reason = 'No initial ML result available'
                logger.warning(f"{symbol} rejected: No initial ML result")
                return result
            
            # Проверяем, что ML сигнал достаточно сильный для каскадного анализа
            ensemble_signal = initial_ml_result.get('ml_ensemble_signal', 'HOLD')
            confidence = initial_ml_result.get('ml_price_confidence', 0.0)
            
            print(f"📊 [CASCADE_SYMBOL] {symbol}: ML сигнал = {ensemble_signal}, уверенность = {confidence:.1%}")
            
            if ensemble_signal not in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL']:
                print(f"❌ [CASCADE_SYMBOL] {symbol}: Слабый ML сигнал {ensemble_signal}")
                result.rejected_at_stage = '1d'
                result.rejection_reason = f'Weak ML signal: {ensemble_signal}'
                logger.info(f"{symbol} rejected: Weak ML signal {ensemble_signal}")
                return result
            
            if confidence < 0.5:  # Минимальная уверенность для каскадного анализа
                print(f"❌ [CASCADE_SYMBOL] {symbol}: Низкая уверенность {confidence:.1%}")
                result.rejected_at_stage = '1d'
                result.rejection_reason = f'Low ML confidence: {confidence:.2f}'
                logger.info(f"{symbol} rejected: Low ML confidence {confidence:.2f}")
                return result
            
            print(f"✅ [CASCADE_SYMBOL] {symbol}: Этап 1d пройден")
            
            # Сохраняем результат 1d этапа
            result.stages['1d'] = {
                'proceed': True,
                'signal': ensemble_signal,
                'confidence': confidence,
                'ensemble_signal': ensemble_signal,
                'price_signal': initial_ml_result.get('ml_price_signal', 'HOLD'),
                'sentiment_signal': initial_ml_result.get('ml_sentiment_signal', 'HOLD'),
                'technical_signal': initial_ml_result.get('ml_technical_signal', 'HOLD'),
                'reason': 'Initial ML analysis passed'
            }
            
            # Этап 1: Подтверждение на часовых данных (1h)
            print(f"⏰ [CASCADE_SYMBOL] {symbol}: Этап 1h - анализ часовых данных...")
            stage1_result = await self._analyze_stage_1h(symbol, result.stages['1d'])
            result.stages['1h'] = stage1_result
            
            if not stage1_result['proceed']:
                print(f"❌ [CASCADE_SYMBOL] {symbol}: Отклонен на этапе 1h - {stage1_result['reason']}")
                result.rejected_at_stage = '1h'
                result.rejection_reason = stage1_result['reason']
                logger.info(f"{symbol} rejected at stage 1h: {result.rejection_reason}")
                return result
            
            print(f"✅ [CASCADE_SYMBOL] {symbol}: Этап 1h пройден")
            
            # Этап 2: Поиск точки входа на минутных данных (1m)
            print(f"🎯 [CASCADE_SYMBOL] {symbol}: Этап 1m - поиск точки входа...")
            stage2_result = await self._analyze_stage_1m(symbol, result.stages['1d'], stage1_result)
            result.stages['1m'] = stage2_result
            
            if not stage2_result['proceed']:
                print(f"❌ [CASCADE_SYMBOL] {symbol}: Отклонен на этапе 1m - {stage2_result['reason']}")
                result.rejected_at_stage = '1m'
                result.rejection_reason = stage2_result['reason']
                logger.info(f"{symbol} rejected at stage 1m: {result.rejection_reason}")
                return result
            
            print(f"✅ [CASCADE_SYMBOL] {symbol}: Этап 1m пройден")
            
            # Этап 3: Оптимизация на секундных данных (1s)
            print(f"⚡ [CASCADE_SYMBOL] {symbol}: Этап 1s - микро-оптимизация...")
            stage3_result = await self._analyze_stage_1s(symbol, result.stages['1d'], stage1_result, stage2_result)
            result.stages['1s'] = stage3_result
            
            if not stage3_result['proceed']:
                print(f"❌ [CASCADE_SYMBOL] {symbol}: Отклонен на этапе 1s - {stage3_result['reason']}")
                result.rejected_at_stage = '1s'
                result.rejection_reason = stage3_result['reason']
                logger.info(f"{symbol} rejected at stage 1s: {result.rejection_reason}")
                return result
            
            print(f"✅ [CASCADE_SYMBOL] {symbol}: Этап 1s пройден")
            
            # Формируем финальный сигнал
            result.final_signal = ensemble_signal  # Используем сигнал из ML анализа
            result.confidence = self._calculate_final_confidence(
                result.stages['1d'], stage1_result, stage2_result, stage3_result
            )
            result.entry_price = stage3_result['entry_price']
            result.stop_loss = stage2_result['stop_loss']
            result.take_profit = stage2_result['take_profit']
            result.risk_reward = stage2_result['risk_reward']
            
            # Проверяем, можно ли включить автоматическую торговлю
            result.auto_trade_enabled = (
                self.auto_trade_config['enabled'] and 
                result.confidence >= self.auto_trade_config['min_confidence'] and
                self._is_trading_hours()
            )
            
            print(f"🎉 [CASCADE_SYMBOL] {symbol}: Каскадный анализ завершен успешно!")
            print(f"  📊 Сигнал: {result.final_signal}")
            print(f"  🎯 Уверенность: {result.confidence:.1%}")
            print(f"  💰 Цена входа: {result.entry_price:.2f}")
            print(f"  🛡️ Стоп-лосс: {result.stop_loss:.2f}")
            print(f"  🎯 Тейк-профит: {result.take_profit:.2f}")
            print(f"  ⚖️ Риск/Доходность: {result.risk_reward:.1f}")
            print(f"  🤖 Автоторговля: {'Да' if result.auto_trade_enabled else 'Нет'}")
            
            logger.info(f"{symbol} cascade analysis completed successfully. Signal: {result.final_signal}, Confidence: {result.confidence:.2f}")
            
        except Exception as e:
            print(f"💥 [CASCADE_SYMBOL] {symbol}: Критическая ошибка - {e}")
            logger.error(f"Error in cascade analysis for {symbol}: {e}")
            result.rejected_at_stage = 'error'
            result.rejection_reason = str(e)
        
        return result
    
    async def _analyze_stage_1d(self, symbol: str) -> Dict[str, Any]:
        """Этап 1: Анализ ML сигналов на дневных данных."""
        try:
            # Получаем FIGI для символа
            figi = self.multi_analyzer.get_figi_for_symbol(symbol)
            if not figi:
                return {
                    'proceed': False,
                    'reason': f'No FIGI mapping found for symbol {symbol}',
                    'signal': None,
                    'confidence': 0.0
                }
            
            # Получаем дневные данные из таблицы data_1d или daily_data
            daily_data = self._get_data_from_db(symbol, '1d')
            
            if daily_data.empty:
                logger.warning(f"No daily data available for {symbol} (FIGI: {figi})")
                return {
                    'proceed': False,
                    'reason': f'No daily data available for {symbol} (FIGI: {figi})',
                    'signal': None,
                    'confidence': 0.0
                }
            
            # Используем кэшированные ML сигналы, если доступны
            ml_signals = {}
            if symbol in self.initial_ml_cache:
                ml_signals = self.initial_ml_cache[symbol]
                logger.info(f"Using cached ML signals for {symbol}")
            else:
                # Генерируем ML сигналы, если нет в кэше
                if self.ml_manager:
                    try:
                        from core.ml.signals import MLSignalGenerator
                        signal_generator = MLSignalGenerator(self.ml_manager)
                        ml_signals = await signal_generator.generate_ml_signals(symbol)
                    except Exception as e:
                        logger.warning(f"ML signals generation failed for {symbol}: {e}")
            
            # Если ML недоступен, используем технические индикаторы
            if not ml_signals or 'error' in ml_signals:
                ml_signals = self._generate_fallback_signals(daily_data)
            
            ensemble_signal = ml_signals.get('ml_ensemble_signal', 'HOLD')
            price_signal = ml_signals.get('ml_price_signal', 'HOLD')
            
            # Проверяем требования этапа
            config = self.stage_configs['1d']
            required_signals = config['required_signals']
            
            # Проверяем наличие требуемых сигналов
            has_ensemble = ensemble_signal in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL']
            has_price = price_signal in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL']
            
            if not (has_ensemble and has_price):
                return {
                    'proceed': False,
                    'reason': f'Missing required signals. Ensemble: {ensemble_signal}, Price: {price_signal}',
                    'signal': ensemble_signal,
                    'confidence': 0.0
                }
            
            # Проверяем согласованность сигналов
            buy_signals = [ensemble_signal, price_signal].count('BUY') + [ensemble_signal, price_signal].count('STRONG_BUY')
            sell_signals = [ensemble_signal, price_signal].count('SELL') + [ensemble_signal, price_signal].count('STRONG_SELL')
            
            if buy_signals > sell_signals:
                final_signal = 'BUY'
                confidence = min(0.9, 0.5 + buy_signals * 0.2)
            elif sell_signals > buy_signals:
                final_signal = 'SELL'
                confidence = min(0.9, 0.5 + sell_signals * 0.2)
            else:
                return {
                    'proceed': False,
                    'reason': 'Conflicting signals between ensemble and price models',
                    'signal': ensemble_signal,
                    'confidence': 0.0
                }
            
            # Проверяем минимальную уверенность
            if confidence < config['min_confidence']:
                return {
                    'proceed': False,
                    'reason': f'Confidence too low: {confidence:.2f} < {config["min_confidence"]}',
                    'signal': final_signal,
                    'confidence': confidence
                }
            
            return {
                'proceed': True,
                'reason': 'Daily ML signals confirmed',
                'signal': final_signal,
                'confidence': confidence,
                'ensemble_signal': ensemble_signal,
                'price_signal': price_signal,
                'sentiment_signal': ml_signals.get('ml_sentiment_signal', 'HOLD'),
                'technical_signal': ml_signals.get('ml_technical_signal', 'HOLD'),
                'data_points': len(daily_data)
            }
            
        except Exception as e:
            logger.error(f"Error in stage 1d analysis for {symbol}: {e}")
            return {
                'proceed': False,
                'reason': f'Stage 1d error: {str(e)}',
                'signal': None,
                'confidence': 0.0
            }
    
    def _generate_fallback_signals(self, daily_data: pd.DataFrame) -> Dict[str, Any]:
        """Генерировать fallback сигналы на основе технических индикаторов."""
        try:
            if len(daily_data) < 20:
                return {'ml_ensemble_signal': 'HOLD', 'ml_price_signal': 'HOLD'}
            
            # Простые технические сигналы
            data = daily_data.copy()
            data['SMA_20'] = data['close'].rolling(window=20, min_periods=1).mean()
            data['SMA_50'] = data['close'].rolling(window=50, min_periods=1).mean()
            
            current_price = data['close'].iloc[-1]
            sma_20 = data['SMA_20'].iloc[-1]
            sma_50 = data['SMA_50'].iloc[-1]
            
            # Простая логика сигналов
            if current_price > sma_20 > sma_50:
                signal = 'BUY'
                confidence = 0.6
            elif current_price < sma_20 < sma_50:
                signal = 'SELL'
                confidence = 0.6
            else:
                signal = 'HOLD'
                confidence = 0.3
            
            return {
                'ml_ensemble_signal': signal,
                'ml_price_signal': signal,
                'ml_sentiment_signal': 'HOLD',
                'ml_technical_signal': signal,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Error generating fallback signals: {e}")
            return {'ml_ensemble_signal': 'HOLD', 'ml_price_signal': 'HOLD'}
    
    async def _analyze_stage_1h(self, symbol: str, stage1_result: Dict[str, Any]) -> Dict[str, Any]:
        """Этап 2: Подтверждение на часовых данных."""
        try:
            # Получаем FIGI для символа
            figi = self.multi_analyzer.get_figi_for_symbol(symbol)
            if not figi:
                return {
                    'proceed': False,
                    'reason': f'No FIGI mapping found for symbol {symbol}',
                    'trend': None,
                    'confidence': 0.0
                }
            
            # Получаем часовые данные из таблицы data_1hour
            hourly_data = self._get_data_from_db(symbol, '1h')
            
            if hourly_data.empty:
                return {
                    'proceed': False,
                    'reason': 'No hourly data available',
                    'trend': None,
                    'confidence': 0.0
                }
            
            # Анализируем тренд на часовых данных
            trend_analysis = self._analyze_hourly_trend(hourly_data, stage1_result['signal'])
            
            # Проверяем требования этапа
            config = self.stage_configs['1h']
            required_confirmations = config['required_confirmations']
            
            # Проверяем подтверждения
            trend_confirmed = trend_analysis['trend_aligned']
            volume_confirmed = trend_analysis['volume_confirmation']
            
            confirmations = {
                'trend': trend_confirmed,
                'volume': volume_confirmed
            }
            
            # Проверяем наличие всех требуемых подтверждений
            missing_confirmations = [conf for conf in required_confirmations if not confirmations.get(conf, False)]
            
            if missing_confirmations:
                return {
                    'proceed': False,
                    'reason': f'Missing confirmations: {missing_confirmations}',
                    'trend': trend_analysis['trend'],
                    'confidence': trend_analysis['confidence'],
                    'confirmations': confirmations
                }
            
            # Проверяем минимальную уверенность
            if trend_analysis['confidence'] < config['min_confidence']:
                return {
                    'proceed': False,
                    'reason': f'Hourly confidence too low: {trend_analysis["confidence"]:.2f} < {config["min_confidence"]}',
                    'trend': trend_analysis['trend'],
                    'confidence': trend_analysis['confidence'],
                    'confirmations': confirmations
                }
            
            return {
                'proceed': True,
                'reason': 'Hourly trend confirmed',
                'trend': trend_analysis['trend'],
                'confidence': trend_analysis['confidence'],
                'confirmations': confirmations,
                'support_level': trend_analysis['support_level'],
                'resistance_level': trend_analysis['resistance_level'],
                'volume_trend': trend_analysis['volume_trend']
            }
            
        except Exception as e:
            logger.error(f"Error in stage 1h analysis for {symbol}: {e}")
            return {
                'proceed': False,
                'reason': f'Stage 1h error: {str(e)}',
                'trend': None,
                'confidence': 0.0
            }
    
    async def _analyze_stage_1m(self, symbol: str, stage1_result: Dict[str, Any], stage2_result: Dict[str, Any]) -> Dict[str, Any]:
        """Этап 3: Поиск точки входа на минутных данных."""
        try:
            # Получаем FIGI для символа
            figi = self.multi_analyzer.get_figi_for_symbol(symbol)
            if not figi:
                return {
                    'proceed': False,
                    'reason': f'No FIGI mapping found for symbol {symbol}',
                    'entry_price': 0.0,
                    'confidence': 0.0
                }
            
            # Получаем минутные данные из таблицы data_1min
            minute_data = self._get_data_from_db(symbol, '1m')
            
            if minute_data.empty:
                return {
                    'proceed': False,
                    'reason': 'No minute data available',
                    'entry_price': 0.0,
                    'confidence': 0.0
                }
            
            # Анализируем точки входа
            entry_analysis = self._analyze_minute_entry(minute_data, stage1_result['signal'], stage2_result)
            
            # Проверяем требования этапа
            config = self.stage_configs['1m']
            required_confirmations = config['required_confirmations']
            
            # Проверяем подтверждения
            has_entry_point = entry_analysis['entry_price'] > 0
            has_good_risk_reward = entry_analysis['risk_reward'] >= 2.0
            
            confirmations = {
                'entry_point': has_entry_point,
                'risk_reward': has_good_risk_reward
            }
            
            # Проверяем наличие всех требуемых подтверждений
            missing_confirmations = [conf for conf in required_confirmations if not confirmations.get(conf, False)]
            
            if missing_confirmations:
                return {
                    'proceed': False,
                    'reason': f'Missing confirmations: {missing_confirmations}',
                    'entry_price': entry_analysis['entry_price'],
                    'confidence': entry_analysis['confidence'],
                    'confirmations': confirmations
                }
            
            # Проверяем минимальную уверенность
            if entry_analysis['confidence'] < config['min_confidence']:
                return {
                    'proceed': False,
                    'reason': f'Minute confidence too low: {entry_analysis["confidence"]:.2f} < {config["min_confidence"]}',
                    'entry_price': entry_analysis['entry_price'],
                    'confidence': entry_analysis['confidence'],
                    'confirmations': confirmations
                }
            
            return {
                'proceed': True,
                'reason': 'Minute entry point confirmed',
                'entry_price': entry_analysis['entry_price'],
                'stop_loss': entry_analysis['stop_loss'],
                'take_profit': entry_analysis['take_profit'],
                'risk_reward': entry_analysis['risk_reward'],
                'confidence': entry_analysis['confidence'],
                'confirmations': confirmations,
                'entry_reason': entry_analysis['entry_reason'],
                'volume_spike': entry_analysis['volume_spike']
            }
            
        except Exception as e:
            logger.error(f"Error in stage 1m analysis for {symbol}: {e}")
            return {
                'proceed': False,
                'reason': f'Stage 1m error: {str(e)}',
                'entry_price': 0.0,
                'confidence': 0.0
            }
    
    async def _analyze_stage_1s(self, symbol: str, stage1_result: Dict[str, Any], stage2_result: Dict[str, Any], stage3_result: Dict[str, Any]) -> Dict[str, Any]:
        """Этап 4: Оптимизация на секундных данных."""
        try:
            # Получаем FIGI для символа
            figi = self.multi_analyzer.get_figi_for_symbol(symbol)
            if not figi:
                return {
                    'proceed': False,
                    'reason': f'No FIGI mapping found for symbol {symbol}',
                    'entry_price': stage3_result['entry_price'],
                    'confidence': 0.0
                }
            
            # Получаем секундные данные из таблицы data_1sec
            second_data = self._get_data_from_db(symbol, '1s')
            
            if second_data.empty:
                # Если секундные данные недоступны, используем минутные данные
                return {
                    'proceed': True,
                    'reason': 'Second data not available, using minute data',
                    'entry_price': stage3_result['entry_price'],
                    'confidence': stage3_result['confidence'] * 0.9,  # Немного снижаем уверенность
                    'execution_quality': 'MEDIUM',
                    'timing_score': 0.7,
                    'bid_ask_spread': 0.0
                }
            
            # Анализируем микро-оптимизацию
            micro_analysis = self._analyze_second_optimization(second_data, stage3_result)
            
            # Проверяем требования этапа
            config = self.stage_configs['1s']
            required_confirmations = config['required_confirmations']
            
            # Проверяем подтверждения
            has_good_execution = micro_analysis['execution_quality'] in ['HIGH', 'MEDIUM']
            
            confirmations = {
                'execution_quality': has_good_execution
            }
            
            # Проверяем наличие всех требуемых подтверждений
            missing_confirmations = [conf for conf in required_confirmations if not confirmations.get(conf, False)]
            
            if missing_confirmations:
                return {
                    'proceed': False,
                    'reason': f'Missing confirmations: {missing_confirmations}',
                    'entry_price': micro_analysis['entry_price'],
                    'confidence': micro_analysis['confidence'],
                    'confirmations': confirmations
                }
            
            # Проверяем минимальную уверенность
            if micro_analysis['confidence'] < config['min_confidence']:
                return {
                    'proceed': False,
                    'reason': f'Second confidence too low: {micro_analysis["confidence"]:.2f} < {config["min_confidence"]}',
                    'entry_price': micro_analysis['entry_price'],
                    'confidence': micro_analysis['confidence'],
                    'confirmations': confirmations
                }
            
            return {
                'proceed': True,
                'reason': 'Second optimization completed',
                'entry_price': micro_analysis['entry_price'],
                'confidence': micro_analysis['confidence'],
                'confirmations': confirmations,
                'execution_quality': micro_analysis['execution_quality'],
                'timing_score': micro_analysis['timing_score'],
                'bid_ask_spread': micro_analysis['bid_ask_spread']
            }
            
        except Exception as e:
            logger.error(f"Error in stage 1s analysis for {symbol}: {e}")
            return {
                'proceed': False,
                'reason': f'Stage 1s error: {str(e)}',
                'entry_price': stage3_result['entry_price'],
                'confidence': 0.0
            }
    
    def _analyze_hourly_trend(self, hourly_data: pd.DataFrame, daily_signal: str) -> Dict[str, Any]:
        """Анализ тренда на часовых данных."""
        try:
            if len(hourly_data) < 24:  # Минимум 24 часа
                return {
                    'trend': 'UNKNOWN',
                    'trend_aligned': False,
                    'confidence': 0.0,
                    'volume_confirmation': False,
                    'support_level': 0.0,
                    'resistance_level': 0.0,
                    'volume_trend': 'UNKNOWN'
                }
            
            # Анализируем тренд
            recent_data = hourly_data.tail(24)  # Последние 24 часа
            
            # Простой анализ тренда по скользящим средним
            recent_data['MA_8'] = recent_data['close'].rolling(window=8, min_periods=1).mean()
            recent_data['MA_24'] = recent_data['close'].rolling(window=24, min_periods=1).mean()
            
            current_price = recent_data['close'].iloc[-1]
            ma_8 = recent_data['MA_8'].iloc[-1]
            ma_24 = recent_data['MA_24'].iloc[-1]
            
            # Определяем тренд
            if ma_8 > ma_24 and current_price > ma_8:
                trend = 'UP'
            elif ma_8 < ma_24 and current_price < ma_8:
                trend = 'DOWN'
            else:
                trend = 'SIDEWAYS'
            
            # Проверяем согласованность с дневным сигналом
            if daily_signal == 'BUY' and trend in ['UP', 'SIDEWAYS']:
                trend_aligned = True
            elif daily_signal == 'SELL' and trend in ['DOWN', 'SIDEWAYS']:
                trend_aligned = True
            else:
                trend_aligned = False
            
            # Анализируем объем
            avg_volume = recent_data['volume'].mean()
            recent_volume = recent_data['volume'].tail(4).mean()  # Последние 4 часа
            volume_spike = recent_volume > avg_volume * 1.2
            
            volume_confirmation = volume_spike if trend_aligned else False
            
            # Определяем уровни поддержки и сопротивления
            support_level = recent_data['low'].min()
            resistance_level = recent_data['high'].max()
            
            # Анализируем тренд объема
            volume_trend = 'INCREASING' if recent_volume > avg_volume else 'DECREASING'
            
            # Рассчитываем уверенность
            confidence = 0.5
            if trend_aligned:
                confidence += 0.2
            if volume_confirmation:
                confidence += 0.2
            if abs(current_price - ma_8) / ma_8 < 0.02:  # Близко к MA
                confidence += 0.1
            
            return {
                'trend': trend,
                'trend_aligned': trend_aligned,
                'confidence': min(0.9, confidence),
                'volume_confirmation': volume_confirmation,
                'support_level': support_level,
                'resistance_level': resistance_level,
                'volume_trend': volume_trend
            }
            
        except Exception as e:
            logger.error(f"Error analyzing hourly trend: {e}")
            return {
                'trend': 'UNKNOWN',
                'trend_aligned': False,
                'confidence': 0.0,
                'volume_confirmation': False,
                'support_level': 0.0,
                'resistance_level': 0.0,
                'volume_trend': 'UNKNOWN'
            }
    
    def _analyze_minute_entry(self, minute_data: pd.DataFrame, daily_signal: str, hourly_result: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ точек входа на минутных данных."""
        try:
            if len(minute_data) < 60:  # Минимум 1 час минутных данных
                return {
                    'entry_price': 0.0,
                    'stop_loss': 0.0,
                    'take_profit': 0.0,
                    'risk_reward': 0.0,
                    'confidence': 0.0,
                    'entry_reason': 'INSUFFICIENT_DATA',
                    'volume_spike': False
                }
            
            recent_data = minute_data.tail(60)  # Последний час
            
            current_price = recent_data['close'].iloc[-1]
            support_level = hourly_result.get('support_level', recent_data['low'].min())
            resistance_level = hourly_result.get('resistance_level', recent_data['high'].max())
            
            # Ищем точку входа в зависимости от сигнала
            if daily_signal == 'BUY':
                # Для покупки ищем отскок от поддержки или пробой сопротивления
                if current_price <= support_level * 1.01:  # В пределах 1% от поддержки
                    entry_price = support_level
                    entry_reason = 'SUPPORT_BOUNCE'
                    stop_loss = support_level * 0.98  # 2% ниже поддержки
                    take_profit = resistance_level
                elif current_price >= resistance_level * 0.99:  # Пробой сопротивления
                    entry_price = resistance_level
                    entry_reason = 'BREAKOUT'
                    stop_loss = support_level
                    take_profit = resistance_level * 1.05  # 5% выше сопротивления
                else:
                    entry_price = current_price
                    entry_reason = 'CURRENT_PRICE'
                    stop_loss = support_level
                    take_profit = resistance_level
            else:  # SELL
                # Для продажи ищем отскок от сопротивления или пробой поддержки
                if current_price >= resistance_level * 0.99:  # В пределах 1% от сопротивления
                    entry_price = resistance_level
                    entry_reason = 'RESISTANCE_REJECTION'
                    stop_loss = resistance_level * 1.02  # 2% выше сопротивления
                    take_profit = support_level
                elif current_price <= support_level * 1.01:  # Пробой поддержки
                    entry_price = support_level
                    entry_reason = 'BREAKDOWN'
                    stop_loss = resistance_level
                    take_profit = support_level * 0.95  # 5% ниже поддержки
                else:
                    entry_price = current_price
                    entry_reason = 'CURRENT_PRICE'
                    stop_loss = resistance_level
                    take_profit = support_level
            
            # Рассчитываем соотношение риск/доходность
            if daily_signal == 'BUY':
                risk = abs(entry_price - stop_loss)
                reward = abs(take_profit - entry_price)
            else:  # SELL
                risk = abs(stop_loss - entry_price)
                reward = abs(entry_price - take_profit)
            
            risk_reward = reward / risk if risk > 0 else 0
            
            # Проверяем объем
            avg_volume = recent_data['volume'].mean()
            recent_volume = recent_data['volume'].tail(10).mean()  # Последние 10 минут
            volume_spike = recent_volume > avg_volume * 1.5
            
            # Рассчитываем уверенность
            confidence = 0.4
            if risk_reward >= 2.0:
                confidence += 0.3
            if volume_spike:
                confidence += 0.2
            if entry_reason in ['SUPPORT_BOUNCE', 'RESISTANCE_REJECTION']:
                confidence += 0.1
            
            return {
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_reward': risk_reward,
                'confidence': min(0.9, confidence),
                'entry_reason': entry_reason,
                'volume_spike': volume_spike
            }
            
        except Exception as e:
            logger.error(f"Error analyzing minute entry: {e}")
            return {
                'entry_price': 0.0,
                'stop_loss': 0.0,
                'take_profit': 0.0,
                'risk_reward': 0.0,
                'confidence': 0.0,
                'entry_reason': 'ERROR',
                'volume_spike': False
            }
    
    def _analyze_second_optimization(self, second_data: pd.DataFrame, minute_result: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ микро-оптимизации на секундных данных."""
        try:
            if len(second_data) < 60:  # Минимум 1 минута секундных данных
                return {
                    'entry_price': minute_result['entry_price'],
                    'confidence': 0.3,
                    'execution_quality': 'LOW',
                    'timing_score': 0.3,
                    'bid_ask_spread': 0.0
                }
            
            recent_data = second_data.tail(60)  # Последняя минута
            
            base_entry = minute_result['entry_price']
            current_price = recent_data['close'].iloc[-1]
            
            # Ищем лучшую точку входа в пределах 0.5% от базовой цены
            price_range = base_entry * 0.005  # 0.5%
            min_price = base_entry - price_range
            max_price = base_entry + price_range
            
            # Если текущая цена в пределах диапазона, используем её
            if min_price <= current_price <= max_price:
                entry_price = current_price
                execution_quality = 'HIGH'
                timing_score = 0.8
            else:
                # Иначе используем ближайшую цену в диапазоне
                if current_price < min_price:
                    entry_price = min_price
                else:
                    entry_price = max_price
                execution_quality = 'MEDIUM'
                timing_score = 0.6
            
            # Симулируем bid/ask spread (обычно 0.1-0.5% для акций)
            bid_ask_spread = base_entry * 0.002  # 0.2%
            
            # Рассчитываем уверенность
            confidence = 0.3
            if execution_quality == 'HIGH':
                confidence += 0.3
            elif execution_quality == 'MEDIUM':
                confidence += 0.2
            
            return {
                'entry_price': entry_price,
                'confidence': confidence,
                'execution_quality': execution_quality,
                'timing_score': timing_score,
                'bid_ask_spread': bid_ask_spread
            }
            
        except Exception as e:
            logger.error(f"Error analyzing second optimization: {e}")
            return {
                'entry_price': minute_result['entry_price'],
                'confidence': 0.3,
                'execution_quality': 'LOW',
                'timing_score': 0.3,
                'bid_ask_spread': 0.0
            }
    
    def _calculate_final_confidence(self, stage1: Dict[str, Any], stage2: Dict[str, Any], stage3: Dict[str, Any], stage4: Dict[str, Any]) -> float:
        """Рассчитать финальную уверенность на основе всех этапов."""
        try:
            # Взвешенная уверенность по этапам
            weights = {
                '1d': 0.4,  # ML сигналы - самый важный
                '1h': 0.3,  # Подтверждение тренда
                '1m': 0.2,  # Точка входа
                '1s': 0.1   # Микро-оптимизация
            }
            
            weighted_confidence = (
                stage1.get('confidence', 0.0) * weights['1d'] +
                stage2.get('confidence', 0.0) * weights['1h'] +
                stage3.get('confidence', 0.0) * weights['1m'] +
                stage4.get('confidence', 0.0) * weights['1s']
            )
            
            return min(0.95, max(0.0, weighted_confidence))
            
        except Exception as e:
            logger.error(f"Error calculating final confidence: {e}")
            return 0.0
    
    def _is_trading_hours(self) -> bool:
        """Проверить, находимся ли в торговые часы."""
        try:
            now = datetime.now()
            current_hour = now.hour
            start_hour = self.auto_trade_config['trading_hours']['start']
            end_hour = self.auto_trade_config['trading_hours']['end']
            
            return start_hour <= current_hour <= end_hour
        except Exception:
            return True  # По умолчанию разрешаем торговлю
    
    async def analyze_multiple_symbols(self, symbols: List[str]) -> List[CascadeSignalResult]:
        """Анализ нескольких символов."""
        results = []
        
        for symbol in symbols:
            try:
                # Получаем предварительный ML результат для символа
                initial_ml_result = self.initial_ml_cache.get(symbol, {})
                
                # Выполняем каскадный анализ
                result = await self.analyze_symbol_cascade(symbol, initial_ml_result)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing symbol {symbol}: {e}")
                # Создаем результат с ошибкой
                error_result = CascadeSignalResult()
                error_result.symbol = symbol
                error_result.rejected_at_stage = 'error'
                error_result.rejection_reason = str(e)
                results.append(error_result)
        
        return results
    
    def get_successful_signals(self, results: List[CascadeSignalResult]) -> List[CascadeSignalResult]:
        """Получить только успешные сигналы."""
        return [result for result in results if result.final_signal is not None]
    
    def get_rejected_signals(self, results: List[CascadeSignalResult]) -> List[CascadeSignalResult]:
        """Получить только отклоненные сигналы."""
        return [result for result in results if result.final_signal is None]
    
    async def execute_auto_trade(self, result: CascadeSignalResult, conn) -> Dict[str, Any]:
        """Выполнить автоматическую сделку на демо-счете."""
        try:
            if not result.auto_trade_enabled or not self.demo_trading:
                return {'success': False, 'reason': 'Auto trading not enabled or demo trading not available'}
            
            # Рассчитываем размер позиции
            account_snapshot = self.demo_trading.get_account_snapshot(conn)
            balance = account_snapshot.get('balance', 0)
            
            # Максимальный размер позиции
            max_position_value = min(
                self.auto_trade_config['max_position_size'],
                balance * self.auto_trade_config['risk_per_trade']
            )
            
            # Количество акций
            quantity = int(max_position_value / result.entry_price)
            
            if quantity <= 0:
                return {'success': False, 'reason': 'Insufficient balance for trade'}
            
            # Выполняем сделку
            trade_result = self.demo_trading.place_trade(
                conn, 
                result.symbol, 
                result.final_signal, 
                quantity, 
                result.entry_price
            )
            
            if trade_result.status == "success":
                logger.info(f"Auto trade executed: {result.symbol} {result.final_signal} {quantity} @ {result.entry_price}")
                return {
                    'success': True,
                    'symbol': result.symbol,
                    'side': result.final_signal,
                    'quantity': quantity,
                    'price': result.entry_price,
                    'balance': trade_result.balance
                }
            else:
                return {'success': False, 'reason': trade_result.message}
                
        except Exception as e:
            logger.error(f"Error executing auto trade for {result.symbol}: {e}")
            return {'success': False, 'reason': str(e)}
    
    def update_auto_trade_config(self, config_updates: Dict[str, Any]):
        """Обновить настройки автоматической торговли."""
        self.auto_trade_config.update(config_updates)
        logger.info(f"Auto trade config updated: {config_updates}")
    
    def get_auto_trade_status(self) -> Dict[str, Any]:
        """Получить статус автоматической торговли."""
        return {
            'enabled': self.auto_trade_config['enabled'],
            'min_confidence': self.auto_trade_config['min_confidence'],
            'max_position_size': self.auto_trade_config['max_position_size'],
            'risk_per_trade': self.auto_trade_config['risk_per_trade'],
            'max_daily_trades': self.auto_trade_config['max_daily_trades'],
            'trading_hours': self.auto_trade_config['trading_hours'],
            'is_trading_hours': self._is_trading_hours()
        }
    
    def _get_data_from_db(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Получить данные из базы данных для указанного таймфрейма."""
        try:
            print(f"🔍 [GET_DATA] Получаем данные для {symbol} ({timeframe})...")
            from core.database import get_connection
            from core.multi_timeframe_db import get_timeframe_data
            
            print(f"🔍 [GET_DATA] Подключаемся к базе данных...")
            conn = get_connection()
            
            # Пытаемся получить данные из специализированных таблиц
            if timeframe in ['1h', '1m', '5m', '15m', '1s', 'tick']:
                data = get_timeframe_data(conn, symbol, timeframe, limit=1000)
                if not data.empty:
                    # Переименовываем колонки для совместимости
                    data = data.rename(columns={'datetime': 'time'})
                    print(f"✅ [GET_DATA] {symbol} ({timeframe}): Получено {len(data)} записей из специализированной таблицы")
                    conn.close()
                    return data
                else:
                    print(f"⚠️ [GET_DATA] {symbol} ({timeframe}): Специализированная таблица пуста")
            
            # Для дневных данных пытаемся получить из data_1d или daily_data
            if timeframe == '1d':
                # Сначала пробуем data_1d
                try:
                    data = get_timeframe_data(conn, symbol, '1d', limit=365)
                    if not data.empty:
                        data = data.rename(columns={'datetime': 'time'})
                        conn.close()
                        return data
                except Exception:
                    pass
                
                # Если не получилось, пробуем daily_data через StockAnalyzer
                if self.multi_analyzer.base_analyzer:
                    figi = self.multi_analyzer.get_figi_for_symbol(symbol)
                    if figi:
                        data = self.multi_analyzer.base_analyzer.get_stock_data(figi)
                        conn.close()
                        return data
                
                # Если не получилось, пробуем получить из data_1d напрямую
                try:
                    print(f"🔍 [GET_DATA] {symbol} ({timeframe}): Пробуем получить из data_1d напрямую...")
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT datetime as time, open, high, low, close, volume
                        FROM data_1d
                        WHERE symbol = ?
                        ORDER BY datetime DESC
                        LIMIT 365
                    """, (symbol,))
                    
                    rows = cursor.fetchall()
                    if rows:
                        data = pd.DataFrame(rows, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                        data['time'] = pd.to_datetime(data['time'])
                        print(f"✅ [GET_DATA] {symbol} ({timeframe}): Получено {len(data)} записей из data_1d")
                        conn.close()
                        return data
                    else:
                        print(f"⚠️ [GET_DATA] {symbol} ({timeframe}): data_1d пуста")
                except Exception:
                    pass
                
                # Если не получилось, пробуем получить из daily_data напрямую
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT dd.date as time, dd.open, dd.high, dd.low, dd.close, dd.volume
                        FROM daily_data dd
                        JOIN companies c ON dd.company_id = c.id
                        WHERE c.contract_code = ?
                        ORDER BY dd.date DESC
                        LIMIT 365
                    """, (symbol,))
                    
                    rows = cursor.fetchall()
                    if rows:
                        data = pd.DataFrame(rows, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                        data['time'] = pd.to_datetime(data['time'])
                        conn.close()
                        return data
                except Exception:
                    pass
            
            print(f"❌ [GET_DATA] {symbol} ({timeframe}): Не удалось получить данные из базы")
            conn.close()
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
            
        except Exception as e:
            print(f"❌ [GET_DATA] {symbol} ({timeframe}): Ошибка получения данных - {e}")
            logger.error(f"Error getting {timeframe} data for {symbol} from DB: {e}")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
    
    def get_available_symbols_with_1d_data(self, min_volume: float = 10000000, min_avg_volume: float = 5000000) -> List[str]:
        """
        Получить список символов с доступными данными 1d и достаточным денежным объемом торгов.
        
        Args:
            min_volume: Минимальный денежный объем торгов за последний день (RUB)
            min_avg_volume: Минимальный средний денежный объем торгов за последние 30 дней (RUB)
            
        Returns:
            List[str]: Список отфильтрованных символов
        """
        try:
            print("🔍 [GET_SYMBOLS] Начинаем получение символов с данными 1d и фильтрацией по объему...")
            print(f"📊 [GET_SYMBOLS] Минимальный объем за день: {min_volume:,.0f}")
            print(f"📊 [GET_SYMBOLS] Минимальный средний объем за 30 дней: {min_avg_volume:,.0f}")
            
            from core.database import get_connection
            
            print("🔍 [GET_SYMBOLS] Подключаемся к базе данных...")
            conn = get_connection()
            cursor = conn.cursor()
            
            # Получаем символы с данными и денежным объемом торгов (volume * close)
            print("🔍 [GET_SYMBOLS] Выполняем SQL запрос с фильтрацией по денежному объему...")
            cursor.execute("""
                SELECT 
                    symbol,
                    COUNT(*) as data_count,
                    AVG(volume * close) as avg_money_volume,
                    MAX(volume * close) as max_money_volume,
                    (SELECT volume * close FROM data_1d d2 
                     WHERE d2.symbol = data_1d.symbol 
                     ORDER BY d2.datetime DESC LIMIT 1) as last_money_volume
                FROM data_1d
                WHERE datetime >= date(
                    (SELECT MAX(datetime) FROM data_1d), '-30 days'
                )
                GROUP BY symbol
                HAVING data_count >= 10
                ORDER BY avg_money_volume DESC
            """)
            
            print("🔍 [GET_SYMBOLS] Получаем результаты запроса...")
            results = cursor.fetchall()
            print(f"📊 [GET_SYMBOLS] SQL запрос вернул {len(results)} строк")
            
            # Фильтруем по денежному объему
            filtered_symbols = []
            volume_stats = []
            
            for row in results:
                symbol, data_count, avg_money_volume, max_money_volume, last_money_volume = row
                
                # Проверяем условия фильтрации по денежному объему
                if (last_money_volume >= min_volume and 
                    avg_money_volume >= min_avg_volume):
                    filtered_symbols.append(symbol)
                    volume_stats.append({
                        'symbol': symbol,
                        'data_count': data_count,
                        'avg_money_volume': avg_money_volume,
                        'max_money_volume': max_money_volume,
                        'last_money_volume': last_money_volume
                    })
                else:
                    print(f"  ❌ {symbol}: денежный объем {last_money_volume:,.0f} RUB (средний: {avg_money_volume:,.0f} RUB) - не прошел фильтр")
            
            print(f"📈 [GET_SYMBOLS] Извлечено {len(results)} символов, отфильтровано {len(filtered_symbols)}")
            
            if filtered_symbols:
                print(f"📋 [GET_SYMBOLS] Первые 5 отфильтрованных символов: {filtered_symbols[:5]}")
                
                # Показываем статистику по денежному объему
                if volume_stats:
                    top_volume = max(volume_stats, key=lambda x: x['avg_money_volume'])
                    print(f"📊 [GET_SYMBOLS] Топ по денежному объему: {top_volume['symbol']} (средний: {top_volume['avg_money_volume']:,.0f} RUB)")
            else:
                print("⚠️ [GET_SYMBOLS] Нет символов, прошедших фильтрацию по объему!")
            
            conn.close()
            print("✅ [GET_SYMBOLS] Соединение с базой данных закрыто")
            
            return filtered_symbols
            
        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
            return []
    
    async def analyze_all_available_symbols(self, min_volume: float = 10000000, 
                                          min_avg_volume: float = 5000000,
                                          use_db_cache: bool = True) -> List[CascadeSignalResult]:
        """
        Автоматический каскадный анализ всех доступных символов.
        
        Args:
            min_volume: Минимальный денежный объем за день (RUB)
            min_avg_volume: Минимальный средний денежный объем за 30 дней (RUB)
            use_db_cache: Использовать ли БД кэш для ML результатов
        
        Workflow:
        1. Получаем все доступные символы с данными 1d
        2. Выполняем предварительный ML анализ для всех символов
        3. Запускаем каскадный анализ только для символов с сильными ML сигналами
        
        Returns:
            List[CascadeSignalResult]: Результаты каскадного анализа
        """
        try:
            print("🔍 [CASCADE_CORE] Начинаем автоматический каскадный анализ...")
            print(f"🔍 [CASCADE_CORE] Параметры фильтрации: min_volume={min_volume}, min_avg_volume={min_avg_volume}")
            print(f"🔍 [CASCADE_CORE] Использование БД кэша: {use_db_cache}")
            logger.info("Starting automatic cascade analysis for all available symbols")
            
            # Получаем все доступные символы с данными 1d и фильтрацией по объему
            print("📊 [CASCADE_CORE] Получаем доступные символы с данными 1d и фильтрацией по объему...")
            print("🔍 [CASCADE_CORE] Вызываем get_available_symbols_with_1d_data() с фильтрацией...")
            available_symbols = self.get_available_symbols_with_1d_data(min_volume=min_volume, min_avg_volume=min_avg_volume)
            print(f"📈 [CASCADE_CORE] get_available_symbols_with_1d_data() вернул {len(available_symbols)} символов после фильтрации")
            print(f"📋 [CASCADE_CORE] Тип результата: {type(available_symbols)}")
            if available_symbols:
                print(f"📋 [CASCADE_CORE] Первые 5 символов: {available_symbols[:5]}")
            else:
                print("⚠️ [CASCADE_CORE] available_symbols пустой!")
            
            if not available_symbols:
                print("⚠️ [CASCADE_CORE] Нет символов с данными 1d")
                logger.warning("No symbols with 1d data available")
                return []
            
            # Показываем первые несколько символов
            if len(available_symbols) <= 10:
                print(f"📋 [CASCADE_CORE] Символы: {', '.join(available_symbols)}")
            else:
                print(f"📋 [CASCADE_CORE] Символы (первые 10): {', '.join(available_symbols[:10])} ... и еще {len(available_symbols) - 10}")
            
            # Выполняем предварительный ML анализ для всех символов
            print("🤖 [CASCADE_CORE] Выполняем предварительный ML анализ...")
            logger.info("Performing initial ML analysis...")
            initial_ml_results = await self.perform_initial_ml_analysis(
                symbols=available_symbols,
                min_volume=min_volume,
                min_avg_volume=min_avg_volume,
                use_db_cache=use_db_cache
            )
            print(f"✅ [CASCADE_CORE] ML анализ завершен для {len(initial_ml_results)} символов")
            
            # Фильтруем символы с сильными ML сигналами
            print("🔍 [CASCADE_CORE] Фильтруем символы с сильными ML сигналами...")
            strong_signal_symbols = []
            for symbol, ml_result in initial_ml_results.items():
                ensemble_signal = ml_result.get('ml_ensemble_signal', 'HOLD')
                confidence = ml_result.get('ml_price_confidence', 0.0)
                
                print(f"  📊 {symbol}: {ensemble_signal} (уверенность: {confidence:.1%})")
                
                # Проверяем, что сигнал достаточно сильный для каскадного анализа
                if (ensemble_signal in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL'] and 
                    confidence >= 0.5):
                    strong_signal_symbols.append(symbol)
                    print(f"  ✅ {symbol} - сильный сигнал, добавляем в каскадный анализ")
                else:
                    print(f"  ❌ {symbol} - слабый сигнал, пропускаем")
            
            print(f"🎯 [CASCADE_CORE] Найдено {len(strong_signal_symbols)} символов с сильными ML сигналами")
            logger.info(f"Found {len(strong_signal_symbols)} symbols with strong ML signals")
            
            if not strong_signal_symbols:
                print("⚠️ [CASCADE_CORE] Нет символов с сильными ML сигналами")
                logger.warning("No symbols with strong ML signals found")
                return []
            
            # Показываем символы для каскадного анализа
            print(f"🚀 [CASCADE_CORE] Символы для каскадного анализа: {', '.join(strong_signal_symbols)}")
            
            # Запускаем каскадный анализ для символов с сильными сигналами
            print("⚡ [CASCADE_CORE] Запускаем каскадный анализ...")
            logger.info("Starting cascade analysis for strong signal symbols...")
            results = []
            
            for i, symbol in enumerate(strong_signal_symbols):
                print(f"🔄 [CASCADE_CORE] Анализируем {symbol} ({i+1}/{len(strong_signal_symbols)})...")
                try:
                    initial_ml_result = initial_ml_results[symbol]
                    result = await self.analyze_symbol_cascade(symbol, initial_ml_result)
                    results.append(result)
                    
                    if result.final_signal:
                        print(f"  ✅ {symbol}: {result.final_signal} (уверенность: {result.confidence:.1%})")
                    else:
                        print(f"  ❌ {symbol}: отклонен на этапе {result.rejected_at_stage} - {result.rejection_reason}")
                        
                except Exception as e:
                    print(f"  💥 {symbol}: ошибка - {e}")
                    logger.error(f"Error in cascade analysis for {symbol}: {e}")
                    # Создаем результат с ошибкой
                    error_result = CascadeSignalResult()
                    error_result.symbol = symbol
                    error_result.rejected_at_stage = 'error'
                    error_result.rejection_reason = str(e)
                    results.append(error_result)
            
            successful_count = len([r for r in results if r.final_signal])
            rejected_count = len([r for r in results if not r.final_signal])
            
            print(f"🎉 [CASCADE_CORE] Каскадный анализ завершен!")
            print(f"  📊 Всего проанализировано: {len(results)}")
            print(f"  ✅ Успешных сигналов: {successful_count}")
            print(f"  ❌ Отклоненных сигналов: {rejected_count}")
            
            logger.info(f"Cascade analysis completed for {len(results)} symbols")
            return results
            
        except Exception as e:
            print(f"💥 [CASCADE_CORE] Критическая ошибка: {e}")
            logger.error(f"Error in automatic cascade analysis: {e}")
            return []

    async def get_analysis_status(self, min_volume: float = 10000000, min_avg_volume: float = 5000000) -> Dict[str, Any]:
        """
        Получить статус анализа: количество доступных символов, 
        количество с сильными ML сигналами и т.д.
        
        Args:
            min_volume: Минимальный денежный объем торгов за последний день (RUB)
            min_avg_volume: Минимальный средний денежный объем торгов за последние 30 дней (RUB)
        
        Returns:
            Dict[str, Any]: Статус анализа
        """
        try:
            # Получаем все доступные символы с фильтрацией
            available_symbols = self.get_available_symbols_with_1d_data(min_volume, min_avg_volume)
            
            # Получаем кэшированные ML результаты
            ml_results = self.initial_ml_cache
            
            # Подсчитываем символы с сильными сигналами
            strong_signal_count = 0
            for symbol, ml_result in ml_results.items():
                ensemble_signal = ml_result.get('ml_ensemble_signal', 'HOLD')
                confidence = ml_result.get('ml_price_confidence', 0.0)
                
                if (ensemble_signal in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL'] and 
                    confidence >= 0.5):
                    strong_signal_count += 1
            
            return {
                'total_symbols_with_1d_data': len(available_symbols),
                'symbols_with_ml_results': len(ml_results),
                'symbols_with_strong_signals': strong_signal_count,
                'ml_analysis_completed': len(ml_results) > 0,
                'ready_for_cascade': strong_signal_count > 0,
                'filter_min_volume': min_volume,
                'filter_min_avg_volume': min_avg_volume
            }
            
        except Exception as e:
            logger.error(f"Error getting analysis status: {e}")
            return {
                'total_symbols_with_1d_data': 0,
                'symbols_with_ml_results': 0,
                'symbols_with_strong_signals': 0,
                'ml_analysis_completed': False,
                'ready_for_cascade': False,
                'filter_min_volume': min_volume,
                'filter_min_avg_volume': min_avg_volume,
                'error': str(e)
            }

    def estimate_ml_analysis_time(self, symbols_count: int) -> Dict[str, Any]:
        """
        Оценить время выполнения ML анализа.
        
        Args:
            symbols_count: Количество символов для анализа
            
        Returns:
            Dict[str, Any]: Оценка времени и статистика
        """
        try:
            # Базовое время на символ (в секундах)
            base_time_per_symbol = 2.0  # 2 секунды на символ
            
            # Время инициализации ML моделей
            initialization_time = 5.0
            
            # Общее время
            total_seconds = initialization_time + (symbols_count * base_time_per_symbol)
            
            # Конвертируем в минуты и секунды
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            
            # Форматируем время
            if minutes > 0:
                time_str = f"{minutes}м {seconds}с"
            else:
                time_str = f"{seconds}с"
            
            return {
                'total_seconds': total_seconds,
                'formatted_time': time_str,
                'symbols_count': symbols_count,
                'time_per_symbol': base_time_per_symbol,
                'initialization_time': initialization_time
            }
            
        except Exception as e:
            logger.error(f"Error estimating ML analysis time: {e}")
            return {
                'total_seconds': 0,
                'formatted_time': "Неизвестно",
                'symbols_count': symbols_count,
                'time_per_symbol': 0,
                'initialization_time': 0
            }

    async def perform_initial_ml_analysis(self, symbols: List[str], 
                                        min_volume: float = 10000000, 
                                        min_avg_volume: float = 5000000,
                                        use_db_cache: bool = True) -> Dict[str, Any]:
        """Выполнить первый ML анализ по таблице data_1d для всех символов.
        
        Args:
            symbols: Список символов для анализа
            min_volume: Минимальный объем фильтрации
            min_avg_volume: Минимальный средний объем фильтрации
            use_db_cache: Использовать ли БД кэш для сохранения/загрузки результатов
            
        Returns:
            Словарь с результатами ML анализа
        """
        try:
            print(f"🤖 [ML_ANALYSIS] Начинаем ML анализ для {len(symbols)} символов...")
            print(f"🔍 [ML_ANALYSIS] Тип symbols: {type(symbols)}")
            print(f"🔍 [ML_ANALYSIS] Длина symbols: {len(symbols) if symbols else 'None'}")
            if symbols:
                print(f"🔍 [ML_ANALYSIS] Первые 5 символов: {symbols[:5]}")
            
            # Проверяем БД кэш если включен
            if use_db_cache:
                print(f"🔍 [ML_ANALYSIS] Проверяем БД кэш...")
                cached_data = cascade_ml_cache.get_ml_results(symbols, min_volume, min_avg_volume)
                if cached_data:
                    print(f"✅ [ML_ANALYSIS] Найдены кэшированные ML результаты: {cached_data['results_count']} символов")
                    print(f"📅 [ML_ANALYSIS] Кэш создан: {cached_data.get('created_at', 'неизвестно')}")
                    return cached_data['ml_results']
                else:
                    print(f"🔍 [ML_ANALYSIS] Кэш не найден или устарел, выполняем новый анализ")
            
            if not self.ml_manager:
                print("⚠️ [ML_ANALYSIS] ML менеджер недоступен, используем fallback режим")
                logger.warning("ML manager not available for initial analysis")
                return {}
            
            print(f"✅ [ML_ANALYSIS] ML менеджер доступен: {type(self.ml_manager)}")
            
            from core.ml.signals import MLSignalGenerator
            signal_generator = MLSignalGenerator(self.ml_manager)
            
            ml_results = {}
            successful_count = 0
            failed_count = 0
            
            for i, symbol in enumerate(symbols):
                print(f"🔄 [ML_ANALYSIS] Анализируем {symbol} ({i+1}/{len(symbols)})...")
                try:
                    # Генерируем ML сигналы для символа
                    signals = await signal_generator.generate_ml_signals(symbol)
                    if 'error' not in signals:
                        ml_results[symbol] = signals
                        successful_count += 1
                        
                        # Показываем результат ML анализа
                        ensemble_signal = signals.get('ml_ensemble_signal', 'HOLD')
                        confidence = signals.get('ml_price_confidence', 0.0)
                        print(f"  ✅ {symbol}: {ensemble_signal} (уверенность: {confidence:.1%})")
                        
                        logger.info(f"ML analysis completed for {symbol}")
                    else:
                        failed_count += 1
                        error_msg = signals.get('error', 'Unknown error')
                        print(f"  ❌ {symbol}: Ошибка ML анализа - {error_msg}")
                        logger.warning(f"ML analysis failed for {symbol}: {error_msg}")
                except Exception as e:
                    failed_count += 1
                    print(f"  💥 {symbol}: Исключение ML анализа - {e}")
                    logger.warning(f"ML analysis error for {symbol}: {e}")
                    continue
            
            # Кэшируем результаты
            print(f"💾 [ML_ANALYSIS] Сохраняем результаты в кэш...")
            print(f"💾 [ML_ANALYSIS] Размер результатов до сохранения: {len(ml_results)}")
            print(f"💾 [ML_ANALYSIS] Размер кэша до сохранения: {len(self.initial_ml_cache)}")
            
            self.initial_ml_cache = ml_results
            
            # Сохраняем в БД кэш если включен
            if use_db_cache and ml_results:
                print(f"💾 [ML_ANALYSIS] Сохраняем результаты в БД кэш...")
                cache_saved = cascade_ml_cache.save_ml_results(
                    symbols=symbols,
                    ml_results=ml_results,
                    min_volume=min_volume,
                    min_avg_volume=min_avg_volume,
                    expires_in_hours=6
                )
                if cache_saved:
                    print(f"✅ [ML_ANALYSIS] Результаты успешно сохранены в БД кэш")
                else:
                    print(f"⚠️ [ML_ANALYSIS] Не удалось сохранить результаты в БД кэш")
            
            print(f"💾 [ML_ANALYSIS] Кэш обновлен!")
            print(f"💾 [ML_ANALYSIS] Размер кэша после сохранения: {len(self.initial_ml_cache)}")
            print(f"💾 [ML_ANALYSIS] Ключи в кэше: {list(self.initial_ml_cache.keys())[:5]}{'...' if len(self.initial_ml_cache) > 5 else ''}")
            
            # Инспектируем кэш после сохранения
            cache_info = self.inspect_ml_cache()
            
            print(f"🎉 [ML_ANALYSIS] ML анализ завершен!")
            print(f"  ✅ Успешно: {successful_count}")
            print(f"  ❌ Ошибок: {failed_count}")
            print(f"  📊 Всего обработано: {len(ml_results)}")
            print(f"  🎯 Сильных сигналов в кэше: {len(cache_info['strong_signals'])}")
            
            logger.info(f"Initial ML analysis completed for {len(ml_results)} symbols")
            return ml_results
            
        except Exception as e:
            print(f"💥 [ML_ANALYSIS] Критическая ошибка ML анализа: {e}")
            logger.error(f"Error in initial ML analysis: {e}")
            return {}

    async def analyze_with_saved_ml_results(self, saved_ml_results: List[Dict[str, Any]], saved_symbols: List[str]) -> List[CascadeSignalResult]:
        """
        Выполнить каскадный анализ с использованием сохраненных ML результатов.
        
        Args:
            saved_ml_results: Список сохраненных ML результатов
            saved_symbols: Список символов, соответствующих результатам
            
        Returns:
            List[CascadeSignalResult]: Результаты каскадного анализа
        """
        try:
            print(f"🔄 [CASCADE_SAVED] Начинаем каскадный анализ с сохраненными ML результатами...")
            print(f"📊 [CASCADE_SAVED] Сохранено {len(saved_ml_results)} ML результатов")
            print(f"📋 [CASCADE_SAVED] Символы: {saved_symbols[:5] if saved_symbols else 'None'}")
            
            # Создаем словарь ML результатов для быстрого поиска
            ml_results_dict = {}
            for i, symbol in enumerate(saved_symbols):
                if i < len(saved_ml_results):
                    ml_results_dict[symbol] = saved_ml_results[i]
            
            print(f"🔍 [CASCADE_SAVED] Создан словарь с {len(ml_results_dict)} ML результатами")
            
            # Обновляем кэш ML результатов
            print(f"💾 [CASCADE_SAVED] Обновляем кэш ML результатов...")
            print(f"💾 [CASCADE_SAVED] Размер кэша до обновления: {len(self.initial_ml_cache)}")
            print(f"💾 [CASCADE_SAVED] Размер новых данных: {len(ml_results_dict)}")
            
            self.initial_ml_cache = ml_results_dict
            print(f"💾 [CASCADE_SAVED] Кэш ML результатов обновлен")
            print(f"💾 [CASCADE_SAVED] Размер кэша после обновления: {len(self.initial_ml_cache)}")
            print(f"💾 [CASCADE_SAVED] Ключи в кэше: {list(self.initial_ml_cache.keys())[:5]}{'...' if len(self.initial_ml_cache) > 5 else ''}")
            
            # Инспектируем кэш после обновления
            cache_info = self.inspect_ml_cache()
            print(f"🔍 [CASCADE_SAVED] Инспекция кэша: {cache_info['cache_size']} элементов, {len(cache_info['strong_signals'])} сильных сигналов")
            
            # Фильтруем символы с сильными ML сигналами
            strong_signal_symbols = []
            for symbol, ml_result in ml_results_dict.items():
                ensemble_signal = ml_result.get('ml_ensemble_signal', 'HOLD')
                confidence = ml_result.get('ml_price_confidence', 0.0)
                
                print(f"  📊 {symbol}: {ensemble_signal} (уверенность: {confidence:.1%})")
                
                # Проверяем, что сигнал достаточно сильный для каскадного анализа
                if (ensemble_signal in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL'] and 
                    confidence >= 0.5):
                    strong_signal_symbols.append(symbol)
                    print(f"  ✅ {symbol} - сильный сигнал, добавляем в каскадный анализ")
                else:
                    print(f"  ❌ {symbol} - слабый сигнал, пропускаем")
            
            print(f"🎯 [CASCADE_SAVED] Найдено {len(strong_signal_symbols)} символов с сильными ML сигналами")
            
            if not strong_signal_symbols:
                print("⚠️ [CASCADE_SAVED] Нет символов с сильными ML сигналами")
                return []
            
            # Запускаем каскадный анализ для символов с сильными сигналами
            print("⚡ [CASCADE_SAVED] Запускаем каскадный анализ...")
            results = []
            
            for i, symbol in enumerate(strong_signal_symbols):
                print(f"🔄 [CASCADE_SAVED] Анализируем {symbol} ({i+1}/{len(strong_signal_symbols)})...")
                try:
                    initial_ml_result = ml_results_dict[symbol]
                    result = await self.analyze_symbol_cascade(symbol, initial_ml_result)
                    results.append(result)
                    
                    if result.final_signal:
                        print(f"  ✅ {symbol}: {result.final_signal} (уверенность: {result.confidence:.1%})")
                    else:
                        print(f"  ❌ {symbol}: отклонен на этапе {result.rejected_at_stage} - {result.rejection_reason}")
                        
                except Exception as e:
                    print(f"  💥 {symbol}: ошибка - {e}")
                    logger.error(f"Error in cascade analysis for {symbol}: {e}")
                    # Создаем результат с ошибкой
                    error_result = CascadeSignalResult()
                    error_result.symbol = symbol
                    error_result.rejected_at_stage = 'error'
                    error_result.rejection_reason = str(e)
                    results.append(error_result)
            
            successful_count = len([r for r in results if r.final_signal])
            rejected_count = len([r for r in results if not r.final_signal])
            
            print(f"🎉 [CASCADE_SAVED] Каскадный анализ с сохраненными ML результатами завершен!")
            print(f"  📊 Всего проанализировано: {len(results)}")
            print(f"  ✅ Успешных сигналов: {successful_count}")
            print(f"  ❌ Отклоненных сигналов: {rejected_count}")
            
            return results
            
        except Exception as e:
            print(f"💥 [CASCADE_SAVED] Критическая ошибка: {e}")
            logger.error(f"Error in analyze_with_saved_ml_results: {e}")
            return []
