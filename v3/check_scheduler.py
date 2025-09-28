"""Проверка работы планировщика."""

print("Проверка планировщика...")

try:
    # Проверяем импорты
    from core.scheduler import TaskScheduler, TaskStatus, TradingCalendar, Market
    print("✅ Импорты работают")
    
    # Проверяем создание объектов
    calendar = TradingCalendar()
    scheduler = TaskScheduler(calendar)
    print("✅ Объекты создаются")
    
    # Проверяем статусы
    print(f"✅ TaskStatus.PENDING: {TaskStatus.PENDING}")
    print(f"✅ TaskStatus.RUNNING: {TaskStatus.RUNNING}")
    
    # Проверяем рынки
    print(f"✅ Market.MOEX: {Market.MOEX}")
    print(f"✅ Market.NYSE: {Market.NYSE}")
    
    print("\n🎉 Планировщик готов к работе!")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
