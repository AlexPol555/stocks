import sqlite3

conn = sqlite3.connect('stock_data.db')
cursor = conn.cursor()

# Проверяем таблицы
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'data_%'")
tables = cursor.fetchall()

print("Data tables:")
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"  {table_name}: {count} records")

# Проверяем компании
cursor.execute("SELECT COUNT(*) FROM companies")
companies = cursor.fetchone()[0]
print(f"Companies: {companies}")

conn.close()
