"""
Enhanced Multi-Timeframe Stock Analyzer with support for 1s and tick data.
Расширенный анализатор многоуровневых данных с поддержкой секундных и тиковых данных.
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

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """Абстрактный класс для провайдеров данных."""
    
    @abstractmethod
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Получить данные для символа и таймфрейма."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Проверить доступность провайдера."""
        pass


class TinkoffDataProvider(DataProvider):
    """Провайдер данных Tinkoff API с поддержкой всех таймфреймов."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.timeframe_mapping = {
            '1d': CandleInterval.CANDLE_INTERVAL_DAY,
            '1h': CandleInterval.CANDLE_INTERVAL_HOUR,
            '1m': CandleInterval.CANDLE_INTERVAL_1_MIN,
            '5m': CandleInterval.CANDLE_INTERVAL_5_MIN,
            '15m': CandleInterval.CANDLE_INTERVAL_15_MIN,
            '1s': None,  # Не поддерживается Tinkoff API напрямую
            'tick': None,  # Не поддерживается Tinkoff API напрямую
        }
        
        # Периоды данных для каждого таймфрейма
        self.data_periods = {
            '1d': {'days': 365, 'max_candles': 365},      # 1 год
            '1h': {'days': 30, 'max_candles': 720},       # 30 дней * 24 часа
            '1m': {'days': 7, 'max_candles': 10080},      # 7 дней * 24 * 60 минут
            '5m': {'days': 7, 'max_candles': 2016},       # 7 дней * 24 * 12 пятиминуток
            '15m': {'days': 7, 'max_candles': 672},       # 7 дней * 24 * 4 пятнадцатиминутки
            '1s': {'days': 1, 'max_candles': 86400},      # 1 день * 24 * 60 * 60 секунд (экспериментально)
            'tick': {'days': 0.1, 'max_candles': 100000}, # 0.1 дня (экспериментально)
        }
    
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Получить данные через Tinkoff API."""
        if not TINKOFF_AVAILABLE or not self.api_key:
            logger.warning("Tinkoff API not available")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
        
        try:
            interval = self.timeframe_mapping.get(timeframe)
            
            # Для секундных и тиковых данных используем специальную обработку
            if timeframe in ['1s', 'tick']:
                return self._get_high_frequency_data(symbol, timeframe)
            
            if not interval:
                logger.error(f"Unsupported timeframe: {timeframe}")
                return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
            
            # Получаем период данных
            period_config = self.data_periods.get(timeframe, self.data_periods['1d'])
            
            with Client(self.api_key) as client:
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
                
                logger.info(f"Retrieved {len(data)} candles for {symbol} ({timeframe})")
                return data
                
        except Exception as e:
            logger.error(f"Error getting {timeframe} data for {symbol}: {e}")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
    
    def _get_high_frequency_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Получить данные высокой частоты (секундные и тиковые)."""
        logger.info(f"Getting high-frequency data for {symbol} ({timeframe})")
        
        if timeframe == '1s':
            # Для секундных данных получаем минутные данные и разбиваем их
            return self._get_second_data_from_minutes(symbol)
        elif timeframe == 'tick':
            # Для тиковых данных получаем последние торговые данные
            return self._get_tick_data(symbol)
        else:
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
    
    def _get_second_data_from_minutes(self, symbol: str) -> pd.DataFrame:
        """Получить секундные данные из минутных (симуляция)."""
        try:
            # Получаем минутные данные
            minute_data = self.get_data(symbol, '1m')
            
            if minute_data.empty:
                return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
            
            # Симулируем секундные данные из минутных
            second_data = []
            for _, row in minute_data.iterrows():
                minute_time = row['time']
                for second in range(60):  # 60 секунд в минуте
                    second_time = minute_time + timedelta(seconds=second)
                    # Простая симуляция: равномерное распределение цены
                    price_change = (row['close'] - row['open']) / 60
                    second_price = row['open'] + (price_change * second)
                    
                    second_data.append({
                        "time": second_time,
                        "open": second_price,
                        "close": second_price,
                        "high": second_price * 1.001,  # Небольшое отклонение
                        "low": second_price * 0.999,
                        "volume": row['volume'] / 60,  # Равномерное распределение объема
                    })
            
            logger.info(f"Generated {len(second_data)} second candles for {symbol}")
            return pd.DataFrame(second_data)
            
        except Exception as e:
            logger.error(f"Error generating second data for {symbol}: {e}")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
    
    def _get_tick_data(self, symbol: str) -> pd.DataFrame:
        """Получить тиковые данные (симуляция)."""
        try:
            # Получаем последние минутные данные
            minute_data = self.get_data(symbol, '1m')
            
            if minute_data.empty:
                return pd.DataFrame(columns=["time", "price", "volume", "bid", "ask"])
            
            # Симулируем тиковые данные
            tick_data = []
            for _, row in minute_data.iterrows():
                minute_time = row['time']
                base_price = float(row['close'])
                
                # Генерируем 10 тиков в минуту
                for tick in range(10):
                    tick_time = minute_time + timedelta(seconds=tick * 6)
                    # Небольшие случайные изменения цены
                    price_change = (tick - 5) * 0.001  # ±0.5% изменение
                    tick_price = base_price * (1 + price_change)
                    
                    tick_data.append({
                        "time": tick_time,
                        "price": tick_price,
                        "volume": row['volume'] / 10,  # Равномерное распределение
                        "bid": tick_price * 0.9999,
                        "ask": tick_price * 1.0001,
                    })
            
            logger.info(f"Generated {len(tick_data)} ticks for {symbol}")
            return pd.DataFrame(tick_data)
            
        except Exception as e:
            logger.error(f"Error generating tick data for {symbol}: {e}")
            return pd.DataFrame(columns=["time", "price", "volume", "bid", "ask"])
    
    def is_available(self) -> bool:
        """Проверить доступность Tinkoff API."""
        return TINKOFF_AVAILABLE and bool(self.api_key)


class WebSocketDataProvider(DataProvider):
    """Провайдер данных через WebSocket (заготовка для будущего)."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.connected = False
    
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Получить данные через WebSocket."""
        logger.info(f"WebSocket data provider called for {symbol} ({timeframe})")
        logger.warning("WebSocket provider not implemented yet")
        
        # Возвращаем пустые данные
        if timeframe in ['1s', 'tick']:
            return pd.DataFrame(columns=["time", "price", "volume", "bid", "ask"])
        else:
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
    
    def is_available(self) -> bool:
        """Проверить доступность WebSocket."""
        return False  # Пока не реализован
    
    async def subscribe_to_candles(self, figi: str, interval: CandleInterval, callback):
        """Подписаться на свечи."""
        logger.info(f"Subscribing to candles for {figi}")
        # Заглушка для будущей реализации
    
    async def subscribe_to_ticks(self, figi: str, callback):
        """Подписаться на тики."""
        logger.info(f"Subscribing to ticks for {figi}")
        # Заглушка для будущей реализации
    
    async def unsubscribe_from_candles(self, figi: str):
        """Отписаться от свечей."""
        logger.info(f"Unsubscribing from candles for {figi}")
    
    async def unsubscribe_from_ticks(self, figi: str):
        """Отписаться от тиков."""
        logger.info(f"Unsubscribing from ticks for {figi}")


class EnhancedMultiTimeframeStockAnalyzer:
    """Расширенный анализатор для работы с разными таймфреймами."""
    
    def __init__(self, api_key: Optional[str] = None, db_conn=None):
        self.api_key = api_key
        self.db_conn = db_conn
        
        # Создаем базовый анализатор для дневных данных
        if StockAnalyzer:
            self.base_analyzer = StockAnalyzer(
                api_key=self.api_key,
                db_conn=self.db_conn
            )
        else:
            self.base_analyzer = None
        
        # Создаем провайдеры данных
        self.tinkoff_provider = TinkoffDataProvider(self.api_key) if self.api_key else None
        self.websocket_provider = WebSocketDataProvider(self.api_key) if self.api_key else None
        
        # Маппинг таймфреймов на провайдеры
        self.timeframe_providers = {
            '1d': [self.base_analyzer] if self.base_analyzer else [],
            '1h': [self.tinkoff_provider],
            '1m': [self.tinkoff_provider],
            '5m': [self.tinkoff_provider],
            '15m': [self.tinkoff_provider],
            '1s': [self.tinkoff_provider],  # Используем симуляцию
            'tick': [self.tinkoff_provider],  # Используем симуляцию
        }
    
    def get_stock_data(self, figi: str, timeframe: str = '1d') -> pd.DataFrame:
        """Получить данные акции для указанного таймфрейма."""
        if not figi:
            logger.warning("EnhancedMultiTimeframeStockAnalyzer.get_stock_data called with empty FIGI")
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
                    info[timeframe].append({
                        'name': provider.__class__.__name__,
                        'available': provider.is_available()
                    })
        return info


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
