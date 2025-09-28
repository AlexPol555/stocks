"""
Real Tinkoff WebSocket Data Provider.
Реальный провайдер данных через WebSocket для Tinkoff API.
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
import pandas as pd

# Попытка импорта Tinkoff API
try:
    from tinkoff.invest import Client, CandleInterval
    from tinkoff.invest.utils import quotation_to_decimal
    TINKOFF_AVAILABLE = True
except ImportError:
    TINKOFF_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Tinkoff API not available. Install with: pip install tinkoff-invest")

logger = logging.getLogger(__name__)


class TinkoffWebSocketProvider:
    """Реальный провайдер данных через WebSocket для Tinkoff API."""
    
    def __init__(self, api_key: str, sandbox: bool = False):
        self.api_key = api_key
        self.sandbox = sandbox
        
        # WebSocket URL
        if sandbox:
            self.ws_url = "wss://sandbox-invest-public-api.tbank.ru/ws/"
        else:
            self.ws_url = "wss://invest-public-api.tbank.ru/ws/"
        
        # Состояние подключения
        self.websocket = None
        self.connected = False
        self.subscriptions = {}  # Активные подписки
        self.callbacks = {}      # Колбэки для обработки данных
        
        # Кэш последних данных
        self.last_data = {}
        
        logger.info(f"TinkoffWebSocketProvider initialized (sandbox: {sandbox})")
    
    async def connect(self):
        """Подключиться к WebSocket."""
        if self.connected:
            logger.info("WebSocket already connected")
            return
        
        try:
            # Подключаемся к WebSocket
            self.websocket = await websockets.connect(
                self.ws_url,
                extra_headers={
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            self.connected = True
            logger.info("Connected to Tinkoff WebSocket")
            
            # Запускаем обработчик сообщений
            asyncio.create_task(self._message_handler())
            
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """Отключиться от WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.connected = False
        logger.info("Disconnected from Tinkoff WebSocket")
    
    async def _message_handler(self):
        """Обработчик входящих сообщений."""
        try:
            async for message in self.websocket:
                await self._process_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            self.connected = False
    
    async def _process_message(self, message: str):
        """Обработать входящее сообщение."""
        try:
            data = json.loads(message)
            message_type = data.get("messageType")
            
            if message_type == "candle":
                await self._handle_candle_data(data)
            elif message_type == "orderbook":
                await self._handle_orderbook_data(data)
            elif message_type == "trade":
                await self._handle_trade_data(data)
            else:
                logger.debug(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _handle_candle_data(self, data: Dict):
        """Обработать данные свечей."""
        try:
            candle = data.get("candle", {})
            figi = candle.get("figi")
            
            if not figi:
                return
            
            # Конвертируем в стандартный формат
            candle_data = {
                "time": datetime.fromisoformat(candle.get("time", "").replace("Z", "+00:00")),
                "open": quotation_to_decimal(candle.get("open", {})),
                "close": quotation_to_decimal(candle.get("close", {})),
                "high": quotation_to_decimal(candle.get("high", {})),
                "low": quotation_to_decimal(candle.get("low", {})),
                "volume": candle.get("volume", 0),
                "interval": candle.get("interval")
            }
            
            # Сохраняем в кэш
            self.last_data[figi] = {
                "candle": candle_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Вызываем колбэк, если есть
            if figi in self.callbacks:
                callback = self.callbacks[figi]
                if asyncio.iscoroutinefunction(callback):
                    await callback(candle_data)
                else:
                    callback(candle_data)
                    
            logger.debug(f"Processed candle data for {figi}")
            
        except Exception as e:
            logger.error(f"Error handling candle data: {e}")
    
    async def _handle_trade_data(self, data: Dict):
        """Обработать тиковые данные."""
        try:
            trade = data.get("trade", {})
            figi = trade.get("figi")
            
            if not figi:
                return
            
            # Конвертируем в стандартный формат
            tick_data = {
                "time": datetime.fromisoformat(trade.get("time", "").replace("Z", "+00:00")),
                "price": quotation_to_decimal(trade.get("price", {})),
                "volume": trade.get("quantity", 0),
                "direction": trade.get("direction", "UNSPECIFIED")
            }
            
            # Сохраняем в кэш
            self.last_data[figi] = {
                "tick": tick_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Вызываем колбэк, если есть
            if figi in self.callbacks:
                callback = self.callbacks[figi]
                if asyncio.iscoroutinefunction(callback):
                    await callback(tick_data)
                else:
                    callback(tick_data)
                    
            logger.debug(f"Processed tick data for {figi}")
            
        except Exception as e:
            logger.error(f"Error handling tick data: {e}")
    
    async def _handle_orderbook_data(self, data: Dict):
        """Обработать данные стакана."""
        try:
            orderbook = data.get("orderbook", {})
            figi = orderbook.get("figi")
            
            if not figi:
                return
            
            # Конвертируем в стандартный формат
            orderbook_data = {
                "time": datetime.fromisoformat(orderbook.get("time", "").replace("Z", "+00:00")),
                "bids": [(quotation_to_decimal(bid.get("price", {})), bid.get("quantity", 0)) 
                         for bid in orderbook.get("bids", [])],
                "asks": [(quotation_to_decimal(ask.get("price", {})), ask.get("quantity", 0)) 
                         for ask in orderbook.get("asks", [])],
                "depth": orderbook.get("depth", 0)
            }
            
            # Сохраняем в кэш
            self.last_data[figi] = {
                "orderbook": orderbook_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Processed orderbook data for {figi}")
            
        except Exception as e:
            logger.error(f"Error handling orderbook data: {e}")
    
    async def subscribe_to_candles(self, figi: str, interval: str = "1m", callback: Optional[Callable] = None):
        """Подписаться на свечи."""
        if not self.connected:
            await self.connect()
        
        # Маппинг интервалов
        interval_mapping = {
            "1m": "CANDLE_INTERVAL_1_MIN",
            "5m": "CANDLE_INTERVAL_5_MIN",
            "15m": "CANDLE_INTERVAL_15_MIN",
            "1h": "CANDLE_INTERVAL_HOUR",
            "1d": "CANDLE_INTERVAL_DAY"
        }
        
        tinkoff_interval = interval_mapping.get(interval)
        if not tinkoff_interval:
            logger.error(f"Unsupported interval: {interval}")
            return
        
        # Сохраняем колбэк
        if callback:
            self.callbacks[figi] = callback
        
        # Отправляем подписку
        subscribe_message = {
            "messageType": "subscribe",
            "subscription": {
                "candles": {
                    "figi": figi,
                    "interval": tinkoff_interval
                }
            }
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        self.subscriptions[figi] = {"type": "candles", "interval": interval}
        
        logger.info(f"Subscribed to candles for {figi} ({interval})")
    
    async def subscribe_to_ticks(self, figi: str, callback: Optional[Callable] = None):
        """Подписаться на тики."""
        if not self.connected:
            await self.connect()
        
        # Сохраняем колбэк
        if callback:
            self.callbacks[figi] = callback
        
        # Отправляем подписку
        subscribe_message = {
            "messageType": "subscribe",
            "subscription": {
                "trades": {
                    "figi": figi
                }
            }
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        self.subscriptions[figi] = {"type": "trades"}
        
        logger.info(f"Subscribed to ticks for {figi}")
    
    async def subscribe_to_orderbook(self, figi: str, depth: int = 10, callback: Optional[Callable] = None):
        """Подписаться на стакан."""
        if not self.connected:
            await self.connect()
        
        # Сохраняем колбэк
        if callback:
            self.callbacks[figi] = callback
        
        # Отправляем подписку
        subscribe_message = {
            "messageType": "subscribe",
            "subscription": {
                "orderBook": {
                    "figi": figi,
                    "depth": depth
                }
            }
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        self.subscriptions[figi] = {"type": "orderbook", "depth": depth}
        
        logger.info(f"Subscribed to orderbook for {figi} (depth: {depth})")
    
    async def unsubscribe_from_candles(self, figi: str):
        """Отписаться от свечей."""
        await self._unsubscribe(figi, "candles")
    
    async def unsubscribe_from_ticks(self, figi: str):
        """Отписаться от тиков."""
        await self._unsubscribe(figi, "trades")
    
    async def unsubscribe_from_orderbook(self, figi: str):
        """Отписаться от стакана."""
        await self._unsubscribe(figi, "orderBook")
    
    async def _unsubscribe(self, figi: str, subscription_type: str):
        """Отписаться от подписки."""
        if not self.connected or figi not in self.subscriptions:
            return
        
        # Отправляем отписку
        unsubscribe_message = {
            "messageType": "unsubscribe",
            "subscription": {
                subscription_type: {
                    "figi": figi
                }
            }
        }
        
        await self.websocket.send(json.dumps(unsubscribe_message))
        
        # Удаляем из подписок и колбэков
        if figi in self.subscriptions:
            del self.subscriptions[figi]
        if figi in self.callbacks:
            del self.callbacks[figi]
        
        logger.info(f"Unsubscribed from {subscription_type} for {figi}")
    
    def get_last_data(self, figi: str) -> Optional[Dict]:
        """Получить последние данные для символа."""
        return self.last_data.get(figi)
    
    def get_all_last_data(self) -> Dict[str, Dict]:
        """Получить все последние данные."""
        return self.last_data.copy()
    
    def is_connected(self) -> bool:
        """Проверить состояние подключения."""
        return self.connected
    
    def get_subscriptions(self) -> Dict[str, Dict]:
        """Получить список активных подписок."""
        return self.subscriptions.copy()
    
    async def get_historical_ticks(self, figi: str, days: int = 1) -> pd.DataFrame:
        """Получить исторические тиковые данные через REST API."""
        if not TINKOFF_AVAILABLE:
            logger.warning("Tinkoff API not available")
            return pd.DataFrame()
        
        try:
            with Client(self.api_key, sandbox=self.sandbox) as client:
                to_date = datetime.now(timezone.utc)
                from_date = to_date - timedelta(days=days)
                
                # Получаем исторические сделки
                response = client.market_data.get_last_trades(
                    figi=figi,
                    from_=from_date,
                    to=to_date
                )
                
                trades = getattr(response, "trades", None) or []
                if not trades:
                    logger.warning(f"No historical ticks found for {figi}")
                    return pd.DataFrame()
                
                # Конвертируем в DataFrame
                data = pd.DataFrame({
                    "time": [trade.time for trade in trades],
                    "price": [quotation_to_decimal(trade.price) for trade in trades],
                    "volume": [trade.quantity for trade in trades],
                    "direction": [trade.direction.name for trade in trades]
                })
                
                logger.info(f"Retrieved {len(data)} historical ticks for {figi}")
                return data
                
        except Exception as e:
            logger.error(f"Error getting historical ticks for {figi}: {e}")
            return pd.DataFrame()
    
    async def get_historical_seconds(self, figi: str, days: int = 1) -> pd.DataFrame:
        """Получить исторические секундные данные (агрегация из тиков)."""
        try:
            # Получаем тиковые данные
            tick_data = await self.get_historical_ticks(figi, days)
            
            if tick_data.empty:
                return pd.DataFrame()
            
            # Агрегируем в секундные свечи
            tick_data['time'] = pd.to_datetime(tick_data['time'])
            tick_data.set_index('time', inplace=True)
            
            # Группируем по секундам
            second_data = tick_data.resample('1S').agg({
                'price': ['first', 'last', 'max', 'min'],
                'volume': 'sum'
            }).dropna()
            
            # Выравниваем колонки
            second_data.columns = ['open', 'close', 'high', 'low', 'volume']
            second_data.reset_index(inplace=True)
            
            logger.info(f"Generated {len(second_data)} second candles from ticks for {figi}")
            return second_data
            
        except Exception as e:
            logger.error(f"Error generating second data for {figi}: {e}")
            return pd.DataFrame()


def create_tinkoff_websocket_provider(api_key: str, sandbox: bool = False) -> TinkoffWebSocketProvider:
    """Создать WebSocket провайдер Tinkoff."""
    return TinkoffWebSocketProvider(api_key, sandbox)
