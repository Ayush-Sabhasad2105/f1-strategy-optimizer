# backend/routes.py
import sys
import os
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List

from src.models.mdp_solver import RaceMDP
from src.models.monte_carlo import RaceSimulator
from backend.track_data import TRACK_PROFILES, CLUSTER_LABELS

router = APIRouter(prefix="/api")


# ─── Schemas ───────────────────────────────────────────────────────────────────

class StrategyRequest(BaseModel):
    track_name:    str   = Field(...,   example="Bahrain")
    total_laps:    int   = Field(57,    ge=20,    le=80)
    base_lap_time: int   = Field(95000, ge=50000, le=200000,
                                 description="Baseline lap time in ms")
    pit_loss:      int   = Field(24000, ge=10000, le=60000,
                                 description="Pit-lane delta in ms")
    deg_penalty:   int   = Field(200,   ge=50,    le=800,
                                 description="Tire deg per lap in ms")
    sc_probability:  float = Field(0.02, ge=0.0, le=0.10,
                                   description="Safety Car probability per lap (0–10%)")
    traffic_penalty: int   = Field(1500, ge=0,   le=3000,
                                   description="Dirty-air penalty per lap in ms")


class PitStopEvent(BaseModel):
    lap:   int
    label: str


class StrategyResponse(BaseModel):
    track_name:    str
    cluster:       int
    cluster_label: str

    # ── Reactive AI (MDP-guided live decisions) ──────────────────────────────
    ai_expected_time_s:   float
    ai_risk_of_ruin_pct:  float
    ai_sim_distribution:  List[float]   # 10 000 values in seconds

    # ── Static Baseline (fixed 2-stop: laps 19 & 38) ────────────────────────
    static_expected_time_s:   float
    static_risk_of_ruin_pct:  float
    static_sim_distribution:  List[float]

    # ── Advantage metrics ────────────────────────────────────────────────────
    time_advantage_s:    float   # static − ai  (positive = AI faster)
    risk_reduction_pct:  float   # static_ruin − ai_ruin  (positive = AI safer)
    winner:              str     # "AI" | "Static" | "Tie"

    # ── Reference strategy from MDP trace ───────────────────────────────────
    mdp_reference_strategy: List[PitStopEvent]


