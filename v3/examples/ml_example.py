"""Example usage of ML modules for trading strategy optimization."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Import ML modules
from core.ml import (
    LSTMPredictor, ModelConfig,
    NewsSentimentAnalyzer, SentimentConfig,
    StockClusterer, ClusteringConfig,
    GeneticOptimizer, GeneticConfig, TradingStrategyFitness,
    TradingAgent, RLConfig,
    EnsemblePredictor, EnsembleConfig
)
from core.ml.integration import create_ml_integration_manager

logger = logging.getLogger(__name__)


def create_sample_data():
    """Create sample stock data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    n_days = len(dates)
    
    # Generate realistic stock data
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, n_days)  # Daily returns
    prices = 100 * np.cumprod(1 + returns)  # Starting price $100
    
    # Generate OHLCV data
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.005, n_days)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, n_days))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, n_days))),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, n_days)
    })
    
    # Add technical indicators
    data['sma_20'] = data['close'].rolling(20).mean()
    data['sma_50'] = data['close'].rolling(50).mean()
    data['ema_12'] = data['close'].ewm(span=12).mean()
    data['ema_26'] = data['close'].ewm(span=26).mean()
    
    # RSI calculation
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD calculation
    data['macd'] = data['ema_12'] - data['ema_26']
    
    # Bollinger Bands
    data['bb_middle'] = data['close'].rolling(20).mean()
    bb_std = data['close'].rolling(20).std()
    data['bb_upper'] = data['bb_middle'] + (bb_std * 2)
    data['bb_lower'] = data['bb_middle'] - (bb_std * 2)
    
    # ATR calculation
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    data['atr'] = true_range.rolling(14).mean()
    
    # Stochastic Oscillator
    low_14 = data['low'].rolling(14).min()
    high_14 = data['high'].rolling(14).max()
    data['stoch_k'] = 100 * ((data['close'] - low_14) / (high_14 - low_14))
    data['stoch_d'] = data['stoch_k'].rolling(3).mean()
    
    return data.fillna(method='ffill').fillna(0)


def example_price_prediction():
    """Example of price prediction using LSTM."""
    print("=== Price Prediction Example ===")
    
    # Create sample data
    data = create_sample_data()
    
    # Configure model
    config = ModelConfig(
        sequence_length=30,
        hidden_size=50,
        epochs=50,
        batch_size=32
    )
    
    # Create predictor
    predictor = LSTMPredictor(config)
    
    # Train model
    print("Training LSTM model...")
    training_result = predictor.train(data)
    print(f"Training completed. Final validation loss: {training_result['final_val_loss']:.6f}")
    
    # Make prediction
    prediction_result = predictor.predict(data.tail(100))
    print(f"Prediction confidence: {prediction_result.confidence:.2%}")
    print(f"RMSE: {prediction_result.rmse:.4f}")
    
    return prediction_result


def example_sentiment_analysis():
    """Example of sentiment analysis."""
    print("\n=== Sentiment Analysis Example ===")
    
    # Create sample news data
    news_data = pd.DataFrame({
        'title': [
            'Stock market reaches new highs',
            'Company reports disappointing earnings',
            'Positive outlook for technology sector',
            'Market volatility concerns investors',
            'Strong economic growth indicators'
        ],
        'content': [
            'The stock market has reached new all-time highs today, driven by strong corporate earnings and positive economic data.',
            'The company reported disappointing quarterly earnings, missing analyst expectations by a significant margin.',
            'Analysts are optimistic about the technology sector, citing strong innovation and market demand.',
            'Investors are concerned about increased market volatility and potential economic headwinds.',
            'Recent economic indicators show strong growth across multiple sectors, boosting investor confidence.'
        ],
        'date': pd.date_range(start='2023-12-01', periods=5, freq='D')
    })
    
    # Configure sentiment analyzer
    config = SentimentConfig(
        model_name="cardiffnlp/twitter-roberta-base-sentiment-latest",
        confidence_threshold=0.7
    )
    
    # Create analyzer
    analyzer = NewsSentimentAnalyzer(config)
    
    # Analyze sentiment
    print("Analyzing news sentiment...")
    sentiment_result = analyzer.get_market_sentiment(news_data)
    
    print(f"Overall sentiment: {sentiment_result['overall_sentiment']}")
    print(f"Confidence: {sentiment_result['confidence']:.2%}")
    print(f"Positive ratio: {sentiment_result['positive_ratio']:.2%}")
    print(f"Total articles: {sentiment_result['total_articles']}")
    
    return sentiment_result


