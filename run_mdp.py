# run_mdp.py
from src.models.mdp_solver import RaceMDP

def main():
    # Cluster 0 Averages (Approximations for a track like Bahrain)
    total_laps = 57
    base_lap_time = 95000  # 95 seconds in milliseconds
    pit_loss = 24000       # 24 seconds lost in the pit lane
    deg_penalty = 200      # 0.2 seconds lost per lap of tire age

    print("--- Initializing F1 Strategy MDP ---")
    print(f"Race Length: {total_laps} Laps")
    print(f"Base Lap: {base_lap_time/1000}s | Pit Loss: {pit_loss/1000}s | Deg/Lap: {deg_penalty/1000}s\n")

    # Initialize the environment
    mdp = RaceMDP(total_laps, base_lap_time, pit_loss, deg_penalty)

    print("Solving Bellman Equation via Backward Induction...")
    mdp.solve()

    print("\n==============================")
    print("   OPTIMAL RACE STRATEGY")
    print("==============================")
    
    strategy = mdp.get_optimal_strategy()
    for event in strategy:
        print(f" -> {event}")
        
    print("==============================\n")

if __name__ == "__main__":
    main()