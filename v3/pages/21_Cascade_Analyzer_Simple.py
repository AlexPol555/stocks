#!/usr/bin/env python3
"""
Cascade Multi-Timeframe Analyzer Page.
Страница каскадного анализа многоуровневых торговых сигналов.
"""

import streamlit as st
import pandas as pd
import asyncio
import json
from datetime import datetime, timedelta
import logging

# Импорты для каскадного анализа
try:
    from core.cascade_analyzer import CascadeAnalyzer, CascadeSignalResult
    from core.cascade_notifications import CascadeNotificationManager
    from core.multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
    from core import demo_trading
    from core.database import get_connection
    CASCADE_AVAILABLE = True
except ImportError as e:
    CASCADE_AVAILABLE = False
    st.error(f"Каскадный анализатор недоступен: {e}")

# Импорты для ML
try:
    from core.ml import create_ml_integration_manager, create_fallback_ml_manager
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Cascade Analyzer",
    page_icon="🎯",
    layout="wide"
)

st.title("Cascade Multi-Timeframe Analyzer")
st.caption("Каскадный анализ многоуровневых торговых сигналов с ML подтверждением")

# Проверка доступности компонентов
if not CASCADE_AVAILABLE:
    st.error("Каскадный анализатор недоступен. Проверьте установку зависимостей.")
    st.stop()

# Инициализация компонентов
if 'cascade_analyzer' not in st.session_state:
    try:
        # Получаем API ключ
        api_key = None
        if hasattr(st, 'secrets') and hasattr(st.secrets, 'TINKOFF_API_KEY'):
            api_key = st.secrets.TINKOFF_API_KEY
            st.session_state.tinkoff_api_key = api_key
        
        if not api_key:
            api_key = st.session_state.get('tinkoff_api_key')
        
        # Создаем анализаторы
        multi_analyzer = EnhancedMultiTimeframeStockAnalyzer(api_key=api_key)
        
        # ML менеджер
        ml_manager = None
        if ML_AVAILABLE:
            try:
                ml_manager = create_ml_integration_manager()
                st.success("ML менеджер загружен")
            except Exception as e:
                ml_manager = create_fallback_ml_manager()
                st.warning(f"Используется fallback ML режим: {e}")
        
        # Создаем каскадный анализатор
        st.session_state.cascade_analyzer = CascadeAnalyzer(
            multi_analyzer=multi_analyzer,
            ml_manager=ml_manager,
            demo_trading=demo_trading
        )
        
        # Создаем менеджер уведомлений
        from core.notifications import NotificationManager
        notification_manager = NotificationManager()
        st.session_state.cascade_notifications = CascadeNotificationManager(notification_manager)
        
        st.success("Каскадный анализатор инициализирован")
        
        # Автоматически запускаем предварительный ML анализ при первой загрузке
        if 'initial_ml_analysis_done' not in st.session_state:
            st.info("🔄 Выполняется предварительный ML анализ всех доступных символов...")
            try:
                # Получаем все доступные символы
                available_symbols = st.session_state.cascade_analyzer.get_available_symbols_with_1d_data()
                
                if available_symbols:
                    # Запускаем предварительный ML анализ
                    initial_ml_results = asyncio.run(
                        st.session_state.cascade_analyzer.perform_initial_ml_analysis(available_symbols)
                    )
                    st.session_state.initial_ml_analysis_done = True
                    st.success(f"✅ Предварительный ML анализ завершен для {len(initial_ml_results)} символов")
                else:
                    st.warning("⚠️ Не найдено символов с данными 1d")
                    st.session_state.initial_ml_analysis_done = True
                    
            except Exception as e:
                st.warning(f"⚠️ Ошибка предварительного ML анализа: {e}")
                st.session_state.initial_ml_analysis_done = True
        
    except Exception as e:
        st.error(f"Ошибка инициализации: {e}")
        st.stop()

# Получаем компоненты
cascade_analyzer = st.session_state.cascade_analyzer
notification_manager = st.session_state.cascade_notifications

# Создаем вкладки
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Анализ сигналов", 
    "Автоторговля", 
    "Уведомления", 
    "Настройки",
    "История"
])

