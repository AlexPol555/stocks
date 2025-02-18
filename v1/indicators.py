# indicators.py
from dataclasses import dataclass, asdict
import pandas as pd
import streamlit as st


@dataclass
class TechnicalIndicators:
    sma: pd.Series
    ema: pd.Series
    rsi: pd.Series
    macd: pd.Series
    macd_signal: pd.Series
    bb_upper: pd.Series
    bb_middle: pd.Series
    bb_lower: pd.Series

def calculate_technical_indicators(prices: pd.Series) -> dict:
    # Ваш код для расчёта технических индикаторов:
    # Например, расчёт SMA, EMA, RSI, MACD и т.д.
    sma = prices.rolling(window=14).mean()
    ema = prices.ewm(span=14, adjust=False).mean()
    # Пример расчёта RSI (упрощённый):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(window=14).mean() / loss.rolling(window=14).mean()
    rsi = 100 - (100 / (1 + rs))
    # Для примера зададим MACD и Bollinger Bands как копии SMA (реальная логика должна быть другой)
    macd = sma  # Просто пример
    macd_signal = ema  # Пример
    bb_middle = sma
    bb_upper = sma + 2 * prices.rolling(window=14).std()
    bb_lower = sma - 2 * prices.rolling(window=14).std()

    indicators = TechnicalIndicators(
        sma=sma,
        ema=ema,
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        bb_upper=bb_upper,
        bb_middle=bb_middle,
        bb_lower=bb_lower
    )
    # Преобразуем объект TechnicalIndicators в словарь,
    # что сделает его сериализуемым для st.cache_data.
    return asdict(indicators)

def parse_technical_indicators(api_response):
    """
    Парсит ответ от API Tinkoff и возвращает данные в формате словаря.
    """
    try:
        data = api_response.get("indicators", [])
        if not data:
            return None

        indicators = {
            "sma": data.get("sma", None),
            "ema": data.get("ema", None),
            "rsi": data.get("rsi", None),
            "macd": data.get("macd", None),
            "macd_signal": data.get("macd_signal", None),
            "bb_upper": data.get("bb_upper", None),
            "bb_middle": data.get("bb_middle", None),
            "bb_lower": data.get("bb_lower", None),
        }
        return indicators
    except Exception as e:
        print(f"Ошибка парсинга индикаторов: {e}")
        return None
