"""
DataUpdater with Shares Support.
DataUpdater с поддержкой акций (shares) и фьючерсов (futures).
"""

import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import pandas as pd

from .multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
from .shares_integration import SharesIntegrator
from .database import get_connection

logger = logging.getLogger(__name__)


class DataUpdaterWithShares:
    """DataUpdater с поддержкой акций и фьючерсов."""
    
    def __init__(self, api_key: str, max_requests_per_minute: int = 30):
        self.api_key = api_key
        self.max_requests_per_minute = max_requests_per_minute
        self.analyzer = EnhancedMultiTimeframeStockAnalyzer(api_key=api_key)
        self.shares_integrator = SharesIntegrator()
        self.is_running = False
        self.scheduler_thread = None
        
        # Rate limiting
        self.request_times = []
        self.request_lock = threading.Lock()
        
        # Deadline'ы для разных методов
        self.deadlines = {
            'GetCandles': 500,
            'GetLastPrices': 500,
            'GetOrderBook': 500,
            'GetTradingStatus': 500,
            'GetInfo': 1000,
        }
        
        # Настройки обновления
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
            'failed_updates': 0,
            'shares_updated': 0,
            'futures_updated': 0
        }
    
    def _wait_for_rate_limit(self, method: str = 'GetCandles', timeframe: str = None):
        """Ожидать с учетом deadline'а метода."""
        with self.request_lock:
            now = time.time()
            deadline_seconds = self.deadlines.get(method, 500) / 1000.0
            
            # Для минутных данных используем более консервативный лимит
            if timeframe == '1m':
                max_requests = min(self.max_requests_per_minute, 20)  # Максимум 20 запросов в минуту для 1m
            else:
                max_requests = self.max_requests_per_minute
            
            # Удаляем запросы старше минуты
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            # Если достигнут лимит, ждем
            if len(self.request_times) >= max_requests:
                wait_time = 60 - (now - self.request_times[0])
                if wait_time > 0:
                    logger.warning(f"Rate limit reached for {timeframe or 'default'}. Waiting {wait_time:.1f} seconds...")
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
        
        logger.info("DataUpdater with shares support scheduler started")
        
        # Запускаем в отдельном потоке
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """Остановить планировщик обновления."""
        self.is_running = False
        schedule.clear()
        logger.info("DataUpdater with shares support scheduler stopped")
    
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
        """Обновить дневные данные для всех активов."""
        logger.info("Updating daily data for all assets (shares + futures)...")
        self._update_timeframe_data('1d')
    
    def update_hourly_data(self):
        """Обновить часовые данные для всех активов."""
        logger.info("Updating hourly data for all assets (shares + futures)...")
        self._update_timeframe_data('1h')
    
    def update_minute_data(self):
        """Обновить минутные данные для всех активов."""
        logger.info("Updating minute data for all assets (shares + futures)...")
        self._update_timeframe_data('1m')
    
    def update_5min_data(self):
        """Обновить 5-минутные данные для всех активов."""
        logger.info("Updating 5-minute data for all assets (shares + futures)...")
        self._update_timeframe_data('5m')
    
    def update_15min_data(self):
        """Обновить 15-минутные данные для всех активов."""
        logger.info("Updating 15-minute data for all assets (shares + futures)...")
        self._update_timeframe_data('15m')
    
    def _update_timeframe_data(self, timeframe: str):
        """Обновить данные для указанного таймфрейма для всех активов."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Получаем ТОЛЬКО акции из базы данных (фьючерсы пока не поддерживаются)
            cursor.execute("""
                SELECT DISTINCT contract_code, asset_type 
                FROM companies 
                WHERE asset_type = 'shares'
                ORDER BY contract_code
            """)
            all_assets = [(row[0], row[1]) for row in cursor.fetchall()]
            
            logger.info(f"Processing {len(all_assets)} shares for {timeframe} update")
            
            # Обновляем статистику
            self.update_stats['total_symbols'] = len(all_assets)
            self.update_stats['shares_updated'] = 0
            self.update_stats['futures_updated'] = 0
            
            # Получаем FIGI маппинг
            figi_mapping = self.analyzer.get_figi_mapping()
            
            updated_count = 0
            error_count = 0
            shares_updated = 0
            futures_updated = 0
            
            # Обрабатываем активы батчами для оптимизации
            batch_size = 10
            
            for i in range(0, len(all_assets), batch_size):
                batch_assets = all_assets[i:i + batch_size]
                
                # Обрабатываем батч
                batch_updated, batch_errors, batch_shares, batch_futures = self._process_asset_batch(
                    batch_assets, timeframe, figi_mapping, conn
                )
                
                updated_count += batch_updated
                error_count += batch_errors
                shares_updated += batch_shares
                # futures_updated += batch_futures  # Фьючерсы не обрабатываются
                
                # Обновляем статистику
                self.update_stats['successful_updates'] += batch_updated
                self.update_stats['failed_updates'] += batch_errors
                self.update_stats['shares_updated'] += batch_shares
                # self.update_stats['futures_updated'] += batch_futures  # Фьючерсы не обрабатываются
                
                # Небольшая пауза между батчами
                time.sleep(0.1)
            
            conn.close()
            logger.info(f"Updated {updated_count} shares for {timeframe}: {shares_updated} successful, {error_count} errors")
            
        except Exception as e:
            logger.error(f"Error updating {timeframe} data: {e}")
    
    def _process_asset_batch(self, assets: List[Tuple[str, str]], timeframe: str, 
                            figi_mapping: Dict, conn) -> Tuple[int, int, int, int]:
        """Обработать батч активов."""
        updated_count = 0
        error_count = 0
        shares_updated = 0
        futures_updated = 0
        
        for contract_code, asset_type in assets:
            try:
                # Для акций используем FIGI, для фьючерсов - contract_code
                if asset_type == 'shares':
                    figi = figi_mapping.get(contract_code)
                    if not figi:
                        logger.warning(f"FIGI not found for {contract_code} ({asset_type})")
                        error_count += 1
                        continue
                    
                    # Проверяем rate limit ТОЛЬКО для реальных запросов к API
                    self._wait_for_rate_limit('GetCandles', timeframe)
                    
                    # Получаем данные через API для акций
                    data = self.analyzer.get_stock_data(figi, timeframe)
                else:
                    # Для фьючерсов используем contract_code напрямую
                    logger.info(f"Updating futures data for {contract_code} ({asset_type})")
                    # Пока что пропускаем фьючерсы, так как у них нет FIGI
                    logger.warning(f"Skipping futures {contract_code} - no FIGI available")
                    error_count += 1
                    continue
                
                if data.empty:
                    logger.warning(f"No data returned for {contract_code} ({asset_type}, {timeframe})")
                    error_count += 1
                    continue
                
                # Сохраняем в БД
                self._save_timeframe_data(conn, contract_code, timeframe, data)
                updated_count += 1
                
                # Обновляем счетчики по типам активов (только для акций)
                if asset_type == 'shares':
                    shares_updated += 1
                
                # Обновляем статистику
                self.update_stats['last_update'][f"{contract_code}_{timeframe}"] = datetime.now().isoformat()
                self.update_stats['update_count'][f"{contract_code}_{timeframe}"] = self.update_stats['update_count'].get(f"{contract_code}_{timeframe}", 0) + 1
                
            except Exception as e:
                error_count += 1
                error_key = f"{contract_code}_{timeframe}"
                self.update_stats['errors'][error_key] = str(e)
                
                # Проверяем, не rate limit ли это
                if "30014" in str(e) or "rate" in str(e).lower():
                    self.update_stats['rate_limit_hits'] += 1
                    logger.warning(f"Rate limit hit for {contract_code} ({asset_type}, {timeframe}): {e}")
                    time.sleep(5)
                else:
                    logger.error(f"Error updating {contract_code} ({asset_type}, {timeframe}): {e}")
        
        return updated_count, error_count, shares_updated, futures_updated
    
    def _save_timeframe_data(self, conn, contract_code: str, timeframe: str, data: pd.DataFrame):
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
                contract_code,  # Используем contract_code как symbol
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
            'failed_updates': self.update_stats['failed_updates'],
            'shares_updated': self.update_stats['shares_updated'],
            'futures_updated': self.update_stats['futures_updated']
        }
    
    def get_asset_statistics(self) -> Dict:
        """Получить статистику по типам активов."""
        return self.shares_integrator.get_asset_statistics()
    
    def get_shares_list(self) -> List[str]:
        """Получить список акций."""
        return self.shares_integrator.get_shares_only()
    
    def get_futures_list(self) -> List[str]:
        """Получить список фьючерсов."""
        return self.shares_integrator.get_futures_only()
    
    def get_all_assets_list(self) -> List[str]:
        """Получить список всех активов."""
        return self.shares_integrator.get_all_assets()
    
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
    
    def integrate_shares(self):
        """Интегрировать акции в систему."""
        logger.info("Starting shares integration...")
        self.shares_integrator.integrate_shares_into_database(self.api_key)
        logger.info("Shares integration completed")


def create_data_updater_with_shares(api_key: str, max_requests_per_minute: int = 30) -> DataUpdaterWithShares:
    """Создать DataUpdater с поддержкой акций."""
    return DataUpdaterWithShares(api_key, max_requests_per_minute)
