"""
Unified Multi-Timeframe Data Management Page.
Объединенная страница управления многоуровневыми данными с поддержкой акций и фьючерсов.
"""

import streamlit as st
import pandas as pd
import asyncio
from datetime import datetime, timedelta
import logging
import json

# Импорты для работы с многоуровневыми данными
try:
    from core.multi_timeframe_analyzer_enhanced import (
        EnhancedMultiTimeframeStockAnalyzer, 
        WebSocketDataProvider
    )
    from core.data_updater_with_shares import DataUpdaterWithShares  # Используем версию с поддержкой акций
    from core.realtime_manager_enhanced import EnhancedRealTimeDataManager
    from core.shares_integration import SharesIntegrator
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
    page_title="Multi-Timeframe Data Management",
    page_icon="⏰",
    layout="wide"
)

st.title("⏰ Multi-Timeframe Data Management")
st.caption("Управление данными разных таймфреймов с поддержкой акций (shares) и фьючерсов (futures)")

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
        st.session_state.multi_analyzer = EnhancedMultiTimeframeStockAnalyzer(api_key=api_key)
        st.session_state.data_updater = DataUpdaterWithShares(api_key, max_requests_per_minute=50)
        st.session_state.real_time_manager = EnhancedRealTimeDataManager(api_key)
        st.session_state.shares_integrator = SharesIntegrator()
        st.success("✅ API ключ Tinkoff загружен из secrets.toml")
        st.info("🚀 DataUpdater с поддержкой акций и фьючерсов включен (50 запросов/мин)")
    else:
        st.warning("⚠️ API ключ Tinkoff не найден. Проверьте .streamlit/secrets.toml")

# Создаем вкладки
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Data Overview", 
    "🔄 Data Updater", 
    "📈 Shares Integration",
    "⚡ Real-Time", 
    "🧠 ML Integration",
    "⚙️ Settings"
])

with tab1:
    st.header("📊 Обзор данных по таймфреймам")
    
    # Получаем статус всех таймфреймов
    if 'data_updater' in st.session_state:
        updater = st.session_state.data_updater
        try:
            all_status = updater.get_all_timeframe_status()
        except AttributeError as e:
            st.error(f"❌ Ошибка получения статуса таймфреймов: {e}")
            st.info("💡 Попробуйте перезапустить страницу")
            all_status = {}
        
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
        
        # Статистика по типам активов
        st.subheader("📈 Статистика по типам активов")
        
        asset_stats = updater.get_asset_statistics()
        if asset_stats:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📊 Акции (shares)", asset_stats.get('shares', 0))
            
            with col2:
                st.metric("📈 Фьючерсы (futures)", asset_stats.get('futures', 0))
            
            with col3:
                st.metric("❓ Неизвестно", asset_stats.get('unknown', 0))
        
        # Детальная информация по каждому таймфрейму
        st.subheader("🔍 Детальная информация")
        
        selected_timeframe = st.selectbox(
            "Выберите таймфрейм для детального просмотра:",
            ['1d', '1h', '1m', '5m', '15m']
        )
        
        if selected_timeframe:
            status = all_status.get(selected_timeframe, {})
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📊 Записей", status.get('record_count', 0))
            
            with col2:
                st.metric("🏷️ Символов", status.get('symbol_count', 0))
            
            with col3:
                st.metric("📅 Последнее обновление", 
                         status.get('last_record', 'Never')[:19] if status.get('last_record') else 'Never')
            
            # Показать примеры данных
            if status.get('table_exists') and status.get('record_count', 0) > 0:
                st.subheader(f"📋 Пример данных ({selected_timeframe})")
                
                try:
                    # Получаем примеры данных из таблицы
                    table_name = f"data_{selected_timeframe.replace('m', 'min').replace('h', 'hour')}"
                    
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
    
    # Статистика обновлений
    stats = updater.get_update_stats()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🛡️ Rate Limit Hits", stats.get('rate_limit_hits', 0))
    
    with col2:
        st.metric("📊 Запросов/мин", stats.get('current_requests_per_minute', 0))
    
    with col3:
        st.metric("❌ Ошибок", len(stats.get('errors', {})))
    
    with col4:
        st.metric("📈 Процент успеха", 
                 f"{(stats.get('successful_updates', 0) / max(stats.get('total_symbols', 1), 1)) * 100:.1f}%")
    
    # Статистика по типам активов
    st.subheader("📊 Статистика обновлений по типам активов")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 Акции обновлено", stats.get('shares_updated', 0))
    
    with col2:
        st.metric("📈 Фьючерсы обновлено", stats.get('futures_updated', 0))
    
    with col3:
        st.metric("📊 Всего активов", stats.get('total_symbols', 0))
    
    # Управление таймфреймами
    st.subheader("⏰ Управление таймфреймами")
    
    timeframes = ['1d', '1h', '1m', '5m', '15m']
    
    # Создаем колонки для каждого таймфрейма
    cols = st.columns(len(timeframes))
    
    for i, timeframe in enumerate(timeframes):
        with cols[i]:
            st.write(f"**{timeframe}**")
            st.caption("✅ Включено")
            
            # Кнопка для ручного обновления
            if st.button(f"🔄 Обновить {timeframe}", key=f"update_{timeframe}"):
                with st.spinner(f"Обновление {timeframe} данных для всех активов..."):
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
                
                st.success(f"✅ {timeframe} данные обновлены для всех активов")
    
    # Информация об оптимизации
    st.info("""
    🚀 **DataUpdater с поддержкой акций и фьючерсов:**
    - Максимум 50 запросов в минуту
    - Обработка всех активов батчами по 10
    - Соблюдение deadline'ов API (500ms для GetCandles)
    - Автоматическое ожидание при достижении лимита
    - Поддержка акций (shares) и фьючерсов (futures)
    """)

