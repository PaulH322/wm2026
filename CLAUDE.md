# WM 2026 — Live Tournament Analytics

Portfolio project: live-updated World Cup 2026 winner prediction and tournament analysis,
powered by the football-data.org API and automated via GitHub Actions.

---

## Goal

Demonstrate Data Analyst + Data Engineering skills through a **live, auto-updating pipeline**
running during an active tournament. Every day after matches are played, new data is fetched,
models are recalculated, and the Streamlit dashboard reflects the current state of the tournament.

---

## Data Source

**football-data.org** — free tier, no scraping, clean REST API.

- Base URL: `https://api.football-data.org/v4/`
- Requires free API key (env var: `FOOTBALL_DATA_API_KEY`)
- Relevant endpoints:
  - `/competitions/WC/matches` — all matches, results, status
  - `/competitions/WC/standings` — group stage standings
  - `/competitions/WC/teams` — team metadata
  - `/competitions/WC/scorers` — top scorers

**Limitations of this API (important):**
- No injury data
- No suspension/yellow card accumulation (partially available via match events on paid tier)
- No player-level stats on free tier

> For injuries and suspensions: see Phase 5 (manual enrichment layer).

---

## Win Probability Model

### Inputs per team (recalculated after every match)

| Feature | Source | Notes |
|---|---|---|
| Goals scored / conceded | API `/matches` | Raw totals |
| Goal difference | Derived | Per match and cumulative |
| Wins / draws / losses | API | Knockout: draws go to extra time |
| **Elo rating** | Calculated | Core model — see below |
| **Form score** | Derived | Last 3 matches, weighted 3/2/1 |
| Remaining bracket difficulty | Derived | Avg. Elo of potential opponents |
| *(Suspensions)* | Manual / scrape | Phase 5 — optional enrichment |
| *(Injuries)* | Manual / scrape | Phase 5 — optional enrichment |

### Elo Rating (core model)

Standard Elo with K-factor tuned for tournament football:

```
new_elo = old_elo + K × (actual_result - expected_result)
expected = 1 / (1 + 10^((opponent_elo - own_elo) / 400))
actual: Win=1, Draw=0.5, Loss=0
K = 40 (knockout matches weighted higher: K=50)
```

Starting Elo values: FIFA ranking-based initialization (fetched once at project start).

### Form Score

```
form_score = (result_n-0 × 3 + result_n-1 × 2 + result_n-2 × 1) / 6
# result: Win=1, Draw=0.5, Loss=0
```

### Monte Carlo Simulation

After each round, simulate the remaining bracket 10,000 times:
- Each match: win probability derived from Elo delta
- Track how often each team wins the tournament
- Output: probability distribution over all remaining teams

```python
# Simplified logic
def simulate_match(elo_a, elo_b):
    p_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    return "A" if random.random() < p_a else "B"
```

---

## Phase 5 — Injury & Suspension Enrichment (optional)

This is the hardest data problem in the project. No free structured API covers this reliably.

**Options:**
1. **Manual JSON file** (`data/manual/player_status.json`) — updated by hand when news breaks.
   Simple structure: `{ "team": "France", "player": "Mbappé", "status": "doubtful", "reason": "knee" }`
2. **Transfermarkt scrape** — more complex, fragile, legal grey zone. Not recommended for portfolio.
3. **News API (NewsAPI.org)** — free tier, search for "[team] injury WM 2026", parse headlines.
   Shows NLP/text skills but low reliability. Good as "bonus feature" label in dashboard.

**Recommendation:** Implement option 1 (manual JSON) with a clear UI note in the dashboard:
*"Injury data manually maintained — last updated: [date]"*. Honest and professional.

---

## Project Structure

```
WM2026-Analytics/
├── .github/
│   └── workflows/
│       └── update_data.yml        # GitHub Actions daily fetch
├── data/
│   ├── raw/                       # Raw API responses (JSON)
│   │   ├── matches.json
│   │   ├── standings.json
│   │   └── teams.json
│   ├── processed/                 # Cleaned CSVs for analysis
│   │   ├── matches_clean.csv
│   │   ├── elo_ratings.csv
│   │   └── win_probabilities.csv
│   └── manual/
│       └── player_status.json     # Injuries / suspensions (manual)
├── notebooks/
│   ├── 01_eda.ipynb               # Exploratory analysis
│   ├── 02_elo_model.ipynb         # Elo rating development
│   └── 03_monte_carlo.ipynb       # Simulation + probabilities
├── src/
│   ├── fetch_data.py              # API calls → data/raw/
│   ├── process_data.py            # Cleaning → data/processed/
│   ├── elo.py                     # Elo model logic
│   ├── monte_carlo.py             # Bracket simulation
│   └── form.py                    # Form score calculation
├── streamlit_app/
│   └── app.py                     # Dashboard (multi-page)
├── requirements.txt
├── .env.example                   # FOOTBALL_DATA_API_KEY=your_key_here
├── .gitignore                     # .env, __pycache__, etc.
└── CLAUDE.md                      # This file
```

