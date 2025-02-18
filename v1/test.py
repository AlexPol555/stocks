import pandas as pd
contract_codes = {
 'IMOEXF': 'IMOEXF',
 'SBRF-12.24': 'SBER',
 'GAZR-12.24': 'GAZP',
 'SMLT-12.24': 'SMLT',
 'GMKN-12.24': 'GMKN',
 'YDEX-12.24': 'YDEX',
 'MGNT-12.24': 'MGNT',
 'ISKJ-12.24': 'ABIO',
 'VTBR-12.24': 'VTBR',
 'SGZH-12.24': 'SGZH',
 'TRNF-12.24': 'TRNFP',
 'WUSH-12.24': 'WUSH',
 'VKCO-12.24': 'VKCO',
 'ALIBABA-12.24': 'BABA',
 'BAIDU-12.24': 'BIDU',
 'SIBN-12.24': 'SIBN',
 'RNFT-12.24': 'RNFT',
 'MVID-12.24': 'MVID',
 'PIKK-12.24': 'PIKK',
 'BELUGA-12.24': 'BELU',
 'MTLR-12.24': 'MTLR',
 'POSI-12.24': 'POSI',
 'ASTR-12.24': 'ASTR',
 'SOFL-12.24': 'SOFL',
 'ALRS-12.24': 'ALRS',
 'NLMK-12.24': 'NLMK',
 'AFLT-12.24': 'AFLT',
 'BANE-12.24': 'BANE',
 'RUAL-12.24': 'RUAL',
 'LEAS-12.24': 'LEAS',
 'AFKS-12.24': 'AFKS',
 'RTKM-12.24': 'RTKM',
 'SFIN-12.24': 'SFIN',
 'MOEX-12.24': 'MOEX',
 'SBPR-12.24': 'SBERP',
 'ROSN-12.24': 'ROSN',
 'TCSI-12.24': 'T',
 'FESH-12.24': 'FESH',
 'PHOR-12.24': 'PHOR',
 'SVCB-12.24': 'SVCB',
 'CBOM-12.24': 'CBOM',
 'LKOH-12.24': 'LKOH',
 'KMAZ-12.24': 'KMAZ',
 'SNGR-12.24': 'SNGS',
 'HYDR-12.24': 'HYDR',
 'NOTK-12.24': 'NVTK',
 'FEES-12.24': 'FEES',
 'MAGN-12.24': 'MAGN',
 'BSPB-12.24': 'BSPB',
 'TATN-12.24': 'TATN',
 'FLOT-12.24': 'FLOT',
 'MTSI-12.24': 'MTSS',
 'TATP-12.24': 'TATNP',
 'CHMF-12.24': 'CHMF',
 'RASP-12.24': 'RASP',
 'IRAO-12.24': 'IRAO',
 'SNGP-12.24': 'SNGSP',
 'PLZL-12.24': 'PLZL',
 'SPBE-12.24': 'SPBE'
}
def update_contract_codes_in_csv(input_csv_path: str, output_csv_path: str, contract_codes: dict):
    """
    Функция считывает CSV-файл, заменяет все совпадения в столбце "Contract Code" согласно словарю
    contract_codes и сохраняет результат в новый CSV-файл.

    :param input_csv_path: Путь к исходному CSV-файлу.
    :param output_csv_path: Путь для сохранения изменённого CSV-файла.
    :param contract_codes: Словарь для замены, например:
                           {'IMOEXF': 'IMOEXF', 'SBRF-12.24': 'SBER'}
    """
    # Считываем CSV
    df = pd.read_csv(input_csv_path)
    
    # Выполняем замену значений в столбце "Contract Code"
    df["Contract Code"] = df["Contract Code"].replace(contract_codes)
    
    # Сохраняем результат в новый CSV
    df.to_csv(output_csv_path, index=False)
    print(f"Данные сохранены в {output_csv_path}")

# Пример использования:


# Предположим, что исходный файл называется "input.csv" и результат мы сохраним в "output.csv"
update_contract_codes_in_csv("D:\output1.csv", "D:\output.csv", contract_codes)
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from bs4 import BeautifulSoup
# import pandas as pd
# import time
# import datetime
# import re


# # Массив с кодами контрактов
# contract_codes = {
#  'IMOEXF': 'IMOEXF',
#  'SBRF-12.24': 'SBER',
#  'GAZR-12.24': 'GAZP',
#  'SMLT-12.24': 'SMLT',
#  'GMKN-12.24': 'GMKN',
#  'YDEX-12.24': 'YDEX',
#  'MGNT-12.24': 'MGNT',
#  'ISKJ-12.24': 'ABIO',
#  'VTBR-12.24': 'VTBR',
#  'SGZH-12.24': 'SGZH',
#  'TRNF-12.24': 'TRNFP',
#  'WUSH-12.24': 'WUSH',
#  'VKCO-12.24': 'VKCO',
#  'ALIBABA-12.24': 'BABA',
#  'BAIDU-12.24': 'BIDU',
#  'SIBN-12.24': 'SIBN',
#  'RNFT-12.24': 'RNFT',
#  'MVID-12.24': 'MVID',
#  'PIKK-12.24': 'PIKK',
#  'BELUGA-12.24': 'BELU',
#  'MTLR-12.24': 'MTLR',
#  'POSI-12.24': 'POSI',
#  'ASTR-12.24': 'ASTR',
#  'SOFL-12.24': 'SOFL',
#  'ALRS-12.24': 'ALRS',
#  'NLMK-12.24': 'NLMK',
#  'AFLT-12.24': 'AFLT',
#  'BANE-12.24': 'BANE',
#  'RUAL-12.24': 'RUAL',
#  'LEAS-12.24': 'LEAS',
#  'AFKS-12.24': 'AFKS',
#  'RTKM-12.24': 'RTKM',
#  'SFIN-12.24': 'SFIN',
#  'MOEX-12.24': 'MOEX',
#  'SBPR-12.24': 'SBERP',
#  'ROSN-12.24': 'ROSN',
#  'TCSI-12.24': 'T',
#  'FESH-12.24': 'FESH',
#  'PHOR-12.24': 'PHOR',
#  'SVCB-12.24': 'SVCB',
#  'CBOM-12.24': 'CBOM',
#  'LKOH-12.24': 'LKOH',
#  'KMAZ-12.24': 'KMAZ',
#  'SNGR-12.24': 'SNGS',
#  'HYDR-12.24': 'HYDR',
#  'NOTK-12.24': 'NVTK',
#  'FEES-12.24': 'FEES',
#  'MAGN-12.24': 'MAGN',
#  'BSPB-12.24': 'BSPB',
#  'TATN-12.24': 'TATN',
#  'FLOT-12.24': 'FLOT',
#  'MTSI-12.24': 'MTSS',
#  'TATP-12.24': 'TATNP',
#  'CHMF-12.24': 'CHMF',
#  'RASP-12.24': 'RASP',
#  'IRAO-12.24': 'IRAO',
#  'SNGP-12.24': 'SNGSP',
#  'PLZL-12.24': 'PLZL',
#  'SPBE-12.24': 'SPBE'
# }

