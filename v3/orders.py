from datetime import datetime, timezone
from tinkoff.invest import Client, RequestError, OrderDirection, OrderType, Quotation

def create_order(ticker: str, volume: int, order_price: float, order_direction: str,
                 analyzer, account_id: str) -> str:
    """
    Создаёт заявку для указанного тикера.
    Если order_price > 0, отправляется лимитная заявка, иначе – рыночная.
    order_direction: "BUY" или "SELL".
    """
    api_key = analyzer.api_key  # Используем API-ключ из экземпляра analyzer
    figi_mapping = analyzer.get_figi_mapping()
    norm_ticker = normalize_ticker(ticker)
    if norm_ticker not in figi_mapping:
        return f"FIGI для тикера {ticker} не найден."
    FIGI = analyzer.get_figi_mapping()
    
    try:
        with Client(api_key) as client:
            # Используем осведомлённое время (UTC) для генерации уникального order_id
            order_id = str(datetime.now(timezone.utc).timestamp())
            
            if order_price > 0:
                # Лимитная заявка
                price_units = int(order_price)
                price_nano = int((order_price - price_units) * 1e9)
                quotation = Quotation(units=price_units, nano=price_nano)
                if order_direction.upper() == "BUY":
                    response = client.orders.post_order(
                        order_id=order_id,
                        figi=FIGI,
                        quantity=volume,
                        price=quotation,
                        account_id=account_id,
                        direction=OrderDirection.ORDER_DIRECTION_BUY,
                        order_type=OrderType.ORDER_TYPE_LIMIT
                    )
                else:
                    response = client.orders.post_order(
                        order_id=order_id,
                        figi=FIGI,
                        quantity=volume,
                        price=quotation,
                        account_id=account_id,
                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                        order_type=OrderType.ORDER_TYPE_LIMIT
                    )
            else:
                # Рыночная заявка (без указания цены)
                if order_direction.upper() == "BUY":
                    response = client.orders.post_order(
                        order_id=order_id,
                        figi=FIGI,
                        quantity=volume,
                        account_id=account_id,
                        direction=OrderDirection.ORDER_DIRECTION_BUY,
                        order_type=OrderType.ORDER_TYPE_MARKET
                    )
                else:
                    response = client.orders.post_order(
                        order_id=order_id,
                        figi=FIGI,
                        quantity=volume,
                        account_id=account_id,
                        direction=OrderDirection.ORDER_DIRECTION_SELL,
                        order_type=OrderType.ORDER_TYPE_MARKET
                    )
        return f"Заявка успешно отправлена. Ответ API: {response}"
    except RequestError as e:
        return f"Ошибка при создании заявки: {str(e)}"
    except Exception as e:
        return f"Произошла ошибка: {str(e)}"
