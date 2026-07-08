"""Daily snapshot of processed data -> data/processed/snapshots/<date>/

Copies the current data/processed/*.csv files into a dated folder so
predictions and results can be compared retroactively (e.g. what did the
model say the day before a match was played?). Re-running on the same day
overwrites that day's snapshot; each new day gets its own folder.
"""
import shutil
from datetime import date
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
SNAPSHOT_DIR = PROCESSED_DIR / "snapshots"


def main() -> None:
    today_dir = SNAPSHOT_DIR / date.today().isoformat()
    today_dir.mkdir(parents=True, exist_ok=True)

    csv_files = list(PROCESSED_DIR.glob("*.csv"))
    for csv_file in csv_files:
        shutil.copy2(csv_file, today_dir / csv_file.name)

    print(f"Saved snapshot of {len(csv_files)} files -> {today_dir}")


if __name__ == "__main__":
    main()
