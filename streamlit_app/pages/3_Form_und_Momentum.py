"""Page 3: Formkurve pro Team + Elo-Verlauf-Vergleich zweier Teams."""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
sys.path.insert(0, str(ROOT_DIR / "src"))

from elo import STARTING_ELO  # noqa: E402
from form import match_result  # noqa: E402

st.set_page_config(page_title="Form & Momentum")
st.title("Form & Momentum")

matches_path = PROCESSED_DIR / "matches_clean.csv"
history_path = PROCESSED_DIR / "elo_history.csv"
form_path = PROCESSED_DIR / "form_scores.csv"

if not (matches_path.exists() and history_path.exists() and form_path.exists()):
    st.error(
        "Daten fehlen. Erst `python src/process_data.py`, `python src/elo.py` "
        "und `python src/form.py` ausführen."
    )
    st.stop()

matches = pd.read_csv(matches_path).sort_values(["date", "match_id"])
history = pd.read_csv(history_path).sort_values(["date", "match_id"])
form_scores = pd.read_csv(form_path)

teams = sorted(pd.unique(matches[["home_team", "away_team"]].values.ravel()))

st.subheader("Formkurve der letzten 3 Spiele")
selected_team = st.selectbox("Team", teams)

team_matches = matches[
    (matches["home_team"] == selected_team) | (matches["away_team"] == selected_team)
].tail(3)

if team_matches.empty:
    st.info("Keine Spiele für dieses Team gefunden.")
else:
    results = [match_result(row, selected_team) for row in team_matches.itertuples()]
    labels = {1.0: "S", 0.5: "U", 0.0: "N"}
    form_curve = pd.DataFrame(
        {"spiel": team_matches["date"] + " (" + team_matches["stage"] + ")", "ergebnis": results}
    ).set_index("spiel")
    st.bar_chart(form_curve)
    st.caption(
        "Verlauf: " + " - ".join(labels[r] for r in results)
        + " (S=Sieg, U=Unentschieden, N=Niederlage)"
    )

    score_row = form_scores[form_scores["team"] == selected_team]
    if not score_row.empty:
        st.metric("Form-Score (gewichtet 3/2/1)", score_row["form_score"].iloc[0])

st.divider()
st.subheader("Elo-Verlauf: zwei Teams im Vergleich")

col_a, col_b = st.columns(2)
team_a = col_a.selectbox("Team A", teams, index=teams.index("France") if "France" in teams else 0)
team_b = col_b.selectbox("Team B", teams, index=teams.index("Argentina") if "Argentina" in teams else 1)


def elo_trajectory(team: str) -> pd.DataFrame:
    team_history = history[
        (history["home_team"] == team) | (history["away_team"] == team)
    ]
    if team_history.empty:
        return pd.DataFrame({"date": [], "elo": []})

    # anchor point one day before the first match so the tournament-start
    # Elo doesn't collide with (and get overwritten by) the first match date
    start_date = (
        pd.to_datetime(team_history["date"].iloc[0]) - pd.Timedelta(days=1)
    ).strftime("%Y-%m-%d")
    points = [{"date": start_date, "elo": STARTING_ELO}]
    for row in team_history.itertuples():
        elo_post = row.home_elo_post if row.home_team == team else row.away_elo_post
        points.append({"date": row.date, "elo": elo_post})
    return pd.DataFrame(points)


trajectory = pd.merge(
    elo_trajectory(team_a).rename(columns={"elo": team_a}),
    elo_trajectory(team_b).rename(columns={"elo": team_b}),
    on="date",
    how="outer",
).sort_values("date").ffill()

chart_data = trajectory.melt("date", var_name="Team", value_name="Elo").dropna(subset=["Elo"])

# Y-Achse eng um die tatsächlichen Werte legen statt bei 0 zu starten,
# sonst sind Elo-Unterschiede um 1500 herum kaum sichtbar
padding = 15
y_min = chart_data["Elo"].min() - padding
y_max = chart_data["Elo"].max() + padding

elo_chart = (
    alt.Chart(chart_data)
    .mark_line(point=True)
    .encode(
        x=alt.X("date:T", title="Datum"),
        y=alt.Y("Elo:Q", scale=alt.Scale(domain=[y_min, y_max]), title="Elo-Rating"),
        color=alt.Color("Team:N", title="Team"),
        tooltip=["date:T", "Team:N", "Elo:Q"],
    )
    .properties(height=350)
)
st.altair_chart(elo_chart, width="stretch")
