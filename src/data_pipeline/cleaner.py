import pandas as pd

def clean_laps_data(raw_laps):
    """Transforms raw timedeltas into database-ready integers and booleans."""
    print("Raw data downloaded. Beginning transformation...")
    laps = raw_laps.copy()

    laps['LapTime_ms'] = laps['LapTime'].dt.total_seconds() * 1000
    laps['Sector1_ms'] = laps['Sector1Time'].dt.total_seconds() * 1000
    laps['Sector2_ms'] = laps['Sector2Time'].dt.total_seconds() * 1000
    laps['Sector3_ms'] = laps['Sector3Time'].dt.total_seconds() * 1000

    laps.fillna({'LapTime_ms': 0, 'Sector1_ms': 0, 'Sector2_ms': 0, 'Sector3_ms': 0, 'TyreLife': 0}, inplace=True)
    
    clean_laps = laps[['Driver', 'LapNumber', 'LapTime_ms', 'Sector1_ms', 'Sector2_ms', 'Sector3_ms', 'Compound', 'TyreLife', 'PitOutTime', 'PitInTime', 'TrackStatus']].copy()

    clean_laps['is_pit_out_lap'] = clean_laps['PitOutTime'].notnull()
    clean_laps['is_pit_in_lap']  = clean_laps['PitInTime'].notnull()
    
    clean_laps.drop(columns=['PitOutTime', 'PitInTime'], inplace=True)
    
    return clean_laps


def clean_weather_data(weather_df, raw_laps):
    """Summarises a race's time-series weather into a single-row dict.

    FastF1 weather_data columns:
        Time, AirTemp, Humidity, Pressure, Rainfall, TrackTemp,
        WindDirection, WindSpeed

    Returns a dict with:
        avg_track_temp_c  – mean track surface temperature across the race
        avg_air_temp_c    – mean ambient air temperature
        avg_humidity_pct  – mean relative humidity
        had_rainfall      – True if INTERMEDIATE or WET tires were used

    These values are stored per race in the Races table and are used by
    feature_extractor.py to exclude wet-weather races from tire-deg and
    pit-loss calculations (wet races have completely different strategies
    that would corrupt the dry-weather model).
    """
    # 1. Check if the race was actually "wet" by seeing if any driver
    # used Intermediate or Wet tires. This is much more reliable than
    # the weather sensor which can log "True" for a few drops of rain
    # that don't affect strategy (e.g. Monaco 2019).
    compounds_used = raw_laps['Compound'].unique()
    is_wet_race = bool(any(c in ['INTERMEDIATE', 'WET'] for c in compounds_used))

    if weather_df is None or weather_df.empty:
        return {
            'avg_track_temp_c': None,
            'avg_air_temp_c':   None,
            'avg_humidity_pct': None,
            'had_rainfall':     False,
        }

    return {
        'avg_track_temp_c': round(float(weather_df['TrackTemp'].mean()), 1),
        'avg_air_temp_c':   round(float(weather_df['AirTemp'].mean()),   1),
        'avg_humidity_pct': round(float(weather_df['Humidity'].mean()),   1),
        'had_rainfall':     is_wet_race,
    }