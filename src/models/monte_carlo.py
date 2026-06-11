# src/models/monte_carlo.py
import numpy as np

class RaceSimulator:
    def __init__(self, total_laps, base_lap_time, pit_loss_mean, deg_penalty):
        self.total_laps = total_laps
        self.base_lap_time = base_lap_time
        self.pit_loss_mean = pit_loss_mean
        self.deg_penalty = deg_penalty
        
    def simulate_single_race(self, mdp_policy=None, static_pit_laps=None):
        """Simulates one complete race dynamically querying the MDP policy."""
        total_time = 0
        tire_age = 0
        in_traffic_laps = 0

        sc_active = False
        sc_laps_remaining = 0
        
        for lap in range(1, self.total_laps + 1):
            # Stochastic Safety Car Trigger
            if not sc_active and np.random.random() < 0.02:
                sc_active = True
                sc_laps_remaining = np.random.randint(2, 6)
                
            if sc_active:
                sc_laps_remaining -= 1
                if sc_laps_remaining <= 0:
                    sc_active = False

            # --- DYNAMIC ACTION DECISION ---
            is_pitting = False
            
            if mdp_policy is not None:
                # Query the 3D MDP: State = [lap_index, tire_age, traffic_laps]
                safe_tire_age = min(tire_age, self.total_laps)
                action_code = mdp_policy[lap - 1, safe_tire_age, in_traffic_laps]
                
                # PLAN B (Reactive Strategy): 
                # If Safety Car is out and tires are more than 10 laps old, take the cheap pit stop!
                if sc_active and tire_age > 10:
                    is_pitting = True
                else:
                    is_pitting = (action_code == 1) # 1 means PIT according to MDP
            elif static_pit_laps is not None:
                # Fallback to static strategy if no policy is provided
                is_pitting = (lap in static_pit_laps)

            # --- EXECUTE LAP ---
            if is_pitting:
                pit_variance = np.random.normal(0, 500) 
                fumble_risk = 5000 if np.random.random() < 0.05 else 0 

                current_pit_loss = (self.pit_loss_mean / 2) if sc_active else self.pit_loss_mean
                
                lap_time = self.base_lap_time + current_pit_loss + pit_variance + fumble_risk
                tire_age = 1
                in_traffic_laps = 3 
            else:
                traffic_noise = np.random.normal(0, 300) 
                dirty_air = np.random.normal(1500, 500) if in_traffic_laps > 0 else 0
                
                if in_traffic_laps > 0: in_traffic_laps -= 1
                
                sc_lap_penalty = 25000 if sc_active else 0
                
                lap_time = self.base_lap_time + (tire_age * self.deg_penalty) + traffic_noise + dirty_air + sc_lap_penalty
                tire_age += 1
                
            total_time += lap_time
            
        return total_time

    def run_monte_carlo(self, strategy_name, num_simulations=1000, ruin_threshold=5650000, mdp_policy=None, static_pit_laps=None):
        """Runs N simulations."""
        results = []
        ruin_count = 0
        
        for _ in range(num_simulations):
            race_time = self.simulate_single_race(mdp_policy=mdp_policy, static_pit_laps=static_pit_laps)
            results.append(race_time)
            
            if race_time > ruin_threshold:
                ruin_count += 1
                
        expected_return = np.mean(results)
        risk_of_ruin = (ruin_count / num_simulations) * 100
        
        return expected_return, risk_of_ruin