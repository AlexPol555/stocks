#!/usr/bin/env python3
"""
Simple Debug.
Простая отладка фильтрации.
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def simple_debug():
    """Простая отладка."""
    print("Debug started")
    
    try:
        from core.shares_integration import SharesIntegrator
        print("SharesIntegrator imported")
        
        # Получаем API ключ
        api_key = None
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and hasattr(st.secrets, 'TINKOFF_API_KEY'):
                api_key = st.secrets.TINKOFF_API_KEY
                print("API key loaded")
            else:
                print("No API key in secrets")
        except ImportError:
            print("Streamlit not available")
        
        if not api_key:
            print("No API key found")
            return
        
        integrator = SharesIntegrator()
        print("Integrator created")
        
        # Тестируем загрузку
        print("Loading all shares...")
        all_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=False)
        print(f"All shares loaded: {len(all_shares)}")
        
        if all_shares:
            print("First 5 shares:")
            for i, share in enumerate(all_shares[:5]):
                print(f"  {i+1}. {share['ticker']} - {share['name']} ({share.get('currency', 'Unknown')})")
        
        print("Loading Russian shares...")
        russian_shares = integrator.load_shares_from_tinkoff_api(api_key, russian_only=True)
        print(f"Russian shares loaded: {len(russian_shares)}")
        
        if russian_shares:
            print("First 5 Russian shares:")
            for i, share in enumerate(russian_shares[:5]):
                print(f"  {i+1}. {share['ticker']} - {share['name']} ({share.get('currency', 'Unknown')})")
        
        print("Debug completed")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_debug()
