# run_clustering.py
import numpy as np
from src.models.feature_extractor import get_track_features
from src.models.kmeans import fit_kmeans, normalize_features

def main():
    print("Extracting features from PostgreSQL...")
    features_df = get_track_features()
    
    if features_df.empty:
        print("Error: Not enough data in the database. Ensure Phase 1 pipeline has finished.")
        return

    # Extract the circuit names for labeling later
    circuit_names = features_df['circuit_name'].values
    
    # Convert our three features into a NumPy matrix
    feature_matrix = features_df[['base_lap_time', 'pit_loss_penalty', 'tire_deg_penalty']].values
    
    print("\nNormalizing data...")
    X_scaled, means, stds = normalize_features(feature_matrix)
    
    # Run our custom K-Means! Let's group the calendar into 4 distinct logistical profiles.
    k_clusters = 4
    print(f"\nRunning custom k-Means clustering with k={k_clusters}...")
    centroids, labels = fit_kmeans(X_scaled, k=k_clusters, max_iters=100)
    
    # Display the results
    print("\n==============================")
    print("FINAL TRACK CLUSTER ASSIGNMENTS")
    print("==============================\n")
    
    features_df['Cluster'] = labels
    
    for i in range(k_clusters):
        tracks_in_cluster = features_df[features_df['Cluster'] == i]['circuit_name'].tolist()
        print(f"Cluster {i} (Count: {len(tracks_in_cluster)}):")
        for track in tracks_in_cluster:
            print(f"  - {track}")
        print("-" * 30)

if __name__ == "__main__":
    main()