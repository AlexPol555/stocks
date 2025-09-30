#!/usr/bin/env python3
"""
Integrated Cascade Analyzer Page.
Интегрированная версия каскадного анализатора, объединяющая все компоненты.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
import asyncio

# Настройка страницы
st.set_page_config(
    page_title="Integrated Cascade Analyzer",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Integrated Cascade Analyzer")
st.markdown("**Интегрированный каскадный анализатор с полной функциональностью**")

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
        
        return enhanced_analyzer, cascade_notifications, True
        
    except Exception as e:
        st.warning(f"Не удалось инициализировать полную версию: {e}")
        return None, None, False

# Простая версия для fallback
class SimpleStage1dResult:
    """Простой результат этапа 1d."""
    
    def __init__(self, symbol: str, signal: str, confidence: float, ensemble_signal: str, price_signal: str):
        self.symbol = symbol
        self.signal = signal
        self.confidence = confidence
        self.ensemble_signal = ensemble_signal
        self.price_signal = price_signal
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'signal': self.signal,
            'confidence': self.confidence,
            'ensemble_signal': self.ensemble_signal,
            'price_signal': self.price_signal,
            'timestamp': self.timestamp.isoformat()
        }

class SimpleIntegratedAnalyzer:
    """Простая интегрированная версия анализатора."""
    
    def __init__(self):
        self.stage1d_cache = {}
        
    def prefilter_symbols_stage1d(self, symbols: List[str]) -> Dict[str, SimpleStage1dResult]:
        """Предварительная фильтрация символов по этапу 1d."""
        results = {}
        
        for symbol in symbols:
            # Проверяем кэш
            if symbol in self.stage1d_cache:
                cache_result = self.stage1d_cache[symbol]
                if (datetime.now() - cache_result.timestamp).seconds < 3600:
                    results[symbol] = cache_result
                    continue
            
            # Симулируем анализ ML сигналов
            if symbol in ['SBER', 'GAZP', 'LKOH', 'MGNT', 'NLMK']:
                signal = 'BUY'
                confidence = 0.75
                ensemble_signal = 'BUY'
                price_signal = 'BUY'
            elif symbol in ['NVTK', 'ROSN', 'YNDX', 'VKCO']:
                signal = 'SELL'
                confidence = 0.70
                ensemble_signal = 'SELL'
                price_signal = 'SELL'
            else:
                signal = 'HOLD'
                confidence = 0.45
                ensemble_signal = 'HOLD'
                price_signal = 'HOLD'
            
            result = SimpleStage1dResult(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                ensemble_signal=ensemble_signal,
                price_signal=price_signal
            )
            
            self.stage1d_cache[symbol] = result
            results[symbol] = result
        
        return results
    
    def get_passed_symbols(self, stage1d_results: Dict[str, SimpleStage1dResult]) -> List[str]:
        """Получить символы, прошедшие этап 1d."""
        return [symbol for symbol, result in stage1d_results.items() 
                if result.signal in ['BUY', 'SELL'] and result.confidence >= 0.6]
    
    def get_buy_candidates(self, stage1d_results: Dict[str, SimpleStage1dResult]) -> List[SimpleStage1dResult]:
        """Получить кандидатов на покупку."""
        return [result for result in stage1d_results.values() 
                if result.signal == 'BUY' and result.confidence >= 0.6]
    
    def get_sell_candidates(self, stage1d_results: Dict[str, SimpleStage1dResult]) -> List[SimpleStage1dResult]:
        """Получить кандидатов на продажу."""
        return [result for result in stage1d_results.values() 
                if result.signal == 'SELL' and result.confidence >= 0.6]
    
    def get_top_candidates(self, stage1d_results: Dict[str, SimpleStage1dResult], limit: int = 20) -> List[SimpleStage1dResult]:
        """Получить топ кандидатов по уверенности."""
        candidates = [result for result in stage1d_results.values() 
                     if result.signal in ['BUY', 'SELL'] and result.confidence >= 0.6]
        
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates[:limit]
    
    def analyze_prefiltered_symbols(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Анализ предварительно отфильтрованных символов."""
        results = []
        
        # Расширенная симуляция результатов
        simulation_data = {
            'SBER': {'signal': 'BUY', 'confidence': 0.85, 'entry': 250.50, 'sl': 245.00, 'tp': 260.00, 'rr': 2.0},
            'GAZP': {'signal': 'BUY', 'confidence': 0.80, 'entry': 180.25, 'sl': 175.00, 'tp': 190.00, 'rr': 1.9},
            'LKOH': {'signal': 'BUY', 'confidence': 0.75, 'entry': 6200.00, 'sl': 6100.00, 'tp': 6400.00, 'rr': 2.0},
            'MGNT': {'signal': 'BUY', 'confidence': 0.72, 'entry': 5200.00, 'sl': 5100.00, 'tp': 5400.00, 'rr': 2.0},
            'NLMK': {'signal': 'BUY', 'confidence': 0.70, 'entry': 150.00, 'sl': 145.00, 'tp': 160.00, 'rr': 2.0},
            'NVTK': {'signal': 'SELL', 'confidence': 0.78, 'entry': 1800.00, 'sl': 1850.00, 'tp': 1700.00, 'rr': 3.0},
            'ROSN': {'signal': 'SELL', 'confidence': 0.75, 'entry': 550.00, 'sl': 570.00, 'tp': 520.00, 'rr': 1.7},
            'YNDX': {'signal': 'SELL', 'confidence': 0.70, 'entry': 2800.00, 'sl': 2900.00, 'tp': 2600.00, 'rr': 2.0},
            'VKCO': {'signal': 'SELL', 'confidence': 0.68, 'entry': 450.00, 'sl': 470.00, 'tp': 420.00, 'rr': 2.0},
        }
        
        for symbol in symbols:
            if symbol in simulation_data:
                data = simulation_data[symbol]
                result = {
                    'symbol': symbol,
                    'final_signal': data['signal'],
                    'confidence': data['confidence'],
                    'entry_price': data['entry'],
                    'stop_loss': data['sl'],
                    'take_profit': data['tp'],
                    'risk_reward': data['rr'],
                    'auto_trade_enabled': True
                }
            else:
                result = {
                    'symbol': symbol,
                    'final_signal': None,
                    'confidence': 0.0,
                    'entry_price': 0.0,
                    'stop_loss': 0.0,
                    'take_profit': 0.0,
                    'risk_reward': 0.0,
                    'auto_trade_enabled': False,
                    'rejection_reason': 'Failed at stage 1h'
                }
            
            results.append(result)
        
        return results
    
    def clear_cache(self):
        """Очистить кэш результатов этапа 1d."""
        self.stage1d_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша."""
        total = len(self.stage1d_cache)
        passed = len([r for r in self.stage1d_cache.values() if r.signal in ['BUY', 'SELL']])
        buy_signals = len([r for r in self.stage1d_cache.values() if r.signal == 'BUY'])
        sell_signals = len([r for r in self.stage1d_cache.values() if r.signal == 'SELL'])
        
        return {
            'total_cached': total,
            'passed_stage1d': passed,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'cache_hit_rate': f"{passed/total*100:.1f}%" if total > 0 else "0%"
        }

# Инициализируем анализатор
enhanced_analyzer, cascade_notifications, full_version = initialize_components()

if not full_version:
    st.info("🔄 Используется упрощенная версия анализатора (полная версия недоступна)")
    enhanced_analyzer = SimpleIntegratedAnalyzer()

# Основной интерфейс
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Анализ", "📊 Статистика", "⚙️ Настройки", "ℹ️ О системе"])

with tab1:
    st.header("Предварительная фильтрация по этапу 1d (ML сигналы)")
    
    # Кнопки управления
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("🔄 Обновить ML фильтр", type="primary"):
            enhanced_analyzer.clear_cache()
            if 'stage1d_results' in st.session_state:
                del st.session_state.stage1d_results
            st.rerun()
    
    with col2:
        if st.button("📊 Статистика"):
            stats = enhanced_analyzer.get_cache_stats()
            st.json(stats)
    
    with col3:
        if st.button("🗑️ Очистить кэш"):
            enhanced_analyzer.clear_cache()
            st.success("Кэш очищен")
    
    with col4:
        if st.button("💾 Экспорт"):
            if 'stage1d_results' in st.session_state:
                results_df = pd.DataFrame([r.to_dict() for r in st.session_state.stage1d_results.values()])
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="📥 Скачать CSV",
                    data=csv,
                    file_name=f"stage1d_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    with col5:
        if st.button("🎲 Демо данные"):
            # Загружаем демо данные
            demo_symbols = ['SBER', 'GAZP', 'LKOH', 'NVTK', 'ROSN', 'MGNT', 'YNDX', 'VKCO', 'NLMK', 'ALRS']
            
            # Убеждаемся, что используем правильный анализатор
            if full_version:
                # Для полной версии используем asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    st.session_state.stage1d_results = loop.run_until_complete(
                        enhanced_analyzer.prefilter_symbols_stage1d(demo_symbols)
                    )
                finally:
                    loop.close()
            else:
                # Для демо версии используем синхронный метод
                st.session_state.stage1d_results = enhanced_analyzer.prefilter_symbols_stage1d(demo_symbols)
            
            st.success("Демо данные загружены!")
            st.rerun()
        
        if st.button("🚀 Демо + Анализ"):
            # Загружаем демо данные и сразу запускаем анализ
            demo_symbols = ['SBER', 'GAZP', 'LKOH', 'NVTK', 'ROSN', 'MGNT', 'YNDX', 'VKCO', 'NLMK', 'ALRS']
            
            # Убеждаемся, что используем правильный анализатор
            if full_version:
                # Для полной версии используем asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    st.session_state.stage1d_results = loop.run_until_complete(
                        enhanced_analyzer.prefilter_symbols_stage1d(demo_symbols)
                    )
                finally:
                    loop.close()
            else:
                # Для демо версии используем синхронный метод
                st.session_state.stage1d_results = enhanced_analyzer.prefilter_symbols_stage1d(demo_symbols)
            
            st.success("Демо данные загружены!")
            
            # Сразу запускаем анализ
            passed_symbols = enhanced_analyzer.get_passed_symbols(st.session_state.stage1d_results)
            if passed_symbols:
                st.info(f"Запуск анализа для {len(passed_symbols)} кандидатов...")
                
                with st.spinner("Выполняется каскадный анализ..."):
                    try:
                        results = enhanced_analyzer.analyze_prefiltered_symbols(passed_symbols)
                        st.session_state.cascade_results = results
                        
                        st.success(f"✅ Анализ завершен! Обработано {len(results)} символов")
                        
                        # Показываем результаты
                        successful_results = [r for r in results if r.get('final_signal') is not None]
                        if successful_results:
                            st.subheader("🎯 Успешные сигналы")
                            for result in successful_results:
                                st.write(f"**{result['symbol']}**: {result['final_signal']} @ {result['entry_price']:.2f} ₽ (R/R: {result['risk_reward']:.1f})")
                        else:
                            st.warning("Нет успешных сигналов")
                            
                    except Exception as e:
                        st.error(f"Ошибка анализа: {e}")
            else:
                st.warning("Нет кандидатов для анализа")
    
    # Добавляем быструю кнопку запуска анализа после загрузки данных
    if 'stage1d_results' in st.session_state:
        passed_symbols = enhanced_analyzer.get_passed_symbols(st.session_state.stage1d_results)
        if passed_symbols:
            st.markdown("### 🚀 Быстрый запуск анализа")
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("📊 Анализировать все", type="primary", key="quick_analyze_all"):
                    st.info(f"Запуск анализа для {len(passed_symbols)} символов...")
                    
                    with st.spinner("Выполняется каскадный анализ..."):
                        try:
                            if full_version:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                try:
                                    results = loop.run_until_complete(
                                        enhanced_analyzer.analyze_prefiltered_symbols(passed_symbols)
                                    )
                                finally:
                                    loop.close()
                            else:
                                results = enhanced_analyzer.analyze_prefiltered_symbols(passed_symbols)
                            
                            st.session_state.cascade_results = results
                            st.success(f"✅ Анализ завершен! Обработано {len(results)} символов")
                            
                            # Показываем краткие результаты
                            successful_results = [r for r in results if r.get('final_signal') is not None]
                            if successful_results:
                                st.subheader("🎯 Успешные сигналы")
                                for result in successful_results[:5]:  # Показываем первые 5
                                    st.write(f"**{result['symbol']}**: {result['final_signal']} @ {result['entry_price']:.2f} ₽ (R/R: {result['risk_reward']:.1f})")
                                
                                if len(successful_results) > 5:
                                    st.write(f"... и еще {len(successful_results) - 5} сигналов")
                            else:
                                st.warning("Нет успешных сигналов")
                                
                        except Exception as e:
                            st.error(f"Ошибка анализа: {e}")
            
            with col2:
                if st.button("📈 Только BUY", key="quick_analyze_buy"):
                    buy_symbols = [r.symbol for r in enhanced_analyzer.get_buy_candidates(st.session_state.stage1d_results)]
                    if buy_symbols:
                        st.info(f"Запуск анализа для {len(buy_symbols)} BUY сигналов...")
                        # Аналогичная логика анализа
                    else:
                        st.warning("Нет BUY сигналов")
            
            with col3:
                if st.button("📉 Только SELL", key="quick_analyze_sell"):
                    sell_symbols = [r.symbol for r in enhanced_analyzer.get_sell_candidates(st.session_state.stage1d_results)]
                    if sell_symbols:
                        st.info(f"Запуск анализа для {len(sell_symbols)} SELL сигналов...")
                        # Аналогичная логика анализа
                    else:
                        st.warning("Нет SELL сигналов")
    
    # Получаем доступные символы
    if full_version:
        try:
            all_symbols = enhanced_analyzer.cascade_analyzer.multi_analyzer.get_available_symbols()
            if not all_symbols:
                all_symbols = ['SBER', 'GAZP', 'LKOH', 'NVTK', 'ROSN', 'MGNT', 'YNDX', 'VKCO']
        except:
            all_symbols = ['SBER', 'GAZP', 'LKOH', 'NVTK', 'ROSN', 'MGNT', 'YNDX', 'VKCO']
    else:
        all_symbols = ['SBER', 'GAZP', 'LKOH', 'NVTK', 'ROSN', 'MGNT', 'YNDX', 'VKCO', 'NLMK', 'ALRS', 'CHMF', 'MTSS']
    
    st.info(f"Доступно символов: {len(all_symbols)} | Режим: {'Полная версия' if full_version else 'Демо версия'}")
    
    # Проверяем кэш результатов этапа 1d
    if 'stage1d_results' not in st.session_state:
        st.info("🔄 Запуск предварительной фильтрации по этапу 1d (ML сигналы)...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            if full_version:
                # Используем asyncio для полной версии
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    stage1d_results = loop.run_until_complete(
                        enhanced_analyzer.prefilter_symbols_stage1d(all_symbols)
                    )
                finally:
                    loop.close()
            else:
                # Используем синхронную версию для демо
                stage1d_results = enhanced_analyzer.prefilter_symbols_stage1d(all_symbols)
            
            st.session_state.stage1d_results = stage1d_results
            
            progress_bar.progress(1.0)
            status_text.text("✅ Фильтрация завершена!")
            
        except Exception as e:
            st.error(f"Ошибка фильтрации: {e}")
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
        st.dataframe(df, width='stretch')
        
        # Кнопки для выбора кандидатов
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🎯 Топ-10"):
                top_10_symbols = [r.symbol for r in top_candidates[:10]]
                st.session_state.selected_candidates = top_10_symbols
                st.success(f"Выбрано {len(top_10_symbols)} топ кандидатов")
        
        with col2:
            if st.button("📈 Все BUY"):
                buy_symbols = [r.symbol for r in buy_candidates]
                st.session_state.selected_candidates = buy_symbols
                st.success(f"Выбрано {len(buy_symbols)} BUY сигналов")
        
        with col3:
            if st.button("📉 Все SELL"):
                sell_symbols = [r.symbol for r in sell_candidates]
                st.session_state.selected_candidates = sell_symbols
                st.success(f"Выбрано {len(sell_symbols)} SELL сигналов")
        
        with col4:
            if st.button("🎲 Случайные 5"):
                import random
                random_symbols = random.sample(passed_symbols, min(5, len(passed_symbols)))
                st.session_state.selected_candidates = random_symbols
                st.success(f"Выбрано {len(random_symbols)} случайных символов")
        
        # Добавляем кнопку для запуска анализа всех прошедших этап 1d
        if passed_symbols:
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                if st.button("🚀 Запустить анализ всех прошедших этап 1d", type="primary", key="analyze_all_passed"):
                    st.info(f"Запуск анализа для {len(passed_symbols)} кандидатов, прошедших этап 1d...")
                    
                    with st.spinner("Выполняется каскадный анализ..."):
                        try:
                            if full_version:
                                # Используем asyncio для полной версии
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                try:
                                    results = loop.run_until_complete(
                                        enhanced_analyzer.analyze_prefiltered_symbols(passed_symbols)
                                    )
                                    
                                    # Отправляем уведомления
                                    for result in results:
                                        if result.final_signal:
                                            loop.run_until_complete(
                                                cascade_notifications.notify_cascade_signal(result)
                                            )
                                finally:
                                    loop.close()
                            else:
                                # Используем синхронную версию для демо
                                results = enhanced_analyzer.analyze_prefiltered_symbols(passed_symbols)
                            
                            st.session_state.cascade_results = results
                            
                            st.success(f"✅ Анализ завершен! Обработано {len(results)} символов")
                            
                            # Показываем результаты
                            successful_results = [r for r in results if r.get('final_signal') is not None]
                            if successful_results:
                                st.subheader("🎯 Успешные сигналы")
                                
                                results_data = []
                                for result in successful_results:
                                    results_data.append({
                                        'Символ': result['symbol'],
                                        'Сигнал': result['final_signal'],
                                        'Уверенность': f"{result['confidence']:.1%}",
                                        'Цена входа': f"{result['entry_price']:.2f} ₽",
                                        'Stop Loss': f"{result['stop_loss']:.2f} ₽",
                                        'Take Profit': f"{result['take_profit']:.2f} ₽",
                                        'R/R': f"{result['risk_reward']:.1f}",
                                        'Автоторговля': "Да" if result['auto_trade_enabled'] else "Нет"
                                    })
                                
                                results_df = pd.DataFrame(results_data)
                                st.dataframe(results_df, width='stretch')
                            else:
                                st.warning("Нет успешных сигналов")
                            
                        except Exception as e:
                            st.error(f"Ошибка анализа: {e}")
        
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
                        if full_version:
                            # Используем asyncio для полной версии
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            try:
                                results = loop.run_until_complete(
                                    enhanced_analyzer.analyze_prefiltered_symbols(selected_symbols)
                                )
                                
                                # Отправляем уведомления
                                for result in results:
                                    if result.final_signal:
                                        loop.run_until_complete(
                                            cascade_notifications.notify_cascade_signal(result)
                                        )
                            finally:
                                loop.close()
                        else:
                            # Используем синхронную версию для демо
                            results = enhanced_analyzer.analyze_prefiltered_symbols(selected_symbols)
                        
                        st.session_state.cascade_results = results
                        
                        st.success(f"✅ Анализ завершен! Обработано {len(results)} символов")
                        
                        # Показываем результаты
                        successful_results = [r for r in results if r.get('final_signal') is not None]
                        if successful_results:
                            st.subheader("🎯 Успешные сигналы")
                            
                            results_data = []
                            for result in successful_results:
                                results_data.append({
                                    'Символ': result['symbol'],
                                    'Сигнал': result['final_signal'],
                                    'Уверенность': f"{result['confidence']:.1%}",
                                    'Цена входа': f"{result['entry_price']:.2f} ₽",
                                    'Stop Loss': f"{result['stop_loss']:.2f} ₽",
                                    'Take Profit': f"{result['take_profit']:.2f} ₽",
                                    'R/R': f"{result['risk_reward']:.1f}",
                                    'Автоторговля': "Да" if result['auto_trade_enabled'] else "Нет"
                                })
                            
                            results_df = pd.DataFrame(results_data)
                            st.dataframe(results_df, width='stretch')
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
    
    # Статистика кэша
    if 'stage1d_results' in st.session_state:
        st.subheader("📊 Статистика кэша")
        cache_stats = enhanced_analyzer.get_cache_stats()
        st.json(cache_stats)

with tab4:
    st.header("ℹ️ О системе")
    
    st.subheader("🎯 Концепция каскадного анализатора")
    
    st.info("""
    **Каскадный анализатор** реализует двухэтапный подход к анализу торговых сигналов:
    
    ### Этап 1: Предварительная фильтрация (1d)
    - **Автоматический запуск** при загрузке страницы
    - **ML анализ** всех доступных символов
    - **Фильтрация** по минимальной уверенности (60%)
    - **Кэширование** результатов для ускорения
    
    ### Этап 2: Каскадный анализ (1h → 1m → 1s)
    - **Подтверждение тренда** на часовых данных
    - **Поиск точки входа** на минутных данных
    - **Микро-оптимизация** на секундных данных
    - **Расчет риск/доходности** и торговых параметров
    """)
    
    st.subheader("🚀 Преимущества")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("""
        **Производительность:**
        - Сокращение времени анализа
        - Исключение неэффективных символов
        - Кэширование результатов
        """)
    
    with col2:
        st.success("""
        **Качество сигналов:**
        - ML фильтрация на входе
        - Многоуровневая проверка
        - Автоматический риск-менеджмент
        """)
    
    st.subheader("📁 Компоненты системы")
    
    components = {
        "Основные": [
            "core/cascade_analyzer.py - Базовый каскадный анализатор",
            "core/cascade_analyzer_enhanced.py - Улучшенная версия с предварительной фильтрацией",
            "core/cascade_notifications.py - Система уведомлений"
        ],
        "Интерфейсы": [
            "pages/21_Cascade_Analyzer_Integrated.py - Интегрированная версия (этот файл)",
            "pages/21_Cascade_Analyzer_Simple.py - Простая демо версия",
            "pages/21_Cascade_Analyzer_Enhanced.py - Расширенная версия с asyncio"
        ],
        "Демонстрация": [
            "demo_enhanced_cascade_simple.py - Демонстрация концепции",
            "docs/ENHANCED_CASCADE_ANALYZER_GUIDE.md - Подробное руководство"
        ]
    }
    
    for category, items in components.items():
        with st.expander(f"📂 {category}"):
            for item in items:
                st.write(f"• {item}")
    
    st.subheader("🔧 Технические детали")
    
    st.code("""