with tab3:
    st.header("📈 Интеграция акций (Shares)")
    
    if 'shares_integrator' not in st.session_state:
        st.error("Shares integrator не инициализирован")
        st.stop()
    
    integrator = st.session_state.shares_integrator
    
    # Статистика по типам активов
    st.subheader("📊 Текущая статистика активов")
    
    asset_stats = integrator.get_asset_statistics()
    if asset_stats:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Акции", asset_stats.get('shares', 0))
        
        with col2:
            st.metric("📈 Фьючерсы", asset_stats.get('futures', 0))
        
        with col3:
            st.metric("❓ Неизвестно", asset_stats.get('unknown', 0))
        
        with col4:
            total = sum(asset_stats.values())
            st.metric("📊 Всего", total)
    
    # Кнопки управления интеграцией
    st.subheader("🔧 Управление интеграцией")
    
    # Настройки фильтрации
    col1, col2 = st.columns([2, 1])
    
    with col1:
        russian_only = st.checkbox(
            "🇷🇺 Только российские акции", 
            value=True, 
            help="Фильтровать только российские акции: INSTRUMENT_STATUS_BASE + RUB валюта + RU ISIN"
        )
    
    with col2:
        if st.button("🔄 Обновить статистику", key="refresh_stats"):
            st.rerun()
    
    # Кнопка интеграции
    if st.button("🔄 Интегрировать акции", key="integrate_shares"):
        with st.spinner("Загрузка акций из Tinkoff API..."):
            try:
                integrator.integrate_shares_into_database(st.session_state.tinkoff_api_key, russian_only)
                if russian_only:
                    st.success("✅ Российские акции успешно интегрированы!")
                else:
                    st.success("✅ Все акции успешно интегрированы!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Ошибка интеграции акций: {e}")
    
    # Списки активов
    st.subheader("📋 Списки активов")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📊 Акции (shares):**")
        shares_list = integrator.get_shares_only()
        if shares_list:
            st.write(f"Всего акций: {len(shares_list)}")
            # Показываем первые 20 акций
            st.write(shares_list[:20])
            if len(shares_list) > 20:
                st.write(f"... и еще {len(shares_list) - 20} акций")
        else:
            st.info("Акции не загружены. Нажмите 'Интегрировать акции'")
    
    with col2:
        st.write("**📈 Фьючерсы (futures):**")
        futures_list = integrator.get_futures_only()
        if futures_list:
            st.write(f"Всего фьючерсов: {len(futures_list)}")
            # Показываем первые 20 фьючерсов
            st.write(futures_list[:20])
            if len(futures_list) > 20:
                st.write(f"... и еще {len(futures_list) - 20} фьючерсов")
        else:
            st.info("Фьючерсы не найдены")
    
    # Информация о интеграции
    st.info("""
    💡 **Интеграция акций:**
    - 🇷🇺 **Фильтрация российских акций** - INSTRUMENT_STATUS_BASE + RUB валюта + RU ISIN
    - 📊 **Фильтрация по типу акций** - только обыкновенные и привилегированные (не ADR/GDR)
    - 🏢 Добавляет их в таблицу companies с asset_type = 'shares'
    - 💾 Сохраняет метаданные: ticker, figi, name, isin, lot_size, currency, share_type
    - 🔄 Обновляет существующие фьючерсы с asset_type = 'futures'
    - ✅ Совместимо с существующей системой
    - 🎯 **Результат**: только российские акции (RUB валюта, RU ISIN)
    """)

