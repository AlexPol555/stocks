"""
Shares Integration Module.
Модуль интеграции акций (shares) в существующую систему.
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class SharesIntegrator:
    """Интегратор акций в существующую систему."""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_path = db_path
    
    def add_shares_support_to_companies_table(self):
        """Добавить поддержку акций в таблицу companies."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Добавляем новые колонки для акций
            cursor.execute("""
                ALTER TABLE companies ADD COLUMN asset_type TEXT DEFAULT 'futures';
            """)
            logger.info("Added asset_type column to companies table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info("asset_type column already exists")
            else:
                logger.error(f"Error adding asset_type column: {e}")
        
        try:
            cursor.execute("""
                ALTER TABLE companies ADD COLUMN ticker TEXT;
            """)
            logger.info("Added ticker column to companies table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info("ticker column already exists")
            else:
                logger.error(f"Error adding ticker column: {e}")
        
        try:
            cursor.execute("""
                ALTER TABLE companies ADD COLUMN lot_size INTEGER DEFAULT 1;
            """)
            logger.info("Added lot_size column to companies table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info("lot_size column already exists")
            else:
                logger.error(f"Error adding lot_size column: {e}")
        
        try:
            cursor.execute("""
                ALTER TABLE companies ADD COLUMN currency TEXT DEFAULT 'RUB';
            """)
            logger.info("Added currency column to companies table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info("currency column already exists")
            else:
                logger.error(f"Error adding currency column: {e}")
        
        try:
            cursor.execute("""
                ALTER TABLE companies ADD COLUMN min_price_increment REAL DEFAULT 0.01;
            """)
            logger.info("Added min_price_increment column to companies table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info("min_price_increment column already exists")
            else:
                logger.error(f"Error adding min_price_increment column: {e}")
        
        conn.commit()
        conn.close()
        logger.info("Successfully added shares support to companies table")
    
    def load_shares_from_tinkoff_api(self, api_key: str, russian_only: bool = True) -> List[Dict]:
        """Загрузить акции из Tinkoff API с правильной фильтрацией через параметры API."""
        try:
            from tinkoff.invest import Client as _Client
            from tinkoff.invest.schemas import InstrumentStatus, ShareType
        except ImportError:
            logger.error("Tinkoff SDK not installed. Install with: pip install tinkoff-invest")
            return []
        
        try:
            with _Client(api_key) as client:
                # Используем правильные параметры API для фильтрации
                if russian_only:
                    # Загружаем только базовые инструменты (российские)
                    instruments = client.instruments.shares(
                        instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE
                    ).instruments
                    logger.info("Loading Russian shares using INSTRUMENT_STATUS_BASE filter")
                else:
                    # Загружаем все инструменты
                    instruments = client.instruments.shares(
                        instrument_status=InstrumentStatus.INSTRUMENT_STATUS_ALL
                    ).instruments
                    logger.info("Loading all shares using INSTRUMENT_STATUS_ALL filter")
                
                shares_data = []
                total_count = 0
                
                for share in instruments:
                    if not getattr(share, "ticker", None):
                        continue
                    
                    total_count += 1
                    
                    # Дополнительная фильтрация по типу акций (только обыкновенные и привилегированные)
                    share_type = getattr(share, 'share_type', None)
                    if share_type and share_type not in [ShareType.SHARE_TYPE_COMMON, ShareType.SHARE_TYPE_PREFERRED]:
                        continue
                    
                    # Дополнительная фильтрация для российских акций
                    if russian_only:
                        currency = getattr(share, 'currency', '')
                        isin = getattr(share, 'isin', '')
                        
                        # Фильтруем только RUB валюту и RU ISIN
                        if currency != 'RUB' and not isin.startswith('RU'):
                            continue
                    
                    # Преобразуем min_price_increment в число
                    min_price_increment = getattr(share, 'min_price_increment', 0.01)
                    if hasattr(min_price_increment, 'units') and hasattr(min_price_increment, 'nano'):
                        # Это объект Quotation, преобразуем в число
                        min_price_increment = float(min_price_increment.units) + float(min_price_increment.nano) / 1e9
                    elif not isinstance(min_price_increment, (int, float)):
                        min_price_increment = 0.01
                    
                    shares_data.append({
                        'ticker': share.ticker,
                        'figi': share.figi,
                        'name': getattr(share, 'name', ''),
                        'isin': getattr(share, 'isin', ''),
                        'lot_size': getattr(share, 'lot', 1),
                        'currency': getattr(share, 'currency', 'RUB'),
                        'min_price_increment': min_price_increment,
                        'trading_status': getattr(share, 'trading_status', 'UNKNOWN'),
                        'share_type': getattr(share, 'share_type', ShareType.SHARE_TYPE_COMMON),
                        'asset_type': 'shares'
                    })
                
                if russian_only:
                    logger.info(f"Loaded {len(shares_data)} Russian shares using API filter (from {total_count} total)")
                else:
                    logger.info(f"Loaded {len(shares_data)} shares using API filter (from {total_count} total)")
                
                return shares_data
                
        except Exception as e:
            logger.error(f"Error loading shares from Tinkoff API: {e}")
            return []
    
    def _is_russian_share(self, share) -> bool:
        """Определить, является ли акция российской."""
        # Список известных российских тикеров
        russian_tickers = {
            'SBER', 'GAZP', 'LKOH', 'ROSN', 'VTBR', 'NVTK', 'MAGN', 'NLMK', 'CHMF', 'PLZL',
            'ALRS', 'AFLT', 'YNDX', 'OZON', 'TCSG', 'POLY', 'GMKN', 'RUAL', 'MTSS', 'MOEX',
            'SBERP', 'GAZPP', 'LKOHP', 'ROSNP', 'VTBRP', 'NVTKP', 'MAGNP', 'NLMKP', 'CHMFP', 'PLZLP',
            'ALRSP', 'AFLTP', 'YNDXP', 'OZONP', 'TCSGP', 'POLYP', 'GMKNP', 'RUALP', 'MTSSP', 'MOEXP',
            'SBER', 'GAZP', 'LKOH', 'ROSN', 'VTBR', 'NVTK', 'MAGN', 'NLMK', 'CHMF', 'PLZL',
            'ALRS', 'AFLT', 'YNDX', 'OZON', 'TCSG', 'POLY', 'GMKN', 'RUAL', 'MTSS', 'MOEX',
            'SBERP', 'GAZPP', 'LKOHP', 'ROSNP', 'VTBRP', 'NVTKP', 'MAGNP', 'NLMKP', 'CHMFP', 'PLZLP',
            'ALRSP', 'AFLTP', 'YNDXP', 'OZONP', 'TCSGP', 'POLYP', 'GMKNP', 'RUALP', 'MTSSP', 'MOEXP'
        }
        
        # Проверяем по тикеру
        ticker = getattr(share, 'ticker', '')
        if ticker in russian_tickers:
            return True
        
        # Проверяем по валюте (RUB)
        currency = getattr(share, 'currency', '')
        if currency == 'RUB':
            return True
        
        # Проверяем по названию (содержит русские слова)
        name = getattr(share, 'name', '')
        russian_keywords = [
            'Сбербанк', 'Газпром', 'Лукойл', 'Роснефть', 'ВТБ', 'Новатэк', 'Магнит', 'НЛМК',
            'Северсталь', 'Полюс', 'Алроса', 'Аэрофлот', 'Яндекс', 'Озон', 'Тинькофф', 'Полиметалл',
            'Норникель', 'РУСАЛ', 'МТС', 'Московская биржа', 'Россия', 'Russian', 'Российская'
        ]
        
        for keyword in russian_keywords:
            if keyword.lower() in name.lower():
                return True
        
        # Проверяем по ISIN (российские ISIN начинаются с RU)
        isin = getattr(share, 'isin', '')
        if isin.startswith('RU'):
            return True
        
        return False
    
    def integrate_shares_into_database(self, api_key: str, russian_only: bool = True):
        """Интегрировать акции в базу данных с правильной фильтрацией через API."""
        # Сначала добавляем поддержку акций в таблицу
        self.add_shares_support_to_companies_table()
        
        # Загружаем акции из API с правильной фильтрацией через параметры API
        shares_data = self.load_shares_from_tinkoff_api(api_key, russian_only)
        
        if not shares_data:
            logger.warning("No shares data loaded from API")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Вставляем акции в таблицу companies
            for share in shares_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO companies 
                    (contract_code, ticker, name, isin, figi, asset_type, lot_size, currency, min_price_increment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    share['ticker'],  # Используем ticker как contract_code для совместимости
                    share['ticker'],
                    share['name'],
                    share['isin'],
                    share['figi'],
                    share['asset_type'],
                    share['lot_size'],
                    share['currency'],
                    share['min_price_increment']
                ))
            
            conn.commit()
            logger.info(f"Successfully integrated {len(shares_data)} shares into database")
            
        except Exception as e:
            logger.error(f"Error integrating shares into database: {e}")
        finally:
            conn.close()
    
    def get_asset_type_mapping(self) -> Dict[str, str]:
        """Получить маппинг contract_code -> asset_type."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT contract_code, asset_type 
                FROM companies 
                WHERE asset_type IS NOT NULL
            """)
            
            mapping = {row[0]: row[1] for row in cursor.fetchall()}
            return mapping
            
        except Exception as e:
            logger.error(f"Error getting asset type mapping: {e}")
            return {}
        finally:
            conn.close()
    
    def get_shares_only(self) -> List[str]:
        """Получить список только акций (shares)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT contract_code 
                FROM companies 
                WHERE asset_type = 'shares'
                ORDER BY contract_code
            """)
            
            shares = [row[0] for row in cursor.fetchall()]
            return shares
            
        except Exception as e:
            logger.error(f"Error getting shares list: {e}")
            return []
        finally:
            conn.close()
    
    def get_futures_only(self) -> List[str]:
        """Получить список только фьючерсов."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT contract_code 
                FROM companies 
                WHERE asset_type = 'futures' OR asset_type IS NULL
                ORDER BY contract_code
            """)
            
            futures = [row[0] for row in cursor.fetchall()]
            return futures
            
        except Exception as e:
            logger.error(f"Error getting futures list: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_assets(self) -> List[str]:
        """Получить список всех активов (акции + фьючерсы)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT contract_code 
                FROM companies 
                ORDER BY contract_code
            """)
            
            assets = [row[0] for row in cursor.fetchall()]
            return assets
            
        except Exception as e:
            logger.error(f"Error getting all assets list: {e}")
            return []
        finally:
            conn.close()
    
    def update_existing_futures_asset_type(self):
        """Обновить существующие фьючерсы, установив asset_type = 'futures'."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Обновляем существующие записи, которые выглядят как фьючерсы
            cursor.execute("""
                UPDATE companies 
                SET asset_type = 'futures'
                WHERE asset_type IS NULL 
                AND (contract_code LIKE 'Si%' 
                     OR contract_code LIKE 'BR%' 
                     OR contract_code LIKE '%-F'
                     OR contract_code LIKE 'RTS%')
            """)
            
            updated_count = cursor.rowcount
            conn.commit()
            logger.info(f"Updated {updated_count} existing records to asset_type = 'futures'")
            
        except Exception as e:
            logger.error(f"Error updating existing futures asset type: {e}")
        finally:
            conn.close()
    
    def get_asset_statistics(self) -> Dict:
        """Получить статистику по типам активов."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    COALESCE(asset_type, 'unknown') as asset_type,
                    COUNT(*) as count
                FROM companies 
                GROUP BY asset_type
                ORDER BY count DESC
            """)
            
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            return stats
            
        except Exception as e:
            logger.error(f"Error getting asset statistics: {e}")
            return {}
        finally:
            conn.close()


def integrate_shares_system(api_key: str, db_path: str = "stock_data.db"):
    """Основная функция интеграции акций в систему."""
    integrator = SharesIntegrator(db_path)
    
    logger.info("Starting shares integration...")
    
    # 1. Обновляем существующие фьючерсы
    integrator.update_existing_futures_asset_type()
    
    # 2. Интегрируем акции
    integrator.integrate_shares_into_database(api_key)
    
    # 3. Получаем статистику
    stats = integrator.get_asset_statistics()
    logger.info(f"Asset statistics: {stats}")
    
    return integrator


if __name__ == "__main__":
    # Пример использования
    import os
    
    api_key = os.getenv('TINKOFF_API_KEY')
    if not api_key:
        print("Please set TINKOFF_API_KEY environment variable")
        exit(1)
    
    integrator = integrate_shares_system(api_key)
    
    print("Shares integration completed!")
    print(f"Shares: {len(integrator.get_shares_only())}")
    print(f"Futures: {len(integrator.get_futures_only())}")
    print(f"Total assets: {len(integrator.get_all_assets())}")
