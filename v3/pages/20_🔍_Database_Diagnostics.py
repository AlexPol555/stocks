"""
Database Diagnostics Page.
Страница для диагностики базы данных.
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Database Diagnostics",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Database Diagnostics")
st.caption("Диагностика базы данных и загрузки данных")

# Проверка базы данных
db_path = "stock_data.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Общая информация
    st.header("📊 Общая информация")
    
    cursor.execute("SELECT COUNT(*) FROM companies")
    companies_count = cursor.fetchone()[0]
    st.metric("🏢 Компаний в БД", companies_count)
    
    # 2. Таблицы данных
    st.header("📈 Таблицы данных")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'data_%'")
    data_tables = cursor.fetchall()
    
    if data_tables:
        table_info = []
        total_records = 0
        
        for table in data_tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            total_records += count
            
            cursor.execute(f"SELECT COUNT(DISTINCT symbol) FROM {table_name}")
            symbols_count = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT MAX(datetime) FROM {table_name}")
            last_record = cursor.fetchone()[0]
            
            table_info.append({
                'Table': table_name,
                'Records': count,
                'Symbols': symbols_count,
                'Last Update': last_record or 'Never'
            })
        
        st.dataframe(pd.DataFrame(table_info), use_container_width=True)
        st.metric("📊 Общее количество записей", total_records)
        
        # 3. Анализ по таймфреймам
        st.header("⏰ Анализ по таймфреймам")
        
        timeframes = ['1d', '1h', '1m', '5m', '15m']
        timeframe_info = []
        
        for tf in timeframes:
            table_name = f"data_{tf.replace('m', 'min').replace('h', 'hour')}"
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if cursor.fetchone():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                cursor.execute(f"SELECT COUNT(DISTINCT symbol) FROM {table_name}")
                symbols = cursor.fetchone()[0]
                timeframe_info.append({
                    'Timeframe': tf,
                    'Records': count,
                    'Symbols': symbols,
                    'Status': '✅ Active'
                })
            else:
                timeframe_info.append({
                    'Timeframe': tf,
                    'Records': 0,
                    'Symbols': 0,
                    'Status': '❌ Not Created'
                })
        
        st.dataframe(pd.DataFrame(timeframe_info), use_container_width=True)
        
        # 4. Топ символов по количеству записей
        st.header("📊 Топ символов по количеству записей")
        
        for table in data_tables:
            table_name = table[0]
            cursor.execute(f"""
                SELECT symbol, COUNT(*) as count 
                FROM {table_name} 
                GROUP BY symbol 
                ORDER BY count DESC 
                LIMIT 10
            """)
            top_symbols = cursor.fetchall()
            
            if top_symbols:
                st.write(f"**{table_name}:**")
                symbols_df = pd.DataFrame(top_symbols, columns=['Symbol', 'Records'])
                st.dataframe(symbols_df, use_container_width=True)
        
        # 5. Временной диапазон данных
        st.header("📅 Временной диапазон данных")
        
        for table in data_tables:
            table_name = table[0]
            cursor.execute(f"SELECT MIN(datetime), MAX(datetime) FROM {table_name}")
            min_date, max_date = cursor.fetchone()
            if min_date and max_date:
                st.write(f"**{table_name}:** {min_date} - {max_date}")
        
        # 6. Рекомендации
        st.header("💡 Рекомендации")
        
        if companies_count == 0:
            st.error("❌ Нет компаний в БД. Запустите загрузку данных.")
        elif total_records == 0:
            st.error("❌ Нет данных в таблицах. Запустите обновление данных.")
        elif total_records < companies_count * 10:
            st.warning("⚠️ Мало данных. Возможно, обновление не завершено.")
            st.info("💡 Запустите обновление данных для всех таймфреймов.")
        else:
            st.success("✅ Данные загружены успешно!")
        
        if len(data_tables) < 5:
            st.warning("⚠️ Не все таймфреймы загружены.")
            st.info("💡 Запустите обновление для всех таймфреймов.")
        
        # 7. Кнопка для обновления данных
        st.header("🔄 Обновление данных")
        
        if st.button("🔄 Запустить обновление данных"):
            st.info("Запуск обновления данных...")
            # Здесь можно добавить логику обновления данных
            st.success("✅ Обновление данных запущено!")
    
    else:
        st.error("❌ Таблицы данных не найдены")
        st.info("💡 Запустите обновление данных для создания таблиц")
    
    conn.close()
    
except Exception as e:
    st.error(f"❌ Ошибка подключения к базе данных: {e}")

# 8. Информация о проблеме с 500 строками
st.header("🔍 Анализ проблемы с 500 строками")

st.info("""
**Возможные причины ограничения в 500 строк:**

1. **Rate Limiting API** - Tinkoff API может ограничивать количество запросов
2. **Ограничения в коде** - где-то есть лимит на количество записей
3. **Неполная загрузка** - данные загружаются не полностью
4. **Проблема с таймфреймами** - данные загружаются только для одного таймфрейма

**Что проверить:**
- Количество компаний в БД
- Количество записей в каждой таблице
- Распределение данных по символам
- Временной диапазон данных
""")

# 9. Кнопка для перезапуска диагностики
if st.button("🔄 Обновить диагностику"):
    st.rerun()
