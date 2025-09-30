#!/usr/bin/env python3
"""
Enhanced Cascade Analyzer Page.
Страница улучшенного каскадного анализатора с предварительной фильтрацией по этапу 1d.
"""

import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime

# Настройка страницы
st.set_page_config(
    page_title="Enhanced Cascade Analyzer",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Enhanced Cascade Analyzer")
st.markdown("**Улучшенный каскадный анализатор с предварительной ML фильтрацией**")

# Инициализация компонентов
@st.cache_resource
def initialize_components():
    """Инициализация компонентов анализатора."""
    try:
        from core.cascade_analyzer import CascadeAnalyzer
        from core.cascade_analyzer_enhanced import EnhancedCascadeAnalyzer
        from core.cascade_notifications import CascadeNotificationManager
        from core.multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
        from core.notifications import NotificationManager
        
        # Получаем API ключ
        api_key = None
        if hasattr(st, 'secrets') and hasattr(st.secrets, 'TINKOFF_API_KEY'):
            api_key = st.secrets.TINKOFF_API_KEY
        elif 'tinkoff_api_key' in st.session_state:
            api_key = st.session_state.tinkoff_api_key
        
        # Создаем компоненты
        multi_analyzer = EnhancedMultiTimeframeStockAnalyzer(api_key=api_key)
        cascade_analyzer = CascadeAnalyzer(
            multi_analyzer=multi_analyzer,
            ml_manager=st.session_state.get('ml_manager'),
            demo_trading=st.session_state.get('demo_trading')
        )
        enhanced_analyzer = EnhancedCascadeAnalyzer(cascade_analyzer)
        notification_manager = NotificationManager()
        cascade_notifications = CascadeNotificationManager(notification_manager)
        
        return enhanced_analyzer, cascade_notifications
        
    except Exception as e:
        st.error(f"Ошибка инициализации: {e}")
        return None, None

# Инициализируем компоненты
enhanced_analyzer, cascade_notifications = initialize_components()

if enhanced_analyzer is None:
    st.error("Не удалось инициализировать анализатор. Проверьте настройки.")
    st.stop()

# Основной интерфейс
tab1, tab2, tab3 = st.tabs(["🎯 Анализ", "📊 Статистика", "⚙️ Настройки"])

with tab1:
    st.header("Предварительная фильтрация по этапу 1d (ML сигналы)")
    
    # Кнопки управления
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Обновить ML фильтр", type="primary"):
            # Очищаем кэш и запускаем новую фильтрацию
            enhanced_analyzer.clear_cache()
            if 'stage1d_results' in st.session_state:
                del st.session_state.stage1d_results
            st.rerun()
    
    with col2:
        if st.button("📊 Показать статистику"):
            stats = enhanced_analyzer.get_cache_stats()
            st.json(stats)
    
    with col3:
        if st.button("🗑️ Очистить кэш"):
            enhanced_analyzer.clear_cache()
            st.success("Кэш очищен")
    
    with col4:
        if st.button("💾 Сохранить результаты"):
            if 'stage1d_results' in st.session_state:
                # Сохраняем результаты в файл
                results_df = pd.DataFrame([r.to_dict() for r in st.session_state.stage1d_results.values()])
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="📥 Скачать CSV",
                    data=csv,
                    file_name=f"stage1d_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    # Получаем все доступные символы
    try:
        all_symbols = enhanced_analyzer.cascade_analyzer.multi_analyzer.get_available_symbols()
        if not all_symbols:
            st.error("Не удалось получить список символов")
            st.stop()
        
        st.info(f"Доступно символов для анализа: {len(all_symbols)}")
        
    except Exception as e:
        st.error(f"Ошибка получения символов: {e}")
        st.stop()
    
    # Проверяем кэш результатов этапа 1d
    if 'stage1d_results' not in st.session_state:
        st.info("🔄 Запуск предварительной фильтрации по этапу 1d (ML сигналы)...")
        
        # Создаем прогресс бар
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Запускаем предварительную фильтрацию синхронно
            import asyncio
            
            # Создаем новый event loop для этой операции
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                stage1d_results = loop.run_until_complete(
                    enhanced_analyzer.prefilter_symbols_stage1d(all_symbols)
                )
                st.session_state.stage1d_results = stage1d_results
                
                progress_bar.progress(1.0)
                status_text.text("✅ Фильтрация завершена!")
                
            finally:
                loop.close()
            
        except Exception as e:
            st.error(f"Ошибка предварительной фильтрации: {e}")
            stage1d_results = {}
            st.session_state.stage1d_results = stage1d_results
    else:
        stage1d_results = st.session_state.stage1d_results
    
    # Получаем кандидатов
    passed_symbols = enhanced_analyzer.get_passed_symbols(stage1d_results)
    buy_candidates = enhanced_analyzer.get_buy_candidates(stage1d_results)
    sell_candidates = enhanced_analyzer.get_sell_candidates(stage1d_results)
    top_candidates = enhanced_analyzer.get_top_candidates(stage1d_results, limit=20)
    
    # Отображаем статистику
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Всего проверено", len(stage1d_results))
    
    with col2:
        st.metric("Прошли этап 1d", len(passed_symbols))
    
    with col3:
        st.metric("Кандидаты BUY", len(buy_candidates))
    
    with col4:
        st.metric("Кандидаты SELL", len(sell_candidates))
    
    # Показываем топ кандидатов
    if top_candidates:
        st.subheader("🏆 Топ кандидатов по уверенности")
        
        # Создаем DataFrame для отображения
        candidates_data = []
        for result in top_candidates:
            candidates_data.append({
                'Символ': result.symbol,
                'Сигнал': result.signal,
                'Уверенность': f"{result.confidence:.1%}",
                'Ансамбль': result.ensemble_signal,
                'Цена': result.price_signal,
                'Время': result.timestamp.strftime('%H:%M:%S')
            })
        
        df = pd.DataFrame(candidates_data)
        st.dataframe(df, use_container_width=True)
        
        # Кнопки для выбора кандидатов
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🎯 Выбрать топ-10"):
                top_10_symbols = [r.symbol for r in top_candidates[:10]]
                st.session_state.selected_candidates = top_10_symbols
                st.success(f"Выбрано {len(top_10_symbols)} топ кандидатов")
        
        with col2:
            if st.button("📈 Выбрать BUY сигналы"):
                buy_symbols = [r.symbol for r in buy_candidates]
                st.session_state.selected_candidates = buy_symbols
                st.success(f"Выбрано {len(buy_symbols)} BUY сигналов")
        
        with col3:
            if st.button("📉 Выбрать SELL сигналы"):
                sell_symbols = [r.symbol for r in sell_candidates]
                st.session_state.selected_candidates = sell_symbols
                st.success(f"Выбрано {len(sell_symbols)} SELL сигналов")
        
        # Показываем выбранных кандидатов
        if 'selected_candidates' in st.session_state:
            selected = st.session_state.selected_candidates
            st.subheader(f"🎯 Выбранные кандидаты ({len(selected)})")
            
            # Создаем чекбоксы для каждого кандидата
            selected_symbols = []
            for symbol in selected:
                if symbol in stage1d_results:
                    result = stage1d_results[symbol]
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        if st.checkbox(f"{symbol}", key=f"candidate_{symbol}"):
                            selected_symbols.append(symbol)
                    
                    with col2:
                        st.write(f"**{result.signal}** | Уверенность: {result.confidence:.1%}")
                    
                    with col3:
                        st.write(f"Ансамбль: {result.ensemble_signal}")
            
            # Кнопка запуска анализа
            if selected_symbols and st.button("🚀 Запустить каскадный анализ", type="primary"):
                st.info(f"Запуск анализа для {len(selected_symbols)} кандидатов...")
                
                with st.spinner("Выполняется каскадный анализ..."):
                    try:
                        # Запускаем анализ предварительно отфильтрованных символов синхронно
                        import asyncio
                        
                        # Создаем новый event loop для этой операции
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            results = loop.run_until_complete(
                                enhanced_analyzer.analyze_prefiltered_symbols(selected_symbols)
                            )
                            st.session_state.cascade_results = results
                            
                            # Отправляем уведомления
                            for result in results:
                                if result.final_signal:
                                    loop.run_until_complete(
                                        cascade_notifications.notify_cascade_signal(result)
                                    )
                        
                        finally:
                            loop.close()
                        
                        st.success(f"✅ Анализ завершен! Обработано {len(results)} символов")
                        
                        # Показываем результаты
                        successful_results = [r for r in results if r.final_signal is not None]
                        if successful_results:
                            st.subheader("🎯 Успешные сигналы")
                            
                            results_data = []
                            for result in successful_results:
                                results_data.append({
                                    'Символ': result.symbol,
                                    'Сигнал': result.final_signal,
                                    'Уверенность': f"{result.confidence:.1%}",
                                    'Цена входа': f"{result.entry_price:.2f} ₽",
                                    'Stop Loss': f"{result.stop_loss:.2f} ₽",
                                    'Take Profit': f"{result.take_profit:.2f} ₽",
                                    'R/R': f"{result.risk_reward:.1f}",
                                    'Автоторговля': "Да" if result.auto_trade_enabled else "Нет"
                                })
                            
                            results_df = pd.DataFrame(results_data)
                            st.dataframe(results_df, use_container_width=True)
                        else:
                            st.warning("Нет успешных сигналов")
                        
                    except Exception as e:
                        st.error(f"Ошибка анализа: {e}")
            
            else:
                st.info("Выберите кандидатов для анализа")
    
    else:
        st.warning("Нет кандидатов, прошедших этап 1d")

with tab2:
    st.header("📊 Статистика анализа")
    
    if 'stage1d_results' in st.session_state:
        stage1d_results = st.session_state.stage1d_results
        
        # Создаем статистику
        total = len(stage1d_results)
        passed = len(enhanced_analyzer.get_passed_symbols(stage1d_results))
        buy_count = len(enhanced_analyzer.get_buy_candidates(stage1d_results))
        sell_count = len(enhanced_analyzer.get_sell_candidates(stage1d_results))
        
        # График распределения сигналов
        import matplotlib.pyplot as plt
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # График 1: Распределение сигналов
        signals = ['BUY', 'SELL', 'HOLD']
        counts = [
            len([r for r in stage1d_results.values() if r.signal == 'BUY']),
            len([r for r in stage1d_results.values() if r.signal == 'SELL']),
            len([r for r in stage1d_results.values() if r.signal == 'HOLD'])
        ]
        
        ax1.pie(counts, labels=signals, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Распределение сигналов')
        
        # График 2: Уверенность
        confidences = [r.confidence for r in stage1d_results.values()]
        ax2.hist(confidences, bins=20, alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Уверенность')
        ax2.set_ylabel('Количество символов')
        ax2.set_title('Распределение уверенности')
        
        st.pyplot(fig)
        
        # Детальная статистика
        st.subheader("📈 Детальная статистика")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Всего символов", total)
            st.metric("Прошли этап 1d", passed, f"{passed/total*100:.1f}%" if total > 0 else "0%")
        
        with col2:
            st.metric("BUY сигналы", buy_count)
            st.metric("SELL сигналы", sell_count)
    
    else:
        st.info("Запустите предварительную фильтрацию для получения статистики")

with tab3:
    st.header("⚙️ Настройки")
    
    # Настройки фильтрации
    st.subheader("🎯 Настройки фильтрации")
    
    col1, col2 = st.columns(2)
    
    with col1:
        min_confidence = st.slider(
            "Минимальная уверенность для этапа 1d",
            min_value=0.5,
            max_value=0.9,
            value=0.6,
            step=0.1,
            help="Минимальная уверенность ML сигналов для прохождения этапа 1d"
        )
    
    with col2:
        max_candidates = st.slider(
            "Максимальное количество кандидатов",
            min_value=5,
            max_value=50,
            value=20,
            step=5,
            help="Максимальное количество кандидатов для отображения"
        )
    
    # Настройки кэша
    st.subheader("💾 Настройки кэша")
    
    cache_hours = st.slider(
        "Время жизни кэша (часы)",
        min_value=1,
        max_value=24,
        value=1,
        step=1,
        help="Время жизни кэша результатов этапа 1d"
    )
    
    if st.button("🔄 Применить настройки"):
        st.success("Настройки применены!")
        # Здесь можно обновить конфигурацию анализатора
    
    # Статистика кэша
    if 'stage1d_results' in st.session_state:
        st.subheader("📊 Статистика кэша")
        cache_stats = enhanced_analyzer.get_cache_stats()
        st.json(cache_stats)
