from __future__ import annotations

import streamlit as st

_PRIMARY = "#2563eb"
_ACCENT = "#16a34a"
_TEXT = "#1f2937"
_BACKGROUND = "#f5f7fb"

_BASE_CSS = f"""
<style>
:root {{
  --ui-primary: {_PRIMARY};
  --ui-accent: {_ACCENT};
  --ui-text: {_TEXT};
}}

html, body, [data-testid="stAppViewContainer"] {{
  background: {_BACKGROUND};
  color: var(--ui-text);
}}

section[data-testid="stSidebar"] {{
  background: white;
  border-right: 1px solid #e5e7eb;
}}

section[data-testid="stSidebar"] .block-container {{
  padding-top: 2rem;
}}

.block-container {{
  padding-top: 2.5rem;
}}

.ui-heading {{
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}}

.ui-heading__icon {{
  font-size: 2.5rem;
  line-height: 1;
}}

.ui-heading__text h1 {{
  margin: 0;
  font-size: 2.3rem;
  font-weight: 700;
}}

.ui-heading__text p {{
  margin: 0.15rem 0 0;
  font-size: 0.95rem;
  color: #4b5563;
}}

.ui-section-title {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 1.8rem 0 0.75rem;
}}

.ui-section-title h3 {{
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
}}

.ui-chip {{
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.35rem 0.9rem;
  font-size: 0.8rem;
  font-weight: 600;
  background: rgba(37,99,235,0.08);
  color: var(--ui-primary);
  margin-right: 0.4rem;
}}

.ui-chip[data-tone="positive"] {{
  background: rgba(22,163,74,0.12);
  color: #15803d;
}}

.ui-chip[data-tone="warning"] {{
  background: rgba(234,179,8,0.14);
  color: #b45309;
}}

.ui-chip[data-tone="negative"] {{
  background: rgba(220,38,38,0.12);
  color: #b91c1c;
}}

.stMetric {{
  background: white;
  border-radius: 18px;
  padding: 1rem 1.2rem;
  border: 1px solid #e2e8f0;
  box-shadow: 0 12px 30px rgba(15,23,42,0.06);
}}

.stMetric label {{
  font-size: 0.85rem !important;
  color: #64748b !important;
}}

.stMetric [data-testid="stMetricValue"] {{
  color: var(--ui-text);
}}

button[kind="primary"] {{
  border-radius: 999px !important;
}}

[data-testid="stForm"] {{
  background: white;
  border-radius: 16px;
  padding: 1rem 1.5rem;
  border: 1px solid #e2e8f0;
}}

[data-testid="stTab"] > div {{
  padding-top: 1rem;
}}

[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {{
  gap: 1rem;
}}

.stDataFrame {{
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}}

.stAlert {{
  border-radius: 14px;
  border: 1px solid #e2e8f0;
}}
</style>
"""


def inject_base_theme() -> None:
    """Inject once-per-session CSS overrides for a cleaner UI."""
    if st.session_state.get("_ui_theme_injected"):
        return
    st.session_state["_ui_theme_injected"] = True
    st.markdown(_BASE_CSS, unsafe_allow_html=True)


def page_header(title: str, description: str | None = None, icon: str | None = None) -> None:
    """Render a prominent page heading with optional icon and description."""
    inject_base_theme()
    icon_html = f"<span class='ui-heading__icon'>{icon}</span>" if icon else ""
    desc_html = f"<p>{description}</p>" if description else ""
    st.markdown(
        f"<div class='ui-heading'>{icon_html}<div class='ui-heading__text'><h1>{title}</h1>{desc_html}</div></div>",
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str | None = None) -> None:
    """Render a secondary section title with an optional subtitle."""
    inject_base_theme()
    subtitle_html = f"<span style='color:#64748b;font-size:0.85rem;'>{subtitle}</span>" if subtitle else ""
    st.markdown(
        f"<div class='ui-section-title'><h3>{title}</h3>{subtitle_html}</div>",
        unsafe_allow_html=True,
    )


def chip(text: str, tone: str = "info") -> str:
    """Return HTML snippet for a colored chip."""
    inject_base_theme()
    return f"<span class='ui-chip' data-tone='{tone}'>{text}</span>"


def chip_row(items: list[tuple[str, str]]) -> None:
    """Render a row of chips, the tone is derived from second value."""
    if not items:
        return
    fragments = []
    for text, tone in items:
        fragments.append(chip(text, tone))
    st.markdown(" ".join(fragments), unsafe_allow_html=True)

