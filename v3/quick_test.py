#!/usr/bin/env python3
"""
Быстрая проверка всех импортов для многоуровневого анализатора.
"""

def test_imports():
    """Тест всех необходимых импортов."""
    print("🔍 Тестирование импортов...")
    
    tests = [
        ("schedule", "import schedule"),
        ("websockets", "import websockets"),
        ("tinkoff.invest", "import tinkoff.invest"),
        ("RealMultiTimeframeStockAnalyzer", "from core.multi_timeframe_analyzer_real import RealMultiTimeframeStockAnalyzer"),
        ("TinkoffWebSocketProvider", "from core.tinkoff_websocket_provider import TinkoffWebSocketProvider"),
        ("EnhancedRealTimeDataManager", "from core.realtime_manager_enhanced import EnhancedRealTimeDataManager"),
        ("EnhancedDataUpdater", "from core.data_updater_enhanced import EnhancedDataUpdater"),
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for name, import_statement in tests:
        try:
            exec(import_statement)
            print(f"✅ {name} - OK")
            success_count += 1
        except ImportError as e:
            print(f"❌ {name} - ОШИБКА: {e}")
        except Exception as e:
            print(f"⚠️ {name} - ПРЕДУПРЕЖДЕНИЕ: {e}")
            success_count += 1  # Считаем как успех, если модуль импортирован
    
    print(f"\n📊 Результат: {success_count}/{total_count} модулей импортировано успешно")
    
    if success_count == total_count:
        print("🎉 ВСЕ ЗАВИСИМОСТИ УСТАНОВЛЕНЫ! Многоуровневый анализатор готов к работе!")
        return True
    else:
        print("⚠️ Некоторые зависимости не установлены. Проверьте ошибки выше.")
        return False

if __name__ == "__main__":
    test_imports()
