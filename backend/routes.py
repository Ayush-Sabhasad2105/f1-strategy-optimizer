# backend/routes.py
import sys
import os
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from src.models.mdp_solver import RaceMDP
from src.models.monte_carlo import RaceSimulator
from backend.database import get_all_track_profiles, get_track_profile

router = APIRouter(prefix="/api")


# ─── Schemas ───────────────────────────────────────────────────────────────────

class StrategyRequest(BaseModel):
    track_name:      str   = Field(...,   example="Bahrain Grand Prix")
    total_laps:      int   = Field(57,    ge=20,    le=80)
    base_lap_time:   int   = Field(95000, ge=50000, le=200000,
                                   description="Baseline lap time in ms")
    pit_loss:        int   = Field(24000, ge=10000, le=60000,
                                   description="Pit-lane delta in ms")
    deg_penalty:     int   = Field(200,   ge=10,    le=800,
                                   description="Tire deg per lap in ms")
    sc_probability:  float = Field(0.02,  ge=0.0,   le=0.10,
                                   description="Safety Car probability per lap (0–10%)")
    traffic_penalty: int   = Field(1500,  ge=0,     le=3000,
                                   description="Dirty-air penalty per lap in ms")
    starting_tire:   str   = Field("Medium", description="Soft, Medium, or Hard")


class PitStopEvent(BaseModel):
    lap:   int
    label: str


class StrategyResponse(BaseModel):
    track_name:    str
    cluster:       int
    cluster_label: str
    starting_tire: str
    data_points:   Optional[int] = None      # ← how many laps powered this profile

    # ── Reactive AI ──────────────────────────────────────────────────────────
    ai_expected_time_s:   float
    ai_risk_of_ruin_pct:  float
    ai_sim_distribution:  List[float]

    # ── Static Baseline ───────────────────────────────────────────────────────
    static_expected_time_s:   float
    static_risk_of_ruin_pct:  float
    static_sim_distribution:  List[float]

    # ── Advantage metrics ─────────────────────────────────────────────────────
    time_advantage_s:   float
    risk_reduction_pct: float
    winner:             str

    # ── MDP trace & dynamic baseline ─────────────────────────────────────────
    mdp_reference_strategy: List[PitStopEvent]
    baseline_laps:          List[int]


class TrackInfo(BaseModel):
    circuit_name:        str
    cluster:             int
    cluster_label:       str
    total_laps:          int
    base_lap_time_ms:    int
    pit_loss_ms:         int
    tire_deg_ms_per_lap: int
    data_points:         Optional[int] = None
    last_updated:        Optional[str] = None


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _parse_pit_laps(strategy_strings: List[str]) -> List[int]:
    laps = []
    for s in strategy_strings:
        try:
            laps.append(int(s.split(" ")[1].rstrip(":")))
        except (IndexError, ValueError):
            pass
    return laps


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/tracks/", response_model=List[TrackInfo], tags=["Tracks"])
def get_tracks():
    """Returns all circuit profiles from the live PostgreSQL database.

    Data source: track_profiles table, populated by feature_extractor.py
    using 7 years of FastF1 telemetry (2019–2025, excl. 2020).
    k-Means (k=4) cluster assignments are recalculated on each pipeline run.
    """
    rows = get_all_track_profiles()
    if not rows:
        raise HTTPException(
            status_code=503,
            detail="track_profiles table is empty. Run python run_pipeline.py first."
        )
    return [
        TrackInfo(
            circuit_name=r["circuit_name"],
            cluster=r["cluster"],
            cluster_label=r["cluster_label"],
            total_laps=r["total_laps"],
            base_lap_time_ms=r["base_lap_time_ms"],
            pit_loss_ms=r["pit_loss_ms"],
            tire_deg_ms_per_lap=r["tire_deg_ms_per_lap"],
            data_points=r.get("data_points"),
            last_updated=str(r["last_updated"]) if r.get("last_updated") else None,
        )
        for r in rows
    ]


