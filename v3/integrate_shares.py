#!/usr/bin/env python3
"""
Shares Integration Script.
Скрипт для интеграции акций (shares) в существующую систему.
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from core.shares_integration import integrate_shares_system

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Основная функция интеграции акций."""
    print("🚀 Запуск интеграции акций (shares) в систему...")
    
    # Получаем API ключ
    api_key = os.getenv('TINKOFF_API_KEY')
    if not api_key:
        print("❌ Ошибка: TINKOFF_API_KEY не установлен")
        print("💡 Установите переменную окружения:")
        print("   export TINKOFF_API_KEY='your_api_key_here'")
        print("   или добавьте в .streamlit/secrets.toml")
        return 1
    
    try:
        # Интегрируем акции
        integrator = integrate_shares_system(api_key)
        
        # Получаем статистику
        shares_count = len(integrator.get_shares_only())
        futures_count = len(integrator.get_futures_only())
        total_count = len(integrator.get_all_assets())
        
        print("\n✅ Интеграция акций завершена успешно!")
        print(f"📊 Статистика:")
        print(f"   - Акции (shares): {shares_count}")
        print(f"   - Фьючерсы (futures): {futures_count}")
        print(f"   - Всего активов: {total_count}")
        
        print("\n🎯 Что дальше:")
        print("   1. Перезапустите Streamlit")
        print("   2. Откройте страницу '⏰ Multi-Timeframe'")
        print("   3. Нажмите 'Интегрировать акции' для загрузки")
        print("   4. Начните обновление данных для всех активов")
        
        return 0
        
    except Exception as e:
        logger.error(f"Ошибка интеграции акций: {e}")
        print(f"❌ Ошибка интеграции акций: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
