"""
RealTimeDataManager - Менеджер для работы с данными в реальном времени.
Управляет WebSocket подключениями, кэшированием данных и мониторингом.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
import pandas as pd

from .multi_timeframe_analyzer import MultiTimeframeStockAnalyzer, WebSocketDataProvider

logger = logging.getLogger(__name__)


class RealTimeDataManager:
    """Менеджер для работы с данными в реальном времени."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.multi_analyzer = MultiTimeframeStockAnalyzer(api_key=api_key)
        self.ws_provider = WebSocketDataProvider(api_key) if api_key else None
        self.data_cache = {}
        self.update_callbacks = {}
        self.is_monitoring = False
        self.monitored_symbols = set()
        
    def get_historical_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Получить исторические данные."""
        try:
            return self.multi_analyzer.get_stock_data(symbol, timeframe)
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol} ({timeframe}): {e}")
            return pd.DataFrame()
    
    async def start_real_time_data(self, symbol: str, timeframes: List[str]):
        """Запустить получение данных в реальном времени."""
        try:
            logger.info(f"Starting real-time monitoring for {symbol} with timeframes: {timeframes}")
            
            # Получаем исторические данные для всех таймфреймов
            for timeframe in timeframes:
                if timeframe != '1s':  # Исторические данные для всех кроме секундных
                    data = self.get_historical_data(symbol, timeframe)
                    if not data.empty:
                        self.data_cache[f"{symbol}_{timeframe}"] = data
                        logger.info(f"Loaded historical data for {symbol} ({timeframe}): {len(data)} records")
                    else:
                        logger.warning(f"No historical data for {symbol} ({timeframe})")
            
            # Подключаемся к WebSocket для тиковых данных
            if '1s' in timeframes and self.ws_provider:
                try:
                    await self.ws_provider.connect()
                    await self.ws_provider.subscribe_to_ticks(symbol, self._handle_tick_data)
                    logger.info(f"Started WebSocket monitoring for {symbol}")
                except Exception as e:
                    logger.error(f"WebSocket connection failed for {symbol}: {e}")
            
            self.monitored_symbols.add(symbol)
            self.is_monitoring = True
            logger.info(f"Real-time monitoring started for {symbol}")
            
        except Exception as e:
            logger.error(f"Error starting real-time data for {symbol}: {e}")
            raise
    
    async def _handle_tick_data(self, tick_data):
        """Обработать тиковые данные."""
        try:
            logger.debug(f"Received tick data: {tick_data}")
            
            # Обработка тиковых данных (заглушка для будущей реализации)
            if isinstance(tick_data, dict):
                symbol = tick_data.get('symbol', 'UNKNOWN')
                price = tick_data.get('price', 0)
                volume = tick_data.get('volume', 0)
                timestamp = tick_data.get('timestamp', datetime.now())
                
                # Обновляем кэш для всех таймфреймов этого символа
                for cache_key in self.data_cache.keys():
                    if cache_key.startswith(f"{symbol}_"):
                        # Здесь должна быть логика агрегации тиков в свечи
                        logger.debug(f"Updating cache for {cache_key} with tick: {price}")
                        
                        # Простое обновление последней цены (заглушка)
                        if not self.data_cache[cache_key].empty:
                            self.data_cache[cache_key].iloc[-1, self.data_cache[cache_key].columns.get_loc('close')] = price
                            self.data_cache[cache_key].iloc[-1, self.data_cache[cache_key].columns.get_loc('time')] = timestamp
            
        except Exception as e:
            logger.error(f"Error handling tick data: {e}")
    
    def get_latest_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Получить последние данные из кэша."""
        cache_key = f"{symbol}_{timeframe}"
        return self.data_cache.get(cache_key, pd.DataFrame())
    
    def get_cached_symbols(self) -> List[str]:
        """Получить список кэшированных символов."""
        symbols = set()
        for cache_key in self.data_cache.keys():
            symbol = cache_key.split('_')[0]
            symbols.add(symbol)
        return list(symbols)
    
    def get_cached_timeframes(self, symbol: str) -> List[str]:
        """Получить список кэшированных таймфреймов для символа."""
        timeframes = []
        for cache_key in self.data_cache.keys():
            if cache_key.startswith(f"{symbol}_"):
                timeframe = cache_key.split('_', 1)[1]
                timeframes.append(timeframe)
        return timeframes
    
    async def stop_real_time_data(self, symbol: str):
        """Остановить получение данных в реальном времени."""
        try:
            logger.info(f"Stopping real-time monitoring for {symbol}")
            
            if self.ws_provider:
                await self.ws_provider.unsubscribe_from_ticks(symbol)
                logger.info(f"Unsubscribed from WebSocket for {symbol}")
            
            # Очищаем кэш для этого символа
            keys_to_remove = [key for key in self.data_cache.keys() if key.startswith(f"{symbol}_")]
            for key in keys_to_remove:
                del self.data_cache[key]
                logger.info(f"Removed cache entry: {key}")
            
            self.monitored_symbols.discard(symbol)
            
            # Если нет активных символов, останавливаем мониторинг
            if not self.monitored_symbols:
                self.is_monitoring = False
                logger.info("No active symbols, stopping monitoring")
            
            logger.info(f"Stopped real-time monitoring for {symbol}")
            
        except Exception as e:
            logger.error(f"Error stopping real-time data for {symbol}: {e}")
    
    async def refresh_data(self, symbol: str, timeframes: List[str]):
        """Обновить данные для символа."""
        try:
            logger.info(f"Refreshing data for {symbol} with timeframes: {timeframes}")
            
            for timeframe in timeframes:
                if timeframe != '1s':  # Обновляем только исторические данные
                    data = self.get_historical_data(symbol, timeframe)
                    if not data.empty:
                        self.data_cache[f"{symbol}_{timeframe}"] = data
                        logger.info(f"Refreshed data for {symbol} ({timeframe}): {len(data)} records")
            
        except Exception as e:
            logger.error(f"Error refreshing data for {symbol}: {e}")
    
    async def close(self):
        """Закрыть все соединения."""
        try:
            logger.info("Closing RealTimeDataManager")
            
            if self.ws_provider:
                await self.ws_provider.close()
                logger.info("WebSocket connection closed")
            
            self.data_cache.clear()
            self.monitored_symbols.clear()
            self.is_monitoring = False
            
            logger.info("RealTimeDataManager closed")
            
        except Exception as e:
            logger.error(f"Error closing RealTimeDataManager: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус менеджера."""
        return {
            'is_monitoring': self.is_monitoring,
            'monitored_symbols': list(self.monitored_symbols),
            'cached_symbols': self.get_cached_symbols(),
            'total_cache_entries': len(self.data_cache),
            'websocket_connected': self.ws_provider.is_connected if self.ws_provider else False,
            'api_key_available': bool(self.api_key)
        }
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Получить информацию о кэше."""
        cache_info = {}
        for cache_key, data in self.data_cache.items():
            symbol, timeframe = cache_key.split('_', 1)
            cache_info[cache_key] = {
                'symbol': symbol,
                'timeframe': timeframe,
                'records': len(data),
                'last_update': data['time'].iloc[-1] if not data.empty and 'time' in data.columns else None,
                'last_price': data['close'].iloc[-1] if not data.empty and 'close' in data.columns else None
            }
        return cache_info


def create_real_time_manager(api_key: str = None) -> RealTimeDataManager:
    """Создать менеджер для работы с данными в реальном времени."""
    return RealTimeDataManager(api_key)
