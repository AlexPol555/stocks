from core.bootstrap import setup_environment

setup_environment()

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core import database, ui
from core.analytics.auto_trader import AutoTrader
from core.analytics.signal_filters import SignalFilter, FilterConfig
from core.analytics.advanced_risk import AdvancedRiskManager, RiskProfile
from core.analyzer import StockAnalyzer
from core.utils import read_api_key
from core.utils_db import get_db_connection, ensure_db_connection

ui.page_header("Автоматическая торговля", "Управление автоматическими торговыми стратегиями", icon="🤖")

# Initialize session state
if 'auto_trader' not in st.session_state:
    st.session_state.auto_trader = None
if 'trading_session' not in st.session_state:
    st.session_state.trading_session = None
if 'risk_manager' not in st.session_state:
    st.session_state.risk_manager = None

# Get database connection
ensure_db_connection()
conn = get_db_connection()

# Ensure auto trading tables exist
database.create_tables(conn)
database.ensure_auto_trading_settings(conn)

# Get current settings
settings = database.get_auto_trading_settings(conn)

# Sidebar controls
st.sidebar.markdown("### Настройки автоматической торговли")

# Auto trading enable/disable
enabled = st.sidebar.checkbox("Включить автоматическую торговлю", value=settings.get('enabled', False))

if enabled != settings.get('enabled', False):
    database.update_auto_trading_settings(get_db_connection(), {'enabled': enabled})
    st.rerun()

if enabled:
    st.sidebar.success("✅ Автоматическая торговля включена")
else:
    st.sidebar.warning("⚠️ Автоматическая торговля отключена")

# Risk management settings
st.sidebar.markdown("#### Управление рисками")
max_position_size = st.sidebar.number_input(
    "Максимальный размер позиции (руб.)", 
    min_value=1000.0, 
    max_value=1000000.0, 
    value=float(settings.get('max_position_size', 10000.0)),
    step=1000.0
)

max_daily_orders = st.sidebar.number_input(
    "Максимум ордеров в день", 
    min_value=1, 
    max_value=100, 
    value=int(settings.get('max_daily_orders', 10))
)

min_signal_strength = st.sidebar.slider(
    "Минимальная сила сигнала", 
    min_value=0.1, 
    max_value=1.0, 
    value=float(settings.get('min_signal_strength', 0.6)),
    step=0.05
)

risk_per_trade = st.sidebar.slider(
    "Риск на сделку (%)", 
    min_value=0.1, 
    max_value=10.0, 
    value=float(settings.get('risk_per_trade', 0.02)) * 100,
    step=0.1
) / 100

# Update settings if changed
new_settings = {
    'max_position_size': max_position_size,
    'max_daily_orders': max_daily_orders,
    'min_signal_strength': min_signal_strength,
    'risk_per_trade': risk_per_trade
}

if new_settings != {k: settings.get(k) for k in new_settings.keys()}:
    database.update_auto_trading_settings(get_db_connection(), new_settings)
    st.rerun()

