"""Monte Carlo bracket simulation -> data/processed/win_probabilities.csv

Simulates the remaining single-elimination bracket N_SIMULATIONS times using
Elo-derived win probabilities and counts how often each team wins the
tournament. Pairings for rounds beyond the next confirmed one (e.g. semis
when only quarter-final fixtures are known) are not exposed by
football-data.org. For already-decided rounds the true bracket order is
derived factually via bracket.order_rounds(); the first still-undetermined
round then pairs up consecutive entries of that order (standard adjacent-
pairing bracket convention: winner of match 1 vs winner of match 2, winner
of match 3 vs winner of match 4, etc.).
"""
import random
from pathlib import Path

import pandas as pd

from bracket import MAIN_BRACKET_STAGES, load_matches_by_stage, order_rounds

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

N_SIMULATIONS = 10_000
RANDOM_SEED = 42


def expected_score(elo_a: float, elo_b: float) -> float:
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def load_remaining_bracket() -> list[tuple[str, str]]:
    matches_by_stage = load_matches_by_stage()
    ordered_rounds = order_rounds(matches_by_stage)
    for stage in MAIN_BRACKET_STAGES:
        pending = [m for m in ordered_rounds.get(stage, []) if m["status"] != "FINISHED"]
        if pending:
            return [(m["homeTeam"]["name"], m["awayTeam"]["name"]) for m in pending]
    return []


def simulate_once(
    pairs: list[tuple[str, str]], elo: dict[str, float], rng: random.Random
) -> str:
    round_pairs = pairs
    while True:
        winners = []
        for team_a, team_b in round_pairs:
            p_a = expected_score(elo[team_a], elo[team_b])
            winners.append(team_a if rng.random() < p_a else team_b)
        if len(winners) == 1:
            return winners[0]
        round_pairs = list(zip(winners[0::2], winners[1::2]))


def main() -> None:
    elo = dict(
        pd.read_csv(PROCESSED_DIR / "elo_ratings.csv")[["team", "elo"]].itertuples(
            index=False, name=None
        )
    )
    pairs = load_remaining_bracket()
    if not pairs:
        print("No remaining knockout matches found - tournament already decided.")
        return

    rng = random.Random(RANDOM_SEED)
    wins = {team: 0 for team in elo}
    for _ in range(N_SIMULATIONS):
        champion = simulate_once(pairs, elo, rng)
        wins[champion] += 1

    probabilities = (
        pd.DataFrame(
            {
                "team": list(wins.keys()),
                "win_probability": [w / N_SIMULATIONS for w in wins.values()],
            }
        )
        .sort_values("win_probability", ascending=False)
        .reset_index(drop=True)
    )

    out_path = PROCESSED_DIR / "win_probabilities.csv"
    probabilities.to_csv(out_path, index=False)
    print(f"Saved win probabilities for {len(probabilities)} teams -> {out_path}")


if __name__ == "__main__":
    main()