def example_stock_clustering():
    """Example of stock clustering."""
    print("\n=== Stock Clustering Example ===")
    
    # Create sample data for multiple stocks
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    all_data = []
    
    for symbol in symbols:
        data = create_sample_data()
        data['symbol'] = symbol
        all_data.append(data)
    
    combined_data = pd.concat(all_data, ignore_index=True)
    
    # Configure clustering
    config = ClusteringConfig(
        algorithm='kmeans',
        n_clusters=3,
        scaler='standard'
    )
    
    # Create clusterer
    clusterer = StockClusterer(config)
    
    # Perform clustering
    print("Performing stock clustering...")
    clustering_result = clusterer.fit(combined_data)
    
    print(f"Number of clusters: {clustering_result.n_clusters}")
    print(f"Silhouette score: {clustering_result.silhouette_score:.4f}")
    
    # Get cluster summary
    cluster_summary = clusterer.get_cluster_summary(clustering_result, combined_data)
    print("\nCluster Summary:")
    print(cluster_summary[['cluster_id', 'size', 'avg_close', 'avg_volume']].to_string())
    
    return clustering_result


def example_genetic_optimization():
    """Example of genetic algorithm optimization."""
    print("\n=== Genetic Optimization Example ===")
    
    # Create sample data
    data = create_sample_data()
    
    # Define parameter space
    parameters = {
        'sma_short': (5, 30),
        'sma_long': (20, 100),
        'rsi_threshold': (20, 40),
        'macd_threshold': (0.001, 0.01)
    }
    
    # Create fitness function
    fitness_function = TradingStrategyFitness(data, 'sharpe_ratio')
    
    # Configure genetic algorithm
    config = GeneticConfig(
        population_size=50,
        generations=20,
        mutation_rate=0.1,
        crossover_rate=0.8
    )
    
    # Create optimizer
    optimizer = GeneticOptimizer(config, fitness_function)
    
    # Run optimization
    print("Running genetic algorithm optimization...")
    optimization_result = optimizer.optimize(parameters, data)
    
    print(f"Best fitness (Sharpe ratio): {optimization_result.best_fitness:.4f}")
    print(f"Generations: {optimization_result.generation}")
    print("Best parameters:")
    for param, value in optimization_result.best_individual.items():
        print(f"  {param}: {value:.4f}")
    
    return optimization_result


def example_ensemble_prediction():
    """Example of ensemble prediction."""
    print("\n=== Ensemble Prediction Example ===")
    
    # Create sample data
    data = create_sample_data()
    
    # Prepare features
    feature_columns = ['open', 'high', 'low', 'close', 'volume', 'sma_20', 'sma_50', 'rsi', 'macd']
    X = data[feature_columns].fillna(method='ffill').fillna(0)
    y = data['close'].pct_change().fillna(0)
    
    # Configure ensemble
    config = EnsembleConfig(
        base_models=['linear', 'ridge', 'rf', 'gb'],
        stacking_method='linear',
        meta_model='linear'
    )
    
    # Create ensemble
    ensemble = EnsemblePredictor(config)
    
    # Fit ensemble
    print("Training ensemble model...")
    ensemble.fit(X, y)
    
    # Make prediction
    prediction = ensemble.predict(X.tail(10))
    
    # Evaluate performance
    metrics = ensemble.evaluate(X, y)
    
    print(f"Ensemble prediction (last 10 days): {prediction[-1]:.4f}")
    print(f"R² score: {metrics['r2']:.4f}")
    print(f"RMSE: {metrics['rmse']:.4f}")
    
    return metrics


def example_ml_integration():
    """Example of ML integration manager."""
    print("\n=== ML Integration Example ===")
    
    # Create ML integration manager
    ml_manager = create_ml_integration_manager()
    
    # Initialize components
    ml_manager.initialize_components()
    
    # Get comprehensive recommendations
    print("Getting ML recommendations...")
    recommendations = ml_manager.get_ml_recommendations('AAPL')
    
    print(f"Overall recommendation: {recommendations['recommendation']}")
    print(f"Overall score: {recommendations['overall_score']:.4f}")
    
    if 'sentiment' in recommendations:
        sentiment = recommendations['sentiment']
        print(f"Market sentiment: {sentiment.get('overall_sentiment', 'Unknown')}")
    
    if 'price_prediction' in recommendations:
        prediction = recommendations['price_prediction']
        if 'prediction' in prediction:
            print(f"Price prediction: {prediction['prediction']:.4f}")
    
    return recommendations


def main():
    """Run all ML examples."""
    print("Machine Learning Examples for Trading Strategy Optimization")
    print("=" * 60)
    
    try:
        # Run examples
        example_price_prediction()
        example_sentiment_analysis()
        example_stock_clustering()
        example_genetic_optimization()
        example_ensemble_prediction()
        example_ml_integration()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        logger.error(f"Example execution failed: {e}")


if __name__ == "__main__":
    main()
