# database.py (заменить/вставить этим содержимым)
from __future__ import annotations

from pathlib import Path
import sqlite3
import decimal
import logging
import pandas as pd
from typing import Optional, Dict, Any, Union

from core.settings import get_settings

sqlite3.register_adapter(decimal.Decimal, float)
logger = logging.getLogger(__name__)

# Database paths are resolved via environment variables or core.settings.

def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Create a sqlite3 connection using configured project paths."""
    settings = get_settings()
    target = Path(db_path).expanduser().resolve() if db_path else settings.database_path
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target.as_posix(), check_same_thread=False, isolation_level=None)
    return conn


def create_tables(conn: sqlite3.Connection):
    """
    Создаёт необходимые таблицы (IF NOT EXISTS) и выполняет простую миграцию contract_code
    из company_parameters -> companies (INSERT OR IGNORE).
    """
    cursor = conn.cursor()

    # 1) Таблица company_parameters (оставляем, чтобы не ломать логику параметров)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_parameters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_code TEXT UNIQUE,
        stop_loss_multiplier REAL,
        take_profit_multiplier REAL,
        max_holding_days INTEGER,
        rsi_period INTEGER,
        macd_fast_period INTEGER,
        macd_slow_period INTEGER,
        macd_signal_period INTEGER,
        bb_period INTEGER,
        bb_std_multiplier REAL
    );
    """)

    # 2) Таблица companies — требуется для JOIN-ов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_code TEXT UNIQUE,
        name TEXT,
        isin TEXT,
        figi TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3) Таблица daily_data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        date TEXT,
        open REAL,
        low REAL,
        high REAL,
        close REAL,
        volume REAL,
        FOREIGN KEY(company_id) REFERENCES companies(id),
        UNIQUE (company_id, date)
    );
    """)

    # 4) Таблица технических индикаторов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS technical_indicators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        date TEXT,
        sma REAL,
        ema REAL,
        rsi REAL,
        macd REAL,
        macd_signal REAL,
        bb_upper REAL,
        bb_middle REAL,
        bb_lower REAL,
        FOREIGN KEY(company_id) REFERENCES companies(id),
        UNIQUE(company_id, date)
    );
    """)

    # 5) Таблица метрик
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        metric_type TEXT,
        value1 REAL,
        value2 REAL,
        value3 REAL,
        value4 REAL,
        value5 REAL,
        date TEXT,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)

    # 6) Безопасная миграция: если есть записи в company_parameters, переносим contract_code
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO companies (contract_code)
        SELECT DISTINCT contract_code FROM company_parameters WHERE contract_code IS NOT NULL AND contract_code != '';
        """)
    except Exception:
        # логируем не фатально
        logger.exception("Миграция contract_code из company_parameters не выполнена.")


    # 7) Demo trading tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS demo_accounts (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        balance REAL NOT NULL,
        initial_balance REAL NOT NULL,
        currency TEXT DEFAULT 'RUB',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS demo_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_code TEXT NOT NULL UNIQUE,
        company_id INTEGER,
        quantity REAL NOT NULL DEFAULT 0,
        avg_price REAL NOT NULL DEFAULT 0,
        realized_pl REAL NOT NULL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS demo_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_code TEXT NOT NULL,
        company_id INTEGER,
        side TEXT NOT NULL,
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        value REAL NOT NULL,
        fee REAL NOT NULL DEFAULT 0,
        realized_pl REAL NOT NULL DEFAULT 0,
        executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)

    # 8) Таблица торговых сигналов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trading_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        signal_type TEXT NOT NULL, -- 'long', 'short', 'close_long', 'close_short'
        signal_strength REAL NOT NULL, -- 0.0 to 1.0
        signal_score REAL NOT NULL, -- raw score before normalization
        price REAL NOT NULL,
        volume REAL,
        atr REAL,
        stop_loss REAL,
        take_profit REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        processed BOOLEAN DEFAULT FALSE,
        FOREIGN KEY(company_id) REFERENCES companies(id),
        UNIQUE(company_id, date, signal_type)
    );
    """)

    # 9) Таблица автоматических ордеров
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auto_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        contract_code TEXT NOT NULL,
        order_type TEXT NOT NULL, -- 'market', 'limit', 'stop', 'stop_limit'
        side TEXT NOT NULL, -- 'BUY', 'SELL'
        quantity REAL NOT NULL,
        price REAL,
        stop_price REAL,
        status TEXT DEFAULT 'pending', -- 'pending', 'submitted', 'filled', 'cancelled', 'rejected'
        tinkoff_order_id TEXT,
        error_message TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(signal_id) REFERENCES trading_signals(id),
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)

    # 10) Таблица настроек автоматической торговли
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auto_trading_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        enabled BOOLEAN DEFAULT FALSE,
        max_position_size REAL DEFAULT 10000.0,
        max_daily_orders INTEGER DEFAULT 10,
        min_signal_strength REAL DEFAULT 0.6,
        risk_per_trade REAL DEFAULT 0.02, -- 2% of account per trade
        stop_loss_atr_multiplier REAL DEFAULT 2.0,
        take_profit_atr_multiplier REAL DEFAULT 3.0,
        max_holding_days INTEGER DEFAULT 5,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 11) Таблица истории автоматических сделок
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auto_trade_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER NOT NULL,
        order_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        contract_code TEXT NOT NULL,
        side TEXT NOT NULL,
        quantity REAL NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL,
        stop_loss REAL,
        take_profit REAL,
        pnl REAL DEFAULT 0.0,
        pnl_percent REAL DEFAULT 0.0,
        holding_days INTEGER DEFAULT 0,
        exit_reason TEXT, -- 'stop_loss', 'take_profit', 'time_exit', 'manual'
        entry_date TEXT NOT NULL,
        exit_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(signal_id) REFERENCES trading_signals(id),
        FOREIGN KEY(order_id) REFERENCES auto_orders(id),
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)

    # 12) Таблица ML сигналов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ml_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        signal_type TEXT NOT NULL, -- 'STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'
        confidence REAL NOT NULL, -- 0.0 to 1.0
        price_signal TEXT,
        sentiment_signal TEXT,
        technical_signal TEXT,
        ensemble_signal TEXT,
        risk_level TEXT, -- 'LOW', 'MEDIUM', 'HIGH'
        price_prediction REAL,
        sentiment TEXT, -- 'positive', 'negative', 'neutral'
        sentiment_score REAL,
        sentiment_confidence REAL,
        price_confidence REAL,
        technical_confidence REAL,
        data_points INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, created_at)
    );
    """)

    # 13) Таблица ML метрик
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ml_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total_signals INTEGER,
        buy_signals INTEGER,
        sell_signals INTEGER,
        hold_signals INTEGER,
        avg_confidence REAL,
        high_risk_signals INTEGER,
        buy_ratio REAL,
        sell_ratio REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 14) Таблица ML кэша
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ml_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cache_key TEXT UNIQUE NOT NULL,
        cache_data TEXT NOT NULL, -- JSON data
        expires_at TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 15) Таблица ML моделей (гибридное хранение)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ml_models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        model_type TEXT NOT NULL,           -- 'lstm', 'gru', 'ensemble', 'sentiment'
        timeframe TEXT NOT NULL,            -- '1d', '1h', '1m', '1s' - для будущего масштабирования
        model_path TEXT NOT NULL,           -- Путь к файлу модели
        accuracy REAL,                      -- Точность модели
        mse REAL,                          -- Среднеквадратичная ошибка
        mae REAL,                          -- Средняя абсолютная ошибка
        rmse REAL,                         -- Корень из среднеквадратичной ошибки
        training_date TEXT NOT NULL,        -- Дата обучения
        data_points INTEGER,               -- Количество точек данных
        sequence_length INTEGER,           -- Длина последовательности
        hidden_size INTEGER,               -- Размер скрытого слоя
        epochs_trained INTEGER,            -- Количество эпох
        training_duration REAL,            -- Время обучения в секундах
        features_used TEXT,                -- JSON список используемых признаков
        hyperparameters TEXT,              -- JSON гиперпараметры
        model_version TEXT DEFAULT '1.0',  -- Версия модели
        is_active BOOLEAN DEFAULT 1,       -- Активна ли модель
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, model_type, timeframe, model_version)
    );
    """)

    # 16) Таблица кэша предсказаний ML
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ml_predictions_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        prediction_type TEXT NOT NULL,     -- 'price', 'sentiment', 'ensemble', 'signal'
        timeframe TEXT NOT NULL,           -- '1d', '1h', '1m', '1s'
        prediction_value REAL,
        confidence REAL,
        input_data TEXT,                   -- JSON входные данные
        prediction_date TEXT NOT NULL,
        expires_at TEXT NOT NULL,          -- Время истечения кэша
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, prediction_type, timeframe, prediction_date)
    );
    """)

    # 17) Таблица метрик производительности ML
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ml_performance_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        model_type TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        metric_name TEXT NOT NULL,         -- 'accuracy', 'precision', 'recall', 'f1_score'
        metric_value REAL NOT NULL,
        measurement_date TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 18) Таблица обучения ML (история)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ml_training_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        model_type TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        training_start TEXT NOT NULL,
        training_end TEXT NOT NULL,
        duration_seconds REAL NOT NULL,
        data_points INTEGER NOT NULL,
        epochs_trained INTEGER NOT NULL,
        final_accuracy REAL,
        final_loss REAL,
        hyperparameters TEXT,              -- JSON гиперпараметры
        training_status TEXT DEFAULT 'completed', -- 'completed', 'failed', 'cancelled'
        error_message TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()

def load_data_from_db(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Возвращает объединённые метрики (metrics) с кодом контракта (contract_code).
    """
    query = """
    SELECT c.contract_code, m.date, m.metric_type, m.value1, m.value2, m.value3, m.value4, m.value5
    FROM metrics m
    JOIN companies c ON m.company_id = c.id
    ORDER BY m.date
    """
    try:
        df = pd.read_sql_query(query, conn)
        return df.drop_duplicates()
    except Exception:
        logger.exception("Ошибка в load_data_from_db")
        return pd.DataFrame()

