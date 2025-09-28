"""Machine Learning package for predictive analytics and strategy optimization."""

# Try to import full ML modules, fallback to basic implementations if not available
try:
    from .predictive_models import (
        LSTMPredictor,
        GRUPredictor,
        PricePredictor,
        PredictionResult,
        ModelConfig,
    )
    from .sentiment_analysis import (
        NewsSentimentAnalyzer,
        SentimentResult,
        SentimentConfig,
    )
    from .clustering import (
        StockClusterer,
        ClusteringResult,
        ClusteringConfig,
    )
    from .genetic_optimization import (
        GeneticOptimizer,
        OptimizationResult,
        GeneticConfig,
    )
    from .reinforcement_learning import (
        TradingAgent,
        RLEnvironment,
        RLConfig,
    )
    from .ensemble_methods import (
        EnsemblePredictor,
        EnsembleConfig,
        VotingEnsemble,
        StackingEnsemble,
    )
    from .integration import create_ml_integration_manager
    from .fallback import create_fallback_ml_manager
    FULL_ML_AVAILABLE = True
except ImportError as e:
    # Import fallback modules
    from .fallback import (
        FallbackPredictor as LSTMPredictor,
        FallbackModelConfig as ModelConfig,
        FallbackPredictionResult as PredictionResult,
        FallbackSentimentAnalyzer as NewsSentimentAnalyzer,
        create_fallback_ml_manager as create_ml_integration_manager,
        create_fallback_ml_manager,
    )
    FULL_ML_AVAILABLE = False

__all__ = [
    # Predictive models
    "LSTMPredictor",
    "GRUPredictor", 
    "PricePredictor",
    "PredictionResult",
    "ModelConfig",
    # Sentiment analysis
    "NewsSentimentAnalyzer",
    "SentimentResult",
    "SentimentConfig",
    # Clustering
    "StockClusterer",
    "ClusteringResult",
    "ClusteringConfig",
    # Genetic optimization
    "GeneticOptimizer",
    "OptimizationResult",
    "GeneticConfig",
    # Reinforcement learning
    "TradingAgent",
    "RLEnvironment",
    "RLConfig",
    # Ensemble methods
    "EnsemblePredictor",
    "EnsembleConfig",
    "VotingEnsemble",
    "StackingEnsemble",
    # ML managers
    "create_ml_integration_manager",
    "create_fallback_ml_manager",
]
