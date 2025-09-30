"""
Shares Integration Page.
Страница для интеграции акций в систему.
"""

import streamlit as st
import sqlite3
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Shares Integration",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Shares Integration")
st.caption("Интеграция акций (shares) в существующую систему")

# Проверка API ключа
api_key = None
try:
    if hasattr(st, 'secrets') and hasattr(st.secrets, 'TINKOFF_API_KEY'):
        api_key = st.secrets.TINKOFF_API_KEY
        st.success("✅ API ключ Tinkoff загружен из secrets.toml")
    else:
        st.warning("⚠️ API ключ Tinkoff не найден в secrets.toml")
except Exception as e:
    st.error(f"❌ Ошибка загрузки API ключа: {e}")

# Проверка базы данных
db_path = "stock_data.db"
if not os.path.exists(db_path):
    st.error("❌ База данных не найдена")
    st.stop()

# Функция для проверки структуры таблицы
def check_table_structure():
    """Проверить структуру таблицы companies."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(companies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        return columns
    except Exception as e:
        st.error(f"Ошибка проверки структуры таблицы: {e}")
        return []
    finally:
        conn.close()

# Функция для добавления поддержки акций
def add_shares_support():
    """Добавить поддержку акций в таблицу companies."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Добавляем колонки для поддержки акций
        columns_to_add = [
            ("asset_type", "TEXT DEFAULT 'futures'"),
            ("ticker", "TEXT"),
            ("lot_size", "INTEGER DEFAULT 1"),
            ("currency", "TEXT DEFAULT 'RUB'"),
            ("min_price_increment", "REAL DEFAULT 0.01")
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE companies ADD COLUMN {column_name} {column_type}")
                st.success(f"✅ Добавлена колонка {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    st.info(f"ℹ️ Колонка {column_name} уже существует")
                else:
                    st.error(f"❌ Ошибка добавления колонки {column_name}: {e}")
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"❌ Ошибка добавления поддержки акций: {e}")
        return False
    finally:
        conn.close()

# Функция для загрузки акций из API
def load_shares_from_api(api_key, russian_only=True):
    """Загрузить акции из Tinkoff API с фильтрацией российских акций."""
    try:
        from tinkoff.invest import Client as _Client
        from tinkoff.invest.schemas import InstrumentStatus, ShareType
    except ImportError:
        st.error("❌ Tinkoff SDK не установлен. Установите: pip install tinkoff-invest")
        return []
    
    try:
        with _Client(api_key) as client:
            # Используем правильные параметры API для фильтрации
            if russian_only:
                # Загружаем только базовые инструменты (российские)
                instruments = client.instruments.shares(
                    instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE
                ).instruments
                st.info("🇷🇺 Загружаем только российские акции (INSTRUMENT_STATUS_BASE)")
            else:
                # Загружаем все инструменты
                instruments = client.instruments.shares(
                    instrument_status=InstrumentStatus.INSTRUMENT_STATUS_ALL
                ).instruments
                st.info("🌍 Загружаем все акции (INSTRUMENT_STATUS_ALL)")
            
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
                    'asset_type': 'shares'
                })
            
            if russian_only:
                st.info(f"📊 Загружено {len(shares_data)} российских акций (из {total_count} всего)")
            else:
                st.info(f"📊 Загружено {len(shares_data)} акций (из {total_count} всего)")
            
            return shares_data
            
    except Exception as e:
        st.error(f"❌ Ошибка загрузки акций из API: {e}")
        return []

# Функция для сохранения акций в БД
def save_shares_to_db(shares_data):
    """Сохранить акции в базу данных."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        saved_count = 0
        for share in shares_data:
            cursor.execute("""
                INSERT OR REPLACE INTO companies 
                (contract_code, ticker, name, isin, figi, asset_type, lot_size, currency, min_price_increment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                share['ticker'],  # Используем ticker как contract_code
                share['ticker'],
                share['name'],
                share['isin'],
                share['figi'],
                share['asset_type'],
                share['lot_size'],
                share['currency'],
                share['min_price_increment']
            ))
            saved_count += 1
        
        conn.commit()
        return saved_count
        
    except Exception as e:
        st.error(f"❌ Ошибка сохранения акций: {e}")
        return 0
    finally:
        conn.close()