class TrackInfo(BaseModel):
    circuit_name:       str
    cluster:            int
    cluster_label:      str
    base_lap_time_ms:   int
    pit_loss_ms:        int
    tire_deg_ms_per_lap: int


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_track(name: str) -> dict:
    for t in TRACK_PROFILES:
        if t["circuit_name"].lower() == name.lower():
            return t
    return None


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
    """Returns all 22 circuit profiles with k-Means cluster assignments."""
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
    V3.0 — Reactive AI vs Static Baseline pipeline:

    1. Solve the 3D MDP (lap × tire_age × traffic_laps) to produce a full
       policy matrix. The `traffic_penalty` drives the dirty-air cost used
       in backward induction.

    2. Run 10,000 Monte Carlo simulations for the REACTIVE AI — the simulator
       queries `mdp.policy` on every lap and optionally pits under a Safety Car
       (Plan B logic: SC active + tire_age > 10 → cheap pit).

    3. Run 10,000 Monte Carlo simulations for the STATIC BASELINE — a fixed
       2-stop strategy (laps 19 & 38), which cannot react to Safety Cars.

    The sc_probability and traffic_penalty from the request are patched into
    the simulator before running so the user's slider values take effect.
    """

    # ── Track context ────────────────────────────────────────────────────────
    track_info    = _get_track(req.track_name)
    cluster_id    = track_info["cluster"] if track_info else 0
    cluster_label = CLUSTER_LABELS.get(cluster_id, "Unknown")

    # ── Step 1: Solve 3D MDP ─────────────────────────────────────────────────
    mdp = RaceMDP(
        total_laps=req.total_laps,
        base_lap_time=req.base_lap_time,
        pit_loss=req.pit_loss,
        deg_penalty_per_lap=req.deg_penalty,
    )
    mdp.traffic_penalty = req.traffic_penalty
    mdp.solve()

    # Reference strategy trace (for display only — AI doesn't follow this rigidly)
    ref_strings  = mdp.get_optimal_strategy()
    ref_pit_laps = _parse_pit_laps(ref_strings)
    ref_events   = [PitStopEvent(lap=l, label=f"Lap {l}: PIT") for l in ref_pit_laps]

    # ── Step 2: Build simulator, patch user-controlled stochastic params ─────
    simulator = RaceSimulator(
        total_laps=req.total_laps,
        base_lap_time=req.base_lap_time,
        pit_loss_mean=req.pit_loss,
        deg_penalty=req.deg_penalty,
    )

    # Monkey-patch the two V3.0 user-controlled random parameters so the
    # internal simulate_single_race() loop picks them up via self.*
    # (The class uses hardcoded 0.02 / 1500 literals — we override them here
    #  so sliders actually drive the simulation without altering the model file)
    original_simulate = simulator.simulate_single_race

    sc_prob     = req.sc_probability
    traffic_pen = req.traffic_penalty

    def _patched_simulate(mdp_policy=None, static_pit_laps=None):
        """Drop-in replacement that respects the user's SC prob & dirty-air penalty."""
        total_time   = 0
        tire_age     = 0
        in_traffic   = 0
        sc_active    = False
        sc_remaining = 0

        for lap in range(1, req.total_laps + 1):
            # Stochastic Safety Car — user-controlled probability
            if not sc_active and np.random.random() < sc_prob:
                sc_active    = True
                sc_remaining = int(np.random.randint(2, 6))
            if sc_active:
                sc_remaining -= 1
                if sc_remaining <= 0:
                    sc_active = False

            # ── Decision ────────────────────────────────────────────────────
            is_pitting = False
            if mdp_policy is not None:
                safe_age    = min(tire_age, req.total_laps)
                safe_traffic = min(in_traffic, 3)
                action_code = mdp_policy[lap - 1, safe_age, safe_traffic]
                # Plan B: opportunistic SC pit if tires are old enough
                if sc_active and tire_age > 10:
                    is_pitting = True
                else:
                    is_pitting = (action_code == 1)
            elif static_pit_laps is not None:
                is_pitting = (lap in static_pit_laps)

            # ── Lap execution ────────────────────────────────────────────────
            if is_pitting:
                pit_var   = np.random.normal(0, 500)
                fumble    = 5000 if np.random.random() < 0.05 else 0
                pit_delta = (req.pit_loss / 2) if sc_active else req.pit_loss
                lap_time  = req.base_lap_time + pit_delta + pit_var + fumble
                tire_age  = 1
                in_traffic = 3
            else:
                noise     = np.random.normal(0, 300)
                dirty_air = (
                    np.random.normal(traffic_pen, traffic_pen * 0.33)
                    if in_traffic > 0 else 0
                )
                if in_traffic > 0:
                    in_traffic -= 1
                sc_pen   = 25000 if sc_active else 0
                lap_time = (
                    req.base_lap_time
                    + (tire_age * req.deg_penalty)
                    + noise + dirty_air + sc_pen
                )
                tire_age += 1

            total_time += lap_time

        return total_time

    # Swap in the patched version
    simulator.simulate_single_race = _patched_simulate

    # ── Step 3: 10 000 simulations — Reactive AI ─────────────────────────────
    N             = 10_000
    ruin_threshold = req.base_lap_time * req.total_laps * 1.05

    ai_results = [
        _patched_simulate(mdp_policy=mdp.policy) for _ in range(N)
    ]

    # ── Step 4: 10 000 simulations — Static 2-Stop ───────────────────────────
    static_laps    = {19, 38}
    static_results = [
        _patched_simulate(static_pit_laps=static_laps) for _ in range(N)
    ]

    # ── Aggregate ────────────────────────────────────────────────────────────
    ai_avg_s     = float(np.mean(ai_results))     / 1000.0
    static_avg_s = float(np.mean(static_results)) / 1000.0

    ai_ruin     = (sum(1 for r in ai_results     if r > ruin_threshold) / N) * 100
    static_ruin = (sum(1 for r in static_results if r > ruin_threshold) / N) * 100

    time_adv  = round(static_avg_s - ai_avg_s, 3)   # positive = AI faster
    risk_red  = round(static_ruin  - ai_ruin,  2)    # positive = AI safer

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
    )
