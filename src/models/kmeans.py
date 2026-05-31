# src/models/kmeans.py
import numpy as np

def initialize_centroids(data, k, strategy='random', custom_points=None):
    """
    Initializes k centroids based on the chosen strategy.
    
    Parameters:
    - data: np.ndarray of shape (N, D) containing N tracks and D features.
    - k: int, number of clusters.
    - strategy: 'random', 'k-means++', or 'custom'.
    - custom_points: np.ndarray of shape (k, D) if strategy is 'custom'.
    """
    if strategy == 'custom' and custom_points is not None:
        return np.array(custom_points, dtype=float)
        
    if strategy == 'random':
        # Randomly select k unique rows from the dataset
        indices = np.random.choice(data.shape[0], k, replace=False)
        return data[indices].copy()
        
    raise ValueError(f"Unknown strategy: {strategy}")

def assign_clusters(data, centroids):
    """
    Assigns each data point to the closest centroid using Euclidean distance.
    
    Returns:
    - labels: np.ndarray of shape (N,) containing cluster indices (0 to k-1).
    """
    # Expanded dimensions to leverage NumPy broadcasting for distance calculation
    # data: (N, 1, D) and centroids: (1, k, D) -> results in (N, k, D) matrix
    distances = np.linalg.norm(data[:, np.newaxis, :] - centroids[np.newaxis, :, :], axis=2)
    
    # Return the index of the minimum distance for each point
    return np.argmin(distances, axis=1)

def update_centroids(data, labels, k):
    """
    Recalculates the centroids as the mean of all points assigned to each cluster.
    
    Returns:
    - new_centroids: np.ndarray of shape (k, D)
    """
    num_features = data.shape[1]
    new_centroids = np.zeros((k, num_features))
    
    for i in range(k):
        # Extract all points belonging to cluster i
        cluster_points = data[labels == i]
        
        if len(cluster_points) > 0:
            new_centroids[i] = np.mean(cluster_points, axis=0)
        else:
            # Handle empty cluster edge-case by leaving it or re-initializing
            new_centroids[i] = data[np.random.choice(data.shape[0])]
            
    return new_centroids

def fit_kmeans(data, k, max_iters=100, tol=1e-4, strategy='random', custom_points=None):
    """
    Runs the complete k-means loop until convergence or max iterations are reached.
    """
    centroids = initialize_centroids(data, k, strategy, custom_points)
    
    for iteration in range(max_iters):
        old_centroids = centroids.copy()
        
        # 1. Assign Step
        labels = assign_clusters(data, centroids)
        
        # 2. Update Step
        centroids = update_centroids(data, labels, k)
        
        # Check for convergence (if centroids move less than the tolerance threshold)
        centroid_shift = np.linalg.norm(centroids - old_centroids)
        if centroid_shift < tol:
            print(f"K-Means converged after {iteration + 1} iterations.")
            break
            
    return centroids, labels

def normalize_features(data_matrix):
    """
    Applies Z-score normalization: (X - Mean) / Standard Deviation.
    Ensures all features contribute equally to the Euclidean distance calculation.
    """
    # Calculate mean and standard deviation for each column (feature)
    means = np.mean(data_matrix, axis=0)
    stds = np.std(data_matrix, axis=0)
    
    # Prevent division by zero if a feature has no variance
    stds[stds == 0] = 1 
    
    normalized_data = (data_matrix - means) / stds
    return normalized_data, means, stds