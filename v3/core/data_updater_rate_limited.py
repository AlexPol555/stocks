"""
Rate-Limited DataUpdater to handle API limits.
DataUpdater с ограничением скорости для работы с лимитами API.
"""

import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import pandas as pd

from .multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
from .database import get_connection

logger = logging.getLogger(__name__)


class RateLimitedDataUpdater:
    """DataUpdater с ограничением скорости для работы с лимитами API."""
    
    def __init__(self, api_key: str, max_requests_per_minute: int = 50):
        self.api_key = api_key
        self.max_requests_per_minute = max_requests_per_minute
        self.analyzer = EnhancedMultiTimeframeStockAnalyzer(api_key=api_key)
        self.is_running = False
        self.scheduler_thread = None
        
        # Rate limiting
        self.request_times = []
        self.request_lock = threading.Lock()
        
        # Настройки обновления (более консервативные)
        self.update_schedules = {
            '1d': {'interval': 'daily', 'time': '18:00'},      # После закрытия рынка
            '1h': {'interval': 'hourly', 'time': ':00'},       # Каждый час
            '1m': {'interval': 'minutely', 'time': ':00'},     # Каждую минуту
            '5m': {'interval': '5minutely', 'time': ':00'},    # Каждые 5 минут
            '15m': {'interval': '15minutely', 'time': ':00'},  # Каждые 15 минут
            '1s': {'interval': 'secondly', 'time': ':00'},     # Каждую секунду (отключено)
            'tick': {'interval': 'realtime', 'time': ':00'},   # В реальном времени (отключено)
        }
        
        # Статистика обновлений
        self.update_stats = {
            'last_update': {},
            'update_count': {},
            'errors': {},
            'rate_limit_hits': 0
        }
    
    def _wait_for_rate_limit(self):
        """Ожидать, если достигнут лимит запросов."""
        with self.request_lock:
            now = time.time()
            # Удаляем запросы старше минуты
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            # Если достигнут лимит, ждем
            if len(self.request_times) >= self.max_requests_per_minute:
                wait_time = 60 - (now - self.request_times[0])
                if wait_time > 0:
                    logger.warning(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    # Обновляем список после ожидания
                    now = time.time()
                    self.request_times = [t for t in self.request_times if now - t < 60]
            
            # Добавляем текущий запрос
            self.request_times.append(now)
    
    def start_scheduler(self):
        """Запустить планировщик обновления."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        
        # Настраиваем расписание (только безопасные интервалы)
        schedule.every().day.at("18:00").do(self.update_daily_data)
        schedule.every().hour.at(":00").do(self.update_hourly_data)
        # Убираем слишком частые обновления
        # schedule.every().minute.at(":00").do(self.update_minute_data)
        # schedule.every(5).minutes.at(":00").do(self.update_5min_data)
        # schedule.every(15).minutes.at(":00").do(self.update_15min_data)
        
        logger.info("Rate-limited data updater scheduler started")
        
        # Запускаем в отдельном потоке
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """Остановить планировщик обновления."""
        self.is_running = False
        schedule.clear()
        logger.info("Rate-limited data updater scheduler stopped")
    
    def _run_scheduler(self):
        """Запустить планировщик в цикле."""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)
    
    def update_daily_data(self):
        """Обновить дневные данные."""
        logger.info("Updating daily data...")
        self._update_timeframe_data('1d')
    
    def update_hourly_data(self):
        """Обновить часовые данные."""
        logger.info("Updating hourly data...")
        self._update_timeframe_data('1h')
    
    def update_minute_data(self):
        """Обновить минутные данные."""
        logger.info("Updating minute data...")
        self._update_timeframe_data('1m')
    
    def update_5min_data(self):
        """Обновить 5-минутные данные."""
        logger.info("Updating 5-minute data...")
        self._update_timeframe_data('5m')
    
    def update_15min_data(self):
        """Обновить 15-минутные данные."""
        logger.info("Updating 15-minute data...")
        self._update_timeframe_data('15m')
    
    def update_second_data(self):
        """Обновить секундные данные (отключено для безопасности)."""
        logger.warning("Second data updates are disabled to prevent rate limiting")
        return
    
    def update_tick_data(self):
        """Обновить тиковые данные (отключено для безопасности)."""
        logger.warning("Tick data updates are disabled to prevent rate limiting")
        return
    
    def _update_timeframe_data(self, timeframe: str):
        """Обновить данные для указанного таймфрейма с ограничением скорости."""
        try:
            # Ожидаем, если нужно
            self._wait_for_rate_limit()
            
            conn = get_connection()
            cursor = conn.cursor()
            
            # Получаем список символов (ограничиваем количество)
            cursor.execute("SELECT DISTINCT contract_code FROM companies LIMIT 10")  # Только первые 10
            symbols = [row[0] for row in cursor.fetchall()]
            
            # Получаем FIGI маппинг
            figi_mapping = self.analyzer.get_figi_mapping()
            
            updated_count = 0
            error_count = 0
            
            for symbol in symbols:
                try:
                    # Проверяем rate limit перед каждым запросом
                    self._wait_for_rate_limit()
                    
                    figi = figi_mapping.get(symbol)
                    if not figi:
                        logger.warning(f"FIGI not found for {symbol}")
                        continue
                    
                    # Получаем данные через API
                    data = self.analyzer.get_stock_data(figi, timeframe)
                    
                    if data.empty:
                        logger.warning(f"No data returned for {symbol} ({timeframe})")
                        continue
                    
                    # Сохраняем в БД
                    self._save_timeframe_data(conn, symbol, timeframe, data)
                    updated_count += 1
                    
                    # Обновляем статистику
                    self.update_stats['last_update'][f"{symbol}_{timeframe}"] = datetime.now().isoformat()
                    self.update_stats['update_count'][f"{symbol}_{timeframe}"] = self.update_stats['update_count'].get(f"{symbol}_{timeframe}", 0) + 1
                    
                except Exception as e:
                    error_count += 1
                    error_key = f"{symbol}_{timeframe}"
                    self.update_stats['errors'][error_key] = str(e)
                    
                    # Проверяем, не rate limit ли это
                    if "30014" in str(e) or "rate" in str(e).lower():
                        self.update_stats['rate_limit_hits'] += 1
                        logger.warning(f"Rate limit hit for {symbol} ({timeframe}): {e}")
                        # Ждем дольше при rate limit
                        time.sleep(10)
                    else:
                        logger.error(f"Error updating {symbol} ({timeframe}): {e}")
            
            conn.close()
            logger.info(f"Updated {updated_count} symbols for {timeframe}, {error_count} errors")
            
        except Exception as e:
            logger.error(f"Error updating {timeframe} data: {e}")
    
    def _save_timeframe_data(self, conn, symbol: str, timeframe: str, data: pd.DataFrame):
        """Сохранить данные таймфрейма в БД."""
        cursor = conn.cursor()
        
        if timeframe == 'tick':
            # Специальная обработка для тиковых данных
            self._save_tick_data(conn, symbol, data)
        else:
            # Обычная обработка для свечных данных
            self._save_candle_data(conn, symbol, timeframe, data)
    
    def _save_candle_data(self, conn, symbol: str, timeframe: str, data: pd.DataFrame):
        """Сохранить свечные данные (OHLCV)."""
        cursor = conn.cursor()
        
        # Создаем таблицу для таймфрейма, если не существует
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
        
        # Вставляем данные
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
    
    def _save_tick_data(self, conn, symbol: str, data: pd.DataFrame):
        """Сохранить тиковые данные."""
        cursor = conn.cursor()
        
        # Создаем таблицу для тиковых данных, если не существует
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_tick (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                datetime TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER,
                bid REAL,
                ask REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, datetime)
            )
        """)
        
        # Вставляем тиковые данные
        for _, row in data.iterrows():
            cursor.execute("""
                INSERT OR REPLACE INTO data_tick
                (symbol, datetime, price, volume, bid, ask)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                row['time'].isoformat(),
                row.get('price', row.get('close', 0)),
                row.get('volume', 0),
                row.get('bid', None),
                row.get('ask', None)
            ))
        
        conn.commit()
    
    def get_update_stats(self) -> Dict:
        """Получить статистику обновлений."""
        return {
            'is_running': self.is_running,
            'last_update': self.update_stats['last_update'],
            'update_count': self.update_stats['update_count'],
            'errors': self.update_stats['errors'],
            'rate_limit_hits': self.update_stats['rate_limit_hits'],
            'current_requests_per_minute': len(self.request_times)
        }
    
    def get_timeframe_status(self, timeframe: str) -> Dict:
        """Получить статус обновления для конкретного таймфрейма."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Проверяем, существует ли таблица
            table_name = f"data_{timeframe.replace('m', 'min').replace('h', 'hour')}" if timeframe != 'tick' else 'data_tick'
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # Получаем статистику по таблице
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                record_count = cursor.fetchone()[0]
                
                cursor.execute(f"SELECT MAX(datetime) FROM {table_name}")
                last_record = cursor.fetchone()[0]
                
                cursor.execute(f"SELECT COUNT(DISTINCT symbol) FROM {table_name}")
                symbol_count = cursor.fetchone()[0]
                
                return {
                    'timeframe': timeframe,
                    'table_exists': True,
                    'record_count': record_count,
                    'symbol_count': symbol_count,
                    'last_record': last_record,
                    'status': 'active'
                }
            else:
                return {
                    'timeframe': timeframe,
                    'table_exists': False,
                    'record_count': 0,
                    'symbol_count': 0,
                    'last_record': None,
                    'status': 'not_created'
                }
                
        except Exception as e:
            logger.error(f"Error getting status for {timeframe}: {e}")
            return {
                'timeframe': timeframe,
                'table_exists': False,
                'error': str(e),
                'status': 'error'
            }
        finally:
            conn.close()
    
    def get_all_timeframe_status(self) -> Dict[str, Dict]:
        """Получить статус всех таймфреймов."""
        timeframes = ['1d', '1h', '1m', '5m', '15m', '1s', 'tick']
        return {tf: self.get_timeframe_status(tf) for tf in timeframes}


def create_rate_limited_data_updater(api_key: str, max_requests_per_minute: int = 50) -> RateLimitedDataUpdater:
    """Создать DataUpdater с ограничением скорости."""
    return RateLimitedDataUpdater(api_key, max_requests_per_minute)