def load_daily_data_from_db(conn: sqlite3.Connection, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Возвращает данные daily_data вместе с contract_code.
    start_date и end_date — строковые даты в формате 'YYYY-MM-DD' (если заданы).
    """
    query = """
    SELECT 
        c.contract_code, 
        dd.date, 
        dd.open, 
        dd.low, 
        dd.high, 
        dd.close, 
        dd.volume
    FROM daily_data dd
    JOIN companies c ON dd.company_id = c.id
    WHERE 1=1
    """
    if start_date:
        query += f" AND dd.date >= '{start_date}'"
    if end_date:
        query += f" AND dd.date <= '{end_date}'"
    query += " ORDER BY dd.date;"
    try:
        df = pd.read_sql_query(query, conn)
        return df.drop_duplicates()
    except Exception:
        logger.exception("Ошибка в load_daily_data_from_db")
        return pd.DataFrame()

def update_technical_indicators(conn: sqlite3.Connection,
                                indicators: Dict[str, Any],
                                daily_data_id: Optional[int] = None,
                                company_id: Optional[int] = None,
                                date: Optional[str] = None):
    """
    Обновляет или вставляет запись в technical_indicators.
    Поддерживает обновление по daily_data_id (если используется) или по (company_id, date).
    Ожидаемый словарь indicators содержит ключи: sma, ema, rsi, macd, macd_signal, bb_upper, bb_middle, bb_lower.
    """
    cursor = conn.cursor()
    try:
        if daily_data_id is not None:
            # Если у вас есть связь daily_data_id -> нужно найти company_id и date из daily_data
            cursor.execute("SELECT company_id, date FROM daily_data WHERE id = ?", (daily_data_id,))
            row = cursor.fetchone()
            if row:
                company_id = row[0]
                date = row[1]
        if company_id is None or date is None:
            raise ValueError("Для обновления technical_indicators требуются company_id и date (или daily_data_id).")

        cursor.execute("SELECT id FROM technical_indicators WHERE company_id = ? AND date = ?", (company_id, date))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE technical_indicators
                SET sma = ?, ema = ?, rsi = ?, macd = ?, macd_signal = ?, bb_upper = ?, bb_middle = ?, bb_lower = ?
                WHERE company_id = ? AND date = ?
            """, (
                indicators.get('sma'), indicators.get('ema'), indicators.get('rsi'),
                indicators.get('macd'), indicators.get('macd_signal'),
                indicators.get('bb_upper'), indicators.get('bb_middle'), indicators.get('bb_lower'),
                company_id, date
            ))
        else:
            cursor.execute("""
                INSERT INTO technical_indicators (company_id, date, sma, ema, rsi, macd, macd_signal, bb_upper, bb_middle, bb_lower)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id, date,
                indicators.get('sma'), indicators.get('ema'), indicators.get('rsi'),
                indicators.get('macd'), indicators.get('macd_signal'),
                indicators.get('bb_upper'), indicators.get('bb_middle'), indicators.get('bb_lower')
            ))
        conn.commit()
    except Exception:
        # не фатально — логируем и продолжаем
        logger.exception("Ошибка при обновлении technical_indicators")

def mergeMetrDaily(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Возвращает DataFrame, объединяющий daily_data и нужные метрики (Открытые позиции, Количество лиц).
    SQL построен так, как в примере ранее — с LEFT JOIN по датам и компаниям.
    """
    cursor = conn.cursor()
    query = """
    SELECT 
        COALESCE(c.contract_code, 'UNKNOWN') AS contract_code,
        CASE
            WHEN COALESCE(c.contract_code, '') LIKE 'Si%' OR COALESCE(c.contract_code, '') LIKE 'BR%' THEN 'futures'
            WHEN COALESCE(c.contract_code, '') LIKE '%-F' THEN 'futures'
            ELSE 'equity'
        END AS asset_class,
        dd.date,
        dd.open,
        dd.low,
        dd.high,
        dd.close,
        dd.volume,
        
        COALESCE(op.value1, 0) AS long_fiz_1,
        COALESCE(op.value2, 0) AS short_fiz_2,
        COALESCE(op.value3, 0) AS long_jur_3,
        COALESCE(op.value4, 0) AS short_jur_4,
        COALESCE(op.value5, 0) AS total_positions,
        
        COALESCE(kl.value1, 0) AS count_fiz_1,
        COALESCE(kl.value2, 0) AS count_fiz_2,
        COALESCE(kl.value3, 0) AS count_jur_3,
        COALESCE(kl.value4, 0) AS count_jur_4,
        COALESCE(kl.value5, 0) AS total_count
        
    FROM daily_data AS dd
    LEFT JOIN companies AS c 
        ON dd.company_id = c.id
        
    LEFT JOIN (
        SELECT 
            company_id, 
            date,
            value1,
            value2,
            value3,
            value4,
            value5
        FROM metrics
        WHERE metric_type = 'Открытые позиции'
    ) AS op 
        ON dd.company_id = op.company_id 
        AND dd.date = op.date
        
    LEFT JOIN (
        SELECT 
            company_id, 
            date,
            value1,
            value2,
            value3,
            value4,
            value5
        FROM metrics
        WHERE metric_type = 'Количество лиц'
    ) AS kl 
        ON dd.company_id = kl.company_id 
        AND dd.date = kl.date
        
    ORDER BY dd.date;
    """
    try:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        data = cursor.fetchall()
        df = pd.DataFrame(data, columns=columns)
        if not df.empty:
            df['contract_code'] = df['contract_code'].fillna('UNKNOWN')
            if 'asset_class' in df.columns:
                df['asset_class'] = df['asset_class'].fillna('unknown')
        return df.drop_duplicates()
    except Exception:
        logger.exception("Ошибка при выполнении mergeMetrDaily")
        return pd.DataFrame()


def ensure_demo_account(conn: sqlite3.Connection, starting_balance: float = 1_000_000.0) -> None:
    """Ensure the demo account row exists."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO demo_accounts (id, balance, initial_balance)
        VALUES (1, ?, ?)
        """,
        (starting_balance, starting_balance),
    )
    conn.commit()


