# src/models/feature_extractor.py
import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def get_track_features():
    """
    Executes a CTE-based SQL query to extract logistical track profiles.
    Returns a Pandas DataFrame containing the raw feature vectors.
    """
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    
    # The SQL Query using Common Table Expressions (CTEs)
    query = text("""
        WITH TrackBaselines AS (
            SELECT 
                race_id, 
                AVG(lap_time_ms) AS base_lap_time
            FROM laps
            WHERE is_pit_in_lap = FALSE 
              AND is_pit_out_lap = FALSE 
              AND track_status = '1' -- '1' indicates a clear track
              AND lap_time_ms > 0
            GROUP BY race_id
        ),
        PitLoss AS (
            SELECT 
                race_id, 
                AVG(lap_time_ms) AS pit_lap_time
            FROM laps
            WHERE (is_pit_in_lap = TRUE OR is_pit_out_lap = TRUE)
              AND lap_time_ms > 0
            GROUP BY race_id
        ),
        TireWear AS (
            SELECT 
                race_id,
                AVG(CASE WHEN tire_life <= 3 THEN lap_time_ms END) AS fresh_tire_ms,
                AVG(CASE WHEN tire_life >= 15 THEN lap_time_ms END) AS worn_tire_ms
            FROM laps
            WHERE is_pit_in_lap = FALSE 
              AND is_pit_out_lap = FALSE 
              AND track_status = '1'
            GROUP BY race_id
        )
        SELECT 
            r.circuit_name,
            tb.base_lap_time,
            (pl.pit_lap_time - tb.base_lap_time) AS pit_loss_penalty,
            (tw.worn_tire_ms - tw.fresh_tire_ms) AS tire_deg_penalty
        FROM races r
        JOIN TrackBaselines tb ON r.race_id = tb.race_id
        JOIN PitLoss pl ON r.race_id = pl.race_id
        JOIN TireWear tw ON r.race_id = tw.race_id
        WHERE tw.worn_tire_ms IS NOT NULL 
          AND tw.fresh_tire_ms IS NOT NULL;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        
    # Drop any potential NaN values that resulted from math operations
    df.dropna(inplace=True)
    return df

if __name__ == "__main__":
    features_df = get_track_features()
    print("--- Track Feature Vectors ---")
    print(features_df.head())