with tab1:
    st.header("Анализ каскадных сигналов")
    
    # Автоматический анализ всех доступных символов
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Статус анализа")
        
        # Получаем статус анализа
        try:
            analysis_status = asyncio.run(cascade_analyzer.get_analysis_status())
            
            # Отображаем статус
            status_col1, status_col2, status_col3 = st.columns(3)
            
            with status_col1:
                st.metric(
                    "Символов с данными 1d", 
                    analysis_status.get('total_symbols_with_1d_data', 0)
                )
            
            with status_col2:
                st.metric(
                    "ML анализ завершен", 
                    "Да" if analysis_status.get('ml_analysis_completed', False) else "Нет"
                )
            
            with status_col3:
                st.metric(
                    "Готово к каскадному анализу", 
                    analysis_status.get('symbols_with_strong_signals', 0)
                )
            
            # Дополнительная информация
            if analysis_status.get('ml_analysis_completed', False):
                st.success(f"✅ ML анализ завершен для {analysis_status.get('symbols_with_ml_results', 0)} символов")
                st.info(f"🔍 Найдено {analysis_status.get('symbols_with_strong_signals', 0)} символов с сильными ML сигналами")
            else:
                st.warning("⚠️ ML анализ не выполнен. Нажмите 'Запустить анализ' для начала")
            
            # Показываем ошибку, если есть
            if 'error' in analysis_status:
                st.error(f"Ошибка получения статуса: {analysis_status['error']}")
                
        except Exception as e:
            st.error(f"Ошибка получения статуса анализа: {e}")
            analysis_status = {
                'total_symbols_with_1d_data': 0,
                'symbols_with_ml_results': 0,
                'symbols_with_strong_signals': 0,
                'ml_analysis_completed': False,
                'ready_for_cascade': False
            }
    
    with col2:
        st.subheader("Управление")
        
        # Кнопка запуска анализа
        if st.button("🚀 Запустить анализ", type="primary", use_container_width=True):
            print("🚀 [CASCADE] Кнопка 'Запустить анализ' нажата")
            
            with st.spinner("Выполняется каскадный анализ всех доступных символов..."):
                try:
                    print("📊 [CASCADE] Начинаем каскадный анализ...")
                    
                    # Получаем статус перед анализом
                    print("🔍 [CASCADE] Получаем статус анализа...")
                    pre_status = asyncio.run(cascade_analyzer.get_analysis_status())
                    print(f"📈 [CASCADE] Статус до анализа: {pre_status}")
                    
                    # Запускаем автоматический анализ всех символов
                    print("⚡ [CASCADE] Запускаем analyze_all_available_symbols()...")
                    results = asyncio.run(cascade_analyzer.analyze_all_available_symbols())
                    print(f"✅ [CASCADE] Анализ завершен! Получено {len(results)} результатов")
                    
                    # Сохраняем результаты
                    st.session_state.cascade_results = results
                    print("💾 [CASCADE] Результаты сохранены в session_state")
                    
                    # Анализируем результаты
                    successful_results = cascade_analyzer.get_successful_signals(results)
                    rejected_results = cascade_analyzer.get_rejected_signals(results)
                    print(f"📊 [CASCADE] Успешных сигналов: {len(successful_results)}")
                    print(f"❌ [CASCADE] Отклоненных сигналов: {len(rejected_results)}")
                    
                    # Показываем детали успешных сигналов
                    if successful_results:
                        print("🎯 [CASCADE] Успешные сигналы:")
                        for i, result in enumerate(successful_results[:5]):  # Показываем первые 5
                            print(f"  {i+1}. {result.symbol}: {result.final_signal} (уверенность: {result.confidence:.1%})")
                    
                    # Показываем детали отклоненных сигналов
                    if rejected_results:
                        print("🚫 [CASCADE] Отклоненные сигналы:")
                        for i, result in enumerate(rejected_results[:5]):  # Показываем первые 5
                            print(f"  {i+1}. {result.symbol}: отклонен на этапе {result.rejected_at_stage} - {result.rejection_reason}")
                    
                    # Отправляем уведомления
                    print("📢 [CASCADE] Отправляем уведомления...")
                    notification_count = 0
                    for result in results:
                        if result.final_signal:
                            try:
                                asyncio.run(notification_manager.notify_cascade_signal(result))
                                notification_count += 1
                            except Exception as e:
                                print(f"⚠️ [CASCADE] Ошибка отправки уведомления для {result.symbol}: {e}")
                    
                    print(f"📨 [CASCADE] Отправлено {notification_count} уведомлений")
                    
                    st.success(f"✅ Анализ завершен! Обработано {len(results)} символов")
                    print("🎉 [CASCADE] Анализ полностью завершен успешно")
                    st.rerun()
                    
                except Exception as e:
                    print(f"❌ [CASCADE] Критическая ошибка анализа: {e}")
                    import traceback
                    print(f"🔍 [CASCADE] Traceback: {traceback.format_exc()}")
                    st.error(f"❌ Ошибка анализа: {e}")
        
        # Кнопка обновления статуса
        if st.button("🔄 Обновить статус", use_container_width=True):
            st.rerun()
        
        # Кнопка очистки результатов
        if st.button("🗑️ Очистить результаты", use_container_width=True):
            if 'cascade_results' in st.session_state:
                del st.session_state.cascade_results
            st.success("Результаты очищены")
            st.rerun()
    
    # Информация о процессе анализа
    st.subheader("Процесс анализа")
    
    with st.expander("ℹ️ Как работает каскадный анализ", expanded=False):
        st.markdown("""
        **Каскадный анализ выполняется в несколько этапов:**
        
        1. **📊 Предварительный ML анализ (1d)** - Анализ дневных данных с помощью ML моделей
        2. **🔍 Фильтрация по силе сигнала** - Отбор только символов с сильными ML сигналами (уверенность ≥ 50%)
        3. **⏰ Подтверждение на часовых данных (1h)** - Проверка тренда и объема
        4. **🎯 Поиск точки входа (1m)** - Определение оптимальной цены входа и стоп-лосса
        5. **⚡ Микро-оптимизация (1s)** - Точная настройка времени входа
        
        **Результат:** Только самые качественные торговые сигналы с высокой вероятностью успеха.
        """)
    
    # Показываем прогресс, если анализ выполняется
    if 'cascade_analysis_in_progress' in st.session_state and st.session_state.cascade_analysis_in_progress:
        st.info("🔄 Выполняется каскадный анализ... Пожалуйста, подождите.")
        st.progress(0.5)  # Можно сделать более детальный прогресс
    
    # Отображение результатов
    if 'cascade_results' in st.session_state:
        results = st.session_state.cascade_results
        successful_results = cascade_analyzer.get_successful_signals(results)
        rejected_results = cascade_analyzer.get_rejected_signals(results)
        
        # Статистика
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Всего проанализировано", len(results))
        
        with col2:
            st.metric("Успешных сигналов", len(successful_results))
        
        with col3:
            st.metric("Отклоненных сигналов", len(rejected_results))
        
        with col4:
            avg_confidence = sum(r.confidence for r in successful_results) / len(successful_results) if successful_results else 0
            st.metric("Средняя уверенность", f"{avg_confidence:.1%}")
        
        # Успешные сигналы
        if successful_results:
            st.subheader("Успешные сигналы")
            
            # Создаем DataFrame для отображения
            successful_data = []
            for result in successful_results:
                successful_data.append({
                    'Символ': result.symbol,
                    'Сигнал': result.final_signal,
                    'Уверенность': f"{result.confidence:.1%}",
                    'Цена входа': f"{result.entry_price:.2f} RUB",
                    'Стоп-лосс': f"{result.stop_loss:.2f} RUB",
                    'Тейк-профит': f"{result.take_profit:.2f} RUB",
                    'Риск/Доходность': f"{result.risk_reward:.1f}",
                    'Автоторговля': "Да" if result.auto_trade_enabled else "Нет",
                    'Время': result.timestamp.strftime('%H:%M:%S')
                })
            
            df_successful = pd.DataFrame(successful_data)
            st.dataframe(df_successful, use_container_width=True)
        
        # Отклоненные сигналы
        if rejected_results:
            st.subheader("Отклоненные сигналы")
            
            rejected_data = []
            for result in rejected_results:
                rejected_data.append({
                    'Символ': result.symbol,
                    'Отклонен на этапе': result.rejected_at_stage,
                    'Причина': result.rejection_reason,
                    'Время': result.timestamp.strftime('%H:%M:%S')
                })
            
            df_rejected = pd.DataFrame(rejected_data)
            st.dataframe(df_rejected, use_container_width=True)

