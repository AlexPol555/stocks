from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from core.indicators.calculations import ATR_COL
from .metrics import TradingCosts


@dataclass(frozen=True)
class TradeRecord:
    direction: str
    entry_index: int
    exit_index: int
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    gross_return: float
    net_return: float
    holding_days: int
    max_favorable_excursion: float
    max_adverse_excursion: float


def simulate_trades(
    data: pd.DataFrame,
    *,
    signal_col: str,
    direction: str,
    atr_col: str,
    risk_params,
    costs: TradingCosts,
    price_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
    date_col: str = "date",
) -> List[TradeRecord]:
    if signal_col not in data.columns:
        return []

    df = data.reset_index(drop=True)
    signals = df[signal_col].fillna(0).astype(int).to_numpy()
    atr_values = df[atr_col].ffill().bfill().to_numpy()
    prices = df[price_col].to_numpy()
    highs = df[high_col].to_numpy()
    lows = df[low_col].to_numpy()
    dates = pd.to_datetime(df[date_col]).to_numpy()

    trades: List[TradeRecord] = []
    n = len(df)
    idx = 0
    open_until = -1

    while idx < n:
        if idx <= open_until:
            idx += 1
            continue
        if signals[idx] <= 0 or np.isnan(prices[idx]) or np.isnan(atr_values[idx]):
            idx += 1
            continue

        entry_price = float(prices[idx])
        atr = float(atr_values[idx])
        entry_date = pd.Timestamp(dates[idx])
        max_holding = int(risk_params.max_holding_days)

        if direction == "long":
            stop_price = entry_price - atr * risk_params.atr_stop_multiplier
            target_price = entry_price + atr * risk_params.atr_target_multiplier
        else:
            stop_price = entry_price + atr * risk_params.atr_stop_multiplier
            target_price = entry_price - atr * risk_params.atr_target_multiplier

        trailing_multiplier = risk_params.trailing_stop_multiplier
        best_exit_index = idx
        exit_price = entry_price
        exit_reason = "time"  # informational, not returned yet
        mfe = 0.0
        mae = 0.0

        for step in range(1, max_holding + 1):
            current_idx = idx + step
            if current_idx >= n:
                break
            high = float(highs[current_idx])
            low = float(lows[current_idx])
            close_price = float(prices[current_idx])
            atr_step = float(atr_values[current_idx]) if not np.isnan(atr_values[current_idx]) else atr

            if direction == "long":
                mfe = max(mfe, (high - entry_price) / entry_price)
                mae = min(mae, (low - entry_price) / entry_price)
                hit_target = high >= target_price
                hit_stop = low <= stop_price
                if hit_stop and hit_target:
                    hit_target = False  # assume stop triggers first (conservative)
                if hit_target:
                    exit_price = target_price
                    best_exit_index = current_idx
                    exit_reason = "target"
                    break
                if hit_stop:
                    exit_price = stop_price
                    best_exit_index = current_idx
                    exit_reason = "stop"
                    break
                if trailing_multiplier:
                    new_trailing = high - trailing_multiplier * atr_step
                    stop_price = max(stop_price, new_trailing)
            else:
                mfe = max(mfe, (entry_price - low) / entry_price)
                mae = min(mae, (entry_price - high) / entry_price)
                hit_target = low <= target_price
                hit_stop = high >= stop_price
                if hit_stop and hit_target:
                    hit_target = False  # stop first
                if hit_target:
                    exit_price = target_price
                    best_exit_index = current_idx
                    exit_reason = "target"
                    break
                if hit_stop:
                    exit_price = stop_price
                    best_exit_index = current_idx
                    exit_reason = "stop"
                    break
                if trailing_multiplier:
                    new_trailing = low + trailing_multiplier * atr_step
                    stop_price = min(stop_price, new_trailing)
        else:
            # time exit when loop not broken
            final_idx = min(idx + max_holding, n - 1)
            exit_price = float(prices[final_idx])
            best_exit_index = final_idx
            if direction == "long":
                mfe = max(mfe, (highs[idx:final_idx + 1].max() - entry_price) / entry_price)
                mae = min(mae, (lows[idx:final_idx + 1].min() - entry_price) / entry_price)
            else:
                mfe = max(mfe, (entry_price - lows[idx:final_idx + 1].min()) / entry_price)
                mae = min(mae, (entry_price - highs[idx:final_idx + 1].max()) / entry_price)

        holding_days = max(1, best_exit_index - idx)
        exit_date = pd.Timestamp(dates[best_exit_index])

        if direction == "long":
            gross_return = (exit_price - entry_price) / entry_price
        else:
            gross_return = (entry_price - exit_price) / entry_price

        per_trade_cost = costs.round_trip_cost(holding_days)
        tax_component = max(gross_return, 0.0) * costs.tax_pct
        net_return = gross_return - per_trade_cost - tax_component

        trades.append(
            TradeRecord(
                direction=direction,
                entry_index=idx,
                exit_index=best_exit_index,
                entry_date=entry_date,
                exit_date=exit_date,
                entry_price=entry_price,
                exit_price=exit_price,
                gross_return=gross_return,
                net_return=net_return,
                holding_days=holding_days,
                max_favorable_excursion=mfe,
                max_adverse_excursion=mae,
            )
        )
        open_until = best_exit_index
        idx = best_exit_index + 1
    return trades


