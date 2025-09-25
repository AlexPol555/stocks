"""Higher level optimisation workflows for indicators."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd

from core.config import ResolvedIndicatorProfile, get_analytics_config
from core.config.manager import AnalyticsConfig
from core.analytics.metrics import TradingCosts, StrategyMetrics, compute_strategy_metrics, extract_trades
from core.analytics.optimisation import (
    OptimizationConstraint,
    OptimizationResult,
    build_parameter_grid,
    cross_validate_parameters,
    cross_validation_results_to_frame,
    optimization_results_to_frame,
    walk_forward_optimize,
)

REPORTS_DIR = Path("reports/optimisation")


def _ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def _load_contract_dataset(conn, contract_code: str) -> pd.DataFrame:
    from core import database

    merged = database.mergeMetrDaily(conn)
    if merged is None or merged.empty:
        return pd.DataFrame()
    data = merged[merged["contract_code"] == contract_code].copy()
    if data.empty:
        return pd.DataFrame()
    data.sort_values("date", inplace=True)
    return data


def _resolve_profile(config: AnalyticsConfig, contract_code: str, data: pd.DataFrame) -> ResolvedIndicatorProfile:
    return config.resolve_indicator_profile(contract_code, data)


def run_walk_forward_workflow(
    conn,
    contract_code: str,
    parameter_grid: Dict[str, Iterable[int]],
    *,
    costs: Optional[TradingCosts] = None,
    constraints: Optional[OptimizationConstraint] = None,
    train_periods: int = 252,
    test_periods: int = 63,
    step: Optional[int] = None,
    objective: str = "sharpe",
) -> pd.DataFrame:
    dataset = _load_contract_dataset(conn, contract_code)
    if dataset.empty:
        return pd.DataFrame()
    config = get_analytics_config()
    profile = _resolve_profile(config, contract_code, dataset)

    wf_results = walk_forward_optimize(
        dataset,
        contract_code,
        profile,
        parameter_grid,
        profit_col="long_trade_net_pct",
        exit_col="long_trade_exit_date",
        costs=costs or TradingCosts(),
        constraints=constraints,
        train_periods=train_periods,
        test_periods=test_periods,
        step=step,
        objective=objective,
        metadata={"contract_code": contract_code},
    )
    if not wf_results:
        return pd.DataFrame()
    df = optimization_results_to_frame(wf_results)
    return df


def run_cross_validation_workflow(
    conn,
    contract_code: str,
    parameter_grid: Dict[str, Iterable[int]],
    *,
    costs: Optional[TradingCosts] = None,
    constraints: Optional[OptimizationConstraint] = None,
    n_splits: int = 5,
    objective: str = "sharpe",
) -> pd.DataFrame:
    dataset = _load_contract_dataset(conn, contract_code)
    if dataset.empty:
        return pd.DataFrame()
    config = get_analytics_config()
    profile = _resolve_profile(config, contract_code, dataset)

    cv_results = cross_validate_parameters(
        dataset,
        contract_code,
        profile,
        parameter_grid,
        profit_col="long_trade_net_pct",
        exit_col="long_trade_exit_date",
        costs=costs or TradingCosts(),
        constraints=constraints,
        n_splits=n_splits,
        objective=objective,
        metadata={"contract_code": contract_code},
    )
    if not cv_results:
        return pd.DataFrame()
    return cross_validation_results_to_frame(cv_results)


def save_optimisation_report(df: pd.DataFrame, *, report_name: str) -> Path:
    if df.empty:
        raise ValueError("Received empty optimisation DataFrame")
    reports_dir = _ensure_reports_dir()
    target = reports_dir / f"{report_name}.csv"
    df.to_csv(target, index=False)
    return target


def compute_kpi_for_signals(data: pd.DataFrame, signal_col: str, profit_col: str, exit_col: str, *, costs: Optional[TradingCosts] = None) -> StrategyMetrics:
    if signal_col not in data.columns or profit_col not in data.columns:
        return StrategyMetrics(
            total_trades=0,
            win_rate=0.0,
            avg_pnl=0.0,
            median_pnl=0.0,
            profit_factor=0.0,
            gross_return=0.0,
            net_return=0.0,
            cagr=0.0,
            sharpe=0.0,
            sortino=0.0,
            max_drawdown=0.0,
        )
    working = data[["date", signal_col, profit_col, exit_col, "close"]].copy()
    working.rename(
        columns={
            signal_col: "Signal",
            profit_col: "Profit",
            exit_col: "Exit_Date",
            "close": "close",
        },
        inplace=True,
    )
    working["date"] = pd.to_datetime(working["date"], errors="coerce")
    working["Exit_Date"] = pd.to_datetime(working["Exit_Date"], errors="coerce")
    working["Profit"] = working["Profit"].astype(float)
    working.loc[working["Signal"] != working["Signal"], "Signal"] = 0
    trades = extract_trades(
        working,
        profit_col="Profit",
        exit_date_col="Exit_Date",
        price_col="close",
    )
    return compute_strategy_metrics(trades, costs=costs or TradingCosts())
