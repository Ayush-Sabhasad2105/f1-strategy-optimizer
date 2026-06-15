# run_pipeline.py
import fastf1
import time
from src.data_pipeline.fetcher import fetch_race_data
from src.data_pipeline.cleaner import clean_laps_data, clean_weather_data

from src.data_pipeline.loader import load_race_data
from src.data_pipeline.feature_extractor import extract_segmented_features

def main():
    print("--- Starting Multi-Year ETL Pipeline ---")
    
    # Loop through multiple historical seasons (starting from 2022 as requested)
    years_to_process = range(2025, 2026)
    
    for year in years_to_process:
        print(f"\n=========================================")
        print(f" FETCHING SEASON: {year}")
        print(f"=========================================")

        if year == 2020:
            print(" -> Skipping 2020 (Pandemic anomalies)")
            continue
        
        schedule = fastf1.get_event_schedule(year)
        races = schedule[schedule['EventFormat'] != 'testing']
        
        for index, event in races.iterrows():
            round_num = event['RoundNumber']
            event_name = event['EventName']
            
            print(f" -> Processing {year} Round {round_num}: {event_name}")
            
            try:
                race_info, raw_laps, weather_df = fetch_race_data(year, round_num)
                clean_laps    = clean_laps_data(raw_laps)
                weather_summary = clean_weather_data(weather_df, raw_laps)
                load_race_data(race_info, clean_laps, weather_summary)
                if weather_summary['had_rainfall']:
                    print(f"    [!] WET RACE detected — flagged in DB (had_rainfall=True)")

                print("    [Zzz] Sleeping for 15 seconds to respect API limits...")
                time.sleep(15)
                
            except Exception as e:
                print(f"    [!] FAILED to process {year} Round {round_num}. Error: {e}")
                continue

    print("\n--- Multi-Year Pipeline Complete! Database is fully populated.---")

    # Phase 2: Extract era-segmented track features from the populated DB
    print("\n--- Running Feature Extraction (Era-Segmented) ---")
    track_profiles = extract_segmented_features()
    print(f"\n✅ Final track profiles ({len(track_profiles)} circuits):")
    print(track_profiles[['circuit_name', 'base_lap_time_ms', 'pit_loss_ms', 'tire_deg_ms_per_lap']].to_string(index=False))

if __name__ == "__main__":
    main()