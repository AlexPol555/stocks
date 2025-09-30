#!/usr/bin/env python3
"""
Debug Russian Filter.
Отладка фильтрации российских акций.
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_russian_filter():
    """Отладка фильтрации российских акций."""
    print("🔍 Отладка фильтрации российских акций...")
    print("=" * 60)
    
    try:
        from core.shares_integration import SharesIntegrator
        
        # Получаем API ключ
        api_key = None
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and hasattr(st.secrets, 'TINKOFF_API_KEY'):
                api_key = st.secrets.TINKOFF_API_KEY
                print("✅ API ключ загружен из Streamlit secrets")
            else:
                print("❌ API ключ не найден в Streamlit secrets")
        except ImportError:
            print("❌ Streamlit не доступен")
        
        if not api_key:
            print("❌ API ключ не найден. Проверьте .streamlit/secrets.toml")
            return
        
        integrator = SharesIntegrator()
        
        print("\n📊 Тестирование загрузки всех акций (russian_only=False)...")
        print("-" * 50)
        all_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=False)
        print(f"Всего акций загружено: {len(all_shares)}")
        
        if all_shares:
            print("\n🌍 Примеры всех акций (первые 10):")
            for i, share in enumerate(all_shares[:10]):
                currency = share.get('currency', 'Unknown')
                isin = share.get('isin', 'Unknown')
                print(f"  {i+1:2d}. {share['ticker']:6s} - {share['name'][:30]:30s} ({currency}) [{isin}]")
        
        print(f"\n📈 Статистика валют всех акций:")
        currencies_all = {}
        for share in all_shares:
            currency = share.get('currency', 'Unknown')
            currencies_all[currency] = currencies_all.get(currency, 0) + 1
        
        for currency, count in sorted(currencies_all.items()):
            print(f"  {currency}: {count} акций")
        
        print(f"\n📋 Статистика ISIN префиксов всех акций:")
        isin_prefixes_all = {}
        for share in all_shares:
            isin = share.get('isin', '')
            if isin:
                prefix = isin[:2] if len(isin) >= 2 else 'Unknown'
                isin_prefixes_all[prefix] = isin_prefixes_all.get(prefix, 0) + 1
        
        for prefix, count in sorted(isin_prefixes_all.items()):
            print(f"  {prefix}: {count} акций")
        
        print("\n🇷🇺 Тестирование загрузки российских акций (russian_only=True)...")
        print("-" * 50)
        russian_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=True)
        print(f"Российских акций загружено: {len(russian_shares)}")
        
        if russian_shares:
            print("\n🏢 Примеры российских акций (первые 10):")
            for i, share in enumerate(russian_shares[:10]):
                currency = share.get('currency', 'Unknown')
                isin = share.get('isin', 'Unknown')
                print(f"  {i+1:2d}. {share['ticker']:6s} - {share['name'][:30]:30s} ({currency}) [{isin}]")
        
        print(f"\n💱 Статистика валют российских акций:")
        currencies_ru = {}
        for share in russian_shares:
            currency = share.get('currency', 'Unknown')
            currencies_ru[currency] = currencies_ru.get(currency, 0) + 1
        
        for currency, count in sorted(currencies_ru.items()):
            print(f"  {currency}: {count} акций")
        
        print(f"\n📋 Статистика ISIN префиксов российских акций:")
        isin_prefixes_ru = {}
        for share in russian_shares:
            isin = share.get('isin', '')
            if isin:
                prefix = isin[:2] if len(isin) >= 2 else 'Unknown'
                isin_prefixes_ru[prefix] = isin_prefixes_ru.get(prefix, 0) + 1
        
        for prefix, count in sorted(isin_prefixes_ru.items()):
            print(f"  {prefix}: {count} акций")
        
        # Проверяем, что все российские акции действительно российские
        print(f"\n🔍 Проверка российских акций:")
        non_russian_count = 0
        for share in russian_shares:
            currency = share.get('currency', '')
            isin = share.get('isin', '')
            if currency != 'RUB' and not isin.startswith('RU'):
                non_russian_count += 1
                print(f"  ⚠️ Не российская акция: {share['ticker']} - {share['name']} ({currency}) [{isin}]")
        
        if non_russian_count == 0:
            print("  ✅ Все загруженные акции являются российскими!")
        else:
            print(f"  ❌ Найдено {non_russian_count} не российских акций")
        
        # Сравнение результатов
        print(f"\n📊 Сравнение результатов:")
        print(f"  Всего акций: {len(all_shares)}")
        print(f"  Российских акций: {len(russian_shares)}")
        if len(all_shares) > 0:
            print(f"  Экономия: {len(all_shares) - len(russian_shares)} акций ({((len(all_shares) - len(russian_shares)) / len(all_shares) * 100):.1f}%)")
        
        print("\n✅ Отладка завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка отладки: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_russian_filter()
