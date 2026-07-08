"""Page 5: Snapshots vergangener Tage - Prognose vs. tatsächliches Ergebnis."""
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
SNAPSHOT_DIR = PROCESSED_DIR / "snapshots"

st.set_page_config(page_title="Verlauf", layout="wide")
st.title("Verlauf")
st.caption(
    "Snapshot eines vergangenen Tages: was das Modell damals vorhergesagt hat, und - "
    "sofern das Spiel inzwischen gespielt wurde - was tatsächlich passiert ist."
)

if not SNAPSHOT_DIR.exists() or not any(SNAPSHOT_DIR.iterdir()):
    st.info(
        "Noch keine Snapshots vorhanden. Sie entstehen automatisch bei jedem "
        '"Daten aktualisieren" auf der Bracket-Simulator-Seite.'
    )
    st.stop()

available_dates = sorted(p.name for p in SNAPSHOT_DIR.iterdir() if p.is_dir())
selected_date = st.selectbox("Datum", available_dates, index=len(available_dates) - 1)
snapshot_path = SNAPSHOT_DIR / selected_date

win_prob_path = snapshot_path / "win_probabilities.csv"
score_pred_path = snapshot_path / "score_predictions.csv"
elo_path = snapshot_path / "elo_ratings.csv"

current_history_path = PROCESSED_DIR / "elo_history.csv"
current_history = pd.read_csv(current_history_path) if current_history_path.exists() else pd.DataFrame()
history_by_id = (
    {row.match_id: row for row in current_history.itertuples()} if not current_history.empty else {}
)

col_elo, col_prob = st.columns(2)

if elo_path.exists():
    with col_elo:
        st.subheader(f"Elo-Rating am {selected_date}")
        elo_snapshot = pd.read_csv(elo_path).sort_values("elo", ascending=False).head(10)
        st.dataframe(elo_snapshot, width="stretch", hide_index=True)

if win_prob_path.exists():
    with col_prob:
        st.subheader(f"Gewinnwahrscheinlichkeit am {selected_date}")
        win_probs = pd.read_csv(win_prob_path)
        remaining = win_probs[win_probs["win_probability"] > 0].sort_values(
            "win_probability", ascending=False
        )
        st.bar_chart(remaining.set_index("team")["win_probability"])

st.divider()
st.subheader(f"Ergebnis-Prognosen am {selected_date}")

if not score_pred_path.exists():
    st.info("Für diesen Tag liegen keine Ergebnis-Prognosen vor.")
else:
    score_preds = pd.read_csv(score_pred_path)
    rows = []
    for match_id, group in score_preds.groupby("match_id"):
        group = group.sort_values("rank")
        top = group.iloc[0]
        score_txt = ", ".join(
            f"{int(r.home_goals)}:{int(r.away_goals)} ({r.probability:.0%})"
            for r in group.itertuples()
        )

        hist = history_by_id.get(match_id)
        if hist is not None:
            ergebnis = f"{int(hist.home_score)}:{int(hist.away_score)}"
            exakt_getroffen = (
                "ja"
                if (int(hist.home_score), int(hist.away_score))
                == (int(top.home_goals), int(top.away_goals))
                else "nein"
            )
        else:
            ergebnis, exakt_getroffen = "noch offen", "-"

        rows.append(
            {
                "spiel": f"{top.home_team} vs. {top.away_team}",
                "prognose (top 3)": score_txt,
                "tatsächliches ergebnis": ergebnis,
                "top-prognose exakt getroffen": exakt_getroffen,
            }
        )

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
