"""Multi-timeframe stock analyzer with future WebSocket support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, Optional, List, Callable, Any
import pandas as pd
import asyncio
import json
from abc import ABC, abstractmethod

from .analyzer import StockAnalyzer, TINKOFF_AVAILABLE
import streamlit as st

logger = logging.getLogger(__name__)

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

# Tinkoff API РёРЅС‚РµСЂРІР°Р»С‹
if TINKOFF_AVAILABLE:
    try:
        from tinkoff.invest import CandleInterval, Client
        from tinkoff.invest.utils import quotation_to_decimal
    except ImportError:
        CandleInterval = None
        Client = None
        quotation_to_decimal = None
else:
    CandleInterval = None
    Client = None
    quotation_to_decimal = None


class DataProvider(ABC):
    """РђР±СЃС‚СЂР°РєС‚РЅС‹Р№ Р±Р°Р·РѕРІС‹Р№ РєР»Р°СЃСЃ РґР»СЏ РїСЂРѕРІР°Р№РґРµСЂРѕРІ РґР°РЅРЅС‹С…."""
    
    @abstractmethod
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """РџРѕР»СѓС‡РёС‚СЊ РґР°РЅРЅС‹Рµ РґР»СЏ СЃРёРјРІРѕР»Р° Рё С‚Р°Р№РјС„СЂРµР№РјР°."""
        pass
    
    @abstractmethod
    def is_supported(self, timeframe: str) -> bool:
        """РџСЂРѕРІРµСЂРёС‚СЊ, РїРѕРґРґРµСЂР¶РёРІР°РµС‚СЃСЏ Р»Рё С‚Р°Р№РјС„СЂРµР№Рј."""
        pass


class TinkoffDataProvider(DataProvider):
    """РџСЂРѕРІР°Р№РґРµСЂ РґР°РЅРЅС‹С… С‡РµСЂРµР· Tinkoff API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
        # РњР°РїРїРёРЅРі С‚Р°Р№РјС„СЂРµР№РјРѕРІ РЅР° РёРЅС‚РµСЂРІР°Р»С‹ Tinkoff
        self.timeframe_mapping = {
            '1d': CandleInterval.CANDLE_INTERVAL_DAY if CandleInterval else None,
            '1h': CandleInterval.CANDLE_INTERVAL_HOUR if CandleInterval else None,
            '1m': CandleInterval.CANDLE_INTERVAL_1_MIN if CandleInterval else None,
            '5m': CandleInterval.CANDLE_INTERVAL_5_MIN if CandleInterval else None,
            '15m': CandleInterval.CANDLE_INTERVAL_15_MIN if CandleInterval else None,
        }
        
        # РџРµСЂРёРѕРґС‹ РґР°РЅРЅС‹С… РґР»СЏ СЂР°Р·РЅС‹С… С‚Р°Р№РјС„СЂРµР№РјРѕРІ
        self.data_periods = {
            '1d': {'days': 365, 'max_candles': 1000},
            '1h': {'days': 30, 'max_candles': 720},    # 30 РґРЅРµР№ * 24 С‡Р°СЃР°
            '1m': {'days': 7, 'max_candles': 10080},   # 7 РґРЅРµР№ * 24 * 60 РјРёРЅСѓС‚
            '5m': {'days': 7, 'max_candles': 2016},    # 7 РґРЅРµР№ * 24 * 12 РїСЏС‚РёРјРёРЅСѓС‚РѕРє
            '15m': {'days': 7, 'max_candles': 672},    # 7 РґРЅРµР№ * 24 * 4 РїСЏС‚РЅР°РґС†Р°С‚РёРјРёРЅСѓС‚РєРё
        }
    
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """РџРѕР»СѓС‡РёС‚СЊ РґР°РЅРЅС‹Рµ С‡РµСЂРµР· Tinkoff API."""
        if not TINKOFF_AVAILABLE or not self.api_key:
            logger.warning("Tinkoff API not available")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
        
        try:
            interval = self.timeframe_mapping.get(timeframe)
            if not interval:
                logger.error(f"Unsupported timeframe: {timeframe}")
                return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
            
            # РџРѕР»СѓС‡Р°РµРј РїРµСЂРёРѕРґ РґР°РЅРЅС‹С…
            period_config = self.data_periods.get(timeframe, self.data_periods['1d'])
            
            with Client(self.api_key) as client:
                to_date = datetime.now(timezone.utc)
                from_date = to_date - timedelta(days=period_config['days'])
                
                response = client.market_data.get_candles(
                    figi=symbol,  # Р’ РґР°РЅРЅРѕРј РєРѕРЅС‚РµРєСЃС‚Рµ symbol СЌС‚Рѕ FIGI
                    from_=from_date,
                    to=to_date,
                    interval=interval,
                )
                
                candles = getattr(response, "candles", None) or []
                if not candles:
                    logger.warning(f"No candles returned for {symbol} with timeframe {timeframe}")
                    return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
                
                # РћРіСЂР°РЅРёС‡РёРІР°РµРј РєРѕР»РёС‡РµСЃС‚РІРѕ СЃРІРµС‡РµР№
                max_candles = period_config['max_candles']
                if len(candles) > max_candles:
                    candles = candles[-max_candles:]
                
                # РљРѕРЅРІРµСЂС‚РёСЂСѓРµРј РІ DataFrame
                data = pd.DataFrame({
                    "time": [candle.time for candle in candles],
                    "open": [quotation_to_decimal(candle.open) for candle in candles],
                    "close": [quotation_to_decimal(candle.close) for candle in candles],
                    "high": [quotation_to_decimal(candle.high) for candle in candles],
                    "low": [quotation_to_decimal(candle.low) for candle in candles],
                    "volume": [candle.volume for candle in candles],
                })
                
                # РЎРѕСЂС‚РёСЂСѓРµРј РїРѕ РІСЂРµРјРµРЅРё
                data = data.sort_values("time").reset_index(drop=True)
                
                logger.info(f"Retrieved {len(data)} candles for {symbol} ({timeframe})")
                return data
                
        except Exception as e:
            logger.error(f"Error getting {timeframe} data for {symbol}: {e}")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
    
    def is_supported(self, timeframe: str) -> bool:
        """РџСЂРѕРІРµСЂРёС‚СЊ, РїРѕРґРґРµСЂР¶РёРІР°РµС‚СЃСЏ Р»Рё С‚Р°Р№РјС„СЂРµР№Рј."""
        return timeframe in self.timeframe_mapping and self.timeframe_mapping[timeframe] is not None


