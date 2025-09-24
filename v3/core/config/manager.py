from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Dict, Mapping, Optional, Tuple, Pattern

import pandas as pd

from .loader import ConfigLoadError, load_yaml_config
from .models import AssetProfile, IndicatorParameters, ResolvedIndicatorProfile, ResolvedRiskProfile, RiskParameters
from .paths import get_analytics_config_path


class AnalyticsConfig:
    """Configuration registry for indicator and asset specific settings."""

    def __init__(self, raw: Mapping[str, object]):
        self._raw = raw
        self._indicator_defaults = self._build_indicator_defaults(raw)
        self._indicator_profiles = self._build_indicator_profiles(raw)
        self._risk_profiles = self._build_risk_profiles(raw)
        self._asset_defaults, self._asset_code_map, self._asset_patterns = self._build_asset_profiles(raw)
        self._volatility_thresholds = self._build_volatility_thresholds(raw)

    @staticmethod
    def _build_indicator_defaults(raw: Mapping[str, object]) -> IndicatorParameters:
        defaults = raw.get("indicator_defaults") or {}
        if not isinstance(defaults, Mapping):
            raise ConfigLoadError("'indicator_defaults' must be a mapping")
        params = IndicatorParameters(
            sma_fast=int(defaults.get("sma_fast", 20)),
            sma_slow=int(defaults.get("sma_slow", 100)),
            ema_fast=int(defaults.get("ema_fast", 20)),
            ema_slow=int(defaults.get("ema_slow", 100)),
            rsi_period=int(defaults.get("rsi_period", 14)),
            macd_fast=int(defaults.get("macd_fast", 12)),
            macd_slow=int(defaults.get("macd_slow", 26)),
            macd_signal=int(defaults.get("macd_signal", 9)),
            bollinger_period=int(defaults.get("bollinger_period", 20)),
            bollinger_std=float(defaults.get("bollinger_std", 2.0)),
            stochastic_period=int(defaults.get("stochastic_period", 14)),
            stochastic_signal=int(defaults.get("stochastic_signal", 3)),
            atr_period=int(defaults.get("atr_period", 14)),
        )
        params.validate()
        return params

    def _build_risk_profiles(self, raw: Mapping[str, object]) -> Dict[str, Dict[str, object]]:
        risk_profiles = raw.get("risk_profiles") or {}
        if not isinstance(risk_profiles, Mapping):
            raise ConfigLoadError("'risk_profiles' must be a mapping of profile names")

        def _parse_risk_params(base: Optional[Mapping[str, Any]], fallback: RiskParameters) -> RiskParameters:
            if base is None:
                return fallback
            if not isinstance(base, Mapping):
                raise ConfigLoadError("Risk parameter override must be a mapping")
            return fallback.merge(base)

        registry: Dict[str, Dict[str, object]] = {}
        for profile_name, profile_cfg in risk_profiles.items():
            if not isinstance(profile_cfg, Mapping):
                raise ConfigLoadError(f"risk_profiles[{profile_name!r}] must be a mapping")

            defaults_cfg = profile_cfg.get("defaults") or {}
            if not isinstance(defaults_cfg, Mapping):
                raise ConfigLoadError(f"risk_profiles[{profile_name!r}].defaults must be a mapping")

            base_long = RiskParameters(
                atr_stop_multiplier=float(defaults_cfg.get("long", {}).get("atr_stop_multiplier", 2.0)) if isinstance(defaults_cfg.get("long"), Mapping) else 2.0,
                atr_target_multiplier=float(defaults_cfg.get("long", {}).get("atr_target_multiplier", 3.0)) if isinstance(defaults_cfg.get("long"), Mapping) else 3.0,
                trailing_stop_multiplier=(
                    float(defaults_cfg.get("long", {}).get("trailing_stop_multiplier"))
                    if isinstance(defaults_cfg.get("long"), Mapping) and defaults_cfg.get("long", {}).get("trailing_stop_multiplier") is not None
                    else None
                ),
                max_holding_days=int(defaults_cfg.get("long", {}).get("max_holding_days", 8)) if isinstance(defaults_cfg.get("long"), Mapping) else 8,
                risk_per_trade_pct=float(defaults_cfg.get("long", {}).get("risk_per_trade_pct", 0.01)) if isinstance(defaults_cfg.get("long"), Mapping) else 0.01,
                position_size_pct=float(defaults_cfg.get("long", {}).get("position_size_pct", 1.0)) if isinstance(defaults_cfg.get("long"), Mapping) else 1.0,
            )
            base_long.validate()

            base_short = RiskParameters(
                atr_stop_multiplier=float(defaults_cfg.get("short", {}).get("atr_stop_multiplier", 2.0)) if isinstance(defaults_cfg.get("short"), Mapping) else 2.0,
                atr_target_multiplier=float(defaults_cfg.get("short", {}).get("atr_target_multiplier", 3.0)) if isinstance(defaults_cfg.get("short"), Mapping) else 3.0,
                trailing_stop_multiplier=(
                    float(defaults_cfg.get("short", {}).get("trailing_stop_multiplier"))
                    if isinstance(defaults_cfg.get("short"), Mapping) and defaults_cfg.get("short", {}).get("trailing_stop_multiplier") is not None
                    else None
                ),
                max_holding_days=int(defaults_cfg.get("short", {}).get("max_holding_days", 6)) if isinstance(defaults_cfg.get("short"), Mapping) else 6,
                risk_per_trade_pct=float(defaults_cfg.get("short", {}).get("risk_per_trade_pct", 0.01)) if isinstance(defaults_cfg.get("short"), Mapping) else 0.01,
                position_size_pct=float(defaults_cfg.get("short", {}).get("position_size_pct", 1.0)) if isinstance(defaults_cfg.get("short"), Mapping) else 1.0,
            )
            base_short.validate()

            profile_map: Dict[str, Dict[str, Dict[str, ResolvedRiskProfile]]] = {}

            for asset_class, timeframe_map in profile_cfg.items():
                if asset_class == "defaults":
                    continue
                if not isinstance(timeframe_map, Mapping):
                    raise ConfigLoadError(
                        f"risk_profiles[{profile_name!r}][{asset_class!r}] must be a mapping"
                    )
                asset_entry: Dict[str, Dict[str, ResolvedRiskProfile]] = {}
                for timeframe, volatility_map in timeframe_map.items():
                    if not isinstance(volatility_map, Mapping):
                        raise ConfigLoadError(
                            f"risk_profiles[{profile_name!r}][{asset_class!r}][{timeframe!r}] must be a mapping"
                        )
                    vol_entry: Dict[str, ResolvedRiskProfile] = {}
                    for volatility, risk_cfg in volatility_map.items():
                        if not isinstance(risk_cfg, Mapping):
                            raise ConfigLoadError(
                                "Risk profile override must be a mapping for "
                                f"profile={profile_name!r}, asset={asset_class!r}, timeframe={timeframe!r}, volatility={volatility!r}"
                            )
                        long_params = _parse_risk_params(risk_cfg.get("long"), base_long)
                        short_params = _parse_risk_params(risk_cfg.get("short"), base_short)
                        vol_entry[str(volatility)] = ResolvedRiskProfile(long=long_params, short=short_params)
                    asset_entry[str(timeframe)] = vol_entry
                profile_map[str(asset_class)] = asset_entry
            registry[str(profile_name)] = {
                "default": ResolvedRiskProfile(long=base_long, short=base_short),
                "overrides": profile_map,
            }
        return registry
    def _build_indicator_profiles(self, raw: Mapping[str, object]) -> Dict[str, Dict[str, Dict[str, IndicatorParameters]]]:
        profiles_raw = raw.get("indicator_profiles") or {}
        if not isinstance(profiles_raw, Mapping):
            raise ConfigLoadError("'indicator_profiles' must be a mapping")
        profiles: Dict[str, Dict[str, Dict[str, IndicatorParameters]]] = {}
        for asset_class, timeframe_map in profiles_raw.items():
            if not isinstance(timeframe_map, Mapping):
                raise ConfigLoadError(f"indicator_profiles[{asset_class!r}] must be a mapping")
            tf_profiles: Dict[str, Dict[str, IndicatorParameters]] = {}
            for timeframe, volatility_map in timeframe_map.items():
                if not isinstance(volatility_map, Mapping):
                    raise ConfigLoadError(
                        f"indicator_profiles[{asset_class!r}][{timeframe!r}] must be a mapping"
                    )
                vol_profiles: Dict[str, IndicatorParameters] = {}
                for volatility, overrides in volatility_map.items():
                    if overrides is None:
                        overrides = {}
                    if not isinstance(overrides, Mapping):
                        raise ConfigLoadError(
                            "Indicator override must be a mapping for "
                            f"asset={asset_class!r}, timeframe={timeframe!r}, volatility={volatility!r}"
                        )
                    vol_profiles[volatility] = self._indicator_defaults.merge(overrides)
                tf_profiles[timeframe] = vol_profiles
            profiles[str(asset_class)] = tf_profiles
        return profiles

    def _build_asset_profiles(
        self, raw: Mapping[str, object]
    ) -> Tuple[AssetProfile, Dict[str, AssetProfile], Tuple[Tuple[Pattern[str], AssetProfile], ...]]:
        assets = raw.get("assets") or {}
        if not isinstance(assets, Mapping):
            raise ConfigLoadError("'assets' must be a mapping")
        defaults_raw = assets.get("defaults") or {}
        if not isinstance(defaults_raw, Mapping):
            raise ConfigLoadError("'assets.defaults' must be a mapping")
        default_profile = AssetProfile(
            asset_class=str(defaults_raw.get("asset_class", "equities")),
            timeframe=str(defaults_raw.get("timeframe", "daily")),
            risk_profile=str(defaults_raw.get("risk_profile", "base")),
            volatility_override=defaults_raw.get("volatility"),
        )
        items = assets.get("items") or []
        if not isinstance(items, list):
            raise ConfigLoadError("'assets.items' must be a list")

        code_map: Dict[str, AssetProfile] = {}
        pattern_entries: list[Tuple[Pattern[str], AssetProfile]] = []
        for item in items:
            if not isinstance(item, Mapping):
                raise ConfigLoadError("Each assets.items entry must be a mapping")
            profile = AssetProfile(
                asset_class=str(item.get("asset_class", default_profile.asset_class)),
                timeframe=str(item.get("timeframe", default_profile.timeframe)),
                risk_profile=str(item.get("risk_profile", default_profile.risk_profile)),
                volatility_override=item.get("volatility", default_profile.volatility_override),
            )
            contract_code = item.get("contract_code")
            pattern = item.get("pattern")
            if contract_code:
                code_map[str(contract_code)] = profile
            elif pattern:
                pattern_entries.append((re.compile(str(pattern)), profile))
        return default_profile, code_map, tuple(pattern_entries)

    def _build_volatility_thresholds(self, raw: Mapping[str, object]) -> Dict[str, Tuple[float, float]]:
        buckets_raw = raw.get("volatility_buckets") or {}
        if not isinstance(buckets_raw, Mapping):
            raise ConfigLoadError("'volatility_buckets' must be a mapping")
        thresholds: Dict[str, Tuple[float, float]] = {}
        for key, bucket in buckets_raw.items():
            if not isinstance(bucket, Mapping):
                raise ConfigLoadError(f"volatility_buckets[{key!r}] must be a mapping")
            atr_cfg = bucket.get("atr_pct") if "atr_pct" in bucket else bucket
            if not isinstance(atr_cfg, Mapping):
                raise ConfigLoadError(f"volatility_buckets[{key!r}].atr_pct must be a mapping")
            low = float(atr_cfg.get("low", 0.0))
            high = float(atr_cfg.get("high", 1.0))
            if low < 0 or high <= 0 or high <= low:
                raise ConfigLoadError(
                    "volatility bucket thresholds must satisfy 0 <= low < high"
                )
            thresholds[str(key)] = (low, high)
        return thresholds

    # ----------------------------------------------------------------- helpers
    def _match_asset_profile(
        self,
        contract_code: Optional[str],
        explicit_asset_class: Optional[str],
        explicit_timeframe: Optional[str],
        explicit_volatility: Optional[str],
    ) -> AssetProfile:
        profile = self._asset_defaults
        if contract_code and contract_code in self._asset_code_map:
            profile = self._asset_code_map[contract_code]
        elif contract_code:
            for pattern, pattern_profile in self._asset_patterns:
                if pattern.search(contract_code):
                    profile = pattern_profile
                    break
        if explicit_asset_class:
            profile = replace(profile, asset_class=explicit_asset_class)
        if explicit_timeframe:
            profile = replace(profile, timeframe=explicit_timeframe)
        if explicit_volatility:
            profile = replace(profile, volatility_override=explicit_volatility)
        return profile

    def _lookup_risk_profile(
        self,
        profile_name: Optional[str],
        asset_class: str,
        timeframe: str,
        volatility: str,
    ) -> Optional[ResolvedRiskProfile]:
        if not self._risk_profiles:
            return None

        selected_name = profile_name or "base"
        registry = self._risk_profiles.get(selected_name) or self._risk_profiles.get("base")
        if registry is None:
            return None

        default_profile = registry.get("default")  # type: ignore[assignment]
        overrides = registry.get("overrides", {})  # type: ignore[assignment]

        def _resolve_from_overrides(source) -> Optional[ResolvedRiskProfile]:
            if not source:
                return None
            asset_map = source.get(asset_class) or source.get("default")
            if not asset_map:
                return None
            timeframe_map = asset_map.get(timeframe) or asset_map.get("default")
            if not timeframe_map:
                return None
            return timeframe_map.get(volatility) or timeframe_map.get("default")

        risk = _resolve_from_overrides(overrides)
        if risk is None and selected_name != "base":
            base_registry = self._risk_profiles.get("base")
            if base_registry:
                risk = _resolve_from_overrides(base_registry.get("overrides", {}))  # type: ignore[arg-type]
                if risk is None:
                    risk = base_registry.get("default")  # type: ignore[index]
        if risk is None:
            risk = default_profile
        return risk

    def _lookup_indicator_parameters(
        self, asset_class: str, timeframe: str, volatility: str
    ) -> IndicatorParameters:
        asset_profiles = self._indicator_profiles.get(asset_class)
        fallback_profiles = self._indicator_profiles.get("default")

        def _resolve_from_maps(maps: Optional[Mapping[str, Mapping[str, IndicatorParameters]]]) -> Optional[IndicatorParameters]:
            if not maps:
                return None
            tf_map = maps.get(timeframe) or maps.get("default")
            if not tf_map:
                return None
            return tf_map.get(volatility) or tf_map.get("default")

        params = _resolve_from_maps(asset_profiles)
        if params is None:
            params = _resolve_from_maps(fallback_profiles)
        if params is None:
            params = self._indicator_defaults
        return params

    def _estimate_volatility_bucket(self, data: pd.DataFrame, asset_class: str) -> str:
        thresholds = self._volatility_thresholds.get(asset_class) or self._volatility_thresholds.get("default")
        if thresholds is None:
            return "medium"
        atr_pct = self._compute_latest_atr_pct(data, self._indicator_defaults.atr_period)
        if atr_pct is None:
            return "medium"
        low, high = thresholds
        if atr_pct < low:
            return "low"
        if atr_pct < high:
            return "medium"
        return "high"

    @staticmethod
    def _compute_latest_atr_pct(data: pd.DataFrame, window: int) -> Optional[float]:
        if data.empty:
            return None
        required_columns = {"high", "low", "close"}
        if not required_columns.issubset(set(data.columns)):
            return None
        working = data.loc[:, ["high", "low", "close"]].copy()
        working.sort_index(inplace=True)
        prev_close = working["close"].shift(1)
        high_low = working["high"] - working["low"]
        high_prev = (working["high"] - prev_close).abs()
        low_prev = (working["low"] - prev_close).abs()
        true_range = pd.concat([high_low, high_prev, low_prev], axis=1).max(axis=1)
        atr = true_range.rolling(window=window, min_periods=1).mean()
        current_close = working["close"].abs()
        if current_close.empty:
            return None
        last_close = current_close.iloc[-1]
        if last_close == 0:
            return None
        latest_atr = atr.iloc[-1]
        if pd.isna(latest_atr):
            return None
        return float(latest_atr / last_close)

    # ------------------------------------------------------------------ public
    def resolve_indicator_profile(
        self,
        contract_code: Optional[str],
        data: pd.DataFrame,
        *,
        asset_class: Optional[str] = None,
        timeframe: Optional[str] = None,
        volatility: Optional[str] = None,
    ) -> ResolvedIndicatorProfile:
        """Resolve indicator parameters for a contract/data slice."""
        asset_profile = self._match_asset_profile(contract_code, asset_class, timeframe, volatility)
        resolved_volatility = asset_profile.volatility_override or volatility
        if not resolved_volatility:
            resolved_volatility = self._estimate_volatility_bucket(data, asset_profile.asset_class)
        params = self._lookup_indicator_parameters(
            asset_profile.asset_class,
            asset_profile.timeframe,
            resolved_volatility,
        )
        risk_settings = self._lookup_risk_profile(
            asset_profile.risk_profile,
            asset_profile.asset_class,
            asset_profile.timeframe,
            resolved_volatility,
        )
        return ResolvedIndicatorProfile(
            asset_class=asset_profile.asset_class,
            timeframe=asset_profile.timeframe,
            volatility=resolved_volatility,
            parameters=params,
            risk=risk_settings,
        )


def load_analytics_config() -> AnalyticsConfig:
    """Load analytics configuration from disk."""
    path = get_analytics_config_path()
    raw = load_yaml_config(path)
    return AnalyticsConfig(raw)


_config_instance: Optional[AnalyticsConfig] = None


def get_analytics_config(force_reload: bool = False) -> AnalyticsConfig:
    """Return singleton analytics configuration instance."""
    global _config_instance
    if force_reload or _config_instance is None:
        _config_instance = load_analytics_config()
    return _config_instance



