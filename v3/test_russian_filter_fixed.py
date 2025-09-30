#!/usr/bin/env python3
"""
Test Russian Filter Fixed.
Тестирование исправленной фильтрации российских акций.
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_russian_filter_fixed():
    """Тестировать исправленную фильтрацию российских акций."""
    print("🔍 Тестирование исправленной фильтрации российских акций...")
    
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
        
        # Показываем примеры всех акций
        print("\n🌍 Примеры всех акций:")
        for i, share in enumerate(all_shares[:10]):
            currency = share.get('currency', 'Unknown')
            isin = share.get('isin', 'Unknown')
            print(f"  {i+1}. {share['ticker']} - {share['name']} ({currency}) [{isin}]")
        
        print("\n🇷🇺 Загрузка российских акций (INSTRUMENT_STATUS_BASE + RUB + RU ISIN)...")
        russian_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=True)
        print(f"Российских акций: {len(russian_shares)}")
        
        if len(all_shares) > 0:
            print(f"\n📈 Экономия: {len(all_shares) - len(russian_shares)} акций ({((len(all_shares) - len(russian_shares)) / len(all_shares) * 100):.1f}%)")
        
        # Показываем примеры российских акций
        print("\n🏢 Примеры российских акций:")
        for i, share in enumerate(russian_shares[:10]):
            currency = share.get('currency', 'Unknown')
            isin = share.get('isin', 'Unknown')
            print(f"  {i+1}. {share['ticker']} - {share['name']} ({currency}) [{isin}]")
        
        if len(russian_shares) > 10:
            print(f"  ... и еще {len(russian_shares) - 10} акций")
        
        # Показываем валюты российских акций
        currencies = {}
        for share in russian_shares:
            currency = share.get('currency', 'Unknown')
            currencies[currency] = currencies.get(currency, 0) + 1
        
        print(f"\n💱 Валюты российских акций:")
        for currency, count in currencies.items():
            print(f"  {currency}: {count} акций")
        
        # Показываем ISIN коды российских акций
        isin_prefixes = {}
        for share in russian_shares:
            isin = share.get('isin', '')
            if isin:
                prefix = isin[:2] if len(isin) >= 2 else 'Unknown'
                isin_prefixes[prefix] = isin_prefixes.get(prefix, 0) + 1
        
        print(f"\n📋 ISIN префиксы российских акций:")
        for prefix, count in isin_prefixes.items():
            print(f"  {prefix}: {count} акций")
        
        # Проверяем, что все российские акции действительно российские
        non_russian_count = 0
        for share in russian_shares:
            currency = share.get('currency', '')
            isin = share.get('isin', '')
            if currency != 'RUB' and not isin.startswith('RU'):
                non_russian_count += 1
                print(f"  ⚠️ Не российская акция: {share['ticker']} ({currency}) [{isin}]")
        
        if non_russian_count == 0:
            print("\n✅ Все загруженные акции являются российскими!")
        else:
            print(f"\n❌ Найдено {non_russian_count} не российских акций")
        
        print("\n✅ Тест завершен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_russian_filter_fixed()
