"""
Enhanced Real-Time Data Manager with real WebSocket support.
Расширенный менеджер данных в реальном времени с поддержкой реального WebSocket.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
import json

from .tinkoff_websocket_provider import TinkoffWebSocketProvider, create_tinkoff_websocket_provider
from .multi_timeframe_analyzer_enhanced import get_tinkoff_api_key
from .database import get_connection

logger = logging.getLogger(__name__)


class EnhancedRealTimeDataManager:
    """
    Расширенный менеджер для получения и обработки данных в реальном времени.
    Использует реальный WebSocket провайдер Tinkoff для получения тиковых и секундных данных.
    """
    
    def __init__(self, api_key: Optional[str] = None, sandbox: bool = False):
        self.api_key = api_key if api_key else get_tinkoff_api_key()
        self.sandbox = sandbox
        self.websocket_provider = None
        
        # Активные подписки
        self.active_subscriptions: Dict[str, asyncio.Task] = {}
        
        # Кэш данных в реальном времени
        self.real_time_cache: Dict[str, Dict[str, Any]] = {}
        
        # Путь к БД
        self.db_path = "stock_data.db"
        
        if self.api_key:
            self.websocket_provider = create_tinkoff_websocket_provider(self.api_key, sandbox)
            logger.info(f"EnhancedRealTimeDataManager initialized with real WebSocket provider (sandbox: {sandbox})")
        else:
            logger.warning("EnhancedRealTimeDataManager: No API key provided. WebSocket provider not initialized.")
    
    async def start_real_time_data(self, figi: str, timeframe: str = '1s'):
        """
        Начать получение данных в реальном времени для указанного FIGI и таймфрейма.
        Поддерживает '1s' (секундные свечи), 'tick' (тиковые данные), 'orderbook' (стакан).
        """
        if not self.websocket_provider:
            logger.error("WebSocket provider not available. Cannot start real-time data.")
            return
        
        if figi in self.active_subscriptions:
            logger.info(f"Real-time data for {figi} already active.")
            return
        
        logger.info(f"Starting real-time data for {figi} ({timeframe})...")
        
        try:
            # Подключаемся к WebSocket, если не подключены
            if not self.websocket_provider.is_connected():
                await self.websocket_provider.connect()
            
            # Создаем задачу для обработки данных
            if timeframe == '1s':
                task = asyncio.create_task(self._subscribe_to_seconds(figi))
            elif timeframe == 'tick':
                task = asyncio.create_task(self._subscribe_to_ticks(figi))
            elif timeframe == 'orderbook':
                task = asyncio.create_task(self._subscribe_to_orderbook(figi))
            else:
                logger.error(f"Unsupported timeframe for real-time data: {timeframe}")
                return
            
            self.active_subscriptions[figi] = task
            logger.info(f"Real-time data started for {figi} ({timeframe})")
            
        except Exception as e:
            logger.error(f"Error starting real-time data for {figi} ({timeframe}): {e}")
    
    async def _subscribe_to_seconds(self, figi: str):
        """Подписаться на секундные данные."""
        try:
            # Подписываемся на минутные свечи (самый короткий доступный интервал)
            await self.websocket_provider.subscribe_to_candles(
                figi, 
                interval="1m",
                callback=self._handle_second_data
            )
            
            # Ждем, пока задача не будет отменена
            await asyncio.Future()  # Бесконечное ожидание
            
        except asyncio.CancelledError:
            logger.info(f"Second data subscription cancelled for {figi}")
        except Exception as e:
            logger.error(f"Error in second data subscription for {figi}: {e}")
        finally:
            # Отписываемся от свечей
            await self.websocket_provider.unsubscribe_from_candles(figi)
    
    async def _subscribe_to_ticks(self, figi: str):
        """Подписаться на тиковые данные."""
        try:
            # Подписываемся на тики
            await self.websocket_provider.subscribe_to_ticks(
                figi,
                callback=self._handle_tick_data
            )
            
            # Ждем, пока задача не будет отменена
            await asyncio.Future()  # Бесконечное ожидание
            
        except asyncio.CancelledError:
            logger.info(f"Tick data subscription cancelled for {figi}")
        except Exception as e:
            logger.error(f"Error in tick data subscription for {figi}: {e}")
        finally:
            # Отписываемся от тиков
            await self.websocket_provider.unsubscribe_from_ticks(figi)
    
    async def _subscribe_to_orderbook(self, figi: str):
        """Подписаться на стакан."""
        try:
            # Подписываемся на стакан
            await self.websocket_provider.subscribe_to_orderbook(
                figi,
                depth=10,
                callback=self._handle_orderbook_data
            )
            
            # Ждем, пока задача не будет отменена
            await asyncio.Future()  # Бесконечное ожидание
            
        except asyncio.CancelledError:
            logger.info(f"Orderbook subscription cancelled for {figi}")
        except Exception as e:
            logger.error(f"Error in orderbook subscription for {figi}: {e}")
        finally:
            # Отписываемся от стакана
            await self.websocket_provider.unsubscribe_from_orderbook(figi)
    
    async def _handle_second_data(self, candle_data: Dict[str, Any]):
        """Обработать секундные данные (из минутных свечей)."""
        try:
            # Получаем символ из FIGI (нужен маппинг)
            symbol = self._figi_to_symbol(candle_data.get('figi', ''))
            
            if not symbol:
                return
            
            # Сохраняем в кэш
            self.real_time_cache[symbol] = {
                'last_candle': candle_data,
                'timestamp': datetime.now().isoformat(),
                'type': 'second'
            }
            
            logger.debug(f"Processed second data for {symbol}: {candle_data}")
            
            # Сохраняем в БД (таблица data_1s)
            await self._save_real_time_data_to_db(symbol, '1s', candle_data)
            
        except Exception as e:
            logger.error(f"Error handling second data: {e}")
    
    async def _handle_tick_data(self, tick_data: Dict[str, Any]):
        """Обработать тиковые данные."""
        try:
            # Получаем символ из FIGI
            symbol = self._figi_to_symbol(tick_data.get('figi', ''))
            
            if not symbol:
                return
            
            # Сохраняем в кэш
            self.real_time_cache[symbol] = {
                'last_tick': tick_data,
                'timestamp': datetime.now().isoformat(),
                'type': 'tick'
            }
            
            logger.debug(f"Processed tick data for {symbol}: {tick_data}")
            
            # Сохраняем в БД (таблица data_tick)
            await self._save_real_time_data_to_db(symbol, 'tick', tick_data)
            
        except Exception as e:
            logger.error(f"Error handling tick data: {e}")
    
    async def _handle_orderbook_data(self, orderbook_data: Dict[str, Any]):
        """Обработать данные стакана."""
        try:
            # Получаем символ из FIGI
            symbol = self._figi_to_symbol(orderbook_data.get('figi', ''))
            
            if not symbol:
                return
            
            # Сохраняем в кэш
            self.real_time_cache[symbol] = {
                'last_orderbook': orderbook_data,
                'timestamp': datetime.now().isoformat(),
                'type': 'orderbook'
            }
            
            logger.debug(f"Processed orderbook data for {symbol}")
            
        except Exception as e:
            logger.error(f"Error handling orderbook data: {e}")
    
    async def _save_real_time_data_to_db(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """Сохранить данные реального времени в соответствующую таблицу БД."""
        try:
            conn = get_connection(self.db_path)
            cursor = conn.cursor()
            
            if timeframe == '1s':
                # Сохраняем в таблицу data_1s
                table_name = "data_1s"
                cursor.execute(f"""
                    INSERT OR REPLACE INTO {table_name}
                    (symbol, datetime, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    data.get('time', datetime.now()).isoformat(),
                    data.get('open', 0.0),
                    data.get('high', 0.0),
                    data.get('low', 0.0),
                    data.get('close', 0.0),
                    data.get('volume', 0)
                ))
                
            elif timeframe == 'tick':
                # Сохраняем в таблицу data_tick
                table_name = "data_tick"
                cursor.execute(f"""
                    INSERT INTO {table_name}
                    (symbol, datetime, price, volume)
                    VALUES (?, ?, ?, ?)
                """, (
                    symbol,
                    data.get('time', datetime.now()).isoformat(),
                    data.get('price', 0.0),
                    data.get('volume', 0)
                ))
            
            conn.commit()
            logger.debug(f"Saved {timeframe} data for {symbol} to DB")
            
        except Exception as e:
            logger.error(f"Error saving {timeframe} data for {symbol} to DB: {e}")
        finally:
            if conn:
                conn.close()
    
    def _figi_to_symbol(self, figi: str) -> Optional[str]:
        """Конвертировать FIGI в символ (нужен маппинг)."""
        # Простой маппинг (в реальности нужен более полный)
        figi_to_symbol = {
            'BBG004730N88': 'SBER',
            'BBG004730ZJ9': 'GAZP',
            'BBG004731032': 'LKOH',
            'BBG00475J7X1': 'NVTK',
            'BBG0047315Y7': 'ROSN',
            'BBG004RVFFC0': 'NLMK',
            'BBG004S681W1': 'ALRS',
            'BBG004S68758': 'MGNT',
            'BBG006L8G4H1': 'YNDX',
            'BBG00QPYJ5X0': 'VKCO',
        }
        return figi_to_symbol.get(figi)
    
    def get_latest_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Получить последние кэшированные данные для символа."""
        return self.real_time_cache.get(symbol)
    
    def get_all_latest_data(self) -> Dict[str, Dict[str, Any]]:
        """Получить все последние данные."""
        return self.real_time_cache.copy()
    
    async def stop_real_time_data(self, figi: str):
        """Остановить получение данных в реальном времени."""
        if figi in self.active_subscriptions:
            # Отменяем задачу
            self.active_subscriptions[figi].cancel()
            
            # Ждем завершения
            try:
                await asyncio.wait_for(self.active_subscriptions[figi], timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for subscription {figi} to stop")
            
            # Удаляем из активных подписок
            del self.active_subscriptions[figi]
            
            logger.info(f"Stopped real-time data for {figi}")
        else:
            logger.info(f"No active subscription found for {figi}")
    
    async def stop_all_real_time_data(self):
        """Остановить все активные подписки на данные в реальном времени."""
        for figi in list(self.active_subscriptions.keys()):
            await self.stop_real_time_data(figi)
        
        # Отключаемся от WebSocket
        if self.websocket_provider and self.websocket_provider.is_connected():
            await self.websocket_provider.disconnect()
        
        logger.info("All real-time data subscriptions stopped")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Получить статус подключения."""
        return {
            'websocket_connected': self.websocket_provider.is_connected() if self.websocket_provider else False,
            'active_subscriptions': len(self.active_subscriptions),
            'subscriptions': list(self.active_subscriptions.keys()),
            'cached_symbols': len(self.real_time_cache),
            'api_key_available': bool(self.api_key)
        }
    
    async def get_historical_ticks(self, figi: str, days: int = 1) -> pd.DataFrame:
        """Получить исторические тиковые данные."""
        if not self.websocket_provider:
            logger.error("WebSocket provider not available")
            return pd.DataFrame()
        
        return await self.websocket_provider.get_historical_ticks(figi, days)
    
    async def get_historical_seconds(self, figi: str, days: int = 1) -> pd.DataFrame:
        """Получить исторические секундные данные."""
        if not self.websocket_provider:
            logger.error("WebSocket provider not available")
            return pd.DataFrame()
        
        return await self.websocket_provider.get_historical_seconds(figi, days)


def create_enhanced_realtime_manager(api_key: Optional[str] = None, sandbox: bool = False) -> EnhancedRealTimeDataManager:
    """Создать расширенный менеджер данных в реальном времени."""
    return EnhancedRealTimeDataManager(api_key, sandbox)
