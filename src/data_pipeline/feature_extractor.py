# src/data_pipeline/feature_extractor.py
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Official lap counts per circuit — not derivable from telemetry
TOTAL_LAPS_MAP = {
    "Bahrain Grand Prix":        57,  "Saudi Arabian Grand Prix":  50,
    "Australian Grand Prix":     58,  "Japanese Grand Prix":       53,
    "Chinese Grand Prix":        56,  "Miami Grand Prix":          57,
    "Emilia Romagna Grand Prix": 63,  "Monaco Grand Prix":         78,
    "Canadian Grand Prix":       70,  "Spanish Grand Prix":        66,
    "Austrian Grand Prix":       71,  "British Grand Prix":        52,
    "Hungarian Grand Prix":      70,  "Belgian Grand Prix":        44,
    "Dutch Grand Prix":          72,  "Italian Grand Prix":        53,
    "Azerbaijan Grand Prix":     51,  "Singapore Grand Prix":      62,
    "United States Grand Prix":  56,  "Mexico City Grand Prix":    71,
    "São Paulo Grand Prix":      71,  "Las Vegas Grand Prix":      50,
    "Qatar Grand Prix":          57,  "Abu Dhabi Grand Prix":      58,
}

CLUSTER_LABELS = {
    0: "Power Circuit",
    1: "Technical/Street",
    2: "Long Pit Lane",
    3: "Extreme Deg",
}

# ── TIRE DEGRADATION CALIBRATION ─────────────────────────────────────────────
# Telemetry-derived deg rates are unreliable: fuel burn (~0.5-1 s/lap) and
# rubber/track-evolution (~0.3-0.8 s/lap) both MASK and outweigh tire wear,
# so any OLS or bin-diff on raw lap times gives zero or negative values.
# These values are calibrated against real F1 one/two-stop strategy windows
# (i.e., values that cause the MDP to recommend pitting at realistic laps):
#
#   High (200-300 ms/lap)  → 2-stop  → Qatar, Spain, Zandvoort, Hungary
#   Medium (130-200 ms/lap)→ 1-stop  → Bahrain, Belgium, Imola, São Paulo
#   Low (80-130 ms/lap)    → 1-stop (late) → Monaco, Singapore, Italy, Baku
#
DEG_CALIBRATION = {
    # ── High deg circuits (bumpy, abrasive, or thermal stress) ───────────────
    "Qatar Grand Prix":             300,  # tyre cliff, multiple stops
    "Spanish Grand Prix":           280,  # historically high deg
    "Dutch Grand Prix":             260,  # abrasive Zandvoort surface
    "Hungarian Grand Prix":         250,  # tight corners, mechanical deg
    "Emilia Romagna Grand Prix":    240,  # bumpy Imola, abrasive kerbs
    "São Paulo Grand Prix":         230,  # bumpy Interlagos
    "Belgian Grand Prix":           210,  # high speed = high tyre stress
    "Bahrain Grand Prix":           200,  # abrasive desert surface
    "Japanese Grand Prix":          190,  # high mechanical load at Suzuka
    # ── Medium deg circuits ──────────────────────────────────────────────────
    "Australian Grand Prix":        170,  # moderate deg post-resurfacing
    "British Grand Prix":           160,  # Silverstone can be aggressive
    "Chinese Grand Prix":           160,  # mix of slow corners and high-speed
    "United States Grand Prix":     160,  # COTA bumps, abrasive
    "Mexico City Grand Prix":       150,  # high altitude reduces load
    "French Grand Prix":            150,  # smooth Paul Ricard surface
    "Austrian Grand Prix":          140,  # short lap, less total stress
    "Miami Grand Prix":             140,  # moderate, surface improving
    # ── Low deg circuits ─────────────────────────────────────────────────────
    "Abu Dhabi Grand Prix":         120,  # smooth Yas Marina
    "Canadian Grand Prix":          110,  # stop-start layout
    "Singapore Grand Prix":         100,  # walls prevent pushing
    "Monaco Grand Prix":             90,  # very smooth, low speed
    "Italian Grand Prix":            90,  # monza: low downforce, low mech deg
    "Azerbaijan Grand Prix":         85,  # smooth Baku, walls limit pace
    "Saudi Arabian Grand Prix":      85,  # smooth Jeddah, high speed
    "Las Vegas Grand Prix":          80,  # cold temps, smooth track
}


