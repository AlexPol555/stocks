def create_tables(conn):
    """
    Создаёт необходимые таблицы (безопасно — IF NOT EXISTS).
    Также выполняет простую миграцию contract_code из company_parameters -> companies,
    если в company_parameters уже есть записи.
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

    # 2) Таблица companies — требуется для JOIN-ов в запросах (mergeMetrDaily, load_data_from_db и т.д.)
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

    # 6) Безопасная миграция: если есть записи в company_parameters с contract_code, 
    #    добавляем их в companies (INSERT OR IGNORE, чтобы не дублировать)
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO companies (contract_code)
        SELECT DISTINCT contract_code FROM company_parameters WHERE contract_code IS NOT NULL AND contract_code != '';
        """)
    except Exception as e:
        # Если company_parameters не содержит контрактов или что-то идёт не так — просто логируем
        import logging
        logging.getLogger(__name__).warning("Миграция contract_code из company_parameters не выполнена: %s", e)

    conn.commit()
