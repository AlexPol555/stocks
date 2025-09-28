"""
Страница управления ML моделями и обучением.
Позволяет управлять моделями, просматривать статистику и запускать обучение.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging
import asyncio

# ML imports
try:
    from core.ml.model_manager import ml_model_manager
    from core.ml.storage import ml_storage
    from core.ml.training_scheduler import ml_training_scheduler
    from core.database import get_connection
    ML_AVAILABLE = True
except ImportError as e:
    ML_AVAILABLE = False
    st.error(f"ML modules not available: {e}")

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="ML Management",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 ML Management")
st.write("Управление ML моделями, обучение и мониторинг производительности")

if not ML_AVAILABLE:
    st.error("ML модули недоступны. Установите необходимые зависимости.")
    st.stop()

# Инициализация планировщика
if 'ml_scheduler_started' not in st.session_state:
    try:
        ml_training_scheduler.start_scheduler()
        st.session_state.ml_scheduler_started = True
        st.success("✅ ML Training Scheduler запущен")
    except Exception as e:
        st.warning(f"⚠️ Не удалось запустить планировщик: {e}")

# Сайдбар для управления
st.sidebar.header("🎛️ Управление ML")

# Статус планировщика
scheduler_status = ml_training_scheduler.get_training_status()
st.sidebar.subheader("📊 Статус планировщика")
st.sidebar.metric("Запущен", "Да" if scheduler_status['is_running'] else "Нет")
st.sidebar.metric("Всего обучений", scheduler_status['stats']['total_trainings'])
st.sidebar.metric("Успешных", scheduler_status['stats']['successful_trainings'])
st.sidebar.metric("Неудачных", scheduler_status['stats']['failed_trainings'])

if scheduler_status['stats']['last_training']:
    last_training = datetime.fromisoformat(scheduler_status['stats']['last_training'])
    st.sidebar.metric("Последнее обучение", last_training.strftime("%H:%M:%S"))

# Управление обучением
st.sidebar.subheader("🚀 Обучение моделей")

if st.sidebar.button("🔄 Обучить все модели (1d)", type="primary"):
    with st.spinner("Обучение всех моделей..."):
        try:
            result = ml_training_scheduler.train_all_models_now('1d', 'lstm')
            if result['success']:
                st.success(f"✅ Обучение завершено: {len(result['results']['successful'])} успешно, {len(result['results']['failed'])} неудачно")
            else:
                st.error(f"❌ Ошибка обучения: {result.get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"❌ Ошибка: {e}")

if st.sidebar.button("🧹 Очистить устаревшие модели"):
    with st.spinner("Очистка устаревших моделей..."):
        try:
            cleaned_count = ml_training_scheduler.cleanup_expired_models()
            st.success(f"✅ Очищено {cleaned_count} устаревших элементов")
        except Exception as e:
            st.error(f"❌ Ошибка очистки: {e}")

# Основной контент
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Статус моделей", 
    "📈 История обучения", 
    "🎯 Предсказания", 
    "⚙️ Настройки", 
    "📋 Логи"
])

# === ВКЛАДКА 1: СТАТУС МОДЕЛЕЙ ===
with tab1:
    st.subheader("📊 Статус ML моделей")
    
    # Получаем статус моделей
    try:
        model_status = ml_model_manager.get_model_status()
        
        if 'error' in model_status:
            st.error(f"Ошибка получения статуса: {model_status['error']}")
        else:
            # Общая статистика
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Всего моделей", model_status['total_models'])
            col2.metric("Символов", model_status['total_symbols'])
            col3.metric("Средняя точность", f"{model_status['average_accuracy']:.2%}")
            col4.metric("Активных задач", scheduler_status['active_tasks'])
            
            # Статистика по таймфреймам
            st.subheader("📈 Статистика по таймфреймам")
            
            timeframe_data = []
            for tf, stats in model_status['timeframe_stats'].items():
                timeframe_data.append({
                    'Таймфрейм': tf,
                    'Моделей': stats['total_models'],
                    'Символов': stats['symbols'],
                    'Средняя точность': f"{stats['avg_accuracy']:.2%}",
                    'Последнее обучение': stats['latest_training'] or 'Никогда'
                })
            
            if timeframe_data:
                timeframe_df = pd.DataFrame(timeframe_data)
                st.dataframe(timeframe_df, use_container_width=True)
                
                # График точности по таймфреймам
                if any(stats['avg_accuracy'] > 0 for stats in model_status['timeframe_stats'].values()):
                    fig = go.Figure(data=[
                        go.Bar(
                            x=list(model_status['timeframe_stats'].keys()),
                            y=[stats['avg_accuracy'] for stats in model_status['timeframe_stats'].values()],
                            text=[f"{stats['avg_accuracy']:.1%}" for stats in model_status['timeframe_stats'].values()],
                            textposition='auto',
                        )
                    ])
                    fig.update_layout(
                        title="Средняя точность моделей по таймфреймам",
                        xaxis_title="Таймфрейм",
                        yaxis_title="Точность",
                        yaxis=dict(tickformat='.0%')
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            # Детальная таблица моделей
            if model_status['models']:
                st.subheader("📋 Детальная информация о моделях")
                
                models_df = pd.DataFrame(model_status['models'])
                
                # Фильтры
                col1, col2, col3 = st.columns(3)
                with col1:
                    selected_timeframe = st.selectbox("Фильтр по таймфрейму", ["Все"] + list(models_df['timeframe'].unique()))
                with col2:
                    min_accuracy = st.slider("Минимальная точность", 0.0, 1.0, 0.0, 0.01)
                with col3:
                    show_only_active = st.checkbox("Только активные", value=True)
                
                # Применяем фильтры
                filtered_df = models_df.copy()
                if selected_timeframe != "Все":
                    filtered_df = filtered_df[filtered_df['timeframe'] == selected_timeframe]
                if 'accuracy' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['accuracy'] >= min_accuracy]
                if show_only_active and 'is_active' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['is_active'] == True]
                
                st.dataframe(filtered_df, use_container_width=True)
                
                # Кнопка экспорта
                csv = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Скачать CSV",
                    data=csv,
                    file_name=f"ml_models_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    except Exception as e:
        st.error(f"Ошибка получения статуса моделей: {e}")

# === ВКЛАДКА 2: ИСТОРИЯ ОБУЧЕНИЯ ===
with tab2:
    st.subheader("📈 История обучения моделей")
    
    # Фильтры для истории
    col1, col2, col3 = st.columns(3)
    with col1:
        history_symbol = st.selectbox("Символ", ["Все"] + [f"Symbol_{i}" for i in range(10)])
    with col2:
        history_timeframe = st.selectbox("Таймфрейм", ["Все", "1d", "1h", "1m", "1s"])
    with col3:
        history_limit = st.slider("Количество записей", 10, 200, 50)
    
    # Получаем историю обучения
    try:
        history_df = ml_training_scheduler.get_training_history(
            symbol=history_symbol if history_symbol != "Все" else None,
            timeframe=history_timeframe if history_timeframe != "Все" else None,
            limit=history_limit
        )
        
        if not history_df.empty:
            st.dataframe(history_df, use_container_width=True)
            
            # График времени обучения
            if 'duration_seconds' in history_df.columns:
                fig = go.Figure(data=[
                    go.Scatter(
                        x=history_df['training_start'],
                        y=history_df['duration_seconds'],
                        mode='markers+lines',
                        text=history_df['symbol'],
                        hovertemplate='<b>%{text}</b><br>Время: %{y:.1f}с<br>Дата: %{x}<extra></extra>'
                    )
                ])
                fig.update_layout(
                    title="Время обучения моделей",
                    xaxis_title="Дата обучения",
                    yaxis_title="Время (секунды)"
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("История обучения пуста")
    
    except Exception as e:
        st.error(f"Ошибка получения истории обучения: {e}")

# === ВКЛАДКА 3: ПРЕДСКАЗАНИЯ ===
with tab3:
    st.subheader("🎯 Тестирование предсказаний")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Настройки предсказания
        pred_symbol = st.text_input("Символ", value="SBER")
        pred_timeframe = st.selectbox("Таймфрейм", ["1d", "1h", "1m", "1s"], index=0)
        pred_days = st.slider("Дней вперед", 1, 7, 1)
        use_cache = st.checkbox("Использовать кэш", value=True)
        
        if st.button("🔮 Предсказать цену", type="primary"):
            with st.spinner("Генерация предсказания..."):
                try:
                    result = ml_model_manager.predict_price_movement(
                        pred_symbol, pred_timeframe, pred_days, use_cache
                    )
                    
                    if 'error' in result:
                        st.error(f"Ошибка предсказания: {result['error']}")
                    else:
                        st.success("✅ Предсказание готово!")
                        
                        # Сохраняем результат в session state для отображения
                        st.session_state['last_prediction'] = result
    
    with col2:
        # Отображение результата предсказания
        if 'last_prediction' in st.session_state:
            result = st.session_state['last_prediction']
            
            col_pred1, col_pred2 = st.columns(2)
            with col_pred1:
                st.metric(
                    "Предсказание",
                    f"{result.get('prediction', 0):.4f}",
                    delta=f"{result.get('confidence', 0):.1%} confidence"
                )
            with col_pred2:
                st.metric(
                    "Кэшировано",
                    "Да" if result.get('cached', False) else "Нет",
                    delta=result.get('cache_date', '') if result.get('cached') else None
                )
            
            # Детальная информация
            if 'model_metrics' in result:
                st.subheader("📊 Метрики модели")
                metrics = result['model_metrics']
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("MSE", f"{metrics.get('mse', 0):.6f}")
                col_m2.metric("MAE", f"{metrics.get('mae', 0):.6f}")
                col_m3.metric("RMSE", f"{metrics.get('rmse', 0):.6f}")
    
    # Тестирование настроений
    st.subheader("😊 Анализ настроений")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        sent_symbol = st.text_input("Символ для анализа настроений", value="SBER")
        sent_timeframe = st.selectbox("Таймфрейм настроений", ["1d", "1h", "1m", "1s"], index=0)
        sent_use_cache = st.checkbox("Использовать кэш настроений", value=True)
        
        if st.button("😊 Анализировать настроения", type="primary"):
            with st.spinner("Анализ настроений..."):
                try:
                    sent_result = ml_model_manager.analyze_sentiment(
                        sent_symbol, sent_timeframe, sent_use_cache
                    )
                    
                    if 'error' in sent_result:
                        st.error(f"Ошибка анализа настроений: {sent_result['error']}")
                    else:
                        st.success("✅ Анализ настроений готов!")
                        st.session_state['last_sentiment'] = sent_result
    
    with col2:
        if 'last_sentiment' in st.session_state:
            sent_result = st.session_state['last_sentiment']
            
            col_sent1, col_sent2 = st.columns(2)
            with col_sent1:
                sentiment = sent_result.get('sentiment', 'neutral')
                confidence = sent_result.get('confidence', 0.5)
                
                # Цветовая индикация настроения
                if sentiment == 'positive':
                    st.success(f"😊 Положительное ({confidence:.1%})")
                elif sentiment == 'negative':
                    st.error(f"😞 Отрицательное ({confidence:.1%})")
                else:
                    st.info(f"😐 Нейтральное ({confidence:.1%})")
            
            with col_sent2:
                st.metric(
                    "Новостей проанализировано",
                    sent_result.get('news_count', 0)
                )
            
            # Распределение настроений
            if 'sentiment_distribution' in sent_result:
                st.subheader("📊 Распределение настроений")
                dist = sent_result['sentiment_distribution']
                
                fig = go.Figure(data=[
                    go.Pie(
                        labels=list(dist.keys()),
                        values=list(dist.values()),
                        hole=0.3
                    )
                ])
                fig.update_layout(title="Распределение настроений в новостях")
                st.plotly_chart(fig, use_container_width=True)

# === ВКЛАДКА 4: НАСТРОЙКИ ===
with tab4:
    st.subheader("⚙️ Настройки ML системы")
    
    # Настройки планировщика
    st.subheader("📅 Настройки планировщика")
    
    for timeframe, config in scheduler_status['schedule_configs'].items():
        with st.expander(f"Таймфрейм {timeframe}"):
            col1, col2 = st.columns(2)
            
            with col1:
                enabled = st.checkbox("Включен", value=config['enabled'], key=f"enabled_{timeframe}")
                retrain_interval = st.number_input(
                    "Интервал переобучения (часы)", 
                    min_value=0.1, 
                    max_value=24.0, 
                    value=config['retrain_interval_hours'],
                    key=f"interval_{timeframe}"
                )
            
            with col2:
                batch_size = st.number_input(
                    "Размер батча", 
                    min_value=1, 
                    max_value=20, 
                    value=config['batch_size'],
                    key=f"batch_{timeframe}"
                )
                priority = st.number_input(
                    "Приоритет", 
                    min_value=1, 
                    max_value=10, 
                    value=config['priority'],
                    key=f"priority_{timeframe}"
                )
            
            if st.button(f"💾 Сохранить настройки {timeframe}", key=f"save_{timeframe}"):
                try:
                    ml_training_scheduler.update_schedule_config(timeframe, {
                        'enabled': enabled,
                        'retrain_interval_hours': retrain_interval,
                        'batch_size': int(batch_size),
                        'priority': int(priority)
                    })
                    st.success(f"✅ Настройки для {timeframe} сохранены")
                except Exception as e:
                    st.error(f"❌ Ошибка сохранения настроек: {e}")
    
    # Управление кэшем
    st.subheader("🗄️ Управление кэшем")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Очистить кэш моделей"):
            try:
                cleaned = ml_storage.cleanup_expired_models()
                st.success(f"✅ Очищено {cleaned} устаревших элементов кэша")
            except Exception as e:
                st.error(f"❌ Ошибка очистки кэша: {e}")
    
    with col2:
        if st.button("📊 Статистика кэша"):
            try:
                # Получаем статистику кэша
                models_df = ml_storage.get_active_models()
                st.info(f"Активных моделей в кэше: {len(models_df)}")
                
                if not models_df.empty:
                    st.dataframe(models_df[['symbol', 'model_type', 'timeframe', 'accuracy', 'training_date']], 
                               use_container_width=True)
            except Exception as e:
                st.error(f"❌ Ошибка получения статистики: {e}")

# === ВКЛАДКА 5: ЛОГИ ===
with tab5:
    st.subheader("📋 Логи и мониторинг")
    
    # Статистика обучения
    st.subheader("📈 Статистика обучения")
    
    stats = scheduler_status['stats']
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Всего обучений", stats['total_trainings'])
    col2.metric("Успешных", stats['successful_trainings'])
    col3.metric("Неудачных", stats['failed_trainings'])
    col4.metric("Среднее время", f"{stats['average_training_time']:.1f}с")
    
    # График успешности обучения
    if stats['total_trainings'] > 0:
        success_rate = stats['successful_trainings'] / stats['total_trainings']
        
        fig = go.Figure(data=[
            go.Bar(
                x=['Успешные', 'Неудачные'],
                y=[stats['successful_trainings'], stats['failed_trainings']],
                marker_color=['green', 'red']
            )
        ])
        fig.update_layout(
            title=f"Успешность обучения (общий показатель: {success_rate:.1%})",
            xaxis_title="Результат",
            yaxis_title="Количество"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Последние ошибки
    st.subheader("🚨 Последние ошибки")
    
    try:
        # Получаем последние неудачные обучения
        failed_history = ml_training_scheduler.get_training_history(limit=20)
        failed_df = failed_history[failed_history['training_status'] == 'failed'] if not failed_history.empty else pd.DataFrame()
        
        if not failed_df.empty:
            st.dataframe(failed_df[['symbol', 'model_type', 'timeframe', 'training_start', 'error_message']], 
                        use_container_width=True)
        else:
            st.info("Нет записей об ошибках")
    
    except Exception as e:
        st.error(f"Ошибка получения логов: {e}")
    
    # Кнопка обновления
    if st.button("🔄 Обновить логи"):
        st.rerun()

# Футер
st.markdown("---")
st.caption("🤖 ML Management System - Управление машинным обучением для торговых стратегий")
