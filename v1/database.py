# database.py
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
        contract_code_stock TEXT UNIQUE,
        contract_code_futures TEXT,
        instrument_type TEXT CHECK(instrument_type IN ('stock', 'futures'))
    );
    """)
    # Таблица daily_data – уникальная запись для (company, date)
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
    # Таблица технических индикаторов (если потребуется)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS technical_indicators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        daily_data_id INTEGER,
        sma REAL,
        ema REAL,
        rsi REAL,
        macd REAL,
        macd_signal REAL,
        bb_upper REAL,
        bb_middle REAL,
        bb_lower REAL,
        FOREIGN KEY(daily_data_id) REFERENCES daily_data(id)
    );
    """)
    # Таблица метрик – каждая строка CSV становится отдельной записью
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        daily_data_id INTEGER,
        metric_type TEXT,
        value1 REAL,
        value2 REAL,
        value3 REAL,
        value4 REAL,
        value5 REAL,
        FOREIGN KEY(daily_data_id) REFERENCES daily_data(id)
    );
    """)
    conn.commit()

def load_metrics_from_db(conn) -> pd.DataFrame:
    """
    Извлекает данные из таблицы metrics с дополнительной проверкой связей.
    """
    query = """
    SELECT c.contract_code, dd.date, m.metric_type, m.value1, m.value2, m.value3, m.value4, m.value5
    FROM metrics m
    JOIN daily_data dd ON m.daily_data_id = dd.id
    JOIN companies c ON dd.company_id = c.id
    WHERE m.daily_data_id IS NOT NULL AND dd.company_id IS NOT NULL
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        print("Нет данных в metrics после проверки связей!")
    else:
        print(df.head())
    return df

def load_daily_data_from_db(conn, start_date=None, end_date=None) -> pd.DataFrame:
    """
    Извлекает данные из базы данных за указанный период.
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
    
    df = pd.read_sql(query, conn)
    return df

def update_technical_indicators(conn, daily_data_id, indicators):
    """
    Обновляет или вставляет технические индикаторы в БД.
    """
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

def find_orphaned_metrics(conn):
    """
    Находит записи в metrics без соответствия в daily_data.
    """
    query = """
    SELECT m.* 
    FROM metrics m
    LEFT JOIN daily_data dd ON m.daily_data_id = dd.id
    WHERE dd.id IS NULL;
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        print("Все записи в metrics корректно связаны с daily_data.")
    else:
        print("Найдены несвязанные записи в metrics:")
        print(df)
    return df

