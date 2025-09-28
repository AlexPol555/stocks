"""
Enhanced Multi-Timeframe Data Management Page.
Расширенная страница управления многоуровневыми данными с поддержкой секундных и тиковых данных.
"""

import streamlit as st
import pandas as pd
import asyncio
from datetime import datetime, timedelta
import logging
import json

# Импорты для работы с многоуровневыми данными
try:
    from core.multi_timeframe_analyzer import (
        MultiTimeframeStockAnalyzer, 
        WebSocketDataProvider
    )
    from core.data_updater_enhanced import EnhancedDataUpdater  # Используем новый расширенный класс
    from core.realtime_manager import RealTimeDataManager
    MULTI_TIMEFRAME_AVAILABLE = True
except ImportError as e:
    MULTI_TIMEFRAME_AVAILABLE = False
    st.error(f"❌ Многоуровневый анализатор недоступен: {e}")

# Импорты для работы с ML
try:
    from core.ml.model_manager import MLModelManager
    from core.ml.storage import ml_storage
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Multi-Timeframe Data",
    page_icon="⏰",
    layout="wide"
)

st.title("⏰ Multi-Timeframe Data Management")
st.caption("Управление данными разных таймфреймов с поддержкой секундных и тиковых данных")

# Проверка доступности компонентов
if not MULTI_TIMEFRAME_AVAILABLE:
    st.error("❌ Многоуровневый анализатор недоступен. Проверьте установку зависимостей.")
    st.stop()

# Инициализация компонентов
if 'multi_analyzer' not in st.session_state:
    api_key = None
    try:
        if hasattr(st, 'secrets') and hasattr(st.secrets, 'TINKOFF_API_KEY'):
            api_key = st.secrets.TINKOFF_API_KEY
            st.session_state.tinkoff_api_key = api_key
    except Exception:
        pass
    
    if not api_key:
        api_key = st.session_state.get('tinkoff_api_key')
    
    if api_key:
        st.session_state.multi_analyzer = MultiTimeframeStockAnalyzer(api_key=api_key)
        st.session_state.data_updater = EnhancedDataUpdater(api_key)  # Используем новый класс
        st.session_state.real_time_manager = RealTimeDataManager(api_key)
        st.success("✅ API ключ Tinkoff загружен из secrets.toml")
    else:
        st.warning("⚠️ API ключ Tinkoff не найден. Проверьте .streamlit/secrets.toml")

# Создаем вкладки
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Data Overview", 
    "🔄 Data Updater", 
    "⚡ Real-Time", 
    "🧠 ML Integration",
    "⚙️ Settings"
])

with tab1:
    st.header("📊 Обзор данных по таймфреймам")
    
    # Получаем статус всех таймфреймов
    if 'data_updater' in st.session_state:
        updater = st.session_state.data_updater
        all_status = updater.get_all_timeframe_status()
        
        # Отображаем статус в виде таблицы
        status_data = []
        for timeframe, status in all_status.items():
            status_data.append({
                'Timeframe': timeframe,
                'Status': status['status'],
                'Records': status['record_count'],
                'Symbols': status['symbol_count'],
                'Last Update': status['last_record'] or 'Never',
                'Table Exists': '✅' if status['table_exists'] else '❌'
            })
        
        st.dataframe(pd.DataFrame(status_data), use_container_width=True)
        
        # Детальная информация по каждому таймфрейму
        st.subheader("🔍 Детальная информация")
        
        selected_timeframe = st.selectbox(
            "Выберите таймфрейм для детального просмотра:",
            ['1d', '1h', '1m', '5m', '15m', '1s', 'tick']
        )
        
        if selected_timeframe:
            status = all_status[selected_timeframe]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📊 Записей", status['record_count'])
            
            with col2:
                st.metric("🏷️ Символов", status['symbol_count'])
            
            with col3:
                st.metric("📅 Последнее обновление", 
                         status['last_record'][:19] if status['last_record'] else 'Never')
            
            # Показать примеры данных
            if status['table_exists'] and status['record_count'] > 0:
                st.subheader(f"📋 Пример данных ({selected_timeframe})")
                
                try:
                    # Получаем примеры данных из таблицы
                    table_name = f"data_{selected_timeframe.replace('m', 'min').replace('h', 'hour')}" if selected_timeframe != 'tick' else 'data_tick'
                    
                    from core.database import get_connection
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute(f"""
                        SELECT * FROM {table_name} 
                        ORDER BY datetime DESC 
                        LIMIT 10
                    """)
                    
                    columns = [description[0] for description in cursor.description]
                    rows = cursor.fetchall()
                    
                    if rows:
                        sample_df = pd.DataFrame(rows, columns=columns)
                        st.dataframe(sample_df, use_container_width=True)
                    else:
                        st.info("Нет данных для отображения")
                    
                    conn.close()
                    
                except Exception as e:
                    st.error(f"Ошибка получения данных: {e}")
    else:
        st.warning("Data updater не инициализирован")