with tab4:
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
        - 🎯 Множественные символы (акции + фьючерсы)
        """)
        
        st.info("💡 Пока используйте вкладку 'Data Updater' для получения данных")
    else:
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
            # Получаем списки акций и фьючерсов
            shares_list = integrator.get_shares_only()
            futures_list = integrator.get_futures_only()
            all_assets = shares_list + futures_list
            
            selected_symbols_rt = st.multiselect(
                "Выберите активы для мониторинга в реальном времени:",
                all_assets,
                default=all_assets[:5] if all_assets else [],
                key="real_time_symbols"
            )
        
        with col2:
            timeframe_rt = st.selectbox(
                "Выберите таймфрейм:",
                ['1s', 'tick', 'orderbook'],
                key="real_time_timeframe"
            )
        
        # Кнопки управления
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ Начать мониторинг", key="start_real_time"):
                if selected_symbols_rt:
                    st.info(f"Запуск мониторинга в реальном времени для {len(selected_symbols_rt)} активов...")
                    for symbol in selected_symbols_rt:
                        figi = st.session_state.multi_analyzer.get_figi_for_symbol(symbol)
                        if figi:
                            asyncio.run(manager.start_real_time_data(figi, timeframe_rt))
                            st.success(f"✅ Мониторинг для {symbol} запущен.")
                        else:
                            st.error(f"❌ FIGI не найден для актива {symbol}.")
                else:
                    st.warning("Выберите хотя бы один актив для мониторинга.")
        
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
            st.info("Выберите активы для просмотра данных в реальном времени.")

with tab5:
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
    - 📈 Анализа акций и фьючерсов
    """)
    
    # Показать доступные данные для ML
    if 'data_updater' in st.session_state:
        updater = st.session_state.data_updater
        try:
            ml_data_status = updater.get_all_timeframe_status()
        except AttributeError as e:
            st.error(f"❌ Ошибка получения статуса для ML: {e}")
            ml_data_status = {}
        
        st.subheader("📊 Данные доступные для ML")
        
        ml_ready_data = []
        for timeframe, status in ml_data_status.items():
            if status.get('record_count', 0) > 0:
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

with tab6:
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
    
    st.subheader("🛡️ Rate Limiting Настройки")
    
    if 'data_updater' in st.session_state:
        updater = st.session_state.data_updater
        stats = updater.get_update_stats()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🛡️ Rate Limit Hits", stats.get('rate_limit_hits', 0))
        
        with col2:
            st.metric("📊 Текущих запросов/мин", stats.get('current_requests_per_minute', 0))
        
        with col3:
            st.metric("🎯 Лимит запросов/мин", updater.max_requests_per_minute)
        
        st.info("""
        **Текущие настройки Rate Limiting:**
        - Максимум 50 запросов в минуту
        - Автоматическое ожидание при достижении лимита
        - Поддержка акций и фьючерсов
        """)
    
    st.subheader("📊 Настройки обновления")
    
    # Показать расписание обновления
    if 'data_updater' in st.session_state:
        updater = st.session_state.data_updater
        
        st.write("**Текущее расписание:**")
        schedules = updater.update_schedules
        
        for timeframe, schedule_info in schedules.items():
            st.write(f"- **{timeframe}**: {schedule_info['interval']} в {schedule_info['time']} (✅ Включено)")
    
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
            'total_errors': len(stats['errors']) if stats['errors'] else 0,
            'rate_limit_hits': stats.get('rate_limit_hits', 0),
            'current_requests_per_minute': stats.get('current_requests_per_minute', 0),
            'shares_updated': stats.get('shares_updated', 0),
            'futures_updated': stats.get('futures_updated', 0)
        })