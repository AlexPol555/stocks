"""Helper functions for multi-timeframe database operations."""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def add_multi_timeframe_tables(conn: sqlite3.Connection):
    """Р”РѕР±Р°РІРёС‚СЊ С‚Р°Р±Р»РёС†С‹ РґР»СЏ СЂР°Р·РЅС‹С… С‚Р°Р№РјС„СЂРµР№РјРѕРІ."""
    cursor = conn.cursor()
    
    # 19) РўР°Р±Р»РёС†Р° С‡Р°СЃРѕРІС‹С… РґР°РЅРЅС‹С…
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_1hour (
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
    );
    """)

    # 20) РўР°Р±Р»РёС†Р° РјРёРЅСѓС‚РЅС‹С… РґР°РЅРЅС‹С…
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_1min (
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
    );
    """)

    # 21) РўР°Р±Р»РёС†Р° 5-РјРёРЅСѓС‚РЅС‹С… РґР°РЅРЅС‹С…
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_5min (
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
    );
    """)

    # 22) РўР°Р±Р»РёС†Р° 15-РјРёРЅСѓС‚РЅС‹С… РґР°РЅРЅС‹С…
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_15min (
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
    );
    """)

    # 23) РўР°Р±Р»РёС†Р° СЃРµРєСѓРЅРґРЅС‹С… РґР°РЅРЅС‹С… (Р·Р°РіРѕС‚РѕРІРєР° РґР»СЏ Р±СѓРґСѓС‰РµРіРѕ)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_1sec (
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
    );
    """)

    # 24) РўР°Р±Р»РёС†Р° С‚РёРєРѕРІС‹С… РґР°РЅРЅС‹С… (Р·Р°РіРѕС‚РѕРІРєР° РґР»СЏ Р±СѓРґСѓС‰РµРіРѕ)
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
    );
    """)

    # 25) РўР°Р±Р»РёС†Р° РЅР°СЃС‚СЂРѕРµРє РѕР±РЅРѕРІР»РµРЅРёСЏ РґР°РЅРЅС‹С…
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_update_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        enabled BOOLEAN DEFAULT TRUE,
        update_1d BOOLEAN DEFAULT TRUE,
        update_1h BOOLEAN DEFAULT TRUE,
        update_1m BOOLEAN DEFAULT TRUE,
        update_5m BOOLEAN DEFAULT TRUE,
        update_15m BOOLEAN DEFAULT TRUE,
        update_1s BOOLEAN DEFAULT FALSE, -- РџРѕРєР° РѕС‚РєР»СЋС‡РµРЅРѕ
        update_tick BOOLEAN DEFAULT FALSE, -- РџРѕРєР° РѕС‚РєР»СЋС‡РµРЅРѕ
        last_update_1d TEXT,
        last_update_1h TEXT,
        last_update_1m TEXT,
        last_update_5m TEXT,
        last_update_15m TEXT,
        last_update_1s TEXT,
        last_update_tick TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 26) РўР°Р±Р»РёС†Р° СЃС‚Р°С‚РёСЃС‚РёРєРё РѕР±РЅРѕРІР»РµРЅРёР№
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_update_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timeframe TEXT NOT NULL,
        symbol TEXT NOT NULL,
        last_update TEXT NOT NULL,
        update_count INTEGER DEFAULT 1,
        error_count INTEGER DEFAULT 0,
        last_error TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(timeframe, symbol)
    );
    """)
    
    conn.commit()
    logger.info("Multi-timeframe tables created successfully")


def get_timeframe_data(conn: sqlite3.Connection, symbol: str, timeframe: str, 
                      limit: int = 1000) -> pd.DataFrame:
    """РџРѕР»СѓС‡РёС‚СЊ РґР°РЅРЅС‹Рµ РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ СЃРёРјРІРѕР»Р° Рё С‚Р°Р№РјС„СЂРµР№РјР°."""
    table_name = f"data_{timeframe.replace('m', 'min').replace('h', 'hour')}"
    
    query = f"""
        SELECT datetime, open, high, low, close, volume
        FROM {table_name}
        WHERE symbol = ?
        ORDER BY datetime DESC
        LIMIT ?
    """
    
    try:
        df = pd.read_sql_query(query, conn, params=(symbol, limit))
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime').reset_index(drop=True)
        return df
    except Exception as e:
        logger.error(f"Error getting {timeframe} data for {symbol}: {e}")
        return pd.DataFrame()


def save_timeframe_data(conn: sqlite3.Connection, symbol: str, timeframe: str, 
                       data: pd.DataFrame) -> int:
    """РЎРѕС…СЂР°РЅРёС‚СЊ РґР°РЅРЅС‹Рµ С‚Р°Р№РјС„СЂРµР№РјР° РІ Р‘Р”."""
    cursor = conn.cursor()
    
    table_name = f"data_{timeframe.replace('m', 'min').replace('h', 'hour')}"
    
    # РЎРѕР·РґР°РµРј С‚Р°Р±Р»РёС†Сѓ, РµСЃР»Рё РЅРµ СЃСѓС‰РµСЃС‚РІСѓРµС‚
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
    saved_count = 0
    for _, row in data.iterrows():
        try:
            cursor.execute(f"""
                INSERT OR REPLACE INTO {table_name}
                (symbol, datetime, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                row['time'].isoformat() if 'time' in row else row['datetime'],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row['volume']
            ))
            saved_count += 1
        except Exception as e:
            logger.error(f"Error saving row for {symbol} ({timeframe}): {e}")
    
    conn.commit()
    return saved_count


