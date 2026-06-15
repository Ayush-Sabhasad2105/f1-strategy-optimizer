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
        WITH clean_laps AS (
            SELECT
                r.circuit_name,
                l.compound,
                l.tire_life,
                l.lap_time_ms
            FROM laps l
            JOIN Races r ON l.race_id = r.race_id
            WHERE r.year IN (2019, 2021, 2022, 2023, 2024, 2025)
              AND r.had_rainfall    = FALSE
              AND l.compound IN ('SOFT', 'MEDIUM', 'HARD')
              AND l.is_pit_in_lap  = FALSE
              AND l.is_pit_out_lap = FALSE
              AND l.lap_time_ms    > 0
              AND l.lap_time_ms    < 250000  -- cap outliers (>4 min = SC/flag laps)
        ),
        early_stint AS (
            -- Median lap time for MEDIUM tires, fresh (laps 3–8)
            -- Must use a single compound to avoid cross-compound bias:
            -- Softs are only at low tire_life, Hards only at high tire_life,
            -- so mixing compounds makes early/late medians incomparable.
            SELECT
                circuit_name,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lap_time_ms) AS med_early
            FROM clean_laps
            WHERE tire_life BETWEEN 3 AND 8
              AND compound = 'MEDIUM'
            GROUP BY circuit_name
        ),
        late_stint AS (
            -- Median lap time for MEDIUM tires, well worn (laps 20–35)
            -- Modern 18-inch F1 tires are essentially flat in the first 20 laps;
            -- the degradation signal only emerges in the 20-35 lap window.
            SELECT
                circuit_name,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lap_time_ms) AS med_late
            FROM clean_laps
            WHERE tire_life BETWEEN 20 AND 35
              AND compound = 'MEDIUM'
            GROUP BY circuit_name
        ),
        data_counts AS (
            SELECT circuit_name, COUNT(*) AS data_points
            FROM clean_laps
            GROUP BY circuit_name
        ),
        pit_in_laps AS (
            SELECT
                r.circuit_name,
                -- Use 10th-percentile to avoid SC/formation lap outliers
                PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY l.lap_time_ms) AS p10_pit_in_ms
            FROM laps l
            JOIN Races r ON l.race_id = r.race_id
            WHERE r.year IN (2019, 2021, 2022, 2023, 2024, 2025)
              AND r.had_rainfall  = FALSE
              AND l.compound IN ('SOFT', 'MEDIUM', 'HARD')
              AND l.is_pit_in_lap = TRUE
              AND l.lap_time_ms   > 0
              AND l.lap_time_ms   < 250000  -- cap outliers
            GROUP BY r.circuit_name
        ),
        clean_median AS (
            SELECT
                circuit_name,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lap_time_ms) AS median_clean_ms
            FROM clean_laps
            WHERE tire_life BETWEEN 3 AND 15
            GROUP BY circuit_name
        )
        SELECT
            e.circuit_name,
            dc.data_points,
            -- deg = (worn median - fresh median) / 22 laps (window: 3-8 vs 20-35)
            GREATEST(
                0,
                ROUND((l.med_late - e.med_early) / 22.0)::int
            ) AS tire_deg_ms_per_lap,
            GREATEST(
                0,
                ROUND(p.p10_pit_in_ms - c.median_clean_ms)::int
            ) AS pit_loss_ms
        FROM early_stint   e
        JOIN late_stint    l  ON e.circuit_name = l.circuit_name
        JOIN pit_in_laps   p  ON e.circuit_name = p.circuit_name
        JOIN clean_median  c  ON e.circuit_name = c.circuit_name
        JOIN data_counts   dc ON e.circuit_name = dc.circuit_name;
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