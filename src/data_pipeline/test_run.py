import sys
import os

# Add the project root to the python path so it can be run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.data_pipeline.fetcher import fetch_race_data
from src.data_pipeline.cleaner import clean_laps_data

if __name__ == "__main__":
    race_data, raw_laps = fetch_race_data(2023, 1)
    clean_laps = clean_laps_data(raw_laps)
    
    print("\n--- Smoke Test Success! ---")
    print(f"Extracted: {race_data['year']} {race_data['circuit_name']}")
    print(clean_laps.head())