# Main content
if enabled:
    # Initialize components if not already done
    if st.session_state.auto_trader is None:
        try:
            api_key = read_api_key()
            analyzer = StockAnalyzer(api_key, db_conn=get_db_connection())
            
            # Create signal filter
            filter_config = FilterConfig(
                min_signal_strength=min_signal_strength,
                min_volume_ratio=1.2,
                max_volatility_percentile=0.8
            )
            signal_filter = SignalFilter(filter_config)
            
            # Create auto trader
            st.session_state.auto_trader = AutoTrader(analyzer, get_db_connection(), signal_filter)
            
            # Create risk manager
            risk_profile = RiskProfile(
                max_position_size=max_position_size,
                max_portfolio_risk=0.05,
                max_daily_loss=0.02,
                max_positions=10
            )
            st.session_state.risk_manager = AdvancedRiskManager(risk_profile)
            
        except Exception as e:
            st.error(f"Ошибка инициализации: {e}")
            st.stop()
    
    # Trading controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Начать торговую сессию", type="primary"):
            if st.session_state.trading_session is None:
                st.session_state.trading_session = st.session_state.auto_trader.start_trading_session()
                st.success("Торговая сессия начата!")
                st.rerun()
            else:
                st.warning("Торговая сессия уже активна")
    
    with col2:
        if st.button("⏹️ Остановить сессию"):
            if st.session_state.trading_session is not None:
                final_stats = st.session_state.auto_trader.stop_trading_session()
                st.session_state.trading_session = None
                st.success("Торговая сессия остановлена!")
                st.json(final_stats)
                st.rerun()
            else:
                st.warning("Нет активной торговой сессии")
    
    with col3:
        if st.button("🔄 Обновить данные"):
            st.rerun()
    
    # Current session info
    if st.session_state.trading_session:
        st.markdown("### 📊 Текущая сессия")
        
        session_stats = st.session_state.auto_trader.get_trading_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("ID сессии", session_stats.get('session_id', 'N/A'))
        with col2:
            st.metric("Ордеров сегодня", session_stats.get('daily_orders', 0))
        with col3:
            st.metric("Всего сделок", session_stats.get('total_trades', 0))
        with col4:
            st.metric("P&L", f"{session_stats.get('total_pnl', 0):.2f} ₽")
        
        # Execute pending orders
        if st.button("⚡ Выполнить ожидающие ордера"):
            with st.spinner("Выполнение ордеров..."):
                results = st.session_state.auto_trader.execute_pending_orders()
                
                if results:
                    st.success(f"Обработано {len(results)} ордеров")
                    
                    # Show results
                    results_df = pd.DataFrame(results)
                    st.dataframe(results_df, use_container_width=True)
                else:
                    st.info("Нет ожидающих ордеров")
    
    # Signal processing
    st.markdown("### 📈 Обработка сигналов")
    
    # Get available tickers
    source = database.mergeMetrDaily(get_db_connection())
    if not source.empty:
        tickers = sorted(source["contract_code"].dropna().unique())
        selected_ticker = st.selectbox("Выберите тикер для обработки", options=tickers)
        
        # Add button to calculate technical indicators first
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🧮 Рассчитать индикаторы"):
                with st.spinner("Расчет технических индикаторов..."):
                    try:
                        from core.indicators import calculate_technical_indicators
                        
                        ticker_data = source[source["contract_code"] == selected_ticker].copy()
                        ticker_data["date"] = pd.to_datetime(ticker_data["date"], errors="coerce")
                        ticker_data = ticker_data.sort_values("date")
                        
                        calculated_data = calculate_technical_indicators(ticker_data, contract_code=selected_ticker)
                        st.success(f"Технические индикаторы рассчитаны для {selected_ticker}")
                        
                        # Show calculated data
                        st.dataframe(calculated_data.tail(10), use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"Ошибка расчета индикаторов: {e}")
                        import traceback
                        st.code(traceback.format_exc())
        
        with col2:
            if st.button("🔍 Обработать сигналы"):
                with st.spinner("Обработка сигналов..."):
                    try:
                        # Get data for selected ticker
                        ticker_data = source[source["contract_code"] == selected_ticker].copy()
                        ticker_data["date"] = pd.to_datetime(ticker_data["date"], errors="coerce")
                        ticker_data = ticker_data.sort_values("date")
                        
                        # Ensure we have required columns
                        required_columns = ['open', 'high', 'low', 'close', 'volume', 'date']
                        missing_columns = [col for col in required_columns if col not in ticker_data.columns]
                        
                        if missing_columns:
                            st.error(f"Отсутствуют необходимые колонки: {missing_columns}")
                            st.info("Убедитесь, что данные загружены и обновлены через страницу 'Автообновление'")
                        else:
                            # Process signals
                            signals = st.session_state.auto_trader.process_signals(ticker_data, selected_ticker)
                            
                            if signals:
                                st.success(f"Сгенерировано {len(signals)} сигналов для {selected_ticker}")
                                
                                # Show signals
                                signals_df = pd.DataFrame(signals)
                                st.dataframe(signals_df, use_container_width=True)
                            else:
                                st.info(f"Нет сигналов для {selected_ticker}")
                            
                    except Exception as e:
                        st.error(f"Ошибка обработки сигналов: {e}")
                        import traceback
                        st.code(traceback.format_exc())
    
    # Pending signals
    st.markdown("### ⏳ Ожидающие сигналы")
    
    pending_signals = database.get_pending_signals(get_db_connection(), limit=50)
    if not pending_signals.empty:
        st.dataframe(pending_signals, use_container_width=True)
        
        # Process all pending signals
        if st.button("🔄 Обработать все ожидающие сигналы"):
            with st.spinner("Обработка всех сигналов..."):
                results = st.session_state.auto_trader.execute_pending_orders()
                
                if results:
                    st.success(f"Обработано {len(results)} сигналов")
                else:
                    st.info("Нет сигналов для обработки")
    else:
        st.info("Нет ожидающих сигналов")
    
    # Trade history
    st.markdown("### 📋 История сделок")
    
    trade_history = database.get_trade_history(get_db_connection(), limit=100)
    if not trade_history.empty:
        # Calculate performance metrics
        total_trades = len(trade_history)
        winning_trades = len(trade_history[trade_history['pnl'] > 0])
        losing_trades = len(trade_history[trade_history['pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        total_pnl = trade_history['pnl'].sum()
        avg_trade_pnl = trade_history['pnl'].mean()
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего сделок", total_trades)
        with col2:
            st.metric("Винрейт", f"{win_rate:.1%}")
        with col3:
            st.metric("Общий P&L", f"{total_pnl:.2f} ₽")
        with col4:
            st.metric("Средний P&L", f"{avg_trade_pnl:.2f} ₽")
        
        # Display trade history
        st.dataframe(trade_history, use_container_width=True)
        
        # Performance chart
        if len(trade_history) > 1:
            trade_history['cumulative_pnl'] = trade_history['pnl'].cumsum()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trade_history.index,
                y=trade_history['cumulative_pnl'],
                mode='lines',
                name='Кумулятивный P&L',
                line=dict(color='blue')
            ))
            
            fig.update_layout(
                title="Кумулятивный P&L",
                xaxis_title="Номер сделки",
                yaxis_title="P&L (₽)",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("История сделок пуста")
    
    # Risk management dashboard
    if st.session_state.risk_manager:
        st.markdown("### ⚠️ Управление рисками")
        
        portfolio_summary = st.session_state.risk_manager.get_portfolio_summary()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Стоимость портфеля", f"{portfolio_summary['portfolio_value']:,.0f} ₽")
        with col2:
            st.metric("Текущая просадка", f"{portfolio_summary['current_drawdown']:.1%}")
        with col3:
            st.metric("Дневной P&L", f"{portfolio_summary['daily_pnl']:,.0f} ₽")
        with col4:
            st.metric("Позиций", f"{portfolio_summary['num_positions']}/{portfolio_summary['max_positions']}")
        
        # Active positions
        if portfolio_summary['positions']:
            st.markdown("#### Активные позиции")
            positions_df = pd.DataFrame(portfolio_summary['positions'])
            st.dataframe(positions_df, use_container_width=True)
        else:
            st.info("Нет активных позиций")

else:
    st.info("Включите автоматическую торговлю в боковой панели для начала работы")
    
    # Show current settings
    st.markdown("### ⚙️ Текущие настройки")
    settings_df = pd.DataFrame([settings])
    st.dataframe(settings_df, use_container_width=True)

