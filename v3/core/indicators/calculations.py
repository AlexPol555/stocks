"""Low level numerical indicator calculations."""
from __future__ import annotations

import pandas as pd


def calculate_basic_indicators(data: pd.DataFrame) -> pd.DataFrame:
    epsilon = 1e-9
    data = data.copy()
    data["SMA_50"] = data["close"].rolling(window=50).mean()
    data["SMA_200"] = data["close"].rolling(window=200).mean()
    data["EMA_50"] = data["close"].ewm(span=50, adjust=False).mean()
    data["EMA_200"] = data["close"].ewm(span=200, adjust=False).mean()

    delta = data["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / (avg_loss + epsilon)
    data["RSI"] = 100 - (100 / (1 + rs))

    data["EMA_12"] = data["close"].ewm(span=12, adjust=False).mean()
    data["EMA_26"] = data["close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = data["EMA_12"] - data["EMA_26"]
    data["Signal_Line"] = data["MACD"].ewm(span=9, adjust=False).mean()
    return data


def generate_trading_signals(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["Buy_Signal"] = (
        (data["SMA_50"] > data["SMA_200"])
        & (data["EMA_50"] > data["EMA_200"])
        & (data["RSI"] < 35)
        & (data["MACD"] > data["Signal_Line"])
    ).astype(int)

    data["Sell_Signal"] = (
        (data["SMA_50"] < data["SMA_200"])
        & (data["EMA_50"] < data["EMA_200"])
        & (data["RSI"] > 65)
        & (data["MACD"] < data["Signal_Line"])
    ).astype(int)

    data["Signal"] = 0
    data.loc[data["Buy_Signal"] == 1, "Signal"] = 1
    data.loc[data["Sell_Signal"] == 1, "Signal"] = -1
    return data


def calculate_additional_indicators(data: pd.DataFrame, atr_period: int = 24) -> pd.DataFrame:
    epsilon = 1e-9
    data = data.copy()

    window_bb = 35
    data["BB_Middle"] = data["close"].rolling(window=window_bb).mean()
    data["BB_Std"] = data["close"].rolling(window=window_bb).std()
    data["BB_Upper"] = data["BB_Middle"] + 2 * data["BB_Std"]
    data["BB_Lower"] = data["BB_Middle"] - 2 * data["BB_Std"]

    window_so = 30
    data["Lowest_Low"] = data["low"].rolling(window=window_so).min()
    data["Highest_High"] = data["high"].rolling(window=window_so).max()
    data["%K"] = 100 * (data["close"] - data["Lowest_Low"]) / (data["Highest_High"] - data["Lowest_Low"] + epsilon)
    data["%D"] = data["%K"].rolling(window=3).mean()

    data["Prev_Close"] = data["close"].shift(1)
    data["High_Low"] = data["high"] - data["low"]
    data["High_PrevClose"] = (data["high"] - data["Prev_Close"]).abs()
    data["Low_PrevClose"] = (data["low"] - data["Prev_Close"]).abs()
    data["TR"] = data[["High_Low", "High_PrevClose", "Low_PrevClose"]].max(axis=1)
    data["ATR"] = data["TR"].rolling(window=atr_period, min_periods=1).mean()
    return data
