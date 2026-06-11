# src/models/mdp_solver.py
import numpy as np

class RaceMDP:
    # NEW: Added max_traffic_laps parameter (defaults to 3 for standard races)
    def __init__(self, total_laps, base_lap_time, pit_loss, deg_penalty, max_traffic_laps=3):
        self.total_laps = total_laps
        self.base_lap_time = base_lap_time
        self.pit_loss = pit_loss
        self.deg_penalty = deg_penalty
        self.traffic_penalty = 1500 
        self.max_traffic = max_traffic_laps 
        
        # 3D State Space now scales dynamically based on max_traffic
        self.V = np.zeros((self.total_laps + 1, self.total_laps + 1, self.max_traffic + 1))
        self.policy = np.zeros((self.total_laps, self.total_laps + 1, self.max_traffic + 1), dtype=int)

    def calculate_lap_cost(self, tire_age, traffic_laps, action):
        traffic_cost = self.traffic_penalty if traffic_laps > 0 else 0
        
        if action == 'Pit':
            return self.base_lap_time + self.pit_loss 
        else:
            return self.base_lap_time + (tire_age * self.deg_penalty) + traffic_cost

    def solve(self):
        self.V[self.total_laps, :, :] = 0 
        
        for lap in range(self.total_laps - 1, -1, -1):
            for tire_age in range(lap + 1):
                # Update loop to use dynamic max_traffic
                for traffic in range(self.max_traffic + 1): 
                    
                    cost_stay = self.calculate_lap_cost(tire_age, traffic, 'Stay Out')
                    next_traffic = max(0, traffic - 1)
                    val_stay = cost_stay + self.V[lap + 1, tire_age + 1, next_traffic]
                    
                    cost_pit = self.calculate_lap_cost(tire_age, traffic, 'Pit')
                    # Pitting forces max_traffic laps of dirty air
                    val_pit = cost_pit + self.V[lap + 1, 1, self.max_traffic] 
                    
                    if val_stay <= val_pit:
                        self.V[lap, tire_age, traffic] = val_stay
                        self.policy[lap, tire_age, traffic] = 0 
                    else:
                        self.V[lap, tire_age, traffic] = val_pit
                        self.policy[lap, tire_age, traffic] = 1

    def get_optimal_strategy(self):
        """Returns a deterministic trace of the optimal strategy (assuming no safety cars)."""
        strategy = []
        tire_age = 0
        traffic = 0
        for lap in range(self.total_laps):
            # Bound tire_age to avoid index out of bounds in edge cases
            safe_age = min(tire_age, self.total_laps)
            safe_traffic = min(traffic, self.max_traffic)
            action = self.policy[lap, safe_age, safe_traffic]
            if action == 1:
                strategy.append(f"Lap {lap + 1}: PIT")
                tire_age = 1
                traffic = self.max_traffic
            else:
                tire_age += 1
                traffic = max(0, traffic - 1)
        return strategy