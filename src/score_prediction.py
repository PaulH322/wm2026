"""Poisson goal model -> data/processed/score_predictions.csv

Simplified independent-Poisson model (standard baseline approach; does not
apply a Dixon-Coles low-score correlation correction). Each team's attack/
defense strength is its average goals scored/conceded so far this
tournament, relative to the tournament-wide average. Expected goals for a
matchup combine one side's attack strength with the other side's defense
weakness. World Cup matches are played at neutral venues, so "home"/"away"
here is only fixture order - no home-advantage factor is applied.

Only predicts matches that are not yet finished but have both participants
already known (e.g. a confirmed quarter-final pairing). Matches whose
participants are still undetermined (future rounds depending on other
results) are skipped.
"""
import json
import math
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

MAX_GOALS = 6
TOP_N = 3

# pseudo-matches at the tournament-average rate, blended into each team's
# attack/defense estimate. Teams have only played a handful of matches, so a
# raw average can hit exactly 0 (e.g. a team that hasn't conceded yet) which
# would make the Poisson model treat conceding a goal as impossible. This
# shrinks small samples toward the tournament average instead.
SHRINKAGE_MATCHES = 2


def build_team_strengths(matches: pd.DataFrame) -> tuple[dict, dict, float]:
    scored = pd.concat(
        [
            matches[["home_team", "home_score"]].rename(
                columns={"home_team": "team", "home_score": "goals"}
            ),
            matches[["away_team", "away_score"]].rename(
                columns={"away_team": "team", "away_score": "goals"}
            ),
        ]
    )
    conceded = pd.concat(
        [
            matches[["home_team", "away_score"]].rename(
                columns={"home_team": "team", "away_score": "goals"}
            ),
            matches[["away_team", "home_score"]].rename(
                columns={"away_team": "team", "home_score": "goals"}
            ),
        ]
    )
    avg_goals = scored["goals"].mean()

    scored_agg = scored.groupby("team")["goals"].agg(["sum", "count"])
    conceded_agg = conceded.groupby("team")["goals"].agg(["sum", "count"])

    attack = (
        (scored_agg["sum"] + SHRINKAGE_MATCHES * avg_goals)
        / (scored_agg["count"] + SHRINKAGE_MATCHES)
        / avg_goals
    ).to_dict()
    defense = (
        (conceded_agg["sum"] + SHRINKAGE_MATCHES * avg_goals)
        / (conceded_agg["count"] + SHRINKAGE_MATCHES)
        / avg_goals
    ).to_dict()
    return attack, defense, avg_goals


def expected_goals(
    team: str, opponent: str, attack: dict, defense: dict, avg_goals: float
) -> float:
    return avg_goals * attack.get(team, 1.0) * defense.get(opponent, 1.0)


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def top_scorelines(
    home_team: str,
    away_team: str,
    attack: dict,
    defense: dict,
    avg_goals: float,
    n: int = TOP_N,
) -> pd.DataFrame:
    lambda_home = expected_goals(home_team, away_team, attack, defense, avg_goals)
    lambda_away = expected_goals(away_team, home_team, attack, defense, avg_goals)

    rows = [
        {
            "home_goals": h,
            "away_goals": a,
            "probability": poisson_pmf(h, lambda_home) * poisson_pmf(a, lambda_away),
        }
        for h in range(MAX_GOALS + 1)
        for a in range(MAX_GOALS + 1)
    ]
    return (
        pd.DataFrame(rows)
        .sort_values("probability", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def find_pending_known_matches() -> list[dict]:
    matches = json.loads((RAW_DIR / "matches.json").read_text(encoding="utf-8"))["matches"]
    return [
        m
        for m in matches
        if m["status"] != "FINISHED"
        and (m["homeTeam"] or {}).get("name")
        and (m["awayTeam"] or {}).get("name")
    ]


def main() -> None:
    matches_clean = pd.read_csv(PROCESSED_DIR / "matches_clean.csv")
    attack, defense, avg_goals = build_team_strengths(matches_clean)

    pending = find_pending_known_matches()

    rows = []
    for m in pending:
        home, away = m["homeTeam"]["name"], m["awayTeam"]["name"]
        top = top_scorelines(home, away, attack, defense, avg_goals)
        for rank, row in enumerate(top.itertuples(), start=1):
            rows.append(
                {
                    "match_id": m["id"],
                    "home_team": home,
                    "away_team": away,
                    "rank": rank,
                    "home_goals": row.home_goals,
                    "away_goals": row.away_goals,
                    "probability": round(row.probability, 4),
                }
            )

    out_path = PROCESSED_DIR / "score_predictions.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"Saved score predictions for {len(pending)} pending matches -> {out_path}")


if __name__ == "__main__":
    main()
