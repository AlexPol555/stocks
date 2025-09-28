"""
Real Multi-Timeframe Data Management Page with WebSocket support.
Реальная страница управления многоуровневыми данными с поддержкой WebSocket.
"""

import streamlit as st
import pandas as pd
import asyncio
from datetime import datetime, timedelta
import logging
import json

# Импорты для работы с многоуровневыми данными
try:
    from core.multi_timeframe_analyzer_real import (
        RealMultiTimeframeStockAnalyzer, 
        create_real_multi_timeframe_analyzer
    )
    from core.tinkoff_websocket_provider import TinkoffWebSocketProvider
    from core.realtime_manager_enhanced import EnhancedRealTimeDataManager
    from core.data_updater_enhanced import EnhancedDataUpdater
    REAL_MULTI_TIMEFRAME_AVAILABLE = True
except ImportError as e:
    REAL_MULTI_TIMEFRAME_AVAILABLE = False
    st.error(f"❌ Реальный многоуровневый анализатор недоступен: {e}")

# Импорты для работы с ML
try:
    from core.ml.model_manager import MLModelManager
    from core.ml.storage import ml_storage
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Real Multi-Timeframe Data",
    page_icon="⏰",
    layout="wide"
)

st.title("⏰ Real Multi-Timeframe Data Management")
st.caption("Управление данными разных таймфреймов с реальной поддержкой WebSocket")

# Проверка доступности компонентов
if not REAL_MULTI_TIMEFRAME_AVAILABLE:
    st.error("❌ Реальный многоуровневый анализатор недоступен. Проверьте установку зависимостей.")
    st.stop()

# Инициализация компонентов
if 'real_multi_analyzer' not in st.session_state:
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
        # Используем реальный анализатор
        st.session_state.real_multi_analyzer = create_real_multi_timeframe_analyzer(api_key, sandbox=False)
        st.session_state.real_data_updater = EnhancedDataUpdater(api_key)
        st.session_state.real_time_manager = EnhancedRealTimeDataManager(api_key, sandbox=False)
        st.success("✅ API ключ Tinkoff загружен из secrets.toml")
        st.success("🚀 Реальный WebSocket провайдер инициализирован!")
    else:
        st.warning("⚠️ API ключ Tinkoff не найден. Проверьте .streamlit/secrets.toml")

# Создаем вкладки
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Data Overview", 
    "🔄 Data Updater", 
    "⚡ Real-Time WebSocket", 
    "🧠 ML Integration",
    "⚙️ Settings",
    "🔗 WebSocket Status"
])

with tab1:
    st.header("📊 Обзор данных по таймфреймам")
    
    # Получаем статус всех таймфреймов
    if 'real_data_updater' in st.session_state:
        updater = st.session_state.real_data_updater
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
        
        # Информация о провайдерах
        if 'real_multi_analyzer' in st.session_state:
            analyzer = st.session_state.real_multi_analyzer
            provider_info = analyzer.get_provider_info()
            
            st.subheader("🔗 Информация о провайдерах данных")
            provider_data = []
            for timeframe, providers in provider_info.items():
                for provider in providers:
                    provider_data.append({
                        'Timeframe': timeframe,
                        'Provider': provider['name'],
                        'Available': '✅' if provider['available'] else '❌',
                        'WebSocket': '✅' if provider.get('websocket_available', False) else '❌',
                        'Connected': '✅' if provider.get('websocket_connected', False) else '❌'
                    })
            
            st.dataframe(pd.DataFrame(provider_data), use_container_width=True)
        
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
            
            # Специальная информация для WebSocket данных
            if selected_timeframe in ['1s', 'tick']:
                st.info("🌐 **WebSocket данные**: Этот таймфрейм использует реальный WebSocket провайдер Tinkoff API")
                
                if 'real_multi_analyzer' in st.session_state:
                    analyzer = st.session_state.real_multi_analyzer
                    ws_provider = analyzer.get_websocket_provider()
                    if ws_provider:
                        st.success(f"✅ WebSocket провайдер доступен")
                        st.info(f"🔗 Подключен: {'Да' if ws_provider.is_connected() else 'Нет'}")
                    else:
                        st.warning("⚠️ WebSocket провайдер недоступен")