def get_available_timeframes() -> List[str]:
    """РџРѕР»СѓС‡РёС‚СЊ СЃРїРёСЃРѕРє РґРѕСЃС‚СѓРїРЅС‹С… С‚Р°Р№РјС„СЂРµР№РјРѕРІ."""
    return ['1d', '1h', '1m', '5m', '15m', '1s', 'tick']


def get_timeframe_table_name(timeframe: str) -> str:
    """РџРѕР»СѓС‡РёС‚СЊ РёРјСЏ С‚Р°Р±Р»РёС†С‹ РґР»СЏ С‚Р°Р№РјС„СЂРµР№РјР°."""
    return f"data_{timeframe.replace('m', 'min').replace('h', 'hour')}"


def update_data_stats(conn: sqlite3.Connection, symbol: str, timeframe: str, 
                     success: bool = True, error_message: str = None):
    """РћР±РЅРѕРІРёС‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ РѕР±РЅРѕРІР»РµРЅРёСЏ РґР°РЅРЅС‹С…."""
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    if success:
        cursor.execute("""
            INSERT OR REPLACE INTO data_update_stats
            (timeframe, symbol, last_update, update_count, error_count, last_error, updated_at)
            VALUES (?, ?, ?, 
                    COALESCE((SELECT update_count FROM data_update_stats WHERE timeframe = ? AND symbol = ?), 0) + 1,
                    COALESCE((SELECT error_count FROM data_update_stats WHERE timeframe = ? AND symbol = ?), 0),
                    NULL, ?)
        """, (timeframe, symbol, now, timeframe, symbol, timeframe, symbol, now))
    else:
        cursor.execute("""
            INSERT OR REPLACE INTO data_update_stats
            (timeframe, symbol, last_update, update_count, error_count, last_error, updated_at)
            VALUES (?, ?, ?, 
                    COALESCE((SELECT update_count FROM data_update_stats WHERE timeframe = ? AND symbol = ?), 0),
                    COALESCE((SELECT error_count FROM data_update_stats WHERE timeframe = ? AND symbol = ?), 0) + 1,
                    ?, ?)
        """, (timeframe, symbol, now, timeframe, symbol, timeframe, symbol, error_message, now))
    
    conn.commit()


def get_data_update_stats(conn: sqlite3.Connection) -> pd.DataFrame:
    """РџРѕР»СѓС‡РёС‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ РѕР±РЅРѕРІР»РµРЅРёСЏ РґР°РЅРЅС‹С…."""
    query = """
        SELECT timeframe, symbol, last_update, update_count, error_count, last_error
        FROM data_update_stats
        ORDER BY last_update DESC
    """
    return pd.read_sql_query(query, conn)
