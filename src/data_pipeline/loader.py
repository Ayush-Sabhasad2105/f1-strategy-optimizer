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

def load_race_data(race_info, clean_laps):

    """Loads race metadata, unique drivers, and laps into the database."""
    engine = get_engine()
    print("Connecting to database to load data....")

    with engine.connect() as conn:

        # 1. Insert the Race and get the generated race_id
        race_query = text("""
            INSERT INTO Races (year, round_number, circuit_name) 
            VALUES (:year, :round_number, :circuit_name)
            ON CONFLICT (year, round_number) DO UPDATE SET circuit_name = EXCLUDED.circuit_name
            RETURNING race_id;
        """)
        result = conn.execute(race_query, race_info)
        row = result.fetchone()

        if row:
            race_id = row[0]

        else:

            fetch_query = text("SELECT race_id FROM Races WHERE year=:year AND round_number=:round_number")
            race_id = conn.execute(fetch_query, race_info).fetchone()[0]


        # 2. Extract and insert unique Drivers to preserve foreign key constraints
        unique_drivers = clean_laps['Driver'].unique()
        for driver in unique_drivers:
            driver_query = text("""
                INSERT INTO Drivers (driver_id) VALUES (:driver)
                ON CONFLICT (driver_id) DO NOTHING;
            """)
            conn.execute(driver_query, {"driver": driver})
            
        # Commit the manual inserts before Pandas handles the bulk insertion
        conn.commit()

    # 3. Format DataFrame to map directly to the PostgreSQL schema layout
    laps_to_insert = clean_laps.copy()
    laps_to_insert['race_id'] = race_id
    
    laps_to_insert.rename(columns={
        'Driver': 'driver_id',
        'LapNumber': 'lap_number',
        'LapTime_ms': 'lap_time_ms',
        'Sector1_ms': 'sector1_ms',
        'Sector2_ms': 'sector2_ms',
        'Sector3_ms': 'sector3_ms',
        'Compound': 'compound',
        'TyreLife': 'tire_life',
        'TrackStatus': 'track_status'
    }, inplace=True)
    
    # 4. Bulk Insert Laps using Pandas optimization
    print("Executing bulk lap insertion...")
    laps_to_insert.to_sql('laps', engine, if_exists='append', index=False)
    print(f"SUCCESS: {len(laps_to_insert)} laps loaded into the database.")