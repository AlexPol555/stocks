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
    from core.ml.cascade_cache import cascade_ml_cache
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

# Детальная диагностика session_state при загрузке страницы
print("=" * 80)
print("🔍 [PAGE_START] ДИАГНОСТИКА SESSION_STATE ПРИ ЗАГРУЗКЕ СТРАНИЦЫ")
print("=" * 80)

# Проверяем все ключи в session_state
print(f"🔍 [PAGE_START] Все ключи в session_state: {list(st.session_state.keys())}")
print(f"🔍 [PAGE_START] Размер session_state: {len(st.session_state)}")

# Проверяем конкретные ключи
cascade_analyzer_exists = 'cascade_analyzer' in st.session_state
initial_ml_results_exists = 'initial_ml_results' in st.session_state
initial_ml_symbols_exists = 'initial_ml_symbols' in st.session_state
initial_ml_analysis_done_exists = 'initial_ml_analysis_done' in st.session_state

print(f"🔍 [PAGE_START] cascade_analyzer в session_state: {cascade_analyzer_exists}")
print(f"🔍 [PAGE_START] initial_ml_results в session_state: {initial_ml_results_exists}")
print(f"🔍 [PAGE_START] initial_ml_symbols в session_state: {initial_ml_symbols_exists}")
print(f"🔍 [PAGE_START] initial_ml_analysis_done в session_state: {initial_ml_analysis_done_exists}")

# Если есть данные, показываем их размеры
if initial_ml_results_exists:
    ml_results_size = len(st.session_state.initial_ml_results) if st.session_state.initial_ml_results else 0
    print(f"🔍 [PAGE_START] Размер initial_ml_results: {ml_results_size}")
    if ml_results_size > 0:
        print(f"🔍 [PAGE_START] Тип initial_ml_results: {type(st.session_state.initial_ml_results)}")
        print(f"🔍 [PAGE_START] Первые ключи initial_ml_results: {list(st.session_state.initial_ml_results.keys())[:5] if isinstance(st.session_state.initial_ml_results, dict) else 'Не словарь'}")

if initial_ml_symbols_exists:
    ml_symbols_size = len(st.session_state.initial_ml_symbols) if st.session_state.initial_ml_symbols else 0
    print(f"🔍 [PAGE_START] Размер initial_ml_symbols: {ml_symbols_size}")
    if ml_symbols_size > 0:
        print(f"🔍 [PAGE_START] Первые символы: {st.session_state.initial_ml_symbols[:5]}")

if initial_ml_analysis_done_exists:
    print(f"🔍 [PAGE_START] initial_ml_analysis_done: {st.session_state.initial_ml_analysis_done}")