def get_or_create_company_id(conn: sqlite3.Connection, contract_code: str) -> Optional[int]:
    """Fetch company id for contract_code; insert placeholder if missing."""
    if not contract_code:
        return None
    normalized = contract_code.strip()
    if not normalized:
        return None
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM companies WHERE contract_code = ?",
        (normalized,),
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO companies (contract_code) VALUES (?)",
        (normalized,),
    )
    conn.commit()
    return cursor.lastrowid


# ==================== AUTO TRADING FUNCTIONS ====================

def ensure_auto_trading_settings(conn: sqlite3.Connection) -> None:
    """Ensure auto trading settings exist with default values."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO auto_trading_settings 
        (id, enabled, max_position_size, max_daily_orders, min_signal_strength, 
         risk_per_trade, stop_loss_atr_multiplier, take_profit_atr_multiplier, max_holding_days)
        VALUES (1, 0, 10000.0, 10, 0.6, 0.02, 2.0, 3.0, 5)
    """)
    conn.commit()


def get_auto_trading_settings(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Get current auto trading settings."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM auto_trading_settings WHERE id = 1")
    row = cursor.fetchone()
    if not row:
        ensure_auto_trading_settings(conn)
        cursor.execute("SELECT * FROM auto_trading_settings WHERE id = 1")
        row = cursor.fetchone()
    
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row)) if row else {}


