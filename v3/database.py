# database.py (вставить/заменить этот блок в начале файла)
import os
import sqlite3
import decimal
import logging

sqlite3.register_adapter(decimal.Decimal, float)
logger = logging.getLogger(__name__)

# Храним файл БД в рабочей директории приложения (Streamlit Cloud)
DB_FILENAME = os.environ.get("STOCK_DB_FILENAME", "stock_data.db")
DB_PATH = os.path.join(os.getcwd(), DB_FILENAME)

def get_connection(db_path: str = None):
    """
    Возвращает sqlite3 connection. По умолчанию — рабочая директория приложения.
    check_same_thread=False полезно для использования в Streamlit.
    """
    path = db_path or DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
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
        import logging
        logging.getLogger(__name__).warning("Миграция contract_code из company_parameters не выполнена.")

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
        import logging
        logging.getLogger(__name__).exception("Ошибка при обновлении technical_indicators")

def mergeMetrDaily(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Возвращает DataFrame, объединяющий daily_data и нужные метрики (Открытые позиции, Количество лиц).
    SQL построен так, как в примере ранее — с LEFT JOIN по датам и компаниям.
    """
    cursor = conn.cursor()
    query = """
    SELECT 
        c.contract_code, 
        dd.date,
        dd.open,
        dd.low,
        dd.high,
        dd.close,
        dd.volume,
        
        op.value1 AS long_fiz_1,
        op.value2 AS short_fiz_2,
        op.value3 AS long_jur_3,
        op.value4 AS short_jur_4,
        op.value5 AS total_positions,
        
        kl.value1 AS count_fiz_1,
        kl.value2 AS count_fiz_2,
        kl.value3 AS count_jur_3,
        kl.value4 AS count_jur_4,
        kl.value5 AS total_count
        
    FROM daily_data AS dd
    JOIN companies AS c 
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
        return df.drop_duplicates()
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Ошибка при выполнении mergeMetrDaily")
        return pd.DataFrame()
