# visualization.py — безопасный вариант с guarded imports и safe_plot
import logging
logger = logging.getLogger(__name__)

import pandas as pd
import streamlit as st

# Guarded imports: matplotlib / plotly / mplfinance
MATPLOTLIB_AVAILABLE = True
PLOTLY_AVAILABLE = True
MPLFINANCE_AVAILABLE = True

try:
    import matplotlib.pyplot as plt
except Exception as _e:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib не доступен: %s", _e)

try:
    import plotly.express as px
except Exception as _e:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly не доступен: %s", _e)

try:
    import mplfinance as mpf
except Exception as _e:
    MPLFINANCE_AVAILABLE = False
    logger.warning("mplfinance не доступен: %s", _e)


def safe_plot_matplotlib(fig):
    """
    Безопасно показать matplotlib-fig: если matplotlib доступен — st.pyplot,
    иначе — вывести информационное сообщение.
    """
    if MATPLOTLIB_AVAILABLE and fig is not None:
        try:
            st.pyplot(fig)
        except Exception as e:
            logger.warning("Ошибка при отображении matplotlib-fig: %s", e)
            st.info("График доступен, но произошла ошибка при его отображении.")
    else:
        st.info("matplotlib не установлен — график недоступен в этом режиме.")


def safe_plot_interactive(fig):
    """
    Безопасно отобразить plotly-figure.
    """
    if PLOTLY_AVAILABLE and fig is not None:
        try:
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            logger.warning("Ошибка при отображении plotly-fig: %s", e)
            st.info("Интерактивный график создан, но не может быть показан.")
    else:
        st.info("Plotly не установлен — интерактивный график недоступен.")


def plot_daily_analysis(data, date_value):
    # Используем столбцы 'date' и 'metric_type'
    data_filtered = data[(data['date'] == date_value) & (data['metric_type'] == 'Открытые позиции')]
    
    # Если данных нет, возвращаем пустой график с сообщением
    if data_filtered.empty:
        if MATPLOTLIB_AVAILABLE:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, "Нет данных для выбранной даты", ha='center', va='center', fontsize=14)
            ax.axis('off')
            return fig
        else:
            st.info("Нет данных для выбранной даты")
            return None

    # Создание графика
    if MATPLOTLIB_AVAILABLE:
        fig, ax = plt.subplots(figsize=(12, 8))
        bars = ax.barh(data_filtered['contract_code'], data_filtered['value1'], color='skyblue')
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height() / 2, f'{width:.2f}', 
                    va='center', ha='left', fontsize=10)
        ax.set_title(f"Открытые позиции на дату {date_value}", fontsize=16, pad=20)
        ax.set_xlabel("Value1", fontsize=14)
        ax.set_ylabel("Contract Code", fontsize=14)
        ax.tick_params(axis='both', labelsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        return fig
    else:
        # fallback: показать таблицу с данными
        st.write(f"Открытые позиции на дату {date_value}")
        st.dataframe(data_filtered[['contract_code', 'value1']])
        return None


def plot_stock_analysis(data, stock_code):
    stock_data = data[(data['contract_code'] == stock_code) & (data['metric_type'] == 'Открытые позиции')].sort_values(by='date')
    
    if stock_data.empty:
        if MATPLOTLIB_AVAILABLE:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "Нет данных для выбранного тикера", ha='center', va='center')
            return fig
        else:
            st.info("Нет данных для выбранного тикера")
            return None

    if MATPLOTLIB_AVAILABLE:
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 18))
        ax1.plot(stock_data['date'], stock_data['value1'], label='Value1', marker='o', color='black')
        ax1.plot(stock_data['date'], stock_data['value4'], label='Value4', marker='o', color='blue')
        ax1.set_title(f"Анализ позиций для {stock_code}")
        ax1.set_xlabel("Дата"); ax1.set_ylabel("Значение"); ax1.legend(); ax1.grid(True)

        ax2.plot(stock_data['date'], stock_data['value2'], label='Value2', marker='o', color='red')
        ax2.plot(stock_data['date'], stock_data['value3'], label='Value3', marker='o', color='green')
        ax2.set_title(f"Дополнительный анализ для {stock_code}")
        ax2.set_xlabel("Дата"); ax2.set_ylabel("Значение"); ax2.legend(); ax2.grid(True)

        ax3.plot(stock_data['date'], stock_data['value5'], label='Value5', marker='o', color='purple')
        ax3.set_title(f"Дополнительный анализ (Value5) для {stock_code}")
        ax3.set_xlabel("Дата"); ax3.set_ylabel("Значение"); ax3.legend(); ax3.grid(True)

        plt.tight_layout()
        return fig
    else:
        # fallback: несколько таблиц / простых line_chart
        st.write(f"Анализ позиций для {stock_code} — упрощённый режим (без matplotlib)")
        try:
            st.line_chart(stock_data.set_index('date')[['value1','value4']])
            st.line_chart(stock_data.set_index('date')[['value2','value3']])
            st.line_chart(stock_data.set_index('date')[['value5']])
        except Exception:
            st.dataframe(stock_data[['date','value1','value2','value3','value4','value5']])
        return None


def plot_interactive_chart(data, stock_code):
    stock_data = data[data['contract_code'] == stock_code]
    if stock_data.empty:
        if PLOTLY_AVAILABLE:
            return px.scatter(title=f"Нет данных для {stock_code}")
        else:
            st.info(f"Нет данных для {stock_code}")
            return None

    if PLOTLY_AVAILABLE:
        fig = px.line(
            stock_data,
            x='date',
            y='value1',
            title=f"Интерактивный график для {stock_code}",
            labels={'date': 'Дата', 'value1': 'Value1'}
        )
        return fig
    else:
        # fallback: static line charts via streamlit
        try:
            st.line_chart(stock_data.set_index('date')['value1'])
        except Exception:
            st.dataframe(stock_data[['date','value1']])
        return None


def plot_grafik_candle_days(df, selected_ticker):
    df_filtered = df[df['contract_code'] == selected_ticker].copy()

    if df_filtered.empty:
        st.info(f"Нет данных для {selected_ticker}")
        return None

    df_filtered['date'] = pd.to_datetime(df_filtered['date'])
    df_filtered.set_index('date', inplace=True)
    df_filtered.sort_index(inplace=True)

    # Используем mplfinance, если доступен
    if MPLFINANCE_AVAILABLE:
        try:
            fig, axlist = mpf.plot(
                df_filtered,
                type='candle',
                volume=True,
                returnfig=True,
                title=f"Candlestick Chart for {selected_ticker} за последний месяц",
                style='default'
            )
            # отрисовываем matplotlib-fig через safe_plot
            safe_plot_matplotlib(fig)
            return fig
        except Exception as e:
            logger.warning("Ошибка mplfinance: %s", e)
            st.info("Ошибка построения свечей (mplfinance).")
            return None
    else:
        # fallback: показать OHLC как линии (упрощённо)
        try:
            st.line_chart(df_filtered[['open','high','low','close']])
        except Exception:
            st.dataframe(df_filtered[['open','high','low','close']])
        return None
