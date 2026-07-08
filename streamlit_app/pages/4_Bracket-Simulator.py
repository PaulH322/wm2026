"""Page 4: Turnierbaum mit Prognose vs. Ergebnis, plus Neuberechnung."""
import html
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
sys.path.insert(0, str(ROOT_DIR / "src"))

from bracket import MAIN_BRACKET_STAGES, STAGE_LABELS, load_matches_by_stage, order_rounds  # noqa: E402
from elo import expected_score  # noqa: E402
from score_prediction import build_team_strengths, top_scorelines  # noqa: E402

PIPELINE_SCRIPTS = [
    "fetch_data.py",
    "process_data.py",
    "elo.py",
    "form.py",
    "monte_carlo.py",
    "score_prediction.py",
    "snapshot.py",
]

BRACKET_CSS = """
<style>
.bracket-wrap {
  --surface: #fcfcfb;
  --border: rgba(11,11,11,0.10);
  --text: #0b0b0b;
  --secondary: #52514e;
  --muted: #898781;
  overflow-x: auto;
  padding-bottom: 8px;
}
@media (prefers-color-scheme: dark) {
  .bracket-wrap {
    --surface: #1a1a19;
    --border: rgba(255,255,255,0.10);
    --text: #ffffff;
    --secondary: #c3c2b7;
    --muted: #898781;
  }
}
.bracket { display: flex; gap: 20px; align-items: stretch; min-width: max-content; }
.bracket-round { display: flex; flex-direction: column; width: 220px; }
.bracket-round-title {
  font-size: 0.72rem; text-transform: uppercase; letter-spacing: .04em;
  color: var(--muted); text-align: center; margin-bottom: 8px; flex: 0 0 auto;
}
.bracket-round-body {
  display: flex; flex-direction: column; justify-content: space-evenly;
  gap: 10px; flex: 1 1 auto;
}
.bracket-match {
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px;
  background: var(--surface); color: var(--text); font-size: 0.82rem;
}
.bracket-match-tbd { opacity: 0.6; }
.bracket-match-projected { border-style: dashed; }
.bracket-teams { font-weight: 600; margin-bottom: 4px; }
.bracket-detail { color: var(--secondary); font-size: 0.76rem; line-height: 1.4; }
.badge { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 0.72rem; font-weight: 600; }
.badge-good { color: #0ca30c; background: rgba(12,163,12,0.12); }
.badge-critical { color: #d03b3b; background: rgba(208,59,59,0.12); }
.badge-muted { color: var(--muted); background: rgba(137,135,129,0.14); }
</style>
"""


def resolve_slot(m: dict, home: str | None, away: str | None, matchup_confirmed: bool, current_elo: dict) -> dict:
    finished = matchup_confirmed and m["status"] == "FINISHED"
    winner = None
    favorite_pct = None

    if finished:
        winner = home if m["score"]["winner"] == "HOME_TEAM" else away
    elif home and away:
        p_home = expected_score(current_elo.get(home, 1500), current_elo.get(away, 1500))
        winner = home if p_home >= 0.5 else away
        favorite_pct = round((p_home if p_home >= 0.5 else 1 - p_home) * 100)

    return {
        "match": m,
        "home": home,
        "away": away,
        "matchup_confirmed": matchup_confirmed,
        "finished": finished,
        "winner": winner,
        "favorite_pct": favorite_pct,
    }


def compute_winners(ordered_rounds: dict, current_elo: dict) -> dict[str, list[dict]]:
    """Resolve (home, away, winner) for every slot in every round. Matches
    that have already been played use the real result; matches that are
    confirmed but not yet played use today's Elo favorite as the projected
    winner; rounds whose participants aren't decided yet (e.g. the final,
    while the semis haven't been played) get their participants from the
    previous round's projected/actual winners, paired up two at a time -
    so a favorite keeps advancing on paper all the way to the final."""
    results: dict[str, list[dict]] = {}
    prev_winners: list[str | None] | None = None

    for stage in MAIN_BRACKET_STAGES:
        matches = ordered_rounds.get(stage, [])
        slots = []
        for i, m in enumerate(matches):
            real_home = (m["homeTeam"] or {}).get("name")
            real_away = (m["awayTeam"] or {}).get("name")
            matchup_confirmed = bool(real_home and real_away)

            home, away = real_home, real_away
            if not matchup_confirmed and prev_winners is not None:
                lo, hi = 2 * i, 2 * i + 1
                if hi < len(prev_winners) and prev_winners[lo] and prev_winners[hi]:
                    home, away = prev_winners[lo], prev_winners[hi]

            slots.append(resolve_slot(m, home, away, matchup_confirmed, current_elo))
        results[stage] = slots
        prev_winners = [s["winner"] for s in slots]

    return results


