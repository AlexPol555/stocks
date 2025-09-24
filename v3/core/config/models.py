from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class IndicatorParameters:
    """Container for indicator window configuration."""

    sma_fast: int
    sma_slow: int
    ema_fast: int
    ema_slow: int
    rsi_period: int
    macd_fast: int
    macd_slow: int
    macd_signal: int
    bollinger_period: int
    bollinger_std: float
    stochastic_period: int
    stochastic_signal: int
    atr_period: int

    def validate(self) -> None:
        numeric_fields = {
            "sma_fast": self.sma_fast,
            "sma_slow": self.sma_slow,
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "rsi_period": self.rsi_period,
            "macd_fast": self.macd_fast,
            "macd_slow": self.macd_slow,
            "macd_signal": self.macd_signal,
            "bollinger_period": self.bollinger_period,
            "stochastic_period": self.stochastic_period,
            "stochastic_signal": self.stochastic_signal,
            "atr_period": self.atr_period,
        }
        for name, value in numeric_fields.items():
            if value <= 0:
                raise ValueError(f"Indicator parameter '{name}' must be positive, got {value}")
        if self.bollinger_std <= 0:
            raise ValueError("Bollinger std multiplier must be positive")

    def merge(self, overrides: Mapping[str, Any]) -> "IndicatorParameters":
        data: Dict[str, Any] = {
            "sma_fast": self.sma_fast,
            "sma_slow": self.sma_slow,
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "rsi_period": self.rsi_period,
            "macd_fast": self.macd_fast,
            "macd_slow": self.macd_slow,
            "macd_signal": self.macd_signal,
            "bollinger_period": self.bollinger_period,
            "bollinger_std": self.bollinger_std,
            "stochastic_period": self.stochastic_period,
            "stochastic_signal": self.stochastic_signal,
            "atr_period": self.atr_period,
        }
        data.update(overrides)
        updated = IndicatorParameters(**data)
        updated.validate()
        return updated


@dataclass(frozen=True)
class RiskParameters:
    """Dynamic risk settings for trade management."""

    atr_stop_multiplier: float
    atr_target_multiplier: float
    trailing_stop_multiplier: Optional[float]
    max_holding_days: int
    risk_per_trade_pct: float
    position_size_pct: float

    def validate(self) -> None:
        if self.atr_stop_multiplier <= 0 or self.atr_target_multiplier <= 0:
            raise ValueError("ATR multipliers must be positive")
        if self.max_holding_days <= 0:
            raise ValueError("max_holding_days must be positive")
        if self.risk_per_trade_pct < 0 or self.position_size_pct <= 0:
            raise ValueError("Risk and position size percentages must be positive")
        if self.trailing_stop_multiplier is not None and self.trailing_stop_multiplier <= 0:
            raise ValueError("Trailing stop multiplier must be positive when provided")

    def merge(self, overrides: Mapping[str, Any]) -> "RiskParameters":
        data: Dict[str, Any] = {
            "atr_stop_multiplier": self.atr_stop_multiplier,
            "atr_target_multiplier": self.atr_target_multiplier,
            "trailing_stop_multiplier": self.trailing_stop_multiplier,
            "max_holding_days": self.max_holding_days,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "position_size_pct": self.position_size_pct,
        }
        data.update({k: overrides[k] for k in overrides if k in data})
        updated = RiskParameters(**data)
        updated.validate()
        return updated


@dataclass(frozen=True)
class ResolvedRiskProfile:
    """Long/short risk definitions for a given instrument profile."""

    long: RiskParameters
    short: RiskParameters


@dataclass(frozen=True)
class AssetProfile:
    """Metadata describing the analytical profile of an instrument."""

    asset_class: str
    timeframe: str
    risk_profile: str = "base"
    volatility_override: Optional[str] = None


@dataclass(frozen=True)
class ResolvedIndicatorProfile:
    """Indicator parameters alongside the resolved metadata keys."""

    asset_class: str
    timeframe: str
    volatility: str
    parameters: IndicatorParameters
    risk: Optional[ResolvedRiskProfile] = None

