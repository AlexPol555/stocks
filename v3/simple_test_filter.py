#!/usr/bin/env python3
"""
Simple Test for Russian Stocks Filter.
Простой тест фильтрации российских акций.
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_filter():
    """Тестировать фильтрацию."""
    print("🔍 Тестирование фильтрации российских акций...")
    
    try:
        from core.shares_integration import SharesIntegrator
        
        integrator = SharesIntegrator()
        
        # Создаем тестовую акцию
        class MockShare:
            def __init__(self, ticker, currency, name, isin):
                self.ticker = ticker
                self.currency = currency
                self.name = name
                self.isin = isin
        
        # Тестируем российские акции
        russian_shares = [
            MockShare("SBER", "RUB", "Сбербанк", "RU0009029540"),
            MockShare("GAZP", "RUB", "Газпром", "RU0007661625"),
            MockShare("YNDX", "RUB", "Яндекс", "RU0009024277"),
        ]
        
        # Тестируем иностранные акции
        foreign_shares = [
            MockShare("AAPL", "USD", "Apple Inc.", "US0378331005"),
            MockShare("TSLA", "USD", "Tesla Inc.", "US88160R1014"),
            MockShare("MSFT", "USD", "Microsoft Corporation", "US5949181045"),
        ]
        
        print("\n🇷🇺 Тестирование российских акций:")
        for share in russian_shares:
            is_russian = integrator._is_russian_share(share)
            print(f"  {share.ticker} ({share.currency}): {'✅' if is_russian else '❌'}")
        
        print("\n🌍 Тестирование иностранных акций:")
        for share in foreign_shares:
            is_russian = integrator._is_russian_share(share)
            print(f"  {share.ticker} ({share.currency}): {'✅' if is_russian else '❌'}")
        
        print("\n✅ Тест завершен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_filter()
