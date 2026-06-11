# run_dynamic_simulation.py
from src.models.mdp_solver import RaceMDP
from src.models.monte_carlo import RaceSimulator

def main():
    total_laps = 57
    base_lap_time = 95000  
    pit_loss = 24000       
    deg_penalty = 200      
    ruin_threshold = 5660000 
    num_seasons = 10000

    print("--- 1. Training MDP (The Brain) ---")
    mdp = RaceMDP(total_laps, base_lap_time, pit_loss, deg_penalty)
    mdp.solve()
    policy_matrix = mdp.policy # Extract the 3D policy array
    print("MDP Solved. Policy generated.")

    print(f"\n--- 2. Running Monte Carlo Simulations ({num_seasons} Seasons) ---")
    simulator = RaceSimulator(total_laps, base_lap_time, pit_loss, deg_penalty)

    # Strategy 1: The Reactive AI (Pass the policy matrix)
    exp_time_ai, risk_ai = simulator.run_monte_carlo(
        strategy_name="Reactive AI", 
        num_simulations=num_seasons, 
        ruin_threshold=ruin_threshold, 
        mdp_policy=policy_matrix
    )
    
    # Strategy 2: The Static 2-Stop (Pass the hardcoded laps)
    static_laps = [19, 38]
    exp_time_static, risk_static = simulator.run_monte_carlo(
        strategy_name="Static 2-Stop", 
        num_simulations=num_seasons, 
        ruin_threshold=ruin_threshold, 
        static_pit_laps=static_laps
    )

    print("\n[ Final Results ]")
    print(f"Strategy: Reactive AI (Dynamic 2-Stop / Plan B SC Pivot)")
    print(f" -> Expected Return (Avg Time): {exp_time_ai / 1000:.2f} seconds")
    print(f" -> Risk of Ruin: {risk_ai:.1f}%")
    
    print(f"\nStrategy: Static 2-Stop {static_laps}")
    print(f" -> Expected Return (Avg Time): {exp_time_static / 1000:.2f} seconds")
    print(f" -> Risk of Ruin: {risk_static:.1f}%")

if __name__ == "__main__":
    main()