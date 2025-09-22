"""Profit calculation utilities."""
from __future__ import annotations

import numpy as np
import pandas as pd


def vectorized_dynamic_profit(
    data: pd.DataFrame,
    signal_col: str,
    profit_col: str,
    exit_date_col: str,
    exit_price_col: str,
    *,
    max_holding_days: int = 3,
    is_short: bool = False,
) -> pd.DataFrame:
    data = data.copy()
    close = data["close"].values
    n = len(data)

    profits = np.full(n, np.nan, dtype=float)
    exit_dates = np.array([None] * n)
    exit_prices = np.full(n, np.nan, dtype=float)

    for i in np.where(data[signal_col] != 0)[0]:
        entry_price = close[i]
        exit_price = None
        exit_date = None

        start = i + 1
        end = min(i + max_holding_days + 1, n)

        if start >= n:
            exit_index = min(i + max_holding_days, n - 1)
            exit_price = entry_price * (1 - 0.005) if not is_short else entry_price * (1 + 0.005)
            exit_date = data.iloc[exit_index].get("date", None)
        else:
            period_data = data.iloc[start:end]

            if not is_short:
                condition = period_data["high"] >= entry_price * (1 + 0.005)
                valid_days = period_data[condition]

                if not valid_days.empty:
                    exit_price = valid_days["high"].max()
                    exit_date = valid_days.loc[valid_days["high"].idxmax()]["date"]
                else:
                    exit_price = entry_price * (1 - 0.005)
                    exit_date = period_data.iloc[-1].get("date", None)
            else:
                condition = period_data["low"] <= entry_price * (1 - 0.005)
                valid_days = period_data[condition]

                if not valid_days.empty:
                    exit_price = valid_days["low"].min()
                    exit_date = valid_days.loc[valid_days["low"].idxmin()]["date"]
                else:
                    exit_price = entry_price * (1 + 0.005)
                    exit_date = period_data.iloc[-1].get("date", None)

        if exit_price is not None:
            if not is_short:
                profit = (exit_price - entry_price) / entry_price * 100
            else:
                profit = (entry_price - exit_price) / entry_price * 100
            profits[i] = profit
            exit_prices[i] = exit_price
            exit_dates[i] = exit_date

    data[profit_col] = profits
    data[exit_date_col] = exit_dates
    data[exit_price_col] = exit_prices
    return data
