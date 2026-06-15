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


def get_engine():
    """Establishes connection to the PostgreSQL database."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment variables.")
    return create_engine(db_url)


def extract_segmented_features():
    print("--- Extracting Era-Segmented Features ---")
    engine = get_engine()

    # ── 1. CLUSTERING CORE (2019–2025, excl. 2020) ──────────────────────────
    query_clustering = text("""
        WITH stint_deltas AS (
            -- For each lap, calculate the time gained/lost vs the previous lap
            -- within the same driver stint. This controls for track evolution:
            -- the effect per single lap (~30ms) is tiny vs tire wear (~100-300ms).
            SELECT
                r.circuit_name,
                COUNT(*) OVER (PARTITION BY r.circuit_name) AS data_points,
                l.lap_time_ms
                    - LAG(l.lap_time_ms) OVER (
                        PARTITION BY l.race_id, l.driver_id
                        ORDER BY l.lap_number
                    ) AS lap_delta_ms,
                l.tire_life
                    - LAG(l.tire_life) OVER (
                        PARTITION BY l.race_id, l.driver_id
                        ORDER BY l.lap_number
                    ) AS life_delta
            FROM laps l
            JOIN Races r ON l.race_id = r.race_id
            WHERE r.year IN (2019, 2021, 2022, 2023, 2024, 2025)
              AND r.had_rainfall    = FALSE
              AND l.compound IN ('SOFT', 'MEDIUM', 'HARD')
              AND l.is_pit_in_lap  = FALSE
              AND l.is_pit_out_lap = FALSE
              AND l.lap_time_ms BETWEEN 1000 AND 250000
              AND l.tire_life BETWEEN 5 AND 30
        ),
        deg_per_circuit AS (
            SELECT
                circuit_name,
                MAX(data_points) AS data_points,
                -- Median lap-over-lap delta: positive = getting slower = real deg
                -- Filter: only consecutive stint laps (life_delta=1),
                --         and cap outliers from SC/yellow laps
                PERCENTILE_CONT(0.5) WITHIN GROUP (
                    ORDER BY lap_delta_ms
                ) AS median_deg_ms
            FROM stint_deltas
            WHERE life_delta = 1
              AND lap_delta_ms BETWEEN -2000 AND 5000
            GROUP BY circuit_name
        ),
        pit_in_laps AS (
            -- The pit-IN lap ends at the pit lane entry timing point.
            -- It captures the deceleration penalty only (~3-5s extra vs clean).
            SELECT
                r.circuit_name,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY l.lap_time_ms) AS median_pit_in_ms
            FROM laps l
            JOIN Races r ON l.race_id = r.race_id
            WHERE r.year IN (2019, 2021, 2022, 2023, 2024, 2025)
              AND r.had_rainfall   = FALSE
              AND l.compound IN ('SOFT', 'MEDIUM', 'HARD')
              AND l.is_pit_in_lap  = TRUE
              AND l.lap_time_ms    BETWEEN 1000 AND 250000
            GROUP BY r.circuit_name
        ),
        pit_out_laps AS (
            -- The pit-OUT lap captures the stationary stop + slow pit lane traversal.
            -- Typically 18-25s extra vs a clean lap at most circuits.
            -- We use P25 (not P10) to avoid SC-window pit stops that are unrealistically cheap.
            SELECT
                r.circuit_name,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY l.lap_time_ms) AS p25_pit_out_ms
            FROM laps l
            JOIN Races r ON l.race_id = r.race_id
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
            FROM laps l
            JOIN Races r ON l.race_id = r.race_id
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
            d.circuit_name,
            d.data_points,
            GREATEST(
                0,
                ROUND(d.median_deg_ms)::int
            ) AS tire_deg_ms_per_lap,
            -- TRUE PIT LANE LOSS formula:
            --   pit_loss = (pit_in − clean) + (pit_out − clean)
            --            = pit_in + pit_out − 2 × clean
            -- This captures BOTH the deceleration penalty (pit-in) and the
            -- stop + slow lane penalty (pit-out). Floored at 15,000ms as a
            -- sanity guard (no real F1 pit stop loses less than 15 seconds).
            GREATEST(
                15000,
                ROUND(
                    COALESCE(i.median_pit_in_ms, c.median_clean_ms)
                    + o.p25_pit_out_ms
                    - 2.0 * c.median_clean_ms
                )::int
            ) AS pit_loss_ms
        FROM deg_per_circuit  d
        JOIN pit_out_laps     o ON d.circuit_name = o.circuit_name
        JOIN clean_median     c ON d.circuit_name = c.circuit_name
        LEFT JOIN pit_in_laps i ON d.circuit_name = i.circuit_name;
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