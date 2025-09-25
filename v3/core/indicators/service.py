"""High level indicator pipeline exposed to Streamlit pages."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd
import streamlit as st

from core.analytics import (
    ScoringConfig,
    ScoreWeights,
    TradingCosts,
    apply_risk_management,
    compute_signal_scores,
)
from core.config import IndicatorParameters, ResolvedIndicatorProfile, get_analytics_config

from .calculations import (
    ATR_COL,
    EMA_FAST_COL,
    EMA_SLOW_COL,
    MACD_COL,
    MACD_SIGNAL_COL,
    RSI_COL,
    SMA_FAST_COL,
    SMA_SLOW_COL,
    calculate_additional_indicators,
    calculate_basic_indicators,
    generate_trading_signals,
)
from .signals import generate_adaptive_signals, generate_final_adaptive_signals, generate_new_adaptive_signals

logger = logging.getLogger(__name__)

SKLEARN_AVAILABLE = True
try:  # pragma: no cover - optional dependency
    from sklearn.ensemble import RandomForestClassifier  # noqa: F401
    from sklearn.model_selection import GridSearchCV, train_test_split  # noqa: F401
except Exception as exc:  # pragma: no cover
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn недоступен: %s", exc)

    class RandomForestClassifier:  # type: ignore
        def __init__(self, *args, **kwargs):
            logger.warning("Используется заглушка RandomForestClassifier (sklearn не установлен).")

        def fit(self, X, y):
            return self

        def predict(self, X):
            try:
                import numpy as np

                return np.zeros(len(X), dtype=int)
            except Exception:  # pragma: no cover - defensive
                return [0] * len(X)

    def train_test_split(X, y, *args, **kwargs):  # type: ignore
        n = len(X)
        split = max(1, int(n * 0.8))
        return X[:split], X[split:], y[:split], y[split:]

    class GridSearchCV:  # type: ignore
        def __init__(self, estimator, param_grid, *args, **kwargs):
            self.estimator = estimator
            self.param_grid = param_grid
            self.best_estimator_ = estimator

        def fit(self, X, y):
            self.estimator.fit(X, y)
            self.best_estimator_ = self.estimator
            return self

try:  # pragma: no cover - streamlit runtime
    if not SKLEARN_AVAILABLE:
        st.warning("scikit-learn недоступен. Проверьте requirements.txt.")
except Exception:  # pragma: no cover - streamlit not initialised
    pass


def _resolve_indicator_profile(
    data: pd.DataFrame,
    *,
    contract_code: Optional[str] = None,
    asset_class: Optional[str] = None,
    timeframe: Optional[str] = None,
    volatility: Optional[str] = None,
) -> ResolvedIndicatorProfile:
    config = get_analytics_config()
    return config.resolve_indicator_profile(
        contract_code,
        data,
        asset_class=asset_class,
        timeframe=timeframe,
        volatility=volatility,
    )


def _resolve_scoring_config(profile: ResolvedIndicatorProfile) -> ScoringConfig:
    asset_class = profile.asset_class.lower()
    volatility = profile.volatility.lower()

    if asset_class == "futures":
        weights = ScoreWeights(trend=0.3, momentum=0.25, volatility=0.25, volume=0.1, sentiment=0.1)
    elif asset_class == "commodities":
        weights = ScoreWeights(trend=0.32, momentum=0.28, volatility=0.2, volume=0.1, sentiment=0.1)
    else:  # equities and default
        weights = ScoreWeights(trend=0.35, momentum=0.3, volatility=0.2, volume=0.1, sentiment=0.05)

    scale = 1.0
    long_threshold = 0.6
    short_threshold = 0.6

    if volatility == "low":
        scale = 0.8
        long_threshold = 0.55
        short_threshold = 0.55
    elif volatility == "high":
        scale = 1.2
        long_threshold = 0.65
        short_threshold = 0.65

    return ScoringConfig(
        weights=weights,
        activation_scale=scale,
        long_threshold=long_threshold,
        short_threshold=short_threshold,
    )


def _resolve_trading_costs() -> TradingCosts:
    def _env_float(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, default))
        except Exception:
            return default

    return TradingCosts(
        commission_pct=_env_float("STOCKS_COMMISSION_PCT", 0.0005),
        tax_pct=_env_float("STOCKS_TAX_PCT", 0.13),
        slippage_pct=_env_float("STOCKS_SLIPPAGE_PCT", 0.0003),
        borrow_daily_pct=_env_float("STOCKS_BORROW_DAILY_PCT", 0.0001),
        leverage_daily_pct=_env_float("STOCKS_LEVERAGE_DAILY_PCT", 0.00005),
    )


def _ensure_compatibility_columns(result: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "Adaptive_Buy": "long",
        "Adaptive_Sell": "short",
        "New_Adaptive_Buy": "long",
        "New_Adaptive_Sell": "short",
        "Final_Buy": "long",
        "Final_Sell": "short",
    }
    for legacy, prefix in mapping.items():
        net_col = f"{prefix}_trade_net_pct"
        exit_price_col = f"{prefix}_trade_exit_price"
        exit_date_col = f"{prefix}_trade_exit_date"
        holding_col = f"{prefix}_trade_holding_days"
        mfe_col = f"{prefix}_trade_mfe"
        mae_col = f"{prefix}_trade_mae"

        result[f"Dynamic_Profit_{legacy}"] = result.get(net_col)
        result[f"Exit_Price_{legacy}"] = result.get(exit_price_col)
        result[f"Exit_Date_{legacy}"] = result.get(exit_date_col)
        result[f"Holding_{legacy}_Days"] = result.get(holding_col)
        result[f"MFE_{legacy}"] = result.get(mfe_col)
        result[f"MAE_{legacy}"] = result.get(mae_col)
    return result


def calculate_technical_indicators(
    data: pd.DataFrame,
    *,
    contract_code: Optional[str] = None,
    asset_class: Optional[str] = None,
    timeframe: Optional[str] = None,
    volatility: Optional[str] = None,
    indicator_params: Optional[IndicatorParameters] = None,
) -> pd.DataFrame:
    result = data.copy()
    profile = _resolve_indicator_profile(
        result,
        contract_code=contract_code,
        asset_class=asset_class,
        timeframe=timeframe,
        volatility=volatility,
    )
    if indicator_params is not None:
        indicator_params.validate()
        params = indicator_params
        profile = ResolvedIndicatorProfile(
            asset_class=profile.asset_class,
            timeframe=profile.timeframe,
            volatility=profile.volatility,
            parameters=indicator_params,
            risk=profile.risk,
        )
    else:
        params = profile.parameters

    result = calculate_basic_indicators(result, params)
    result = generate_trading_signals(result)
    result = calculate_additional_indicators(result, params)
    result = generate_adaptive_signals(result, use_adaptive=True)
    result = generate_new_adaptive_signals(result)

    if ATR_COL not in result.columns:
        result = calculate_additional_indicators(result, params)

    result = generate_final_adaptive_signals(result)

    scoring_config = _resolve_scoring_config(profile)
    result = compute_signal_scores(result, config=scoring_config)

    result["Final_Buy_Signal"] = result["long_signal"]
    result["Final_Sell_Signal"] = result["short_signal"]
    result["Signal"] = result["long_signal"] - result["short_signal"]

    trading_costs = _resolve_trading_costs()
    if profile.risk is not None:
        risk_artifacts = apply_risk_management(
            result,
            risk_profile=profile.risk,
            costs=trading_costs,
        )
        result = risk_artifacts["frame"]
        long_trades_df = risk_artifacts.get("long_trades")
        short_trades_df = risk_artifacts.get("short_trades")
        result.attrs["long_trades"] = [] if long_trades_df is None or long_trades_df.empty else long_trades_df.to_dict("records")
        result.attrs["short_trades"] = [] if short_trades_df is None or short_trades_df.empty else short_trades_df.to_dict("records")
    else:
        for prefix in ("long", "short"):
            for col in [
                f"{prefix}_trade_net_pct",
                f"{prefix}_trade_gross_pct",
                f"{prefix}_trade_exit_price",
                f"{prefix}_trade_exit_date",
                f"{prefix}_trade_holding_days",
                f"{prefix}_trade_mfe",
                f"{prefix}_trade_mae",
            ]:
                if col not in result.columns:
                    result[col] = pd.NA

    result = _ensure_compatibility_columns(result)

    result["resolved_asset_class"] = profile.asset_class
    result["resolved_timeframe"] = profile.timeframe
    result["resolved_volatility"] = profile.volatility
    result.attrs["indicator_profile"] = profile
    result.attrs["scoring_config"] = scoring_config
    result.attrs["trading_costs"] = trading_costs
    return result


@st.cache_data(show_spinner=True)
def get_calculated_data(
    db_path: Union[str, Path],
    *,
    indicator_overrides: Optional[Dict[str, Any]] = None,
    data_version: Optional[str] = None,
) -> pd.DataFrame:
    """Собрать рассчитанные данные по всем контрактам."""
    from core import database

    resolved_path = Path(db_path).expanduser().resolve()
    conn = None
    try:
        conn = database.get_connection(resolved_path)
        merge_data = database.mergeMetrDaily(conn)
    except Exception as exc:
        st.warning(f"Ошибка вызова mergeMetrDaily: {exc}")
        merge_data = pd.DataFrame()
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logger.exception("Failed to close database connection for %s", resolved_path)

    if merge_data is None or merge_data.empty:
        st.warning("Нет данных: mergeMetrDaily не вернул DataFrame. Проверьте таблицы daily_data и metrics.")
        return pd.DataFrame()

    results = []
    for contract, group in merge_data.groupby("contract_code"):
        try:
            kwargs: Dict[str, Any] = indicator_overrides.get(contract, {}) if indicator_overrides else {}
            results.append(
                calculate_technical_indicators(
                    group.copy(),
                    contract_code=contract,
                    asset_class=kwargs.get("asset_class"),
                    timeframe=kwargs.get("timeframe"),
                    volatility=kwargs.get("volatility"),
                )
            )
        except Exception as exc:
            st.warning(f"Ошибка расчета показателей для {contract}: {exc}")
            logger.exception("Indicator calculation failed for %s", contract)

    if not results:
        st.warning("Не удалось собрать показатели: список результатов пуст.")
        return pd.DataFrame()

    try:
        df_all = pd.concat(results, ignore_index=True)
        return df_all.drop_duplicates()
    except Exception as exc:
        st.error(f"Ошибка объединения результатов: {exc}")
        return pd.DataFrame()


def clear_get_calculated_data() -> None:
    get_calculated_data.clear()
