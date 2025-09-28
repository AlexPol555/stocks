"""Database connection utilities for Streamlit applications."""

from __future__ import annotations

import streamlit as st
from typing import Optional
import sqlite3

from core.utils import open_database_connection


def get_db_connection() -> sqlite3.Connection:
    """
    Get database connection from session state or create new one.
    
    Returns
    -------
    sqlite3.Connection
        Database connection
    """
    if 'db_conn' not in st.session_state:
        st.session_state.db_conn = open_database_connection()
    
    return st.session_state.db_conn


def close_db_connection():
    """Close database connection if it exists in session state."""
    if 'db_conn' in st.session_state:
        try:
            st.session_state.db_conn.close()
            del st.session_state.db_conn
        except Exception:
            pass  # Ignore errors when closing


def ensure_db_connection():
    """Ensure database connection exists and is valid."""
    if 'db_conn' not in st.session_state:
        st.session_state.db_conn = open_database_connection()
        return
    
    # Test if connection is still valid
    try:
        st.session_state.db_conn.execute("SELECT 1")
    except Exception:
        # Connection is closed or invalid, create new one
        st.session_state.db_conn.close()
        st.session_state.db_conn = open_database_connection()
