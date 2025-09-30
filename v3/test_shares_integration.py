#!/usr/bin/env python3
"""
Shares Integration Test.
Тест интеграции акций в базу данных.
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_shares_integration():
    """Тест интеграции акций."""
    print("Тест интеграции акций...")
    
    try:
        from core.shares_integration import SharesIntegrator
        
        # Получаем API ключ
        api_key = None
        try:
            with open('.streamlit/secrets.toml', 'r', encoding='utf-8') as f:
                content = f.read()
                for line in content.split('\n'):
                    if 'TINKOFF_API_KEY' in line and '=' in line:
                        api_key = line.split('=')[1].strip().strip('"').strip("'")
                        break
        except FileNotFoundError:
            pass
        
        if not api_key:
            print("API ключ не найден. Проверьте .streamlit/secrets.toml")
            return
        
        print(f"API ключ найден: {api_key[:10]}...")
        
        # Создаем интегратор
        integrator = SharesIntegrator()
        
        # Добавляем поддержку акций в таблицу
        print("\nДобавление поддержки акций в таблицу companies...")
        integrator.add_shares_support_to_companies_table()
        
        # Загружаем российские акции
        print("\nЗагрузка российских акций...")
        russian_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=True)
        print(f"Загружено {len(russian_shares)} российских акций")
        
        if len(russian_shares) > 0:
            print("\nПримеры российских акций:")
            for i, share in enumerate(russian_shares[:5]):
                print(f"  {i+1}. {share['ticker']} - {share['name']} ({share['currency']}) [{share['isin']}]")
        
        # Интегрируем акции в базу данных
        print("\nИнтеграция акций в базу данных...")
        result = integrator.integrate_shares_into_database(api_key, russian_only=True)
        print(f"Результат интеграции: {result}")
        
        # Проверяем, что акции добавлены в базу
        print("\nПроверка базы данных...")
        import sqlite3
        conn = sqlite3.connect("stock_data.db")
        cursor = conn.cursor()
        
        # Подсчитываем акции
        cursor.execute("SELECT COUNT(*) FROM companies WHERE asset_type = 'shares'")
        shares_count = cursor.fetchone()[0]
        print(f"Акций в базе данных: {shares_count}")
        
        # Показываем примеры акций из базы
        cursor.execute("SELECT ticker, name, currency, isin FROM companies WHERE asset_type = 'shares' LIMIT 5")
        shares_in_db = cursor.fetchall()
        
        print("\nПримеры акций из базы данных:")
        for i, (ticker, name, currency, isin) in enumerate(shares_in_db):
            print(f"  {i+1}. {ticker} - {name} ({currency}) [{isin}]")
        
        conn.close()
        
        print("\nТест интеграции завершен успешно!")
        
    except Exception as e:
        print(f"Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_shares_integration()