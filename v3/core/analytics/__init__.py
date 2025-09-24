"""Analytics helpers (metrics, optimisation, backtesting)."""

from .metrics import StrategyMetrics, TradingCosts, compute_strategy_metrics, extract_trades
from .optimisation import (
    CrossValidationResult,
    OptimizationConstraint,
    OptimizationResult,
    build_parameter_grid,
    cross_validate_parameters,
    cross_validation_results_to_frame,
    optimization_results_to_frame,
    walk_forward_optimize,
)
from .scoring import ScoringConfig, ScoreWeights, compute_signal_scores
from .risk import TradeRecord, apply_risk_management, simulate_trades

__all__ = [
    "ScoringConfig",
    "ScoreWeights",
    "StrategyMetrics",
    "TradeRecord",
    "TradingCosts",
    "compute_strategy_metrics",
    "extract_trades",
    "OptimizationConstraint",
    "OptimizationResult",
    "CrossValidationResult",
    "build_parameter_grid",
    "cross_validate_parameters",
    "walk_forward_optimize",
]
