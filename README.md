<div align="center">

# 🏎️ F1 Supply Chain & Race Strategy Optimizer

**A full-stack Operations Research platform for Formula 1 strategy simulation.**  
Built with a custom k-Means clustering model, a Markov Decision Process (MDP) solver, and a Monte Carlo risk engine — all wired to a live React dashboard.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql)](https://www.postgresql.org/)

</div>

---

## 📖 Overview

This project answers a single question an F1 strategy engineer faces on race day:

> *"Given this track's tire degradation profile and pit-lane loss, at exactly which laps should we pit — and how risky is that call if something goes wrong in the pit box?"*

It solves this by chaining four distinct computational phases:

| Phase | What it does |
|---|---|
| **1 — ETL Pipeline** | Fetches lap-by-lap telemetry for every 2023 race via FastF1 and loads it into PostgreSQL |
| **2 — Feature Engineering** | Runs CTE-based SQL to extract per-circuit logistical profiles (baseline lap time, pit-loss delta, tire degradation rate) |
| **3 — k-Means Clustering** | Groups all 22 circuits into 4 logistical archetypes using a from-scratch NumPy k-Means implementation |
| **4 — MDP + Monte Carlo** | Solves a Bellman backward-induction MDP for optimal pit laps; validates the strategy with 1,000 stochastic race simulations |
| **5 — FastAPI Backend** | Exposes the solver as a REST API with live chaos-variable injection |
| **6 — React Dashboard** | Interactive command-center UI with KPI cards, risk-distribution charts, and a track-cluster scatter plot |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  React Frontend  (localhost:3000)                                │
│  App.js ─► Dashboard.jsx ─► KpiCard / Charts (Recharts)         │
│  Proxies /api/* ─────────────────────────────────────────────►   │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼───────────────────────────────────┐
│  FastAPI Backend  (localhost:8000)                               │
│  backend/app.py ─► backend/routes.py                            │
│  GET  /api/tracks/    – 22 circuits with cluster assignments     │
│  POST /api/strategy/  – MDP solve + 1 000 Monte Carlo sims       │
└──────────────┬───────────────────────────────────────────────────┘
               │ Python imports
┌──────────────▼───────────────────────────────────────────────────┐
│  src/models/                                                     │
│    mdp_solver.py     RaceMDP  – Backward Induction (Bellman)     │
│    monte_carlo.py    RaceSimulator – stochastic lap simulation   │
│    kmeans.py         fit_kmeans – pure NumPy k-Means             │
│    feature_extractor.py  CTE SQL → Pandas DataFrame              │
│  backend/track_data.py   22 F1 circuit profiles (static cache)  │
│                                                                  │
│  PostgreSQL  (laps, races tables populated by Phase 1 ETL)       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Project Structure

```
f1-supply-chain-optimizer/
│
├── src/                          # Core Python library
│   ├── data_pipeline/
│   │   ├── fetcher.py            # FastF1 → raw lap DataFrame
│   │   ├── cleaner.py            # Pandas cleaning & type casting
│   │   └── loader.py             # SQLAlchemy ORM → PostgreSQL
│   ├── models/
│   │   ├── feature_extractor.py  # CTE SQL feature engineering
│   │   ├── kmeans.py             # Custom k-Means (NumPy only)
│   │   ├── mdp_solver.py         # RaceMDP – Bellman backward induction
│   │   └── monte_carlo.py        # RaceSimulator – 1 000-run MC
│   └── utils/
│
├── backend/                      # Phase 5 – FastAPI layer
│   ├── app.py                    # FastAPI app + CORS middleware
│   ├── routes.py                 # /api/tracks/ and /api/strategy/
│   ├── track_data.py             # 22 circuit profiles + cluster labels
│   └── requirements.txt
│
├── frontend/                     # Phase 6 – React dashboard
│   ├── src/
│   │   ├── App.js                # Root component, state, sidebar
│   │   ├── index.css             # Dark/light design system (CSS vars)
│   │   ├── api.js                # fetchTracks / computeStrategy
│   │   └── components/
│   │       ├── Dashboard.jsx     # KPI cards, timeline, charts layout
│   │       ├── KpiCard.jsx       # Reusable metric card
│   │       ├── RiskDistributionChart.jsx  # MC overlap area chart
│   │       └── TrackClusterChart.jsx      # k-Means scatter plot
│   └── package.json
│
├── run_pipeline.py               # Phase 1 – Full season ETL runner
├── run_clustering.py             # Phase 3 – k-Means runner (CLI)
├── run_mdp.py                    # Phase 4a – MDP solver (CLI)
├── run_simulation.py             # Phase 4b – Monte Carlo runner (CLI)
├── .env                          # DATABASE_URL (not committed)
└── .venv/                        # Python 3.12 virtual environment
```

---

## ⚙️ The Math

### Phase 3 — k-Means Clustering
Each of the 22 circuits is represented as a 3-feature vector:

```
x = [base_lap_time_ms, pit_loss_ms, tire_deg_ms_per_lap]
```

The from-scratch implementation (`src/models/kmeans.py`) runs:
1. **Z-score normalization** — prevents lap time (large magnitude) from dominating the distance
2. **Random centroid initialization**
3. **Assign step** — Euclidean distance via NumPy broadcasting (no loops)
4. **Update step** — mean of each cluster
5. **Convergence check** — stops when centroid shift < `tol=1e-4`

Circuits are grouped into **4 logistical archetypes**:

| Cluster | Label | Examples |
|---|---|---|
| 0 | Power Circuit | Bahrain, Monza, Jeddah |
| 1 | Technical / Street | Monaco, Hungaroring, Barcelona |
| 2 | Long Pit Lane | Silverstone, Spa, COTA |
| 3 | Extreme Degradation | Suzuka, Zandvoort, Qatar |

### Phase 4a — Race Strategy MDP

**State:** `(lap, tire_age)` — current lap number and age of current tyre set  
**Actions:** `Stay Out` or `Pit`  
**Reward:** negative lap time (we minimise total race time)

The Bellman equation solved via backward induction:

```
V(lap, tire_age) = min(
    cost_stay(tire_age) + V(lap+1, tire_age+1),   # Stay Out
    cost_pit()          + V(lap+1, 1)              # Pit → fresh tyres
)
```

Lap cost models:
```python
cost_stay = base_lap_time + tire_age × deg_penalty   # linear degradation
cost_pit  = base_lap_time + pit_loss                 # immediate time loss
```

### Phase 4b — Monte Carlo Risk Simulation

1,000 stochastic races are simulated for both the **MDP strategy** and a **naive baseline** (evenly-spaced stops):

- **Lap time noise:** `N(0, 300 ms)` — traffic, wind, minor errors  
- **Pit stop noise:** `N(0, 500 ms)` — tyre gun variance  
- **Chaos fumble:** user-configurable probability `p` adds a penalty of `t` ms (defaults: 5%, 5 s)

Output KPIs:
- **Expected Return** — mean total race time across 1,000 runs
- **Risk of Ruin** — % of simulations exceeding `base_lap_time × total_laps × 1.05`
- **Time Delta** — MDP mean minus Baseline mean

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

> **Note:** The ETL pipeline additionally requires `fastf1`, `pandas`, `sqlalchemy`, and `psycopg2-binary`. Install them if you want to run Phase 1–3:
> ```bash
> pip install fastf1 pandas sqlalchemy psycopg2-binary
> ```

### 3. Run the data pipeline *(optional — skip if using static track data)*

```bash
# Phase 1 — Populate PostgreSQL with 2023 season lap data
python run_pipeline.py

# Phase 3 — Run k-Means and view cluster assignments
python run_clustering.py

# Phase 4a — Solve MDP for Bahrain defaults
python run_mdp.py

# Phase 4b — Run 1 000 Monte Carlo simulations
python run_simulation.py
```

### 4. Start the backend

```bash
.venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

API docs available at **http://localhost:8000/docs**

### 5. Start the frontend

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
| **Sidebar — Circuit Selector** | Dropdown of all 22 circuits; selecting a track pre-fills the race parameters from its profile |
| **Sidebar — Race Parameters** | Sliders for Total Laps, Base Lap Time, Pit Lane Loss, Tire Degradation |
| **Sidebar — ⚡ Chaos Variables** | Pit Fumble Probability (0–20%) and Fumble Time (0–10 s) — injected into the Monte Carlo engine |
| **KPI Cards** | Optimal Strategy label, MDP expected race time, Time Delta vs baseline, Risk of Ruin %, Track Cluster |
| **Pit Stop Timeline** | Red chips (MDP) vs blue chips (Baseline) showing each pit lap at a glance |
| **Monte Carlo Chart** | Overlapping area histogram of 1,000 simulated race times with mean reference lines |
| **Track Cluster Map** | Scatter plot of all circuits (Tire Deg × Pit Loss), colour-coded by cluster; selected circuit highlighted |
| **Theme Toggle** | Dark / Light mode; preference persisted in `localStorage` |

---

## 🔌 API Reference

### `GET /api/tracks/`

Returns all 22 circuit profiles with cluster assignments.

```jsonc
// Response
[
  {
    "circuit_name": "Bahrain",
    "cluster": 0,
    "cluster_label": "Power Circuit",
    "base_lap_time_ms": 95000,
    "pit_loss_ms": 24000,
    "tire_deg_ms_per_lap": 200
  },
  ...
]
```

### `POST /api/strategy/`

Solves the MDP and runs Monte Carlo simulations. All time values in **milliseconds**.

```jsonc
// Request body
{
  "track_name": "Bahrain",
  "total_laps": 57,
  "base_lap_time": 95000,
  "pit_loss": 24000,
  "deg_penalty": 200,
  "fumble_probability": 0.05,   // 5%
  "fumble_time_ms": 5000        // 5 s
}

// Response (abbreviated)
{
  "optimal_strategy": [{"lap": 16, "label": "Lap 16: PIT"}, ...],
  "stop_count": 3,
  "mdp_expected_time_s": 5412.7,
  "baseline_expected_time_s": 5413.0,
  "time_delta_s": -0.3,
  "mdp_risk_of_ruin_pct": 0.0,
  "baseline_risk_of_ruin_pct": 0.0,
  "mdp_sim_distribution": [5401.2, 5398.7, ...],     // 1 000 values
  "baseline_sim_distribution": [5410.5, 5415.3, ...]
}
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Data ingestion | FastF1, Pandas |
| Database | PostgreSQL + SQLAlchemy |
| ML / OR models | NumPy (k-Means, MDP, Monte Carlo) |
| Backend API | FastAPI + Uvicorn |
| Frontend framework | React 18 (Create React App) |
| Charts | Recharts 2 |
| Icons | Lucide React |
| Styling | Vanilla CSS (custom properties design system) |

---

## 🗺️ Roadmap

- [ ] Live DB integration — swap `track_data.py` static store for `get_track_features()` once DB is populated
- [ ] k-Means++ initialization for more deterministic cluster assignments
- [ ] Multi-driver strategy comparison (undercut / overcut window)
- [ ] Safety Car probability injection as a Chaos Variable
- [ ] Export strategy PDF report from the dashboard

---

