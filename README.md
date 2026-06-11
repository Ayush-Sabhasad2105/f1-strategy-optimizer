<div align="center">

# 🏎️ F1 Supply Chain & Race Strategy Optimizer (V3.0)

**A full-stack Operations Research platform for Formula 1 strategy simulation.**  
Built with a custom k-Means clustering model, a 3D Markov Decision Process (MDP) solver, and a 10,000-run Monte Carlo risk engine — all wired to a live React dashboard featuring a Reactive AI vs Static Baseline showdown.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql)](https://www.postgresql.org/)

</div>

---

## 📖 Overview

This project answers a single question an F1 strategy engineer faces on race day:

> *"Given this track's tire degradation profile, pit-lane loss, and stochastic race conditions (Safety Cars, dirty air), exactly when should we pit — and is our Reactive AI safer than a Static human baseline?"*

It solves this by chaining four distinct computational phases:

| Phase | What it does |
|---|---|
| **1 — ETL Pipeline** | Fetches lap-by-lap telemetry for every 2023 race via FastF1 and loads it into PostgreSQL |
| **2 — Feature Engineering** | Runs CTE-based SQL to extract per-circuit logistical profiles (baseline lap time, pit-loss delta, tire degradation rate) |
| **3 — k-Means Clustering** | Groups all 22 circuits into 4 logistical archetypes using a from-scratch NumPy k-Means implementation |
| **4 — 3D MDP + Monte Carlo** | Solves a Bellman backward-induction MDP (lap × tire_age × traffic) for dynamic pit decisions; runs 10,000 stochastic race simulations pitting the AI against a static baseline |
| **5 — FastAPI Backend** | Exposes the solver as a REST API with live stochastic race condition parameters |
| **6 — React Dashboard** | Interactive command-center UI with a Winner Verdict banner, dual risk panels, dynamic lap labels, and a track-cluster scatter plot |

---

## 🏗️ Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│  React Frontend  (localhost:3000)                                │
│  App.js ─► Dashboard.jsx ─► DualRuinPanel / RiskCharts          │
│  Proxies /api/* ─────────────────────────────────────────────►   │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼───────────────────────────────────┐
│  FastAPI Backend  (localhost:8000)                               │
│  backend/app.py ─► backend/routes.py                            │
│  GET  /api/tracks/    – 22 circuits with cluster & total laps    │
│  POST /api/strategy/  – MDP solve + dual 10k Monte Carlo sims    │
└──────────────┬───────────────────────────────────────────────────┘
               │ Python imports
┌──────────────▼───────────────────────────────────────────────────┐
│  src/models/                                                     │
│    mdp_solver.py     RaceMDP  – 3D Backward Induction (Bellman)  │
│    monte_carlo.py    RaceSimulator – stochastic live simulation  │
│    kmeans.py         fit_kmeans – pure NumPy k-Means             │
│    feature_extractor.py  CTE SQL → Pandas DataFrame              │
│  backend/track_data.py   22 F1 circuit profiles (static cache)  │
│                                                                  │
│  PostgreSQL  (laps, races tables populated by Phase 1 ETL)       │
└──────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ The Math

### Phase 3 — k-Means Clustering
Each of the 22 circuits is represented as a 3-feature vector:

```text
x = [base_lap_time_ms, pit_loss_ms, tire_deg_ms_per_lap]
```

Circuits are grouped into **4 logistical archetypes** (e.g. Power, Technical, Long Pit Lane, Extreme Deg) to inform macro-level strategy decisions.

### Phase 4a — Race Strategy 3D MDP

The V3.0 engine upgraded the MDP from a 2D state space to a 3D matrix to mathematically avoid "Dirty Air" (traffic).

**State:** `(lap, tire_age, traffic_laps)`  
**Actions:** `Stay Out` or `Pit`  
**Reward:** negative lap time (minimizing total race time)

Pitting incurs pit loss but resets `tire_age` to 1 and forces `traffic_laps` to 3 (you drop into the pack). Staying out linearly degrades tires and adds a "dirty air penalty" if `traffic_laps > 0`.

### Phase 4b — Monte Carlo Risk Simulation

**10,000 stochastic races** are simulated in parallel to compare:
1. **Reactive AI**: Queries the 3D MDP policy matrix on every lap. If a Safety Car (SC) deploys and tires are old (`> 10 laps`), it uses Plan B logic to take a cheap pit stop.
2. **Static Baseline**: Uses a predetermined, evenly-spaced 2-stop strategy dynamically derived from `total_laps` and the user's `starting_tire` choice. It *cannot* react to Safety Cars.

**Stochastic Injection:**
- Lap time noise: `N(0, 300 ms)`
- Pit stop noise & fumbles: `N(0, 500 ms)`, 5% chance of 5s fumble
- SC Deployments: User-controlled probability slider (defaults to 2% per lap)
- Traffic Penalty: User-controlled dirty air multiplier

---

## 🚀 Getting Started

### Prerequisites

| Tool | Version |
|---|---|
| Python | **3.12** (3.14 is too new for `pydantic-core`) |
| Node.js | 18+ |
| PostgreSQL | 14+ |

### 1. Clone & configure

```bash
git clone <your-repo-url>
cd f1-supply-chain-optimizer

# Copy and fill in your DB connection string
cp .env.example .env
# Edit .env → DATABASE_URL=postgresql://user:password@localhost:5432/f1_supply_chain
```

### 2. Python environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 3. Run the servers

**Start the FastAPI Backend:**
```bash
.venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```
API docs available at **http://localhost:8000/docs**

**Start the React Frontend:**
```bash
cd frontend
npm install
npm start
```
Dashboard opens at **http://localhost:3000**

---

## 🖥️ Dashboard Features

| Section | Description |
|---|---|
| **Circuit Selector** | Dropdown of 22 circuits; automatically hydrates lap counts and logistical defaults |
| **Race Parameters** | Sliders for Base Lap Time, Pit Loss, Tire Deg, and a dropdown for **Starting Tire** (Soft/Medium/Hard) |
| **V3.0 Race Conditions** | Sliders for Safety Car Probability and Dirty Air Penalty to stress-test the simulation |
| **Winner Verdict Banner** | Highlights whether the Reactive AI or the Static Baseline statistically won the 10,000 sims (or tied < 0.5s) |
| **Dual Risk Panel** | Side-by-side Risk of Ruin percentages with animated bars and an explicit "ΔRuin" pill |
| **Monte Carlo Chart** | Overlapping Recharts histogram showing the right-skewed SC tail effect for the Static strategy |
| **Track Cluster Map** | Scatter plot of all circuits (Tire Deg × Pit Loss), color-coded by k-Means cluster |

---

## 🔌 API Reference

### `GET /api/tracks/`

Returns all 22 circuit profiles with cluster assignments and official `total_laps`.

### `POST /api/strategy/`

Solves the 3D MDP and runs 10,000 parallel Monte Carlo simulations for both AI and Static strategies.

```jsonc
// Request body (V3.0)
{
  "track_name": "Bahrain",
  "total_laps": 57,
  "base_lap_time": 95000,
  "pit_loss": 24000,
  "deg_penalty": 200,
  "sc_probability": 0.02,
  "traffic_penalty": 1500,
  "starting_tire": "Medium"
}

// Response (V3.0 abbreviated)
{
  "track_name": "Bahrain",
  "starting_tire": "Medium",
  "ai_expected_time_s": 5412.7,
  "ai_risk_of_ruin_pct": 2.1,
  "ai_sim_distribution": [5401.2, 5398.7, ...],  // 10k values
  "static_expected_time_s": 5418.0,
  "static_risk_of_ruin_pct": 8.4,
  "static_sim_distribution": [5410.5, 5415.3, ...],
  "time_advantage_s": 5.3,
  "risk_reduction_pct": 6.3,
  "winner": "AI",
  "baseline_laps": [19, 38], // Dynamically generated based on starting_tire
  "mdp_reference_strategy": [...]
}
```

---

## 🗺️ Roadmap

- [x] Integrate Safety Car probability as a stochastic input
- [x] Upgrade to 3D MDP for "Dirty Air" traffic dodging
- [x] Multi-driver / compound dynamic baselines (`starting_tire` injection)
- [ ] Containerize with Docker and `docker-compose` for easier deployment
- [ ] Move the 20,000 Monte Carlo loops to a Celery/Redis background task queue
- [ ] Live DB integration — swap `track_data.py` static store for `get_track_features()`

---