# Функция для получения статистики
def get_asset_statistics():
    """Получить статистику по типам активов."""
    conn = sqlite3.connect(db_path)
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
        st.error(f"Ошибка получения статистики: {e}")
        return {}
    finally:
        conn.close()

# Основной интерфейс
st.header("🔍 Проверка текущего состояния")

# Проверяем структуру таблицы
columns = check_table_structure()
if columns:
    st.write("**Структура таблицы companies:**")
    for col in columns:
        st.write(f"- {col}")
    
    # Проверяем, есть ли поддержка акций
    if 'asset_type' in columns:
        st.success("✅ Поддержка акций уже добавлена")
    else:
        st.warning("⚠️ Поддержка акций не добавлена")
        
        if st.button("🔧 Добавить поддержку акций"):
            if add_shares_support():
                st.success("✅ Поддержка акций добавлена!")
                st.rerun()
            else:
                st.error("❌ Ошибка добавления поддержки акций")

# Статистика активов
st.header("📊 Статистика активов")
stats = get_asset_statistics()
if stats:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Акции", stats.get('shares', 0))
    
    with col2:
        st.metric("📈 Фьючерсы", stats.get('futures', 0))
    
    with col3:
        st.metric("❓ Неизвестно", stats.get('unknown', 0))
    
    with col4:
        total = sum(stats.values())
        st.metric("📊 Всего", total)

# Интеграция акций
if api_key and 'asset_type' in columns:
    st.header("🚀 Интеграция акций")
    
    # Настройки фильтрации
    col1, col2 = st.columns([2, 1])
    
    with col1:
        russian_only = st.checkbox(
            "🇷🇺 Только российские акции", 
            value=True, 
            help="Фильтровать только российские акции: INSTRUMENT_STATUS_BASE + RUB валюта + RU ISIN"
        )
    
    with col2:
        if st.button("🔄 Обновить статистику", key="refresh_shares_stats"):
            st.rerun()
    
    if st.button("📡 Загрузить акции из Tinkoff API"):
        with st.spinner("Загрузка акций из Tinkoff API..."):
            shares_data = load_shares_from_api(api_key, russian_only)
            
            if shares_data:
                if russian_only:
                    st.success(f"✅ Загружено {len(shares_data)} российских акций из API")
                else:
                    st.success(f"✅ Загружено {len(shares_data)} акций из API")
                
                # Показываем примеры
                st.write("**Примеры загруженных акций:**")
                for i, share in enumerate(shares_data[:5]):
                    currency = share.get('currency', 'Unknown')
                    isin = share.get('isin', 'Unknown')
                    st.write(f"{i+1}. {share['ticker']}: {share['name']} ({currency}) [{isin}]")
                
                if st.button("💾 Сохранить акции в базу данных"):
                    with st.spinner("Сохранение акций в базу данных..."):
                        saved_count = save_shares_to_db(shares_data)
                        
                        if saved_count > 0:
                            st.success(f"✅ Сохранено {saved_count} акций в базу данных")
                            st.rerun()
                        else:
                            st.error("❌ Ошибка сохранения акций")
            else:
                st.error("❌ Не удалось загрузить акции из API")

# Информация о интеграции
st.header("💡 Информация о интеграции")

st.info("""
**Что делает интеграция акций:**

1. **Расширяет таблицу companies** - добавляет колонки для поддержки акций
2. **Загружает акции из Tinkoff API** - получает список акций с фильтрацией
3. **Фильтрация российских акций** - использует INSTRUMENT_STATUS_BASE + RUB валюта + RU ISIN
4. **Сохраняет в базу данных** - интегрирует акции с существующими фьючерсами
5. **Совместимость** - не нарушает работу существующей системы

**Фильтрация российских акций:**
- 🇷🇺 **INSTRUMENT_STATUS_BASE** - только базовые инструменты (российские)
- 💱 **RUB валюта** - акции в российских рублях
- 📋 **RU ISIN** - ISIN коды начинающиеся с "RU"
- 🏢 **Тип акций** - только обыкновенные и привилегированные (не ADR/GDR)

**После интеграции:**
- Акции будут доступны для анализа и торговли
- ML модели смогут обучаться на большем объеме данных
- Система будет поддерживать как акции, так и фьючерсы
""")

# Кнопка для обновления статистики
if st.button("🔄 Обновить статистику"):
    st.rerun()
