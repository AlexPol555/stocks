# orders.py — безопасная реализация create_order с guarded-imports и проверками
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Попытка импортировать normalize_ticker (если есть в проекте)
try:
    from auto_update import normalize_ticker
except Exception:
    # если нет — используем простую нормализацию
    def normalize_ticker(t):
        return (t or "").upper().strip()

# Guarded import tinkoff SDK
TINKOFF_AVAILABLE = True
try:
    from tinkoff.invest import Client, RequestError, OrderDirection, OrderType, Quotation
except Exception as _e:
    TINKOFF_AVAILABLE = False
    logger.warning("tinkoff SDK не доступен: %s", _e)

    # Заглушки (минимальные)
    class RequestError(Exception):
        pass

    class OrderDirection:
        ORDER_DIRECTION_BUY = "BUY"
        ORDER_DIRECTION_SELL = "SELL"

    class OrderType:
        ORDER_TYPE_MARKET = "MARKET"
        ORDER_TYPE_LIMIT = "LIMIT"

    class Quotation:
        def __init__(self, units: int = 0, nano: int = 0):
            self.units = units
            self.nano = nano

    class Client:
        def __init__(self, token: str = None):
            self.token = token
            logger.debug("Используется заглушка Client (tinkoff SDK отсутствует).")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        # заглушечный orders namespace
        @property
        def orders(self):
            class _Orders:
                def post_order(self, *args, **kwargs):
                    raise RuntimeError("Tinkoff SDK отсутствует — реальная отправка ордера недоступна.")
            return _Orders()

def tinkoff_enabled():
    # Можно полностью отключить реальные вызовы одновременной установкой переменной окружения
    if os.getenv("DISABLE_TINKOFF", "0") == "1":
        return False
    return TINKOFF_AVAILABLE

def _make_quotation_from_price(price: float) -> Quotation:
    """
    Преобразует float price -> Quotation(units, nano).
    """
    units = int(price)
    nano = int(round((price - units) * 1e9))
    # безопасно: nano не должен быть 1e9
    if nano >= 1_000_000_000:
        units += 1
        nano = 0
    return Quotation(units=units, nano=nano)

def create_order(ticker: str,
                 volume: int,
                 order_price: float,
                 order_direction: str,
                 analyzer,
                 account_id: str = None,
                 api_key: str = None) -> dict:
    """
    Универсальный wrapper для создания ордера.
    Возвращает словарь с полем 'status' и 'message' (и доп. полями для дебага).
    """
    # Проверки входных данных
    if not ticker:
        return {"status": "error", "message": "Ticker не указан."}
    if volume is None or volume <= 0:
        return {"status": "error", "message": "Неверный объём (volume)."}
    order_dir = (order_direction or "").upper()
    if order_dir not in ("BUY", "SELL"):
        return {"status": "error", "message": "order_direction должен быть 'BUY' или 'SELL'."}

    # Если явно отключено или SDK недоступен — не падаем
    if not tinkoff_enabled():
        logger.info("Tinkoff отключён или SDK отсутствует — ордер не отправлен (режим эмуляции).")
        return {
            "status": "skipped",
            "message": "Tinkoff SDK не доступен или отключён (DISABLE_TINKOFF=1). Ордер не отправлен.",
            "ticker": ticker,
            "volume": volume,
            "price": order_price,
            "direction": order_dir
        }

    # Получаем api_key: аргумент > analyzer.api_key > переменные окружения > st.secrets (в основном коде)
    key = api_key or getattr(analyzer, "api_key", None) or os.getenv("TINKOFF_API_KEY")
    if not key:
        logger.warning("API key не найден.")
        return {"status": "error", "message": "API key не задан."}

    # Получаем FIGI для тикера
    try:
        figi_map = analyzer.get_figi_mapping() if hasattr(analyzer, "get_figi_mapping") else {}
        norm = normalize_ticker(ticker)
        figi = figi_map.get(norm)
        if not figi:
            # пробуем искать по исходному тикеру (на случай плохой нормализации)
            figi = figi_map.get(ticker)
        if not figi:
            return {"status": "error", "message": f"FIGI для тикера {ticker} не найден."}
    except Exception as e:
        logger.exception("Ошибка при получении FIGI: %s", e)
        return {"status": "error", "message": f"Ошибка при получении FIGI: {e}"}

    # Собираем запрос и отправляем
    try:
        with Client(key) as client:
            order_id = str(datetime.now(timezone.utc).timestamp())

            # Построим payload, но вызов SDK может отличаться в конкретной версии — обернём в попытку
            if order_price and order_price > 0:
                quotation = _make_quotation_from_price(float(order_price))
                # Limit order
                try:
                    # Попробуем стандартный вариант post_order
                    response = client.orders.post_order(
                        order_id=order_id,
                        figi=figi,
                        quantity=volume,
                        price=quotation,
                        account_id=account_id,
                        direction=(OrderDirection.ORDER_DIRECTION_BUY if order_dir == "BUY" else OrderDirection.ORDER_DIRECTION_SELL),
                        order_type=OrderType.ORDER_TYPE_LIMIT
                    )
                except Exception as e_post:
                    # если сигнатура другая — попробуем альтернативный вызов (без order_id)
                    try:
                        response = client.orders.post_order(
                            figi=figi,
                            quantity=volume,
                            price=quotation,
                            account_id=account_id,
                            direction=(OrderDirection.BUY if order_dir == "BUY" else OrderDirection.SELL),
                            order_type=(OrderType.LIMIT if hasattr(OrderType, "LIMIT") else OrderType.ORDER_TYPE_LIMIT)
                        )
                    except Exception as e2:
                        logger.exception("Ошибка при отправке лимитной заявки: %s ; %s", e_post, e2)
                        raise
            else:
                # Market order
                try:
                    response = client.orders.post_order(
                        order_id=order_id,
                        figi=figi,
                        quantity=volume,
                        account_id=account_id,
                        direction=(OrderDirection.ORDER_DIRECTION_BUY if order_dir == "BUY" else OrderDirection.ORDER_DIRECTION_SELL),
                        order_type=OrderType.ORDER_TYPE_MARKET
                    )
                except Exception as e_post:
                    try:
                        response = client.orders.post_order(
                            figi=figi,
                            quantity=volume,
                            account_id=account_id,
                            direction=(OrderDirection.BUY if order_dir == "BUY" else OrderDirection.SELL),
                            order_type=(OrderType.MARKET if hasattr(OrderType, "MARKET") else OrderType.ORDER_TYPE_MARKET)
                        )
                    except Exception as e2:
                        logger.exception("Ошибка при отправке рыночной заявки: %s ; %s", e_post, e2)
                        raise

        # Если дошли до сюда — считаем, что отправка успешна (response может быть объектом SDK)
        return {"status": "ok", "message": "Заявка отправлена.", "api_response": repr(response)}
    except RequestError as e:
        logger.error("RequestError: %s", e)
        return {"status": "error", "message": f"RequestError: {e}"}
    except Exception as e:
        logger.exception("Неожиданная ошибка при создании заявки: %s", e)
        return {"status": "error", "message": f"Ошибка: {e}"}
