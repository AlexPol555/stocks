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
   
    def get_stock_data(self, figi: str) -> pd.DataFrame:
        """
        Возвращает DataFrame с историческими свечами для FIGI.
        Логика:
          1) Если Tinkoff SDK доступен и есть api_key — запрашиваем candles через SDK.
          2) Если SDK недоступен или нет api_key — пытаемся прочитать свечи из local DB (companies.figi -> daily_data).
        Возвращаемые колонки: ['time', 'open', 'close', 'high', 'low', 'volume']
        """
        if not figi:
            logger.warning("get_stock_data: figi пустой, возвращаю пустой DataFrame.")
            return pd.DataFrame(columns=['time', 'open', 'close', 'high', 'low', 'volume'])

        # 1) Попытка через SDK (если доступен)
        try:
            if TINKOFF_AVAILABLE and self.api_key:
                with Client(self.api_key) as client:
                    market_data = client.market_data
                    to_date = datetime.now(timezone.utc)
                    from_date = to_date - timedelta(days=365)
                    res = market_data.get_candles(
                        figi=figi,
                        from_=from_date,
                        to=to_date,
                        interval=CandleInterval.CANDLE_INTERVAL_DAY
                    )
                    candles = getattr(res, "candles", None) or []
                    if not candles:
                        logger.info("Tinkoff API вернул пустой список свечей для FIGI %s", figi)
                        # fallthrough to DB fallback below
                    else:
                        data = pd.DataFrame([{
                            "time": candle.time,
                            "open": quotation_to_decimal(candle.open),
                            "close": quotation_to_decimal(candle.close),
                            "high": quotation_to_decimal(candle.high),
                            "low": quotation_to_decimal(candle.low),
                            "volume": candle.volume
                        } for candle in candles])
                        data['time'] = pd.to_datetime(data['time'])
                        data.sort_values(by='time', inplace=True)
                        return data[['time', 'open', 'close', 'high', 'low', 'volume']]
        except Exception as e:
            logger.exception("Ошибка при получении свечей через Tinkoff API: %s", e)
            # продолжим к попытке чтения из БД

        # 2) Fallback: чтение из локальной БД по figi -> daily_data
        if getattr(self, "db_conn", None):
            try:
                query = """
                SELECT dd.date as time, dd.open, dd.close, dd.high, dd.low, dd.volume
                FROM daily_data dd
                JOIN companies c ON dd.company_id = c.id
                WHERE c.figi = ?
                ORDER BY dd.date ASC
                """
                df = pd.read_sql_query(query, self.db_conn, params=(figi,))
                if df.empty:
                    logger.info("Fallback: нет данных в daily_data для FIGI %s", figi)
                    return pd.DataFrame(columns=['time', 'open', 'close', 'high', 'low', 'volume'])
                df['time'] = pd.to_datetime(df['time'])
                return df[['time', 'open', 'close', 'high', 'low', 'volume']]
            except Exception as ex:
                logger.exception("Ошибка чтения свечей из БД: %s", ex)

        # Ничего не найдено — пустой DataFrame
        return pd.DataFrame(columns=['time', 'open', 'close', 'high', 'low', 'volume'])


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