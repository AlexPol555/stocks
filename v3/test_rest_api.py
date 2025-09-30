#!/usr/bin/env python3
"""
REST API Test.
Тест с использованием REST API напрямую.
"""

import requests
import json
import os

def test_rest_api():
    """Тест с использованием REST API."""
    print("Тест с использованием REST API...")
    
    # Получаем API ключ
    api_key = None
    
    # Пробуем получить из переменной окружения
    api_key = os.getenv('TINKOFF_API_KEY')
    
    # Если не найден, пробуем из файла
    if not api_key:
        try:
            with open('.streamlit/secrets.toml', 'r', encoding='utf-8') as f:
                content = f.read()
                # Простой парсинг TOML
                for line in content.split('\n'):
                    if 'TINKOFF_API_KEY' in line and '=' in line:
                        api_key = line.split('=')[1].strip().strip('"').strip("'")
                        break
        except FileNotFoundError:
            pass
    
    if not api_key:
        print("API ключ не найден. Проверьте .streamlit/secrets.toml или переменную TINKOFF_API_KEY")
        return
    
    print(f"API ключ найден: {api_key[:10]}...")
    
    # Настройки API
    base_url = "https://invest-public-api.tbank.ru/rest/"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Получаем список акций
        print("\nЗагрузка списка акций...")
        response = requests.post(
            f"{base_url}/tinkoff.public.invest.api.contract.v1.InstrumentsService/Shares",
            headers=headers,
            json={"instrument_status": "INSTRUMENT_STATUS_ALL"}
        )
        
        if response.status_code == 200:
            data = response.json()
            shares = data.get('instruments', [])
            print(f"Загружено {len(shares)} инструментов")
            
            # Фильтруем только акции с тикером
            filtered_shares = []
            for share in shares:
                if not share.get("ticker"):
                    continue
                
                # Дополнительная фильтрация по типу акций
                share_type = share.get('shareType', '')
                if share_type and share_type not in ['SHARE_TYPE_COMMON', 'SHARE_TYPE_PREFERRED']:
                    continue
                
                filtered_shares.append({
                    'ticker': share.get('ticker', ''),
                    'name': share.get('name', ''),
                    'currency': share.get('currency', ''),
                    'isin': share.get('isin', ''),
                    'share_type': share.get('shareType', ''),
                    'trading_status': share.get('tradingStatus', ''),
                    'instrument_status': share.get('instrumentStatus', '')
                })
            
            print(f"Акций с тикером: {len(filtered_shares)}")
            
            # Показываем примеры всех акций
            print("\nПримеры всех акций:")
            for i, share in enumerate(filtered_shares[:10]):
                currency = share.get('currency', 'Unknown')
                isin = share.get('isin', 'Unknown')
                print(f"  {i+1}. {share['ticker']} - {share['name']} ({currency}) [{isin}]")
            
            # Фильтруем российские акции
            print("\nФильтрация российских акций...")
            russian_shares = []
            for share in filtered_shares:
                currency = share.get('currency', '')
                isin = share.get('isin', '')
                
                # Фильтруем только RUB валюту ИЛИ RU ISIN
                if currency == 'RUB' or isin.startswith('RU'):
                    russian_shares.append(share)
            
            print(f"Российских акций: {len(russian_shares)}")
            
            if len(filtered_shares) > 0:
                print(f"\nЭкономия: {len(filtered_shares) - len(russian_shares)} акций ({((len(filtered_shares) - len(russian_shares)) / len(filtered_shares) * 100):.1f}%)")
            
            # Показываем примеры российских акций
            print("\nПримеры российских акций:")
            for i, share in enumerate(russian_shares[:10]):
                currency = share.get('currency', 'Unknown')
                isin = share.get('isin', 'Unknown')
                print(f"  {i+1}. {share['ticker']} - {share['name']} ({currency}) [{isin}]")
            
            if len(russian_shares) > 10:
                print(f"  ... и еще {len(russian_shares) - 10} акций")
            
            # Анализируем валюты
            currencies = {}
            for share in russian_shares:
                currency = share.get('currency', 'Unknown')
                currencies[currency] = currencies.get(currency, 0) + 1
            
            print(f"\nВалюты российских акций:")
            for currency, count in currencies.items():
                print(f"  {currency}: {count} акций")
            
            # Анализируем ISIN коды
            isin_prefixes = {}
            for share in russian_shares:
                isin = share.get('isin', '')
                if isin:
                    prefix = isin[:2] if len(isin) >= 2 else 'Unknown'
                    isin_prefixes[prefix] = isin_prefixes.get(prefix, 0) + 1
            
            print(f"\nISIN префиксы российских акций:")
            for prefix, count in isin_prefixes.items():
                print(f"  {prefix}: {count} акций")
            
            # Проверяем качество фильтрации
            print("\nПроверка качества фильтрации:")
            non_russian_count = 0
            for share in russian_shares:
                currency = share.get('currency', '')
                isin = share.get('isin', '')
                if currency != 'RUB' and not isin.startswith('RU'):
                    non_russian_count += 1
                    print(f"  Не российская акция: {share['ticker']} ({currency}) [{isin}]")
            
            if non_russian_count == 0:
                print("Все загруженные акции являются российскими!")
            else:
                print(f"Найдено {non_russian_count} не российских акций")
            
            print("\nТест завершен успешно!")
            
        else:
            print(f"Ошибка API: {response.status_code}")
            print(f"Ответ: {response.text}")
            
    except Exception as e:
        print(f"Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rest_api()