with tab2:
    st.header("🔄 Управление обновлением данных")
    
    if 'data_updater' not in st.session_state:
        st.error("Data updater не инициализирован")
        st.stop()
    
    updater = st.session_state.data_updater
    
    # Статус планировщика
    col1, col2 = st.columns([2, 1])
    
    with col1:
        is_running = updater.is_running
        st.metric("🔄 Статус планировщика", "✅ Работает" if is_running else "❌ Остановлен")
    
    with col2:
        if st.button("▶️ Запустить" if not is_running else "⏹️ Остановить"):
            if not is_running:
                updater.start_scheduler()
                st.success("✅ Планировщик запущен")
                st.rerun()
            else:
                updater.stop_scheduler()
                st.success("✅ Планировщик остановлен")
                st.rerun()
    
    # Управление таймфреймами
    st.subheader("⏰ Управление таймфреймами")
    
    timeframes = ['1d', '1h', '1m', '5m', '15m', '1s', 'tick']
    
    # Создаем колонки для каждого таймфрейма
    cols = st.columns(len(timeframes))
    
    for i, timeframe in enumerate(timeframes):
        with cols[i]:
            st.write(f"**{timeframe}**")
            
            # Кнопка для ручного обновления
            if st.button(f"🔄 Обновить {timeframe}", key=f"update_{timeframe}"):
                with st.spinner(f"Обновление {timeframe} данных..."):
                    if timeframe == '1d':
                        updater.update_daily_data()
                    elif timeframe == '1h':
                        updater.update_hourly_data()
                    elif timeframe == '1m':
                        updater.update_minute_data()
                    elif timeframe == '5m':
                        updater.update_5min_data()
                    elif timeframe == '15m':
                        updater.update_15min_data()
                    elif timeframe == '1s':
                        updater.update_second_data()
                    elif timeframe == 'tick':
                        updater.update_tick_data()
                
                st.success(f"✅ {timeframe} данные обновлены")
    
    # Предупреждение о частых обновлениях
    st.warning("""
    ⚠️ **Предупреждение:**
    - Секундные данные (1s) обновляются каждую секунду - очень высокая нагрузка!
    - Тиковые данные (tick) обновляются в реальном времени - экстремальная нагрузка!
    - Рекомендуется включать только при необходимости для тестирования.
    """)
    
    # Статистика обновлений
    st.subheader("📈 Статистика обновлений")
    
    stats = updater.get_update_stats()
    
    if stats['update_count']:
        st.write("**Количество обновлений:**")
        for key, count in list(stats['update_count'].items())[:10]:  # Показываем первые 10
            st.write(f"- {key}: {count}")
    
    if stats['errors']:
        st.write("**Ошибки:**")
        for key, error in list(stats['errors'].items())[:5]:  # Показываем первые 5 ошибок
            st.error(f"- {key}: {error}")

with tab3:
    st.header("⚡ Данные в реальном времени")
    
    if 'real_time_manager' not in st.session_state or st.session_state.real_time_manager is None:
        st.info("🚧 Real-Time менеджер пока не реализован")
        st.warning("Эта функция будет доступна в будущих версиях")
        
        # Показываем заглушку
        st.subheader("🔮 Планы развития")
        st.write("""
        **Real-Time функции в разработке:**
        - 🌐 WebSocket подключение для тиковых данных
        - ⚡ Секундные данные (1s)
        - 📡 Потоковые обновления
        - 🎯 Множественные символы
        """)
        
        st.info("💡 Пока используйте вкладку 'Data Updater' для получения данных")
    else:
        manager = st.session_state.real_time_manager
        
        # Выбор символов для мониторинга
        col1, col2 = st.columns([2, 1])
        
        with col1:
            available_symbols = st.session_state.multi_analyzer.get_available_symbols()
            selected_symbols_rt = st.multiselect(
                "Выберите символы для мониторинга в реальном времени:",
                available_symbols,
                default=available_symbols[:5] if available_symbols else [],
                key="real_time_symbols"
            )
        
        with col2:
            timeframe_rt = st.selectbox(
                "Выберите таймфрейм:",
                ['1s', 'tick'], # Только секундные и тиковые данные для реального времени
                key="real_time_timeframe"
            )
        
        if st.button("▶️ Начать мониторинг", key="start_real_time"):
            if selected_symbols_rt:
                st.info(f"Запуск мониторинга в реальном времени для {len(selected_symbols_rt)} символов...")
                for symbol in selected_symbols_rt:
                    figi = st.session_state.multi_analyzer.get_figi_for_symbol(symbol)
                    if figi:
                        asyncio.run(manager.start_real_time_data(figi, timeframe_rt))
                        st.success(f"✅ Мониторинг для {symbol} запущен.")
                    else:
                        st.error(f"❌ FIGI не найден для символа {symbol}.")
            else:
                st.warning("Выберите хотя бы один символ для мониторинга.")
        
        if st.button("⏹️ Остановить мониторинг", key="stop_real_time"):
            st.info("Остановка мониторинга в реальном времени...")
            asyncio.run(manager.stop_all_real_time_data())
            st.success("✅ Мониторинг остановлен.")
        
        st.subheader("📊 Последние данные в реальном времени")
        if selected_symbols_rt:
            latest_data_display = []
            for symbol in selected_symbols_rt:
                data = manager.get_latest_data(symbol)
                if data:
                    latest_data_display.append({
                        "Symbol": symbol,
                        "Last Update": data.get('timestamp'),
                        "Data": json.dumps(data.get('last_1s_candle') or data.get('last_tick'))
                    })
            if latest_data_display:
                st.dataframe(pd.DataFrame(latest_data_display), use_container_width=True)
            else:
                st.info("Нет данных в реальном времени для отображения.")
        else:
            st.info("Выберите символы для просмотра данных в реальном времени.")

