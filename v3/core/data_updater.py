"""Data updater for multi-timeframe data synchronization."""

import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import pandas as pd

from .multi_timeframe_analyzer import MultiTimeframeStockAnalyzer
from .database import get_connection

logger = logging.getLogger(__name__)


class DataUpdater:
    """РџР»Р°РЅРёСЂРѕРІС‰РёРє РѕР±РЅРѕРІР»РµРЅРёСЏ РґР°РЅРЅС‹С… СЂР°Р·РЅС‹С… С‚Р°Р№РјС„СЂРµР№РјРѕРІ."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.analyzer = MultiTimeframeStockAnalyzer(api_key=api_key)
        self.is_running = False
        self.scheduler_thread = None
        
        # РќР°СЃС‚СЂРѕР№РєРё РѕР±РЅРѕРІР»РµРЅРёСЏ
        self.update_schedules = {
            '1d': {'interval': 'daily', 'time': '18:00'},      # РџРѕСЃР»Рµ Р·Р°РєСЂС‹С‚РёСЏ СЂС‹РЅРєР°
            '1h': {'interval': 'hourly', 'time': ':00'},       # РљР°Р¶РґС‹Р№ С‡Р°СЃ
            '1m': {'interval': 'minutely', 'time': ':00'},     # РљР°Р¶РґСѓСЋ РјРёРЅСѓС‚Сѓ
            '5m': {'interval': '5minutely', 'time': ':00'},    # РљР°Р¶РґС‹Рµ 5 РјРёРЅСѓС‚
            '15m': {'interval': '15minutely', 'time': ':00'},  # РљР°Р¶РґС‹Рµ 15 РјРёРЅСѓС‚
        }
        
        # РЎС‚Р°С‚РёСЃС‚РёРєР° РѕР±РЅРѕРІР»РµРЅРёР№
        self.update_stats = {
            'last_update': {},
            'update_count': {},
            'errors': {}
        }
    
    def start_scheduler(self):
        """Р—Р°РїСѓСЃС‚РёС‚СЊ РїР»Р°РЅРёСЂРѕРІС‰РёРє РѕР±РЅРѕРІР»РµРЅРёСЏ."""
        if self.is_running:
            logger.warning("Data updater is already running")
            return
        
        self.is_running = True
        
        # РќР°СЃС‚СЂР°РёРІР°РµРј СЂР°СЃРїРёСЃР°РЅРёРµ
        schedule.every().day.at("18:00").do(self.update_daily_data)
        schedule.every().hour.at(":00").do(self.update_hourly_data)
        schedule.every().minute.at(":00").do(self.update_minute_data)
        schedule.every(5).minutes.at(":00").do(self.update_5min_data)
        schedule.every(15).minutes.at(":00").do(self.update_15min_data)
        
        logger.info("Data updater scheduler started")
        
        # Р—Р°РїСѓСЃРєР°РµРј РІ РѕС‚РґРµР»СЊРЅРѕРј РїРѕС‚РѕРєРµ
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """РћСЃС‚Р°РЅРѕРІРёС‚СЊ РїР»Р°РЅРёСЂРѕРІС‰РёРє РѕР±РЅРѕРІР»РµРЅРёСЏ."""
        if not self.is_running:
            logger.warning("Data updater is not running")
            return
        
        self.is_running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Data updater scheduler stopped")
    
    def _run_scheduler(self):
        """Р—Р°РїСѓСЃС‚РёС‚СЊ РїР»Р°РЅРёСЂРѕРІС‰РёРє РІ С†РёРєР»Рµ."""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)
    
    def update_daily_data(self):
        """РћР±РЅРѕРІРёС‚СЊ РґРЅРµРІРЅС‹Рµ РґР°РЅРЅС‹Рµ."""
        logger.info("Updating daily data...")
        self._update_timeframe_data('1d')
    
    def update_hourly_data(self):
        """РћР±РЅРѕРІРёС‚СЊ С‡Р°СЃРѕРІС‹Рµ РґР°РЅРЅС‹Рµ."""
        logger.info("Updating hourly data...")
        self._update_timeframe_data('1h')
    
    def update_minute_data(self):
        """РћР±РЅРѕРІРёС‚СЊ РјРёРЅСѓС‚РЅС‹Рµ РґР°РЅРЅС‹Рµ."""
        logger.info("Updating minute data...")
        self._update_timeframe_data('1m')
    
    def update_5min_data(self):
        """РћР±РЅРѕРІРёС‚СЊ 5-РјРёРЅСѓС‚РЅС‹Рµ РґР°РЅРЅС‹Рµ."""
        logger.info("Updating 5-minute data...")
        self._update_timeframe_data('5m')
    
    def update_15min_data(self):
        """РћР±РЅРѕРІРёС‚СЊ 15-РјРёРЅСѓС‚РЅС‹Рµ РґР°РЅРЅС‹Рµ."""
        logger.info("Updating 15-minute data...")
        self._update_timeframe_data('15m')
    
    def _update_timeframe_data(self, timeframe: str):
        """РћР±РЅРѕРІРёС‚СЊ РґР°РЅРЅС‹Рµ РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ С‚Р°Р№РјС„СЂРµР№РјР°."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # РџРѕР»СѓС‡Р°РµРј СЃРїРёСЃРѕРє СЃРёРјРІРѕР»РѕРІ
            cursor.execute("SELECT DISTINCT contract_code FROM companies")
            symbols = [row[0] for row in cursor.fetchall()]
            
            # РџРѕР»СѓС‡Р°РµРј FIGI РјР°РїРїРёРЅРі
            figi_mapping = self.analyzer.get_figi_mapping()
            
            updated_count = 0
            error_count = 0
            
            for symbol in symbols:
                try:
                    figi = figi_mapping.get(symbol)
                    if not figi:
                        logger.warning(f"FIGI not found for {symbol}")
                        continue
                    
                    # РџРѕР»СѓС‡Р°РµРј РґР°РЅРЅС‹Рµ С‡РµСЂРµР· API
                    data = self.analyzer.get_stock_data(figi, timeframe)
                    
                    if data.empty:
                        logger.warning(f"No data returned for {symbol} ({timeframe})")
                        continue
                    
                    # РЎРѕС…СЂР°РЅСЏРµРј РІ Р‘Р”
                    self._save_timeframe_data(conn, symbol, timeframe, data)
                    updated_count += 1
                    
                    # РћР±РЅРѕРІР»СЏРµРј СЃС‚Р°С‚РёСЃС‚РёРєСѓ
                    self.update_stats['last_update'][f"{symbol}_{timeframe}"] = datetime.now().isoformat()
                    self.update_stats['update_count'][f"{symbol}_{timeframe}"] = self.update_stats['update_count'].get(f"{symbol}_{timeframe}", 0) + 1
                    
                except Exception as e:
                    error_count += 1
                    error_key = f"{symbol}_{timeframe}"
                    self.update_stats['errors'][error_key] = str(e)
                    logger.error(f"Error updating {symbol} ({timeframe}): {e}")
            
            conn.close()
            logger.info(f"Updated {updated_count} symbols for {timeframe}, {error_count} errors")
            
        except Exception as e:
            logger.error(f"Error updating {timeframe} data: {e}")
    
    def _save_timeframe_data(self, conn, symbol: str, timeframe: str, data: pd.DataFrame):
        """РЎРѕС…СЂР°РЅРёС‚СЊ РґР°РЅРЅС‹Рµ С‚Р°Р№РјС„СЂРµР№РјР° РІ Р‘Р”."""
        cursor = conn.cursor()
        
        # РЎРѕР·РґР°РµРј С‚Р°Р±Р»РёС†Сѓ РґР»СЏ С‚Р°Р№РјС„СЂРµР№РјР°, РµСЃР»Рё РЅРµ СЃСѓС‰РµСЃС‚РІСѓРµС‚
        table_name = f"data_{timeframe.replace('m', 'min').replace('h', 'hour')}"
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                datetime TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, datetime)
            )
        """)
        
        # Р’СЃС‚Р°РІР»СЏРµРј РґР°РЅРЅС‹Рµ
        for _, row in data.iterrows():
            cursor.execute(f"""
                INSERT OR REPLACE INTO {table_name}
                (symbol, datetime, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                row['time'].isoformat(),
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row['volume']
            ))
        
        conn.commit()
    
    def get_update_stats(self) -> Dict:
        """РџРѕР»СѓС‡РёС‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ РѕР±РЅРѕРІР»РµРЅРёР№."""
        return {
            'is_running': self.is_running,
            'last_update': self.update_stats['last_update'],
            'update_count': self.update_stats['update_count'],
            'errors': self.update_stats['errors']
        }
    
    def force_update(self, timeframe: str, symbols: Optional[List[str]] = None):
        """РџСЂРёРЅСѓРґРёС‚РµР»СЊРЅРѕ РѕР±РЅРѕРІРёС‚СЊ РґР°РЅРЅС‹Рµ РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ С‚Р°Р№РјС„СЂРµР№РјР°."""
        logger.info(f"Force updating {timeframe} data for symbols: {symbols or 'all'}")
        
        if symbols:
            # РћР±РЅРѕРІР»СЏРµРј С‚РѕР»СЊРєРѕ СѓРєР°Р·Р°РЅРЅС‹Рµ СЃРёРјРІРѕР»С‹
            for symbol in symbols:
                try:
                    figi_mapping = self.analyzer.get_figi_mapping()
                    figi = figi_mapping.get(symbol)
                    if not figi:
                        continue
                    
                    data = self.analyzer.get_stock_data(figi, timeframe)
                    if not data.empty:
                        conn = get_connection()
                        self._save_timeframe_data(conn, symbol, timeframe, data)
                        conn.close()
                        logger.info(f"Force updated {symbol} ({timeframe})")
                except Exception as e:
                    logger.error(f"Error force updating {symbol} ({timeframe}): {e}")
        else:
            # РћР±РЅРѕРІР»СЏРµРј РІСЃРµ СЃРёРјРІРѕР»С‹
            self._update_timeframe_data(timeframe)


# Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ СЌРєР·РµРјРїР»СЏСЂ РґР»СЏ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ РІ РїСЂРёР»РѕР¶РµРЅРёРё
_data_updater_instance = None

def get_data_updater(api_key: str = None) -> DataUpdater:
    """РџРѕР»СѓС‡РёС‚СЊ РіР»РѕР±Р°Р»СЊРЅС‹Р№ СЌРєР·РµРјРїР»СЏСЂ DataUpdater."""
    global _data_updater_instance
    if _data_updater_instance is None:
        _data_updater_instance = DataUpdater(api_key)
    return _data_updater_instance

def start_data_updater(api_key: str = None):
    """Р—Р°РїСѓСЃС‚РёС‚СЊ РіР»РѕР±Р°Р»СЊРЅС‹Р№ DataUpdater."""
    updater = get_data_updater(api_key)
    updater.start_scheduler()

def stop_data_updater():
    """РћСЃС‚Р°РЅРѕРІРёС‚СЊ РіР»РѕР±Р°Р»СЊРЅС‹Р№ DataUpdater."""
    global _data_updater_instance
    if _data_updater_instance:
        _data_updater_instance.stop_scheduler()
        _data_updater_instance = None