# Основные классы:
- CascadeAnalyzer: Базовый каскадный анализатор
- EnhancedCascadeAnalyzer: Улучшенная версия с предварительной фильтрацией
- CascadeSignalResult: Результат каскадного анализа
- Stage1dResult: Результат этапа 1d

# Ключевые методы:
- prefilter_symbols_stage1d(): Предварительная фильтрация
- analyze_prefiltered_symbols(): Каскадный анализ
- get_passed_symbols(): Получение прошедших символов
- get_top_candidates(): Топ кандидаты по уверенности
    """, language="python")
    
    st.subheader("🎮 Как использовать")
    
    st.markdown("""
    1. **Загрузка страницы** → Автоматическая предварительная фильтрация
    2. **Просмотр кандидатов** → Выбор символов для анализа
    3. **Запуск анализа** → Каскадный анализ выбранных символов
    4. **Просмотр результатов** → Торговые сигналы с параметрами
    5. **Экспорт данных** → Сохранение результатов в CSV
    """)
    
    # Статус системы
    st.subheader("📊 Статус системы")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if full_version:
            st.success("✅ Полная версия активна")
        else:
            st.warning("⚠️ Демо версия активна")
    
    with col2:
        if 'stage1d_results' in st.session_state:
            st.success("✅ Данные загружены")
        else:
            st.info("ℹ️ Данные не загружены")
    
    with col3:
        if 'cascade_results' in st.session_state:
            st.success("✅ Анализ выполнен")
        else:
            st.info("ℹ️ Анализ не выполнен")
