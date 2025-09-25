"""Core analytics primitives.

This module hosts :class:`StockAnalyzer` that encapsulates all interactions with
Tinkoff Invest as well as the database fallbacks that were previously spread
across the legacy ``stock_analyzer.py`` file.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Callable, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# --- optional tinkoff SDK -------------------------------------------------
TINKOFF_AVAILABLE = True
try:  # pragma: no cover - depends on environment
    from tinkoff.invest import CandleInterval, Client  # type: ignore
    from tinkoff.invest.utils import quotation_to_decimal  # type: ignore
except Exception as exc:  # pragma: no cover - executed when SDK is missing
    TINKOFF_AVAILABLE = False
    Client = None  # type: ignore
    CandleInterval = None  # type: ignore

    def quotation_to_decimal(quotation) -> float:  # type: ignore[override]
        """Gracefully convert a tinkoff quotation replacement to ``float``."""
        try:
            units = float(getattr(quotation, "units", 0))
            nano = float(getattr(quotation, "nano", 0))
            return units + nano / 1e9
        except Exception:  # pragma: no cover - defensive
            return 0.0

    logger.warning("tinkoff-invest SDK is not available: %s", exc)


@dataclass
class StockAnalyzer:
    """High level facade around market data sources.

    Parameters
    ----------
    api_key:
        Access token for Tinkoff Invest. When omitted, the analyzer falls back to offline mode.
    db_conn:
        Optional SQLite connection used as a local data source when the API is unavailable.
    warn_callback:
        Optional callable that allows the caller to surface warning messages in the UI layer.
    """

    api_key: Optional[str]
    db_conn: Optional[object] = None
    warn_callback: Optional[Callable[[str], None]] = None

    def _warn(self, message: str) -> None:
        if callable(self.warn_callback):
            try:
                self.warn_callback(message)
                return
            except Exception:
                logger.exception("warn_callback failed")
        logger.warning(message)

    # ------------------------------------------------------------------ utils
    def _figi_from_db_or_empty(self) -> Dict[str, str]:
        """Attempt to build ticker -> FIGI mapping from the database."""
        if not self.db_conn:
            logger.info("StockAnalyzer: DB connection not provided вЂ“ returning empty mapping")
            return {}

        try:
            query = (
                "SELECT contract_code, figi FROM companies "
                "WHERE figi IS NOT NULL AND figi != ''"
            )
            df = pd.read_sql_query(query, self.db_conn)
            return dict(zip(df["contract_code"], df["figi"]))
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to fetch FIGI mapping from DB: %s", exc)
            return {}

    # ---------------------------------------------------------------- FIGI map
    def get_figi_mapping(self) -> Dict[str, str]:
        """Return a ticker -> FIGI mapping.

        Priority: online API (when SDK + API key available) в†’ database fallback
        в†’ empty mapping.
        """
        if not self.api_key:
            logger.warning("Tinkoff API key not provided вЂ“ falling back to DB mapping")
            try:
                self._warn(
                    "Tinkoff API key РЅРµ Р·Р°РґР°РЅ: FIGI Р±СѓРґСѓС‚ С‡РёС‚Р°С‚СЊСЃСЏ С‚РѕР»СЊРєРѕ РёР· Р±Р°Р·С‹ РґР°РЅРЅС‹С…."
                )
            except Exception:  # pragma: no cover - streamlit not initialised
                pass
            return self._figi_from_db_or_empty()

        try:  # pragma: no cover - depends on external SDK
            from tinkoff.invest import Client as _Client  # type: ignore
        except Exception as exc:
            logger.warning("Tinkoff SDK cannot be imported (%s). Using DB fallback.", exc)
            try:
                self._warn("Tinkoff SDK РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅ. РџСЂРѕРІРµСЂСЊС‚Рµ requirements.txt.")
            except Exception:  # pragma: no cover
                pass
            return self._figi_from_db_or_empty()

        try:  # pragma: no cover - depends on network
            with _Client(self.api_key) as client:
                instruments = client.instruments.shares().instruments
                mapping = {
                    share.ticker: share.figi
                    for share in instruments
                    if getattr(share, "ticker", None)
                }
                if not mapping:
                    logger.warning("Tinkoff API returned an empty instruments list")
                    return self._figi_from_db_or_empty()
                return mapping
        except Exception as exc:
            logger.exception("FIGI fetch via Tinkoff API failed: %s", exc)
            try:
                self._warn("РћС€РёР±РєР° РїСЂРё РІС‹Р·РѕРІРµ Tinkoff API. РЎРј. Р»РѕРіРё РїСЂРёР»РѕР¶РµРЅРёСЏ.")
            except Exception:  # pragma: no cover
                pass
            return self._figi_from_db_or_empty()

    # --------------------------------------------------------------- market data
    def get_stock_data(self, figi: str) -> pd.DataFrame:
        """Return OHLCV data for the given FIGI."""
        if not figi:
            logger.warning("StockAnalyzer.get_stock_data called with empty FIGI")
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])

        if TINKOFF_AVAILABLE and self.api_key:  # pragma: no cover - external SDK
            try:
                assert Client is not None and CandleInterval is not None
                with Client(self.api_key) as client:
                    to_date = datetime.now(timezone.utc)
                    from_date = to_date - timedelta(days=365)
                    response = client.market_data.get_candles(
                        figi=figi,
                        from_=from_date,
                        to=to_date,
                        interval=CandleInterval.CANDLE_INTERVAL_DAY,
                    )
                    candles = getattr(response, "candles", None) or []
                    if candles:
                        data = pd.DataFrame(
                            {
                                "time": candle.time,
                                "open": quotation_to_decimal(candle.open),
                                "close": quotation_to_decimal(candle.close),
                                "high": quotation_to_decimal(candle.high),
                                "low": quotation_to_decimal(candle.low),
                                "volume": candle.volume,
                            }
                            for candle in candles
                        )
                        data["time"] = pd.to_datetime(data["time"])
                        return data.sort_values("time")
            except Exception as exc:
                logger.exception("Failed to fetch candles via Tinkoff API: %s", exc)
                # fall back to DB

        if not self.db_conn:
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])

        try:
            query = (
                "SELECT dd.date AS time, dd.open, dd.close, dd.high, dd.low, dd.volume "
                "FROM daily_data dd "
                "JOIN companies c ON dd.company_id = c.id "
                "WHERE c.figi = ? ORDER BY dd.date ASC"
            )
            df = pd.read_sql_query(query, self.db_conn, params=(figi,))
            if df.empty:
                logger.info("No stored candles for FIGI %s", figi)
                return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])
            df["time"] = pd.to_datetime(df["time"])
            return df
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to fetch candles from DB: %s", exc)
            return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])

    # ------------------------------------------------------------ tech analysis
    @staticmethod
    def get_technical_indicators(ticker_uid: str, from_date: datetime, to_date: datetime, token: str):
        """Call REST endpoint that returns technical indicators."""
        import http.client
        import json

        conn = http.client.HTTPSConnection("sandbox-invest-public-api.tinkoff.ru")
        payload = json.dumps(
            {
                "indicatorType": "INDICATOR_TYPE_UNSPECIFIED",
                "instrumentUid": ticker_uid,
                "from": from_date.isoformat() + "Z",
                "to": to_date.isoformat() + "Z",
                "interval": "INDICATOR_INTERVAL_DAY",
                "typeOfPrice": "TYPE_OF_PRICE_CLOSE",
                "length": 14,
            }
        )
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

        try:  # pragma: no cover - network call
            conn.request(
                "POST",
                "/rest/tinkoff.public.invest.api.contract.v1.MarketDataService/GetTechAnalysis",
                payload,
                headers,
            )
            response = conn.getresponse()
            raw = response.read()
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            logger.error("GetTechAnalysis request failed: %s", exc)
            return {}
