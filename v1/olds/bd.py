import pandas as pd
import os
from datetime import datetime, timedelta
import streamlit as st
import matplotlib.pyplot as plt
from tinkoff.invest import Client, CandleInterval
from tinkoff.invest.services import InstrumentsService, MarketDataService
from tinkoff.invest.utils import quotation_to_decimal
from dataclasses import dataclass
from typing import Dict, Optional
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


class StockAnalyzer:
    def __init__(self, api_key: str, data_folder: str):
        self.api_key = api_key
        self.data_folder = data_folder

    def get_figi_mapping(self) -> Dict[str, str]:
        """Получить отображение FIGI для всех акций."""
        try:
            with Client(self.api_key) as client:
                instruments: InstrumentsService = client.instruments
                shares = instruments.shares().instruments
                return {share.ticker: share.figi for share in shares}
        except Exception as e:
            logger.error(f"Ошибка при получении FIGI mapping: {e}")
            return {}

    def get_stock_data(self, figi: str) -> Optional[pd.DataFrame]:
        """Получить исторические данные по акции и рассчитать технические индикаторы."""
        try:
            with Client(self.api_key) as client:
                market_data: MarketDataService = client.market_data
                to_date = datetime.utcnow()
                from_date = to_date - timedelta(days=365)

                candles = market_data.get_candles(
                    figi=figi,
                    from_=from_date,
                    to=to_date,
                    interval=CandleInterval.CANDLE_INTERVAL_DAY
                ).candles

                if not candles:
                    logger.warning(f"Нет данных для FIGI {figi}")
                    return None

                data = pd.DataFrame([{
                    "time": candle.time,
                    "open": quotation_to_decimal(candle.open),
                    "close": quotation_to_decimal(candle.close),
                    "high": quotation_to_decimal(candle.high),
                    "low": quotation_to_decimal(candle.low),
                    "volume": candle.volume
                } for candle in candles])

                # Расчет технических индикаторов
                indicators = self.calculate_technical_indicators(data['close'])

                # Добавление индикаторов в DataFrame
                data = data.assign(
                    SMA=indicators.sma,
                    EMA=indicators.ema,
                    RSI=indicators.rsi,
                    MACD=indicators.macd,
                    MACD_signal=indicators.macd_signal,
                    BB_upper=indicators.bb_upper,
                    BB_middle=indicators.bb_middle,
                    BB_lower=indicators.bb_lower
                )

                return data

        except Exception as e:
            logger.error(f"Ошибка получения данных для FIGI {figi}: {e}")
            return None

    def calculate_technical_indicators(self, prices: pd.Series) -> TechnicalIndicators:
        """Рассчитать технические индикаторы для заданного ряда цен."""
        # Расчет RSI
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # Расчет MACD
        short_ema = prices.ewm(span=12, adjust=False).mean()
        long_ema = prices.ewm(span=26, adjust=False).mean()
        macd = short_ema - long_ema
        macd_signal = macd.ewm(span=9, adjust=False).mean()

        # Расчет Bollinger Bands
        sma = prices.rolling(window=20).mean()
        std = prices.rolling(window=20).std()

        return TechnicalIndicators(
            sma=prices.rolling(window=14).mean(),
            ema=prices.ewm(span=14, adjust=False).mean(),
            rsi=rsi,
            macd=macd,
            macd_signal=macd_signal,
            bb_upper=sma + (std * 2),
            bb_middle=sma,
            bb_lower=sma - (std * 2)
        )

    @staticmethod
    @st.cache_data
    def load_data(folder_path: str) -> pd.DataFrame:
        """Загрузить и предобработать CSV файлы из указанной папки."""
        try:
            files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
            if not files:
                logger.warning("CSV файлы не найдены в указанной папке")
                return pd.DataFrame()
            all_data = pd.concat(
                [pd.read_csv(os.path.join(folder_path, f)) for f in files],
                ignore_index=True
            )
            all_data['Contract Code'] = all_data['Contract Code'].str.split('-').str[0]
            all_data['Date'] = pd.to_datetime(all_data['Date'])
            return all_data
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return pd.DataFrame()

    def update_data_with_technicals(self) -> Optional[pd.DataFrame]:
        """Обновить CSV данные, добавив технические индикаторы."""
        try:
            # Загрузка исходных данных
            data = self.load_data(self.data_folder)
            if data.empty:
                logger.error("Не удалось загрузить исходные данные")
                return None

            # Получение FIGI отображения
            figi_dict = self.get_figi_mapping()
            if not figi_dict:
                logger.error("Не удалось получить FIGI коды")
                return None

            # Сбор технических данных для каждой акции
            tech_data = []
            for ticker in data['Contract Code'].unique():
                if ticker in figi_dict:
                    logger.info(f"Обработка {ticker}")
                    stock_data = self.get_stock_data(figi_dict[ticker])
                    if stock_data is not None:
                        # Переименование столбцов для избежания конфликтов
                        columns_to_rename = {
                            'time': 'tech_time',
                            'open': 'tech_open',
                            'close': 'tech_close',
                            'high': 'tech_high',
                            'low': 'tech_low',
                            'volume': 'tech_volume',
                            'SMA': 'tech_SMA',
                            'EMA': 'tech_EMA',
                            'RSI': 'tech_RSI',
                            'MACD': 'tech_MACD',
                            'MACD_signal': 'tech_MACD_signal',
                            'BB_upper': 'tech_BB_upper',
                            'BB_middle': 'tech_BB_middle',
                            'BB_lower': 'tech_BB_lower'
                        }
                        stock_data = stock_data.rename(columns=columns_to_rename)
                        stock_data['Contract Code'] = ticker
                        # Приведение времени к типу date
                        stock_data['Date'] = pd.to_datetime(stock_data['tech_time']).dt.date
                        tech_data.append(stock_data)
                else:
                    logger.warning(f"FIGI не найден для {ticker}")

            if tech_data:
                combined_tech_data = pd.concat(tech_data, ignore_index=True)
                data['Date'] = pd.to_datetime(data['Date']).dt.date

                merged_data = pd.merge(
                    data,
                    combined_tech_data,
                    on=['Contract Code', 'Date'],
                    how='left'
                )

                output_path = os.path.join(self.data_folder, 'all/updated_data.csv')
                merged_data.to_csv(output_path, index=False)
                logger.info(f"Данные успешно обновлены и сохранены в {output_path}")
                return merged_data
            else:
                logger.error("Не удалось получить технические данные")
                return None

        except Exception as e:
            logger.error(f"Ошибка при обновлении технических данных: {e}")
            return None


