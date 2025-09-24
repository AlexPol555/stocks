"""Signal generation helpers."""
from __future__ import annotations

import pandas as pd

from .calculations import (
    ATR_COL,
    BB_LOWER_COL,
    BB_UPPER_COL,
    EMA_FAST_COL,
    EMA_SLOW_COL,
    MACD_COL,
    MACD_SIGNAL_COL,
    RSI_COL,
    SMA_FAST_COL,
    SMA_SLOW_COL,
    STOCH_K_COL,
)


def generate_adaptive_signals(data: pd.DataFrame, use_adaptive: bool = True) -> pd.DataFrame:
    data = data.copy()
    if use_adaptive:
        window = 15
        data["RSI_mean"] = data[RSI_COL].rolling(window=window, min_periods=1).mean()
        data["RSI_std"] = data[RSI_COL].rolling(window=window, min_periods=1).std()
        adaptive_buy_threshold = data["RSI_mean"] - data["RSI_std"]
        adaptive_sell_threshold = data["RSI_mean"] + data["RSI_std"]

        data["Adaptive_Buy_Signal"] = (
            (data[SMA_FAST_COL] > data[SMA_SLOW_COL])
            & (data[EMA_FAST_COL] > data[EMA_SLOW_COL])
            & (data[RSI_COL] < adaptive_buy_threshold)
            & (data[MACD_COL] > data[MACD_SIGNAL_COL])
        ).astype(int)

        data["Adaptive_Sell_Signal"] = (
            (data[SMA_FAST_COL] < data[SMA_SLOW_COL])
            & (data[EMA_FAST_COL] < data[EMA_SLOW_COL])
            & (data[RSI_COL] > adaptive_sell_threshold)
            & (data[MACD_COL] < data[MACD_SIGNAL_COL])
        ).astype(int)
    return data


def generate_new_adaptive_signals(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["ATR_MA"] = data[ATR_COL].rolling(window=24, min_periods=1).mean()

    data["New_Adaptive_Buy_Signal"] = (
        (data["close"] < data[BB_LOWER_COL])
        & (data[STOCH_K_COL] < 15)
        & (data[ATR_COL] < data["ATR_MA"])
    ).astype(int)

    sell_condition = (
        (data["close"] > data[BB_UPPER_COL])
        & (data[STOCH_K_COL] > 85)
        & (data[ATR_COL] < data["ATR_MA"])
    )
    data["New_Adaptive_Sell_Signal"] = sell_condition.astype(int)

    data.drop(columns=["ATR_MA"], inplace=True)
    return data


def calculate_additional_filters(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["Volume_Filter"] = data["volume"] > data["volume"].rolling(window=20, min_periods=1).mean()
    lower_bound = data[ATR_COL].quantile(0.25)
    upper_bound = data[ATR_COL].quantile(0.75)
    data["Volatility_Filter"] = (data[ATR_COL] > lower_bound) & (data[ATR_COL] < upper_bound)
    return data


def generate_final_adaptive_signals(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["Combined_Buy_Signal"] = (data.get("Adaptive_Buy_Signal", 0) | data.get("New_Adaptive_Buy_Signal", 0)).astype(int)
    data = calculate_additional_filters(data)
    data["Final_Buy_Signal"] = (
        data["Combined_Buy_Signal"]
        & data["Volume_Filter"]
        & data["Volatility_Filter"]
    ).astype(int)
    return data

