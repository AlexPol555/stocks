import sqlite3
conn = sqlite3.connect('stock_data.db')
for table in ['articles','article_ticker','tickers']:
    print('---', table)
    try:
        cur = conn.execute(f'PRAGMA table_info({table})')
        rows = cur.fetchall()
        if not rows:
            print('  (no rows)')
        for row in rows:
            print(' ', row)
    except Exception as exc:
        print(table, exc)
