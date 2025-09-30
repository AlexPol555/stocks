#!/usr/bin/env python3
"""
Test Russian Stocks Filter.
Тестирование фильтрации российских акций.
"""

import os
import sys
from core.shares_integration import SharesIntegrator

def test_russian_stocks_filter():
    """Тестировать фильтрацию российских акций."""
    print("🔍 Тестирование фильтрации российских акций...")
    
    # Получаем API ключ
    api_key = None
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and hasattr(st.secrets, 'TINKOFF_API_KEY'):
            api_key = st.secrets.TINKOFF_API_KEY
    except ImportError:
        pass
    
    if not api_key:
        print("❌ API ключ не найден. Проверьте .streamlit/secrets.toml")
        return
    
    integrator = SharesIntegrator()
    
    print("📊 Загрузка всех акций...")
    all_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=False)
    print(f"Всего акций: {len(all_shares)}")
    
    print("\n🇷🇺 Загрузка только российских акций...")
    russian_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=True)
    print(f"Российских акций: {len(russian_shares)}")
    
    print(f"\n📈 Экономия: {len(all_shares) - len(russian_shares)} акций ({((len(all_shares) - len(russian_shares)) / len(all_shares) * 100):.1f}%)")
    
    # Показываем примеры российских акций
    print("\n🏢 Примеры российских акций:")
    for i, share in enumerate(russian_shares[:10]):
        print(f"  {i+1}. {share['ticker']} - {share['name']} ({share['currency']})")
    
    if len(russian_shares) > 10:
        print(f"  ... и еще {len(russian_shares) - 10} акций")
    
    # Показываем валюты
    currencies = {}
    for share in russian_shares:
        currency = share.get('currency', 'Unknown')
        currencies[currency] = currencies.get(currency, 0) + 1
    
    print(f"\n💱 Валюты российских акций:")
    for currency, count in currencies.items():
        print(f"  {currency}: {count} акций")

if __name__ == "__main__":
    test_russian_stocks_filter()
