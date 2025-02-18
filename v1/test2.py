import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from datetime import datetime
import time

options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Безголовый режим
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

# Инициализация драйвера через Selenium Manager
driver = webdriver.Chrome(options=options)

# Функция для получения кодов с сайта Московской биржи
def get_contract_codes(url):
    try:
        # Загружаем страницу
        driver.get(url)
        time.sleep(3)  # Даем время на загрузку страницы

        # Получаем HTML-код страницы
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # Ищем таблицу с классом table1 listMainFortsIssue
        table = soup.findAll("table", class_="table1 listMainFortsIssue")[1]
        # Считываем строки таблицы
        rows = table.find_all("tr")[1:]  # Пропускаем заголовок таблицы

        # Извлекаем коды и другие данные
        data = []
        for row in rows:
            cols = row.find_all("td")
            cols = [col.get_text(strip=True) for col in cols]
            if cols:
                data.append(cols)
        return data
    
    finally:
        driver.quit()  # Закрываем браузер

# Основной код
if __name__ == "__main__":
    # URL страницы с данными
    url = "https://www.moex.com/ru/derivatives/"

    # Получаем коды контрактов
    extracted_data = get_contract_codes(url)
    

    test12 = []
    for i in extracted_data:
        test12.append(i[0])

    # Печатаем результат
    print(test12)