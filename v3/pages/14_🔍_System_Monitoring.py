"""System monitoring page for health checks and metrics."""

from pathlib import Path

from core.bootstrap import setup_environment

setup_environment()

import asyncio
import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from core import ui
from core.notifications import notification_manager, notify_signal, notify_error, notify_critical, notify_trade, dashboard_alerts
from core.monitoring import SystemHealthChecker, MetricsCollector

# Load .env file for notifications
def load_env_file():
    """Load environment variables from .env file."""
    from pathlib import Path
    import os
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load .env file
load_env_file()


ui.page_header(
    "Мониторинг системы",
    "Health checks, метрики производительности и состояние компонентов.",
    icon="🔍",
)

# Initialize components
if "health_checker" not in st.session_state:
    st.session_state["health_checker"] = SystemHealthChecker()

if "metrics_collector" not in st.session_state:
    st.session_state["metrics_collector"] = MetricsCollector()

health_checker = st.session_state["health_checker"]
metrics_collector = st.session_state["metrics_collector"]

# Sidebar controls
with st.sidebar:
    st.subheader("Управление мониторингом")
    
    # Health checks
    if st.button("🔍 Запустить Health Checks", use_container_width=True):
        with st.spinner("Выполняются проверки состояния..."):
            results = asyncio.run(health_checker.run_all_checks())
            st.session_state["last_health_check"] = results
            st.success("Health checks завершены!")
    
    # Metrics collection
    if st.button("📊 Собрать метрики", use_container_width=True):
        with st.spinner("Собираются метрики системы..."):
            metrics = asyncio.run(metrics_collector.collect_metrics())
            st.session_state["last_metrics"] = metrics
            st.success("Метрики собраны!")
    
    # Start/stop metrics collection
    if metrics_collector.is_running():
        if st.button("⏹️ Остановить сбор метрик", use_container_width=True):
            asyncio.run(metrics_collector.stop_collection())
            st.success("Сбор метрик остановлен!")
    else:
        if st.button("▶️ Запустить сбор метрик", use_container_width=True):
            asyncio.run(metrics_collector.start_collection(interval=60.0))
            st.success("Сбор метрик запущен!")
    
    # Test notifications
    if st.button("🔔 Тест уведомлений", use_container_width=True):
        with st.spinner("Тестируются каналы уведомлений..."):
            results = asyncio.run(notification_manager.test_all_channels())
            st.session_state["notification_test_results"] = results
            st.success("Тест уведомлений завершен!")

# Main content
tab1, tab2, tab3, tab4 = st.tabs(["Health Checks", "Метрики", "Уведомления", "Статус системы"])

with tab1:
    st.subheader("🔍 Health Checks")
    
    # Display last health check results
    if "last_health_check" in st.session_state:
        results = st.session_state["last_health_check"]
        
        # Overall status
        overall_status = health_checker.get_overall_status()
        status_colors = {
            "healthy": "🟢",
            "warning": "🟡", 
            "critical": "🔴",
            "unknown": "⚪"
        }
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Общий статус", f"{status_colors.get(overall_status, '⚪')} {overall_status.upper()}")
        with col2:
            st.metric("Всего проверок", len(results))
        with col3:
            healthy_count = sum(1 for r in results.values() if r.is_healthy)
            st.metric("Здоровых", f"{healthy_count}/{len(results)}")
        
        # Individual component status
        st.subheader("Статус компонентов")
        
        for component, result in results.items():
            with st.expander(f"{status_colors.get(result.status, '⚪')} {component}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Статус:** {result.status}")
                    st.write(f"**Сообщение:** {result.message}")
                    if result.response_time_ms:
                        st.write(f"**Время ответа:** {result.response_time_ms:.1f}ms")
                
                with col2:
                    st.write(f"**Время:** {result.timestamp.strftime('%H:%M:%S')}")
                    if result.details:
                        st.write("**Детали:**")
                        st.json(result.details)
    else:
        st.info("Нажмите 'Запустить Health Checks' для проверки состояния системы")

