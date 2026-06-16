# src/models/mdp_solver.py
import numpy as np

class RaceMDP:
    def __init__(self, total_laps, base_lap_time, pit_loss, deg_penalty, max_traffic_laps=3, starting_compound="Medium"):
        self.total_laps = total_laps
        self.base_lap_time = base_lap_time
        self.pit_loss = pit_loss
        self.deg_penalty = deg_penalty
        self.traffic_penalty = 1500 
        self.max_traffic = max_traffic_laps 
        self.starting_compound = starting_compound
        
        # Compound Mapping: 0=Soft, 1=Medium, 2=Hard
        self.compounds = {0: "Soft", 1: "Medium", 2: "Hard"}
        self.compound_map = {"Soft": 0, "Medium": 1, "Hard": 2}
        
        # 5D State Space: [lap, tire_age, traffic, current_compound, has_switched]
        self.V = np.zeros((self.total_laps + 1, self.total_laps + 1, self.max_traffic + 1, 3, 2))
        
        # Action space: 0=Stay, 1=Pit(Soft), 2=Pit(Medium), 3=Pit(Hard)
        self.policy = np.zeros((self.total_laps, self.total_laps + 1, self.max_traffic + 1, 3, 2), dtype=int)

    def calculate_lap_cost(self, tire_age, traffic_laps, compound_idx, action):
        traffic_cost = self.traffic_penalty if traffic_laps > 0 else 0
        
        if compound_idx == 0:    # Soft
            current_deg = int(self.deg_penalty * 2.0)
            current_base = self.base_lap_time - 600
        elif compound_idx == 2:  # Hard
            current_deg = int(self.deg_penalty * 0.75)
            current_base = self.base_lap_time + 600
        else:                    # Medium
            current_deg = self.deg_penalty
            current_base = self.base_lap_time
        
        if action == 'Pit':
            return current_base + self.pit_loss 
        else:
            return current_base + (tire_age * current_deg) + traffic_cost

    def solve(self):
        # Base cases: End of race
        self.V[self.total_laps, :, :, :, :] = 0 
        
        # Enforce two-compound rule: infinite cost if race ends and has_switched == 0
        penalty = 1e9
        self.V[self.total_laps, :, :, :, 0] = penalty
        
        for lap in range(self.total_laps - 1, -1, -1):
            for tire_age in range(lap + 1):
                for traffic in range(self.max_traffic + 1): 
                    for comp in range(3):
                        for switched in range(2):
                            
                            # Option 0: Stay Out
                            cost_stay = self.calculate_lap_cost(tire_age, traffic, comp, 'Stay Out')
                            next_traffic = max(0, traffic - 1)
                            val_stay = cost_stay + self.V[lap + 1, tire_age + 1, next_traffic, comp, switched]
                            
                            best_val = val_stay
                            best_action = 0
                            
                            # Options 1, 2, 3: Pit for Soft, Medium, Hard
                            # Note: Pitting takes place at the end of the lap. The current lap is run on the OLD tire.
                            cost_pit = self.calculate_lap_cost(tire_age, traffic, comp, 'Pit')
                            
                            for next_comp in range(3):
                                next_switched = 1 if next_comp != comp else switched
                                val_pit = cost_pit + self.V[lap + 1, 1, self.max_traffic, next_comp, next_switched]
                                
                                if val_pit < best_val:
                                    best_val = val_pit
                                    best_action = next_comp + 1
                                    
                            self.V[lap, tire_age, traffic, comp, switched] = best_val
                            self.policy[lap, tire_age, traffic, comp, switched] = best_action

    def get_optimal_strategy(self):
        """Returns a deterministic trace of the optimal strategy (assuming no safety cars)."""
        strategy = []
        tire_age = 0
        traffic = 0
        current_comp = self.compound_map.get(self.starting_compound, 1)
        has_switched = 0
        
        for lap in range(self.total_laps):
            safe_age = min(tire_age, self.total_laps)
            safe_traffic = min(traffic, self.max_traffic)
            
            action = self.policy[lap, safe_age, safe_traffic, current_comp, has_switched]
            
            if action > 0:
                next_comp = action - 1
                strategy.append({"lap": lap + 1, "compound": self.compounds[next_comp]})
                
                if next_comp != current_comp:
                    has_switched = 1
                current_comp = next_comp
                tire_age = 1
                traffic = self.max_traffic
            else:
                tire_age += 1
                traffic = max(0, traffic - 1)
                
        return strategy