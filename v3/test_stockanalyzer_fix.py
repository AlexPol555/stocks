"""
Тест исправления ошибки StockAnalyzer.
"""

import os
import sys
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_stockanalyzer_fix():
    """Тест исправления ошибки StockAnalyzer."""
    print("Тест исправления ошибки StockAnalyzer...")
    
    try:
        # Импортируем исправленный анализатор
        from core.multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
        
        # Получаем API ключ
        api_key = None
        try:
            import streamlit as st
            api_key = st.secrets.get("TINKOFF_API_KEY")
        except:
            api_key = os.getenv("TINKOFF_API_KEY")
        
        if not api_key:
            print("ERROR: API ключ не найден")
            return
        
        print(f"OK: API ключ найден: {api_key[:10]}...")
        
        # Создаем анализатор
        analyzer = EnhancedMultiTimeframeStockAnalyzer(api_key=api_key)
        
        # Тестируем получение информации о провайдерах
        print("\n--- Тест провайдеров ---")
        provider_info = analyzer.get_provider_info()
        
        for timeframe, providers in provider_info.items():
            print(f"\n{timeframe}:")
            for provider in providers:
                print(f"  - {provider['name']}: {'OK' if provider['available'] else 'ERROR'}")
        
        # Тестируем получение данных для разных таймфреймов
        print("\n--- Тест получения данных ---")
        test_figi = "BBG004730N88"  # SBER
        
        timeframes = ['1d', '1h', '1m', '5m', '15m']
        
        for timeframe in timeframes:
            print(f"\nТестируем {timeframe}:")
            try:
                data = analyzer.get_stock_data(test_figi, timeframe)
                
                if not data.empty:
                    print(f"  OK: получено {len(data)} записей")
                else:
                    print(f"  WARNING: данные не получены")
                    
            except Exception as e:
                error_msg = str(e)
                if "is_available" in error_msg:
                    print(f"  ERROR: {timeframe}: Ошибка is_available - {e}")
                else:
                    print(f"  ERROR: {timeframe}: {e}")
        
        print("\n--- Тест завершен ---")
        
    except ImportError as e:
        print(f"ERROR: Ошибка импорта: {e}")
    except Exception as e:
        print(f"ERROR: Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_stockanalyzer_fix()
