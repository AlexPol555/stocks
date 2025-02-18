import pandas as pd

def bulk_populate_database_from_csv(csv_path_or_buffer: str, conn):
    """
    Массовая загрузка: заполняет базу данных из CSV-файла, где CSV содержит заголовки:
    Contract Code,Metric,Value1,Value2,Value3,Value4,Value5,Date
    После успешной загрузки этот CSV можно удалить.
    """
    try:
        df = pd.read_csv(csv_path_or_buffer)
    except Exception as e:
        raise ValueError(f"Ошибка при чтении CSV: {e}")

    # Если первый столбец – индекс (например, "Unnamed: 0"), удаляем его
    if df.columns[0].startswith("Unnamed"):
        df = df.drop(columns=df.columns[0])
    
    # Проверка наличия необходимых столбцов
    required_columns = {"Contract Code", "Metric", "Value1", "Value2", "Value3", "Value4", "Value5", "Date"}
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        raise ValueError(f"Отсутствуют обязательные столбцы: {missing}")
    
    # Преобразуем столбец Date, вычитая один день (смещение)
    df["Date"] = pd.to_datetime(df["Date"]) - pd.Timedelta(days=1)
    # Фильтруем записи: оставляем только будние дни (понедельник=0, ..., пятница=4)
    df = df[df["Date"].dt.weekday < 5]
    
    cursor = conn.cursor()
    
    # 1. Заполнение таблицы companies
    companies = df["Contract Code"].unique()
    for comp in companies:
        cursor.execute("INSERT OR IGNORE INTO companies (contract_code) VALUES (?)", (comp,))
    conn.commit()
    
    # Получаем отображение: contract_code -> company_id
    cursor.execute("SELECT id, contract_code FROM companies")
    comp_map = {row[1]: row[0] for row in cursor.fetchall()}
    print("Карта компаний:", comp_map)
    
    # 2. Вставляем данные в таблицу metrics
    for _, row in df.iterrows():
        company_id = comp_map.get(row["Contract Code"])
        if company_id is None:
            continue
        cursor.execute("""
            INSERT INTO metrics (company_id, metric_type, value1, value2, value3, value4, value5, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            row["Metric"],
            row["Value1"],
            row["Value2"],
            row["Value3"],
            row["Value4"],
            row["Value5"],
            row["Date"].strftime("%Y-%m-%d")
        ))
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
