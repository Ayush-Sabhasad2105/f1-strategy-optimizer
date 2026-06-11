# backend/routes.py
import sys
import os
import numpy as np

# Ensure the project root is on the path so src.models is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from src.models.mdp_solver import RaceMDP
from src.models.monte_carlo import RaceSimulator
from backend.track_data import TRACK_PROFILES, CLUSTER_LABELS

router = APIRouter(prefix="/api")


# ─── Request / Response Schemas ────────────────────────────────────────────────

class StrategyRequest(BaseModel):
    track_name: str = Field(..., example="Bahrain")
    total_laps: int = Field(57, ge=20, le=80, example=57)
    base_lap_time: int = Field(
        95000, ge=50000, le=200000,
        description="Baseline lap time in milliseconds", example=95000
    )
    pit_loss: int = Field(
        24000, ge=10000, le=60000,
        description="Pit-lane delta in milliseconds", example=24000
    )
    deg_penalty: int = Field(
        200, ge=50, le=800,
        description="Lap-time loss per lap of tire age (ms)", example=200
    )
    # ── Classic Chaos Variables ─────────────────────────────────────────────
    fumble_probability: float = Field(
        0.05, ge=0.0, le=0.20,
        description="Probability of a catastrophic pit fumble (0-20%)"
    )
    fumble_time_ms: int = Field(
        5000, ge=0, le=10000,
        description="Extra time added when a fumble occurs (ms)"
    )
    # ── V2.0 Elite Strategy Variables ──────────────────────────────────────
    sc_probability: float = Field(
        0.02, ge=0.0, le=0.10,
        description="Probability per lap that a Safety Car is deployed (0-10%)"
    )
    traffic_penalty: int = Field(
        1500, ge=0, le=3000,
        description="Dirty-air time penalty per lap while running in traffic (ms)"
    )


class PitStopEvent(BaseModel):
    lap: int
    label: str


class StrategyResponse(BaseModel):
    track_name: str
    cluster: int
    cluster_label: str
    optimal_strategy: List[PitStopEvent]
    stop_count: int
    baseline_strategy: List[PitStopEvent]
    # ── KPI values ──────────────────────────────────────────────────────────
    mdp_expected_time_s: float
    baseline_expected_time_s: float
    time_delta_s: float
    winner: str                        # "MDP" | "Baseline" | "Tie"
    mdp_risk_of_ruin_pct: float
    baseline_risk_of_ruin_pct: float
    ruin_delta_pct: float              # baseline_ruin - mdp_ruin (positive = MDP safer)
    # ── Chart data (10 000 simulations) ────────────────────────────────────
    mdp_sim_distribution: List[float]
    baseline_sim_distribution: List[float]


class TrackInfo(BaseModel):
    circuit_name: str
    cluster: int
    cluster_label: str
    base_lap_time_ms: int
    pit_loss_ms: int
    tire_deg_ms_per_lap: int


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_track(track_name: str) -> dict:
    """Case-insensitive lookup of a track profile by name."""
    for t in TRACK_PROFILES:
        if t["circuit_name"].lower() == track_name.lower():
            return t
    return None


def _build_baseline_strategy(total_laps: int, stop_count: int) -> List[int]:
    """
    Constructs a naive evenly-spaced baseline pit schedule with the same
    number of stops as the MDP strategy. Guarantees at least 1 stop.
    """
    stops = max(stop_count, 1)
    interval = total_laps // (stops + 1)
    return [interval * (i + 1) for i in range(stops)]


def _parse_optimal_pit_laps(strategy_strings: List[str]) -> List[int]:
    """Parses 'Lap X: PIT' strings into a list of integer lap numbers."""
    laps = []
    for s in strategy_strings:
        try:
            lap_num = int(s.split(" ")[1].rstrip(":"))
            laps.append(lap_num)
        except (IndexError, ValueError):
            pass
    return laps


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/tracks/", response_model=List[TrackInfo], tags=["Tracks"])
def get_tracks():
    """
    Returns all available F1 circuit profiles with their k-Means cluster
    assignments (0-3) and key logistical features.
    """
    return [
        TrackInfo(
            circuit_name=t["circuit_name"],
            cluster=t["cluster"],
            cluster_label=CLUSTER_LABELS[t["cluster"]],
            base_lap_time_ms=t["base_lap_time_ms"],
            pit_loss_ms=t["pit_loss_ms"],
            tire_deg_ms_per_lap=t["tire_deg_ms_per_lap"],
        )
        for t in TRACK_PROFILES
    ]


