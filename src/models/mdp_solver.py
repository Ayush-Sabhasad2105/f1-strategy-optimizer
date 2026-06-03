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
        
        # Value table: dimensions are (Total Laps + 1) x (Max possible tire age)
        # We add 1 to laps to represent the terminal state (race finish)
        self.V = np.zeros((self.total_laps + 1, self.total_laps + 1))
        
        # Policy table to store the best action: 0 for 'Stay Out', 1 for 'Pit'
        self.policy = np.zeros((self.total_laps, self.total_laps + 1), dtype=int)

    def calculate_lap_cost(self, tire_age, action):
        """Returns the time cost of a single lap given the tire age and action."""
        if action == 'Pit':
            # Heavy immediate time loss, but tires are fresh for THIS lap
            return self.base_lap_time + self.pit_loss
        else:
            # Slower lap times as tires get older. 
            # (Assuming a simple linear degradation model for the baseline)
            return self.base_lap_time + (tire_age * self.deg_penalty)

    def solve(self):
        """Runs Backward Induction (Value Iteration) to find the optimal strategy."""
        
        # Terminal state: at lap = total_laps, the race is over, remaining cost is 0.
        self.V[self.total_laps, :] = 0 
        
        # Work backwards from the last lap to the first lap
        for lap in range(self.total_laps - 1, -1, -1):
            # The maximum possible tire age at this lap is 'lap' itself
            for tire_age in range(lap + 1):
                
                # Option 1: Stay Out
                cost_stay = self.calculate_lap_cost(tire_age, 'Stay Out')
                # Next state: lap advances by 1, tire age advances by 1
                val_stay = cost_stay + self.V[lap + 1, tire_age + 1]
                
                # Option 2: Pit
                cost_pit = self.calculate_lap_cost(tire_age, 'Pit')
                # Next state: lap advances by 1, tire age resets to 1 
                # (since we just drove 1 lap on the new tires)
                val_pit = cost_pit + self.V[lap + 1, 1]
                
                # Bellman update: choose the action that minimizes total remaining time
                if val_stay <= val_pit:
                    self.V[lap, tire_age] = val_stay
                    self.policy[lap, tire_age] = 0 # 0 represents Stay Out
                else:
                    self.V[lap, tire_age] = val_pit
                    self.policy[lap, tire_age] = 1 # 1 represents Pit

    def get_optimal_strategy(self):
        """Traces the policy table forward to map out the optimal pit stops."""
        strategy = []
        current_tire_age = 0
        
        for lap in range(self.total_laps):
            action = self.policy[lap, current_tire_age]
            
            if action == 1:
                strategy.append(f"Lap {lap + 1}: PIT")
                current_tire_age = 1
            else:
                current_tire_age += 1
                
        if not strategy:
            strategy.append("Zero-Stop Strategy (Unlikely but mathematically possible!)")
            
        return strategy