"""Page 2: Ergebnisse, Tordifferenz pro Team, Upset-Tracker."""
from pathlib import Path

import pandas as pd
import streamlit as st

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

st.set_page_config(page_title="Turnier-Übersicht")
st.title("Turnier-Übersicht")

matches_path = PROCESSED_DIR / "matches_clean.csv"
history_path = PROCESSED_DIR / "elo_history.csv"

if not matches_path.exists():
    st.error("Keine matches_clean.csv gefunden. Erst `python src/process_data.py` ausführen.")
    st.stop()

matches = pd.read_csv(matches_path).sort_values(["date", "match_id"], ascending=False)

st.subheader("Ergebnisse aller gespielten Spiele")
st.dataframe(
    matches[["date", "stage", "home_team", "home_score", "away_score", "away_team"]],
    width="stretch",
    hide_index=True,
)

st.subheader("Tordifferenz pro Team")
goals_for = matches.groupby("home_team")["home_score"].sum().add(
    matches.groupby("away_team")["away_score"].sum(), fill_value=0
)
goals_against = matches.groupby("home_team")["away_score"].sum().add(
    matches.groupby("away_team")["home_score"].sum(), fill_value=0
)
goal_diff = (goals_for - goals_against).sort_values(ascending=False)
goal_diff.index.name = "team"
st.bar_chart(goal_diff)

st.subheader("Upset-Tracker")
st.caption("Spiele, in denen das Elo-Modell mit dem Favoriten falsch lag.")
if history_path.exists():
    history = pd.read_csv(history_path)
    upsets = history[history["upset"]].sort_values(["date", "match_id"], ascending=False)
    if upsets.empty:
        st.info("Bisher keine Überraschungssiege laut Elo-Modell.")
    else:
        st.dataframe(
            upsets[
                [
                    "date",
                    "stage",
                    "home_team",
                    "home_score",
                    "away_score",
                    "away_team",
                    "home_elo_pre",
                    "away_elo_pre",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
else:
    st.warning("Keine elo_history.csv gefunden. Erst `python src/elo.py` ausführen.")
