"""Elo rating model -> data/processed/elo_ratings.csv

Starting Elo: flat 1500 for every team. CLAUDE.md calls for FIFA
ranking-based initialization, but the football-data.org free tier does not
expose ranking data, so this is a placeholder until a ranking source is
wired in.
"""
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

STARTING_ELO = 1500
K_GROUP_STAGE = 40
K_KNOCKOUT = 50


def expected_score(elo_a: float, elo_b: float) -> float:
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def actual_score(winner: str, is_home: bool) -> float:
    if winner == "DRAW":
        return 0.5
    won = (winner == "HOME_TEAM") == is_home
    return 1.0 if won else 0.0


def main() -> None:
    matches = pd.read_csv(PROCESSED_DIR / "matches_clean.csv").sort_values(
        ["date", "match_id"]
    )

    elo: dict[str, float] = {}

    def get_elo(team: str) -> float:
        return elo.setdefault(team, STARTING_ELO)

    for row in matches.itertuples():
        home_elo, away_elo = get_elo(row.home_team), get_elo(row.away_team)
        k = K_GROUP_STAGE if row.stage == "GROUP_STAGE" else K_KNOCKOUT

        home_actual = actual_score(row.winner, is_home=True)
        away_actual = 1 - home_actual

        home_expected = expected_score(home_elo, away_elo)
        away_expected = 1 - home_expected

        elo[row.home_team] = home_elo + k * (home_actual - home_expected)
        elo[row.away_team] = away_elo + k * (away_actual - away_expected)

    ratings = (
        pd.DataFrame(sorted(elo.items(), key=lambda x: -x[1]), columns=["team", "elo"])
        .assign(elo=lambda df: df["elo"].round(1))
    )

    out_path = PROCESSED_DIR / "elo_ratings.csv"
    ratings.to_csv(out_path, index=False)
    print(f"Saved {len(ratings)} team ratings -> {out_path}")


if __name__ == "__main__":
    main()