class StockVisualizer:
    @staticmethod
    def plot_daily_analysis(data: pd.DataFrame, date: datetime) -> plt.Figure:
        """Построить графики анализа по выбранной дате."""
        # Если столбец 'Date' уже имеет тип date, преобразование не требуется
        if pd.api.types.is_datetime64_any_dtype(data['Date']):
            date_filter = data['Date'].dt.date == date if isinstance(date, datetime) else data['Date'] == date
        else:
            date_filter = data['Date'] == date

        data_filtered = data[(date_filter) & (data['Metric'] == 'Открытые позиции')]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 20))

        # График 1: Retail Long vs Institutional Short
        ax1.barh(data_filtered['Contract Code'], data_filtered['Value1'],
                 label='Retail Long', color='black', alpha=0.7, height=0.4)
        ax1.barh(data_filtered['Contract Code'], -data_filtered['Value4'],
                 label='Institutional Short', color='red', alpha=0.7, height=0.4)
        ax1.set_title(f"Retail Long vs Institutional Short on {date}")
        ax1.set_xlabel("Количество")
        ax1.set_ylabel("Тикер акции")
        ax1.grid(True)
        ax1.legend()

        # График 2: Retail Short vs Institutional Long
        ax2.barh(data_filtered['Contract Code'], data_filtered['Value2'],
                 label='Retail Short', color='black', alpha=0.7, height=0.4)
        ax2.barh(data_filtered['Contract Code'], -data_filtered['Value3'],
                 label='Institutional Long', color='green', alpha=0.7, height=0.4)
        ax2.set_title(f"Retail Short vs Institutional Long on {date}")
        ax2.set_xlabel("Количество")
        ax2.set_ylabel("Тикер акции")
        ax2.grid(True)
        ax2.legend()

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_stock_analysis(data: pd.DataFrame, stock_code: str) -> plt.Figure:
        """Построить детальные графики анализа для выбранной акции."""
        stock_data = data[(data['Contract Code'] == stock_code) & (data['Metric'] == 'Открытые позиции')].sort_values(by='Date')

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 18))

        # График 1: Лонги физлиц vs Шорты юрлиц
        ax1.plot(stock_data['Date'], stock_data['Value1'],
                 label='Лонги физлиц', marker='o', color='black', alpha=0.8, linewidth=2)
        ax1.plot(stock_data['Date'], stock_data['Value4'],
                 label='Шорты юрлиц', marker='o', color='blue', alpha=0.8, linewidth=2)
        ax1.set_title(f"Анализ позиций - {stock_code}")
        ax1.grid(True)
        ax1.legend()

        # График 2: Шорты физлиц vs Лонги юрлиц
        ax2.plot(stock_data['Date'], stock_data['Value2'],
                 label='Шорты физлиц', marker='o', color='black', alpha=0.8, linewidth=2)
        ax2.plot(stock_data['Date'], stock_data['Value3'],
                 label='Лонги юрлиц', marker='o', color='blue', alpha=0.8, linewidth=2)
        ax2.set_title(f"Анализ позиций - {stock_code}")
        ax2.grid(True)
        ax2.legend()

        # График 3: Технический анализ
        ax3.plot(stock_data['Date'], stock_data['tech_close'],
                 label='Цена закрытия', color='black', alpha=0.8, linewidth=2)
        ax3.plot(stock_data['Date'], stock_data['tech_SMA'],
                 label='SMA (14)', color='orange', alpha=0.8, linewidth=2)
        ax3.plot(stock_data['Date'], stock_data['tech_BB_upper'],
                 label='BB верхняя', color='red', alpha=0.8, linewidth=2)
        ax3.plot(stock_data['Date'], stock_data['tech_BB_lower'],
                 label='BB нижняя', color='green', alpha=0.8, linewidth=2)
        ax3.set_title(f"Технический анализ - {stock_code}")
        ax3.grid(True)
        ax3.legend()

        plt.tight_layout()
        return fig


