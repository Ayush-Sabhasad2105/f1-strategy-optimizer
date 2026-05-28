# run_pipeline.py
import fastf1
from src.data_pipeline.fetcher import fetch_race_data
from src.data_pipeline.cleaner import clean_laps_data
from src.data_pipeline.loader import load_race_data

def main():
    print("--- Starting Phase 1: Full Season ETL Pipeline ---")
    
    # Get the official 2023 schedule
    schedule = fastf1.get_event_schedule(2023)
    
    # Filter out pre-season testing, keep only actual race weekends
    races = schedule[schedule['EventFormat'] != 'testing']
    
    for index, event in races.iterrows():
        round_num = event['RoundNumber']
        event_name = event['EventName']
        
        print(f"\n=========================================")
        print(f"Processing Round {round_num}: {event_name}")
        print(f"=========================================")
        
        try:
            # Step 2: Extract
            race_info, raw_laps = fetch_race_data(2023, round_num)
            
            # Step 3: Transform
            clean_laps = clean_laps_data(raw_laps)
            
            # Step 4: Load
            load_race_data(race_info, clean_laps)
            
        except Exception as e:
            # If a race gets cancelled (like Imola 2023) or data is missing, skip and continue
            print(f"FAILED to process Round {round_num}. Error: {e}")
            continue

    print("\n--- Season Pipeline Complete! Database is fully populated. ---")

if __name__ == "__main__":
    main()