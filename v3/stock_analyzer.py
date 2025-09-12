# stock_analyzer.py
import os
import logging
import pandas as pd
from datetime import datetime, timedelta, timezone
# from tinkoff.invest import Client, CandleInterval
from tinkoff.invest.services import InstrumentsService, MarketDataService
from tinkoff.invest.utils import quotation_to_decimal
import streamlit as st
from indicators import calculate_technical_indicators
from data_loader import load_csv_data
import http.client
import json

logger = logging.getLogger(__name__)


class StockAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_figi_mapping(self) -> dict:
        """
        Получает отображение тикера в FIGI для акций.
        """
        try:
            with Client(self.api_key) as client:
                instruments: InstrumentsService = client.instruments
                shares = instruments.shares().instruments
                return {share.ticker: share.figi for share in shares}
        except Exception as e:
            logger.error(f"Ошибка при получении FIGI: {e}")
            return {}

    def get_stock_data(self, figi: str) -> pd.DataFrame:
        """
        Получает исторические данные по акции и рассчитывает технические индикаторы.
        """
        try:
            with Client(self.api_key) as client:
                market_data: MarketDataService = client.market_data
                to_date = datetime.now(timezone.utc)
                from_date = to_date - timedelta(days=365)
                candles = market_data.get_candles(
                    figi=figi,
                    from_=from_date,
                    to=to_date,
                    interval=CandleInterval.CANDLE_INTERVAL_DAY
                ).candles

                if not candles:
                    logger.warning(f"Нет данных для FIGI {figi}")
                    return pd.DataFrame()

                data = pd.DataFrame([{
                    "time": candle.time,
                    "open": quotation_to_decimal(candle.open),
                    "close": quotation_to_decimal(candle.close),
                    "high": quotation_to_decimal(candle.high),
                    "low": quotation_to_decimal(candle.low),
                    "volume": candle.volume
                } for candle in candles])
                return data


        except Exception as e:
            logger.error(f"Ошибка получения данных для FIGI {figi}: {e}")
            return pd.DataFrame()

    def get_technical_indicators(ticker_uid, from_date, to_date, token):
        """
        Получает технические индикаторы с Tinkoff API.
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
        conn.request("POST", "/rest/tinkoff.public.invest.api.contract.v1.MarketDataService/GetTechAnalysis", payload,
                     headers)
        res = conn.getresponse()
        data = res.read()

        # print("Ответ API Tinkoff (GetTechAnalysis):", data)

        return json.loads(data.decode("utf-8"))