#!/usr/bin/env python3
"""
Simple Import Test.
Простой тест импорта.
"""

def test_import():
    """Тест импорта."""
    print("Тест импорта...")
    
    try:
        # Добавляем site-packages в путь
        import sys
        import site
        site_packages = site.getsitepackages()
        for path in site_packages:
            if path not in sys.path:
                sys.path.append(path)
        
        print("Импорт tinkoff_invest...")
        import tinkoff_invest
        print(f"tinkoff_invest импортирован: {tinkoff_invest.__file__}")
        
        print("Импорт Client...")
        from tinkoff_invest import Client
        print("Client импортирован успешно")
        
        print("Импорт схем...")
        from tinkoff_invest.schemas import InstrumentStatus, ShareType
        print("Схемы импортированы успешно")
        
        print("Все импорты работают!")
        
    except Exception as e:
        print(f"Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_import()
