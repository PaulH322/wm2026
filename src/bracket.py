"""Shared knockout-bracket structure helpers.

football-data.org gives each match's stage and (once decided) its two
participants, but never the bracket linkage itself - which match feeds
which. This module derives that linkage by building the tree backward from
the final: for an already-decided match its two feeders are found factually
(whichever earlier match each participant actually won); for a match not
decided yet there is nothing factual to derive, so its two feeders are
picked from the remaining fixtures of the earlier round in chronological
order (the standard adjacent-pairing bracket convention).

Building it this way (root-down, not leaf-up) matters: sorting the leaf
round by date and hoping adjacent matches pair up does NOT generally
reproduce the real bracket - the real draw has no relation to fixture
scheduling order. Working backward from a match whose participants are
known and matching by team identity is the only way to get the true
pairing for decided rounds.
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


def _team_names(m: dict) -> set[str]:
    return {n for n in ((m["homeTeam"] or {}).get("name"), (m["awayTeam"] or {}).get("name")) if n}


def _build_node(matches_by_stage: dict[str, list[dict]], stage_idx: int, match: dict, used: dict[str, set]) -> dict:
    stage = MAIN_BRACKET_STAGES[stage_idx]
    used[stage].add(match["id"])
    node = {"stage": stage, "match": match, "children": None}

    if stage_idx == 0:
        return node

    prev_stage = MAIN_BRACKET_STAGES[stage_idx - 1]
    prev_available = [m for m in matches_by_stage.get(prev_stage, []) if m["id"] not in used[prev_stage]]

    home = (match["homeTeam"] or {}).get("name")
    away = (match["awayTeam"] or {}).get("name")

    feeder_a = feeder_b = None
    if home and away:
        feeder_a = next((m for m in prev_available if home in _team_names(m)), None)
        feeder_b = next(
            (m for m in prev_available if away in _team_names(m) and m is not feeder_a), None
        )

    if feeder_a is None or feeder_b is None:
        fallback = sorted(prev_available, key=lambda m: (m["utcDate"], m["id"]))
        feeder_a, feeder_b = fallback[0], fallback[1]

    left = _build_node(matches_by_stage, stage_idx - 1, feeder_a, used)
    right = _build_node(matches_by_stage, stage_idx - 1, feeder_b, used)
    node["children"] = (left, right)
    return node


def build_bracket_tree(matches_by_stage: dict[str, list[dict]]) -> dict | None:
    final_matches = matches_by_stage.get(MAIN_BRACKET_STAGES[-1], [])
    if not final_matches:
        return None
    root_match = sorted(final_matches, key=lambda m: (m["utcDate"], m["id"]))[0]
    used: dict[str, set] = {stage: set() for stage in MAIN_BRACKET_STAGES}
    return _build_node(matches_by_stage, len(MAIN_BRACKET_STAGES) - 1, root_match, used)


def flatten_tree(root: dict | None) -> dict[str, list[dict]]:
    """Depth-first flatten (children before the match they feed) so each
    stage's list keeps the strict pairing: match i's two participants came
    from matches 2i and 2i+1 of the previous stage's list."""
    result: dict[str, list[dict]] = {stage: [] for stage in MAIN_BRACKET_STAGES}
    if root is None:
        return result

    def walk(node: dict) -> None:
        if node["children"]:
            walk(node["children"][0])
            walk(node["children"][1])
        result[node["stage"]].append(node["match"])

    walk(root)
    return result


def order_rounds(matches_by_stage: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Each stage's matches in strict-pairing order (see module docstring)."""
    ordered = flatten_tree(build_bracket_tree(matches_by_stage))
    return {stage: matches for stage, matches in ordered.items() if matches}
