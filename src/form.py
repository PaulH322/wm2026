"""Form score, last 3 matches weighted 3/2/1 -> data/processed/form_scores.csv"""
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

WEIGHTS = [3, 2, 1]  # most recent match first


def match_result(row, team: str) -> float:
    if row.winner == "DRAW":
        return 0.5
    is_home = row.home_team == team
    won = (row.winner == "HOME_TEAM") == is_home
    return 1.0 if won else 0.0


def main() -> None:
    matches = pd.read_csv(PROCESSED_DIR / "matches_clean.csv").sort_values(
        ["date", "match_id"]
    )
    teams = pd.unique(matches[["home_team", "away_team"]].values.ravel())

    scores = []
    for team in teams:
        team_matches = matches[
            (matches["home_team"] == team) | (matches["away_team"] == team)
        ]
        last_matches = team_matches.tail(3).iloc[::-1]  # most recent first
        results = [match_result(row, team) for row in last_matches.itertuples()]
        weights = WEIGHTS[: len(results)]
        form_score = sum(r * w for r, w in zip(results, weights)) / sum(weights)
        scores.append(
            {
                "team": team,
                "form_score": round(form_score, 3),
                "matches_considered": len(results),
            }
        )

    df = pd.DataFrame(scores).sort_values("form_score", ascending=False).reset_index(
        drop=True
    )
    out_path = PROCESSED_DIR / "form_scores.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved form scores for {len(df)} teams -> {out_path}")


if __name__ == "__main__":
    main()
