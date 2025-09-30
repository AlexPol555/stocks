#!/usr/bin/env python3
"""
Debug to File.
Отладка с записью в файл.
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_to_file():
    """Отладка с записью в файл."""
    with open("debug_output.txt", "w", encoding="utf-8") as f:
        f.write("🔍 Отладка фильтрации российских акций...\n")
        f.write("=" * 60 + "\n")
        
        try:
            from core.shares_integration import SharesIntegrator
            f.write("✅ SharesIntegrator импортирован\n")
            
            # Получаем API ключ
            api_key = None
            try:
                import streamlit as st
                if hasattr(st, 'secrets') and hasattr(st.secrets, 'TINKOFF_API_KEY'):
                    api_key = st.secrets.TINKOFF_API_KEY
                    f.write("✅ API ключ загружен из Streamlit secrets\n")
                else:
                    f.write("❌ API ключ не найден в Streamlit secrets\n")
            except ImportError:
                f.write("❌ Streamlit не доступен\n")
            
            if not api_key:
                f.write("❌ API ключ не найден. Проверьте .streamlit/secrets.toml\n")
                return
            
            integrator = SharesIntegrator()
            f.write("✅ Integrator создан\n")
            
            # Тестируем загрузку всех акций
            f.write("\n📊 Загрузка всех акций (russian_only=False)...\n")
            f.write("-" * 50 + "\n")
            all_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=False)
            f.write(f"Всего акций загружено: {len(all_shares)}\n")
            
            if all_shares:
                f.write("\n🌍 Примеры всех акций (первые 10):\n")
                for i, share in enumerate(all_shares[:10]):
                    currency = share.get('currency', 'Unknown')
                    isin = share.get('isin', 'Unknown')
                    f.write(f"  {i+1:2d}. {share['ticker']:6s} - {share['name'][:30]:30s} ({currency}) [{isin}]\n")
            
            # Статистика валют
            f.write(f"\n📈 Статистика валют всех акций:\n")
            currencies_all = {}
            for share in all_shares:
                currency = share.get('currency', 'Unknown')
                currencies_all[currency] = currencies_all.get(currency, 0) + 1
            
            for currency, count in sorted(currencies_all.items()):
                f.write(f"  {currency}: {count} акций\n")
            
            # Тестируем загрузку российских акций
            f.write("\n🇷🇺 Загрузка российских акций (russian_only=True)...\n")
            f.write("-" * 50 + "\n")
            russian_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=True)
            f.write(f"Российских акций загружено: {len(russian_shares)}\n")
            
            if russian_shares:
                f.write("\n🏢 Примеры российских акций (первые 10):\n")
                for i, share in enumerate(russian_shares[:10]):
                    currency = share.get('currency', 'Unknown')
                    isin = share.get('isin', 'Unknown')
                    f.write(f"  {i+1:2d}. {share['ticker']:6s} - {share['name'][:30]:30s} ({currency}) [{isin}]\n")
            
            # Статистика валют российских акций
            f.write(f"\n💱 Статистика валют российских акций:\n")
            currencies_ru = {}
            for share in russian_shares:
                currency = share.get('currency', 'Unknown')
                currencies_ru[currency] = currencies_ru.get(currency, 0) + 1
            
            for currency, count in sorted(currencies_ru.items()):
                f.write(f"  {currency}: {count} акций\n")
            
            # Проверяем, что все российские акции действительно российские
            f.write(f"\n🔍 Проверка российских акций:\n")
            non_russian_count = 0
            for share in russian_shares:
                currency = share.get('currency', '')
                isin = share.get('isin', '')
                if currency != 'RUB' and not isin.startswith('RU'):
                    non_russian_count += 1
                    f.write(f"  ⚠️ Не российская акция: {share['ticker']} - {share['name']} ({currency}) [{isin}]\n")
            
            if non_russian_count == 0:
                f.write("  ✅ Все загруженные акции являются российскими!\n")
            else:
                f.write(f"  ❌ Найдено {non_russian_count} не российских акций\n")
            
            # Сравнение результатов
            f.write(f"\n📊 Сравнение результатов:\n")
            f.write(f"  Всего акций: {len(all_shares)}\n")
            f.write(f"  Российских акций: {len(russian_shares)}\n")
            if len(all_shares) > 0:
                f.write(f"  Экономия: {len(all_shares) - len(russian_shares)} акций ({((len(all_shares) - len(russian_shares)) / len(all_shares) * 100):.1f}%)\n")
            
            f.write("\n✅ Отладка завершена!\n")
            
        except Exception as e:
            f.write(f"❌ Ошибка отладки: {e}\n")
            import traceback
            f.write(traceback.format_exc())

if __name__ == "__main__":
    debug_to_file()
    print("Отладка завершена. Результаты в debug_output.txt")
