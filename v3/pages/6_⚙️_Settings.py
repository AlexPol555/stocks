from core.bootstrap import setup_environment

setup_environment()

import os

import streamlit as st

from core import demo_trading, ui, utils

ui.page_header("Настройки", "Управление страницами, интеграциями и демо-счётом.", icon="⚙️")

ui.section_title("Доступность страниц")
all_pages = [
    ("Dashboard", "📊 Дашборд"),
    ("Analyzer", "🧮 Аналитика"),
    ("Data_Load", "📥 Загрузка"),
    ("Auto_Update", "🔁 Автообновление"),
    ("Orders", "🛒 Ордеры"),
    ("Demo_Stats", "📈 Статистика демо"),
    ("Lightweight_Chart", "📈 Лёгкие графики"),
    ("Debug", "🧰 Отладка"),
]

default_visibility = {key: True for key, _ in all_pages}
default_visibility["Debug"] = False

visibility = st.session_state.get("page_visibility", default_visibility.copy())
cols = st.columns(3)
for idx, (key, label) in enumerate(all_pages):
    with cols[idx % 3]:
        visibility[key] = st.checkbox(label, value=visibility.get(key, default_visibility[key]))
st.session_state["page_visibility"] = visibility
st.caption("Изменения применяются мгновенно к сайдбару приложения.")

ui.section_title("Интеграции")
try:
    secrets = utils._secrets_dict()
    if secrets:
        st.success("Файл secrets.toml найден. Ключи:" + ", ".join(secrets.keys()))
    else:
        st.info("Файл secrets.toml отсутствует — используйте переменные окружения.")
except Exception as exc:
    st.error(f"Не удалось прочитать secrets.toml: {exc}")

env_api = os.getenv("TINKOFF_API_KEY")
env_db = os.getenv("DB_PATH")
info_cols = st.columns(2)
info_cols[0].metric("TINKOFF_API_KEY", "настроен" if env_api else "нет")
info_cols[1].metric("DB_PATH", env_db or "не задан")

ui.section_title("База данных")
db_path = utils.read_db_path()
st.write("Путь к базе данных:", db_path)
try:
    db_size = os.path.getsize(db_path)
    st.write("Размер файла:", f"{db_size / 1024:.1f} КБ")
except Exception:
    st.info("Файл базы данных не найден. Он будет создан при первой записи.")

ui.section_title("Демо-счёт")
conn_demo = None
try:
    conn_demo = utils.open_database_connection()
    snapshot = demo_trading.get_account_snapshot(conn_demo)
    account_info = demo_trading.get_account(conn_demo)
    currency = account_info.get("currency", "RUB")

    def fmt(value: float) -> str:
        return format(float(value), ',.2f').replace(',', ' ')

    top_cols = st.columns(4)
    top_cols[0].metric("Баланс", f"{fmt(snapshot['balance'])} {currency}")
    top_cols[1].metric("Инвестировано", f"{fmt(snapshot['invested_value'])} {currency}")
    top_cols[2].metric("Рыночная стоимость", f"{fmt(snapshot['market_value'])} {currency}")
    top_cols[3].metric("Equity", f"{fmt(snapshot['equity'])} {currency}")

    pl_cols = st.columns(3)
    pl_cols[0].metric("Нереализованный P/L", f"{fmt(snapshot['unrealized_pl'])} {currency}")
    pl_cols[1].metric("Реализованный P/L", f"{fmt(snapshot['realized_pl'])} {currency}")
    pl_cols[2].metric("Итоговый P/L", f"{fmt(snapshot['total_pl'])} {currency}")

    st.caption("Демо-счёт хранится в той же базе, что и исторические данные.")

    with st.form("demo_adjust_balance"):
        left_col, right_col = st.columns(2)
        with left_col:
            delta = st.number_input("Изменение баланса", min_value=0.0, step=100.0, format="%.2f")
        with right_col:
            direction = st.selectbox("Действие", ("Пополнить", "Списать"))
        if st.form_submit_button("Применить"):
            if delta <= 0:
                st.warning("Введите значение больше нуля.")
            else:
                sign = 1 if direction == "Пополнить" else -1
                try:
                    new_balance = demo_trading.adjust_balance(conn_demo, sign * delta)
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"Не удалось обновить баланс: {exc}")
                else:
                    st.success(f"Новый баланс: {fmt(new_balance)} {currency}")
                    st.experimental_rerun()

    with st.form("demo_reset"):
        new_balance = st.number_input(
            "Начальный баланс",
            min_value=0.0,
            value=float(snapshot['initial_balance']),
            step=100.0,
            format="%.2f",
        )
        confirm = st.checkbox("Я понимаю, что текущая история сделок будет очищена")
        if st.form_submit_button("Сбросить демо-счёт"):
            if not confirm:
                st.warning("Поставьте подтверждение, если готовы очистить историю сделок.")
            else:
                try:
                    demo_trading.reset_account(conn_demo, new_balance)
                except Exception as exc:
                    st.error(f"Не удалось сбросить демо-счёт: {exc}")
                else:
                    st.success("Демо-счёт сброшен.")
                    st.experimental_rerun()
except Exception as exc:
    st.warning(f"Не удалось получить данные демо-счёта: {exc}")
finally:
    if conn_demo is not None:
        conn_demo.close()

ui.section_title("Диагностика БД")
try:
    conn = utils.open_database_connection()
    utils.db_health_check(conn)
    conn.close()
except Exception as exc:
    st.warning(f"Проверка БД пропущена: {exc}")
