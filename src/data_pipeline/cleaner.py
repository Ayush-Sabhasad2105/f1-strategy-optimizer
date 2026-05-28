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
    clean_laps['is_pit_in_lap'] = clean_laps['PitInTime'].notnull()
    
    clean_laps.drop(columns=['PitOutTime', 'PitInTime'], inplace=True)
    
    return clean_laps