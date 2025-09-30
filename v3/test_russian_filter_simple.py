#!/usr/bin/env python3
"""
Simple Russian Filter Test.
Простой тест фильтрации российских акций без зависимостей от core модулей.
"""

import os
import sys

def test_russian_filter_simple():
    """Простой тест фильтрации российских акций."""
    print("Простой тест фильтрации российских акций...")
    
    try:
        # Прямой импорт Tinkoff SDK
        from tinkoff.invest import Client as _Client
        from tinkoff.invest.schemas import InstrumentStatus, ShareType
        print("Tinkoff SDK импортирован успешно")
        
        # Получаем API ключ из переменной окружения или файла
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
        
        # Тестируем загрузку акций
        with _Client(api_key) as client:
            print("\nЗагрузка всех акций (INSTRUMENT_STATUS_ALL)...")
            all_instruments = client.instruments.shares(
                instrument_status=InstrumentStatus.INSTRUMENT_STATUS_ALL
            ).instruments
            
            print(f"Всего инструментов: {len(all_instruments)}")
            
            # Фильтруем только акции с тикером
            all_shares = []
            for share in all_instruments:
                if not getattr(share, "ticker", None):
                    continue
                
                # Дополнительная фильтрация по типу акций
                share_type = getattr(share, 'share_type', None)
                if share_type and share_type not in [ShareType.SHARE_TYPE_COMMON, ShareType.SHARE_TYPE_PREFERRED]:
                    continue
                
                all_shares.append({
                    'ticker': share.ticker,
                    'name': getattr(share, 'name', ''),
                    'currency': getattr(share, 'currency', ''),
                    'isin': getattr(share, 'isin', ''),
                    'share_type': getattr(share, 'share_type', None)
                })
            
            print(f"Акций с тикером: {len(all_shares)}")
            
            # Показываем примеры всех акций
            print("\nПримеры всех акций:")
            for i, share in enumerate(all_shares[:10]):
                currency = share.get('currency', 'Unknown')
                isin = share.get('isin', 'Unknown')
                print(f"  {i+1}. {share['ticker']} - {share['name']} ({currency}) [{isin}]")
            
            # Фильтруем российские акции
            print("\nФильтрация российских акций...")
            russian_shares = []
            for share in all_shares:
                currency = share.get('currency', '')
                isin = share.get('isin', '')
                
                # Фильтруем только RUB валюту и RU ISIN
                if currency == 'RUB' or isin.startswith('RU'):
                    russian_shares.append(share)
            
            print(f"Российских акций: {len(russian_shares)}")
            
            if len(all_shares) > 0:
                print(f"\nЭкономия: {len(all_shares) - len(russian_shares)} акций ({((len(all_shares) - len(russian_shares)) / len(all_shares) * 100):.1f}%)")
            
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
            non_russian_count = 0
            for share in russian_shares:
                currency = share.get('currency', '')
                isin = share.get('isin', '')
                if currency != 'RUB' and not isin.startswith('RU'):
                    non_russian_count += 1
                    print(f"  Не российская акция: {share['ticker']} ({currency}) [{isin}]")
            
            if non_russian_count == 0:
                print("\nВсе загруженные акции являются российскими!")
            else:
                print(f"\nНайдено {non_russian_count} не российских акций")
            
            print("\nТест завершен успешно!")
        
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Установите tinkoff-invest: pip install tinkoff-invest")
    except Exception as e:
        print(f"Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_russian_filter_simple()

