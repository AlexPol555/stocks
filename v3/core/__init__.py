"""Core package exposing reusable building blocks for the Streamlit app."""

from . import database
from .analyzer import StockAnalyzer
from .data_loader import load_csv_data
from .indicators import (
    calculate_additional_filters,
    calculate_additional_indicators,
    calculate_basic_indicators,
    calculate_technical_indicators,
    clear_get_calculated_data,
    generate_adaptive_signals,
    generate_final_adaptive_signals,
    generate_new_adaptive_signals,
    generate_trading_signals,
    get_calculated_data,
    vectorized_dynamic_profit,
)
from .jobs.auto_update import auto_update_all_tickers, normalize_ticker, update_missing_market_data
from .orders.service import create_order, tinkoff_enabled
from . import demo_trading
from .populate import bulk_populate_database_from_csv, incremental_populate_database_from_csv
from .visualization import (
    plot_daily_analysis,
    plot_interactive_chart,
    plot_stock_analysis,
    safe_plot_interactive,
    safe_plot_matplotlib,
)

__all__ = [
    "StockAnalyzer",
    "auto_update_all_tickers",
    "bulk_populate_database_from_csv",
    "calculate_additional_filters",
    "calculate_additional_indicators",
    "calculate_basic_indicators",
    "calculate_technical_indicators",
    "clear_get_calculated_data",
    "create_order",
    "database",
    "generate_adaptive_signals",
    "generate_final_adaptive_signals",
    "generate_new_adaptive_signals",
    "generate_trading_signals",
    "get_calculated_data",
    "incremental_populate_database_from_csv",
    "load_csv_data",
    "normalize_ticker",
    "plot_daily_analysis",
    "plot_interactive_chart",
    "plot_stock_analysis",
    "safe_plot_interactive",
    "safe_plot_matplotlib",
    "tinkoff_enabled",
    "update_missing_market_data",
    "demo_trading",
    "vectorized_dynamic_profit",
]
