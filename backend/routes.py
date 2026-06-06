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
from typing import List

from src.models.mdp_solver import RaceMDP
from src.models.monte_carlo import RaceSimulator
from backend.track_data import TRACK_PROFILES, CLUSTER_LABELS

router = APIRouter(prefix="/api")


# ─── Request / Response Schemas ────────────────────────────────────────────────

class StrategyRequest(BaseModel):
    track_name: str = Field(..., example="Bahrain")
    total_laps: int = Field(57, ge=20, le=80, example=57)
    base_lap_time: int = Field(95000, ge=50000, le=200000, description="Baseline lap time in milliseconds", example=95000)
    pit_loss: int = Field(24000, ge=10000, le=60000, description="Pit-lane delta in milliseconds", example=24000)
    deg_penalty: int = Field(200, ge=50, le=800, description="Lap-time loss per lap of tire age (ms)", example=200)
    # Chaos Variables
    fumble_probability: float = Field(0.05, ge=0.0, le=0.20, description="Probability of a catastrophic pit fumble (0-20%)")
    fumble_time_ms: int = Field(5000, ge=0, le=10000, description="Extra time added when a fumble occurs (ms)")


class PitStopEvent(BaseModel):
    lap: int
    label: str


class SimDataPoint(BaseModel):
    race_time_s: float


class StrategyResponse(BaseModel):
    track_name: str
    cluster: int
    cluster_label: str
    optimal_strategy: List[PitStopEvent]
    stop_count: int
    baseline_strategy: List[PitStopEvent]
    # KPI values
    mdp_expected_time_s: float
    baseline_expected_time_s: float
    time_delta_s: float
    mdp_risk_of_ruin_pct: float
    baseline_risk_of_ruin_pct: float
    # Chart data
    mdp_sim_distribution: List[float]       # raw race times in seconds (1000 simulations)
    baseline_sim_distribution: List[float]  # raw race times in seconds (1000 simulations)


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
    Constructs a naive evenly-spaced baseline pit schedule
    with the same number of stops as the MDP strategy.
    Ensures at least a 1-stop baseline if MDP returns 0 stops.
    """
    stops = max(stop_count, 1)
    interval = total_laps // (stops + 1)
    return [interval * (i + 1) for i in range(stops)]


def _parse_optimal_pit_laps(strategy_strings: List[str]) -> List[int]:
    """Parses 'Lap X: PIT' strings into a list of integer lap numbers."""
    laps = []
    for s in strategy_strings:
        # Format: "Lap 16: PIT"
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
    Runs the full F1 strategy pipeline for a given track and parameters:
    1. Solves the MDP via backward induction to find optimal pit stops.
    2. Constructs a naive evenly-spaced baseline with the same stop count.
    3. Runs 1000 Monte Carlo simulations for each strategy.
    Returns KPI metrics and raw simulation distributions for charting.
    """

    # Look up cluster info (non-blocking — user params drive the solver)
    track_info = _get_track(req.track_name)
    cluster_id = track_info["cluster"] if track_info else 0
    cluster_label = CLUSTER_LABELS.get(cluster_id, "Unknown")

    # ── Step 1: Solve MDP ───────────────────────────────────────────────────
    mdp = RaceMDP(
        total_laps=req.total_laps,
        base_lap_time=req.base_lap_time,
        pit_loss=req.pit_loss,
        deg_penalty_per_lap=req.deg_penalty,
    )
    mdp.solve()
    strategy_strings = mdp.get_optimal_strategy()

    optimal_pit_laps = _parse_optimal_pit_laps(strategy_strings)
    stop_count = len(optimal_pit_laps)

    optimal_events = [PitStopEvent(lap=lap, label=f"Lap {lap}: PIT") for lap in optimal_pit_laps]

    # ── Step 2: Baseline Strategy ───────────────────────────────────────────
    baseline_pit_laps = _build_baseline_strategy(req.total_laps, stop_count)
    baseline_events = [PitStopEvent(lap=lap, label=f"Lap {lap}: PIT") for lap in baseline_pit_laps]

    # ── Step 3: Monte Carlo Simulations ────────────────────────────────────
    # Patch in the user-supplied chaos variables for this run
    simulator = RaceSimulator(
        total_laps=req.total_laps,
        base_lap_time=req.base_lap_time,
        pit_loss_mean=req.pit_loss,
        deg_penalty=req.deg_penalty,
    )

    # Override the stochastic parameters via monkey-patching so we don't alter
    # the core class signature
    fumble_prob = req.fumble_probability
    fumble_time = req.fumble_time_ms

    def _simulate_with_chaos(pit_laps):
        """Inner simulator that respects the user's chaos sliders."""
        total_time = 0
        tire_age = 0
        for lap in range(1, req.total_laps + 1):
            if lap in pit_laps:
                pit_variance = np.random.normal(0, 500)
                fumble_penalty = fumble_time if np.random.random() < fumble_prob else 0
                lap_time = req.base_lap_time + req.pit_loss + pit_variance + fumble_penalty
                tire_age = 1
            else:
                traffic_noise = np.random.normal(0, 300)
                lap_time = req.base_lap_time + (tire_age * req.deg_penalty) + traffic_noise
                tire_age += 1
            total_time += lap_time
        return total_time

    N = 1000
    mdp_results = [_simulate_with_chaos(set(optimal_pit_laps)) for _ in range(N)]
    baseline_results = [_simulate_with_chaos(set(baseline_pit_laps)) for _ in range(N)]

    # Ruin threshold: anything beyond 5% over the theoretical minimum is "ruin"
    theoretical_min = req.base_lap_time * req.total_laps
    ruin_threshold = theoretical_min * 1.05

    mdp_ruin = (sum(1 for r in mdp_results if r > ruin_threshold) / N) * 100
    baseline_ruin = (sum(1 for r in baseline_results if r > ruin_threshold) / N) * 100

    mdp_avg_s = float(np.mean(mdp_results)) / 1000.0
    baseline_avg_s = float(np.mean(baseline_results)) / 1000.0
    time_delta_s = round(baseline_avg_s - mdp_avg_s, 3)

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
        mdp_risk_of_ruin_pct=round(mdp_ruin, 2),
        baseline_risk_of_ruin_pct=round(baseline_ruin, 2),
        mdp_sim_distribution=[round(r / 1000.0, 3) for r in mdp_results],
        baseline_sim_distribution=[round(r / 1000.0, 3) for r in baseline_results],
    )