def resolve_third_place(third_place_matches: list[dict], sf_slots: list[dict], current_elo: dict) -> dict | None:
    if not third_place_matches:
        return None
    m3 = third_place_matches[0]
    real_home = (m3["homeTeam"] or {}).get("name")
    real_away = (m3["awayTeam"] or {}).get("name")
    matchup_confirmed = bool(real_home and real_away)

    def loser(slot: dict | None) -> str | None:
        if not slot or slot["winner"] is None:
            return None
        return slot["away"] if slot["winner"] == slot["home"] else slot["home"]

    home3 = real_home or (loser(sf_slots[0]) if len(sf_slots) > 0 else None)
    away3 = real_away or (loser(sf_slots[1]) if len(sf_slots) > 1 else None)
    return resolve_slot(m3, home3, away3, matchup_confirmed, current_elo)


def format_top_scorelines(scorelines: pd.DataFrame) -> str:
    return ", ".join(
        f"{int(r.home_goals)}:{int(r.away_goals)} ({r.probability:.0%})"
        for r in scorelines.itertuples()
    )


def render_slot_card(
    slot: dict, history_by_id: dict, score_pred_by_id: dict, goal_model: tuple
) -> str:
    m = slot["match"]
    date = m["utcDate"][:10]
    home, away = slot["home"], slot["away"]

    if not (home and away):
        return (
            '<div class="bracket-match bracket-match-tbd">'
            '<div class="bracket-teams">Teilnehmer offen</div>'
            f'<div class="bracket-detail">{date}</div></div>'
        )

    home_safe, away_safe = html.escape(home), html.escape(away)

    if slot["finished"]:
        score = m["score"]["fullTime"]
        hist = history_by_id.get(m["id"])
        if hist is not None:
            correct = not bool(hist["upset"])
            badge_class = "badge-good" if correct else "badge-critical"
            badge_text = "Favorit richtig" if correct else "Favorit falsch"
            detail = (
                f'{score["home"]}:{score["away"]} &middot; '
                f'<span class="badge {badge_class}">{badge_text}</span>'
            )
        else:
            detail = f'{score["home"]}:{score["away"]}'
        card_class = "bracket-match"
    else:
        favorit = home_safe if slot["winner"] == home else away_safe
        lines = [f"Favorit: {favorit} ({slot['favorite_pct']}%)"]

        if slot["matchup_confirmed"]:
            preds = score_pred_by_id.get(m["id"])
            if preds is not None and not preds.empty:
                lines.append(f"Erw. Ergebnis: {format_top_scorelines(preds)}")
            card_class = "bracket-match"
        else:
            attack, defense, avg_goals = goal_model
            preds = top_scorelines(home, away, attack, defense, avg_goals)
            lines.append(f"Erw. Ergebnis: {format_top_scorelines(preds)}")
            lines.insert(0, '<span class="badge badge-muted">Prognose</span>')
            card_class = "bracket-match bracket-match-projected"

        detail = "<br>".join(lines)

    return (
        f'<div class="{card_class}">'
        f'<div class="bracket-teams">{home_safe} - {away_safe}</div>'
        f'<div class="bracket-detail">{detail}</div></div>'
    )


def build_bracket_html(
    computed_rounds: dict, history_by_id: dict, score_pred_by_id: dict, goal_model: tuple
) -> str:
    columns = []
    for stage in MAIN_BRACKET_STAGES:
        slots = computed_rounds.get(stage)
        if not slots:
            continue
        cards = "".join(
            render_slot_card(s, history_by_id, score_pred_by_id, goal_model) for s in slots
        )
        columns.append(
            f'<div class="bracket-round"><div class="bracket-round-title">{STAGE_LABELS[stage]}</div>'
            f'<div class="bracket-round-body">{cards}</div></div>'
        )
    return BRACKET_CSS + f'<div class="bracket-wrap"><div class="bracket">{"".join(columns)}</div></div>'


