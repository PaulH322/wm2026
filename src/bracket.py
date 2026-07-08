"""Shared knockout-bracket structure helpers.

football-data.org gives each match's stage and (once decided) its two
participants, but never the bracket linkage itself - which match feeds
which. For rounds that are already decided this module derives that
linkage factually (by finding which earlier match each participant
actually won); for rounds that aren't decided yet there is nothing factual
to derive, so callers that need to project forward pair up consecutive
entries of the previous round (standard bracket convention: winner of
match 1 vs winner of match 2, match 3 vs match 4, ...).
"""
import json
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

MAIN_BRACKET_STAGES = ["LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]
STAGE_LABELS = {
    "LAST_32": "Sechzehntelfinale",
    "LAST_16": "Achtelfinale",
    "QUARTER_FINALS": "Viertelfinale",
    "SEMI_FINALS": "Halbfinale",
    "THIRD_PLACE": "Spiel um Platz 3",
    "FINAL": "Finale",
}


def load_matches_by_stage() -> dict[str, list[dict]]:
    matches = json.loads((RAW_DIR / "matches.json").read_text(encoding="utf-8"))["matches"]
    by_stage: dict[str, list[dict]] = {}
    for m in matches:
        if m["stage"] in STAGE_LABELS:
            by_stage.setdefault(m["stage"], []).append(m)
    return by_stage


def order_rounds(matches_by_stage: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Order each round top-to-bottom so it lines up with the round before
    it. For rounds whose participants are already decided, the order is
    derived factually (which earlier match each team actually won); for
    rounds not yet decided it falls back to chronological order."""
    ordered: dict[str, list[dict]] = {}
    prev_index: dict[str, int] | None = None

    for stage in MAIN_BRACKET_STAGES:
        stage_matches = matches_by_stage.get(stage, [])
        if not stage_matches:
            continue

        if prev_index is None:
            stage_matches = sorted(stage_matches, key=lambda m: (m["utcDate"], m["id"]))
        else:
            def sort_key(m):
                teams = [(m["homeTeam"] or {}).get("name"), (m["awayTeam"] or {}).get("name")]
                indices = [prev_index[t] for t in teams if t and t in prev_index]
                return (min(indices) if indices else 999, m["utcDate"], m["id"])

            stage_matches = sorted(stage_matches, key=sort_key)

        ordered[stage] = stage_matches
        prev_index = {}
        for idx, m in enumerate(stage_matches):
            for side in ("homeTeam", "awayTeam"):
                name = (m[side] or {}).get("name")
                if name:
                    prev_index[name] = idx

    return ordered
