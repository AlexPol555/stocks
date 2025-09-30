"""
Тест для проверки исправления ограничений периодов Tinkoff API.
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_period_limits():
    """Тест ограничений периодов для разных таймфреймов."""
    print("Тест ограничений периодов Tinkoff API...")
    
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
        
        # Тестируем разные таймфреймы
        test_timeframes = ['1d', '1h', '1m', '5m', '15m']
        test_figi = "BBG004730N88"  # SBER
        
        print(f"\nТестируем таймфреймы для SBER (FIGI: {test_figi}):")
        
        for timeframe in test_timeframes:
            print(f"\n--- Тестируем {timeframe} ---")
            try:
                data = analyzer.get_stock_data(test_figi, timeframe)
                
                if not data.empty:
                    print(f"OK: {timeframe}: получено {len(data)} записей")
                    print(f"   Период: {data['time'].min()} - {data['time'].max()}")
                else:
                    print(f"WARNING: {timeframe}: данные не получены")
                    
            except Exception as e:
                error_msg = str(e)
                if "30014" in error_msg:
                    print(f"ERROR: {timeframe}: Ошибка 30014 - превышен период запроса")
                else:
                    print(f"ERROR: {timeframe}: Ошибка - {e}")
        
        print("\n--- Тест завершен ---")
        
    except ImportError as e:
        print(f"ERROR: Ошибка импорта: {e}")
    except Exception as e:
        print(f"ERROR: Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_period_limits()
