# src/models/mdp_solver.py
import numpy as np

class RaceMDP:
    def __init__(self, total_laps, base_lap_time, pit_loss, deg_penalty_per_lap):
        """
        Initializes the F1 Strategy MDP.
        All time values should be in milliseconds.
        """
        self.total_laps = total_laps
        self.base_lap_time = base_lap_time
        self.pit_loss = pit_loss
        self.deg_penalty = deg_penalty_per_lap
        self.traffic_penalty = 1500 # 1.5 seconds lost per lap in dirty air
        
        # 3D State Space: (Lap) x (Tire Age) x (Traffic Laps Remaining: 0, 1, 2, 3)
        self.V = np.zeros((self.total_laps + 1, self.total_laps + 1, 4))

        # Policy table to store the best action: 0 for 'Stay Out', 1 for 'Pit'
        self.policy = np.zeros((self.total_laps, self.total_laps + 1, 4), dtype=int)

    def calculate_lap_cost(self, tire_age, traffic_laps, action):
        """Returns the time cost of a single lap given the tire age and action."""

        traffic_cost = self.traffic_penalty if traffic_laps > 0 else 0
        if action == 'Pit':
            # Heavy immediate time loss, but tires are fresh for THIS lap
            return self.base_lap_time + self.pit_loss
        else:
            # Slower lap times as tires get older. 
            # (Assuming a simple linear degradation model for the baseline)
            return self.base_lap_time + (tire_age * self.deg_penalty) + traffic_cost

    def solve(self):
        """Runs Backward Induction (Value Iteration) to find the optimal strategy."""
        
        # Terminal state: at lap = total_laps, the race is over, remaining cost is 0.
        self.V[self.total_laps, :, :] = 0 
        
        # Work backwards from the last lap to the first lap
        for lap in range(self.total_laps - 1, -1, -1):
            for tire_age in range(lap + 1):
                for traffic in range(4): # 0 to 3 laps of traffic
                    
                    # Option 1: Stay Out
                    cost_stay = self.calculate_lap_cost(tire_age, traffic, 'Stay Out')
                    next_traffic = max(0, traffic - 1)
                    val_stay = cost_stay + self.V[lap + 1, tire_age + 1, next_traffic]
                    
                    # Option 2: Pit
                    cost_pit = self.calculate_lap_cost(tire_age, traffic, 'Pit')
                    # Pitting resets tire age to 1, but forces 3 laps of traffic
                    val_pit = cost_pit + self.V[lap + 1, 1, 3] 
                    
                    if val_stay <= val_pit:
                        self.V[lap, tire_age, traffic] = val_stay
                        self.policy[lap, tire_age, traffic] = 0 # Stay Out
                    else:
                        self.V[lap, tire_age, traffic] = val_pit
                        self.policy[lap, tire_age, traffic] = 1 # Pit

    def get_optimal_strategy(self):
        """Traces the policy table forward to map out the optimal pit stops."""

        strategy = []
        current_tire_age = 0
        current_traffic = 0
        
        for lap in range(self.total_laps):
            action = self.policy[lap, current_tire_age, current_traffic]
            
            if action == 1:
                strategy.append(f"Lap {lap + 1}: PIT")
                current_tire_age = 1
                current_traffic = 3 # Emerge into traffic
            else:
                current_tire_age += 1
                current_traffic = max(0, current_traffic - 1)
                
        if not strategy:
            strategy.append("Zero-Stop Strategy (Unlikely but mathematically possible!)")
            
        return strategy