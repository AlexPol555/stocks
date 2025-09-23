from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time
import datetime
import re


def _contract_codes():
    # Массив с кодами контрактов
    return {
 'IMOEXF': 'IMOEXF',
 'SBRF-6.25': 'SBER',
 'GAZR-6.25': 'GAZP',
 'SMLT-6.25': 'SMLT',
 'GMKN-6.25': 'GMKN',
 'YDEX-6.25': 'YDEX',
 'MGNT-6.25': 'MGNT',
 'ISKJ-6.25': 'ABIO',
 'VTBR-6.25': 'VTBR',
 'SGZH-6.25': 'SGZH',
 'TRNF-6.25': 'TRNFP',
 'WUSH-6.25': 'WUSH',
 'VKCO-6.25': 'VKCO',
 'SIBN-6.25': 'SIBN',
 'RNFT-6.25': 'RNFT',
 'MVID-6.25': 'MVID',
 'PIKK-6.25': 'PIKK',
 'BELUGA-6.25': 'BELU',
 'MTLR-6.25': 'MTLR',
 'POSI-6.25': 'POSI',
 'ASTR-6.25': 'ASTR',
 'SOFL-6.25': 'SOFL',
 'ALRS-6.25': 'ALRS',
 'NLMK-6.25': 'NLMK',
 'AFLT-6.25': 'AFLT',
 'BANE-6.25': 'BANE',
 'RUAL-6.25': 'RUAL',
 'LEAS-6.25': 'LEAS',
 'AFKS-6.25': 'AFKS',
 'RTKM-6.25': 'RTKM',
 'SFIN-6.25': 'SFIN',
 'MOEX-6.25': 'MOEX',
 'SBPR-6.25': 'SBERP',
 'ROSN-6.25': 'ROSN',
 'TCSI-6.25': 'T',
 'FESH-6.25': 'FESH',
 'PHOR-6.25': 'PHOR',
 'SVCB-6.25': 'SVCB',
 'CBOM-6.25': 'CBOM',
 'LKOH-6.25': 'LKOH',
 'KMAZ-6.25': 'KMAZ',
 'SNGR-6.25': 'SNGS',
 'HYDR-6.25': 'HYDR',
 'NOTK-6.25': 'NVTK',
 'FEES-6.25': 'FEES',
 'MAGN-6.25': 'MAGN',
 'BSPB-6.25': 'BSPB',
 'TATN-6.25': 'TATN',
 'FLOT-6.25': 'FLOT',
 'MTSI-6.25': 'MTSS',
 'TATP-6.25': 'TATNP',
 'CHMF-6.25': 'CHMF',
 'RASP-6.25': 'RASP',
 'IRAO-6.25': 'IRAO',
 'SNGP-6.25': 'SNGSP',
 'PLZL-6.25': 'PLZL',
 'SPBE-6.25': 'SPBE'
}

def run_moex_parser() -> pd.DataFrame:
    codes = _contract_codes()
    data = []

    # Настройка браузера
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Безголовый режим
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    try:
        for code in codes:
            url = f"https://www.moex.com/ru/contract.aspx?code={code}"
            driver.get(url)
            try:
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "contract-open-positions")))

                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                table = soup.find('table', class_='contract-open-positions table1')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        cols = [ele.get_text(strip=True).replace('\xa0', '') for ele in cols]
                        if cols:
                            data.append([codes[code]] + cols)
            except Exception as e:
                # просто пропускаем проблемный контракт
                pass
            time.sleep(0.5)
    finally:
        driver.quit()

    if not data:
        return pd.DataFrame()

    columns = ['Contract Code', 'Metric', 'Value1', 'Value2', 'Value3', 'Value4', 'Value5']
    df = pd.DataFrame(data, columns=columns)
    df['Date'] = datetime.datetime.now().strftime('%Y-%m-%d')
    df['Contract Code'] = df['Contract Code'].str.split('-').str[0]
    return df
# with webdriver.Chrome(options=options) as driver:
#     driver.get('https://www.moex.com/ru/derivatives/')
#     print("Открыта главная страница MOEX.")

#     # Обработка каждого контракта
#     for code in contract_codes:
#         url = f"https://www.moex.com/ru/contract.aspx?code={code}"
#         driver.get(url)
#         print(f"Открыта страница контракта: {url}")

#         try:
#             # Ждём загрузки таблицы
#             wait = WebDriverWait(driver, 15)
#             wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table1")))

#             # Получаем HTML-код страницы
#             page_source = driver.page_source
#             soup = BeautifulSoup(page_source, 'html.parser')

#             # Извлечение ISIN-кода
#             isin = "Не найден"
#             message_div = soup.find('div', class_='ContractTablesOptions_message_1NAdF')
#             if message_div:
#                 message_text = message_div.get_text(strip=True)
#                 match = re.search(r'ISIN:\s*([A-Z0-9]+)', message_text)
#                 if match:
#                     isin = match.group(1)
#             print(f"Найден ISIN для {code}: {isin}")

#             # Поиск таблицы с данными
#             table = soup.find('table', class_='contract-open-positions') or soup.find('table', class_='table1')

#             if table:
#                 # Извлечение данных
#                 rows = table.find_all('tr')
#                 for row in rows:
#                     cols = row.find_all('td')
#                     cols = [ele.get_text(strip=True).replace('\xa0', '') for ele in cols]
#                     if cols:
#                         data.append([code, isin] + cols)
#                 print(f"Данные для контракта {code} успешно извлечены.")
#             else:
#                 print(f"Таблица не найдена для контракта {code}.")
#         except Exception as e:
#             print(f"Ошибка при обработке контракта {code}: {e}")
        
#         time.sleep(0.5)

if __name__ == "__main__":
    df = run_moex_parser()
    if df.empty:
        print("Данные не были найдены или сохранены.")
    else:
        df.to_csv('contracts_summary.csv', index=False, encoding='utf-8-sig')
        print("Данные успешно сохранены в contracts_summary.csv")