with tab4:
    st.header("🧠 ML интеграция")
    
    if not ML_AVAILABLE:
        st.warning("ML компоненты недоступны")
        st.stop()
    
    st.write("""
    **Интеграция с ML системой:**
    
    Многоуровневые данные могут использоваться для:
    - 📊 Анализа паттернов на разных таймфреймах
    - 🧠 Обучения ML моделей на исторических данных
    - ⚡ Предсказания в реальном времени
    - 🎯 Оптимизации торговых стратегий
    """)
    
    # Показать доступные данные для ML
    if 'data_updater' in st.session_state:
        updater = st.session_state.data_updater
        ml_data_status = updater.get_all_timeframe_status()
        
        st.subheader("📊 Данные доступные для ML")
        
        ml_ready_data = []
        for timeframe, status in ml_data_status.items():
            if status['record_count'] > 0:
                ml_ready_data.append({
                    'Timeframe': timeframe,
                    'Records': status['record_count'],
                    'Symbols': status['symbol_count'],
                    'ML Ready': '✅' if status['record_count'] > 100 else '⚠️'
                })
        
        if ml_ready_data:
            st.dataframe(pd.DataFrame(ml_ready_data), use_container_width=True)
            
            st.info("💡 Данные готовы для использования в ML моделях")
        else:
            st.warning("⚠️ Недостаточно данных для ML анализа")

with tab5:
    st.header("⚙️ Настройки")
    
    st.subheader("🔑 API Настройки")
    
    # Показать текущий API ключ (скрытый)
    api_key = st.session_state.get('tinkoff_api_key', 'Не установлен')
    if api_key != 'Не установлен':
        masked_key = api_key[:8] + '*' * (len(api_key) - 12) + api_key[-4:] if len(api_key) > 12 else '***'
        st.text_input("Текущий API ключ:", value=masked_key, disabled=True)
    else:
        st.text_input("API ключ:", value="Не установлен", disabled=True)
    
    st.info("💡 API ключ автоматически загружается из .streamlit/secrets.toml")
    
    st.subheader("📊 Настройки обновления")
    
    # Показать расписание обновления
    if 'data_updater' in st.session_state:
        updater = st.session_state.data_updater
        
        st.write("**Текущее расписание:**")
        schedules = updater.update_schedules
        
        for timeframe, schedule_info in schedules.items():
            st.write(f"- **{timeframe}**: {schedule_info['interval']} в {schedule_info['time']}")
        
        st.warning("""
        ⚠️ **Важно:**
        - Секундные данные (1s) создают очень высокую нагрузку
        - Тиковые данные (tick) создают экстремальную нагрузку
        - Используйте только при необходимости для тестирования
        """)
    
    st.subheader("🗄️ Управление базой данных")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Проверить таблицы"):
            st.info("Проверка таблиц базы данных...")
            # Здесь можно добавить проверку таблиц
            
    with col2:
        if st.button("🧹 Очистить кэш"):
            st.info("Очистка кэша...")
            # Здесь можно добавить очистку кэша
    
    st.subheader("📈 Мониторинг производительности")
    
    # Показать статистику производительности
    if 'data_updater' in st.session_state:
        stats = st.session_state.data_updater.get_update_stats()
        
        st.write("**Статистика обновлений:**")
        st.json({
            'is_running': stats['is_running'],
            'total_updates': sum(stats['update_count'].values()) if stats['update_count'] else 0,
            'total_errors': len(stats['errors']) if stats['errors'] else 0
        })
