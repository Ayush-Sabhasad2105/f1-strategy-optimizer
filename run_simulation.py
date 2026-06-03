# run_simulation.py
from src.models.monte_carlo import RaceSimulator

def main():
    # Environment variables (Cluster 0)
    total_laps = 57
    base_lap_time = 95000  
    pit_loss = 24000       
    deg_penalty = 200      
    
    # We define 'Ruin' as a total race time slower than 5,660,000 ms (approx 1h 34m 20s)
    ruin_threshold = 5660000 

    simulator = RaceSimulator(total_laps, base_lap_time, pit_loss, deg_penalty)

    print("--- Running Monte Carlo Simulations (1000 Seasons) ---")

    # Strategy 1: The MDP's Aggressive 3-Stop
    strat_3_stop = [16, 30, 44]
    exp_time_3, risk_3 = simulator.run_monte_carlo("Aggressive 3-Stop", strat_3_stop, 1000, ruin_threshold)
    
    # Strategy 2: A Conservative 2-Stop
    strat_2_stop = [19, 38]
    exp_time_2, risk_2 = simulator.run_monte_carlo("Conservative 2-Stop", strat_2_stop, 1000, ruin_threshold)

    print("\n[ Results ]")
    print(f"Strategy: Aggressive 3-Stop {strat_3_stop}")
    print(f" -> Expected Return (Avg Time): {exp_time_3 / 1000:.2f} seconds")
    print(f" -> Risk of Ruin: {risk_3:.1f}%")
    
    print(f"\nStrategy: Conservative 2-Stop {strat_2_stop}")
    print(f" -> Expected Return (Avg Time): {exp_time_2 / 1000:.2f} seconds")
    print(f" -> Risk of Ruin: {risk_2:.1f}%")
    
    print("\nAnalysis: Does the extra pit stop introduce too much fumble risk to justify the tire advantage?")

if __name__ == "__main__":
    main()