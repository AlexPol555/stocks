"""ML and AI page for predictive analytics and strategy optimization."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import logging

# Import ML modules
try:
    # Test basic dependencies first
    import seaborn
    import matplotlib
    import torch
    import transformers
    import sklearn
    import plotly
    
    from core.ml import (
        LSTMPredictor, GRUPredictor, ModelConfig,
        NewsSentimentAnalyzer, SentimentConfig,
        StockClusterer, ClusteringConfig,
        GeneticOptimizer, GeneticConfig,
        TradingAgent, RLConfig,
        EnsemblePredictor, EnsembleConfig
    )
    from core.ml.integration import create_ml_integration_manager
    ML_AVAILABLE = True
    FALLBACK_MODE = False
except ImportError as e:
    st.warning(f"Full ML modules not available: {e}")
    st.info("Using fallback implementation. For full features, install: pip install seaborn matplotlib torch transformers scikit-learn plotly")
    
    # Try to import fallback modules
    try:
        from core.ml.fallback import create_fallback_ml_manager
        ML_AVAILABLE = True
        FALLBACK_MODE = True
    except ImportError as e2:
        st.error(f"Fallback modules also not available: {e2}")
        ML_AVAILABLE = False
        FALLBACK_MODE = False

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="ML & AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Machine Learning & AI")
st.markdown("Predictive analytics, sentiment analysis, and strategy optimization using ML/AI")

# Show mode indicator
if FALLBACK_MODE:
    st.warning("⚠️ Running in fallback mode. Some advanced features may be limited. Install full dependencies for complete functionality.")
else:
    st.success("✅ Full ML functionality available")

# Initialize session state
if 'ml_manager' not in st.session_state:
    if FALLBACK_MODE:
        st.session_state.ml_manager = create_fallback_ml_manager()
    else:
        st.session_state.ml_manager = create_ml_integration_manager()

# Get available tickers for dropdowns
@st.cache_data
def get_available_tickers():
    """Get available tickers from database."""
    try:
        tickers = st.session_state.ml_manager.get_available_tickers()
        return tickers
    except Exception as e:
        st.error(f"Error getting tickers: {e}")
        return []

available_tickers = get_available_tickers()

# Debug information
if st.checkbox("🔍 Show Debug Information", key="debug_info"):
    st.subheader("Debug Information")
    
    # Check database file
    import os
    db_exists = os.path.exists("stock_data.db")
    st.write(f"Database file exists: {db_exists}")
    
    if db_exists:
        try:
            import sqlite3
            conn = sqlite3.connect("stock_data.db")
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            st.write(f"Tables in database: {tables}")
            
            # Check companies table
            if 'companies' in tables:
                cursor.execute("SELECT COUNT(*) FROM companies")
                count = cursor.fetchone()[0]
                st.write(f"Companies count: {count}")
                
                # Get sample tickers
                cursor.execute("SELECT contract_code FROM companies LIMIT 10")
                sample_tickers = [row[0] for row in cursor.fetchall()]
                st.write(f"Sample tickers: {sample_tickers}")
            else:
                st.write("❌ Companies table not found!")
            
            conn.close()
        except Exception as e:
            st.write(f"❌ Database error: {e}")

if not ML_AVAILABLE:
    st.error("ML modules are not available. Please install required dependencies.")
    st.stop()

# Sidebar for configuration
st.sidebar.header("ML Configuration")

# Sentiment Analysis Configuration
st.sidebar.subheader("Sentiment Analysis")
sentiment_model = st.sidebar.selectbox(
    "Sentiment Model",
    ["cardiffnlp/twitter-roberta-base-sentiment-latest", "distilbert-base-uncased-finetuned-sst-2-english"],
    index=0
)
sentiment_confidence = st.sidebar.slider("Confidence Threshold", 0.0, 1.0, 0.7)

# Price Prediction Configuration
st.sidebar.subheader("Price Prediction")
prediction_model = st.sidebar.selectbox("Prediction Model", ["LSTM", "GRU"], index=0)
sequence_length = st.sidebar.slider("Sequence Length", 10, 100, 60)
hidden_size = st.sidebar.slider("Hidden Size", 32, 128, 50)
epochs = st.sidebar.slider("Epochs", 10, 200, 100)

# Clustering Configuration
st.sidebar.subheader("Stock Clustering")
clustering_algorithm = st.sidebar.selectbox("Algorithm", ["kmeans", "dbscan", "hierarchical"], index=0)
n_clusters = st.sidebar.slider("Number of Clusters", 2, 10, 5)

# Main content
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Sentiment Analysis",
    "🔮 Price Prediction", 
    "🎯 Strategy Optimization",
    "📈 Stock Clustering",
    "🧠 Reinforcement Learning",
    "🎭 Ensemble Methods"
])

with tab1:
    st.header("📊 News Sentiment Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Market Sentiment Overview")
        
        if st.button("Analyze Market Sentiment", key="sentiment_analyze"):
            with st.spinner("Analyzing market sentiment..."):
                try:
                    sentiment_result = st.session_state.ml_manager.analyze_market_sentiment()
                    
                    # Display sentiment metrics
                    col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
                    
                    with col_metric1:
                        st.metric(
                            "Overall Sentiment",
                            sentiment_result.get('overall_sentiment', 'Unknown').upper(),
                            delta=None
                        )
                    
                    with col_metric2:
                        st.metric(
                            "Confidence",
                            f"{sentiment_result.get('confidence', 0):.2%}",
                            delta=None
                        )
                    
                    with col_metric3:
                        st.metric(
                            "Positive Ratio",
                            f"{sentiment_result.get('positive_ratio', 0):.2%}",
                            delta=None
                        )
                    
                    with col_metric4:
                        st.metric(
                            "Total Articles",
                            sentiment_result.get('total_articles', 0),
                            delta=None
                        )
                    
                    # Sentiment distribution chart
                    if 'positive_ratio' in sentiment_result:
                        sentiment_data = {
                            'Sentiment': ['Positive', 'Negative', 'Neutral'],
                            'Percentage': [
                                sentiment_result.get('positive_ratio', 0),
                                sentiment_result.get('negative_ratio', 0),
                                sentiment_result.get('neutral_ratio', 0)
                            ]
                        }
                        
                        fig = px.pie(
                            pd.DataFrame(sentiment_data),
                            values='Percentage',
                            names='Sentiment',
                            title="Sentiment Distribution",
                            color_discrete_map={
                                'Positive': '#00ff00',
                                'Negative': '#ff0000',
                                'Neutral': '#808080'
                            }
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"Sentiment analysis failed: {e}")
    
    with col2:
        st.subheader("Configuration")
        st.info("Configure sentiment analysis parameters in the sidebar.")

with tab2:
    st.header("🔮 Price Prediction")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Predict Price Movement")
        
        # Symbol input with dropdown
        if available_tickers:
            symbol = st.selectbox(
                "Stock Symbol", 
                options=available_tickers,
                index=0 if available_tickers else 0,
                key="prediction_symbol"
            )
        else:
            symbol = st.text_input("Stock Symbol", value="SBER", key="prediction_symbol")
            st.warning("No tickers found in database. Please load data first.")
        
        if st.button("Predict Price Movement", key="price_predict"):
            with st.spinner("Making prediction using cached model..."):
                try:
                    prediction_result = st.session_state.ml_manager.predict_price_movement(symbol, '1d', 1)
                    
                    if 'error' in prediction_result:
                        st.error(f"Prediction failed: {prediction_result['error']}")
                    else:
                        # Display prediction
                        col_pred1, col_pred2, col_pred3 = st.columns(3)
                        
                        with col_pred1:
                            prediction = prediction_result.get('prediction', 0)
                            st.metric(
                                "Price Prediction",
                                f"{prediction:.4f}",
                                delta=f"{prediction:.2%}" if prediction != 0 else None
                            )
                        
                        with col_pred2:
                            confidence = prediction_result.get('confidence', 0)
                            st.metric(
                                "Confidence",
                                f"{confidence:.2%}",
                                delta=None
                            )
                        
                        with col_pred3:
                            rmse = prediction_result.get('model_metrics', {}).get('rmse', 0)
                            st.metric(
                                "RMSE",
                                f"{rmse:.4f}",
                                delta=None
                            )
                        
                        # Model performance metrics
                        if 'model_metrics' in prediction_result:
                            metrics = prediction_result['model_metrics']
                            
                            metrics_data = {
                                'Metric': ['MSE', 'MAE', 'RMSE'],
                                'Value': [
                                    metrics.get('mse', 0),
                                    metrics.get('mae', 0),
                                    metrics.get('rmse', 0)
                                ]
                            }
                            
                            fig = px.bar(
                                pd.DataFrame(metrics_data),
                                x='Metric',
                                y='Value',
                                title="Model Performance Metrics"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"Price prediction failed: {e}")
    
    with col2:
        st.subheader("Model Configuration")
        st.info(f"Model: {prediction_model}")
        st.info(f"Sequence Length: {sequence_length}")
        st.info(f"Hidden Size: {hidden_size}")
        st.info(f"Epochs: {epochs}")

with tab3:
    st.header("🎯 Strategy Optimization")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Optimize Trading Strategy")
        
        # Strategy parameters
        if available_tickers:
            opt_symbol = st.selectbox(
                "Stock Symbol", 
                options=available_tickers,
                index=0 if available_tickers else 0,
                key="optimization_symbol"
            )
        else:
            opt_symbol = st.text_input("Stock Symbol", value="SBER", key="optimization_symbol")
        strategy_type = st.selectbox(
            "Strategy Type",
            ["sma_crossover", "rsi", "macd", "combined"],
            key="strategy_type"
        )
        
        if st.button("Optimize Strategy", key="strategy_optimize"):
            with st.spinner("Running genetic algorithm optimization..."):
                try:
                    optimization_result = st.session_state.ml_manager.optimize_trading_strategy(
                        opt_symbol, strategy_type
                    )
                    
                    if 'error' in optimization_result:
                        st.error(f"Optimization failed: {optimization_result['error']}")
                    else:
                        # Display results
                        st.success("Strategy optimization completed!")
                        
                        # Best parameters
                        st.subheader("Best Parameters")
                        best_params = optimization_result.get('best_parameters', {})
                        for param, value in best_params.items():
                            st.write(f"**{param}**: {value:.4f}")
                        
                        # Performance metrics
                        col_perf1, col_perf2, col_perf3 = st.columns(3)
                        
                        with col_perf1:
                            fitness = optimization_result.get('best_fitness', 0)
                            st.metric(
                                "Best Fitness (Sharpe Ratio)",
                                f"{fitness:.4f}",
                                delta=None
                            )
                        
                        with col_perf2:
                            generations = optimization_result.get('generations', 0)
                            st.metric(
                                "Generations",
                                generations,
                                delta=None
                            )
                        
                        with col_perf3:
                            convergence = optimization_result.get('convergence')
                            st.metric(
                                "Convergence",
                                f"Gen {convergence}" if convergence else "Not reached",
                                delta=None
                            )
                        
                        # Fitness history chart
                        if 'fitness_history' in optimization_result:
                            fitness_history = optimization_result['fitness_history']
                            
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                y=fitness_history,
                                mode='lines',
                                name='Fitness',
                                line=dict(color='blue')
                            ))
                            fig.update_layout(
                                title="Fitness Evolution",
                                xaxis_title="Generation",
                                yaxis_title="Fitness (Sharpe Ratio)"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"Strategy optimization failed: {e}")
    
    with col2:
        st.subheader("Optimization Info")
        st.info(f"Strategy: {strategy_type}")
        st.info("Using Genetic Algorithm")
        st.info("Fitness: Sharpe Ratio")

with tab4:
    st.header("📈 Stock Clustering")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Cluster Stocks")
        
        # Stock symbols input
        if available_tickers:
            selected_tickers = st.multiselect(
                "Select Stock Symbols",
                options=available_tickers,
                default=available_tickers[:5] if len(available_tickers) >= 5 else available_tickers,
                key="clustering_symbols_multiselect"
            )
            symbols_input = "\n".join(selected_tickers) if selected_tickers else ""
        else:
            symbols_input = st.text_area(
                "Stock Symbols (one per line)",
                value="SBER\nGAZP\nLKOH\nNVTK\nROSN",
                key="clustering_symbols"
            )
        
        if st.button("Cluster Stocks", key="cluster_stocks"):
            with st.spinner("Performing stock clustering..."):
                try:
                    symbols = [s.strip() for s in symbols_input.split('\n') if s.strip()]
                    
                    clustering_result = st.session_state.ml_manager.cluster_stocks(symbols)
                    
                    if 'error' in clustering_result:
                        st.error(f"Clustering failed: {clustering_result['error']}")
                    else:
                        st.success("Stock clustering completed!")
                        
                        # Display cluster info
                        col_cluster1, col_cluster2, col_cluster3 = st.columns(3)
                        
                        with col_cluster1:
                            n_clusters = clustering_result.get('n_clusters', 0)
                            st.metric(
                                "Number of Clusters",
                                n_clusters,
                                delta=None
                            )
                        
                        with col_cluster2:
                            silhouette = clustering_result.get('silhouette_score', 0)
                            st.metric(
                                "Silhouette Score",
                                f"{silhouette:.4f}",
                                delta=None
                            )
                        
                        with col_cluster3:
                            st.metric(
                                "Algorithm",
                                clustering_algorithm.upper(),
                                delta=None
                            )
                        
                        # Cluster summary
                        if 'cluster_summary' in clustering_result:
                            cluster_summary = pd.DataFrame(clustering_result['cluster_summary'])
                            
                            st.subheader("Cluster Summary")
                            st.dataframe(cluster_summary, use_container_width=True)
                        
                        # Feature importance
                        if 'feature_importance' in clustering_result and clustering_result['feature_importance']:
                            importance_data = clustering_result['feature_importance']
                            
                            importance_df = pd.DataFrame(
                                list(importance_data.items()),
                                columns=['Feature', 'Importance']
                            ).sort_values('Importance', ascending=True)
                            
                            fig = px.bar(
                                importance_df,
                                x='Importance',
                                y='Feature',
                                orientation='h',
                                title="Feature Importance"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"Stock clustering failed: {e}")
    
    with col2:
        st.subheader("Clustering Info")
        st.info(f"Algorithm: {clustering_algorithm}")
        st.info(f"Clusters: {n_clusters}")
        st.info("Features: Price, Volume, Technical Indicators")

with tab5:
    st.header("🧠 Reinforcement Learning")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Train RL Agent")
        
        if available_tickers:
            rl_symbol = st.selectbox(
                "Stock Symbol", 
                options=available_tickers,
                index=0 if available_tickers else 0,
                key="rl_symbol"
            )
        else:
            rl_symbol = st.text_input("Stock Symbol", value="SBER", key="rl_symbol")
        episodes = st.slider("Training Episodes", 100, 2000, 1000, key="rl_episodes")
        
        if st.button("Train RL Agent", key="train_rl"):
            with st.spinner("Training reinforcement learning agent..."):
                try:
                    # Update RL config
                    st.session_state.ml_manager.rl_config.episodes = episodes
                    
                    training_result = st.session_state.ml_manager.train_rl_agent(rl_symbol)
                    
                    if 'error' in training_result:
                        st.error(f"RL training failed: {training_result['error']}")
                    else:
                        st.success("RL agent training completed!")
                        
                        # Display results
                        col_rl1, col_rl2, col_rl3 = st.columns(3)
                        
                        with col_rl1:
                            final_reward = training_result.get('final_reward', 0)
                            st.metric(
                                "Final Reward",
                                f"{final_reward:.4f}",
                                delta=None
                            )
                        
                        with col_rl2:
                            portfolio_value = training_result.get('final_portfolio_value', 0)
                            st.metric(
                                "Final Portfolio Value",
                                f"${portfolio_value:,.2f}",
                                delta=None
                            )
                        
                        with col_rl3:
                            portfolio_return = training_result.get('portfolio_return', 0)
                            st.metric(
                                "Portfolio Return",
                                f"{portfolio_return:.2%}",
                                delta=None
                            )
                        
                        # Training progress
                        if 'training_scores' in training_result:
                            scores = training_result['training_scores']
                            
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                y=scores,
                                mode='lines',
                                name='Training Scores',
                                line=dict(color='green')
                            ))
                            fig.update_layout(
                                title="Training Progress",
                                xaxis_title="Episode",
                                yaxis_title="Score"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"RL training failed: {e}")
    
    with col2:
        st.subheader("RL Configuration")
        st.info(f"Episodes: {episodes}")
        st.info("Algorithm: DQN")
        st.info("Actions: Buy, Hold, Sell")

with tab6:
    st.header("🎭 Ensemble Methods")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Ensemble Prediction")
        
        if available_tickers:
            ensemble_symbol = st.selectbox(
                "Stock Symbol", 
                options=available_tickers,
                index=0 if available_tickers else 0,
                key="ensemble_symbol"
            )
        else:
            ensemble_symbol = st.text_input("Stock Symbol", value="SBER", key="ensemble_symbol")
        ensemble_method = st.selectbox(
            "Ensemble Method",
            ["voting_hard", "voting_soft", "stacking_linear", "stacking_nonlinear"],
            key="ensemble_method"
        )
        
        if st.button("Create Ensemble Prediction", key="ensemble_predict"):
            with st.spinner("Creating ensemble prediction..."):
                try:
                    ensemble_result = st.session_state.ml_manager.create_ensemble_prediction(ensemble_symbol)
                    
                    if 'error' in ensemble_result:
                        st.error(f"Ensemble prediction failed: {ensemble_result['error']}")
                    else:
                        st.success("Ensemble prediction completed!")
                        
                        # Display prediction
                        col_ens1, col_ens2, col_ens3 = st.columns(3)
                        
                        with col_ens1:
                            prediction = ensemble_result.get('prediction', 0)
                            st.metric(
                                "Ensemble Prediction",
                                f"{prediction:.4f}",
                                delta=f"{prediction:.2%}" if prediction != 0 else None
                            )
                        
                        with col_ens2:
                            r2 = ensemble_result.get('metrics', {}).get('r2', 0)
                            st.metric(
                                "R² Score",
                                f"{r2:.4f}",
                                delta=None
                            )
                        
                        with col_ens3:
                            rmse = ensemble_result.get('metrics', {}).get('rmse', 0)
                            st.metric(
                                "RMSE",
                                f"{rmse:.4f}",
                                delta=None
                            )
                        
                        # Model metrics
                        if 'metrics' in ensemble_result:
                            metrics = ensemble_result['metrics']
                            
                            metrics_data = {
                                'Metric': ['MSE', 'MAE', 'RMSE', 'R²'],
                                'Value': [
                                    metrics.get('mse', 0),
                                    metrics.get('mae', 0),
                                    metrics.get('rmse', 0),
                                    metrics.get('r2', 0)
                                ]
                            }
                            
                            fig = px.bar(
                                pd.DataFrame(metrics_data),
                                x='Metric',
                                y='Value',
                                title="Ensemble Model Performance"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Feature importance
                        if 'feature_importance' in ensemble_result and ensemble_result['feature_importance']:
                            importance_data = ensemble_result['feature_importance']
                            
                            importance_df = pd.DataFrame(
                                list(importance_data.items()),
                                columns=['Feature', 'Importance']
                            ).sort_values('Importance', ascending=True)
                            
                            fig = px.bar(
                                importance_df,
                                x='Importance',
                                y='Feature',
                                orientation='h',
                                title="Feature Importance (Ensemble)"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"Ensemble prediction failed: {e}")
    
    with col2:
        st.subheader("Ensemble Info")
        st.info(f"Method: {ensemble_method}")
        st.info("Base Models: Linear, Ridge, Random Forest, Gradient Boosting")
        st.info("Meta Model: Linear Regression")

# Footer
st.markdown("---")
st.markdown("**ML & AI Module** - Advanced machine learning capabilities for trading strategy optimization and market analysis.")