# # for key in contract_codes: 
# #     print(key, contract_codes[key])
# data = []

# # Настройка браузера
# options = webdriver.ChromeOptions()
# options.add_argument("--headless")  # Безголовый режим
# options.add_argument("--disable-gpu")
# options.add_argument("--no-sandbox")

# # Инициализация драйвера через Selenium Manager
# driver = webdriver.Chrome(options=options)

# # Обработка каждого контракта
# for code in contract_codes:
#     url = f"https://www.moex.com/ru/contract.aspx?code={code}"
#     driver.get(url)  # Открываем страницу
    
#     try:
#         # Ждём загрузки таблицы
#         wait = WebDriverWait(driver, 10)
#         wait.until(EC.presence_of_element_located((By.CLASS_NAME, "contract-open-positions")))

#         # Получаем HTML-код страницы
#         page_source = driver.page_source
#         soup = BeautifulSoup(page_source, 'html.parser')
#         # Поиск таблицы с нужным классом
#         table = soup.find('table', class_='contract-open-positions table1')
#         print(code)
#         if table:
#             # Извлечение данных
#             rows = table.find_all('tr')
#             for row in rows:
#                 cols = row.find_all('td')
#                 cols = [ele.get_text(strip=True).replace('\xa0', '') for ele in cols]
#                 if cols:
#                     data.append([contract_codes[code]] + cols)
#         else:
#             print(f"Таблица не найдена для контракта {code}.")
#     except Exception as e:
#         print(f"Ошибка при обработке контракта {code}: {e}")
#     time.sleep(0.5)

# # Завершаем работу драйвера
# driver.quit()
# # with webdriver.Chrome(options=options) as driver:
# #     driver.get('https://www.moex.com/ru/derivatives/')
# #     print("Открыта главная страница MOEX.")

# #     # Обработка каждого контракта
# #     for code in contract_codes:
# #         url = f"https://www.moex.com/ru/contract.aspx?code={code}"
# #         driver.get(url)
# #         print(f"Открыта страница контракта: {url}")

# #         try:
# #             # Ждём загрузки таблицы
# #             wait = WebDriverWait(driver, 15)
# #             wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table1")))

# #             # Получаем HTML-код страницы
# #             page_source = driver.page_source
# #             soup = BeautifulSoup(page_source, 'html.parser')

# #             # Извлечение ISIN-кода
# #             isin = "Не найден"
# #             message_div = soup.find('div', class_='ContractTablesOptions_message_1NAdF')
# #             if message_div:
# #                 message_text = message_div.get_text(strip=True)
# #                 match = re.search(r'ISIN:\s*([A-Z0-9]+)', message_text)
# #                 if match:
# #                     isin = match.group(1)
# #             print(f"Найден ISIN для {code}: {isin}")

# #             # Поиск таблицы с данными
# #             table = soup.find('table', class_='contract-open-positions') or soup.find('table', class_='table1')

# #             if table:
# #                 # Извлечение данных
# #                 rows = table.find_all('tr')
# #                 for row in rows:
# #                     cols = row.find_all('td')
# #                     cols = [ele.get_text(strip=True).replace('\xa0', '') for ele in cols]
# #                     if cols:
# #                         data.append([code, isin] + cols)
# #                 print(f"Данные для контракта {code} успешно извлечены.")
# #             else:
# #                 print(f"Таблица не найдена для контракта {code}.")
# #         except Exception as e:
# #             print(f"Ошибка при обработке контракта {code}: {e}")
        
# #         time.sleep(0.5)

# # Вывод собранных данных
# for entry in data:
#     print(entry)

# if data:
#     columns = ['Contract Code', 'Metric', 'Value1', 'Value2', 'Value3', 'Value4', 'Value5']
#     df = pd.DataFrame(data, columns=columns)

#     # Добавляем колонку с текущей датой
#     df['Date'] = datetime.datetime.now().strftime('%Y-%m-%d')
#     df['Contract Code'] = df['Contract Code'].str.split('-').str[0]
#     # Сохранение в CSV
#     df.to_csv('contracts_summary.csv', index=False, encoding='utf-8-sig')
#     print("Данные успешно сохранены в contracts_data.csv")
# else:
#     print("Данные не были найдены или сохранены.")