---

## GitHub Actions — Automated Daily Update

**File:** `.github/workflows/update_data.yml`

```yaml
name: Update WM Data

on:
  schedule:
    - cron: '0 6 * * *'   # Every day at 06:00 UTC (= 08:00 CEST)
  workflow_dispatch:        # Also triggerable manually via GitHub UI

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Fetch latest data
        env:
          FOOTBALL_DATA_API_KEY: ${{ secrets.FOOTBALL_DATA_API_KEY }}
        run: python src/fetch_data.py

      - name: Process & recalculate model
        run: |
          python src/process_data.py
          python src/elo.py
          python src/monte_carlo.py

      - name: Commit updated data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/processed/ data/raw/
          git diff --staged --quiet || git commit -m "Auto-update: $(date '+%Y-%m-%d %H:%M') UTC"
          git push
```

**Required GitHub Secret:**
- `FOOTBALL_DATA_API_KEY` — set under *Settings → Secrets and variables → Actions*

**Timing logic:**
- Cron runs at 06:00 UTC daily — most WM matches finish by then
- `workflow_dispatch` allows manual trigger after a big match day

---

## Streamlit Dashboard — Pages

### Page 1 — 🏆 Gewinnwahrscheinlichkeit
- Balkendiagramm: alle verbleibenden Teams mit Monte-Carlo-Wahrscheinlichkeit
- "Stand nach Spiel X" — Timestamp der letzten Aktualisierung
- Tabelle: Elo-Rating aller Teams, sortiert

### Page 2 — 📊 Turnier-Übersicht
- Ergebnisse aller gespielten Spiele
- Tordifferenz-Visualisierung pro Team
- Upset-Tracker: Spiele wo das Elo-Modell falsch lag (Überraschungssiege)

### Page 3 — 📈 Form & Momentum
- Formkurve der letzten 3 Spiele pro Team (Dropdown)
- Vergleich zweier Teams: Elo-Verlauf über das Turnier

### Page 4 — 🎲 Bracket-Simulator
- Interaktiv: User wählt Viertelfinalpaarungen manuell → Simulation läuft durch
- Zeigt: "Was wäre wenn Spanien auf Frankreich trifft?"

### Page 5 — 🏥 Kader-Status *(optional)*
- Tabelle aus `player_status.json`
- Einfluss auf Elo: z.B. -20 Elo-Punkte wenn Stamm-Torwart fehlt (konfigurierbar)

---

## Conventions

- Python 3.11
- Libraries: `requests`, `pandas`, `numpy`, `matplotlib`, `seaborn`, `streamlit`, `scipy`
- All API calls in `src/fetch_data.py` — never inline in notebooks
- Processed data always in `data/processed/` — notebooks read from there, never from raw
- Secrets never committed — always via `.env` locally, GitHub Secrets in CI
- `requirements.txt` pinned versions for reproducibility

---

## Timeline

| Datum | Meilenstein |
|---|---|
| Jetzt | Setup, API-Anbindung, Elo-Grundmodell |
| ~10. Juli | Viertelfinale läuft — Dashboard live mit 4 Teams |
| ~14. Juli | Halbfinale — Monte Carlo besonders spannend mit 4 Teams |
| 19. Juli | **WM-Finale** — letzter Live-Update, Projekt abgeschlossen |
| Nach dem 19. Juli | Projekt als "abgeschlossene Live-Analyse WM 2026" im Portfolio |

---

## Portfolio Value

Dieses Projekt demonstriert:

- **API-Integration** — REST API, Auth, Pagination, Error Handling
- **Automatisierte Pipeline** — GitHub Actions, Cron, CI/CD-Grundverständnis
- **Datenmodellierung** — Elo-Rating, gewichtete Kennzahlen, Feature Engineering
- **Statistik / Simulation** — Monte Carlo, Wahrscheinlichkeitsverteilungen
- **Dashboard** — Streamlit, interaktive Visualisierungen
- **Aktualität** — Projekt läuft live während eines echten Events (WM 2026)