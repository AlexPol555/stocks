# bootstrap
from pathlib import Path
import sys
def _add_paths():
    here = Path(__file__).resolve()
    root = here.parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    for sub in ("core", "services"):
        ep = root / sub
        if ep.exists() and str(ep) not in sys.path:
            sys.path.insert(0, str(ep))
    parent = root.parent
    if parent and str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
_add_paths()
# -----

import pandas as pd
import streamlit as st

from core.populate import bulk_populate_database_from_csv, incremental_populate_database_from_csv
from core.utils import open_database_connection, run_api_update_job

st.title("📥 Data Load")

update_mode = st.sidebar.selectbox("Update mode:", ["CSV Upload", "API price"])

if update_mode == "CSV Upload":
    csv_upload_mode = st.sidebar.selectbox("Type:", ["Bulk", "Incremental"])

    if "csv_data" not in st.session_state:
        st.session_state.csv_data = None

    uploaded_file = st.file_uploader("Select CSV file", type="csv")
    if uploaded_file is not None:
        st.session_state.csv_data = uploaded_file

    if st.session_state.csv_data is not None:
        conn = None
        try:
            st.session_state.csv_data.seek(0)
            df_csv = pd.read_csv(st.session_state.csv_data, encoding="utf-8-sig")
            df_csv.columns = df_csv.columns.str.strip()
            st.write("Columns:", df_csv.columns.tolist())
            st.write("Preview:", df_csv.head())
            st.write("Shape:", df_csv.shape)
            st.session_state.csv_data.seek(0)
            conn = open_database_connection()
            if csv_upload_mode == "Bulk":
                bulk_populate_database_from_csv(st.session_state.csv_data, conn)
                st.success("Bulk upload done!")
            else:
                incremental_populate_database_from_csv(st.session_state.csv_data, conn)
                st.success("Incremental upload done!")
        except Exception as e:
            st.error(f"CSV error: {e}")
        finally:
            if conn is not None:
                conn.close()
    else:
        st.info("Upload a CSV file.")

else:  # API price
    st.write("Update via API for tickers in DB.")
    api_update_mode = st.radio("Kind:", ["Full", "Only missing (increment)"], horizontal=True)
    full_update = (api_update_mode == "Full")

    if st.button("Run API update now"):
        with st.spinner("Running..."):
            logs = run_api_update_job(full_update=full_update)
        st.success("Done!")
        for m in logs:
            st.write("•", m)