print("=" * 80)

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
        print("🔧 [PAGE_INIT] Создаем CascadeAnalyzer...")
        print(f"🔧 [PAGE_INIT] Multi analyzer: {type(multi_analyzer)}")
        print(f"🔧 [PAGE_INIT] ML manager: {type(ml_manager)}")
        print(f"🔧 [PAGE_INIT] Demo trading: {type(demo_trading)}")
        
        st.session_state.cascade_analyzer = CascadeAnalyzer(
            multi_analyzer=multi_analyzer,
            ml_manager=ml_manager,
            demo_trading=demo_trading
        )
        print("🔧 [PAGE_INIT] CascadeAnalyzer создан успешно")
        print(f"🔧 [PAGE_INIT] CascadeAnalyzer в session_state: {'cascade_analyzer' in st.session_state}")
        print(f"🔧 [PAGE_INIT] Размер кэша в новом CascadeAnalyzer: {len(st.session_state.cascade_analyzer.initial_ml_cache)}")
        
        # Создаем менеджер уведомлений
        from core.notifications import NotificationManager
        notification_manager = NotificationManager()
        st.session_state.cascade_notifications = CascadeNotificationManager(notification_manager)
        
        st.success("Каскадный анализатор инициализирован")
        
        # Проверяем, нужно ли выполнять предварительный ML анализ
        print("=" * 60)
        print("🔍 [PAGE_INIT] ПРОВЕРКА НЕОБХОДИМОСТИ ML АНАЛИЗА")
        print("=" * 60)
        
        # Детальная проверка каждого условия
        has_ml_results_key = 'initial_ml_results' in st.session_state
        has_ml_results_value = st.session_state.get('initial_ml_results') is not None
        has_ml_results_length = len(st.session_state.get('initial_ml_results', [])) > 0 if has_ml_results_value else False
        
        has_ml_symbols_key = 'initial_ml_symbols' in st.session_state
        has_ml_symbols_value = st.session_state.get('initial_ml_symbols') is not None
        has_ml_symbols_length = len(st.session_state.get('initial_ml_symbols', [])) > 0 if has_ml_symbols_value else False
        
        print(f"🔍 [PAGE_INIT] initial_ml_results:")
        print(f"  - Ключ существует: {has_ml_results_key}")
        print(f"  - Значение не None: {has_ml_results_value}")
        print(f"  - Длина > 0: {has_ml_results_length}")
        if has_ml_results_value:
            print(f"  - Размер: {len(st.session_state.initial_ml_results)}")
            print(f"  - Тип: {type(st.session_state.initial_ml_results)}")
        
        print(f"🔍 [PAGE_INIT] initial_ml_symbols:")
        print(f"  - Ключ существует: {has_ml_symbols_key}")
        print(f"  - Значение не None: {has_ml_symbols_value}")
        print(f"  - Длина > 0: {has_ml_symbols_length}")
        if has_ml_symbols_value:
            print(f"  - Размер: {len(st.session_state.initial_ml_symbols)}")
            print(f"  - Тип: {type(st.session_state.initial_ml_symbols)}")
        
        has_cached_results = has_ml_results_key and has_ml_results_value and has_ml_results_length
        has_cached_symbols = has_ml_symbols_key and has_ml_symbols_value and has_ml_symbols_length
        
        print(f"🔍 [PAGE_INIT] ИТОГОВАЯ ПРОВЕРКА:")
        print(f"🔍 [PAGE_INIT] Есть кэшированные результаты: {has_cached_results}")
        print(f"🔍 [PAGE_INIT] Есть кэшированные символы: {has_cached_symbols}")
        print(f"🔍 [PAGE_INIT] initial_ml_analysis_done: {st.session_state.get('initial_ml_analysis_done', False)}")
        print("=" * 60)
        
        # Выполняем ML анализ только если нет кэшированных результатов
        if not has_cached_results or not has_cached_symbols:
            print("🔄 [PAGE_INIT] Запускаем предварительный ML анализ...")
            st.info("🔄 Выполняется предварительный ML анализ всех доступных символов...")
            
            try:
                # Получаем все доступные символы с фильтрацией по денежному объему
                available_symbols = st.session_state.cascade_analyzer.get_available_symbols_with_1d_data(
                    min_volume=10000000, 
                    min_avg_volume=5000000
                )
                
                if available_symbols:
                    print(f"📊 [PAGE_INIT] Найдено {len(available_symbols)} символов для ML анализа")
                    print(f"📋 [PAGE_INIT] Первые 5 символов: {available_symbols[:5]}")
                    
                    # Оцениваем время выполнения
                    time_estimate = st.session_state.cascade_analyzer.estimate_ml_analysis_time(len(available_symbols))
                    st.info(f"⏱️ Ожидаемое время выполнения: {time_estimate['formatted_time']}")
                    print(f"⏱️ [PAGE_INIT] Ожидаемое время: {time_estimate['formatted_time']}")
                    
                    # Запускаем предварительный ML анализ
                    print("🤖 [PAGE_INIT] Запускаем предварительный ML анализ...")
                    initial_ml_results = asyncio.run(
                        st.session_state.cascade_analyzer.perform_initial_ml_analysis(available_symbols)
                    )
                    print(f"🤖 [PAGE_INIT] ML анализ завершен, получено {len(initial_ml_results)} результатов")
                    
                    # Сохраняем результаты в session_state
                    print("💾 [PAGE_INIT] Сохраняем результаты в session_state...")
                    print(f"💾 [PAGE_INIT] Размер initial_ml_results: {len(initial_ml_results)}")
                    print(f"💾 [PAGE_INIT] Размер available_symbols: {len(available_symbols)}")
                    
                    st.session_state.initial_ml_results = initial_ml_results
                    st.session_state.initial_ml_analysis_done = True
                    st.session_state.initial_ml_symbols = available_symbols
                    
                    print("💾 [PAGE_INIT] Результаты сохранены в session_state")
                    print(f"💾 [PAGE_INIT] initial_ml_results в session_state: {len(st.session_state.initial_ml_results)}")
                    print(f"💾 [PAGE_INIT] initial_ml_symbols в session_state: {len(st.session_state.initial_ml_symbols)}")
                    
                    st.success(f"✅ Предварительный ML анализ завершен для {len(initial_ml_results)} символов")
                else:
                    st.warning("⚠️ Не найдено символов с данными 1d, прошедших фильтрацию по объему")
                    st.session_state.initial_ml_analysis_done = True
                    st.session_state.initial_ml_results = []
                    st.session_state.initial_ml_symbols = []
                    
            except Exception as e:
                st.warning(f"⚠️ Ошибка предварительного ML анализа: {e}")
                st.session_state.initial_ml_analysis_done = True
                st.session_state.initial_ml_results = []
                st.session_state.initial_ml_symbols = []
        else:
            print("=" * 60)
            print("✅ [PAGE_INIT] ИСПОЛЬЗУЕМ КЭШИРОВАННЫЕ РЕЗУЛЬТАТЫ")
            print("=" * 60)
            print(f"✅ [PAGE_INIT] Кэшированных результатов: {len(st.session_state.initial_ml_results)}")
            print(f"✅ [PAGE_INIT] Кэшированных символов: {len(st.session_state.initial_ml_symbols)}")
            
            # Проверяем качество кэшированных результатов
            valid_results = 0
            strong_signals = 0
            
            print(f"🔍 [PAGE_INIT] Анализируем качество кэшированных результатов...")
            for symbol, result in st.session_state.initial_ml_results.items():
                if isinstance(result, dict) and 'ml_ensemble_signal' in result and 'ml_price_confidence' in result:
                    valid_results += 1
                    confidence = result.get('ml_price_confidence', 0.0)
                    signal = result.get('ml_ensemble_signal', 'HOLD')
                    
                    if (signal in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL'] and confidence >= 0.5):
                        strong_signals += 1
                        print(f"  🎯 {symbol}: {signal} (уверенность: {confidence:.1%})")
            
            print(f"🔍 [PAGE_INIT] Валидных результатов: {valid_results}")
            print(f"🔍 [PAGE_INIT] Сильных сигналов: {strong_signals}")
            
            # Если все результаты HOLD с уверенностью 0.0%, возможно есть проблема
            if strong_signals == 0 and valid_results > 0:
                print("⚠️ [PAGE_INIT] Все кэшированные результаты HOLD с уверенностью 0.0% - возможна проблема")
                st.warning("⚠️ Кэшированные результаты выглядят некорректно (все HOLD с уверенностью 0.0%). Рекомендуется перезапустить анализ.")
            else:
                st.info(f"✅ Используются кэшированные ML результаты ({len(st.session_state.initial_ml_results)} символов, {strong_signals} сильных сигналов)")
            
            print("=" * 60)
        
    except Exception as e:
        st.error(f"Ошибка инициализации: {e}")
        st.stop()

# Получаем компоненты
cascade_analyzer = st.session_state.cascade_analyzer
notification_manager = st.session_state.cascade_notifications

# Проверяем состояние кэша при каждой загрузке страницы
print("=" * 60)
print("🔍 [PAGE_LOAD] ПРОВЕРКА СОСТОЯНИЯ КЭША ПРИ ЗАГРУЗКЕ СТРАНИЦЫ")
print("=" * 60)
print(f"🔍 [PAGE_LOAD] Размер кэша в CascadeAnalyzer: {len(cascade_analyzer.initial_ml_cache)}")
print(f"🔍 [PAGE_LOAD] initial_ml_results в session_state: {len(st.session_state.get('initial_ml_results', []))}")
print(f"🔍 [PAGE_LOAD] initial_ml_symbols в session_state: {len(st.session_state.get('initial_ml_symbols', []))}")
print(f"🔍 [PAGE_LOAD] initial_ml_analysis_done: {st.session_state.get('initial_ml_analysis_done', False)}")

# Детальная проверка содержимого
if st.session_state.get('initial_ml_results'):
    print(f"🔍 [PAGE_LOAD] Тип initial_ml_results: {type(st.session_state.initial_ml_results)}")
    print(f"🔍 [PAGE_LOAD] Первые ключи: {list(st.session_state.initial_ml_results.keys())[:5] if isinstance(st.session_state.initial_ml_results, dict) else 'Не словарь'}")

if cascade_analyzer.initial_ml_cache:
    print(f"🔍 [PAGE_LOAD] Тип кэша: {type(cascade_analyzer.initial_ml_cache)}")
    print(f"🔍 [PAGE_LOAD] Первые ключи кэша: {list(cascade_analyzer.initial_ml_cache.keys())[:5] if isinstance(cascade_analyzer.initial_ml_cache, dict) else 'Не словарь'}")

print("=" * 60)

# Синхронизируем кэш с session_state если нужно
print("🔄 [PAGE_LOAD] Проверяем необходимость синхронизации...")
print(f"🔄 [PAGE_LOAD] Условие 1 (session_state -> кэш): {bool(st.session_state.get('initial_ml_results') and len(cascade_analyzer.initial_ml_cache) == 0)}")
print(f"🔄 [PAGE_LOAD] Условие 2 (кэш -> session_state): {bool(len(cascade_analyzer.initial_ml_cache) > 0 and not st.session_state.get('initial_ml_results'))}")

if (st.session_state.get('initial_ml_results') and 
    len(cascade_analyzer.initial_ml_cache) == 0):
    print("🔄 [PAGE_LOAD] Синхронизируем кэш с session_state...")
    print(f"🔄 [PAGE_LOAD] Размер session_state перед синхронизацией: {len(st.session_state.initial_ml_results)}")
    cascade_analyzer.initial_ml_cache = st.session_state.initial_ml_results
    print(f"🔄 [PAGE_LOAD] Кэш синхронизирован, размер: {len(cascade_analyzer.initial_ml_cache)}")
elif (len(cascade_analyzer.initial_ml_cache) > 0 and 
      not st.session_state.get('initial_ml_results')):
    print("🔄 [PAGE_LOAD] Синхронизируем session_state с кэшем...")
    print(f"🔄 [PAGE_LOAD] Размер кэша перед синхронизацией: {len(cascade_analyzer.initial_ml_cache)}")
    st.session_state.initial_ml_results = cascade_analyzer.initial_ml_cache
    print(f"🔄 [PAGE_LOAD] session_state синхронизирован, размер: {len(st.session_state.initial_ml_results)}")
else:
    print("✅ [PAGE_LOAD] Синхронизация не требуется")

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
    
    # Настройки фильтрации
    with st.expander("🔧 Настройки фильтрации", expanded=False):
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            min_volume = st.number_input(
                "Минимальный денежный объем за день (RUB)",
                min_value=0,
                value=st.session_state.get('min_volume', 10000000),
                step=1000000,
                help="Минимальный денежный объем торгов за последний день (volume * close)"
            )
            st.session_state.min_volume = min_volume
        
        with col_filter2:
            min_avg_volume = st.number_input(
                "Минимальный средний денежный объем за 30 дней (RUB)",
                min_value=0,
                value=st.session_state.get('min_avg_volume', 5000000),
                step=1000000,
                help="Минимальный средний денежный объем торгов за последние 30 дней (volume * close)"
            )
            st.session_state.min_avg_volume = min_avg_volume
        
        if st.button("🔄 Применить фильтры", type="primary"):
            try:
                # Получаем отфильтрованные символы
                filtered_symbols = cascade_analyzer.get_available_symbols_with_1d_data(
                    min_volume=min_volume,
                    min_avg_volume=min_avg_volume
                )
                
                # Очищаем предыдущие результаты
                if 'initial_ml_results' in st.session_state:
                    del st.session_state.initial_ml_results
                if 'initial_ml_symbols' in st.session_state:
                    del st.session_state.initial_ml_symbols
                if 'initial_ml_analysis_done' in st.session_state:
                    del st.session_state.initial_ml_analysis_done
                
                st.success(f"✅ Фильтрация применена! Найдено {len(filtered_symbols)} символов")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Ошибка применения фильтров: {e}")
    
    # Автоматический анализ всех доступных символов
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Статус анализа")
        
        # Получаем статус анализа
        try:
            current_min_volume = st.session_state.get('min_volume', 10000000)
            current_min_avg_volume = st.session_state.get('min_avg_volume', 5000000)
            analysis_status = asyncio.run(cascade_analyzer.get_analysis_status(current_min_volume, current_min_avg_volume))
            
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
            
            # Показываем информацию о фильтрации
            current_min_volume = st.session_state.get('min_volume', 10000000)
            current_min_avg_volume = st.session_state.get('min_avg_volume', 5000000)
            
            st.info(f"🔧 Текущие фильтры: денежный объем ≥ {current_min_volume:,.0f} RUB, средний денежный объем ≥ {current_min_avg_volume:,.0f} RUB")
            
            # Показываем информацию о сохраненных ML результатах
            if 'initial_ml_results' in st.session_state and st.session_state.initial_ml_results:
                st.info(f"💾 Сохранено {len(st.session_state.initial_ml_results)} результатов предварительного ML анализа")
                
                # Показываем краткую статистику сохраненных результатов
                strong_signals = [r for r in st.session_state.initial_ml_results if r.get('confidence', 0) >= 0.5]
                if strong_signals:
                    st.success(f"🎯 Из них {len(strong_signals)} символов с сильными сигналами (уверенность ≥ 50%)")
                    
                    # Показываем топ-5 сильных сигналов
                    with st.expander("🔍 Топ сильных ML сигналов", expanded=False):
                        for i, signal in enumerate(strong_signals[:5]):
                            symbol = signal.get('symbol', 'Unknown')
                            confidence = signal.get('confidence', 0)
                            signal_type = signal.get('signal', 'Unknown')
                            st.write(f"{i+1}. **{symbol}**: {signal_type} (уверенность: {confidence:.1%})")
            else:
                st.info("💾 Результаты предварительного ML анализа не найдены")
            
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
        
        # Кнопка для повторного использования сохраненных ML результатов
        if 'initial_ml_results' in st.session_state and st.session_state.initial_ml_results:
            if st.button("🔄 Использовать сохраненные ML результаты", use_container_width=True):
                print("🔄 [CASCADE] Используем сохраненные ML результаты")
                
                with st.spinner("Используем сохраненные ML результаты для каскадного анализа..."):
                    try:
                        # Используем сохраненные ML результаты
                        saved_results = st.session_state.initial_ml_results
                        saved_symbols = st.session_state.initial_ml_symbols
                        
                        print(f"📊 [CASCADE] Используем {len(saved_results)} сохраненных ML результатов")
                        
                        # Запускаем каскадный анализ с сохраненными результатами
                        results = asyncio.run(
                            cascade_analyzer.analyze_with_saved_ml_results(saved_results, saved_symbols)
                        )
                        
                        # Сохраняем результаты
                        st.session_state.cascade_results = results
                        
                        # Анализируем результаты
                        successful_results = cascade_analyzer.get_successful_signals(results)
                        rejected_results = cascade_analyzer.get_rejected_signals(results)
                        
                        # Отправляем уведомления
                        notification_count = 0
                        for result in results:
                            if result.final_signal:
                                try:
                                    asyncio.run(notification_manager.notify_cascade_signal(result))
                                    notification_count += 1
                                except Exception as e:
                                    print(f"⚠️ [CASCADE] Ошибка отправки уведомления для {result.symbol}: {e}")
                        
                        st.success(f"✅ Каскадный анализ завершен с использованием сохраненных ML результатов! Обработано {len(results)} символов")
                        st.rerun()
                        
                    except Exception as e:
                        print(f"❌ [CASCADE] Ошибка использования сохраненных результатов: {e}")
                        st.error(f"❌ Ошибка: {e}")
        
        # Кнопка запуска полного анализа
        if st.button("🚀 Запустить полный анализ", type="primary", use_container_width=True):
            print("🚀 [CASCADE] Кнопка 'Запустить анализ' нажата")
            
            # Получаем текущие настройки фильтрации
            min_volume = st.session_state.get('min_volume', 1000000)
            min_avg_volume = st.session_state.get('min_avg_volume', 500000)
            
            # Оцениваем время выполнения
            available_symbols = cascade_analyzer.get_available_symbols_with_1d_data(
                min_volume=min_volume, 
                min_avg_volume=min_avg_volume
            )
            time_estimate = cascade_analyzer.estimate_ml_analysis_time(len(available_symbols))
            
            with st.spinner(f"Выполняется каскадный анализ {len(available_symbols)} символов (ожидаемое время: {time_estimate['formatted_time']})..."):
                try:
                    print("📊 [CASCADE] Начинаем каскадный анализ...")
                    print(f"📊 [CASCADE] Фильтрация: min_volume={min_volume}, min_avg_volume={min_avg_volume}")
                    print(f"⏱️ [CASCADE] Ожидаемое время: {time_estimate['formatted_time']}")
                    
                    # Получаем статус перед анализом
                    print("🔍 [CASCADE] Получаем статус анализа...")
                    pre_status = asyncio.run(cascade_analyzer.get_analysis_status())
                    print(f"📈 [CASCADE] Статус до анализа: {pre_status}")
                    
                    # Запускаем автоматический анализ всех символов
                    print("⚡ [CASCADE] Запускаем analyze_all_available_symbols()...")
                    results = asyncio.run(cascade_analyzer.analyze_all_available_symbols(
                        min_volume=min_volume,
                        min_avg_volume=min_avg_volume,
                        use_db_cache=True
                    ))
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
        
        # Кнопка инспекции кэша
        if st.button("🔍 Инспекция кэша", use_container_width=True):
            try:
                cache_info = cascade_analyzer.inspect_ml_cache()
                st.success(f"✅ Инспекция кэша завершена! Размер: {cache_info['cache_size']} элементов")
                
                # Показываем детали кэша
                if cache_info['cache_size'] > 0:
                    st.write("**Содержимое кэша:**")
                    for symbol, details in list(cache_info['cache_details'].items())[:10]:  # Показываем первые 10
                        st.write(f"- **{symbol}**: {details['ensemble_signal']} (уверенность: {details['confidence']:.1%})")
                    
                    if cache_info['cache_size'] > 10:
                        st.write(f"... и еще {cache_info['cache_size'] - 10} символов")
                    
                    # Показываем сильные сигналы
                    if cache_info['strong_signals']:
                        st.write("**Сильные сигналы:**")
                        for signal in cache_info['strong_signals'][:5]:  # Показываем первые 5
                            st.write(f"- **{signal['symbol']}**: {signal['signal']} (уверенность: {signal['confidence']:.1%})")
                else:
                    st.info("Кэш пустой")
                    
            except Exception as e:
                st.error(f"❌ Ошибка инспекции кэша: {e}")
        
        # Кнопка проверки целостности кэша
        if st.button("🔧 Проверка целостности кэша", use_container_width=True):
            try:
                integrity_info = cascade_analyzer.verify_cache_integrity()
                
                if integrity_info['is_valid']:
                    st.success(f"✅ Кэш валиден! Размер: {integrity_info['cache_size']}, валидных записей: {integrity_info['valid_entries']}")
                else:
                    st.error(f"❌ Кэш невалиден! Проблем: {len(integrity_info['issues'])}")
                
                # Показываем детали
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Статистика:**")
                    st.write(f"- Размер кэша: {integrity_info['cache_size']}")
                    st.write(f"- Валидных записей: {integrity_info['valid_entries']}")
                    st.write(f"- Невалидных записей: {integrity_info['invalid_entries']}")
                    st.write(f"- Записей с ошибками: {integrity_info['error_entries']}")
                
                with col2:
                    st.write("**Рекомендации:**")
                    for rec in integrity_info['recommendations']:
                        st.write(f"- {rec}")
                
                # Показываем проблемы
                if integrity_info['issues']:
                    with st.expander("⚠️ Проблемы в кэше", expanded=False):
                        for issue in integrity_info['issues'][:10]:  # Показываем первые 10
                            st.write(f"- {issue}")
                        if len(integrity_info['issues']) > 10:
                            st.write(f"... и еще {len(integrity_info['issues']) - 10} проблем")
                    
            except Exception as e:
                st.error(f"❌ Ошибка проверки целостности: {e}")
        
        # Кнопка принудительного перезапуска ML анализа
        if st.button("🔄 Перезапустить ML анализ", use_container_width=True):
            try:
                print("🔄 [FORCE_RESTART] Принудительный перезапуск ML анализа...")
                
                # Очищаем кэш и session_state
                if 'initial_ml_results' in st.session_state:
                    del st.session_state.initial_ml_results
                if 'initial_ml_symbols' in st.session_state:
                    del st.session_state.initial_ml_symbols
                if 'initial_ml_analysis_done' in st.session_state:
                    del st.session_state.initial_ml_analysis_done
                
                # Очищаем кэш в CascadeAnalyzer
                cascade_analyzer.initial_ml_cache = {}
                
                print("🔄 [FORCE_RESTART] Кэш очищен, перезагружаем страницу...")
                st.success("ML анализ будет перезапущен при следующей загрузке страницы")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Ошибка перезапуска: {e}")
        
        # Кнопка очистки ML результатов
        if 'initial_ml_results' in st.session_state and st.session_state.initial_ml_results:
            if st.button("🗑️ Очистить ML результаты", use_container_width=True):
                del st.session_state.initial_ml_results
                del st.session_state.initial_ml_symbols
                del st.session_state.initial_ml_analysis_done
                st.success("ML результаты очищены")
                st.rerun()
        
        # Управление БД кэшем
        st.subheader("🗄️ Управление БД кэшем")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Кнопка статуса БД кэша
            if st.button("📊 Статус БД кэша", use_container_width=True):
                try:
                    status = cascade_ml_cache.get_cache_status()
                    st.success("✅ Статус БД кэша получен")
                    
                    col1_status, col2_status = st.columns(2)
                    with col1_status:
                        st.write("**Общая статистика:**")
                        st.write(f"- Всего записей: {status.get('total_entries', 0)}")
                        st.write(f"- Валидных записей: {status.get('valid_entries', 0)}")
                        st.write(f"- Устаревших записей: {status.get('expired_entries', 0)}")
                        st.write(f"- Время жизни кэша: {status.get('cache_duration_hours', 0)} часов")
                    
                    with col2_status:
                        st.write("**Последняя запись:**")
                        if status.get('last_entry'):
                            last = status['last_entry']
                            st.write(f"- Ключ: {last.get('key', 'N/A')[:50]}...")
                            st.write(f"- Создана: {last.get('created_at', 'N/A')}")
                            st.write(f"- Истекает: {last.get('expires_at', 'N/A')}")
                        else:
                            st.write("Нет записей")
                            
                except Exception as e:
                    st.error(f"❌ Ошибка получения статуса БД кэша: {e}")
            
            # Кнопка инспекции БД кэша
            if st.button("🔍 Инспекция БД кэша", use_container_width=True):
                try:
                    cache_info = cascade_ml_cache.inspect_cache()
                    st.success(f"✅ Инспекция БД кэша завершена! Найдено {cache_info.get('total_entries', 0)} записей")
                    
                    if cache_info.get('entries'):
                        st.write("**Записи в БД кэше:**")
                        for entry in cache_info['entries'][:5]:  # Показываем первые 5
                            st.write(f"- **{entry['key'][:30]}...**: {entry['symbols_count']} символов, создана {entry['created_at']}")
                            st.write(f"  - Истекла: {'Да' if entry['is_expired'] else 'Нет'}")
                            st.write(f"  - Параметры: min_volume={entry['min_volume']}, min_avg_volume={entry['min_avg_volume']}")
                            st.write("---")
                        
                        if len(cache_info['entries']) > 5:
                            st.write(f"... и еще {len(cache_info['entries']) - 5} записей")
                    else:
                        st.write("БД кэш пуст")
                        
                except Exception as e:
                    st.error(f"❌ Ошибка инспекции БД кэша: {e}")
        
        with col2:
            # Кнопка очистки БД кэша
            if st.button("🗑️ Очистить БД кэш", use_container_width=True):
                try:
                    deleted_count = cascade_ml_cache.clear_cache()
                    st.success(f"✅ БД кэш очищен! Удалено {deleted_count} записей")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка очистки БД кэша: {e}")
            
            # Кнопка очистки устаревшего БД кэша
            if st.button("🧹 Очистить устаревший БД кэш", use_container_width=True):
                try:
                    deleted_count = cascade_ml_cache.clear_expired_cache()
                    st.success(f"✅ Устаревший БД кэш очищен! Удалено {deleted_count} записей")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка очистки устаревшего БД кэша: {e}")
    
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
