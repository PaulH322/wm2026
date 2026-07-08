"""WM 2026 Live Tournament Analytics - landing page."""
from datetime import datetime
from pathlib import Path

import streamlit as st

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

st.set_page_config(page_title="WM 2026 Analytics")
st.title("WM 2026 - Live Tournament Analytics")
st.markdown(
    "Live-updated WM-2026-Gewinnprognose auf Basis von Elo-Rating, Form-Score "
    "und Monte-Carlo-Simulation. Nutze die Seiten in der Sidebar links."
)

elo_path = PROCESSED_DIR / "elo_ratings.csv"
if elo_path.exists():
    last_updated = datetime.fromtimestamp(elo_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    st.caption(f"Daten zuletzt aktualisiert: {last_updated}")
