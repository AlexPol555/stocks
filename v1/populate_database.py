import pandas as pd

# def bulk_populate_database_from_csv(csv_path_or_buffer: str, conn):
#     """
#     Массовая загрузка: заполняет базу данных из CSV-файла, где CSV содержит заголовки:
#     Contract Code,Metric,Value1,Value2,Value3,Value4,Value5,Date
#     После успешной загрузки этот CSV можно удалить.
#     """
#     # Читаем CSV
#     df = pd.read_csv(csv_path_or_buffer)
#     # Если первый столбец – индекс (например, "Unnamed: 0"), удаляем его
#     if df.columns[0].startswith("Unnamed"):
#         df = df.drop(columns=df.columns[0])
    
#     # Преобразуем столбец Date, вычитая один день (смещение)
#     df["Date"] = pd.to_datetime(df["Date"]) - pd.Timedelta(days=1)
#     df['Contract Code'] = df['Contract Code'].str.split('-').str[0]
#     # Фильтруем записи: оставляем только будние дни (понедельник=0, ..., пятница=4)
#     df = df[df["Date"].dt.weekday < 5]
    
#     cursor = conn.cursor()
    
#     # 1. Заполнение таблицы companies
#     companies = df["Contract Code"].unique()
#     for comp in companies:
#         cursor.execute("INSERT OR IGNORE INTO companies (contract_code) VALUES (?)", (comp,))
#     conn.commit()
    
#     # Получаем отображение: contract_code -> company_id
#     cursor.execute("SELECT id, contract_code FROM companies")
#     comp_map = {row[1]: row[0] for row in cursor.fetchall()}
    
#     # 2. Создаем записи в daily_data для уникальных пар (Contract Code, Date)
#     daily_group = df.groupby(["Contract Code", "Date"]).size().reset_index()[["Contract Code", "Date"]]
#     daily_data_mapping = {}
#     for _, row in daily_group.iterrows():
#         company_id = comp_map[row["Contract Code"]]
#         cursor.execute("""
#             INSERT INTO daily_data (company_id, date, open, low, high, close, volume)
#             VALUES (?, ?, NULL, NULL, NULL, NULL, NULL)
#         """, (company_id, row["Date"].strftime("%Y-%m-%d")))
#         daily_data_id = cursor.lastrowid
#         daily_data_mapping[(row["Contract Code"], row["Date"].strftime("%Y-%m-%d"))] = daily_data_id
#     conn.commit()
    
#     # 3. Вставляем данные по метрикам для каждой строки CSV
#     for _, row in df.iterrows():
#         key = (row["Contract Code"], row["Date"].strftime("%Y-%m-%d"))
#         daily_data_id = daily_data_mapping.get(key)
#         if daily_data_id is None:
#             continue
#         cursor.execute("""
#             INSERT INTO metrics (daily_data_id, metric_type, value1, value2, value3, value4, value5)
#             VALUES (?, ?, ?, ?, ?, ?, ?)
#         """, (
#             daily_data_id,
#             row["Metric"],
#             row["Value1"],
#             row["Value2"],
#             row["Value3"],
#             row["Value4"],
#             row["Value5"]
#         ))
#     conn.commit()
def bulk_populate_database_from_csv(csv_path_or_buffer: str, conn):
    """
    Массовая загрузка данных в общий справочник companies.
    """
    df = pd.read_csv(csv_path_or_buffer)
    df["Instrument Type"] = df["Contract Code"].apply(lambda x: "futures" if "-" in x else "stock")
    df["Base Code"] = df["Contract Code"].str.split('-').str[0]

    cursor = conn.cursor()

    # 1. Заполняем общий справочник companies
    companies = df[["Contract Code", "Instrument Type"]].drop_duplicates()
    for _, row in companies.iterrows():
        cursor.execute("""
            INSERT OR IGNORE INTO companies (contract_code, instrument_type) 
            VALUES (?, ?)
        """, (row["Contract Code"], row["Instrument Type"]))
    conn.commit()

    # 2. Заполняем daily_data (для акций)
    daily_data = df[df["Instrument Type"] == "stock"]
    for _, row in daily_data.iterrows():
        cursor.execute("""
            INSERT INTO daily_data (company_id, date, open, low, high, close, volume)
            VALUES (
                (SELECT id FROM companies WHERE contract_code = ?), ?, ?, ?, ?, ?, ?
            )
        """, (row["Contract Code"], row["Date"], row["Open"], row["Low"], row["High"], row["Close"], row["Volume"]))
    conn.commit()

    # 3. Заполняем metrics (для фьючерсов)
    futures_data = df[df["Instrument Type"] == "futures"]
    for _, row in futures_data.iterrows():
        cursor.execute("""
            INSERT INTO metrics (daily_data_id, metric_type, value1, value2, value3, value4, value5)
            VALUES (
                (SELECT dd.id FROM daily_data dd
                 JOIN companies c ON dd.company_id = c.id
                 WHERE c.contract_code = ? AND dd.date = ?), 
                ?, ?, ?, ?, ?, ?
            )
        """, (row["Base Code"], row["Date"], row["Metric"], row["Value1"], row["Value2"], row["Value3"], row["Value4"], row["Value5"]))
    conn.commit()

