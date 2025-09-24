from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

import pandas as pd

from core.config import IndicatorParameters, ResolvedIndicatorProfile

from .metrics import StrategyMetrics, TradingCosts, compute_strategy_metrics, extract_trades


@dataclass(frozen=True)
class OptimizationConstraint:
    min_trades: int = 5
    min_win_rate: float = 0.3
    max_win_rate: float = 0.9
    min_profit_factor: float = 0.9
    max_drawdown: float = -0.8
    min_cagr: float = 0.0

    def satisfied(self, metrics: StrategyMetrics) -> bool:
        if metrics.total_trades < self.min_trades:
            return False
        if metrics.win_rate < self.min_win_rate or metrics.win_rate > self.max_win_rate:
            return False
        if metrics.profit_factor < self.min_profit_factor:
            return False
        if metrics.max_drawdown < self.max_drawdown:
            return False
        if metrics.cagr < self.min_cagr:
            return False
        return True


@dataclass(frozen=True)
class OptimizationResult:
    window_index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    params: IndicatorParameters
    train_metrics: StrategyMetrics
    test_metrics: StrategyMetrics
    objective_value: float
    contract_code: str
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CrossValidationResult:
    params: IndicatorParameters
    fold_metrics: Sequence[StrategyMetrics]
    avg_objective: float
    contract_code: str
    metadata: Dict[str, object] = field(default_factory=dict)


def build_parameter_grid(
    base_params: IndicatorParameters,
    grid: Mapping[str, Iterable[float]],
) -> List[IndicatorParameters]:
    keys = list(grid.keys())
    combinations = list(product(*[grid[k] for k in keys]))
    results: List[IndicatorParameters] = []
    for combo in combinations:
        overrides = {k: combo[idx] for idx, k in enumerate(keys)}
        results.append(base_params.merge(overrides))
    return results


def _evaluate_candidate(
    data: pd.DataFrame,
    contract_code: str,
    profile: ResolvedIndicatorProfile,
    params: IndicatorParameters,
    *,
    profit_col: str,
    exit_col: str,
    costs: TradingCosts,
) -> StrategyMetrics:
    from core.indicators.service import calculate_technical_indicators

    enriched = calculate_technical_indicators(
        data,
        contract_code=contract_code,
        asset_class=profile.asset_class,
        timeframe=profile.timeframe,
        volatility=profile.volatility,
        indicator_params=params,
    )
    trades = extract_trades(enriched, profit_col=profit_col, exit_date_col=exit_col)
    return compute_strategy_metrics(trades, costs=costs)


def walk_forward_optimize(
    data: pd.DataFrame,
    contract_code: str,
    profile: ResolvedIndicatorProfile,
    parameter_grid: Mapping[str, Iterable[float]],
    *,
    profit_col: str,
    exit_col: str,
    costs: Optional[TradingCosts] = None,
    constraints: Optional[OptimizationConstraint] = None,
    train_periods: int = 252,
    test_periods: int = 63,
    step: Optional[int] = None,
    objective: str = "sharpe",
    metadata: Optional[Dict[str, object]] = None,
) -> List[OptimizationResult]:
    if costs is None:
        costs = TradingCosts()
    if constraints is None:
        constraints = OptimizationConstraint()
    if step is None:
        step = test_periods

    parameter_candidates = build_parameter_grid(profile.parameters, parameter_grid)
    if not parameter_candidates:
        parameter_candidates = [profile.parameters]

    data = data.sort_values("date")
    results: List[OptimizationResult] = []
    total_rows = len(data)
    window_index = 0

    for start in range(0, total_rows - train_periods - test_periods + 1, step):
        train_slice = data.iloc[start : start + train_periods]
        test_slice = data.iloc[start + train_periods : start + train_periods + test_periods]
        if train_slice.empty or test_slice.empty:
            continue

        best_candidate = None
        best_objective = float("-inf")
        best_train_metrics: Optional[StrategyMetrics] = None

        for candidate in parameter_candidates:
            train_metrics = _evaluate_candidate(
                train_slice,
                contract_code,
                profile,
                candidate,
                profit_col=profit_col,
                exit_col=exit_col,
                costs=costs,
            )
            if not constraints.satisfied(train_metrics):
                continue

            objective_value = getattr(train_metrics, objective, None)
            if objective_value is None:
                raise AttributeError(f"Unknown optimization objective: {objective}")

            if objective_value > best_objective:
                best_objective = float(objective_value)
                best_candidate = candidate
                best_train_metrics = train_metrics

        if best_candidate is None or best_train_metrics is None:
            window_index += 1
            continue

        test_metrics = _evaluate_candidate(
            test_slice,
            contract_code,
            profile,
            best_candidate,
            profit_col=profit_col,
            exit_col=exit_col,
            costs=costs,
        )
        result = OptimizationResult(
            window_index=window_index,
            train_start=pd.to_datetime(train_slice["date"].iloc[0]),
            train_end=pd.to_datetime(train_slice["date"].iloc[-1]),
            test_start=pd.to_datetime(test_slice["date"].iloc[0]),
            test_end=pd.to_datetime(test_slice["date"].iloc[-1]),
            params=best_candidate,
            train_metrics=best_train_metrics,
            test_metrics=test_metrics,
            objective_value=float(getattr(test_metrics, objective, float("nan"))),
            contract_code=contract_code,
            metadata=metadata or {},
        )
        results.append(result)
        window_index += 1

    return results