def apply_risk_management(
    data: pd.DataFrame,
    *,
    risk_profile,
    costs: TradingCosts,
    long_signal_col: str = "long_signal",
    short_signal_col: str = "short_signal",
    atr_col: str = ATR_COL,
) -> Dict[str, pd.DataFrame]:
    df = data.copy()
    index_map = list(df.index)
    index_map = list(df.index)
    long_trades = simulate_trades(
        df,
        signal_col=long_signal_col,
        direction="long",
        atr_col=atr_col,
        risk_params=risk_profile.long,
        costs=costs,
    )
    short_trades = simulate_trades(
        df,
        signal_col=short_signal_col,
        direction="short",
        atr_col=atr_col,
        risk_params=risk_profile.short,
        costs=costs,
    )

    df = _annotate_trades(
        df,
        long_trades,
        prefix="long",
        index_map=index_map,
    )
    df = _annotate_trades(
        df,
        short_trades,
        prefix="short",
        index_map=index_map,
    )

    return {
        "frame": df,
        "long_trades": pd.DataFrame([t.__dict__ for t in long_trades]) if long_trades else pd.DataFrame(),
        "short_trades": pd.DataFrame([t.__dict__ for t in short_trades]) if short_trades else pd.DataFrame(),
    }


def _annotate_trades(
    df: pd.DataFrame,
    trades: List[TradeRecord],
    prefix: str,
    *,
    index_map: Optional[Sequence] = None,
) -> pd.DataFrame:
    if not trades:
        columns = {
            f"{prefix}_trade_net_pct": np.nan,
            f"{prefix}_trade_gross_pct": np.nan,
            f"{prefix}_trade_exit_price": np.nan,
            f"{prefix}_trade_exit_date": pd.NaT,
            f"{prefix}_trade_holding_days": np.nan,
        }
        for col, default in columns.items():
            if col not in df.columns:
                df[col] = default
        return df

    df = df.copy()
    positional_index = list(index_map) if index_map is not None else list(df.index)
    for trade in trades:
        if trade.entry_index < 0 or trade.entry_index >= len(positional_index):
            continue
        idx = positional_index[trade.entry_index]
        df.loc[idx, f"{prefix}_trade_net_pct"] = trade.net_return * 100.0
        df.loc[idx, f"{prefix}_trade_gross_pct"] = trade.gross_return * 100.0
        df.loc[idx, f"{prefix}_trade_exit_price"] = trade.exit_price
        df.loc[idx, f"{prefix}_trade_exit_date"] = trade.exit_date
        df.loc[idx, f"{prefix}_trade_holding_days"] = trade.holding_days
        df.loc[idx, f"{prefix}_trade_mfe"] = trade.max_favorable_excursion * 100.0
        df.loc[idx, f"{prefix}_trade_mae"] = trade.max_adverse_excursion * 100.0
    return df
