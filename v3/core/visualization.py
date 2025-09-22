"""Utility functions that build charts for Streamlit pages."""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

MATPLOTLIB_AVAILABLE = True
PLOTLY_AVAILABLE = True
MPLFINANCE_AVAILABLE = True

try:  # pragma: no cover - optional dependency
    import matplotlib.pyplot as plt  # type: ignore
except Exception as exc:  # pragma: no cover
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not available: %s", exc)

try:  # pragma: no cover - optional dependency
    import plotly.express as px  # type: ignore
except Exception as exc:  # pragma: no cover
    PLOTLY_AVAILABLE = False
    logger.warning("plotly not available: %s", exc)

try:  # pragma: no cover - optional dependency
    import mplfinance as mpf  # type: ignore
except Exception as exc:  # pragma: no cover
    MPLFINANCE_AVAILABLE = False
    logger.warning("mplfinance not available: %s", exc)


def safe_plot_matplotlib(fig):
    if MATPLOTLIB_AVAILABLE and fig is not None:
        try:
            st.pyplot(fig)
        except Exception as exc:  # pragma: no cover - streamlit runtime
            logger.warning("matplotlib rendering failed: %s", exc)
            st.info("График создан, но произошла ошибка при его отображении.")
    else:
        st.info("matplotlib не установлен — график недоступен в этом режиме.")


def safe_plot_interactive(fig):
    if PLOTLY_AVAILABLE and fig is not None:
        try:
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:  # pragma: no cover
            logger.warning("plotly rendering failed: %s", exc)
            st.info("Интерактивный график создан, но не может быть показан.")
    else:
        st.info("Plotly не установлен — интерактивный график недоступен.")


def plot_daily_analysis(data: pd.DataFrame, date_value):
    filtered = data[(data["date"] == date_value) & (data["metric_type"] == "Открытые позиции")]
    if filtered.empty:
        if MATPLOTLIB_AVAILABLE:
            fig, ax = plt.subplots(figsize=(8, 4))  # type: ignore
            ax.text(0.5, 0.5, "Нет данных для выбранной даты", ha="center", va="center", fontsize=14)
            ax.axis("off")
            return fig
        st.info("Нет данных для выбранной даты")
        return None

    if MATPLOTLIB_AVAILABLE:
        fig, ax = plt.subplots(figsize=(12, 8))  # type: ignore
        bars = ax.barh(filtered["contract_code"], filtered["value1"], color="skyblue")
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height() / 2, f"{width:.2f}", va="center", ha="left", fontsize=10)
        ax.set_title(f"Открытые позиции на дату {date_value}", fontsize=16, pad=20)
        ax.set_xlabel("Value1", fontsize=14)
        ax.set_ylabel("Contract Code", fontsize=14)
        ax.tick_params(axis="both", labelsize=12)
        ax.grid(True, linestyle="--", alpha=0.7)
        return fig

    st.write(f"Открытые позиции на дату {date_value}")
    st.dataframe(filtered[["contract_code", "value1"]])
    return None


def plot_stock_analysis(data: pd.DataFrame, stock_code: str):
    stock_data = data[(data["contract_code"] == stock_code) & (data["metric_type"] == "Открытые позиции")].sort_values("date")
    if stock_data.empty:
        if MATPLOTLIB_AVAILABLE:
            fig, ax = plt.subplots()  # type: ignore
            ax.text(0.5, 0.5, "Нет данных для выбранного тикера", ha="center", va="center")
            return fig
        st.info("Нет данных для выбранного тикера")
        return None

    if MATPLOTLIB_AVAILABLE:
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 18))  # type: ignore
        ax1.plot(stock_data["date"], stock_data["value1"], label="Value1", marker="o", color="black")
        ax1.plot(stock_data["date"], stock_data["value4"], label="Value4", marker="o", color="blue")
        ax1.set_title(f"Анализ позиций для {stock_code}")
        ax1.set_xlabel("Дата")
        ax1.set_ylabel("Значение")
        ax1.legend()
        ax1.grid(True)

        ax2.plot(stock_data["date"], stock_data["value2"], label="Value2", marker="o", color="red")
        ax2.plot(stock_data["date"], stock_data["value3"], label="Value3", marker="o", color="green")
        ax2.set_title(f"Дополнительный анализ для {stock_code}")
        ax2.set_xlabel("Дата")
        ax2.set_ylabel("Значение")
        ax2.legend()
        ax2.grid(True)

        ax3.plot(stock_data["date"], stock_data["value5"], label="Value5", marker="o", color="purple")
        ax3.set_title(f"Дополнительный анализ (Value5) для {stock_code}")
        ax3.set_xlabel("Дата")
        ax3.set_ylabel("Значение")
        ax3.legend()
        ax3.grid(True)
        return fig

    st.write(f"Анализ позиций для {stock_code} — упрощённый режим (без matplotlib)")
    try:
        st.line_chart(stock_data.set_index("date")[["value1", "value4"]])
        st.line_chart(stock_data.set_index("date")[["value2", "value3"]])
        st.line_chart(stock_data.set_index("date")[["value5"]])
    except Exception:  # pragma: no cover - streamlit runtime
        st.dataframe(stock_data[["date", "value1", "value2", "value3", "value4", "value5"]])
    return None


def plot_interactive_chart(data: pd.DataFrame, stock_code: str):
    stock_data = data[data["contract_code"] == stock_code]
    if stock_data.empty:
        if PLOTLY_AVAILABLE:
            return px.scatter(title=f"Нет данных для {stock_code}")  # type: ignore
        st.info(f"Нет данных для {stock_code}")
        return None

    if PLOTLY_AVAILABLE:
        fig = px.line(  # type: ignore
            stock_data,
            x="date",
            y="value1",
            title=f"Интерактивный график для {stock_code}",
            labels={"date": "Дата", "value1": "Value1"},
        )
        return fig

    try:
        st.line_chart(stock_data.set_index("date")[["value1"]])
    except Exception:  # pragma: no cover - streamlit runtime
        st.dataframe(stock_data[["date", "value1"]])
    return None
