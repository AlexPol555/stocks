from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Dict, List

from core.bootstrap import setup_environment

setup_environment()

import time as pytime

import streamlit as st

from core import news, ui


@st.cache_data(ttl=60)
def _load_articles(limit: int) -> List[Dict[str, Any]]:
    return news.fetch_recent_articles(limit=limit)


@st.cache_data(ttl=120)
def _load_sources() -> List[Dict[str, Any]]:
    return news.fetch_sources()


@st.cache_data(ttl=120)
def _load_jobs(limit: int) -> List[Dict[str, Any]]:
    return news.fetch_jobs(limit=limit)


ui.page_header(
    "Новости",
    "Собираем RSS-ленты и выделяем упоминания тикеров за прошедший день.",
    icon="🗞️",
)

news.ensure_schema()

control_col, summary_col = st.columns((2, 1))
with control_col:
    if st.button("Запустить парсер сейчас", use_container_width=True):
        progress_placeholder = st.empty()
        progress_bar = st.progress(0)

        state = {
            "start": None,
            "total_sources": 0,
            "article_totals": {},
            "article_total": 0,
            "articles_done": 0,
            "matching_total": 0,
            "matching_done": 0,
            "current_source": "",
            "logs": [],
            "eta": None,
        }

        def _format_duration(value: float) -> str:
            seconds = int(max(value, 0))
            minutes, sec = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                return f"{hours:02d}:{minutes:02d}:{sec:02d}"
            return f"{minutes:02d}:{sec:02d}"

        def _log(message: str) -> None:
            state["logs"].append(message)
            state["logs"] = state["logs"][-6:]

        def _render_progress() -> None:
            processed = state["articles_done"] + state["matching_done"]
            total = max(state["article_total"] + state["matching_total"], 1)
            ratio = min(max(processed / total, 0.0), 1.0)
            progress_bar.progress(int(ratio * 100))

            lines: List[str] = []
            if state["current_source"]:
                lines.append(f"**Текущий источник:** {state['current_source']}")
            if state["article_total"]:
                lines.append(
                    f"Статей обработано: {state['articles_done']} / {state['article_total']}"
                )
            else:
                lines.append(f"Статей обработано: {state['articles_done']}")
            if state["matching_total"]:
                lines.append(
                    f"Сопоставление тикеров: {state['matching_done']} / {state['matching_total']}"
                )
            if state["eta"] is not None and processed < total:
                lines.append(f"Оценка завершения: ≈ {_format_duration(state['eta'])}")
            elif processed >= total and total > 0:
                lines.append("Оценка завершения: выполнено")

            if state["logs"]:
                lines.append("")
                lines.extend(f"• {entry}" for entry in state["logs"][-5:])

            progress_placeholder.markdown("\n".join(lines) or " ")

        def _progress_callback(stage: str, payload: Dict[str, object]) -> None:
            now = pytime.time()
            if state["start"] is None:
                state["start"] = now

            if stage == "start":
                state["total_sources"] = int(payload.get("total_sources", 0) or 0)
                _log(f"Запуск: источников {state['total_sources']}")
            elif stage == "source_start":
                state["current_source"] = str(payload.get("source") or "")
                idx = int(payload.get("index", 0) or 0)
                total = state["total_sources"] or 1
                _log(f"Источник {idx}/{total}: {state['current_source']} — получаем ленту")
            elif stage == "source_feed":
                idx = int(payload.get("index", 0) or 0)
                entries = int(payload.get("entries", 0) or 0)
                state["article_totals"][idx] = entries
                state["article_total"] = sum(state["article_totals"].values())
                _log(
                    f"{payload.get('source')}: записей в ленте {entries}"
                )
            elif stage == "article_progress":
                state["articles_done"] += 1
                article_total = int(payload.get("article_total", 0) or 0)
                article_index = int(payload.get("article_index", 0) or 0)
                title = str(payload.get("title") or "").strip()
                if article_total <= 5 or article_index == article_total or article_index % 5 == 0:
                    if title:
                        truncated = (title[:57] + "…") if len(title) > 60 else title
                        _log(
                            f"{payload.get('source')}: {article_index}/{article_total} — {truncated}"
                        )
                    else:
                        _log(
                            f"{payload.get('source')}: {article_index}/{article_total}"
                        )
            elif stage == "article_skipped":
                article_total = int(payload.get("article_total", 0) or 0)
                article_index = int(payload.get("article_index", 0) or 0)
                reason = str(payload.get("reason") or "пропуск")
                _log(
                    f"{payload.get('source')}: {article_index}/{article_total} — {reason}"
                )
            elif stage == "source_store":
                _log(
                    f"{payload.get('source')}: сохранено {payload.get('new_articles', 0)}, дублей {payload.get('duplicates', 0)}"
                )
            elif stage == "matching_start":
                state["matching_total"] = int(payload.get("total", 0) or 0)
                state["matching_done"] = 0
                if state["matching_total"]:
                    _log(
                        f"Сопоставляем тикеры: {state['matching_total']} статей"
                    )
            elif stage == "matching_progress":
                state["matching_done"] = int(payload.get("processed", 0) or 0)
            elif stage == "complete":
                _log(
                    "Итог: новых {new}, дублей {dup}, совпадений {match}".format(
                        new=payload.get("new_articles", 0),
                        dup=payload.get("duplicates", 0),
                        match=payload.get("ticker_matches", 0),
                    )
                )

            processed = state["articles_done"] + state["matching_done"]
            total = max(state["article_total"] + state["matching_total"], 1)
            if processed > 0 and total:
                elapsed = now - (state["start"] or now)
                estimated_total = elapsed / processed * total
                state["eta"] = max(estimated_total - elapsed, 0.0)
            else:
                state["eta"] = None

            _render_progress()

        with st.spinner("Собираем новости..."):
            result = news.run_fetch_job(progress_callback=_progress_callback)

        status = result.get("status")
        if status == "success":
            progress_bar.progress(100)
            stats = result.get("stats", {})
            new_articles = stats.get("new_articles", 0)
            duplicates = stats.get("duplicates", 0)
            tickers = stats.get("ticker_matches", 0)
            st.success(
                f"Готово: добавлено {new_articles} статей, пропущено дублей {duplicates}, совпадений тикеров {tickers}."
            )
            _load_articles.clear()
            _load_sources.clear()
            _load_jobs.clear()
        elif status == "locked":
            progress_bar.empty()
            progress_placeholder.warning("Парсер уже выполняется. Повторите попытку позже.")
        else:
            progress_bar.empty()
            progress_placeholder.error(
                f"Ошибка выполнения: {result.get('error', 'неизвестно')}"
            )

    if st.button("Сбросить блокировку", use_container_width=True):
        with st.spinner("Сбрасываем блокировку..."):
            was_locked = news.release_parser_lock()
        if was_locked:
            st.success("Лок был сброшен. Можно повторить запуск.")
        else:
            st.info("Лок уже свободен. Повторный запуск доступен.")
        _load_jobs.clear()

