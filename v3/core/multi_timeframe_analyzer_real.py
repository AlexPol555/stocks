"""
Real Multi-Timeframe Stock Analyzer with actual WebSocket support.
Реальный анализатор многоуровневых данных с поддержкой реального WebSocket.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import pandas as pd
import streamlit as st

# Попытка импорта Tinkoff API
try:
    from tinkoff.invest import Client, CandleInterval
    from tinkoff.invest.utils import quotation_to_decimal
    TINKOFF_AVAILABLE = True
except ImportError:
    TINKOFF_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Tinkoff API not available. Install with: pip install tinkoff-invest")

# Импорт базового анализатора
try:
    from core.analyzer import StockAnalyzer
except ImportError:
    StockAnalyzer = None
    logger.warning("StockAnalyzer not available")

# Импорт WebSocket провайдера
try:
    from .tinkoff_websocket_provider import TinkoffWebSocketProvider
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("WebSocket provider not available")

logger = logging.getLogger(__name__)


class RealTinkoffDataProvider:
    """Реальный провайдер данных Tinkoff API с поддержкой всех таймфреймов."""
    
    def __init__(self, api_key: str, sandbox: bool = False):
        self.api_key = api_key
        self.sandbox = sandbox
        self.timeframe_mapping = {
            '1d': CandleInterval.CANDLE_INTERVAL_DAY,
            '1h': CandleInterval.CANDLE_INTERVAL_HOUR,
            '1m': CandleInterval.CANDLE_INTERVAL_1_MIN,
            '5m': CandleInterval.CANDLE_INTERVAL_5_MIN,
            '15m': CandleInterval.CANDLE_INTERVAL_15_MIN,
            # Секундные и тиковые данные теперь доступны через WebSocket!
            '1s': 'WEBSOCKET_SECONDS',  # Через WebSocket
            'tick': 'WEBSOCKET_TICKS',  # Через WebSocket
        }
        
        # Периоды данных для каждого таймфрейма
        self.data_periods = {
            '1d': {'days': 365, 'max_candles': 365},      # 1 год
            '1h': {'days': 30, 'max_candles': 720},       # 30 дней * 24 часа
            '1m': {'days': 7, 'max_candles': 10080},      # 7 дней * 24 * 60 минут
            '5m': {'days': 7, 'max_candles': 2016},       # 7 дней * 24 * 12 пятиминуток
            '15m': {'days': 7, 'max_candles': 672},       # 7 дней * 24 * 4 пятнадцатиминутки
            '1s': {'days': 1, 'max_candles': 86400},      # 1 день через WebSocket
            'tick': {'days': 0.1, 'max_candles': 100000}, # 0.1 дня через WebSocket
        }
        
        # WebSocket провайдер для реальных данных
        if WEBSOCKET_AVAILABLE:
            self.websocket_provider = TinkoffWebSocketProvider(api_key, sandbox)
        else:
            self.websocket_provider = None
    
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Получить данные через Tinkoff API или WebSocket."""
        if not TINKOFF_AVAILABLE or not self.api_key:
            logger.warning("Tinkoff API not available")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
        
        try:
            interval = self.timeframe_mapping.get(timeframe)
            
            # Для секундных и тиковых данных используем WebSocket
            if timeframe in ['1s', 'tick']:
                if self.websocket_provider:
                    return self._get_websocket_data(symbol, timeframe)
                else:
                    logger.warning(f"WebSocket provider not available for {timeframe}")
                    return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
            
            if not interval or interval in ['WEBSOCKET_SECONDS', 'WEBSOCKET_TICKS']:
                logger.error(f"Unsupported timeframe: {timeframe}")
                return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
            
            # Получаем период данных
            period_config = self.data_periods.get(timeframe, self.data_periods['1d'])
            
            with Client(self.api_key, sandbox=self.sandbox) as client:
                to_date = datetime.now(timezone.utc)
                from_date = to_date - timedelta(days=period_config['days'])
                
                response = client.market_data.get_candles(
                    figi=symbol,  # В данном контексте symbol это FIGI
                    from_=from_date,
                    to=to_date,
                    interval=interval,
                )
                
                candles = getattr(response, "candles", None) or []
                if not candles:
                    logger.warning(f"No candles returned for {symbol} with timeframe {timeframe}")
                    return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
                
                # Ограничиваем количество свечей
                max_candles = period_config['max_candles']
                if len(candles) > max_candles:
                    candles = candles[-max_candles:]
                
                # Конвертируем в DataFrame
                data = pd.DataFrame({
                    "time": [candle.time for candle in candles],
                    "open": [quotation_to_decimal(candle.open) for candle in candles],
                    "close": [quotation_to_decimal(candle.close) for candle in candles],
                    "high": [quotation_to_decimal(candle.high) for candle in candles],
                    "low": [quotation_to_decimal(candle.low) for candle in candles],
                    "volume": [candle.volume for candle in candles],
                })
                
                logger.info(f"Retrieved {len(data)} candles for {symbol} ({timeframe}) via REST API")
                return data
                
        except Exception as e:
            logger.error(f"Error getting {timeframe} data for {symbol}: {e}")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
    
    def _get_websocket_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Получить данные через WebSocket (асинхронно)."""
        import asyncio
        
        try:
            # Запускаем асинхронную функцию
            loop = asyncio.get_event_loop()
            if timeframe == '1s':
                return loop.run_until_complete(self.websocket_provider.get_historical_seconds(symbol))
            elif timeframe == 'tick':
                return loop.run_until_complete(self.websocket_provider.get_historical_ticks(symbol))
            else:
                return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
                
        except Exception as e:
            logger.error(f"Error getting WebSocket data for {symbol} ({timeframe}): {e}")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
    
    def is_available(self) -> bool:
        """Проверить доступность Tinkoff API."""
        return TINKOFF_AVAILABLE and bool(self.api_key)
    
    def get_websocket_provider(self) -> Optional[TinkoffWebSocketProvider]:
        """Получить WebSocket провайдер."""
        return self.websocket_provider


class RealMultiTimeframeStockAnalyzer:
    """Реальный анализатор для работы с разными таймфреймами с поддержкой реального WebSocket."""
    
    def __init__(self, api_key: Optional[str] = None, db_conn=None, sandbox: bool = False):
        self.api_key = api_key
        self.db_conn = db_conn
        self.sandbox = sandbox
        
        # Создаем базовый анализатор для дневных данных
        if StockAnalyzer:
            self.base_analyzer = StockAnalyzer(
                api_key=self.api_key,
                db_conn=self.db_conn
            )
        else:
            self.base_analyzer = None
        
        # Создаем провайдеры данных
        self.tinkoff_provider = RealTinkoffDataProvider(self.api_key, sandbox) if self.api_key else None
        
        # Маппинг таймфреймов на провайдеры
        self.timeframe_providers = {
            '1d': [self.base_analyzer] if self.base_analyzer else [],
            '1h': [self.tinkoff_provider],
            '1m': [self.tinkoff_provider],
            '5m': [self.tinkoff_provider],
            '15m': [self.tinkoff_provider],
            '1s': [self.tinkoff_provider],  # Теперь реальные данные через WebSocket!
            'tick': [self.tinkoff_provider],  # Теперь реальные данные через WebSocket!
        }
        
        logger.info(f"RealMultiTimeframeStockAnalyzer initialized with real WebSocket support (sandbox: {sandbox})")
    
    def get_stock_data(self, figi: str, timeframe: str = '1d') -> pd.DataFrame:
        """Получить данные акции для указанного таймфрейма."""
        if not figi:
            logger.warning("RealMultiTimeframeStockAnalyzer.get_stock_data called with empty FIGI")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
        
        # Определяем провайдера
        providers = self.timeframe_providers.get(timeframe, [])
        
        for provider in providers:
            if provider and provider.is_available():
                try:
                    data = provider.get_data(figi, timeframe)
                    if not data.empty:
                        logger.info(f"Retrieved {len(data)} records for {figi} ({timeframe}) via {provider.__class__.__name__}")
                        return data
                except Exception as e:
                    logger.error(f"Error getting data from {provider.__class__.__name__}: {e}")
                    continue
        
        logger.warning(f"No data available for {figi} ({timeframe})")
        return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
    
    def get_multiple_timeframes(self, figi: str, timeframes: List[str]) -> Dict[str, pd.DataFrame]:
        """Получить данные для нескольких таймфреймов одновременно."""
        results = {}
        
        for timeframe in timeframes:
            try:
                data = self.get_stock_data(figi, timeframe)
                results[timeframe] = data
                logger.info(f"Retrieved {len(data)} candles for {figi} ({timeframe})")
            except Exception as e:
                logger.error(f"Error getting {timeframe} data for {figi}: {e}")
                results[timeframe] = pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
        
        return results
    
    def get_figi_mapping(self) -> Dict[str, str]:
        """Получить маппинг тикеров на FIGI."""
        if self.base_analyzer and hasattr(self.base_analyzer, 'get_figi_mapping'):
            return self.base_analyzer.get_figi_mapping()
        else:
            # Возвращаем базовый маппинг
            return {
                'SBER': 'BBG004730N88',
                'GAZP': 'BBG004730ZJ9',
                'LKOH': 'BBG004731032',
                'NVTK': 'BBG00475J7X1',
                'ROSN': 'BBG0047315Y7',
                'NLMK': 'BBG004RVFFC0',
                'ALRS': 'BBG004S681W1',
                'MGNT': 'BBG004S68758',
                'YNDX': 'BBG006L8G4H1',
                'VKCO': 'BBG00QPYJ5X0',
            }
    
    def get_available_symbols(self) -> List[str]:
        """Получить список доступных символов."""
        if self.base_analyzer and hasattr(self.base_analyzer, 'get_available_symbols'):
            return self.base_analyzer.get_available_symbols()
        else:
            return list(self.get_figi_mapping().keys())
    
    def get_figi_for_symbol(self, symbol: str) -> Optional[str]:
        """Получить FIGI для символа."""
        return self.get_figi_mapping().get(symbol)
    
    def get_supported_timeframes(self) -> List[str]:
        """Получить список поддерживаемых таймфреймов."""
        return list(self.timeframe_providers.keys())
    
    def get_provider_info(self) -> Dict[str, Dict]:
        """Получить информацию о провайдерах."""
        info = {}
        for timeframe, providers in self.timeframe_providers.items():
            info[timeframe] = []
            for provider in providers:
                if provider:
                    provider_info = {
                        'name': provider.__class__.__name__,
                        'available': provider.is_available()
                    }
                    
                    # Добавляем информацию о WebSocket для секундных и тиковых данных
                    if timeframe in ['1s', 'tick'] and hasattr(provider, 'get_websocket_provider'):
                        ws_provider = provider.get_websocket_provider()
                        if ws_provider:
                            provider_info['websocket_available'] = True
                            provider_info['websocket_connected'] = ws_provider.is_connected()
                        else:
                            provider_info['websocket_available'] = False
                    
                    info[timeframe].append(provider_info)
        return info
    
    def get_websocket_provider(self) -> Optional[TinkoffWebSocketProvider]:
        """Получить WebSocket провайдер."""
        if self.tinkoff_provider:
            return self.tinkoff_provider.get_websocket_provider()
        return None


def get_tinkoff_api_key() -> Optional[str]:
    """Получить API ключ Tinkoff из secrets или session_state."""
    try:
        # Сначала пробуем получить из secrets
        if hasattr(st, 'secrets') and hasattr(st.secrets, 'TINKOFF_API_KEY'):
            return st.secrets.TINKOFF_API_KEY
    except Exception:
        pass
    
    # Затем из session_state
    return st.session_state.get('tinkoff_api_key')


def create_real_multi_timeframe_analyzer(api_key: Optional[str] = None, sandbox: bool = False) -> RealMultiTimeframeStockAnalyzer:
    """Создать реальный анализатор многоуровневых данных."""
    return RealMultiTimeframeStockAnalyzer(api_key, sandbox=sandbox)
