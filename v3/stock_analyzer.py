"""Backwards compatibility shim exposing :class:`core.analyzer.StockAnalyzer`."""
from core.analyzer import StockAnalyzer  # noqa: F401

__all__ = ["StockAnalyzer"]