def update_auto_trading_settings(conn: sqlite3.Connection, settings: Dict[str, Any]) -> None:
    """Update auto trading settings."""
    cursor = conn.cursor()
    settings['updated_at'] = pd.Timestamp.now().isoformat()
    
    # Build dynamic update query
    set_clauses = []
    values = []
    for key, value in settings.items():
        if key != 'id':
            set_clauses.append(f"{key} = ?")
            values.append(value)
    
    if set_clauses:
        query = f"UPDATE auto_trading_settings SET {', '.join(set_clauses)} WHERE id = 1"
        cursor.execute(query, values)
        conn.commit()


def save_trading_signal(conn: sqlite3.Connection, signal_data: Dict[str, Any]) -> int:
    """Save a trading signal to the database."""
    cursor = conn.cursor()
    
    # Ensure company exists
    company_id = get_or_create_company_id(conn, signal_data['contract_code'])
    if not company_id:
        raise ValueError(f"Could not create company for {signal_data['contract_code']}")
    
    cursor.execute("""
        INSERT OR REPLACE INTO trading_signals 
        (company_id, date, signal_type, signal_strength, signal_score, price, 
         volume, atr, stop_loss, take_profit, processed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company_id,
        signal_data['date'],
        signal_data['signal_type'],
        signal_data['signal_strength'],
        signal_data['signal_score'],
        signal_data['price'],
        signal_data.get('volume'),
        signal_data.get('atr'),
        signal_data.get('stop_loss'),
        signal_data.get('take_profit'),
        signal_data.get('processed', False)
    ))
    conn.commit()
    return cursor.lastrowid


def get_pending_signals(conn: sqlite3.Connection, limit: int = 100) -> pd.DataFrame:
    """Get unprocessed trading signals."""
    query = """
        SELECT ts.*, c.contract_code
        FROM trading_signals ts
        JOIN companies c ON ts.company_id = c.id
        WHERE ts.processed = FALSE
        ORDER BY ts.created_at ASC
        LIMIT ?
    """
    return pd.read_sql_query(query, conn, params=(limit,))


def save_auto_order(conn: sqlite3.Connection, order_data: Dict[str, Any]) -> int:
    """Save an automatic order to the database."""
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO auto_orders 
        (signal_id, company_id, contract_code, order_type, side, quantity, 
         price, stop_price, status, tinkoff_order_id, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_data['signal_id'],
        order_data['company_id'],
        order_data['contract_code'],
        order_data['order_type'],
        order_data['side'],
        order_data['quantity'],
        order_data.get('price'),
        order_data.get('stop_price'),
        order_data.get('status', 'pending'),
        order_data.get('tinkoff_order_id'),
        order_data.get('error_message')
    ))
    conn.commit()
    return cursor.lastrowid


def update_order_status(conn: sqlite3.Connection, order_id: int, status: str, 
                       tinkoff_order_id: str = None, error_message: str = None) -> None:
    """Update order status."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE auto_orders 
        SET status = ?, tinkoff_order_id = ?, error_message = ?, updated_at = ?
        WHERE id = ?
    """, (status, tinkoff_order_id, error_message, pd.Timestamp.now().isoformat(), order_id))
    conn.commit()


def mark_signal_processed(conn: sqlite3.Connection, signal_id: int) -> None:
    """Mark a signal as processed."""
    cursor = conn.cursor()
    cursor.execute("UPDATE trading_signals SET processed = TRUE WHERE id = ?", (signal_id,))
    conn.commit()


def get_daily_order_count(conn: sqlite3.Connection, date: str = None) -> int:
    """Get count of orders created today."""
    if not date:
        date = pd.Timestamp.now().strftime('%Y-%m-%d')
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM auto_orders 
        WHERE DATE(created_at) = ?
    """, (date,))
    return cursor.fetchone()[0]


