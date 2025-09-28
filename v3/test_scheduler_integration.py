"""Тест интеграции планировщика с основным приложением."""

import asyncio
import logging
from datetime import datetime, timedelta

from core.scheduler import TaskScheduler, TradingCalendar, Market, RealSchedulerIntegration

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_basic_scheduler():
    """Тест базового планировщика."""
    print("=== Тест базового планировщика ===")
    
    # Создаем планировщик
    trading_calendar = TradingCalendar()
    scheduler = TaskScheduler(trading_calendar)
    
    # Добавляем тестовые задачи
    async def test_task_1():
        print(f"Тестовая задача 1 выполнена в {datetime.now()}")
        await asyncio.sleep(1)
        
    async def test_task_2():
        print(f"Тестовая задача 2 выполнена в {datetime.now()}")
        await asyncio.sleep(2)
        
    scheduler.add_task(
        name="test_task_1",
        func=test_task_1,
        interval=timedelta(seconds=5),
        priority=10
    )
    
    scheduler.add_task(
        name="test_task_2", 
        func=test_task_2,
        interval=timedelta(seconds=8),
        priority=5
    )
    
    # Запускаем планировщик
    print("Запускаем планировщик...")
    await scheduler.start()
    
    # Работаем 20 секунд
    print("Планировщик работает 20 секунд...")
    await asyncio.sleep(20)
    
    # Останавливаем
    print("Останавливаем планировщик...")
    await scheduler.stop()
    
    # Показываем статус
    status = scheduler.get_status()
    print(f"Финальный статус: {status}")


async def test_real_integration():
    """Тест реальной интеграции."""
    print("\n=== Тест реальной интеграции ===")
    
    try:
        # Создаем интеграцию
        integration = RealSchedulerIntegration()
        
        # Получаем статус
        status = integration.get_status()
        print(f"Статус планировщика: {status}")
        
        # Запускаем планировщик
        print("Запускаем планировщик...")
        integration.start_scheduler()
        
        # Работаем 10 секунд
        print("Планировщик работает 10 секунд...")
        await asyncio.sleep(10)
        
        # Останавливаем
        print("Останавливаем планировщик...")
        integration.stop_scheduler()
        
        # Финальный статус
        final_status = integration.get_status()
        print(f"Финальный статус: {final_status}")
        
    except Exception as e:
        print(f"Ошибка в тесте интеграции: {e}")
        logger.exception("Ошибка в тесте интеграции")


def test_trading_calendar():
    """Тест торгового календаря."""
    print("\n=== Тест торгового календаря ===")
    
    calendar = TradingCalendar()
    
    # Проверяем торговые дни
    is_trading = calendar.is_trading_day()
    print(f"Сегодня торговый день: {is_trading}")
    
    # Проверяем открытие рынков
    is_moex_open = calendar.is_market_open(Market.MOEX)
    print(f"MOEX открыт: {is_moex_open}")
    
    is_nyse_open = calendar.is_market_open(Market.NYSE)
    print(f"NYSE открыт: {is_nyse_open}")
    
    # Следующий торговый день
    next_trading = calendar.get_next_trading_day()
    print(f"Следующий торговый день: {next_trading}")
    
    # Оптимальное время для задач
    optimal_time = calendar.get_optimal_run_time("update_market_data", Market.MOEX)
    print(f"Оптимальное время для обновления данных: {optimal_time}")


async def main():
    """Главная функция тестирования."""
    print("Запуск тестов планировщика...")
    
    # Тест торгового календаря
    test_trading_calendar()
    
    # Тест базового планировщика
    await test_basic_scheduler()
    
    # Тест реальной интеграции
    await test_real_integration()
    
    print("\nВсе тесты завершены!")


if __name__ == "__main__":
    asyncio.run(main())
