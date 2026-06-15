import fastf1
import pandas as pd
import os

cache_dir = os.path.join(os.path.dirname(__file__), '../../data/raw')
os.makedirs(cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(cache_dir)

def fetch_race_data(year, round_number):

    """Downloads session telemetry from FastF1."""
    print(f"Fetching Year: {year}, Round: {round_number} from FastF1 servers...")

    session = fastf1.get_session(year, round_number, 'R')
    session.load(telemetry=False, weather=True)

    race_info = {
        'year' : year,
        'round_number' : round_number,
        'circuit_name' : session.event['EventName']
    }

    return race_info, session.laps