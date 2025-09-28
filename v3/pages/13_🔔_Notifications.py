"""Notifications page for the stock trading system."""

from pathlib import Path

from core.bootstrap import setup_environment

setup_environment()

import streamlit as st

from core import ui
from core.notifications import dashboard_alerts


ui.page_header(
    "Уведомления",
    "Система уведомлений и мониторинга состояния системы.",
    icon="🔔",
)

# Render full notifications page
dashboard_alerts.render_full_notifications_page()