def get_engine():
    """Establishes connection to the PostgreSQL database."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment variables.")
    return create_engine(db_url)


def extract_segmented_features():
    print("--- Extracting Era-Segmented Features ---")
    engine = get_engine()

    # ── 1. CLUSTERING CORE ──────────────────────────────────────────────────
    # The DB provides: data_points (lap count) and pit_loss_ms (measured).
    # tire_deg_ms_per_lap comes from DEG_CALIBRATION (telemetry-derived values
    # are unreliable — fuel burn + track evolution fully mask tire wear).
    query_clustering = text("""
        WITH data_counts AS (
            SELECT r.circuit_name, COUNT(*) AS data_points
            FROM laps l JOIN Races r ON l.race_id = r.race_id
            WHERE r.year IN (2019, 2021, 2022, 2023, 2024, 2025)
              AND r.had_rainfall = FALSE
              AND l.compound IN ('SOFT', 'MEDIUM', 'HARD')
              AND l.is_pit_in_lap = FALSE AND l.is_pit_out_lap = FALSE
              AND l.lap_time_ms BETWEEN 1000 AND 250000
            GROUP BY r.circuit_name
        ),
        pit_in_laps AS (
            SELECT
                r.circuit_name,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY l.lap_time_ms) AS median_pit_in_ms
            FROM laps l JOIN Races r ON l.race_id = r.race_id
            WHERE r.year IN (2019, 2021, 2022, 2023, 2024, 2025)
              AND r.had_rainfall   = FALSE
              AND l.compound IN ('SOFT', 'MEDIUM', 'HARD')
              AND l.is_pit_in_lap  = TRUE
              AND l.lap_time_ms    BETWEEN 1000 AND 250000
            GROUP BY r.circuit_name
        ),
        pit_out_laps AS (
            SELECT
                r.circuit_name,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY l.lap_time_ms) AS p25_pit_out_ms
            FROM laps l JOIN Races r ON l.race_id = r.race_id
            WHERE r.year IN (2019, 2021, 2022, 2023, 2024, 2025)
              AND r.had_rainfall   = FALSE
              AND l.compound IN ('SOFT', 'MEDIUM', 'HARD')
              AND l.is_pit_out_lap = TRUE
              AND l.lap_time_ms    BETWEEN 1000 AND 250000
            GROUP BY r.circuit_name
        ),
        clean_median AS (
            SELECT
                r.circuit_name,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY l.lap_time_ms) AS median_clean_ms
            FROM laps l JOIN Races r ON l.race_id = r.race_id
            WHERE r.year IN (2019, 2021, 2022, 2023, 2024, 2025)
              AND r.had_rainfall    = FALSE
              AND l.compound IN ('SOFT', 'MEDIUM', 'HARD')
              AND l.is_pit_in_lap  = FALSE
              AND l.is_pit_out_lap = FALSE
              AND l.lap_time_ms BETWEEN 1000 AND 250000
              AND l.tire_life BETWEEN 3 AND 15
            GROUP BY r.circuit_name
        )
        SELECT
            dc.circuit_name,
            dc.data_points,
            -- pit_loss = (pit_in penalty) + (pit_out penalty)
            --          = median_pit_in + P25_pit_out - 2 × clean_lap
            GREATEST(
                15000,
                ROUND(
                    COALESCE(i.median_pit_in_ms, c.median_clean_ms)
                    + o.p25_pit_out_ms
                    - 2.0 * c.median_clean_ms
                )::int
            ) AS pit_loss_ms
        FROM data_counts   dc
        JOIN pit_out_laps  o  ON dc.circuit_name = o.circuit_name
        JOIN clean_median  c  ON dc.circuit_name = c.circuit_name
        LEFT JOIN pit_in_laps i ON dc.circuit_name = i.circuit_name;
    """)

    # ── 2. SIMULATION CORE (2022–2025 Ground Effect era) ────────────────────

    query_simulation = text("""
        WITH clean_laps AS (
            SELECT
                r.circuit_name,
                l.lap_time_ms
            FROM laps l
            JOIN Races r ON l.race_id = r.race_id
            WHERE r.year BETWEEN 2022 AND 2025
              AND r.had_rainfall    = FALSE
              AND l.compound IN ('SOFT', 'MEDIUM', 'HARD')
              AND l.is_pit_in_lap  = FALSE
              AND l.is_pit_out_lap = FALSE
              AND l.lap_time_ms    > 0
              AND l.lap_time_ms    < 250000  -- cap SC/flag outliers
              AND l.tire_life BETWEEN 3 AND 20
        )
        SELECT
            circuit_name,
            ROUND(
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lap_time_ms)
            )::int AS base_lap_time_ms
        FROM clean_laps
        GROUP BY circuit_name;
    """)

    with engine.connect() as conn:
        df_clustering = pd.read_sql(query_clustering, conn)
        df_simulation = pd.read_sql(query_simulation, conn)

    final_track_profiles = pd.merge(
        df_clustering,
        df_simulation,
        on='circuit_name',
        how='inner'
    )

    # Apply calibrated tire degradation (telemetry-derived values are masked
    # by fuel burn + track evolution; DEG_CALIBRATION provides values that
    # drive realistic MDP pit stop decisions).
    final_track_profiles["tire_deg_ms_per_lap"] = (
        final_track_profiles["circuit_name"]
        .map(DEG_CALIBRATION)
        .fillna(120)          # sensible default for any circuit not in the dict
        .astype(int)
    )

    print(f"Segmentation complete. {len(final_track_profiles)} circuits extracted.")
    print("Modern Ground Effect baseline successfully isolated from 13-inch era.")

    # ── 3. k-Means clustering (k=4) & persist to DB ──────────────────────────
    persist_track_profiles(final_track_profiles, engine)

    return final_track_profiles


def persist_track_profiles(df: pd.DataFrame, engine):
    """Run k-Means (k=4) on [deg, pit_loss, base_lap_time] and write to track_profiles."""
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        print("  [!] scikit-learn not installed — skipping k-Means persistence.")
        print("      Install: .venv/bin/pip install scikit-learn")
        return

    features = df[["tire_deg_ms_per_lap", "pit_loss_ms", "base_lap_time_ms"]].copy()
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    df     = df.copy()
    df["cluster"] = kmeans.fit_predict(X_scaled)

    # Relabel clusters deterministically by ascending mean pit_loss_ms
    cluster_mean_pit = df.groupby("cluster")["pit_loss_ms"].mean().sort_values()
    remap = {old: new for new, old in enumerate(cluster_mean_pit.index)}
    df["cluster"]       = df["cluster"].map(remap)
    df["cluster_label"] = df["cluster"].map(CLUSTER_LABELS)

    # Add official total_laps from the lookup map
    df["total_laps"] = df["circuit_name"].map(TOTAL_LAPS_MAP).fillna(57).astype(int)

    upsert_sql = text("""
        INSERT INTO track_profiles (
            circuit_name, total_laps, base_lap_time_ms,
            pit_loss_ms, tire_deg_ms_per_lap,
            cluster, cluster_label, data_points, last_updated
        ) VALUES (
            :circuit_name, :total_laps, :base_lap_time_ms,
            :pit_loss_ms, :tire_deg_ms_per_lap,
            :cluster, :cluster_label, :data_points, NOW()
        )
        ON CONFLICT (circuit_name) DO UPDATE SET
            total_laps          = EXCLUDED.total_laps,
            base_lap_time_ms    = EXCLUDED.base_lap_time_ms,
            pit_loss_ms         = EXCLUDED.pit_loss_ms,
            tire_deg_ms_per_lap = EXCLUDED.tire_deg_ms_per_lap,
            cluster             = EXCLUDED.cluster,
            cluster_label       = EXCLUDED.cluster_label,
            data_points         = EXCLUDED.data_points,
            last_updated        = NOW();
    """)

    with engine.connect() as conn:
        for _, row in df.iterrows():
            conn.execute(upsert_sql, {
                "circuit_name":        row["circuit_name"],
                "total_laps":          int(row["total_laps"]),
                "base_lap_time_ms":    int(row["base_lap_time_ms"]),
                "pit_loss_ms":         int(row["pit_loss_ms"]),
                "tire_deg_ms_per_lap": int(row["tire_deg_ms_per_lap"]),
                "cluster":             int(row["cluster"]),
                "cluster_label":       row["cluster_label"],
                "data_points":         int(row["data_points"]),
            })
        conn.commit()

    print(f"  ✅ {len(df)} circuit profiles written to track_profiles table.")
    print(df[["circuit_name", "cluster", "cluster_label",
              "base_lap_time_ms", "pit_loss_ms", "tire_deg_ms_per_lap"]].to_string(index=False))


if __name__ == "__main__":
    profiles_df = extract_segmented_features()
    print(profiles_df.to_string())