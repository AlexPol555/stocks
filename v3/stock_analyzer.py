# stock_analyzer.py
import os
import logging
import pandas as pd
from datetime import datetime, timedelta, timezone

# Попробуем импортировать Tinkoff SDK — если его нет, включим режим "без Tinkoff"
TINKOFF_AVAILABLE = True
try:
    from tinkoff.invest import Client, CandleInterval
    from tinkoff.invest.services import InstrumentsService, MarketDataService
    from tinkoff.invest.utils import quotation_to_decimal
except Exception as _e:
    TINKOFF_AVAILABLE = False
    Client = None
    CandleInterval = None
    InstrumentsService = None
    MarketDataService = None

    # Простая заглушка для quotation_to_decimal (возвращает 0.0 при отсутствии SDK)
    def quotation_to_decimal(q):
        try:
            # если q похож на объект quotation — пытаемся конвертировать
            return float(getattr(q, "units", 0)) + float(getattr(q, "nano", 0)) / 1e9
        except Exception:
            return 0.0

import streamlit as st
from indicators import calculate_technical_indicators
from data_loader import load_csv_data
import http.client
import json

# В файле stock_analyzer.py замените конструктор и метод get_figi_mapping на этот блок:

import logging
logger = logging.getLogger(__name__)
import streamlit as st

class StockAnalyzer:
    def __init__(self, api_key, db_conn=None):
        self.api_key = api_key
        self.db_conn = db_conn

    def get_figi_mapping(self) -> dict:
        """
        Возвращает mapping ticker -> figi.
        Поведение:
         - если доступен tinkoff SDK и задан api_key — используем API;
         - иначе, пытаемся прочитать figi из таблицы companies (если db_conn передан);
         - иначе возвращаем пустой словарь и логируем причину.
        """
        # 1) Проверка ключа
        if not self.api_key:
            logger.warning("Tinkoff API key not provided; get_figi_mapping вернёт mapping из БД (если есть) или {}.")
            st.warning("Tinkoff API key не задан: FIGI mapping пуст. Добавьте TINKOFF_API_KEY в Streamlit Secrets, если нужен API.")
            return self._figi_from_db_or_empty()

        # 2) Попытка динамически импортировать SDK (чтобы избежать ImportError во время импорта модуля)
        try:
            from tinkoff.invest import Client
        except Exception as e:
            logger.warning("Tinkoff SDK не найден: %s. Попробую получить FIGI из БД.", e)
            st.warning("Tinkoff SDK не установлен в окружении (ModuleNotFoundError). Проверьте requirements.txt.")
            return self._figi_from_db_or_empty()

        # 3) Если импорт успешен — вызываем API
        try:
            with Client(self.api_key) as client:
                instruments = client.instruments.shares().instruments
                mapping = {share.ticker: share.figi for share in instruments if getattr(share, 'ticker', None)}
                if not mapping:
                    logger.warning("Tinkoff API вернул пустой список инструментов.")
                    return self._figi_from_db_or_empty()
                return mapping
        except Exception as e:
            logger.exception("Ошибка при запросе FIGI через Tinkoff API: %s", e)
            st.warning("Ошибка при вызове Tinkoff API. См. логи.")
            return self._figi_from_db_or_empty()

    def _figi_from_db_or_empty(self):
        """
        Попытка получить mapping из БД (companies.figi) если доступно соединение.
        """
        if not self.db_conn:
            logger.info("DB connection не передан — возвращаю пустой mapping.")
            return {}
        try:
            import pandas as pd
            query = "SELECT contract_code, figi FROM companies WHERE figi IS NOT NULL AND figi != '';"
            df = pd.read_sql_query(query, self.db_conn)
            return dict(zip(df['contract_code'], df['figi']))
        except Exception as e:
            logger.exception("Не удалось получить FIGI из БД: %s", e)
            return {}

    @staticmethod
    def get_technical_indicators(ticker_uid, from_date, to_date, token):

        """
        Вызов REST-метода sandbox/публичного API для расчёта тех. индикаторов.
        Этот метод не использует SDK Tinkoff и может работать без него.
        """
        conn = http.client.HTTPSConnection("sandbox-invest-public-api.tinkoff.ru")
        payload = json.dumps({
            "indicatorType": "INDICATOR_TYPE_UNSPECIFIED",
            "instrumentUid": ticker_uid,
            "from": from_date.isoformat() + "Z",
            "to": to_date.isoformat() + "Z",
            "interval": "INDICATOR_INTERVAL_DAY",
            "typeOfPrice": "TYPE_OF_PRICE_CLOSE",
            "length": 14
        })
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        try:
            conn.request("POST", "/rest/tinkoff.public.invest.api.contract.v1.MarketDataService/GetTechAnalysis", payload, headers)
            res = conn.getresponse()
            data = res.read()
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            logger.error(f"Ошибка при вызове GetTechAnalysis: {e}")
            return {}
        # stock_analyzer.py — ДОБАВИТЬ ВНУТРЬ КЛАССА StockAnalyzer
    def get_stock_data(self, ticker: str, start_date=None, end_date=None, timeframe: str = "1d"):
    """
    Совместимость со старым кодом: вернуть OHLCV для тикера.
    Пытаемся делегировать в существующие методы/модули.
    Ожидается pandas.DataFrame с колонками: ['date','open','high','low','close','volume'] (или аналог).
    """
    # 1) Если внутри класса уже есть «правильный» метод — используем его
    for candidate in ("get_price_history", "load_price_history", "load_stock_data", "fetch_stock_data"):
        if hasattr(self, candidate):
            return getattr(self, candidate)(ticker, start_date, end_date, timeframe)

    # 2) Через data_loader, если он за это отвечает
    try:
        import data_loader
        for candidate in ("get_stock_data", "fetch_stock_data", "load_price_history", "load_stock_data"):
            if hasattr(data_loader, candidate):
                return getattr(data_loader, candidate)(ticker, start_date, end_date, timeframe)
    except Exception:
        pass

    # 3) Через database, если там есть удобная обёртка
    try:
        import database
        for candidate in ("get_price_history", "read_price_history", "get_ohlcv", "read_ohlcv"):
            if hasattr(database, candidate):
                return getattr(database, candidate)(ticker, start_date, end_date, timeframe)
    except Exception:
        pass

    # 4) Если ничего не нашлось — сообщаем явно
    raise NotImplementedError(
        "StockAnalyzer.get_stock_data не нашёл базовый метод получения OHLCV. "
        "Проверь названия функций в data_loader/database и добавь сюда в список кандидатов."
    )

