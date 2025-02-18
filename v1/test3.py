# import time
# from datetime import datetime, timedelta

# test = datetime.now() - timedelta(days=1)
# print(test.strftime('%Y-%m-%d'))

# print(datetime.datetime.now().strftime('%Y-%m-%d'))
import sqlite3
import pandas as pd

DB_NAME = "stock_data.db"

def fix_metrics_links():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Поиск всех несвязанных записей
        cursor.execute("""
            SELECT m.id, m.metric_type, dd.date, c.contract_code
            FROM metrics m
            LEFT JOIN daily_data dd ON m.daily_data_id = dd.id
            LEFT JOIN companies c ON dd.company_id = c.id
            WHERE dd.id IS NULL
        """)
        rows = cursor.fetchall()

        # Исправление ссылок
        for m_id, metric_type, date, contract_code in rows:
            if contract_code and date:
                cursor.execute("""
                    SELECT dd.id FROM daily_data dd
                    JOIN companies c ON dd.company_id = c.id
                    WHERE c.contract_code = ? AND dd.date = ?
                """, (contract_code, date))
                result = cursor.fetchone()
                if result:
                    daily_data_id = result[0]
                    cursor.execute("""
                        UPDATE metrics SET daily_data_id = ? WHERE id = ?
                    """, (daily_data_id, m_id))

        conn.commit()

fix_metrics_links()
print("Связи восстановлены.")


# contract_codes = {
#  'IMOEXF': 'IMOEXF',
#  'SBRF-3.25': 'SBER',
#  'GAZR-3.25': 'GAZP',
#  'SMLT-3.25': 'SMLT',
#  'GMKN-3.25': 'GMKN',
#  'YDEX-3.25': 'YDEX',
#  'MGNT-3.25': 'MGNT',
#  'ISKJ-3.25': 'ABIO',
#  'VTBR-3.25': 'VTBR',
#  'SGZH-3.25': 'SGZH',
#  'TRNF-3.25': 'TRNFP',
#  'WUSH-3.25': 'WUSH',
#  'VKCO-3.25': 'VKCO',
#  'ALIBABA-3.25': 'BABA',
#  'BAIDU-3.25': 'BIDU',
#  'SIBN-3.25': 'SIBN',
#  'RNFT-3.25': 'RNFT',
#  'MVID-3.25': 'MVID',
#  'PIKK-3.25': 'PIKK',
#  'BELUGA-3.25': 'BELU',
#  'MTLR-3.25': 'MTLR',
#  'POSI-3.25': 'POSI',
#  'ASTR-3.25': 'ASTR',
#  'SOFL-3.25': 'SOFL',
#  'ALRS-3.25': 'ALRS',
#  'NLMK-3.25': 'NLMK',
#  'AFLT-3.25': 'AFLT',
#  'BANE-3.25': 'BANE',
#  'RUAL-3.25': 'RUAL',
#  'LEAS-3.25': 'LEAS',
#  'AFKS-3.25': 'AFKS',
#  'RTKM-3.25': 'RTKM',
#  'SFIN-3.25': 'SFIN',
#  'MOEX-3.25': 'MOEX',
#  'SBPR-3.25': 'SBERP',
#  'ROSN-3.25': 'ROSN',
#  'TCSI-3.25': 'T',
#  'FESH-3.25': 'FESH',
#  'PHOR-3.25': 'PHOR',
#  'SVCB-3.25': 'SVCB',
#  'CBOM-3.25': 'CBOM',
#  'LKOH-3.25': 'LKOH',
#  'KMAZ-3.25': 'KMAZ',
#  'SNGR-3.25': 'SNGS',
#  'HYDR-3.25': 'HYDR',
#  'NOTK-3.25': 'NVTK',
#  'FEES-3.25': 'FEES',
#  'MAGN-3.25': 'MAGN',
#  'BSPB-3.25': 'BSPB',
#  'TATN-3.25': 'TATN',
#  'FLOT-3.25': 'FLOT',
#  'MTSI-3.25': 'MTSS',
#  'TATP-3.25': 'TATNP',
#  'CHMF-3.25': 'CHMF',
#  'RASP-3.25': 'RASP',
#  'IRAO-3.25': 'IRAO',
#  'SNGP-3.25': 'SNGSP',
#  'PLZL-3.25': 'PLZL',
#  'SPBE-3.25': 'SPBE'
# }