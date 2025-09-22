"""Business logic for placing orders via the Tinkoff Invest API."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# --- optional dependency: tinkoff-invest ------------------------------------
TINKOFF_AVAILABLE = True
try:  # pragma: no cover - optional dependency
    from tinkoff.invest import Client, OrderDirection, OrderType, Quotation, RequestError  # type: ignore
except Exception as exc:  # pragma: no cover - executed when SDK missing
    TINKOFF_AVAILABLE = False
    logger.warning("tinkoff-invest SDK is not available: %s", exc)

    class RequestError(Exception):
        pass

    class OrderDirection:  # type: ignore
        ORDER_DIRECTION_BUY = "BUY"
        ORDER_DIRECTION_SELL = "SELL"
        BUY = "BUY"
        SELL = "SELL"

    class OrderType:  # type: ignore
        ORDER_TYPE_MARKET = "MARKET"
        ORDER_TYPE_LIMIT = "LIMIT"
        MARKET = "MARKET"
        LIMIT = "LIMIT"

    class Quotation:  # type: ignore
        def __init__(self, units: int = 0, nano: int = 0):
            self.units = units
            self.nano = nano

    class Client:  # type: ignore
        def __init__(self, token: Optional[str] = None):
            self.token = token

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: D401 - same semantics as context manager
            return False

        class orders:  # type: ignore
            @staticmethod
            def post_order(*args, **kwargs):
                raise RuntimeError("Tinkoff SDK отсутствует — ордер не отправлен.")


def tinkoff_enabled() -> bool:
    if os.getenv("DISABLE_TINKOFF", "0") == "1":
        return False
    return TINKOFF_AVAILABLE


def _make_quotation_from_price(price: float) -> Quotation:
    units = int(price)
    nano = int(round((price - units) * 1e9))
    if nano >= 1_000_000_000:
        units += 1
        nano = 0
    return Quotation(units=units, nano=nano)


def create_order(
    ticker: str,
    volume: int,
    order_price: float,
    order_direction: str,
    analyzer,
    account_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    if not ticker:
        return {"status": "error", "message": "Ticker не указан."}
    if volume is None or volume <= 0:
        return {"status": "error", "message": "Неверный объём (volume)."}

    order_dir = (order_direction or "").upper()
    if order_dir not in ("BUY", "SELL"):
        return {"status": "error", "message": "order_direction должен быть 'BUY' или 'SELL'."}

    if not tinkoff_enabled():
        logger.info("Tinkoff отключён или SDK отсутствует — ордер не отправлен (режим эмуляции).")
        return {
            "status": "skipped",
            "message": "Tinkoff SDK не доступен или отключён (DISABLE_TINKOFF=1). Ордер не отправлен.",
            "ticker": ticker,
            "volume": volume,
            "price": order_price,
            "direction": order_dir,
        }

    key = api_key or getattr(analyzer, "api_key", None) or os.getenv("TINKOFF_API_KEY")
    if not key:
        logger.warning("API key не найден.")
        return {"status": "error", "message": "API key не задан."}

    try:
        figi_map = analyzer.get_figi_mapping() if hasattr(analyzer, "get_figi_mapping") else {}
        try:
            from core.jobs.auto_update import normalize_ticker
        except Exception:  # pragma: no cover - defensive
            normalize_ticker = lambda value: (value or "").upper().strip()
        norm = normalize_ticker(ticker)
        figi = figi_map.get(norm) or figi_map.get(ticker)
        if not figi:
            return {"status": "error", "message": f"FIGI для тикера {ticker} не найден."}
    except Exception as exc:
        logger.exception("Ошибка при получении FIGI: %s", exc)
        return {"status": "error", "message": f"Ошибка при получении FIGI: {exc}"}

    try:  # pragma: no cover - network call
        with Client(key) as client:
            order_id = str(datetime.now(timezone.utc).timestamp())
            if order_price and order_price > 0:
                quotation = _make_quotation_from_price(float(order_price))
                try:
                    response = client.orders.post_order(
                        order_id=order_id,
                        figi=figi,
                        quantity=volume,
                        price=quotation,
                        account_id=account_id,
                        direction=(
                            OrderDirection.ORDER_DIRECTION_BUY
                            if order_dir == "BUY"
                            else OrderDirection.ORDER_DIRECTION_SELL
                        ),
                        order_type=OrderType.ORDER_TYPE_LIMIT,
                    )
                except Exception:
                    response = client.orders.post_order(
                        figi=figi,
                        quantity=volume,
                        price=quotation,
                        account_id=account_id,
                        direction=(
                            getattr(OrderDirection, "BUY", OrderDirection.ORDER_DIRECTION_BUY)
                            if order_dir == "BUY"
                            else getattr(OrderDirection, "SELL", OrderDirection.ORDER_DIRECTION_SELL)
                        ),
                        order_type=getattr(OrderType, "LIMIT", OrderType.ORDER_TYPE_LIMIT),
                    )
            else:
                response = client.orders.post_order(
                    order_id=order_id,
                    figi=figi,
                    quantity=volume,
                    direction=(
                        OrderDirection.ORDER_DIRECTION_BUY
                        if order_dir == "BUY"
                        else OrderDirection.ORDER_DIRECTION_SELL
                    ),
                    account_id=account_id,
                    order_type=OrderType.ORDER_TYPE_MARKET,
                )
    except RequestError as exc:
        logger.exception("Tinkoff API вернул ошибку: %s", exc)
        return {"status": "error", "message": f"Ошибка Tinkoff API: {exc}"}
    except Exception as exc:
        logger.exception("Unexpected error while posting order: %s", exc)
        return {"status": "error", "message": f"Неожиданная ошибка: {exc}"}

    return {
        "status": "success",
        "message": "Ордер отправлен.",
        "ticker": ticker,
        "volume": volume,
        "price": order_price,
        "direction": order_dir,
        "response": getattr(response, "__dict__", str(response)),
    }
