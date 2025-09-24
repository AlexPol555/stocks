"""Low level numerical indicator calculations driven by configuration profiles."""
from __future__ import annotations

from typing import Tuple

import pandas as pd

from core.config import IndicatorParameters


SMA_FAST_COL = "SMA_FAST"
SMA_SLOW_COL = "SMA_SLOW"
EMA_FAST_COL = "EMA_FAST"
EMA_SLOW_COL = "EMA_SLOW"
MACD_COL = "MACD"
MACD_SIGNAL_COL = "MACD_SIGNAL"
RSI_COL = "RSI"
BB_MID_COL = "BB_MIDDLE"
BB_STD_COL = "BB_STD"
BB_UPPER_COL = "BB_UPPER"
BB_LOWER_COL = "BB_LOWER"
STOCH_K_COL = "STOCHASTIC_K"
STOCH_D_COL = "STOCHASTIC_D"
ATR_COL = "ATR"


def _resolve_window_columns(params: IndicatorParameters) -> Tuple[str, str, str, str]:
    return (
        f"SMA_{params.sma_fast}",
        f"SMA_{params.sma_slow}",
        f"EMA_{params.ema_fast}",
        f"EMA_{params.ema_slow}",
    )


def calculate_basic_indicators(data: pd.DataFrame, params: IndicatorParameters) -> pd.DataFrame:
    epsilon = 1e-9
    data = data.copy()

    sma_fast_col, sma_slow_col, ema_fast_col, ema_slow_col = _resolve_window_columns(params)
    data[sma_fast_col] = data["close"].rolling(window=params.sma_fast, min_periods=1).mean()
    data[sma_slow_col] = data["close"].rolling(window=params.sma_slow, min_periods=1).mean()
    data[SMA_FAST_COL] = data[sma_fast_col]
    data[SMA_SLOW_COL] = data[sma_slow_col]

    data[ema_fast_col] = data["close"].ewm(span=params.ema_fast, adjust=False).mean()
    data[ema_slow_col] = data["close"].ewm(span=params.ema_slow, adjust=False).mean()
    data[EMA_FAST_COL] = data[ema_fast_col]
    data[EMA_SLOW_COL] = data[ema_slow_col]

    delta = data["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    alpha = 1.0 / max(params.rsi_period, 1)
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
    rs = avg_gain / (avg_loss + epsilon)
    data[RSI_COL] = 100 - (100 / (1 + rs))

    ema_fast = data["close"].ewm(span=params.macd_fast, adjust=False).mean()
    ema_slow = data["close"].ewm(span=params.macd_slow, adjust=False).mean()
    data[MACD_COL] = ema_fast - ema_slow
    data[MACD_SIGNAL_COL] = data[MACD_COL].ewm(span=params.macd_signal, adjust=False).mean()
    return data


def generate_trading_signals(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["Buy_Signal"] = (
        (data[SMA_FAST_COL] > data[SMA_SLOW_COL])
        & (data[EMA_FAST_COL] > data[EMA_SLOW_COL])
        & (data[RSI_COL] < 35)
        & (data[MACD_COL] > data[MACD_SIGNAL_COL])
    ).astype(int)

    data["Sell_Signal"] = (
        (data[SMA_FAST_COL] < data[SMA_SLOW_COL])
        & (data[EMA_FAST_COL] < data[EMA_SLOW_COL])
        & (data[RSI_COL] > 65)
        & (data[MACD_COL] < data[MACD_SIGNAL_COL])
    ).astype(int)

    data["Signal"] = 0
    data.loc[data["Buy_Signal"] == 1, "Signal"] = 1
    data.loc[data["Sell_Signal"] == 1, "Signal"] = -1
    return data


def calculate_additional_indicators(data: pd.DataFrame, params: IndicatorParameters) -> pd.DataFrame:
    epsilon = 1e-9
    data = data.copy()

    window_bb = params.bollinger_period
    data[BB_MID_COL] = data["close"].rolling(window=window_bb, min_periods=1).mean()
    data[BB_STD_COL] = data["close"].rolling(window=window_bb, min_periods=1).std(ddof=0)
    data[BB_UPPER_COL] = data[BB_MID_COL] + params.bollinger_std * data[BB_STD_COL]
    data[BB_LOWER_COL] = data[BB_MID_COL] - params.bollinger_std * data[BB_STD_COL]

    window_so = params.stochastic_period
    data["Lowest_Low"] = data["low"].rolling(window=window_so, min_periods=1).min()
    data["Highest_High"] = data["high"].rolling(window=window_so, min_periods=1).max()
    data[STOCH_K_COL] = 100 * (data["close"] - data["Lowest_Low"]) / (
        data["Highest_High"] - data["Lowest_Low"] + epsilon
    )
    data[STOCH_D_COL] = data[STOCH_K_COL].rolling(window=params.stochastic_signal, min_periods=1).mean()

    data["Prev_Close"] = data["close"].shift(1)
    data["High_Low"] = data["high"] - data["low"]
    data["High_PrevClose"] = (data["high"] - data["Prev_Close"]).abs()
    data["Low_PrevClose"] = (data["low"] - data["Prev_Close"]).abs()
    data["TR"] = data[["High_Low", "High_PrevClose", "Low_PrevClose"]].max(axis=1)
    data[ATR_COL] = data["TR"].rolling(window=params.atr_period, min_periods=1).mean()
    return data

