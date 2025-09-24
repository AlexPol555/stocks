from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .metrics import TradingCosts  # noqa: F401  # placeholder for future integration
from core.indicators.calculations import (
    BB_MID_COL,
    BB_STD_COL,
    EMA_FAST_COL,
    EMA_SLOW_COL,
    MACD_COL,
    MACD_SIGNAL_COL,
    RSI_COL,
    SMA_FAST_COL,
    SMA_SLOW_COL,
)


@dataclass(frozen=True)
class ScoreWeights:
    trend: float = 0.35
    momentum: float = 0.25
    volatility: float = 0.2
    volume: float = 0.1
    sentiment: float = 0.1

    def normalize(self) -> "ScoreWeights":
        total = self.trend + self.momentum + self.volatility + self.volume + self.sentiment
        if total <= 0:
            return self
        return ScoreWeights(
            trend=self.trend / total,
            momentum=self.momentum / total,
            volatility=self.volatility / total,
            volume=self.volume / total,
            sentiment=self.sentiment / total,
        )


@dataclass(frozen=True)
class ScoringConfig:
    weights: ScoreWeights = ScoreWeights()
    activation_scale: float = 1.0
    long_threshold: float = 0.6
    short_threshold: float = 0.6


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def compute_signal_scores(
    data: pd.DataFrame,
    *,
    config: Optional[ScoringConfig] = None,
) -> pd.DataFrame:
    if config is None:
        config = ScoringConfig()
    weights = config.weights.normalize()
    epsilon = 1e-9

    df = data.copy()

    trend_fast = (df[SMA_FAST_COL] - df[SMA_SLOW_COL]) / (df[SMA_SLOW_COL].abs() + epsilon)
    trend_ema = (df[EMA_FAST_COL] - df[EMA_SLOW_COL]) / (df[EMA_SLOW_COL].abs() + epsilon)
    trend_signal = np.tanh(0.5 * trend_fast + 0.5 * trend_ema)

    momentum_rsi = ((df[RSI_COL] - 50.0) / 50.0).clip(-1.0, 1.0)
    macd_delta = (df[MACD_COL] - df[MACD_SIGNAL_COL]) / (df[MACD_SIGNAL_COL].abs() + epsilon)
    momentum_signal = np.tanh(0.6 * momentum_rsi + 0.4 * macd_delta)

    bollinger_position = (df["close"] - df[BB_MID_COL]) / (df[BB_STD_COL] * 2 + epsilon)
    volatility_signal = (-bollinger_position).clip(-1.0, 1.0)

    volume_ratio = (df["volume"] / (df["volume"].rolling(window=20, min_periods=5).mean() + epsilon)) - 1.0
    volume_signal = np.tanh(volume_ratio)

    sentiment_signal = _compute_sentiment_signal(df)

    long_raw = (
        weights.trend * trend_signal
        + weights.momentum * momentum_signal
        + weights.volatility * volatility_signal
        + weights.volume * volume_signal
        + weights.sentiment * sentiment_signal
    )
    short_raw = (
        weights.trend * (-trend_signal)
        + weights.momentum * (-momentum_signal)
        + weights.volatility * (-volatility_signal)
        + weights.volume * (-volume_signal)
        + weights.sentiment * (-sentiment_signal)
    )

    long_score = np.tanh(long_raw)
    short_score = np.tanh(short_raw)

    activation_scale = max(config.activation_scale, 1e-6)
    long_probability = _sigmoid(long_score / activation_scale)
    short_probability = _sigmoid(short_score / activation_scale)

    df["long_score"] = long_score
    df["short_score"] = short_score
    df["long_probability"] = long_probability
    df["short_probability"] = short_probability
    df["long_signal"] = (long_probability >= config.long_threshold).astype(int)
    df["short_signal"] = (short_probability >= config.short_threshold).astype(int)
    df["composite_signal"] = df["long_probability"] - df["short_probability"]
    return df


def _compute_sentiment_signal(df: pd.DataFrame) -> np.ndarray:
    sentiment_cols = [
        "long_fiz_1",
        "short_fiz_2",
        "long_jur_3",
        "short_jur_4",
        "total_positions",
    ]
    if not set(sentiment_cols).intersection(df.columns):
        return np.zeros(len(df))

    long_components = np.zeros(len(df), dtype=float)
    short_components = np.zeros(len(df), dtype=float)

    if "long_fiz_1" in df.columns:
        long_components += df["long_fiz_1"].fillna(0).to_numpy()
    if "long_jur_3" in df.columns:
        long_components += df["long_jur_3"].fillna(0).to_numpy()
    if "short_fiz_2" in df.columns:
        short_components += df["short_fiz_2"].fillna(0).to_numpy()
    if "short_jur_4" in df.columns:
        short_components += df["short_jur_4"].fillna(0).to_numpy()

    net = long_components - short_components
    denominator = np.abs(long_components) + np.abs(short_components) + np.abs(df.get("total_positions", 0)) + 1e-9
    return np.tanh(net / denominator)
