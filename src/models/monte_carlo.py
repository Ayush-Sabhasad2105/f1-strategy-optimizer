# src/models/monte_carlo.py
import numpy as np

class RaceSimulator:
    def __init__(self, total_laps, base_lap_time, pit_loss_mean, deg_penalty):
        self.total_laps = total_laps
        self.base_lap_time = base_lap_time
        self.pit_loss_mean = pit_loss_mean
        self.deg_penalty = deg_penalty
        
    def simulate_single_race(self, pit_laps):
        """Simulates one complete race with stochastic variables and Traffic Penalties."""
        total_time = 0
        tire_age = 0
        in_traffic_laps = 0  # NEW: Counter for dirty air
        
        for lap in range(1, self.total_laps + 1):
            if lap in pit_laps:
                # Stochastic Pit Stop: Mean of 24s, 5% chance of a 5s delay
                pit_variance = np.random.normal(0, 500) 
                fumble_risk = 5000 if np.random.random() < 0.05 else 0 
                
                lap_time = self.base_lap_time + self.pit_loss_mean + pit_variance + fumble_risk
                tire_age = 1
                
                # NEW: Emerge into traffic. You are stuck behind slower cars for the next 3 laps.
                in_traffic_laps = 3 
            else:
                # Standard ambient variance
                traffic_noise = np.random.normal(0, 300) 
                
                # NEW: Apply the Dirty Air Penalty
                dirty_air_penalty = 0
                if in_traffic_laps > 0:
                    # Lose an average of 1.5 seconds per lap while trying to pass
                    dirty_air_penalty = np.random.normal(1500, 500) 
                    in_traffic_laps -= 1
                
                lap_time = self.base_lap_time + (tire_age * self.deg_penalty) + traffic_noise + dirty_air_penalty
                tire_age += 1
                
            total_time += lap_time
            
        return total_time

    def run_monte_carlo(self, strategy_name, pit_laps, num_simulations=1000, ruin_threshold=5650000):
        """Runs N simulations to evaluate expected return and risk of ruin."""
        results = []
        ruin_count = 0
        
        for _ in range(num_simulations):
            race_time = self.simulate_single_race(pit_laps)
            results.append(race_time)
            
            # Risk of Ruin: If the race time exceeds our threshold (e.g., dropping out of the points)
            if race_time > ruin_threshold:
                ruin_count += 1
                
        expected_return = np.mean(results)
        risk_of_ruin = (ruin_count / num_simulations) * 100
        
        return expected_return, risk_of_ruin