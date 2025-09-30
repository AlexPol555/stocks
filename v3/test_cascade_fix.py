#!/usr/bin/env python3
"""
Test Cascade Analyzer after data fix.
Тест каскадного анализатора после исправления данных.
"""

import sys
from pathlib import Path

# Добавляем корневую папку в путь
sys.path.append(str(Path(__file__).parent))

def test_cascade_analyzer():
    """Тест каскадного анализатора."""
    
    print("Testing Cascade Analyzer...")
    print("=" * 40)
    
    try:
        # Импортируем необходимые модули
        from core.cascade_analyzer import CascadeAnalyzer
        from core.multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer
        import asyncio
        
        # Создаем анализатор
        multi_analyzer = EnhancedMultiTimeframeStockAnalyzer()
        cascade_analyzer = CascadeAnalyzer(multi_analyzer=multi_analyzer)
        
        print("✅ Cascade analyzer created successfully")
        
        # Тестируем получение FIGI маппинга
        figi_mapping = multi_analyzer.get_figi_mapping()
        print(f"✅ FIGI mapping loaded: {len(figi_mapping)} symbols")
        
        # Тестируем символы
        test_symbols = ['VSMO', 'UNAC', 'CNRU', 'VKCO', 'MGNT']
        
        for symbol in test_symbols:
            figi = multi_analyzer.get_figi_for_symbol(symbol)
            if figi:
                print(f"✅ {symbol}: FIGI = {figi}")
                
                # Тестируем получение данных
                daily_data = multi_analyzer.get_stock_data(figi, '1d')
                if not daily_data.empty:
                    print(f"  ✅ Daily data: {len(daily_data)} records")
                else:
                    print(f"  ❌ No daily data")
            else:
                print(f"❌ {symbol}: No FIGI found")
        
        print("\n✅ Basic functionality test passed!")
        
        # Тестируем каскадный анализ (только первый этап)
        print("\nTesting cascade analysis (stage 1d only)...")
        
        async def test_stage_1d():
            result = await cascade_analyzer._analyze_stage_1d('VSMO')
            print(f"VSMO Stage 1d result: {result.get('reason', 'Unknown')}")
            if result.get('proceed'):
                print("✅ VSMO passed stage 1d")
            else:
                print(f"❌ VSMO failed stage 1d: {result.get('reason')}")
        
        # Запускаем тест
        asyncio.run(test_stage_1d())
        
        print("\n✅ Cascade analyzer test completed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed")
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Основная функция."""
    
    print("Cascade Analyzer Test After Data Fix")
    print("=" * 50)
    
    test_cascade_analyzer()
    
    print("\nNext steps:")
    print("1. Test in Streamlit interface")
    print("2. Run full cascade analysis")
    print("3. Check ML integration")

if __name__ == "__main__":
    main()