def save_trade_history(conn: sqlite3.Connection, trade_data: Dict[str, Any]) -> int:
    """Save trade history record."""
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO auto_trade_history 
        (signal_id, order_id, company_id, contract_code, side, quantity, 
         entry_price, exit_price, stop_loss, take_profit, pnl, pnl_percent, 
         holding_days, exit_reason, entry_date, exit_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trade_data['signal_id'],
        trade_data['order_id'],
        trade_data['company_id'],
        trade_data['contract_code'],
        trade_data['side'],
        trade_data['quantity'],
        trade_data['entry_price'],
        trade_data.get('exit_price'),
        trade_data.get('stop_loss'),
        trade_data.get('take_profit'),
        trade_data.get('pnl', 0.0),
        trade_data.get('pnl_percent', 0.0),
        trade_data.get('holding_days', 0),
        trade_data.get('exit_reason'),
        trade_data['entry_date'],
        trade_data.get('exit_date')
    ))
    conn.commit()
    return cursor.lastrowid


def get_trade_history(conn: sqlite3.Connection, limit: int = 100) -> pd.DataFrame:
    """Get trade history."""
    query = """
        SELECT ath.*, c.contract_code
        FROM auto_trade_history ath
        JOIN companies c ON ath.company_id = c.id
        ORDER BY ath.created_at DESC
        LIMIT ?
    """
    return pd.read_sql_query(query, conn, params=(limit,))