def cross_validate_parameters(
    data: pd.DataFrame,
    contract_code: str,
    profile: ResolvedIndicatorProfile,
    parameter_grid: Mapping[str, Iterable[float]],
    *,
    profit_col: str,
    exit_col: str,
    costs: Optional[TradingCosts] = None,
    constraints: Optional[OptimizationConstraint] = None,
    n_splits: int = 5,
    objective: str = "sharpe",
    metadata: Optional[Dict[str, object]] = None,
) -> List[CrossValidationResult]:
    if costs is None:
        costs = TradingCosts()
    if constraints is None:
        constraints = OptimizationConstraint()

    parameter_candidates = build_parameter_grid(profile.parameters, parameter_grid)
    if not parameter_candidates:
        parameter_candidates = [profile.parameters]

    data = data.sort_values("date")
    total_rows = len(data)
    split_size = total_rows // (n_splits + 1)
    if split_size == 0:
        return []

    results: List[CrossValidationResult] = []

    for candidate in parameter_candidates:
        fold_metrics: List[StrategyMetrics] = []
        valid_candidate = True
        for split in range(1, n_splits + 1):
            end = split * split_size
            fold_data = data.iloc[:end]
            if fold_data.empty:
                continue
            metrics = _evaluate_candidate(
                fold_data,
                contract_code,
                profile,
                candidate,
                profit_col=profit_col,
                exit_col=exit_col,
                costs=costs,
            )
            if not constraints.satisfied(metrics):
                valid_candidate = False
                break
            fold_metrics.append(metrics)

        if not valid_candidate or not fold_metrics:
            continue

        objective_values = [getattr(m, objective, float("nan")) for m in fold_metrics]
        avg_objective = float(pd.Series(objective_values).mean())
        results.append(
            CrossValidationResult(
                params=candidate,
                fold_metrics=tuple(fold_metrics),
                avg_objective=avg_objective,
                contract_code=contract_code,
                metadata=metadata or {},
            )
        )

    return results


def optimization_results_to_frame(results: Sequence[OptimizationResult]) -> pd.DataFrame:
    records = []
    for item in results:
        record: Dict[str, object] = {
            "window_index": item.window_index,
            "contract_code": item.contract_code,
            "train_start": item.train_start,
            "train_end": item.train_end,
            "test_start": item.test_start,
            "test_end": item.test_end,
            "objective_value": item.objective_value,
        }
        record.update({f"train_{k}": v for k, v in item.train_metrics.to_dict().items()})
        record.update({f"test_{k}": v for k, v in item.test_metrics.to_dict().items()})
        record.update({
            "param_sma_fast": item.params.sma_fast,
            "param_sma_slow": item.params.sma_slow,
            "param_ema_fast": item.params.ema_fast,
            "param_ema_slow": item.params.ema_slow,
            "param_rsi_period": item.params.rsi_period,
            "param_macd_fast": item.params.macd_fast,
            "param_macd_slow": item.params.macd_slow,
            "param_macd_signal": item.params.macd_signal,
            "param_bollinger_period": item.params.bollinger_period,
            "param_bollinger_std": item.params.bollinger_std,
            "param_stochastic_period": item.params.stochastic_period,
            "param_stochastic_signal": item.params.stochastic_signal,
            "param_atr_period": item.params.atr_period,
        })
        record.update({f"meta_{k}": v for k, v in (item.metadata or {}).items()})
        records.append(record)
    return pd.DataFrame(records)


def cross_validation_results_to_frame(results: Sequence[CrossValidationResult]) -> pd.DataFrame:
    records = []
    for item in results:
        record: Dict[str, object] = {
            "contract_code": item.contract_code,
            "avg_objective": item.avg_objective,
        }
        record.update({
            "param_sma_fast": item.params.sma_fast,
            "param_sma_slow": item.params.sma_slow,
            "param_ema_fast": item.params.ema_fast,
            "param_ema_slow": item.params.ema_slow,
            "param_rsi_period": item.params.rsi_period,
            "param_macd_fast": item.params.macd_fast,
            "param_macd_slow": item.params.macd_slow,
            "param_macd_signal": item.params.macd_signal,
            "param_bollinger_period": item.params.bollinger_period,
            "param_bollinger_std": item.params.bollinger_std,
            "param_stochastic_period": item.params.stochastic_period,
            "param_stochastic_signal": item.params.stochastic_signal,
            "param_atr_period": item.params.atr_period,
        })
        record.update({f"meta_{k}": v for k, v in (item.metadata or {}).items()})
        for idx, metrics in enumerate(item.fold_metrics):
            prefix = f"fold{idx + 1}_"
            record.update({f"{prefix}{k}": v for k, v in metrics.to_dict().items()})
        records.append(record)
    return pd.DataFrame(records)
