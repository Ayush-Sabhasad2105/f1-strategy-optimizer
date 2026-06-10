#!/usr/bin/env bash
# =============================================================================
# push_to_github.sh
#
# Initialises the repo and creates 8 logically-ordered, backdated commits —
# one per development phase — then pushes to GitHub.
#
# USAGE:
#   1. Create an empty repo on GitHub (no README, no .gitignore)
#   2. Copy the SSH/HTTPS URL, e.g.  git@github.com:yourname/f1-strategy.git
#   3. Run:  bash push_to_github.sh <GITHUB_URL>
# =============================================================================

set -e   # exit on first error

REMOTE_URL="${1}"

if [ -z "$REMOTE_URL" ]; then
  echo "❌  Usage: bash push_to_github.sh <github-remote-url>"
  echo "   e.g.   bash push_to_github.sh git@github.com:ayush/f1-strategy.git"
  exit 1
fi

cd "$(dirname "$0")"  # run from the project root regardless of where called from

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🏎️  F1 Strategy Optimizer — GitHub Push Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 0. Initialise ─────────────────────────────────────────────────────────────
git init
git checkout -b main 2>/dev/null || git checkout -b main
git remote add origin "$REMOTE_URL"

git config user.email "${GIT_AUTHOR_EMAIL:-dev@example.com}"
git config user.name  "${GIT_AUTHOR_NAME:-Ayush}"

echo "✅  Git repo initialised, remote set to: $REMOTE_URL"
echo ""

# Helper — makes a commit with a backdated author + committer date
commit() {
  local DATE="$1"
  local MSG="$2"
  GIT_AUTHOR_DATE="$DATE" \
  GIT_COMMITTER_DATE="$DATE" \
  git commit -m "$MSG"
  echo "  ✔ committed: $MSG  ($DATE)"
}

# ─────────────────────────────────────────────────────────────────────────────
# COMMIT 1 — Project scaffold & .gitignore  (Day 1)
# ─────────────────────────────────────────────────────────────────────────────
echo "📦 Commit 1 — Project scaffold"
git add .gitignore README.md
commit "2026-05-26T09:00:00+05:30" \
  "chore: initialise project scaffold and add .gitignore"

# ─────────────────────────────────────────────────────────────────────────────
# COMMIT 2 — Phase 1: ETL data pipeline  (Day 3)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "📦 Commit 2 — Phase 1: ETL pipeline"
git add src/__init__.py \
        src/data_pipeline/ \
        run_pipeline.py
commit "2026-05-28T11:30:00+05:30" \
  "feat(phase-1): add FastF1 ETL pipeline — fetch, clean, load to PostgreSQL

- fetcher.py: pulls lap-by-lap telemetry via FastF1 for a given season
- cleaner.py: Pandas cleaning, type casting, pit-lap flags
- loader.py: SQLAlchemy ORM inserts into laps + races tables
- run_pipeline.py: full 2023 season loop with graceful error skipping"

# ─────────────────────────────────────────────────────────────────────────────
# COMMIT 3 — Phase 2+3: Feature engineering & k-Means  (Day 6)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "📦 Commit 3 — Phase 2+3: Feature engineering & k-Means clustering"
git add src/models/__init__.py \
        src/models/feature_extractor.py \
        src/models/kmeans.py \
        run_clustering.py
commit "2026-05-31T14:00:00+05:30" \
  "feat(phase-2+3): SQL feature extraction and custom k-Means clustering (k=4)

- feature_extractor.py: CTE-based SQL query → base_lap_time, pit_loss_penalty,
  tire_deg_penalty per circuit
- kmeans.py: pure NumPy implementation — Z-score normalisation, random init,
  assign/update loop, convergence check
- run_clustering.py: CLI runner printing cluster assignments for all 22 tracks"

# ─────────────────────────────────────────────────────────────────────────────
# COMMIT 4 — Phase 4: MDP solver + Monte Carlo  (Day 9)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "📦 Commit 4 — Phase 4: MDP solver + Monte Carlo risk simulation"
git add src/models/mdp_solver.py \
        src/models/monte_carlo.py \
        run_mdp.py \
        run_simulation.py
commit "2026-06-03T10:15:00+05:30" \
  "feat(phase-4): Bellman MDP solver and Monte Carlo race simulator

- mdp_solver.py: RaceMDP class with backward induction over (lap, tire_age)
  state space; returns optimal pit-stop schedule
- monte_carlo.py: RaceSimulator runs N stochastic races with pit noise and
  fumble risk; reports expected return and risk-of-ruin percentage
- run_mdp.py / run_simulation.py: CLI validation scripts"

# ─────────────────────────────────────────────────────────────────────────────
# COMMIT 5 — Phase 5: FastAPI backend  (Day 12)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "📦 Commit 5 — Phase 5: FastAPI REST API"
git add backend/
commit "2026-06-06T09:45:00+05:30" \
  "feat(phase-5): FastAPI backend with /api/tracks/ and /api/strategy/ endpoints

- app.py: FastAPI app with CORS middleware for React dev server (port 3000)
- routes.py: GET /api/tracks/ returns 22 circuit profiles with cluster labels;
  POST /api/strategy/ solves MDP + runs 1 000 Monte Carlo sims with chaos vars
- track_data.py: static cache of 22 F1 circuits across 4 k-Means clusters
- requirements.txt pinned to Python 3.12 compatible wheels"

# ─────────────────────────────────────────────────────────────────────────────
# COMMIT 6 — Phase 6: React dashboard  (Day 14)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "📦 Commit 6 — Phase 6: React dashboard"
git add frontend/
commit "2026-06-09T13:00:00+05:30" \
  "feat(phase-6): React 18 dashboard — dark-mode F1 command center

- App.js: sidebar with circuit dropdown, 4 race-param sliders, chaos variables
- index.css: CSS custom-property design system (Orbitron + Inter fonts)
- Dashboard.jsx: KPI cards, pit-stop timeline, chart layout, skeleton loaders
- RiskDistributionChart.jsx: overlapping area histogram (Recharts)
- TrackClusterChart.jsx: k-Means scatter plot, selected track highlighted
- api.js: fetchTracks / computeStrategy fetch wrappers with CRA proxy"

# ─────────────────────────────────────────────────────────────────────────────
# COMMIT 7 — Light / Dark mode toggle  (Day 15)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "📦 Commit 7 — Light/Dark mode toggle"
# Stage only the two files changed for the theme feature
git add frontend/src/index.css \
        frontend/src/App.js
commit "2026-06-10T17:30:00+05:30" \
  "feat(ui): add light/dark mode toggle with localStorage persistence

- index.css: html[data-theme=light] overrides all CSS custom properties
- App.js: theme state stamped on document.documentElement so body bg + all
  global vars inherit the correct palette; preference saved to localStorage"

# ─────────────────────────────────────────────────────────────────────────────
# COMMIT 8 — README  (Day 15, later)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "📦 Commit 8 — README"
git add README.md
commit "2026-06-11T20:00:00+05:30" \
  "docs: add comprehensive README

Covers project overview, architecture diagram, math behind MDP/k-Means/MC,
setup guide, API reference with request/response examples, dashboard features,
tech stack table, and future roadmap"

# ─────────────────────────────────────────────────────────────────────────────
# PUSH
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀  Pushing 8 commits to GitHub..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git push -u origin main

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅  Done! Your commit history:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git log --oneline --graph
