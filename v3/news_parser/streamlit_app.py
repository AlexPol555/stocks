"""Minimal Streamlit UI to trigger the parser."""

import sqlite3
import subprocess

import streamlit as st

from news_parser.config import load_config

CONFIG = load_config()
DB_PATH = str(CONFIG.db_path)

st.set_page_config(page_title="News Parser", layout="wide")
st.title("News Parser — MOEX")

if st.button("Обновить новости", use_container_width=True):
    subprocess.Popen(["python", "-m", "news_parser.main", "--once"])
    st.info("Обновление запущено. Проверьте журнал запусков ниже.")

with sqlite3.connect(DB_PATH) as conn:
    cur = conn.cursor()
    cur.execute(
        "SELECT started_at, finished_at, new_articles, duplicates, status FROM jobs_log ORDER BY id DESC LIMIT 5"
    )
    rows = cur.fetchall()

st.subheader("Журнал запусков")
if not rows:
    st.write("Запусков пока не было.")
else:
    for row in rows:
        st.write(
            {
                "started_at": row[0],
                "finished_at": row[1],
                "new_articles": row[2],
                "duplicates": row[3],
                "status": row[4],
            }
        )
