import sqlite3
import pandas as pd
import decimal

sqlite3.register_adapter(decimal.Decimal, float)

DB_NAME = "stock_data.db"

def get_connection(db_path: str = DB_NAME):
    """Устанавливает соединение с базой данных SQLite."""
    conn = sqlite3.connect(db_path)
    return conn

def create_tables(conn):
    cursor = conn.cursor()
    # Таблица компаний
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_code TEXT UNIQUE
    );
    """)
    # Таблица daily_data
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
    # Таблица технических индикаторов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS technical_indicators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        sma REAL,
        ema REAL,
        rsi REAL,
        macd REAL,
        macd_signal REAL,
        bb_upper REAL,
        bb_middle REAL,
        bb_lower REAL,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    """)
    # Таблица метрик
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
    conn.commit()

def load_data_from_db(conn) -> pd.DataFrame:
    query = """
    SELECT c.contract_code, m.date, m.metric_type, m.value1, m.value2, m.value3, m.value4, m.value5
    FROM metrics m
    JOIN companies c ON m.company_id = c.id
    """
    df = pd.read_sql(query, conn)
    return df

def load_daily_data_from_db(conn, start_date=None, end_date=None) -> pd.DataFrame:
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
    df = pd.read_sql(query, conn)
    return df

def update_technical_indicators(conn, daily_data_id, indicators):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM technical_indicators WHERE daily_data_id = ?", (daily_data_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE technical_indicators
            SET sma = ?, ema = ?, rsi = ?, macd = ?, macd_signal = ?, bb_upper = ?, bb_middle = ?, bb_lower = ?
            WHERE daily_data_id = ?
        """, (indicators['sma'], indicators['ema'], indicators['rsi'], indicators['macd'], indicators['macd_signal'],
              indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'], daily_data_id))
    else:
        cursor.execute("""
            INSERT INTO technical_indicators (daily_data_id, sma, ema, rsi, macd, macd_signal, bb_upper, bb_middle, bb_lower)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (daily_data_id, indicators['sma'], indicators['ema'], indicators['rsi'], indicators['macd'], indicators['macd_signal'],
              indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower']))
    conn.commit()


def mergeMetrDaily(conn) -> pd.DataFrame:
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
        
        -- Данные для "Открытые позиции"
        op.value1 AS long_fiz_1,
        op.value2 AS short_fiz_2,
        op.value3 AS long_jur_3,
        op.value4 AS short_jur_4,
        op.value5 AS total_positions,
        
        -- Данные для "Количество лиц"
        kl.value1 AS count_fiz_1,
        kl.value2 AS count_fiz_2,
        kl.value3 AS count_jur_3,
        kl.value4 AS count_jur_4,
        kl.value5 AS total_count
        
    FROM daily_data AS dd
    JOIN companies AS c 
        ON dd.company_id = c.id
        
    -- Подзапрос для "Открытые позиции"
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
        
    -- Подзапрос для "Количество лиц"
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

    # Выполнение запроса
    cursor.execute(query)

    # Извлечение результатов
    columns = [col[0] for col in cursor.description]
    data = cursor.fetchall()
    # Преобразование в DataFrame
    df = pd.DataFrame(data, columns=columns)

    return df