with summary_col:
    st.caption("Источник списка RSS можно настроить в config/news_parser.json или переменных окружения.")

st.divider()

ui.section_title("Свежие публикации", "последние записи по всем источникам")

feed_limit = st.slider("Количество новостей", min_value=5, max_value=100, value=25, step=5)
articles = []
try:
    articles = _load_articles(feed_limit)
except Exception as exc:  # pragma: no cover - UI feedback
    st.error(f"Не удалось загрузить список статей: {exc}")

if not articles:
    st.info("В базе пока нет новостей. Запустите парсер, чтобы заполнить ленту.")
else:
    for article in articles:
        container = st.container()
        title = article.get("title") or "Без названия"
        url = article.get("url")
        meta_parts = []
        if article.get("source"):
            meta_parts.append(article["source"])
        published_at = article.get("published_at")
        if published_at:
            meta_parts.append(str(published_at).replace("T", " "))
        if url:
            container.markdown(f"### [{title}]({url})")
        else:
            container.markdown(f"### {title}")
        if meta_parts:
            container.caption(" • ".join(meta_parts))
        tickers = article.get("tickers") or []
        if tickers:
            chips = [(ticker, "info") for ticker in tickers]
            ui.chip_row(chips)
        body = (article.get("body") or "").strip()
        if body:
            snippet = body if len(body) <= 420 else body[:417] + "..."
            container.write(snippet)
        container.divider()