with tab2:
    st.subheader("📊 Метрики системы")
    
    # Current metrics
    current_metrics = metrics_collector.get_current_metrics()
    if current_metrics:
        st.subheader("Текущие метрики")
        
        # System metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("CPU", f"{current_metrics.cpu_percent:.1f}%")
        with col2:
            st.metric("Память", f"{current_metrics.memory_percent:.1f}%")
        with col3:
            st.metric("Диск", f"{current_metrics.disk_percent:.1f}%")
        with col4:
            st.metric("Потоки", current_metrics.process_num_threads)
        
        # Application metrics
        st.subheader("Метрики приложения")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Размер БД", f"{current_metrics.database_size / 1024 / 1024:.1f} MB")
        with col2:
            st.metric("Активные сигналы", current_metrics.active_signals)
        with col3:
            st.metric("Сделки сегодня", current_metrics.trades_today)
        with col4:
            st.metric("Память процесса", f"{current_metrics.process_memory_rss / 1024 / 1024:.1f} MB")
        
        # Historical metrics
        st.subheader("Исторические метрики")
        since_time = datetime.now() - timedelta(hours=24)
        history = metrics_collector.get_metrics_history(since=since_time)
        
        if history:
            # Create DataFrame for plotting
            df = pd.DataFrame([m.to_dict() for m in history])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # CPU and Memory chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['cpu_percent'],
                mode='lines',
                name='CPU %',
                line=dict(color='blue')
            ))
            fig.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['memory_percent'],
                mode='lines',
                name='Memory %',
                line=dict(color='red')
            ))
            
            fig.update_layout(
                title="CPU и Memory Usage",
                xaxis_title="Время",
                yaxis_title="Процент",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Disk usage chart
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['disk_percent'],
                mode='lines',
                name='Disk %',
                line=dict(color='green')
            ))
            
            fig2.update_layout(
                title="Disk Usage",
                xaxis_title="Время",
                yaxis_title="Процент",
                height=300
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Metrics summary
        summary = metrics_collector.get_metrics_summary(hours=24)
        if summary and summary.get("data_points", 0) > 0:
            st.subheader("Сводка за 24 часа")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("CPU (среднее)", f"{summary['cpu']['avg']:.1f}%")
                st.metric("CPU (макс)", f"{summary['cpu']['max']:.1f}%")
            with col2:
                st.metric("Memory (среднее)", f"{summary['memory']['avg']:.1f}%")
                st.metric("Memory (макс)", f"{summary['memory']['max']:.1f}%")
            with col3:
                st.metric("Disk (среднее)", f"{summary['disk']['avg']:.1f}%")
                st.metric("Disk (макс)", f"{summary['disk']['max']:.1f}%")
    else:
        st.info("Метрики не собраны. Нажмите 'Собрать метрики' или 'Запустить сбор метрик'")

with tab3:
    st.subheader("🔔 Уведомления")
    
    # Check Telegram status directly
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    telegram_configured = bool(bot_token and chat_id)
    
    # Notification manager status
    status = notification_manager.get_status()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Telegram", "✅ Включен" if telegram_configured else "❌ Отключен")
    with col2:
        st.metric("Health Checker", "✅ Доступен" if status["health_checker_available"] else "❌ Недоступен")
    with col3:
        st.metric("Metrics Collector", "✅ Доступен" if status["metrics_collector_available"] else "❌ Недоступен")
    
    # Test results
    if "notification_test_results" in st.session_state:
        st.subheader("Результаты тестирования")
        results = st.session_state["notification_test_results"]
        
        for channel, success in results.items():
            status_icon = "✅" if success else "❌"
            st.write(f"{status_icon} {channel.capitalize()}: {'Успешно' if success else 'Ошибка'}")
    
    # Send test notification
    st.subheader("Тестовые уведомления")
    
    # Test all 6 notification types
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Тест сигнала (Приоритет 3)"):
            asyncio.run(notify_signal(
                ticker="TEST",
                signal_type="Test Signal",
                price=100.0,
                signal_value=1,
                additional_data={"test": True, "priority": 3}
            ))
            st.success("Тестовый сигнал отправлен!")
        
        if st.button("❌ Тест ошибки (Приоритет 2)"):
            asyncio.run(notify_error(
                error_type="Test Error",
                error_message="Это тестовое сообщение об ошибке",
                component="Test Component",
                additional_data={"test": True, "priority": 2}
            ))
            st.success("Тестовое уведомление об ошибке отправлено!")
        
        if st.button("🚨 Тест критического (Приоритет 4)"):
            asyncio.run(notify_critical(
                critical_type="Test Critical",
                message="Это критическое тестовое уведомление",
                additional_data={"test": True, "priority": 4}
            ))
            st.success("Критическое уведомление отправлено!")
    
    with col2:
        if st.button("💰 Тест сделки (Приоритет 3)"):
            asyncio.run(notify_trade(
                ticker="TEST",
                side="BUY",
                quantity=10,
                price=100.0,
                total_value=1000.0,
                additional_data={"test": True, "priority": 3}
            ))
            st.success("Тестовое уведомление о сделке отправлено!")
        
        if st.button("📈 Тест отчета (Приоритет 1)"):
            from core.notifications import notification_manager
            report_data = {
                "total_signals": 5,
                "trades_executed": 2,
                "profit_loss": 150.50,
                "active_positions": 3
            }
            asyncio.run(notification_manager.send_daily_report(report_data))
            st.success("Тестовый ежедневный отчет отправлен!")
        
        if st.button("🔍 Тест health check (Приоритет 1)"):
            from core.notifications import notification_manager
            asyncio.run(notification_manager.send_health_check_notification(
                component="Test Component",
                status="healthy",
                details={"test": True, "priority": 1}
            ))
            st.success("Тестовый health check отправлен!")
    
    # Test all notifications with delays
    st.subheader("Тест всех уведомлений с задержками")
    
    # Information about Telegram rate limiting
    st.info("""
    **ℹ️ Информация о Telegram Rate Limiting:**
    
    Telegram Bot API имеет ограничения на частоту отправки сообщений:
    - Минимум 1 секунда между сообщениями
    - При быстрой отправке сообщения могут блокироваться
    - Это нормальное поведение, не ошибка системы
    
    **Рекомендации:**
    - Используйте индивидуальные кнопки для надежной отправки
    - При пакетной отправке не все сообщения могут дойти
    - В реальной работе система отправляет уведомления по мере необходимости
    """)
    
    # Telegram status check
    if st.button("🔍 Проверить статус Telegram"):
        from core.notifications import notification_manager
        status = notification_manager.get_status()
        
        st.write("**Статус каналов уведомлений:**")
        for channel, channel_status in status.get("channels", {}).items():
            if channel == "telegram":
                if channel_status.get("enabled", False):
                    st.success(f"✅ Telegram: {channel_status.get('status', 'Неизвестно')}")
                else:
                    st.error(f"❌ Telegram: {channel_status.get('status', 'Отключен')}")
            else:
                status_icon = "✅" if channel_status.get("enabled", False) else "❌"
                st.write(f"{status_icon} {channel.capitalize()}: {channel_status.get('status', 'Неизвестно')}")
        
        # Test single message
        if st.button("📤 Отправить тестовое сообщение"):
            try:
                asyncio.run(notification_manager.send_test_message())
                st.success("Тестовое сообщение отправлено!")
            except Exception as e:
                st.error(f"Ошибка отправки: {e}")
    
    if st.button("🚀 Тест всех 6 типов уведомлений (с задержками)"):
        async def test_all_notifications():
            results = []
            
            # Test signal
            try:
                await notify_signal(
                    ticker="BATCH_TEST",
                    signal_type="Batch Test Signal",
                    price=150.0,
                    signal_value=1,
                    additional_data={"batch_test": True, "order": 1}
                )
                results.append("✅ Сигнал отправлен")
            except Exception as e:
                results.append(f"❌ Сигнал ошибка: {e}")
            
            await asyncio.sleep(5)  # 5 second delay
            
            # Test error
            try:
                await notify_error(
                    error_type="Batch Test Error",
                    error_message="Batch test error message",
                    component="Batch Test Component",
                    additional_data={"batch_test": True, "order": 2}
                )
                results.append("✅ Ошибка отправлена")
            except Exception as e:
                results.append(f"❌ Ошибка ошибка: {e}")
            
            await asyncio.sleep(5)  # 5 second delay
            
            # Test critical
            try:
                await notify_critical(
                    critical_type="Batch Test Critical",
                    message="Batch test critical message",
                    additional_data={"batch_test": True, "order": 3}
                )
                results.append("✅ Критическое отправлено")
            except Exception as e:
                results.append(f"❌ Критическое ошибка: {e}")
            
            await asyncio.sleep(5)  # 5 second delay
            
            # Test trade
            try:
                await notify_trade(
                    ticker="BATCH_TEST",
                    side="SELL",
                    quantity=5,
                    price=150.0,
                    total_value=750.0,
                    additional_data={"batch_test": True, "order": 4}
                )
                results.append("✅ Сделка отправлена")
            except Exception as e:
                results.append(f"❌ Сделка ошибка: {e}")
            
            await asyncio.sleep(5)  # 5 second delay
            
            # Test daily report
            try:
                from core.notifications import notification_manager
                report_data = {
                    "total_signals": 10,
                    "trades_executed": 5,
                    "profit_loss": 250.75,
                    "active_positions": 8
                }
                await notification_manager.send_daily_report(report_data)
                results.append("✅ Отчет отправлен")
            except Exception as e:
                results.append(f"❌ Отчет ошибка: {e}")
            
            await asyncio.sleep(5)  # 5 second delay
            
            # Test health check
            try:
                await notification_manager.send_health_check_notification(
                    component="Batch Test Component",
                    status="healthy",
                    details={"batch_test": True, "order": 6}
                )
                results.append("✅ Health check отправлен")
            except Exception as e:
                results.append(f"❌ Health check ошибка: {e}")
            
            return results
        
        with st.spinner("Отправка всех уведомлений с задержками..."):
            results = asyncio.run(test_all_notifications())
        
        # Show results
        st.success("Тестирование завершено!")
        for result in results:
            st.write(result)
        
        st.info("💡 Если не все уведомления пришли в Telegram, попробуйте тестировать по одному через отдельные кнопки выше.")
    
    # Alternative test with even longer delays
    if st.button("🐌 Тест с большими задержками (10 сек между сообщениями)"):
        async def test_with_long_delays():
            results = []
            
            # Test signal
            try:
                await notify_signal(
                    ticker="SLOW_TEST",
                    signal_type="Slow Test Signal",
                    price=200.0,
                    signal_value=1,
                    additional_data={"slow_test": True, "order": 1}
                )
                results.append("✅ Сигнал отправлен")
            except Exception as e:
                results.append(f"❌ Сигнал ошибка: {e}")
            
            await asyncio.sleep(10)  # 10 second delay
            
            # Test error
            try:
                await notify_error(
                    error_type="Slow Test Error",
                    error_message="Slow test error message",
                    component="Slow Test Component",
                    additional_data={"slow_test": True, "order": 2}
                )
                results.append("✅ Ошибка отправлена")
            except Exception as e:
                results.append(f"❌ Ошибка ошибка: {e}")
            
            await asyncio.sleep(10)  # 10 second delay
            
            # Test critical
            try:
                await notify_critical(
                    critical_type="Slow Test Critical",
                    message="Slow test critical message",
                    additional_data={"slow_test": True, "order": 3}
                )
                results.append("✅ Критическое отправлено")
            except Exception as e:
                results.append(f"❌ Критическое ошибка: {e}")
            
            await asyncio.sleep(10)  # 10 second delay
            
            # Test trade
            try:
                await notify_trade(
                    ticker="SLOW_TEST",
                    side="BUY",
                    quantity=3,
                    price=200.0,
                    total_value=600.0,
                    additional_data={"slow_test": True, "order": 4}
                )
                results.append("✅ Сделка отправлена")
            except Exception as e:
                results.append(f"❌ Сделка ошибка: {e}")
            
            await asyncio.sleep(10)  # 10 second delay
            
            # Test daily report
            try:
                from core.notifications import notification_manager
                report_data = {
                    "total_signals": 15,
                    "trades_executed": 8,
                    "profit_loss": 350.25,
                    "active_positions": 12
                }
                await notification_manager.send_daily_report(report_data)
                results.append("✅ Отчет отправлен")
            except Exception as e:
                results.append(f"❌ Отчет ошибка: {e}")
            
            await asyncio.sleep(10)  # 10 second delay
            
            # Test health check
            try:
                await notification_manager.send_health_check_notification(
                    component="Slow Test Component",
                    status="healthy",
                    details={"slow_test": True, "order": 6}
                )
                results.append("✅ Health check отправлен")
            except Exception as e:
                results.append(f"❌ Health check ошибка: {e}")
            
            return results
        
        with st.spinner("Отправка всех уведомлений с большими задержками (около 1 минуты)..."):
            results = asyncio.run(test_with_long_delays())
        
        # Show results
        st.success("Тестирование с большими задержками завершено!")
        for result in results:
            st.write(result)
        
        st.info("💡 Этот тест занимает около 1 минуты, но должен гарантированно доставить все сообщения в Telegram.")
    
    # Dashboard notifications test
    st.subheader("Dashboard уведомления")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Dashboard сигнал"):
            dashboard_alerts.add_signal_alert(
                ticker="DASHBOARD_TEST",
                signal_type="Dashboard Test Signal",
                price=200.0,
                signal_value=1
            )
            st.success("Dashboard сигнал добавлен!")
    
    with col2:
        if st.button("❌ Dashboard ошибка"):
            dashboard_alerts.add_error_alert(
                error_type="Dashboard Test Error",
                error_message="Тестовая ошибка для dashboard",
                component="Dashboard Test"
            )
            st.success("Dashboard ошибка добавлена!")
    
    with col3:
        if st.button("🚨 Dashboard критическое"):
            dashboard_alerts.add_critical_alert(
                critical_type="Dashboard Critical Test",
                message="Критическое уведомление для dashboard"
            )
            st.success("Dashboard критическое уведомление добавлено!")
    
    # Show current notifications count
    stats = dashboard_alerts.get_notification_stats()
    st.info(f"📊 Всего уведомлений в dashboard: {stats['total']}, непрочитанных: {stats['unread']}")

with tab4:
    st.subheader("📋 Статус системы")
    
    # System information
    st.subheader("Информация о системе")
    
    try:
        import psutil
        import platform
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**ОС:** {platform.system()} {platform.release()}")
            st.write(f"**Python:** {platform.python_version()}")
            st.write(f"**CPU ядер:** {psutil.cpu_count()}")
        
        with col2:
            memory = psutil.virtual_memory()
            st.write(f"**Общая память:** {memory.total / 1024 / 1024 / 1024:.1f} GB")
            st.write(f"**Доступная память:** {memory.available / 1024 / 1024 / 1024:.1f} GB")
            st.write(f"**Использование памяти:** {memory.percent:.1f}%")
        
    except ImportError:
        st.warning("psutil не установлен. Установите: pip install psutil")
    
    # Application status
    st.subheader("Статус приложения")
    
    # Database status
    try:
        from core.database import open_database_connection
        conn = open_database_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daily_data")
        daily_data_count = cursor.fetchone()[0]
        conn.close()
        
        st.success(f"✅ База данных подключена. Записей: {daily_data_count}")
    except Exception as e:
        st.error(f"❌ Ошибка подключения к БД: {e}")
    
    # Notification channels status
    st.subheader("Каналы уведомлений")
    
    if telegram_configured:
        st.success("✅ Telegram настроен")
        st.write(f"Bot Token: {bot_token[:10]}...{bot_token[-10:] if len(bot_token) > 20 else bot_token}")
        st.write(f"Chat ID: {chat_id}")
    else:
        st.warning("⚠️ Telegram не настроен")
        if not bot_token:
            st.write("❌ TELEGRAM_BOT_TOKEN не найден")
        if not chat_id:
            st.write("❌ TELEGRAM_CHAT_ID не найден")
    
    st.success("✅ Dashboard уведомления доступны")
    
    # Metrics collection status
    if metrics_collector.is_running():
        st.success("✅ Сбор метрик активен")
    else:
        st.info("ℹ️ Сбор метрик не запущен")