with tab2:
    st.header("Автоматическая торговля")
    
    # Статус автоторговли
    auto_trade_status = cascade_analyzer.get_auto_trade_status()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("Текущий статус автоторговли:")
        st.write(f"- Включена: {'Да' if auto_trade_status['enabled'] else 'Нет'}")
        st.write(f"- Минимальная уверенность: {auto_trade_status['min_confidence']:.1%}")
        st.write(f"- Максимальный размер позиции: {auto_trade_status['max_position_size']} RUB")
        st.write(f"- Риск на сделку: {auto_trade_status['risk_per_trade']:.1%}")
        st.write(f"- Максимум сделок в день: {auto_trade_status['max_daily_trades']}")
        st.write(f"- Торговые часы: {auto_trade_status['trading_hours']['start']}:00 - {auto_trade_status['trading_hours']['end']}:00")
        st.write(f"- Сейчас торговые часы: {'Да' if auto_trade_status['is_trading_hours'] else 'Нет'}")
    
    with col2:
        if st.button("Обновить статус"):
            st.rerun()

with tab3:
    st.header("Настройки уведомлений")
    
    # Текущие настройки уведомлений
    notification_config = notification_manager.get_notification_config()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Текущие настройки")
        st.write(f"- Уведомления включены: {'Да' if notification_config['enabled'] else 'Нет'}")
        st.write(f"- Минимальная уверенность: {notification_config['min_confidence_for_notification']:.1%}")
        st.write(f"- Минимальный риск/доходность: {notification_config['min_risk_reward_for_notification']:.1f}")
        st.write(f"- Уведомления об автоторговле: {'Да' if notification_config['auto_trade_notifications'] else 'Нет'}")
        st.write(f"- Уведомления об отклонениях: {'Да' if notification_config['stage_rejection_notifications'] else 'Нет'}")
        st.write(f"- Дневная сводка: {'Да' if notification_config['daily_summary'] else 'Нет'}")
    
    with col2:
        st.subheader("Каналы уведомлений")
        st.write(f"- Telegram: {'Да' if notification_config['telegram_enabled'] else 'Нет'}")
        st.write(f"- Email: {'Да' if notification_config['email_enabled'] else 'Нет'}")
        st.write(f"- Webhook: {'Да' if notification_config['webhook_enabled'] else 'Нет'}")

