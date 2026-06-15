# run_backfill_weather.py
"""
One-time weather backfill for races already loaded into the database
without weather data (had_rainfall IS NULL).

HOW IT WORKS:
  1. Queries the DB for every race where had_rainfall IS NULL.
  2. Re-opens the FastF1 session from the LOCAL CACHE (no full re-download
     of lap data — FastF1 only fetches what is missing).
  3. Calls session.load(laps=False, telemetry=False, weather=True) so
     only the lightweight weather endpoint is hit.
  4. UPDATEs the Races row with the 4 weather columns.

RUN ONCE:
  .venv/bin/python run_backfill_weather.py

PREREQUISITE — add the weather columns to your Races table first:
  ALTER TABLE Races
    ADD COLUMN IF NOT EXISTS avg_track_temp_c  NUMERIC(5,1),
    ADD COLUMN IF NOT EXISTS avg_air_temp_c    NUMERIC(5,1),
    ADD COLUMN IF NOT EXISTS avg_humidity_pct  NUMERIC(5,1),
    ADD COLUMN IF NOT EXISTS had_rainfall      BOOLEAN DEFAULT FALSE;
"""

import time
import fastf1
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from src.data_pipeline.cleaner import clean_weather_data

load_dotenv()

# ── FastF1 cache (same dir the pipeline uses) ─────────────────────────────────
cache_dir = os.path.join(os.path.dirname(__file__), 'data/raw')
os.makedirs(cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(cache_dir)
fastf1.set_log_level("WARNING")

# ── DB connection ─────────────────────────────────────────────────────────────
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("DATABASE_URL not set in .env")
engine = create_engine(db_url)


def fetch_races_needing_weather(conn):
    """Returns all (race_id, year, round_number) where weather was not stored.

    We check avg_track_temp_c IS NULL rather than had_rainfall IS NULL because
    PostgreSQL set had_rainfall = FALSE (the column default) on all existing rows
    when the column was added via ALTER TABLE — even before the backfill ran.
    avg_track_temp_c has no default so it stays NULL until the backfill writes it.
    """
    result = conn.execute(text("""
        SELECT race_id, year, round_number
        FROM   Races
        WHERE  avg_track_temp_c IS NULL
        ORDER  BY year, round_number;
    """))
    return result.fetchall()



def update_weather(conn, race_id, weather_summary):
    conn.execute(text("""
        UPDATE Races SET
            avg_track_temp_c = :avg_track_temp_c,
            avg_air_temp_c   = :avg_air_temp_c,
            avg_humidity_pct = :avg_humidity_pct,
            had_rainfall     = :had_rainfall
        WHERE race_id = :race_id;
    """), {**weather_summary, "race_id": race_id})
    conn.commit()


def main():
    print("=== Weather Backfill ===")
    print("Querying DB for races without weather data...\n")

    with engine.connect() as conn:
        races = fetch_races_needing_weather(conn)

        if not races:
            print("✅ Nothing to backfill — all races already have weather data.")
            return

        print(f"Found {len(races)} races to backfill.\n")

        for race_id, year, round_number in races:
            print(f"  [{year} R{round_number}] Loading weather from cache...", end=" ", flush=True)
            try:
                session = fastf1.get_session(year, round_number, 'R')
                # laps=False → skip re-downloading lap data from cache
                # weather=True → fetch only the weather endpoint (fast)
                session.load(laps=False, telemetry=False, weather=True)

                weather_summary = clean_weather_data(session.weather_data)
                update_weather(conn, race_id, weather_summary)

                flag = "🌧  WET" if weather_summary['had_rainfall'] else "☀  DRY"
                print(f"{flag}  track={weather_summary['avg_track_temp_c']}°C  "
                      f"air={weather_summary['avg_air_temp_c']}°C")

            except Exception as e:
                print(f"⚠  FAILED — {e}")
                continue

            # Small pause to respect FastF1 API rate limits for any cache misses
            time.sleep(2)

    print("\n✅ Backfill complete.")
    print("   Wet races will now be excluded from tire-deg and pit-loss calculations.")


if __name__ == "__main__":
    main()