@router.post("/strategy/", response_model=StrategyResponse, tags=["Strategy"])
def compute_strategy(req: StrategyRequest):
    """
    Runs the full F1 v2.0 strategy pipeline:
    1. Solves the 3D MDP (lap × tire_age × traffic_laps) via backward induction.
       The `traffic_penalty` drives how aggressively the MDP avoids pit-outs.
    2. Constructs an evenly-spaced baseline with the same stop count.
    3. Runs 10,000 Monte Carlo simulations for each strategy, injecting:
       - Safety Car probability (sc_probability) and stochastic SC duration
       - Pit fumble probability and fumble time
       - Dirty-air penalty (traffic_penalty) after each pit stop (3-lap window)
    Returns KPI metrics, a winner verdict, dual Risk-of-Ruin figures, and raw
    simulation distributions for the risk chart.
    """

    # ── Track context ────────────────────────────────────────────────────────
    track_info = _get_track(req.track_name)
    cluster_id    = track_info["cluster"] if track_info else 0
    cluster_label = CLUSTER_LABELS.get(cluster_id, "Unknown")

    # ── Step 1: Solve 3D MDP ─────────────────────────────────────────────────
    mdp = RaceMDP(
        total_laps=req.total_laps,
        base_lap_time=req.base_lap_time,
        pit_loss=req.pit_loss,
        deg_penalty_per_lap=req.deg_penalty,
    )
    # Inject V2.0 traffic penalty into the MDP before solving
    mdp.traffic_penalty = req.traffic_penalty
    mdp.solve()
    strategy_strings = mdp.get_optimal_strategy()

    optimal_pit_laps = _parse_optimal_pit_laps(strategy_strings)
    stop_count       = len(optimal_pit_laps)
    optimal_events   = [PitStopEvent(lap=lap, label=f"Lap {lap}: PIT") for lap in optimal_pit_laps]

    # ── Step 2: Baseline ─────────────────────────────────────────────────────
    baseline_pit_laps = _build_baseline_strategy(req.total_laps, stop_count)
    baseline_events   = [PitStopEvent(lap=lap, label=f"Lap {lap}: PIT") for lap in baseline_pit_laps]

    # ── Step 3: 10 000 Monte Carlo Simulations ───────────────────────────────
    # Capture all user-controllable variables in the closure.
    sc_prob      = req.sc_probability
    traffic_pen  = req.traffic_penalty
    fumble_prob  = req.fumble_probability
    fumble_time  = req.fumble_time_ms

    def _simulate(pit_laps: set) -> float:
        """
        Full stochastic single-race simulation (V2.0):
          - Safety Car: deploys with `sc_prob` chance per lap; lasts 2-5 laps.
            SC laps are neutralised (+25 s); pitstops under SC cost half.
          - Dirty air: 3-lap traffic window after each pit stop; adds
            N(traffic_pen, traffic_pen*0.33) ms per affected lap.
          - Fumble risk: per pit stop, `fumble_prob` chance adds `fumble_time` ms.
          - Normal noise: N(0,300) ms per racing lap; N(0,500) ms pit variance.
        """
        total_time     = 0
        tire_age       = 0
        in_traffic     = 0   # laps of dirty-air remaining
        sc_active      = False
        sc_remaining   = 0

        for lap in range(1, req.total_laps + 1):
            # Safety Car trigger
            if not sc_active and np.random.random() < sc_prob:
                sc_active    = True
                sc_remaining = int(np.random.randint(2, 6))

            if sc_active:
                sc_remaining -= 1
                if sc_remaining <= 0:
                    sc_active = False

            if lap in pit_laps:
                pit_variance = np.random.normal(0, 500)
                fumble_pen   = fumble_time if np.random.random() < fumble_prob else 0
                # SC discount: pitstop under SC costs half the pit-lane delta
                effective_pit = (req.pit_loss / 2) if sc_active else req.pit_loss
                lap_time     = req.base_lap_time + effective_pit + pit_variance + fumble_pen
                tire_age     = 1
                in_traffic   = 3   # emerge into dirty air for 3 laps
            else:
                traffic_noise = np.random.normal(0, 300)
                dirty_air = (
                    np.random.normal(traffic_pen, traffic_pen * 0.33)
                    if in_traffic > 0 else 0
                )
                if in_traffic > 0:
                    in_traffic -= 1
                # SC neutralisation: laps under SC run at a fixed slow pace
                sc_penalty = 25000 if sc_active else 0
                lap_time = (
                    req.base_lap_time
                    + (tire_age * req.deg_penalty)
                    + traffic_noise
                    + dirty_air
                    + sc_penalty
                )
                tire_age += 1

            total_time += lap_time

        return total_time

    N = 10_000
    mdp_laps      = set(optimal_pit_laps)
    baseline_laps = set(baseline_pit_laps)

    mdp_results      = [_simulate(mdp_laps)      for _ in range(N)]
    baseline_results = [_simulate(baseline_laps) for _ in range(N)]

    # Ruin threshold: 5% over the theoretical clean-race minimum
    theoretical_min = req.base_lap_time * req.total_laps
    ruin_threshold  = theoretical_min * 1.05

    mdp_ruin      = (sum(1 for r in mdp_results      if r > ruin_threshold) / N) * 100
    baseline_ruin = (sum(1 for r in baseline_results if r > ruin_threshold) / N) * 100

    mdp_avg_s      = float(np.mean(mdp_results))      / 1000.0
    baseline_avg_s = float(np.mean(baseline_results)) / 1000.0
    time_delta_s   = round(baseline_avg_s - mdp_avg_s, 3)  # positive = MDP faster

    # Winner verdict
    THRESHOLD = 0.5  # < 0.5 s difference is a statistical tie
    if abs(time_delta_s) < THRESHOLD:
        winner = "Tie"
    elif time_delta_s > 0:
        winner = "MDP"
    else:
        winner = "Baseline"

    return StrategyResponse(
        track_name=req.track_name,
        cluster=cluster_id,
        cluster_label=cluster_label,
        optimal_strategy=optimal_events,
        stop_count=stop_count,
        baseline_strategy=baseline_events,
        mdp_expected_time_s=round(mdp_avg_s, 3),
        baseline_expected_time_s=round(baseline_avg_s, 3),
        time_delta_s=time_delta_s,
        winner=winner,
        mdp_risk_of_ruin_pct=round(mdp_ruin, 2),
        baseline_risk_of_ruin_pct=round(baseline_ruin, 2),
        ruin_delta_pct=round(baseline_ruin - mdp_ruin, 2),
        mdp_sim_distribution=[round(r / 1000.0, 3) for r in mdp_results],
        baseline_sim_distribution=[round(r / 1000.0, 3) for r in baseline_results],
    )
