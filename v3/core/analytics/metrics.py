from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt
from typing import Dict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TradingCosts:
    """Round-trip trading costs expressed in percentage terms."""

    commission_pct: float = 0.0  # per side
    tax_pct: float = 0.0  # applied on profitable trades
    slippage_pct: float = 0.0  # per trade
    borrow_daily_pct: float = 0.0  # financing or borrow cost daily
    leverage_daily_pct: float = 0.0  # leverage fee per day

    def round_trip_cost(self, holding_days: float) -> float:
        base = 2 * self.commission_pct + self.slippage_pct
        base += holding_days * (self.borrow_daily_pct + self.leverage_daily_pct)
        return base


@dataclass(frozen=True)
class StrategyMetrics:
    total_trades: int
    win_rate: float
    avg_pnl: float
    median_pnl: float
    profit_factor: float
    gross_return: float
    net_return: float
    cagr: float
    sharpe: float
    sortino: float
    max_drawdown: float

    def to_dict(self) -> Dict[str, float]:
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                data[key] = float(value)
        return data


def extract_trades(
    data: pd.DataFrame,
    *,
    profit_col: str,
    exit_date_col: str,
    price_col: str = "close",
) -> pd.DataFrame:
    required = {"date", profit_col, exit_date_col}
    missing = required.difference(data.columns)
    if missing:
        raise KeyError(f"DataFrame missing required columns: {missing}")

    entries = data.loc[data[profit_col].notna(), ["date", profit_col, exit_date_col, price_col]].copy()
    entries.rename(
        columns={
            "date": "entry_date",
            profit_col: "pnl_pct",
            exit_date_col: "exit_date",
            price_col: "entry_price",
        },
        inplace=True,
    )
    entries["entry_date"] = pd.to_datetime(entries["entry_date"], errors="coerce")
    entries["exit_date"] = pd.to_datetime(entries["exit_date"], errors="coerce")
    holding = (entries["exit_date"] - entries["entry_date"]).dt.days
    entries["holding_days"] = holding.clip(lower=0).fillna(0).astype(float)
    return entries


def compute_strategy_metrics(
    trades: pd.DataFrame,
    *,
    costs: TradingCosts,
    risk_free_rate: float = 0.0,
) -> StrategyMetrics:
    if trades.empty:
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

    pnl_pct = trades["pnl_pct"].astype(float) / 100.0
    holding_days = trades["holding_days"].astype(float)

    per_trade_cost = holding_days.apply(costs.round_trip_cost)
    tax_component = pnl_pct.clip(lower=0) * costs.tax_pct
    net_returns = pnl_pct - per_trade_cost - tax_component

    gross_curve = (1 + pnl_pct).cumprod()
    net_curve = (1 + net_returns).cumprod()

    gross_return = float(gross_curve.iloc[-1] - 1)
    net_return = float(net_curve.iloc[-1] - 1)

    start_date = trades["entry_date"].min()
    end_date = trades["exit_date"].max()
    if pd.isna(start_date) or pd.isna(end_date) or end_date <= start_date:
        years = len(trades) / 252.0
    else:
        years = max((end_date - start_date).days / 365.25, 1.0 / 365.25)

    if years <= 0:
        years = len(trades) / 252.0 if len(trades) else 1.0

    cagr = float((1 + net_return) ** (1 / years) - 1) if net_return > -1 else -1.0

    total_trades = len(trades)
    wins = (pnl_pct > 0).sum()
    losses = (pnl_pct < 0).sum()
    win_rate = wins / total_trades if total_trades else 0.0
    avg_pnl = float(pnl_pct.mean() * 100)
    median_pnl = float(pnl_pct.median() * 100)

    gross_profit = pnl_pct[pnl_pct > 0].sum()
    gross_loss = pnl_pct[pnl_pct < 0].sum()
    profit_factor = float(gross_profit / abs(gross_loss)) if gross_loss != 0 else float("inf")

    mean_net = net_returns.mean()
    std_net = net_returns.std(ddof=1)
    trades_per_year = total_trades / years if years > 0 else total_trades
    sharpe = 0.0
    if std_net > 0:
        sharpe = float((mean_net - risk_free_rate / max(trades_per_year, 1e-9)) * sqrt(trades_per_year) / std_net)

    downside = net_returns[net_returns < 0]
    sortino = 0.0
    if not downside.empty:
        downside_std = downside.std(ddof=1)
        if downside_std > 0:
            sortino = float((mean_net - risk_free_rate / max(trades_per_year, 1e-9)) * sqrt(trades_per_year) / downside_std)

    running_max = net_curve.cummax()
    drawdowns = net_curve / running_max - 1
    max_drawdown = float(drawdowns.min())

    return StrategyMetrics(
        total_trades=int(total_trades),
        win_rate=float(win_rate),
        avg_pnl=avg_pnl,
        median_pnl=median_pnl,
        profit_factor=float(profit_factor),
        gross_return=gross_return,
        net_return=net_return,
        cagr=float(cagr),
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=max_drawdown,
    )