with tab4:
    st.header("Настройки каскадного анализа")
    
    # Настройки этапов
    st.subheader("Настройки этапов анализа")
    
    stage_configs = cascade_analyzer.stage_configs
    
    for stage, config in stage_configs.items():
        with st.expander(f"Этап {stage}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("Текущие настройки:")
                st.write(f"- Минимальная уверенность: {config['min_confidence']:.1%}")
                st.write(f"- Период данных: {config['lookback_days']} дней")
            
            with col2:
                st.write("Требования:")
                if 'required_signals' in config:
                    st.write(f"- Требуемые сигналы: {', '.join(config['required_signals'])}")
                if 'required_confirmations' in config:
                    st.write(f"- Требуемые подтверждения: {', '.join(config['required_confirmations'])}")

with tab5:
    st.header("История каскадного анализа")
    
    # Здесь можно добавить сохранение истории в базу данных
    st.info("История анализа будет сохранена в базе данных в следующих версиях")
    
    if 'cascade_results' in st.session_state:
        results = st.session_state.cascade_results
        
        # Экспорт результатов
        st.subheader("Экспорт результатов")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Экспорт в CSV"):
                try:
                    # Создаем DataFrame для экспорта
                    export_data = []
                    for result in results:
                        export_data.append(result.to_dict())
                    
                    df_export = pd.DataFrame(export_data)
                    csv = df_export.to_csv(index=False)
                    
                    st.download_button(
                        label="Скачать CSV",
                        data=csv,
                        file_name=f"cascade_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                except Exception as e:
                    st.error(f"Ошибка экспорта: {e}")
        
        with col2:
            if st.button("Экспорт в JSON"):
                try:
                    export_data = [result.to_dict() for result in results]
                    json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
                    
                    st.download_button(
                        label="Скачать JSON",
                        data=json_data,
                        file_name=f"cascade_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                    
                except Exception as e:
                    st.error(f"Ошибка экспорта: {e}")
    
    else:
        st.info("Нет результатов для экспорта. Сначала запустите анализ.")

# Футер с информацией
st.divider()
st.caption("Cascade Multi-Timeframe Analyzer - Система каскадного анализа многоуровневых торговых сигналов")
