"""Fetch WM 2026 data from football-data.org -> data/raw/*.json"""
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.football-data.org/v4"
API_KEY = os.environ["FOOTBALL_DATA_API_KEY"]
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

ENDPOINTS = {
    "matches": "/competitions/WC/matches",
    "standings": "/competitions/WC/standings",
    "teams": "/competitions/WC/teams",
}


def fetch(endpoint: str) -> dict:
    response = requests.get(
        f"{BASE_URL}{endpoint}",
        headers={"X-Auth-Token": API_KEY},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, endpoint in ENDPOINTS.items():
        data = fetch(endpoint)
        out_path = RAW_DIR / f"{name}.json"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved {name} -> {out_path}")


if __name__ == "__main__":
    main()
