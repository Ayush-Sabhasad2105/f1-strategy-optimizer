# src/data_pipeline/feature_extractor.py
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    """Establishes connection to the PostgreSQL database."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment variables.")
    return create_engine(db_url)

def extract_segmented_features():
    """
    Returns a merged DataFrame of per-circuit track profiles using an
    era-segmented approach:

      - Clustering core  (2019-2025, excl. 2020): tire degradation slope
        and pit-lane loss delta averaged across the broadest dataset.

      - Simulation core  (2022-2025 Ground Effect era only): baseline
        clean-air lap times from a technically homogeneous regulation period.

    Tire degradation: average ms/lap penalty estimated by computing the
    slope of lap_time_ms over tire_life for non-pit laps, grouped per circuit.

    Pit loss: average extra time on a pit-in lap vs. the driver's median
    clean lap at that circuit (approximated as AVG pit-in lap time minus
    AVG clean lap time).
    """
    print("--- Extracting Era-Segmented Features ---")
    engine = get_engine()

    # ── 1. CLUSTERING CORE (2019–2025, excl. 2020) ──────────────────────────
    # Tire deg: average ms added per extra lap of tire age on clean laps.
    # We measure it as the per-circuit OLS-like estimator:
    #   slope ≈ ( SUM(tyre_life * lap_time_ms) - n*mean(tl)*mean(lt) ) /
    #           ( SUM(tyre_life^2)             - n*mean(tl)^2         )
    # Pit loss: average (pit_in lap time − median clean lap time) per circuit.
    query_clustering = text("""
        WITH clean_laps AS (
            -- Non-pit laps with valid lap times
            SELECT
                r.circuit_name,
                l.tire_life,
                l.lap_time_ms
            FROM laps l
            JOIN races r ON l.race_id = r.race_id
            WHERE r.year IN (2019, 2021, 2022, 2023, 2024, 2025)
              AND l.is_pit_in_lap  = FALSE
              AND l.is_pit_out_lap = FALSE
              AND l.lap_time_ms    > 0
        ),
        deg_stats AS (
            SELECT
                circuit_name,
                COUNT(*)                          AS n,
                AVG(tire_life::float)             AS mean_tl,
                AVG(lap_time_ms::float)           AS mean_lt,
                SUM(tire_life::float * lap_time_ms::float) AS sum_tl_lt,
                SUM(tire_life::float * tire_life::float)   AS sum_tl2
            FROM clean_laps
            GROUP BY circuit_name
        ),
        pit_in_laps AS (
            SELECT
                r.circuit_name,
                AVG(l.lap_time_ms) AS avg_pit_in_ms
            FROM laps l
            JOIN races r ON l.race_id = r.race_id
            WHERE r.year IN (2019, 2021, 2022, 2023, 2024, 2025)
              AND l.is_pit_in_lap = TRUE
              AND l.lap_time_ms   > 0
            GROUP BY r.circuit_name
        ),
        clean_median AS (
            SELECT
                circuit_name,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lap_time_ms) AS median_clean_ms
            FROM clean_laps
            WHERE tire_life BETWEEN 3 AND 15   -- representative race pace window
            GROUP BY circuit_name
        )
        SELECT
            d.circuit_name,
            -- Tire degradation slope in ms per lap of tire age
            GREATEST(
                0,
                ROUND(
                    (d.sum_tl_lt - d.n * d.mean_tl * d.mean_lt)
                    / NULLIF(d.sum_tl2 - d.n * d.mean_tl * d.mean_tl, 0)
                )::int
            ) AS tire_deg_ms_per_lap,
            -- Pit-lane loss in ms
            GREATEST(
                0,
                ROUND(p.avg_pit_in_ms - c.median_clean_ms)::int
            ) AS pit_loss_ms
        FROM deg_stats      d
        JOIN pit_in_laps    p ON d.circuit_name = p.circuit_name
        JOIN clean_median   c ON d.circuit_name = c.circuit_name;
    """)

    # ── 2. SIMULATION CORE (2022–2025 Ground Effect era) ────────────────────
    # Base lap time: median clean-air lap in the representative tire-life window
    # using only the post-2022 technical regulation cars (18-inch tyres).
    query_simulation = text("""
        WITH clean_laps AS (
            SELECT
                r.circuit_name,
                l.lap_time_ms
            FROM laps l
            JOIN races r ON l.race_id = r.race_id
            WHERE r.year BETWEEN 2022 AND 2025
              AND l.is_pit_in_lap  = FALSE
              AND l.is_pit_out_lap = FALSE
              AND l.lap_time_ms    > 0
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
        df_clustering  = pd.read_sql(query_clustering,  conn)
        df_simulation  = pd.read_sql(query_simulation,  conn)

    # Merge: inner join so only circuits present in both windows are kept
    final_track_profiles = pd.merge(
        df_clustering,
        df_simulation,
        on='circuit_name',
        how='inner'
    )

    print(f"Segmentation complete. {len(final_track_profiles)} circuits extracted.")
    print("Modern Ground Effect baseline successfully isolated from 13-inch era.")
    return final_track_profiles

if __name__ == "__main__":
    profiles_df = extract_segmented_features()
    print(profiles_df.to_string())