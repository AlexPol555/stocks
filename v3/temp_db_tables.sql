# Р”РѕР±Р°РІР»СЏРµРј С‚Р°Р±Р»РёС†С‹ РґР»СЏ СЂР°Р·РЅС‹С… С‚Р°Р№РјС„СЂРµР№РјРѕРІ РїРѕСЃР»Рµ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёС… ML С‚Р°Р±Р»РёС†

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