def main():
    st.title("Анализ и отбор акций для покупки/продажи")

    analyzer = StockAnalyzer(
        api_key=st.secrets["TINKOFF_API_KEY"],
        data_folder='C:/projek/FilesBd'
    )
    visualizer = StockVisualizer()

    if st.button("Обновить технические данные"):
        with st.spinner("Обновление данных..."):
            result = analyzer.update_data_with_technicals()
            if result is not None:
                st.success("Данные успешно обновлены!")
            else:
                st.error("Произошла ошибка при обновлении данных")

    # Если существует обновлённый файл, загружаем его, иначе загружаем исходные CSV файлы
    updated_path = os.path.join(analyzer.data_folder, 'all/updated_data.csv')
    if os.path.exists(updated_path):
        data = pd.read_csv(updated_path, parse_dates=['Date'])
        # Приводим столбец Date к типу date
        data['Date'] = pd.to_datetime(data['Date']).dt.date
    else:
        data = StockAnalyzer.load_data(analyzer.data_folder)

    if data.empty:
        st.error("Нет данных для анализа.")
        return

    unique_dates = data['Date'].unique()
    selected_date = st.selectbox("Выберите дату", unique_dates)

    if st.button("Построить график"):
        fig = visualizer.plot_daily_analysis(data, selected_date)
        st.pyplot(fig)

    stock_codes = data['Contract Code'].unique()
    selected_stock = st.selectbox("Выберите акцию", stock_codes)

    if st.button("Построить график для акции"):
        fig = visualizer.plot_stock_analysis(data, selected_stock)
        st.pyplot(fig)


if __name__ == "__main__":
    main()