@router.post("/strategy/", response_model=StrategyResponse, tags=["Strategy"])
def compute_strategy(req: StrategyRequest):
    # ── Track context: pull live from DB ─────────────────────────────────────
    track_row = get_track_profile(req.track_name)

    if track_row:
        # Override user-submitted params with DB-sourced ground-truth values
        pit_loss    = track_row["pit_loss_ms"]
        deg_penalty = track_row["tire_deg_ms_per_lap"]
        cluster_id    = track_row["cluster"]
        cluster_label = track_row["cluster_label"]
        data_points   = track_row.get("data_points")
    else:
        # Graceful fallback: use whatever the user submitted
        pit_loss      = req.pit_loss
        deg_penalty   = req.deg_penalty
        cluster_id    = 0
        cluster_label = "Unknown (not in DB)"
        data_points   = None

    base_lap_time = req.base_lap_time   # kept user-editable for scenario testing

    # ── Step 1: Solve 3D MDP ─────────────────────────────────────────────────
    mdp = RaceMDP(
        total_laps=req.total_laps,
        base_lap_time=base_lap_time,
        pit_loss=pit_loss,
        deg_penalty=deg_penalty,
        starting_compound=req.starting_tire,
    )
    mdp.traffic_penalty = req.traffic_penalty
    mdp.solve()

    ref_strings  = mdp.get_optimal_strategy()
    ref_pit_laps = _parse_pit_laps(ref_strings)
    ref_events   = [PitStopEvent(lap=l, label=f"Lap {l}: PIT") for l in ref_pit_laps]

    # ── Step 2: Build simulator ───────────────────────────────────────────────
    simulator = RaceSimulator(
        total_laps=req.total_laps,
        base_lap_time=base_lap_time,
        pit_loss_mean=pit_loss,
        deg_penalty=deg_penalty,
    )

    sc_prob     = req.sc_probability
    traffic_pen = req.traffic_penalty

    def _patched_simulate(mdp_policy=None, static_pit_laps=None):
        total_time   = 0
        tire_age     = 0
        in_traffic   = 0
        sc_active    = False
        sc_remaining = 0
        has_pitted   = False

        for lap in range(1, req.total_laps + 1):
            if not sc_active and np.random.random() < sc_prob:
                sc_active    = True
                sc_remaining = int(np.random.randint(2, 6))
            if sc_active:
                sc_remaining -= 1
                if sc_remaining <= 0:
                    sc_active = False

            is_pitting = False
            if mdp_policy is not None:
                safe_age     = min(tire_age, req.total_laps)
                safe_traffic = min(in_traffic, 3)
                action_code  = mdp_policy[lap - 1, safe_age, safe_traffic]
                if sc_active and tire_age > 10:
                    is_pitting = True
                else:
                    is_pitting = (action_code == 1)
            elif static_pit_laps is not None:
                is_pitting = (lap in static_pit_laps)

            if is_pitting:
                pit_var   = np.random.normal(0, 500)
                fumble    = 5000 if np.random.random() < 0.05 else 0
                pit_delta = (pit_loss / 2) if sc_active else pit_loss
                
                # Calculate lap cost for the pit lap
                lap_time  = base_lap_time + pit_delta + pit_var + fumble
                tire_age  = 1
                in_traffic = 3
                has_pitted = True
            else:
                noise     = np.random.normal(0, 300)
                dirty_air = (
                    np.random.normal(traffic_pen, traffic_pen * 0.33)
                    if in_traffic > 0 else 0
                )
                if in_traffic > 0:
                    in_traffic -= 1
                sc_pen   = 25000 if sc_active else 0
                
                # Apply compound modifiers to the first stint
                current_deg = deg_penalty
                if not has_pitted:
                    if req.starting_tire == "Soft":
                        current_deg = int(deg_penalty * 2.0)
                    elif req.starting_tire == "Hard":
                        current_deg = int(deg_penalty * 0.75)
                
                lap_time = (
                    base_lap_time
                    + (tire_age * current_deg)
                    + noise + dirty_air + sc_pen
                )
                tire_age += 1

            total_time += lap_time

        return total_time

    simulator.simulate_single_race = _patched_simulate

    # ── Step 3: Dynamic tire-compound baseline laps ───────────────────────────
    total = req.total_laps
    if req.starting_tire == "Soft":
        baseline_laps = [int(total * 0.25), int(total * 0.60)]
    elif req.starting_tire == "Hard":
        baseline_laps = [int(total * 0.45), int(total * 0.80)]
    else:  # Medium
        baseline_laps = [int(total * 0.33), int(total * 0.66)]

    static_laps = set(baseline_laps)

    # ── Step 4: 10,000 Monte Carlo simulations ────────────────────────────────
    N              = 10_000
    ruin_threshold = base_lap_time * req.total_laps * 1.05

    ai_results     = [_patched_simulate(mdp_policy=mdp.policy)    for _ in range(N)]
    static_results = [_patched_simulate(static_pit_laps=static_laps) for _ in range(N)]

    # ── Aggregate ─────────────────────────────────────────────────────────────
    ai_avg_s     = float(np.mean(ai_results))     / 1000.0
    static_avg_s = float(np.mean(static_results)) / 1000.0

    ai_ruin     = (sum(1 for r in ai_results     if r > ruin_threshold) / N) * 100
    static_ruin = (sum(1 for r in static_results if r > ruin_threshold) / N) * 100

    time_adv = round(static_avg_s - ai_avg_s, 3)
    risk_red = round(static_ruin  - ai_ruin,  2)

    THRESHOLD = 0.5
    if abs(time_adv) < THRESHOLD:
        winner = "Tie"
    elif time_adv > 0:
        winner = "AI"
    else:
        winner = "Static"

    return StrategyResponse(
        track_name=req.track_name,
        cluster=cluster_id,
        cluster_label=cluster_label,
        starting_tire=req.starting_tire,
        data_points=data_points,
        ai_expected_time_s=round(ai_avg_s, 3),
        ai_risk_of_ruin_pct=round(ai_ruin, 2),
        ai_sim_distribution=[round(r / 1000.0, 3) for r in ai_results],
        static_expected_time_s=round(static_avg_s, 3),
        static_risk_of_ruin_pct=round(static_ruin, 2),
        static_sim_distribution=[round(r / 1000.0, 3) for r in static_results],
        time_advantage_s=time_adv,
        risk_reduction_pct=risk_red,
        winner=winner,
        mdp_reference_strategy=ref_events,
        baseline_laps=baseline_laps,
    )