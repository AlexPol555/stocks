"""
Optimized DataUpdater with all tickers and timeframes.
Оптимизированный DataUpdater для всех тикеров и таймфреймов.
"""

import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import pandas as pd
import random

from .multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
from .database import get_connection

logger = logging.getLogger(__name__)


class OptimizedDataUpdater:
    """Оптимизированный DataUpdater для всех тикеров и таймфреймов."""
    
    def __init__(self, api_key: str, max_requests_per_minute: int = 50):
        self.api_key = api_key
        self.max_requests_per_minute = max_requests_per_minute
        self.analyzer = EnhancedMultiTimeframeStockAnalyzer(api_key=api_key)
        self.is_running = False
        self.scheduler_thread = None
        
        # Rate limiting с учетом deadline'ов
        self.request_times = []
        self.request_lock = threading.Lock()
        
        # Deadline'ы для разных методов (в миллисекундах)
        self.deadlines = {
            'GetCandles': 500,      # 500ms для свечей
            'GetLastPrices': 500,   # 500ms для последних цен
            'GetOrderBook': 500,    # 500ms для стакана
            'GetTradingStatus': 500, # 500ms для статуса торгов
            'GetInfo': 1000,        # 1000ms для информации
            'GetPortfolio': 1500,   # 1500ms для портфеля
            'GetPositions': 1000,   # 1000ms для позиций
        }
        
        # Настройки обновления для всех таймфреймов
        self.update_schedules = {
            '1d': {'interval': 'daily', 'time': '18:00', 'priority': 1},
            '1h': {'interval': 'hourly', 'time': ':00', 'priority': 2},
            '1m': {'interval': 'minutely', 'time': ':00', 'priority': 3},
            '5m': {'interval': '5minutely', 'time': ':00', 'priority': 4},
            '15m': {'interval': '15minutely', 'time': ':00', 'priority': 5},
        }
        
        # Статистика обновлений
        self.update_stats = {
            'last_update': {},
            'update_count': {},
            'errors': {},
            'rate_limit_hits': 0,
            'total_symbols': 0,
            'successful_updates': 0,
            'failed_updates': 0
        }
        
        # Кэш для оптимизации
        self.symbol_cache = {}
        self.figi_cache = {}
        self.last_update_times = {}
    
    def _wait_for_rate_limit(self, method: str = 'GetCandles'):
        """Ожидать с учетом deadline'а метода."""
        with self.request_lock:
            now = time.time()
            deadline_seconds = self.deadlines.get(method, 500) / 1000.0
            
            # Удаляем запросы старше минуты
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            # Если достигнут лимит, ждем
            if len(self.request_times) >= self.max_requests_per_minute:
                wait_time = 60 - (now - self.request_times[0])
                if wait_time > 0:
                    logger.warning(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    now = time.time()
                    self.request_times = [t for t in self.request_times if now - t < 60]
            
            # Добавляем текущий запрос
            self.request_times.append(now)
            
            # Небольшая задержка для соблюдения deadline'а
            time.sleep(deadline_seconds / 1000.0)
    
    def start_scheduler(self):
        """Запустить планировщик обновления."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        
        # Настраиваем расписание для всех таймфреймов
        schedule.every().day.at("18:00").do(self.update_daily_data)
        schedule.every().hour.at(":00").do(self.update_hourly_data)
        schedule.every().minute.at(":00").do(self.update_minute_data)
        schedule.every(5).minutes.at(":00").do(self.update_5min_data)
        schedule.every(15).minutes.at(":00").do(self.update_15min_data)
        
        logger.info("Optimized data updater scheduler started")
        
        # Запускаем в отдельном потоке
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """Остановить планировщик обновления."""
        self.is_running = False
        schedule.clear()
        logger.info("Optimized data updater scheduler stopped")
    
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
        """Обновить дневные данные для всех тикеров."""
        logger.info("Updating daily data for all tickers...")
        self._update_timeframe_data('1d')
    
    def update_hourly_data(self):
        """Обновить часовые данные для всех тикеров."""
        logger.info("Updating hourly data for all tickers...")
        self._update_timeframe_data('1h')
    
    def update_minute_data(self):
        """Обновить минутные данные для всех тикеров."""
        logger.info("Updating minute data for all tickers...")
        self._update_timeframe_data('1m')
    
    def update_5min_data(self):
        """Обновить 5-минутные данные для всех тикеров."""
        logger.info("Updating 5-minute data for all tickers...")
        self._update_timeframe_data('5m')
    
    def update_15min_data(self):
        """Обновить 15-минутные данные для всех тикеров."""
        logger.info("Updating 15-minute data for all tickers...")
        self._update_timeframe_data('15m')
    
    def _update_timeframe_data(self, timeframe: str):
        """Обновить данные для указанного таймфрейма для всех тикеров."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Получаем ВСЕ символы из базы данных
            cursor.execute("SELECT DISTINCT contract_code FROM companies ORDER BY contract_code")
            all_symbols = [row[0] for row in cursor.fetchall()]
            
            # Обновляем статистику
            self.update_stats['total_symbols'] = len(all_symbols)
            
            # Получаем FIGI маппинг
            figi_mapping = self.analyzer.get_figi_mapping()
            
            updated_count = 0
            error_count = 0
            
            # Обрабатываем символы батчами для оптимизации
            batch_size = 10  # Обрабатываем по 10 символов за раз
            
            for i in range(0, len(all_symbols), batch_size):
                batch_symbols = all_symbols[i:i + batch_size]
                
                # Обрабатываем батч
                batch_updated, batch_errors = self._process_symbol_batch(
                    batch_symbols, timeframe, figi_mapping, conn
                )
                
                updated_count += batch_updated
                error_count += batch_errors
                
                # Обновляем статистику
                self.update_stats['successful_updates'] += batch_updated
                self.update_stats['failed_updates'] += batch_errors
                
                # Небольшая пауза между батчами
                time.sleep(0.1)
            
            conn.close()
            logger.info(f"Updated {updated_count} symbols for {timeframe}, {error_count} errors")
            
        except Exception as e:
            logger.error(f"Error updating {timeframe} data: {e}")
    
    def _process_symbol_batch(self, symbols: List[str], timeframe: str, 
                            figi_mapping: Dict, conn) -> Tuple[int, int]:
        """Обработать батч символов."""
        updated_count = 0
        error_count = 0
        
        for symbol in symbols:
            try:
                # Проверяем rate limit перед каждым запросом
                self._wait_for_rate_limit('GetCandles')
                
                figi = figi_mapping.get(symbol)
                if not figi:
                    logger.warning(f"FIGI not found for {symbol}")
                    error_count += 1
                    continue
                
                # Получаем данные через API
                data = self.analyzer.get_stock_data(figi, timeframe)
                
                if data.empty:
                    logger.warning(f"No data returned for {symbol} ({timeframe})")
                    error_count += 1
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
                    time.sleep(5)
                else:
                    logger.error(f"Error updating {symbol} ({timeframe}): {e}")
        
        return updated_count, error_count
    
    def _save_timeframe_data(self, conn, symbol: str, timeframe: str, data: pd.DataFrame):
        """Сохранить данные таймфрейма в БД."""
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
    
    def get_update_stats(self) -> Dict:
        """Получить статистику обновлений."""
        return {
            'is_running': self.is_running,
            'last_update': self.update_stats['last_update'],
            'update_count': self.update_stats['update_count'],
            'errors': self.update_stats['errors'],
            'rate_limit_hits': self.update_stats['rate_limit_hits'],
            'current_requests_per_minute': len(self.request_times),
            'total_symbols': self.update_stats['total_symbols'],
            'successful_updates': self.update_stats['successful_updates'],
            'failed_updates': self.update_stats['failed_updates']
        }
    
    def get_timeframe_status(self, timeframe: str) -> Dict:
        """Получить статус обновления для конкретного таймфрейма."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Проверяем, существует ли таблица
            table_name = f"data_{timeframe.replace('m', 'min').replace('h', 'hour')}"
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
        timeframes = ['1d', '1h', '1m', '5m', '15m']
        return {tf: self.get_timeframe_status(tf) for tf in timeframes}
    
    def get_symbols_by_timeframe(self, timeframe: str) -> List[str]:
        """Получить список символов для конкретного таймфрейма."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            table_name = f"data_{timeframe.replace('m', 'min').replace('h', 'hour')}"
            cursor.execute(f"SELECT DISTINCT symbol FROM {table_name} ORDER BY symbol")
            symbols = [row[0] for row in cursor.fetchall()]
            return symbols
        except Exception as e:
            logger.error(f"Error getting symbols for {timeframe}: {e}")
            return []
        finally:
            conn.close()
    
    def get_latest_data_for_symbol(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Получить последние данные для конкретного символа и таймфрейма."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            table_name = f"data_{timeframe.replace('m', 'min').replace('h', 'hour')}"
            cursor.execute(f"""
                SELECT * FROM {table_name} 
                WHERE symbol = ? 
                ORDER BY datetime DESC 
                LIMIT 1
            """, (symbol,))
            
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Error getting latest data for {symbol} ({timeframe}): {e}")
            return None
        finally:
            conn.close()


def create_optimized_data_updater(api_key: str, max_requests_per_minute: int = 50) -> OptimizedDataUpdater:
    """Создать оптимизированный DataUpdater."""
    return OptimizedDataUpdater(api_key, max_requests_per_minute)
