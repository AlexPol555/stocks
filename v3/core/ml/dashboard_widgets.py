#!/usr/bin/env python3
"""ML widgets for Dashboard integration."""

import asyncio
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import streamlit as st

# Optional plotly import
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

logger = logging.getLogger(__name__)

class MLDashboardWidgets:
    """ML widgets for Dashboard integration."""
    
    def __init__(self, ml_manager):
        self.ml_manager = ml_manager
        self.signal_generator = None
        
    def initialize_signal_generator(self):
        """Initialize signal generator."""
        if self.signal_generator is None:
            from .signals import MLSignalGenerator
            self.signal_generator = MLSignalGenerator(self.ml_manager)
    
    async def render_ml_signals_section(self, symbols: List[str], max_symbols: int = 10, use_cache: bool = True):
        """Render ML signals section for Dashboard."""
        try:
            self.initialize_signal_generator()
            
            st.subheader("🤖 ML Trading Signals")
            st.caption("AI-powered trading signals based on price prediction, sentiment analysis, and technical indicators")
            st.info("📊 Signals are sorted by quality (signal strength + confidence) - best opportunities first")
            
            # Get ML signals for selected symbols
            selected_symbols = symbols[:max_symbols] if len(symbols) > max_symbols else symbols
            
            if not selected_symbols:
                st.warning("No symbols selected for ML analysis")
                return
            
            # Generate signals with progress bar and timer
            signals_df = await self._generate_signals_with_progress(selected_symbols, use_cache)
            
            if signals_df.empty:
                st.error("Failed to generate ML signals")
                return
            
            # Sort by signal quality (confidence and signal strength)
            signals_df = self._sort_signals_by_quality(signals_df)
            
            # Show only best signals option
            show_best_only = st.checkbox("🎯 Show only best signals (BUY/STRONG_BUY)", key="show_best_signals")
            if show_best_only:
                best_signals = signals_df[signals_df['ensemble_signal'].isin(['BUY', 'STRONG_BUY'])]
                if not best_signals.empty:
                    signals_df = best_signals
                    st.success(f"🎯 Showing {len(signals_df)} best BUY signals")
                else:
                    st.warning("No BUY signals found in current selection")
            
            # Display signals in columns
            cols = st.columns(min(3, len(signals_df)))
            
            for idx, (_, row) in enumerate(signals_df.iterrows()):
                col_idx = idx % len(cols)
                
                with cols[col_idx]:
                    self._render_signal_card(row)
            
            # Detailed signals table
            if st.checkbox("Show detailed ML signals", key="ml_detailed_signals"):
                self._render_signals_table(signals_df)
                
        except Exception as e:
            logger.error(f"Error rendering ML signals section: {e}")
            st.error(f"ML signals error: {e}")
    
    def _sort_signals_by_quality(self, signals_df: pd.DataFrame) -> pd.DataFrame:
        """Sort signals by quality (confidence and signal strength)."""
        try:
            # Create quality score based on signal strength and confidence
            signal_strength_map = {
                'STRONG_BUY': 5,
                'BUY': 4,
                'HOLD': 3,
                'SELL': 2,
                'STRONG_SELL': 1
            }
            
            # Calculate quality score
            signals_df['signal_strength'] = signals_df['ensemble_signal'].map(signal_strength_map).fillna(3)
            signals_df['quality_score'] = (
                signals_df['signal_strength'] * 0.6 +  # Signal strength weight
                signals_df['confidence'] * 0.4         # Confidence weight
            )
            
            # Sort by quality score (descending) and confidence (descending)
            signals_df = signals_df.sort_values(['quality_score', 'confidence'], ascending=[False, False])
            
            # Remove temporary columns
            signals_df = signals_df.drop(['signal_strength', 'quality_score'], axis=1)
            
            return signals_df
            
        except Exception as e:
            logger.error(f"Error sorting signals by quality: {e}")
            return signals_df
    
    async def _generate_signals_with_progress(self, selected_symbols: List[str], use_cache: bool = True) -> pd.DataFrame:
        """Generate ML signals with progress bar and timer."""
        import time
        from datetime import datetime, timedelta
        
        # Calculate estimated time based on number of symbols
        # Base time: 2 seconds per symbol + 5 seconds overhead
        estimated_time_per_symbol = 2.0
        overhead_time = 5.0
        total_estimated_time = len(selected_symbols) * estimated_time_per_symbol + overhead_time
        
        # Try to get from cache first
        if use_cache:
            from .cache import ml_cache_manager
            cached_signals = ml_cache_manager.get_ml_signals(selected_symbols)
            if not cached_signals.empty:
                st.info(f"✅ Using cached ML signals ({len(cached_signals)} symbols) - Generated at: {cached_signals['created_at'].iloc[0] if 'created_at' in cached_signals.columns else 'Unknown'}")
                return cached_signals
        
        # Create progress container
        progress_container = st.container()
        with progress_container:
            st.info(f"🤖 Analyzing {len(selected_symbols)} symbols - Estimated time: {total_estimated_time:.0f} seconds")
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            timer_text = st.empty()
            
            # Start timer
            start_time = time.time()
            
            try:
                results = []
                total_symbols = len(selected_symbols)
                
                for i, symbol in enumerate(selected_symbols):
                    # Update progress
                    progress = (i + 1) / total_symbols
                    progress_bar.progress(progress)
                    
                    # Calculate elapsed and estimated remaining time
                    elapsed_time = time.time() - start_time
                    if i > 0:
                        avg_time_per_symbol = elapsed_time / (i + 1)
                        remaining_symbols = total_symbols - (i + 1)
                        estimated_remaining = remaining_symbols * avg_time_per_symbol
                    else:
                        estimated_remaining = total_estimated_time - elapsed_time
                    
                    # Update status
                    status_text.text(f"📊 Processing {symbol} ({i + 1}/{total_symbols})")
                    
                    # Update timer
                    elapsed_str = f"{elapsed_time:.1f}s"
                    remaining_str = f"{max(0, estimated_remaining):.1f}s"
                    timer_text.text(f"⏱️ Elapsed: {elapsed_str} | Remaining: {remaining_str}")
                    
                    # Generate signals for current symbol
                    signals = await self.signal_generator.generate_ml_signals(symbol)
                    
                    if 'error' not in signals:
                        results.append({
                            'symbol': symbol,
                            'ensemble_signal': signals.get('ml_ensemble_signal', 'HOLD'),
                            'price_signal': signals.get('ml_price_signal', 'HOLD'),
                            'sentiment_signal': signals.get('ml_sentiment_signal', 'HOLD'),
                            'technical_signal': signals.get('ml_technical_signal', 'HOLD'),
                            'risk_level': signals.get('ml_risk_level', 'UNKNOWN'),
                            'confidence': round(np.mean([
                                signals.get('ml_price_confidence', 0.5),
                                signals.get('ml_sentiment_confidence', 0.5),
                                signals.get('ml_technical_confidence', 0.5)
                            ]), 2),
                            'data_points': signals.get('data_points', 0),
                            'timestamp': signals.get('timestamp', ''),
                            'price_prediction': signals.get('ml_price_prediction'),
                            'sentiment': signals.get('ml_sentiment'),
                            'sentiment_score': signals.get('ml_sentiment_score'),
                            'sentiment_confidence': signals.get('ml_sentiment_confidence'),
                            'price_confidence': signals.get('ml_price_confidence'),
                            'technical_confidence': signals.get('ml_technical_confidence')
                        })
                    
                    # Small delay to show progress
                    await asyncio.sleep(0.1)
                
                # Final update
                total_time = time.time() - start_time
                progress_bar.progress(1.0)
                status_text.text(f"✅ Completed analysis of {len(results)} symbols")
                timer_text.text(f"⏱️ Total time: {total_time:.1f}s")
                
                # Save to cache
                if results:
                    from .cache import ml_cache_manager
                    signals_df = pd.DataFrame(results)
                    ml_cache_manager.save_ml_signals(signals_df)
                    st.success(f"💾 Saved {len(results)} ML signals to cache")
                
                # Clear progress after a short delay
                await asyncio.sleep(2)
                progress_container.empty()
                
                return pd.DataFrame(results)
                
            except Exception as e:
                logger.error(f"Error generating signals with progress: {e}")
                progress_container.empty()
                st.error(f"Failed to generate ML signals: {e}")
                return pd.DataFrame()
    
    def _render_signal_card(self, signal_data: pd.Series):
        """Render individual signal card."""
        try:
            symbol = signal_data['symbol']
            ensemble_signal = signal_data['ensemble_signal']
            confidence = signal_data['confidence']
            risk_level = signal_data['risk_level']
            
            # Signal color and emoji
            signal_config = {
                'STRONG_BUY': {'color': 'green', 'emoji': '🚀', 'bg': '#d4edda'},
                'BUY': {'color': 'lightgreen', 'emoji': '📈', 'bg': '#d1ecf1'},
                'HOLD': {'color': 'orange', 'emoji': '⏸️', 'bg': '#fff3cd'},
                'SELL': {'color': 'lightcoral', 'emoji': '📉', 'bg': '#f8d7da'},
                'STRONG_SELL': {'color': 'red', 'emoji': '💥', 'bg': '#f5c6cb'}
            }
            
            config = signal_config.get(ensemble_signal, signal_config['HOLD'])
            
            # Risk level color
            risk_colors = {
                'LOW': 'green',
                'MEDIUM': 'orange', 
                'HIGH': 'red',
                'UNKNOWN': 'gray'
            }
            risk_color = risk_colors.get(risk_level, 'gray')
            
            # Create card
            with st.container():
                st.markdown(f"""
                <div style="
                    border: 1px solid {config['color']};
                    border-radius: 8px;
                    padding: 12px;
                    margin: 4px 0;
                    background-color: {config['bg']};
                ">
                    <h4 style="margin: 0; color: {config['color']};">
                        {config['emoji']} {symbol}
                    </h4>
                    <p style="margin: 4px 0; font-weight: bold;">
                        {ensemble_signal}
                    </p>
                    <p style="margin: 2px 0; font-size: 0.9em;">
                        Confidence: {confidence:.1%}
                    </p>
                    <p style="margin: 2px 0; font-size: 0.9em; color: {risk_color};">
                        Risk: {risk_level}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            logger.error(f"Error rendering signal card: {e}")
            st.error(f"Signal card error: {e}")
    
    def _render_signals_table(self, signals_df: pd.DataFrame):
        """Render detailed signals table."""
        try:
            # Format the dataframe for display
            display_df = signals_df.copy()
            display_df = display_df.rename(columns={
                'symbol': 'Symbol',
                'ensemble_signal': 'ML Signal',
                'price_signal': 'Price Signal',
                'sentiment_signal': 'Sentiment',
                'technical_signal': 'Technical',
                'risk_level': 'Risk',
                'confidence': 'Confidence',
                'data_points': 'Data Points'
            })
            
            # Style the dataframe
            def highlight_signals(val):
                if val in ['STRONG_BUY', 'BUY']:
                    return 'background-color: #d4edda'
                elif val in ['STRONG_SELL', 'SELL']:
                    return 'background-color: #f8d7da'
                else:
                    return 'background-color: #fff3cd'
            
            styled_df = display_df.style.applymap(highlight_signals, subset=['ML Signal', 'Price Signal', 'Sentiment', 'Technical'])
            
            st.dataframe(styled_df, width='stretch')
            
        except Exception as e:
            logger.error(f"Error rendering signals table: {e}")
            st.error(f"Signals table error: {e}")
    
    def render_ml_analytics_section(self, symbol: str):
        """Render ML analytics section for a specific symbol."""
        try:
            st.subheader(f"🤖 ML Analytics: {symbol}")
            
            # Get ML recommendations with progress indicator
            recommendations = self._get_ml_recommendations_with_progress(symbol)
            
            if 'error' in recommendations:
                st.error(f"ML analysis error: {recommendations['error']}")
                return
            
            # Create tabs for different analytics
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Predictions", "🎯 Clustering", "🧬 Optimization", "📈 Sentiment"])
            
            with tab1:
                self._render_predictions_tab(symbol, recommendations)
            
            with tab2:
                self._render_clustering_tab(symbol, recommendations)
            
            with tab3:
                self._render_optimization_tab(symbol, recommendations)
            
            with tab4:
                self._render_sentiment_tab(symbol, recommendations)
                
        except Exception as e:
            logger.error(f"Error rendering ML analytics section: {e}")
            st.error(f"ML analytics error: {e}")
    
    def _get_ml_recommendations_with_progress(self, symbol: str) -> Dict[str, Any]:
        """Get ML recommendations with progress indicator."""
        import time
        
        # Create progress container
        progress_container = st.container()
        with progress_container:
            st.info(f"🔍 Analyzing {symbol} - Estimated time: 10-15 seconds")
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            timer_text = st.empty()
            
            # Start timer
            start_time = time.time()
            
            try:
                # Simulate progress for different analysis steps
                analysis_steps = [
                    "📊 Price prediction analysis...",
                    "🎯 Clustering analysis...",
                    "🧬 Strategy optimization...",
                    "📈 Sentiment analysis...",
                    "🔄 Generating recommendations..."
                ]
                
                for i, step in enumerate(analysis_steps):
                    # Update progress
                    progress = (i + 1) / len(analysis_steps)
                    progress_bar.progress(progress)
                    
                    # Update status
                    status_text.text(step)
                    
                    # Update timer
                    elapsed_time = time.time() - start_time
                    timer_text.text(f"⏱️ Elapsed: {elapsed_time:.1f}s")
                    
                    # Small delay to show progress
                    time.sleep(0.5)
                
                # Get actual recommendations
                recommendations = self.ml_manager.get_ml_recommendations(symbol)
                
                # Final update
                total_time = time.time() - start_time
                progress_bar.progress(1.0)
                status_text.text(f"✅ Analysis completed for {symbol}")
                timer_text.text(f"⏱️ Total time: {total_time:.1f}s")
                
                # Clear progress after a short delay
                time.sleep(1)
                progress_container.empty()
                
                return recommendations
                
            except Exception as e:
                logger.error(f"Error getting ML recommendations with progress: {e}")
                progress_container.empty()
                return {'error': str(e)}
    
    def _render_predictions_tab(self, symbol: str, recommendations: Dict[str, Any]):
        """Render predictions tab."""
        try:
            # Price prediction
            if 'price_prediction' in recommendations:
                pred = recommendations['price_prediction']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric(
                        "Predicted Direction",
                        pred.get('direction', 'Unknown'),
                        delta=f"{pred.get('confidence', 0):.1%} confidence"
                    )
                
                with col2:
                    st.metric(
                        "Prediction Horizon",
                        f"{pred.get('horizon_days', 0)} days",
                        delta=f"Accuracy: {pred.get('accuracy', 0):.1%}"
                    )
                
                # Prediction chart
                if 'historical_predictions' in pred:
                    self._render_prediction_chart(pred['historical_predictions'])
            
            # Clustering info
            if 'clustering' in recommendations:
                cluster_info = recommendations['clustering']
                st.info(f"**Cluster**: {cluster_info.get('cluster', 'Unknown')} - {cluster_info.get('description', 'No description')}")
                
        except Exception as e:
            logger.error(f"Error rendering predictions tab: {e}")
            st.error(f"Predictions error: {e}")
    
    def _render_clustering_tab(self, symbol: str, recommendations: Dict[str, Any]):
        """Render clustering tab."""
        try:
            if 'clustering' in recommendations:
                cluster_info = recommendations['clustering']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Cluster ID", cluster_info.get('cluster', 'Unknown'))
                    st.metric("Silhouette Score", f"{cluster_info.get('silhouette_score', 0):.3f}")
                
                with col2:
                    st.metric("Cluster Size", cluster_info.get('cluster_size', 0))
                    st.metric("Similarity", f"{cluster_info.get('similarity', 0):.1%}")
                
                # Cluster characteristics
                if 'characteristics' in cluster_info:
                    st.subheader("Cluster Characteristics")
                    for char, value in cluster_info['characteristics'].items():
                        st.write(f"**{char}**: {value}")
                
                # Similar stocks
                if 'similar_stocks' in cluster_info:
                    st.subheader("Similar Stocks")
                    similar = cluster_info['similar_stocks']
                    if similar:
                        st.write(", ".join(similar[:10]))  # Show first 10
                    else:
                        st.write("No similar stocks found")
                        
        except Exception as e:
            logger.error(f"Error rendering clustering tab: {e}")
            st.error(f"Clustering error: {e}")
    
    def _render_optimization_tab(self, symbol: str, recommendations: Dict[str, Any]):
        """Render optimization tab."""
        try:
            if 'optimization' in recommendations:
                opt_info = recommendations['optimization']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Optimized Return", f"{opt_info.get('optimized_return', 0):.2%}")
                    st.metric("Risk Level", opt_info.get('risk_level', 'Unknown'))
                
                with col2:
                    st.metric("Sharpe Ratio", f"{opt_info.get('sharpe_ratio', 0):.3f}")
                    st.metric("Max Drawdown", f"{opt_info.get('max_drawdown', 0):.2%}")
                
                # Optimization parameters
                if 'parameters' in opt_info:
                    st.subheader("Optimized Parameters")
                    params = opt_info['parameters']
                    for param, value in params.items():
                        st.write(f"**{param}**: {value}")
                        
        except Exception as e:
            logger.error(f"Error rendering optimization tab: {e}")
            st.error(f"Optimization error: {e}")
    
    def _render_sentiment_tab(self, symbol: str, recommendations: Dict[str, Any]):
        """Render sentiment tab."""
        try:
            if 'sentiment' in recommendations:
                sent_info = recommendations['sentiment']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Overall Sentiment", sent_info.get('overall_sentiment', 'Unknown'))
                    st.metric("Confidence", f"{sent_info.get('confidence', 0):.1%}")
                
                with col2:
                    st.metric("Articles Analyzed", sent_info.get('total_articles', 0))
                    st.metric("Sentiment Score", f"{sent_info.get('sentiment_score', 0):.3f}")
                
                # Sentiment breakdown
                if 'breakdown' in sent_info:
                    st.subheader("Sentiment Breakdown")
                    breakdown = sent_info['breakdown']
                    for sentiment, count in breakdown.items():
                        st.write(f"**{sentiment}**: {count} articles")
                        
        except Exception as e:
            logger.error(f"Error rendering sentiment tab: {e}")
            st.error(f"Sentiment error: {e}")
    
    def _render_prediction_chart(self, historical_predictions: List[Dict]):
        """Render prediction chart."""
        try:
            if not historical_predictions:
                return
            
            if not PLOTLY_AVAILABLE:
                st.info("📊 Chart visualization requires plotly. Install with: pip install plotly")
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(historical_predictions)
            
            # Create chart
            fig = go.Figure()
            
            # Actual prices
            if 'actual' in df.columns and 'date' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['actual'],
                    mode='lines',
                    name='Actual Price',
                    line=dict(color='blue')
                ))
            
            # Predicted prices
            if 'predicted' in df.columns and 'date' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['predicted'],
                    mode='lines',
                    name='Predicted Price',
                    line=dict(color='red', dash='dash')
                ))
            
            fig.update_layout(
                title="Price Predictions vs Actual",
                xaxis_title="Date",
                yaxis_title="Price",
                height=400
            )
            
            st.plotly_chart(fig, width='stretch')
            
        except Exception as e:
            logger.error(f"Error rendering prediction chart: {e}")
            st.error(f"Prediction chart error: {e}")
    
    def render_ml_metrics_summary(self, symbols: List[str]) -> Dict[str, Any]:
        """Render ML metrics summary."""
        try:
            self.initialize_signal_generator()
            
            if not symbols:
                return {}
            
            # Get signals for all symbols with progress indicator
            signals_df = self._get_ml_metrics_with_progress(symbols)
            
            if signals_df.empty:
                return {}
            
            # Calculate summary metrics
            total_signals = len(signals_df)
            buy_signals = len(signals_df[signals_df['ensemble_signal'].isin(['BUY', 'STRONG_BUY'])])
            sell_signals = len(signals_df[signals_df['ensemble_signal'].isin(['SELL', 'STRONG_SELL'])])
            hold_signals = len(signals_df[signals_df['ensemble_signal'] == 'HOLD'])
            
            avg_confidence = signals_df['confidence'].mean()
            high_risk = len(signals_df[signals_df['risk_level'] == 'HIGH'])
            
            return {
                'total_signals': total_signals,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'hold_signals': hold_signals,
                'avg_confidence': avg_confidence,
                'high_risk_signals': high_risk,
                'buy_ratio': buy_signals / total_signals if total_signals > 0 else 0,
                'sell_ratio': sell_signals / total_signals if total_signals > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error rendering ML metrics summary: {e}")
            return {}
    
    def _get_ml_metrics_with_progress(self, symbols: List[str]) -> pd.DataFrame:
        """Get ML metrics with progress indicator."""
        import time
        
        # Create progress container
        progress_container = st.container()
        with progress_container:
            st.info(f"📊 Calculating ML metrics for {len(symbols)} symbols - Estimated time: 5-8 seconds")
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            timer_text = st.empty()
            
            # Start timer
            start_time = time.time()
            
            try:
                # Simulate progress for metrics calculation
                metrics_steps = [
                    "📊 Generating ML signals...",
                    "🎯 Calculating signal statistics...",
                    "📈 Computing confidence metrics...",
                    "🔄 Finalizing summary..."
                ]
                
                for i, step in enumerate(metrics_steps):
                    # Update progress
                    progress = (i + 1) / len(metrics_steps)
                    progress_bar.progress(progress)
                    
                    # Update status
                    status_text.text(step)
                    
                    # Update timer
                    elapsed_time = time.time() - start_time
                    timer_text.text(f"⏱️ Elapsed: {elapsed_time:.1f}s")
                    
                    # Small delay to show progress
                    time.sleep(0.3)
                
                # Get actual signals
                signals_df = self.signal_generator.get_ml_signal_summary(symbols)
                
                # Final update
                total_time = time.time() - start_time
                progress_bar.progress(1.0)
                status_text.text(f"✅ Metrics calculated for {len(symbols)} symbols")
                timer_text.text(f"⏱️ Total time: {total_time:.1f}s")
                
                # Clear progress after a short delay
                time.sleep(1)
                progress_container.empty()
                
                return signals_df
                
            except Exception as e:
                logger.error(f"Error getting ML metrics with progress: {e}")
                progress_container.empty()
                return pd.DataFrame()
