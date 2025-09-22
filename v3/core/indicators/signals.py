"""Signal generation helpers."""
from __future__ import annotations

import pandas as pd


def generate_adaptive_signals(data: pd.DataFrame, use_adaptive: bool = True) -> pd.DataFrame:
    data = data.copy()
    if use_adaptive:
        window = 15
        data["RSI_mean"] = data["RSI"].rolling(window=window, min_periods=1).mean()
        data["RSI_std"] = data["RSI"].rolling(window=window, min_periods=1).std()
        adaptive_buy_threshold = data["RSI_mean"] - data["RSI_std"]
        adaptive_sell_threshold = data["RSI_mean"] + data["RSI_std"]

        data["Adaptive_Buy_Signal"] = (
            (data["SMA_50"] > data["SMA_200"])
            & (data["EMA_50"] > data["EMA_200"])
            & (data["RSI"] < adaptive_buy_threshold)
            & (data["MACD"] > data["Signal_Line"])
        ).astype(int)

        data["Adaptive_Sell_Signal"] = (
            (data["SMA_50"] < data["SMA_200"])
            & (data["EMA_50"] < data["EMA_200"])
            & (data["RSI"] > adaptive_sell_threshold)
            & (data["MACD"] < data["Signal_Line"])
        ).astype(int)
    return data


def generate_new_adaptive_signals(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["ATR_MA"] = data["ATR"].rolling(window=24, min_periods=1).mean()

    data["New_Adaptive_Buy_Signal"] = (
        (data["close"] < data["BB_Lower"])
        & (data["%K"] < 15)
        & (data["ATR"] < data["ATR_MA"])
    ).astype(int)

    sell_condition = (
        (data["close"] > data["BB_Upper"])
        & (data["%K"] > 85)
        & (data["ATR"] < data["ATR_MA"])
    )
    data["New_Adaptive_Sell_Signal"] = sell_condition.astype(int)

    data.drop(columns=["ATR_MA"], inplace=True)
    return data


def calculate_additional_filters(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["Volume_Filter"] = data["volume"] > data["volume"].rolling(window=20).mean()
    lower_bound = data["ATR"].quantile(0.25)
    upper_bound = data["ATR"].quantile(0.75)
    data["Volatility_Filter"] = (data["ATR"] > lower_bound) & (data["ATR"] < upper_bound)
    return data


def generate_final_adaptive_signals(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["Combined_Buy_Signal"] = (data["Adaptive_Buy_Signal"] | data["New_Adaptive_Buy_Signal"]).astype(int)
    data = calculate_additional_filters(data)
    data["Final_Buy_Signal"] = (
        data["Combined_Buy_Signal"]
        & data["Volume_Filter"]
        & data["Volatility_Filter"]
    ).astype(int)
    return data
