"""High level indicator pipeline exposed to Streamlit pages."""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from .calculations import calculate_additional_indicators, calculate_basic_indicators, generate_trading_signals
from .profit import vectorized_dynamic_profit
from .signals import generate_adaptive_signals, generate_final_adaptive_signals, generate_new_adaptive_signals

logger = logging.getLogger(__name__)

SKLEARN_AVAILABLE = True
try:  # pragma: no cover - optional dependency
    from sklearn.ensemble import RandomForestClassifier  # noqa: F401
    from sklearn.model_selection import GridSearchCV, train_test_split  # noqa: F401
except Exception as exc:  # pragma: no cover
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn не доступна: %s", exc)

    class RandomForestClassifier:  # type: ignore
        def __init__(self, *args, **kwargs):
            logger.warning("Используется заглушка RandomForestClassifier (sklearn отсутствует).")

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
        st.warning("scikit-learn не установлен. Анализ работает в упрощённом режиме.")
except Exception:  # pragma: no cover - streamlit not initialised
    pass


def calculate_technical_indicators(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    result = calculate_basic_indicators(result)
    result = generate_trading_signals(result)
    result = calculate_additional_indicators(result)
    result = generate_adaptive_signals(result, use_adaptive=True)
    result = generate_new_adaptive_signals(result)

    if "ATR" not in result.columns:
        result = calculate_additional_indicators(result)

    result = generate_final_adaptive_signals(result)
    result = vectorized_dynamic_profit(result, "Signal", "Dynamic_Profit_Base", "Exit_Date_Base", "Exit_Price_Base")
    result = vectorized_dynamic_profit(
        result,
        "Adaptive_Buy_Signal",
        "Dynamic_Profit_Adaptive_Buy",
        "Exit_Date_Adaptive_Buy",
        "Exit_Price_Adaptive_Buy",
    )
    result = vectorized_dynamic_profit(
        result,
        "Adaptive_Sell_Signal",
        "Dynamic_Profit_Adaptive_Sell",
        "Exit_Date_Adaptive_Sell",
        "Exit_Price_Adaptive_Sell",
        is_short=True,
    )
    result = vectorized_dynamic_profit(
        result,
        "New_Adaptive_Buy_Signal",
        "Dynamic_Profit_New_Adaptive_Buy",
        "Exit_Date_New_Adaptive_Buy",
        "Exit_Price_New_Adaptive_Buy",
    )
    result = vectorized_dynamic_profit(
        result,
        "New_Adaptive_Sell_Signal",
        "Dynamic_Profit_New_Adaptive_Sell",
        "Exit_Date_New_Adaptive_Sell",
        "Exit_Price_New_Adaptive_Sell",
        is_short=True,
    )
    result = vectorized_dynamic_profit(
        result,
        "Final_Buy_Signal",
        "Dynamic_Profit_Final_Buy",
        "Exit_Date_Final_Buy",
        "Exit_Price_Final_Buy",
    )
    return result


@st.cache_data(show_spinner=True)
def get_calculated_data(_conn) -> pd.DataFrame:
    import core.database as database

    try:
        merge_data = database.mergeMetrDaily(_conn)
    except Exception as exc:
        st.warning(f"Ошибка при вызове mergeMetrDaily: {exc}")
        return pd.DataFrame()

    if merge_data is None or merge_data.empty:
        st.warning("Нет данных: mergeMetrDaily вернул пустой DataFrame. Проверьте таблицы daily_data и metrics в БД.")
        return pd.DataFrame()

    results = []
    for contract, group in merge_data.groupby("contract_code"):
        try:
            results.append(calculate_technical_indicators(group.copy()))
        except Exception as exc:
            st.warning(f"Ошибка обработки контракта {contract}: {exc}")

    if not results:
        st.warning("После обработки групп не осталось данных для объединения (results пуст).")
        return pd.DataFrame()

    try:
        df_all = pd.concat(results, ignore_index=True)
        return df_all.drop_duplicates()
    except Exception as exc:
        st.error(f"Ошибка объединения результатов: {exc}")
        return pd.DataFrame()


def clear_get_calculated_data() -> None:
    get_calculated_data.clear()
