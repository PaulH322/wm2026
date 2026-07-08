"""Minimal end-to-end check: render current Elo ratings.

Not the final multi-page dashboard from CLAUDE.md yet - just a smoke test
that the pipeline (fetch -> process -> elo) produces something visible.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

st.set_page_config(page_title="WM 2026 - Elo Check", page_icon="\U0001F3C6")
st.title("WM 2026 - Elo Ratings (Pipeline Smoke Test)")

ratings_path = PROCESSED_DIR / "elo_ratings.csv"
if not ratings_path.exists():
    st.error("Keine elo_ratings.csv gefunden. Erst `python src/elo.py` ausfuehren.")
    st.stop()

ratings = pd.read_csv(ratings_path)

st.bar_chart(ratings.set_index("team")["elo"])
st.dataframe(ratings, use_container_width=True)
