# visualization.py
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import mplfinance as mpf
import streamlit as st


def plot_daily_analysis(data, date_value) -> plt.Figure:
    # Используем столбцы 'date' и 'metric_type'
    data_filtered = data[(data['date'] == date_value) & (data['metric_type'] == 'Открытые позиции')]
    
    # Если данных нет, возвращаем пустой график с сообщением
    if data_filtered.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "Нет данных для выбранной даты", ha='center', va='center', fontsize=14)
        ax.axis('off')  # Скрываем оси
        return fig

    # Создание графика
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Построение горизонтальной столбчатой диаграммы
    bars = ax.barh(data_filtered['contract_code'], data_filtered['value1'], color='skyblue')
    
    # Добавление подписей к столбцам
    for bar in bars:
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height() / 2, f'{width:.2f}', 
                va='center', ha='left', fontsize=10)
    
    # Настройка заголовка и подписей осей
    ax.set_title(f"Открытые позиции на дату {date_value}", fontsize=16, pad=20)
    ax.set_xlabel("Value1", fontsize=14)
    ax.set_ylabel("Contract Code", fontsize=14)
    
    # Увеличение размера шрифта меток на осях
    ax.tick_params(axis='both', labelsize=12)
    
    # Добавление сетки для улучшения читаемости
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Автоматическое выравнивание меток на оси Y
    plt.tight_layout()
    
    return fig

def plot_stock_analysis(data, stock_code) -> plt.Figure:
    # Используем правильные имена столбцов: 'contract_code', 'metric_type' и 'date'
    stock_data = data[(data['contract_code'] == stock_code) & (data['metric_type'] == 'Открытые позиции')].sort_values(by='date')
    
    # Если данных нет, создаём пустой график с сообщением
    if stock_data.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Нет данных для выбранного тикера", ha='center', va='center')
        return fig

    # Создаём 3 графика (пример)
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 18))
    
    # График 1: Пример построения линий (используем value1 и value4, например)
    ax1.plot(stock_data['date'], stock_data['value1'], label='Value1', marker='o', color='black')
    ax1.plot(stock_data['date'], stock_data['value4'], label='Value4', marker='o', color='blue')
    ax1.set_title(f"Анализ позиций для {stock_code}")
    ax1.set_xlabel("Дата")
    ax1.set_ylabel("Значение")
    ax1.legend()
    ax1.grid(True)
    
    # График 2: Пример для value2 и value3
    ax2.plot(stock_data['date'], stock_data['value2'], label='Value2', marker='o', color='red')
    ax2.plot(stock_data['date'], stock_data['value3'], label='Value3', marker='o', color='green')
    ax2.set_title(f"Дополнительный анализ для {stock_code}")
    ax2.set_xlabel("Дата")
    ax2.set_ylabel("Значение")
    ax2.legend()
    ax2.grid(True)
    
    # График 3: Используем value5
    ax3.plot(stock_data['date'], stock_data['value5'], label='Value5', marker='o', color='purple')
    ax3.set_title(f"Дополнительный анализ (Value5) для {stock_code}")
    ax3.set_xlabel("Дата")
    ax3.set_ylabel("Значение")
    ax3.legend()
    ax3.grid(True)
    
    plt.tight_layout()
    return fig

def plot_interactive_chart(data, stock_code):
    # Используем корректное имя столбца: 'contract_code' вместо 'Contract Code'
    stock_data = data[data['contract_code'] == stock_code]
    if stock_data.empty:
        return px.scatter(title=f"Нет данных для {stock_code}")
    
    fig = px.line(
        stock_data,
        x='date',  # убедитесь, что столбец с датой называется 'date'
        y='value1',  # например, используем столбец 'value1'
        title=f"Интерактивный график для {stock_code}",
        labels={'date': 'Дата', 'value1': 'Value1'}
    )
    return fig

def plot_grafik_candle_days(df, selected_ticker):
    df_filtered = df[df['contract_code'] == selected_ticker].copy()

    df_filtered['date'] = pd.to_datetime(df_filtered['date'])
    df_filtered.set_index('date', inplace=True)
    df_filtered.sort_index(inplace=True)

    # Определяем дату начала для последнего месяца
    last_month_date = pd.Timestamp.today() - pd.DateOffset(months=1)

    # Фильтруем данные за последний месяц
    df_last_month = df_filtered[df_filtered.index >= last_month_date]

    # Построение графика с помощью mplfinance
    fig, axlist = mpf.plot(
        df_filtered,
        type='candle',
        volume=True,
        returnfig=True,
        title=f"Candlestick Chart for {selected_ticker} за последний месяц",
        style='default'
    )

    st.pyplot(fig)