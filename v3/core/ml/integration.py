"""Integration module for ML with existing analytics and news pipeline."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
import logging
from datetime import datetime, timedelta

from ..analytics import StrategyMetrics, compute_strategy_metrics
from ..news_pipeline import NewsBatchProcessor
from .predictive_models import LSTMPredictor, GRUPredictor, ModelConfig, create_predictor
from .sentiment_analysis import NewsSentimentAnalyzer, SentimentConfig
from .clustering import StockClusterer, ClusteringConfig, create_clusterer
from .genetic_optimization import GeneticOptimizer, GeneticConfig, TradingStrategyFitness
from .reinforcement_learning import TradingAgent, RLEnvironment, RLConfig
from .ensemble_methods import EnsemblePredictor, EnsembleConfig
from .model_manager import ml_model_manager
from .storage import ml_storage
from .training_scheduler import ml_training_scheduler

logger = logging.getLogger(__name__)


class MLIntegrationManager:
    """Manager for integrating ML capabilities with existing modules."""
    
    def __init__(self, database_manager=None, news_processor=None):
        self.database_manager = database_manager
        self.news_processor = news_processor or NewsBatchProcessor()
        
        # ML components
        self.sentiment_analyzer = None
        self.price_predictor = None
        self.stock_clusterer = None
        self.genetic_optimizer = None
        self.rl_agent = None
        self.ensemble_predictor = None
        
        # Configuration
        self.sentiment_config = SentimentConfig()
        self.model_config = ModelConfig()
        self.clustering_config = ClusteringConfig()
        self.genetic_config = GeneticConfig()
        self.rl_config = RLConfig()
        self.ensemble_config = EnsembleConfig()
    
    def initialize_components(self):
        """Initialize all ML components."""
        try:
            # Initialize sentiment analyzer
            self.sentiment_analyzer = NewsSentimentAnalyzer(self.sentiment_config)
            logger.info("Sentiment analyzer initialized")
            
            # Initialize other components as needed
            logger.info("ML components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ML components: {e}")
    
    def analyze_market_sentiment(self, days_back: int = 7) -> Dict[str, Any]:
        """Analyze market sentiment from recent news."""
        if not self.sentiment_analyzer:
            self.initialize_components()
        
        try:
            # Try to get news data from database first
            news_data = self._get_news_data_from_db(days_back)
            
            if news_data.empty:
                # Fallback to dummy data for demonstration
                logger.warning("No news data available, using dummy data for sentiment analysis")
                news_data = pd.DataFrame({
                    'title': [
                        'Stock market reaches new highs',
                        'Company reports strong earnings',
                        'Economic indicators show growth',
                        'Market volatility concerns investors',
                        'Positive outlook for technology sector'
                    ],
                    'content': [
                        'The stock market has reached new all-time highs today, driven by strong corporate earnings and positive economic data.',
                        'The company reported strong quarterly earnings, exceeding analyst expectations by a significant margin.',
                        'Recent economic indicators show strong growth across multiple sectors, boosting investor confidence.',
                        'Investors are concerned about increased market volatility and potential economic headwinds.',
                        'Analysts are optimistic about the technology sector, citing strong innovation and market demand.'
                    ],
                    'date': pd.date_range(start=datetime.now() - timedelta(days=days_back), periods=5, freq='D')
                })
            
            # Analyze sentiment
            sentiment_result = self.sentiment_analyzer.get_market_sentiment(news_data)
            
            return sentiment_result
        
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                'overall_sentiment': 'neutral',
                'confidence': 0.0,
                'total_articles': 0,
                'error': str(e)
            }
    
    def predict_price_movement(self, symbol: str, days_ahead: int = 1, timeframe: str = '1d') -> Dict[str, Any]:
        """Predict price movement for a given symbol using new ML system."""
        try:
            # Используем новый ML менеджер
            return ml_model_manager.predict_price_movement(symbol, timeframe, days_ahead)
        
        except Exception as e:
            logger.error(f"Price prediction failed: {e}")
            return {'error': str(e)}
    
    def cluster_stocks(self, symbols: List[str], timeframe: str = '1d') -> Dict[str, Any]:
        """Cluster stocks based on their characteristics using new ML system."""
        try:
            # Используем новый ML менеджер
            return ml_model_manager.cluster_stocks(symbols, timeframe)
        
        except Exception as e:
            logger.error(f"Stock clustering failed: {e}")
            return {'error': str(e)}
    
    def optimize_trading_strategy(self, symbol: str, strategy_type: str = 'combined') -> Dict[str, Any]:
        """Optimize trading strategy using genetic algorithms."""
        try:
            # Get historical data
            historical_data = self._get_stock_data_from_db(symbol)
            
            if historical_data.empty:
                return {'error': f'No historical data available for {symbol}'}
            
            # Define parameter space
            from .genetic_optimization import create_parameter_space
            parameters = create_parameter_space(strategy_type)
            
            # Create fitness function
            fitness_function = TradingStrategyFitness(historical_data, 'sharpe_ratio')
            
            # Create optimizer
            if not self.genetic_optimizer:
                self.genetic_optimizer = GeneticOptimizer(self.genetic_config, fitness_function)
            
            # Run optimization
            optimization_result = self.genetic_optimizer.optimize(parameters, historical_data)
            
            return {
                'best_parameters': optimization_result.best_individual,
                'best_fitness': optimization_result.best_fitness,
                'generations': optimization_result.generation,
                'convergence': optimization_result.convergence_generation,
                'fitness_history': optimization_result.fitness_history[-10:]  # Last 10 generations
            }
        
        except Exception as e:
            logger.error(f"Strategy optimization failed: {e}")
            return {'error': str(e)}
    
    def train_rl_agent(self, symbol: str) -> Dict[str, Any]:
        """Train reinforcement learning agent for trading."""
        try:
            # Get historical data
            historical_data = self._get_stock_data_from_db(symbol)
            
            if historical_data.empty:
                return {'error': f'No historical data available for {symbol}'}
            
            # Create RL environment
            rl_env = RLEnvironment(historical_data, self.rl_config)
            
            # Create agent
            if not self.rl_agent:
                from .reinforcement_learning import create_trading_agent
                self.rl_agent = create_trading_agent(self.rl_config)
            
            # Train agent
            training_results = rl_env.train_agent(self.rl_agent)
            
            # Evaluate agent
            evaluation_results = rl_env.evaluate_agent(self.rl_agent)
            
            return {
                'training_scores': training_results['scores'][-10:],  # Last 10 episodes
                'portfolio_values': training_results['portfolio_values'][-10:],
                'final_reward': evaluation_results['total_reward'],
                'final_portfolio_value': evaluation_results['final_portfolio_value'],
                'portfolio_return': evaluation_results['portfolio_return']
            }
        
        except Exception as e:
            logger.error(f"RL training failed: {e}")
            return {'error': str(e)}
    
    def create_ensemble_prediction(self, symbol: str) -> Dict[str, Any]:
        """Create ensemble prediction combining multiple models."""
        try:
            # Get historical data
            historical_data = self._get_stock_data_from_db(symbol)
            
            if historical_data.empty:
                return {'error': f'No historical data available for {symbol}'}
            
            # Prepare features
            feature_columns = ['open', 'high', 'low', 'close', 'volume']
            technical_indicators = ['sma_20', 'sma_50', 'rsi', 'macd']
            available_indicators = [col for col in technical_indicators if col in historical_data.columns]
            feature_columns.extend(available_indicators)
            
            X = historical_data[feature_columns].ffill().fillna(0)
            y = historical_data['close'].pct_change().fillna(0)
            
            # Create ensemble
            if not self.ensemble_predictor:
                self.ensemble_predictor = EnsemblePredictor(self.ensemble_config)
            
            # Fit ensemble
            self.ensemble_predictor.fit(X, y)
            
            # Make prediction
            prediction = self.ensemble_predictor.predict(X.tail(1))
            
            # Evaluate performance
            metrics = self.ensemble_predictor.evaluate(X, y)
            
            return {
                'prediction': prediction[0] if len(prediction) > 0 else 0,
                'metrics': metrics,
                'feature_importance': self.ensemble_predictor.get_feature_importance()
            }
        
        except Exception as e:
            logger.error(f"Ensemble prediction failed: {e}")
            return {'error': str(e)}
    
    def _get_news_data_from_db(self, days_back: int = 7) -> pd.DataFrame:
        """Get news data from database for sentiment analysis."""
        try:
            import sqlite3
            from pathlib import Path
            
            db_path = "stock_data.db"
            if not Path(db_path).exists():
                return pd.DataFrame()
            
            conn = sqlite3.connect(db_path)
            
            # Check for news-related tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%news%' OR name LIKE '%article%')")
            news_tables = cursor.fetchall()
            
            if not news_tables:
                conn.close()
                return pd.DataFrame()
            
            # Use the first available news table
            news_table = news_tables[0][0]
            logger.info(f"Using news table: {news_table}")
            
            # Log available columns
            cursor.execute(f"PRAGMA table_info({news_table})")
            columns = [col[1] for col in cursor.fetchall()]
            logger.info(f"Available columns in {news_table}: {columns}")
            
            # Get news data - adapt query based on table structure
            if 'articles' in news_table.lower():
                # For articles table - check available columns first
                cursor.execute(f"PRAGMA table_info({news_table})")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Build query based on available columns
                select_parts = []
                if 'title' in columns:
                    select_parts.append('title')
                else:
                    select_parts.append('NULL as title')
                
                if 'content' in columns:
                    select_parts.append('content')
                elif 'text' in columns:
                    select_parts.append('text as content')
                elif 'body' in columns:
                    select_parts.append('body as content')
                else:
                    select_parts.append('NULL as content')
                
                if 'created_at' in columns:
                    select_parts.append('created_at as date')
                elif 'date' in columns:
                    select_parts.append('date')
                elif 'published_at' in columns:
                    select_parts.append('published_at as date')
                else:
                    select_parts.append('NULL as date')
                
                # Build WHERE clause based on available date columns
                date_where = ""
                if 'created_at' in columns:
                    date_where = f"WHERE created_at >= date('now', '-{days_back} days')"
                elif 'date' in columns:
                    date_where = f"WHERE date >= date('now', '-{days_back} days')"
                elif 'published_at' in columns:
                    date_where = f"WHERE published_at >= date('now', '-{days_back} days')"
                
                # Build ORDER BY clause
                order_by = ""
                if 'created_at' in columns:
                    order_by = "ORDER BY created_at DESC"
                elif 'date' in columns:
                    order_by = "ORDER BY date DESC"
                elif 'published_at' in columns:
                    order_by = "ORDER BY published_at DESC"
                
                query = f"""
                    SELECT 
                        {', '.join(select_parts)}
                    FROM {news_table}
                    {date_where}
                    {order_by}
                    LIMIT 100
                """
            else:
                # For other news tables
                query = """
                    SELECT 
                        title,
                        content,
                        date
                    FROM {}
                    WHERE date >= date('now', '-{} days')
                    ORDER BY date DESC
                    LIMIT 100
                """.format(news_table, days_back)
            
            try:
                df = pd.read_sql_query(query, conn)
                conn.close()
                return df
            except Exception as e:
                logger.warning(f"News query failed: {e}")
                conn.close()
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Failed to get news data: {e}")
            return pd.DataFrame()
    
    def _get_stock_data_from_db(self, symbol: str) -> pd.DataFrame:
        """Get stock data from database for a given symbol."""
        try:
            import sqlite3
            from pathlib import Path
            
            db_path = "stock_data.db"
            if not Path(db_path).exists():
                logger.warning(f"Database file not found: {db_path}")
                return pd.DataFrame()
            
            conn = sqlite3.connect(db_path)
            
            # Get stock data
            query = """
                SELECT 
                    dd.date,
                    dd.open,
                    dd.high,
                    dd.low,
                    dd.close,
                    dd.volume
                FROM daily_data dd
                JOIN companies c ON dd.company_id = c.id
                WHERE c.contract_code = ?
                ORDER BY dd.date
            """
            
            df = pd.read_sql_query(query, conn, params=(symbol,))
            conn.close()
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                
                # Add some basic technical indicators
                df['sma_20'] = df['close'].rolling(20).mean()
                df['sma_50'] = df['close'].rolling(50).mean()
                df['ema_12'] = df['close'].ewm(span=12).mean()
                df['ema_26'] = df['close'].ewm(span=26).mean()
                
                # RSI calculation
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))
                
                # MACD calculation
                df['macd'] = df['ema_12'] - df['ema_26']
                
                # Bollinger Bands
                df['bb_middle'] = df['close'].rolling(20).mean()
                bb_std = df['close'].rolling(20).std()
                df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
                df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            return df.ffill().fillna(0)
            
        except Exception as e:
            logger.error(f"Failed to get stock data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_available_tickers(self) -> List[str]:
        """Get list of available tickers from database."""
        try:
            import sqlite3
            from pathlib import Path
            
            db_path = "stock_data.db"
            if not Path(db_path).exists():
                logger.warning(f"Database file not found: {db_path}")
                return []
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if companies table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
            if not cursor.fetchone():
                logger.warning("Companies table not found in database")
                conn.close()
                return []
            
            # Get tickers
            cursor.execute("SELECT DISTINCT contract_code FROM companies ORDER BY contract_code")
            tickers = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"Found {len(tickers)} tickers in database")
            conn.close()
            return tickers
                
        except Exception as e:
            logger.error(f"Failed to get tickers: {e}")
            return []
    
    def get_ml_recommendations(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive ML-based recommendations for a symbol."""
        recommendations = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'sentiment': self.analyze_market_sentiment(),
            'price_prediction': self.predict_price_movement(symbol),
            'strategy_optimization': self.optimize_trading_strategy(symbol),
            'ensemble_prediction': self.create_ensemble_prediction(symbol)
        }
        
        # Calculate overall recommendation score
        score = 0
        factors = 0
        
        # Sentiment factor
        if 'sentiment' in recommendations and 'overall_sentiment' in recommendations['sentiment']:
            sentiment = recommendations['sentiment']['overall_sentiment']
            if sentiment == 'positive':
                score += 1
            elif sentiment == 'negative':
                score -= 1
            factors += 1
        
        # Price prediction factor
        if 'price_prediction' in recommendations and 'prediction' in recommendations['price_prediction']:
            prediction = recommendations['price_prediction']['prediction']
            if prediction > 0.01:  # 1% positive prediction
                score += 1
            elif prediction < -0.01:  # 1% negative prediction
                score -= 1
            factors += 1
        
        # Strategy optimization factor
        if 'strategy_optimization' in recommendations and 'best_fitness' in recommendations['strategy_optimization']:
            fitness = recommendations['strategy_optimization']['best_fitness']
            if fitness > 1.0:  # Good Sharpe ratio
                score += 1
            elif fitness < 0.5:  # Poor Sharpe ratio
                score -= 1
            factors += 1
        
        # Calculate final score
        if factors > 0:
            final_score = score / factors
            if final_score > 0.3:
                recommendation = 'BUY'
            elif final_score < -0.3:
                recommendation = 'SELL'
            else:
                recommendation = 'HOLD'
        else:
            final_score = 0
            recommendation = 'HOLD'
        
        recommendations['overall_score'] = final_score
        recommendations['recommendation'] = recommendation
        
        return recommendations


def create_ml_integration_manager(database_manager=None, news_processor=None) -> MLIntegrationManager:
    """Factory function to create ML integration manager."""
    return MLIntegrationManager(database_manager, news_processor)
