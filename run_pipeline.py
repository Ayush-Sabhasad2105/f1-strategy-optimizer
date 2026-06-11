# run_pipeline.py
import fastf1
from src.data_pipeline.fetcher import fetch_race_data
from src.data_pipeline.cleaner import clean_laps_data
from src.data_pipeline.loader import load_race_data

def main():
    print("--- Starting Multi-Year ETL Pipeline ---")
    
    # Loop through multiple historical seasons
    years_to_process = [2021, 2022, 2023]
    
    for year in years_to_process:
        print(f"\n=========================================")
        print(f" FETCHING SEASON: {year}")
        print(f"=========================================")
        
        schedule = fastf1.get_event_schedule(year)
        races = schedule[schedule['EventFormat'] != 'testing']
        
        for index, event in races.iterrows():
            round_num = event['RoundNumber']
            event_name = event['EventName']
            
            print(f" -> Processing {year} Round {round_num}: {event_name}")
            
            try:
                # FastF1 allows you to load weather data by passing weather=True 
                # (You will need to update fetcher.py to handle this extra DataFrame later)
                race_info, raw_laps = fetch_race_data(year, round_num) 
                
                clean_laps = clean_laps_data(raw_laps)
                load_race_data(race_info, clean_laps)
                
            except Exception as e:
                print(f"    [!] FAILED to process {year} Round {round_num}. Error: {e}")
                continue

    print("\n--- Multi-Year Pipeline Complete! ---")

if __name__ == "__main__":
    main()