st.divider()

ui.section_title("Сводка за день", "кластеризация упоминаний и топ тикеров")

utc_today = datetime.now(timezone.utc).date()
default_summary_day = utc_today if utc_today > date.min else date.today()
selected_day = st.date_input(
    "Дата (MSK)",
    value=default_summary_day,
    max_value=utc_today,
    help="Выберите дату, чтобы сформировать обзор за московский торговый день",
)

summary_data: Dict[str, Any] | None = None
try:
    target_dt = datetime.combine(selected_day, time.min, tzinfo=timezone.utc)
    summary_data = news.build_summary(target_dt)
except Exception as exc:  # pragma: no cover - UI feedback
    st.error(f"Не удалось построить сводку: {exc}")

if summary_data:
    top_mentions = summary_data.get("top_mentions", [])
    if top_mentions:
        mention_table = [[item.get("ticker"), item.get("mentions")] for item in top_mentions]
        st.markdown("**Топ упоминаний:**")
        st.table({"Тикер": [row[0] for row in mention_table], "Количество": [row[1] for row in mention_table]})
    else:
        st.caption("За выбранный день нет привязанных тикеров.")

    clusters = summary_data.get("clusters", [])
    if clusters:
        for cluster in clusters:
            header = cluster.get("headline") or "Без заголовка"
            sources_count = cluster.get("sources_count", 1)
            extra = f"{sources_count} источника" if sources_count != 1 else "1 источник"
            st.markdown(f"#### {header}")
            st.caption(extra)
            cluster_tickers = cluster.get("tickers") or []
            if cluster_tickers:
                ui.chip_row([(ticker, "info") for ticker in cluster_tickers])
            summary_text = (cluster.get("summary") or "").strip()
            if summary_text:
                st.write(summary_text)
            links = cluster.get("links") or []
            if links:
                link_items = "\n".join(f"- [{idx + 1}]({link})" for idx, link in enumerate(links))
                st.markdown(link_items)
            st.divider()
    else:
        st.caption("Кластеров с новостями не найдено для выбранного дня.")

st.divider()

sources = []
try:
    sources = _load_sources()
except Exception as exc:  # pragma: no cover - UI feedback
    st.error(f"Не удалось загрузить источники: {exc}")

if sources:
    ui.section_title("Подключенные источники", "история добавления в хранилище")
    st.dataframe(
        {
            "Название": [row.get("name") for row in sources],
            "RSS": [row.get("rss_url") for row in sources],
            "Сайт": [row.get("website") for row in sources],
            "Добавлено": [row.get("created_at") for row in sources],
        },
        use_container_width=True,
    )

jobs = []
try:
    jobs = _load_jobs(15)
except Exception as exc:  # pragma: no cover - UI feedback
    st.error(f"Не удалось загрузить историю запусков: {exc}")

if jobs:
    ui.section_title("История запусков", "данные из таблицы jobs_log")
    st.dataframe(
        {
            "Начато": [row.get("started_at") for row in jobs],
            "Статус": [row.get("status") for row in jobs],
            "Завершено": [row.get("finished_at") for row in jobs],
            "Новых статей": [row.get("new_articles") for row in jobs],
            "Дубликатов": [row.get("duplicates") for row in jobs],
            "Комментарий": [row.get("log") for row in jobs],
        },
        use_container_width=True,
    )

st.caption("Новости и связанные таблицы сохраняются в основной базе данных приложения.")
