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

        # Safety Car State
        sc_active = False
        sc_laps_remaining = 0
        
        for lap in range(1, self.total_laps + 1):

            # Stochastic Safety Car Trigger (approx 2% chance per lap)
            if not sc_active and np.random.random() < 0.02:
                sc_active = True
                sc_laps_remaining = np.random.randint(2, 6) # SC lasts 2 to 5 laps
                
            if sc_active:
                sc_laps_remaining -= 1
                if sc_laps_remaining <= 0:
                    sc_active = False

            if lap in pit_laps:
                # Stochastic Pit Stop: Mean of 24s, 5% chance of a 5s delay
                pit_variance = np.random.normal(0, 500) 
                fumble_risk = 5000 if np.random.random() < 0.05 else 0 

                # CHEAP PIT STOP under Safety Car!
                current_pit_loss = (self.pit_loss_mean / 2) if sc_active else self.pit_loss_mean
                
                lap_time = self.base_lap_time + current_pit_loss + pit_variance + fumble_risk
                tire_age = 1
                
                # NEW: Emerge into traffic. You are stuck behind slower cars for the next 3 laps.
                in_traffic_laps = 3 
                
            else:
                traffic_noise = np.random.normal(0, 300) 
                dirty_air = np.random.normal(1500, 500) if in_traffic_laps > 0 else 0
                
                if in_traffic_laps > 0: in_traffic_laps -= 1
                
                # Laps are drastically slower under SC, neutralizing tire advantage
                sc_lap_penalty = 25000 if sc_active else 0
                
                lap_time = self.base_lap_time + (tire_age * self.deg_penalty) + traffic_noise + dirty_air + sc_lap_penalty
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