with tab2:
    st.header("🔄 Управление обновлением данных")
    
    if 'real_data_updater' not in st.session_state:
        st.error("Real data updater не инициализирован")
        st.stop()
    
    updater = st.session_state.real_data_updater
    
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
            
            # Показываем тип данных
            if timeframe in ['1s', 'tick']:
                st.caption("🌐 WebSocket")
            
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

with tab3:
    st.header("⚡ Данные в реальном времени через WebSocket")
    
    if 'real_time_manager' not in st.session_state or st.session_state.real_time_manager is None:
        st.error("Real-time менеджер не инициализирован")
        st.stop()
    
    manager = st.session_state.real_time_manager
    
    # Статус подключения
    connection_status = manager.get_connection_status()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🌐 WebSocket", "✅ Подключен" if connection_status['websocket_connected'] else "❌ Отключен")
    
    with col2:
        st.metric("📡 Подписки", connection_status['active_subscriptions'])
    
    with col3:
        st.metric("📊 Кэш символов", connection_status['cached_symbols'])
    
    with col4:
        st.metric("🔑 API ключ", "✅ Есть" if connection_status['api_key_available'] else "❌ Нет")
    
    # Выбор символов для мониторинга
    col1, col2 = st.columns([2, 1])
    
    with col1:
        available_symbols = st.session_state.real_multi_analyzer.get_available_symbols()
        selected_symbols_rt = st.multiselect(
            "Выберите символы для мониторинга в реальном времени:",
            available_symbols,
            default=available_symbols[:3] if available_symbols else [],
            key="real_time_symbols"
        )
    
    with col2:
        timeframe_rt = st.selectbox(
            "Выберите таймфрейм:",
            ['1s', 'tick', 'orderbook'],  # Реальные WebSocket данные
            key="real_time_timeframe"
        )
    
    # Кнопки управления
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ Начать мониторинг", key="start_real_time"):
            if selected_symbols_rt:
                st.info(f"Запуск мониторинга в реальном времени для {len(selected_symbols_rt)} символов...")
                for symbol in selected_symbols_rt:
                    figi = st.session_state.real_multi_analyzer.get_figi_for_symbol(symbol)
                    if figi:
                        asyncio.run(manager.start_real_time_data(figi, timeframe_rt))
                        st.success(f"✅ Мониторинг для {symbol} запущен.")
                    else:
                        st.error(f"❌ FIGI не найден для символа {symbol}.")
            else:
                st.warning("Выберите хотя бы один символ для мониторинга.")
    
    with col2:
        if st.button("⏹️ Остановить мониторинг", key="stop_real_time"):
            st.info("Остановка мониторинга в реальном времени...")
            asyncio.run(manager.stop_all_real_time_data())
            st.success("✅ Мониторинг остановлен.")
    
    # Отображение данных в реальном времени
    st.subheader("📊 Последние данные в реальном времени")
    
    if selected_symbols_rt:
        latest_data_display = []
        for symbol in selected_symbols_rt:
            data = manager.get_latest_data(symbol)
            if data:
                latest_data_display.append({
                    "Symbol": symbol,
                    "Type": data.get('type', 'unknown'),
                    "Last Update": data.get('timestamp'),
                    "Data": json.dumps(data, default=str)[:100] + "..." if len(str(data)) > 100 else json.dumps(data, default=str)
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
    
    Реальные многоуровневые данные могут использоваться для:
    - 📊 Анализа паттернов на разных таймфреймах
    - 🧠 Обучения ML моделей на реальных данных
    - ⚡ Предсказания в реальном времени
    - 🎯 Оптимизации торговых стратегий
    - 🌐 Использования реальных WebSocket данных
    """)
    
    # Показать доступные данные для ML
    if 'real_data_updater' in st.session_state:
        updater = st.session_state.real_data_updater
        ml_data_status = updater.get_all_timeframe_status()
        
        st.subheader("📊 Данные доступные для ML")
        
        ml_ready_data = []
        for timeframe, status in ml_data_status.items():
            if status['record_count'] > 0:
                data_source = "🌐 WebSocket" if timeframe in ['1s', 'tick'] else "📡 REST API"
                ml_ready_data.append({
                    'Timeframe': timeframe,
                    'Records': status['record_count'],
                    'Symbols': status['symbol_count'],
                    'Source': data_source,
                    'ML Ready': '✅' if status['record_count'] > 100 else '⚠️'
                })
        
        if ml_ready_data:
            st.dataframe(pd.DataFrame(ml_ready_data), use_container_width=True)
            
            st.info("💡 Реальные данные готовы для использования в ML моделях")
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
    
    # Настройки WebSocket
    st.subheader("🌐 WebSocket Настройки")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sandbox_mode = st.checkbox("Песочница (Sandbox)", value=False)
        if sandbox_mode:
            st.info("🧪 Режим песочницы включен")
        else:
            st.warning("⚠️ Режим продакшена")
    
    with col2:
        if st.button("🔄 Переподключить WebSocket"):
            st.info("Переподключение к WebSocket...")
            # Здесь можно добавить логику переподключения
    
    st.subheader("📊 Настройки обновления")
    
    # Показать расписание обновления
    if 'real_data_updater' in st.session_state:
        updater = st.session_state.real_data_updater
        
        st.write("**Текущее расписание:**")
        schedules = updater.update_schedules
        
        for timeframe, schedule_info in schedules.items():
            data_source = "🌐 WebSocket" if timeframe in ['1s', 'tick'] else "📡 REST API"
            st.write(f"- **{timeframe}**: {schedule_info['interval']} в {schedule_info['time']} ({data_source})")

with tab6:
    st.header("🔗 WebSocket Status")
    
    if 'real_time_manager' not in st.session_state:
        st.error("Real-time менеджер не инициализирован")
        st.stop()
    
    manager = st.session_state.real_time_manager
    
    # Детальная информация о WebSocket
    connection_status = manager.get_connection_status()
    
    st.subheader("📊 Статус подключения")
    
    status_data = [
        {"Parameter": "WebSocket Connected", "Value": "✅ Yes" if connection_status['websocket_connected'] else "❌ No"},
        {"Parameter": "Active Subscriptions", "Value": connection_status['active_subscriptions']},
        {"Parameter": "Cached Symbols", "Value": connection_status['cached_symbols']},
        {"Parameter": "API Key Available", "Value": "✅ Yes" if connection_status['api_key_available'] else "❌ No"},
    ]
    
    st.dataframe(pd.DataFrame(status_data), use_container_width=True)
    
    # Информация о подписках
    if connection_status['subscriptions']:
        st.subheader("📡 Активные подписки")
        for subscription in connection_status['subscriptions']:
            st.write(f"- {subscription}")
    else:
        st.info("Нет активных подписок")
    
    # Кэшированные данные
    st.subheader("💾 Кэшированные данные")
    all_data = manager.get_all_latest_data()
    
    if all_data:
        cache_data = []
        for symbol, data in all_data.items():
            cache_data.append({
                "Symbol": symbol,
                "Type": data.get('type', 'unknown'),
                "Last Update": data.get('timestamp', 'Never'),
                "Data Size": len(str(data))
            })
        
        st.dataframe(pd.DataFrame(cache_data), use_container_width=True)
    else:
        st.info("Нет кэшированных данных")
    
    # Кнопки управления WebSocket
    st.subheader("🎛️ Управление WebSocket")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔌 Подключить"):
            st.info("Подключение к WebSocket...")
            # Здесь можно добавить логику подключения
    
    with col2:
        if st.button("🔌 Отключить"):
            st.info("Отключение от WebSocket...")
            # Здесь можно добавить логику отключения
    
    with col3:
        if st.button("🔄 Обновить статус"):
            st.rerun()