st.set_page_config(page_title="Bracket-Simulator", layout="wide")
st.title("Bracket-Simulator")
st.caption(
    "Turnierbaum mit Prognose je Spiel. Sobald ein Spiel gespielt wurde, zeigt sich, "
    "ob das Elo-Modell mit dem Favoriten richtig lag."
)
st.caption(
    "Gestrichelte Felder sind noch keine feststehenden Spiele, sondern zeigen, wer bei "
    "durchgehendem Favoritensieg einziehen würde."
)

elo_path = PROCESSED_DIR / "elo_ratings.csv"
history_path = PROCESSED_DIR / "elo_history.csv"
score_pred_path = PROCESSED_DIR / "score_predictions.csv"

if not elo_path.exists():
    st.error(
        "Basisdaten fehlen. Erst `python src/fetch_data.py`, `python src/process_data.py` "
        "und `python src/elo.py` ausführen."
    )
    st.stop()

current_elo = dict(pd.read_csv(elo_path)[["team", "elo"]].itertuples(index=False, name=None))
history = pd.read_csv(history_path) if history_path.exists() else pd.DataFrame()
history_by_id = (
    {row["match_id"]: row for _, row in history.iterrows()} if not history.empty else {}
)

score_predictions = pd.read_csv(score_pred_path) if score_pred_path.exists() else pd.DataFrame()
score_pred_by_id = (
    {mid: grp.sort_values("rank") for mid, grp in score_predictions.groupby("match_id")}
    if not score_predictions.empty
    else {}
)

matches_clean_path = PROCESSED_DIR / "matches_clean.csv"
goal_model = build_team_strengths(pd.read_csv(matches_clean_path)) if matches_clean_path.exists() else ({}, {}, 1.5)

matches_by_stage = load_matches_by_stage()
ordered_rounds = order_rounds(matches_by_stage)
computed_rounds = compute_winners(ordered_rounds, current_elo)

st.markdown(
    build_bracket_html(computed_rounds, history_by_id, score_pred_by_id, goal_model),
    unsafe_allow_html=True,
)

third_place_slot = resolve_third_place(
    matches_by_stage.get("THIRD_PLACE", []), computed_rounds.get("SEMI_FINALS", []), current_elo
)
if third_place_slot:
    st.markdown(f"**{STAGE_LABELS['THIRD_PLACE']}**")
    st.markdown(
        BRACKET_CSS
        + '<div class="bracket-wrap"><div class="bracket" style="min-width:220px;">'
        + render_slot_card(third_place_slot, history_by_id, score_pred_by_id, goal_model)
        + "</div></div>",
        unsafe_allow_html=True,
    )

with st.expander("Alle K.-o.-Spiele als Tabelle"):
    rows = []
    for stage in list(STAGE_LABELS):
        for m in sorted(matches_by_stage.get(stage, []), key=lambda m: (m["utcDate"], m["id"])):
            home = (m["homeTeam"] or {}).get("name") or "?"
            away = (m["awayTeam"] or {}).get("name") or "?"
            date = m["utcDate"][:10]
            if m["status"] == "FINISHED":
                score = m["score"]["fullTime"]
                ergebnis = f"{score['home']}:{score['away']}"
                hist = history_by_id.get(m["id"])
                richtig = "-" if hist is None else ("ja" if not bool(hist["upset"]) else "nein")
            else:
                ergebnis, richtig = "steht noch aus", "-"
            rows.append(
                {
                    "date": date,
                    "stage": STAGE_LABELS[stage],
                    "spiel": f"{home} vs. {away}",
                    "ergebnis": ergebnis,
                    "richtig gelegen": richtig,
                }
            )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

if history_by_id:
    knockout_ids = {m["id"] for matches in matches_by_stage.values() for m in matches}
    knockout_richtig = [
        not bool(row["upset"]) for mid, row in history_by_id.items() if mid in knockout_ids
    ]
    if knockout_richtig:
        st.metric(
            "Trefferquote K.-o.-Runde",
            f"{sum(knockout_richtig)} / {len(knockout_richtig)}",
        )

st.divider()
if st.button("Daten aktualisieren (neue Ergebnisse abrufen und neu berechnen)", type="primary"):
    with st.spinner("Hole neue Daten und berechne neu..."):
        for script in PIPELINE_SCRIPTS:
            result = subprocess.run(
                [sys.executable, str(ROOT_DIR / "src" / script)],
                cwd=str(ROOT_DIR),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                st.error(f"Fehler in {script}:\n{result.stderr}")
                st.stop()
    st.success("Daten aktualisiert.")
    st.rerun()
