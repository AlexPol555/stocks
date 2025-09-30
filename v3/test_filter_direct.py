#!/usr/bin/env python3
"""
Test Filter Direct.
Прямой тест фильтрации.
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_filter_direct():
    """Прямой тест фильтрации."""
    print("Starting test...")
    
    try:
        # Импортируем необходимые модули
        from core.shares_integration import SharesIntegrator
        print("Imported SharesIntegrator")
        
        # Создаем интегратор
        integrator = SharesIntegrator()
        print("Created integrator")
        
        # Получаем API ключ
        api_key = None
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and hasattr(st.secrets, 'TINKOFF_API_KEY'):
                api_key = st.secrets.TINKOFF_API_KEY
                print("Got API key from Streamlit")
            else:
                print("No API key in Streamlit secrets")
        except ImportError:
            print("Streamlit not available")
        
        if not api_key:
            print("No API key found")
            return
        
        # Тестируем загрузку
        print("Testing all shares...")
        all_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=False)
        print(f"All shares: {len(all_shares)}")
        
        print("Testing Russian shares...")
        russian_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=True)
        print(f"Russian shares: {len(russian_shares)}")
        
        # Показываем примеры
        if all_shares:
            print("First 5 all shares:")
            for i, share in enumerate(all_shares[:5]):
                print(f"  {i+1}. {share['ticker']} - {share['name']} ({share.get('currency', 'Unknown')})")
        
        if russian_shares:
            print("First 5 Russian shares:")
            for i, share in enumerate(russian_shares[:5]):
                print(f"  {i+1}. {share['ticker']} - {share['name']} ({share.get('currency', 'Unknown')})")
        
        print("Test completed")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_filter_direct()
