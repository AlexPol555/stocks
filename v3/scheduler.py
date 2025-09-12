
"""
scheduler.py — минималистичный планировщик для Streamlit/Standalone

Функции:
- start_daily_midnight(job_fn, tz="Europe/Stockholm") -> (thread, stop_event, get_state)
- stop_scheduler(stop_event)
- seconds_until_next_midnight(tz="Europe/Stockholm") -> int
- next_midnight_datetime(tz="Europe/Stockholm") -> datetime

Работает в отдельном потоке: ждёт до ближайшей полуночи (в указанном часовом поясе),
вызывает job_fn(), затем планирует следующую полночь и так по кругу.

Без внешних зависимостей (без APScheduler), устойчив к перезапускам Streamlit скрипта
(при условии, что вы создаёте планировщик через st.cache_resource).
"""
from __future__ import annotations
import threading
import time
from datetime import datetime, timedelta, time as dtime
from typing import Callable, Optional

try:
    # Python 3.9+: стандартная зона времени
    from zoneinfo import ZoneInfo
    def _get_tz(tz_name: str):
        return ZoneInfo(tz_name)
except Exception:
    # Fallback: без zoneinfo — используем наивное локальное время
    ZoneInfo = None
    def _get_tz(tz_name: str):
        return None  # будет наивное

def _now(tz_name: str):
    tz = _get_tz(tz_name)
    return datetime.now(tz)

def next_midnight_datetime(tz: str = "Europe/Stockholm") -> datetime:
    now = _now(tz)
    tomorrow = now.date() + timedelta(days=1)
    return datetime.combine(tomorrow, dtime(0, 0, 0), tzinfo=now.tzinfo)

def seconds_until_next_midnight(tz: str = "Europe/Stockholm") -> int:
    nm = next_midnight_datetime(tz)
    now = _now(tz)
    delta = (nm - now).total_seconds()
    return max(0, int(delta))

def start_daily_midnight(job_fn: Callable[[], None],
                         tz: str = "Europe/Stockholm",
                         on_error: Optional[Callable[[Exception], None]] = None):
    """
    Запускает отдельный поток, который будет вызывать job_fn() каждый день в 00:00 указанного tz.
    Возвращает (thread, stop_event, get_state), где:
      - thread: запущенный поток (daemon=True)
      - stop_event: threading.Event для мягкой остановки
      - get_state: функция без аргументов, возвращающая dict со статусом:
          {"last_run": datetime|None, "next_run": datetime, "running": bool}
    """
    stop_event = threading.Event()
    state = {"last_run": None, "next_run": next_midnight_datetime(tz), "running": True}

    def _loop():
        while not stop_event.is_set():
            try:
                # Спим до следующей полуночи
                secs = seconds_until_next_midnight(tz)
                # Спать кусками по 10 секунд, чтобы быстрее реагировать на stop_event
                chunk = 10
                slept = 0
                while slept < secs and not stop_event.is_set():
                    time.sleep(min(chunk, secs - slept))
                    slept += min(chunk, secs - slept)
                if stop_event.is_set():
                    break

                # Запускаем job
                try:
                    job_fn()
                except Exception as e:
                    if on_error:
                        on_error(e)
                finally:
                    state["last_run"] = _now(tz)

                # Планируем следующую полуночь
                state["next_run"] = next_midnight_datetime(tz)

            except Exception as e:
                # Непредвиденная ошибка цикла — подождём минуту и попробуем снова
                if on_error:
                    on_error(e)
                time.sleep(60)

        state["running"] = False

    th = threading.Thread(target=_loop, daemon=True, name="daily-midnight-scheduler")
    th.start()

    def get_state():
        return dict(state)

    return th, stop_event, get_state

def stop_scheduler(stop_event):
    """Запрашивает мягкую остановку планировщика."""
    if stop_event and hasattr(stop_event, "set"):
        stop_event.set()