class WebSocketDataProvider(DataProvider):
    """Р—Р°РіРѕС‚РѕРІРєР° РґР»СЏ WebSocket РїСЂРѕРІР°Р№РґРµСЂР° (Р±СѓРґСѓС‰Р°СЏ СЂРµР°Р»РёР·Р°С†РёСЏ)."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.ws_url = "wss://invest-public-api.tinkoff.ru/ws"  # Р—Р°РіРѕС‚РѕРІРєР°
        self.is_connected = False
        self.subscriptions = {}
        self.data_cache = {}
    
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """РџРѕР»СѓС‡РёС‚СЊ РґР°РЅРЅС‹Рµ РёР· РєСЌС€Р° WebSocket."""
        cache_key = f"{symbol}_{timeframe}"
        return self.data_cache.get(cache_key, pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"]))
    
    def is_supported(self, timeframe: str) -> bool:
        """WebSocket РїРѕРґРґРµСЂР¶РёРІР°РµС‚ С‚РѕР»СЊРєРѕ СЃРµРєСѓРЅРґРЅС‹Рµ РґР°РЅРЅС‹Рµ."""
        return timeframe in ['1s', 'tick']
    
    async def connect(self):
        """РџРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє WebSocket (Р·Р°РіРѕС‚РѕРІРєР°)."""
        logger.info("WebSocket connection placeholder - not implemented yet")
        self.is_connected = True
    
    async def subscribe_to_ticks(self, symbol: str, callback: Callable):
        """РџРѕРґРїРёСЃР°С‚СЊСЃСЏ РЅР° С‚РёРєРѕРІС‹Рµ РґР°РЅРЅС‹Рµ (Р·Р°РіРѕС‚РѕРІРєР°)."""
        logger.info(f"WebSocket subscription placeholder for {symbol}")
        self.subscriptions[symbol] = callback
    
    async def unsubscribe_from_ticks(self, symbol: str):
        """РћС‚РїРёСЃР°С‚СЊСЃСЏ РѕС‚ С‚РёРєРѕРІС‹С… РґР°РЅРЅС‹С… (Р·Р°РіРѕС‚РѕРІРєР°)."""
        if symbol in self.subscriptions:
            del self.subscriptions[symbol]
            logger.info(f"WebSocket unsubscription for {symbol}")


@dataclass
class MultiTimeframeStockAnalyzer:
    """РђРЅР°Р»РёР·Р°С‚РѕСЂ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ СЂР°Р·РЅС‹РјРё С‚Р°Р№РјС„СЂРµР№РјР°РјРё."""
    
    api_key: Optional[str] = None
    db_conn = None
    
    def __post_init__(self):
        # РЎРѕР·РґР°РµРј Р±Р°Р·РѕРІС‹Р№ Р°РЅР°Р»РёР·Р°С‚РѕСЂ РґР»СЏ РґРЅРµРІРЅС‹С… РґР°РЅРЅС‹С…
        self.base_analyzer = StockAnalyzer(
            api_key=self.api_key,
            db_conn=self.db_conn
        )
        
        # РЎРѕР·РґР°РµРј РїСЂРѕРІР°Р№РґРµСЂС‹ РґР°РЅРЅС‹С…
        self.tinkoff_provider = TinkoffDataProvider(self.api_key) if self.api_key else None
        self.websocket_provider = WebSocketDataProvider(self.api_key) if self.api_key else None
        
        # РњР°РїРїРёРЅРі С‚Р°Р№РјС„СЂРµР№РјРѕРІ РЅР° РїСЂРѕРІР°Р№РґРµСЂС‹
        self.provider_mapping = {
            '1d': 'base',      # РСЃРїРѕР»СЊР·СѓРµРј СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёР№ StockAnalyzer
            '1h': 'tinkoff',   # Tinkoff API
            '1m': 'tinkoff',   # Tinkoff API
            '5m': 'tinkoff',   # Tinkoff API
            '15m': 'tinkoff',  # Tinkoff API
            '1s': 'websocket', # WebSocket (Р±СѓРґСѓС‰РµРµ)
            'tick': 'websocket', # WebSocket (Р±СѓРґСѓС‰РµРµ)
        }
    
    def get_stock_data(self, figi: str, timeframe: str = '1d') -> pd.DataFrame:
        """РџРѕР»СѓС‡РёС‚СЊ РґР°РЅРЅС‹Рµ Р°РєС†РёР№ РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ С‚Р°Р№РјС„СЂРµР№РјР°."""
        if not figi:
            logger.warning("MultiTimeframeStockAnalyzer.get_stock_data called with empty FIGI")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
        
        # РћРїСЂРµРґРµР»СЏРµРј РїСЂРѕРІР°Р№РґРµСЂР°
        provider_type = self.provider_mapping.get(timeframe, 'base')
        
        if provider_type == 'base':
            # РСЃРїРѕР»СЊР·СѓРµРј СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёР№ РјРµС‚РѕРґ РґР»СЏ РґРЅРµРІРЅС‹С… РґР°РЅРЅС‹С…
            return self.base_analyzer.get_stock_data(figi)
        
        elif provider_type == 'tinkoff' and self.tinkoff_provider:
            return self.tinkoff_provider.get_data(figi, timeframe)
        
        elif provider_type == 'websocket' and self.websocket_provider:
            return self.websocket_provider.get_data(figi, timeframe)
        
        else:
            logger.warning(f"No provider available for timeframe {timeframe}")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
    
    def get_multiple_timeframes(self, figi: str, timeframes: List[str]) -> Dict[str, pd.DataFrame]:
        """РџРѕР»СѓС‡РёС‚СЊ РґР°РЅРЅС‹Рµ РґР»СЏ РЅРµСЃРєРѕР»СЊРєРёС… С‚Р°Р№РјС„СЂРµР№РјРѕРІ РѕРґРЅРѕРІСЂРµРјРµРЅРЅРѕ."""
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
        """РџРѕР»СѓС‡РёС‚СЊ РјР°РїРїРёРЅРі С‚РёРєРµСЂРѕРІ РЅР° FIGI."""
        return self.base_analyzer.get_figi_mapping()
    
    def get_available_timeframes(self) -> List[str]:
        """РџРѕР»СѓС‡РёС‚СЊ СЃРїРёСЃРѕРє РґРѕСЃС‚СѓРїРЅС‹С… С‚Р°Р№РјС„СЂРµР№РјРѕРІ."""
        return list(self.provider_mapping.keys())
    
    def is_timeframe_supported(self, timeframe: str) -> bool:
        """РџСЂРѕРІРµСЂРёС‚СЊ, РїРѕРґРґРµСЂР¶РёРІР°РµС‚СЃСЏ Р»Рё С‚Р°Р№РјС„СЂРµР№Рј."""
        provider_type = self.provider_mapping.get(timeframe, 'base')
        
        if provider_type == 'base':
            return True  # Р”РЅРµРІРЅС‹Рµ РґР°РЅРЅС‹Рµ РІСЃРµРіРґР° РїРѕРґРґРµСЂР¶РёРІР°СЋС‚СЃСЏ
        elif provider_type == 'tinkoff':
            return self.tinkoff_provider and self.tinkoff_provider.is_supported(timeframe)
        elif provider_type == 'websocket':
            return self.websocket_provider and self.websocket_provider.is_supported(timeframe)
        
        return False
    
    async def start_real_time_data(self, figi: str, timeframes: List[str]):
        """Р—Р°РїСѓСЃС‚РёС‚СЊ РїРѕР»СѓС‡РµРЅРёРµ РґР°РЅРЅС‹С… РІ СЂРµР°Р»СЊРЅРѕРј РІСЂРµРјРµРЅРё (Р·Р°РіРѕС‚РѕРІРєР°)."""
        logger.info(f"Starting real-time data for {figi} with timeframes: {timeframes}")
        
        # Р”Р»СЏ WebSocket С‚Р°Р№РјС„СЂРµР№РјРѕРІ
        websocket_timeframes = [tf for tf in timeframes if tf in ['1s', 'tick']]
        if websocket_timeframes and self.websocket_provider:
            await self.websocket_provider.connect()
            for timeframe in websocket_timeframes:
                await self.websocket_provider.subscribe_to_ticks(figi, self._handle_tick_data)
    
    async def _handle_tick_data(self, tick_data):
        """РћР±СЂР°Р±РѕС‚Р°С‚СЊ С‚РёРєРѕРІС‹Рµ РґР°РЅРЅС‹Рµ (Р·Р°РіРѕС‚РѕРІРєР°)."""
        logger.debug(f"Received tick data: {tick_data}")
        # Р—РґРµСЃСЊ Р±СѓРґРµС‚ Р»РѕРіРёРєР° РѕР±СЂР°Р±РѕС‚РєРё С‚РёРєРѕРІС‹С… РґР°РЅРЅС‹С…
    
    async def stop_real_time_data(self, figi: str):
        """РћСЃС‚Р°РЅРѕРІРёС‚СЊ РїРѕР»СѓС‡РµРЅРёРµ РґР°РЅРЅС‹С… РІ СЂРµР°Р»СЊРЅРѕРј РІСЂРµРјРµРЅРё (Р·Р°РіРѕС‚РѕРІРєР°)."""
        if self.websocket_provider:
            await self.websocket_provider.unsubscribe_from_ticks(figi)
        logger.info(f"Stopped real-time data for {figi}")


# Р“Р»РѕР±Р°Р»СЊРЅС‹Рµ С„СѓРЅРєС†РёРё РґР»СЏ СѓРґРѕР±СЃС‚РІР°
def create_multi_timeframe_analyzer(api_key: str = None) -> MultiTimeframeStockAnalyzer:
    """РЎРѕР·РґР°С‚СЊ Р°РЅР°Р»РёР·Р°С‚РѕСЂ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ СЂР°Р·РЅС‹РјРё С‚Р°Р№РјС„СЂРµР№РјР°РјРё."""
    return MultiTimeframeStockAnalyzer(api_key=api_key)


def get_supported_timeframes() -> List[str]:
    """РџРѕР»СѓС‡РёС‚СЊ СЃРїРёСЃРѕРє РїРѕРґРґРµСЂР¶РёРІР°РµРјС‹С… С‚Р°Р№РјС„СЂРµР№РјРѕРІ."""
    return ['1d', '1h', '1m', '5m', '15m', '1s', 'tick']


def is_timeframe_available(timeframe: str) -> bool:
    """РџСЂРѕРІРµСЂРёС‚СЊ, РґРѕСЃС‚СѓРїРµРЅ Р»Рё С‚Р°Р№РјС„СЂРµР№Рј РІ С‚РµРєСѓС‰РµР№ РєРѕРЅС„РёРіСѓСЂР°С†РёРё."""
    if timeframe in ['1d']:
        return True  # Р’СЃРµРіРґР° РґРѕСЃС‚СѓРїРµРЅ
    elif timeframe in ['1h', '1m', '5m', '15m']:
        return TINKOFF_AVAILABLE  # Р—Р°РІРёСЃРёС‚ РѕС‚ Tinkoff API
    elif timeframe in ['1s', 'tick']:
        return False  # РџРѕРєР° РЅРµ СЂРµР°Р»РёР·РѕРІР°РЅРѕ
    else:
        return False
