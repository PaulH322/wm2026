"""Page 1: Gewinnwahrscheinlichkeit (Monte Carlo) + Elo-Rangliste."""
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

st.set_page_config(page_title="Gewinnwahrscheinlichkeit")
st.title("Gewinnwahrscheinlichkeit")

win_prob_path = PROCESSED_DIR / "win_probabilities.csv"
elo_path = PROCESSED_DIR / "elo_ratings.csv"
matches_path = PROCESSED_DIR / "matches_clean.csv"

if not (win_prob_path.exists() and elo_path.exists()):
    st.error(
        "Prognosedaten fehlen. Erst `python src/elo.py` und "
        "`python src/monte_carlo.py` ausführen."
    )
    st.stop()

if matches_path.exists():
    last_match = pd.read_csv(matches_path).sort_values(["date", "match_id"]).iloc[-1]
    st.caption(
        f"Stand nach Spiel {last_match.match_id} "
        f"({last_match.date}): {last_match.home_team} {last_match.home_score}:"
        f"{last_match.away_score} {last_match.away_team}"
    )

last_updated = datetime.fromtimestamp(win_prob_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
st.caption(f"Letzte Aktualisierung: {last_updated}")

win_probabilities = pd.read_csv(win_prob_path)
remaining = win_probabilities[win_probabilities["win_probability"] > 0].sort_values(
    "win_probability", ascending=False
)

st.subheader("Monte-Carlo-Gewinnwahrscheinlichkeit (verbleibende Teams)")
st.bar_chart(remaining.set_index("team")["win_probability"])

st.subheader("Elo-Rating (alle Teams)")
elo_ratings = pd.read_csv(elo_path).sort_values("elo", ascending=False).reset_index(drop=True)
st.dataframe(elo_ratings, width="stretch")
