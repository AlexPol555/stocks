#!/usr/bin/env python3
"""
Debug script for Cascade Analyzer data issues.
Скрипт диагностики проблем с данными в каскадном анализаторе.
"""

import logging
import sys
from pathlib import Path

# Добавляем корневую папку в путь
sys.path.append(str(Path(__file__).parent))

from core.database import get_connection
from core.multi_timeframe_analyzer_enhanced import EnhancedMultiTimeframeStockAnalyzer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_symbol_data(symbols):
    """Диагностика данных для символов."""
    
    print(f"🔍 Диагностика данных для символов: {symbols}")
    print("=" * 60)
    
    # Создаем анализатор
    analyzer = EnhancedMultiTimeframeStockAnalyzer()
    
    # Получаем маппинг FIGI
    figi_mapping = analyzer.get_figi_mapping()
    print(f"📊 Загружено {len(figi_mapping)} FIGI маппингов:")
    for symbol, figi in list(figi_mapping.items())[:5]:  # Показываем первые 5
        print(f"  {symbol} -> {figi}")
    if len(figi_mapping) > 5:
        print(f"  ... и еще {len(figi_mapping) - 5} символов")
    print()
    
    # Проверяем каждый символ
    for symbol in symbols:
        print(f"🔍 Проверка символа: {symbol}")
        
        # Получаем FIGI
        figi = analyzer.get_figi_for_symbol(symbol)
        if not figi:
            print(f"  ❌ FIGI не найден для {symbol}")
            continue
        
        print(f"  📋 FIGI: {figi}")
        
        # Проверяем данные для разных таймфреймов
        timeframes = ['1d', '1h', '1m', '1s']
        
        for tf in timeframes:
            try:
                data = analyzer.get_stock_data(figi, tf)
                if data.empty:
                    print(f"    ❌ {tf}: Нет данных")
                else:
                    print(f"    ✅ {tf}: {len(data)} записей")
                    if len(data) > 0:
                        latest = data.iloc[-1]
                        print(f"      Последняя запись: {latest['time']} - {latest['close']}")
            except Exception as e:
                print(f"    ❌ {tf}: Ошибка - {e}")
        
        print()
    
    # Проверяем базу данных
    print("🗄️ Проверка базы данных:")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Проверяем таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  📋 Найдено таблиц: {len(tables)}")
        
        # Проверяем companies
        if 'companies' in tables:
            cursor.execute("SELECT COUNT(*) FROM companies")
            company_count = cursor.fetchone()[0]
            print(f"  🏢 Компаний в БД: {company_count}")
            
            # Проверяем конкретные символы
            for symbol in symbols:
                cursor.execute("SELECT id, ticker, figi FROM companies WHERE ticker = ?", (symbol,))
                company = cursor.fetchone()
                if company:
                    print(f"    ✅ {symbol}: ID={company[0]}, FIGI={company[2]}")
                else:
                    print(f"    ❌ {symbol}: Не найден в БД")
        
        # Проверяем daily_data
        if 'daily_data' in tables:
            cursor.execute("SELECT COUNT(*) FROM daily_data")
            daily_count = cursor.fetchone()[0]
            print(f"  📈 Записей daily_data: {daily_count}")
            
            # Проверяем данные для конкретных символов
            for symbol in symbols:
                cursor.execute("""
                    SELECT COUNT(*) FROM daily_data dd 
                    JOIN companies c ON dd.company_id = c.id 
                    WHERE c.ticker = ?
                """, (symbol,))
                count = cursor.fetchone()[0]
                print(f"    📊 {symbol}: {count} записей daily_data")
        
        conn.close()
        
    except Exception as e:
        print(f"  ❌ Ошибка БД: {e}")
    
    print("\n" + "=" * 60)

def main():
    """Основная функция."""
    
    # Символы для диагностики
    symbols = ['VSMO', 'UNAC', 'CNRU', 'VKCO', 'MGNT']
    
    print("🎯 Диагностика каскадного анализатора")
    print("=" * 60)
    
    # Диагностика данных
    debug_symbol_data(symbols)
    
    # Рекомендации
    print("💡 Рекомендации:")
    print("1. Убедитесь, что символы добавлены в базу данных")
    print("2. Проверьте наличие API ключа Tinkoff")
    print("3. Запустите обновление данных: auto_update_all_tickers()")
    print("4. Проверьте подключение к интернету")
    
    print("\n🔧 Команды для исправления:")
    print("1. Добавить символы в БД:")
    print("   python populate_database.py")
    print("2. Обновить данные:")
    print("   python auto_update.py")
    print("3. Проверить API ключ:")
    print("   python check_api.py")

if __name__ == "__main__":
    main()




