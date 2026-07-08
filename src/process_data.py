"""Clean raw API data -> data/processed/matches_clean.csv"""
import json
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def main() -> None:
    matches = json.loads((RAW_DIR / "matches.json").read_text(encoding="utf-8"))["matches"]

    rows = []
    for match in matches:
        if match["status"] != "FINISHED":
            continue
        full_time = match["score"]["fullTime"]
        rows.append(
            {
                "match_id": match["id"],
                "date": match["utcDate"][:10],
                "stage": match["stage"],
                "home_team": match["homeTeam"]["name"],
                "away_team": match["awayTeam"]["name"],
                "home_score": full_time["home"],
                "away_score": full_time["away"],
                # winner (not just fullTime score) so knockout matches decided
                # on penalties are counted correctly, not as a draw
                "winner": match["score"]["winner"],
            }
        )

    df = pd.DataFrame(rows).sort_values(["date", "match_id"]).reset_index(drop=True)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "matches_clean.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} finished matches -> {out_path}")


if __name__ == "__main__":
    main()
