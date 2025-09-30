#!/usr/bin/env python3
"""
Test API Filtering.
Тестирование правильной фильтрации через параметры Tinkoff API.
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_api_filtering():
    """Тестировать правильную фильтрацию через API."""
    print("🔍 Тестирование правильной фильтрации через Tinkoff API...")
    
    try:
        from core.shares_integration import SharesIntegrator
        
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
        
        print("\n📊 Загрузка всех акций (INSTRUMENT_STATUS_ALL)...")
        all_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=False)
        print(f"Всего акций: {len(all_shares)}")
        
        print("\n🇷🇺 Загрузка российских акций (INSTRUMENT_STATUS_BASE)...")
        russian_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=True)
        print(f"Российских акций: {len(russian_shares)}")
        
        if len(all_shares) > 0:
            print(f"\n📈 Экономия: {len(all_shares) - len(russian_shares)} акций ({((len(all_shares) - len(russian_shares)) / len(all_shares) * 100):.1f}%)")
        
        # Показываем примеры российских акций
        print("\n🏢 Примеры российских акций:")
        for i, share in enumerate(russian_shares[:10]):
            share_type = share.get('share_type', 'Unknown')
            print(f"  {i+1}. {share['ticker']} - {share['name']} ({share['currency']}) [{share_type}]")
        
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
        
        # Показываем типы акций
        share_types = {}
        for share in russian_shares:
            share_type = share.get('share_type', 'Unknown')
            share_types[share_type] = share_types.get(share_type, 0) + 1
        
        print(f"\n📊 Типы акций:")
        for share_type, count in share_types.items():
            print(f"  {share_type}: {count} акций")
        
        print("\n✅ Тест завершен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_filtering()
