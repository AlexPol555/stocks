#!/usr/bin/env python3
"""
Simple Filter Logic Test.
Простой тест логики фильтрации без Tinkoff SDK.
"""

def test_filter_logic():
    """Тест логики фильтрации российских акций."""
    print("Простой тест логики фильтрации российских акций...")
    
    # Симулируем данные акций
    test_shares = [
        # Российские акции
        {'ticker': 'SBER', 'name': 'Сбербанк', 'currency': 'RUB', 'isin': 'RU0009029540'},
        {'ticker': 'GAZP', 'name': 'Газпром', 'currency': 'RUB', 'isin': 'RU0007661625'},
        {'ticker': 'LKOH', 'name': 'Лукойл', 'currency': 'RUB', 'isin': 'RU0009024277'},
        {'ticker': 'NVTK', 'name': 'Новатэк', 'currency': 'RUB', 'isin': 'RU0009062467'},
        {'ticker': 'ROSN', 'name': 'Роснефть', 'currency': 'RUB', 'isin': 'RU000A0J2Q06'},
        
        # Американские акции
        {'ticker': 'AAPL', 'name': 'Apple Inc', 'currency': 'USD', 'isin': 'US0378331005'},
        {'ticker': 'MSFT', 'name': 'Microsoft Corp', 'currency': 'USD', 'isin': 'US5949181045'},
        {'ticker': 'GOOGL', 'name': 'Alphabet Inc', 'currency': 'USD', 'isin': 'US02079K3059'},
        
        # Европейские акции
        {'ticker': 'ASML', 'name': 'ASML Holding', 'currency': 'EUR', 'isin': 'NL0010273215'},
        {'ticker': 'SAP', 'name': 'SAP SE', 'currency': 'EUR', 'isin': 'DE0007164600'},
        
        # Российские акции с USD валютой (редко, но возможно)
        {'ticker': 'YNDX', 'name': 'Yandex', 'currency': 'USD', 'isin': 'RU0009024277'},
    ]
    
    print(f"Всего тестовых акций: {len(test_shares)}")
    
    # Показываем все акции
    print("\nВсе тестовые акции:")
    for i, share in enumerate(test_shares):
        currency = share.get('currency', 'Unknown')
        isin = share.get('isin', 'Unknown')
        print(f"  {i+1}. {share['ticker']} - {share['name']} ({currency}) [{isin}]")
    
    # Применяем фильтрацию российских акций
    print("\nПрименение фильтрации российских акций...")
    russian_shares = []
    for share in test_shares:
        currency = share.get('currency', '')
        isin = share.get('isin', '')
        
        # Фильтруем только RUB валюту ИЛИ RU ISIN
        if currency == 'RUB' or isin.startswith('RU'):
            russian_shares.append(share)
    
    print(f"Российских акций после фильтрации: {len(russian_shares)}")
    
    # Показываем отфильтрованные акции
    print("\nОтфильтрованные российские акции:")
    for i, share in enumerate(russian_shares):
        currency = share.get('currency', 'Unknown')
        isin = share.get('isin', 'Unknown')
        print(f"  {i+1}. {share['ticker']} - {share['name']} ({currency}) [{isin}]")
    
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
    
    # Тестируем разные варианты фильтрации
    print("\nТестирование разных вариантов фильтрации:")
    
    # Вариант 1: Только RUB валюта
    rub_only = [s for s in test_shares if s.get('currency') == 'RUB']
    print(f"Только RUB валюта: {len(rub_only)} акций")
    
    # Вариант 2: Только RU ISIN
    ru_isin_only = [s for s in test_shares if s.get('isin', '').startswith('RU')]
    print(f"Только RU ISIN: {len(ru_isin_only)} акций")
    
    # Вариант 3: RUB ИЛИ RU ISIN (текущий)
    rub_or_ru = [s for s in test_shares if s.get('currency') == 'RUB' or s.get('isin', '').startswith('RU')]
    print(f"RUB ИЛИ RU ISIN: {len(rub_or_ru)} акций")
    
    # Вариант 4: RUB И RU ISIN (строгий)
    rub_and_ru = [s for s in test_shares if s.get('currency') == 'RUB' and s.get('isin', '').startswith('RU')]
    print(f"RUB И RU ISIN: {len(rub_and_ru)} акций")
    
    print("\nТест завершен успешно!")

if __name__ == "__main__":
    test_filter_logic()