def incremental_populate_database_from_csv(csv_path_or_buffer: str, conn):
    """
    Инкрементальная загрузка: добавляет данные из нового CSV-файла.
    Если для (Contract Code, Date) уже существует запись в daily_data,
    новые данные добавляются в таблицу metrics без создания новой записи в daily_data.
    """
    df = pd.read_csv(csv_path_or_buffer)
    if df.columns[0].startswith("Unnamed"):
        df = df.drop(columns=df.columns[0])
    # Преобразуем дату: вычитаем один день
    df["Date"] = pd.to_datetime(df["Date"]) - pd.Timedelta(days=1)
    # Оставляем только будние дни
    df['Contract Code'] = df['Contract Code'].str.split('-').str[0]
    df = df[df["Date"].dt.weekday < 5]
    
    cursor = conn.cursor()
    
    # Обновляем таблицу companies
    companies = df["Contract Code"].unique()
    for comp in companies:
        cursor.execute("INSERT OR IGNORE INTO companies (contract_code) VALUES (?)", (comp,))
    conn.commit()
    
    cursor.execute("SELECT id, contract_code FROM companies")
    comp_map = {row[1]: row[0] for row in cursor.fetchall()}
    
    # Проверяем наличие записи в daily_data для каждой уникальной пары (Contract Code, Date)
    daily_data_mapping = {}
    daily_group = df.groupby(["Contract Code", "Date"]).size().reset_index()[["Contract Code", "Date"]]
    for _, row in daily_group.iterrows():
        company_id = comp_map[row["Contract Code"]]
        date_str = row["Date"].strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT id FROM daily_data WHERE company_id = ? AND date = ?
        """, (company_id, date_str))
        result = cursor.fetchone()
        if result is None:
            cursor.execute("""
                INSERT INTO daily_data (company_id, date, open, low, high, close, volume)
                VALUES (?, ?, NULL, NULL, NULL, NULL, NULL)
            """, (company_id, date_str))
            daily_data_id = cursor.lastrowid
        else:
            daily_data_id = result[0]
        daily_data_mapping[(row["Contract Code"], date_str)] = daily_data_id
    conn.commit()
    
    # Вставляем данные в таблицу metrics
    for _, row in df.iterrows():
        key = (row["Contract Code"], row["Date"].strftime("%Y-%m-%d"))
        daily_data_id = daily_data_mapping.get(key)
        if daily_data_id is None:
            continue
        cursor.execute("""
            INSERT INTO metrics (daily_data_id, metric_type, value1, value2, value3, value4, value5)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            daily_data_id,
            row["Metric"],
            row["Value1"],
            row["Value2"],
            row["Value3"],
            row["Value4"],
            row["Value5"]
        ))
    conn.commit()
