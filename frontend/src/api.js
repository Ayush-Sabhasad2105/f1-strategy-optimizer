// frontend/src/api.js
const BASE_URL = "/api";

/**
 * Fetches all available F1 tracks with cluster assignments.
 * @returns {Promise<Array>}
 */
export async function fetchTracks() {
  const res = await fetch(`${BASE_URL}/tracks/`);
  if (!res.ok) throw new Error(`Failed to fetch tracks: ${res.statusText}`);
  return res.json();
}

/**
 * Computes the optimal race strategy.
 * @param {Object} payload  - Matches the StrategyRequest Pydantic model.
 * @returns {Promise<Object>}
 */
export async function computeStrategy(payload) {
  const res = await fetch(`${BASE_URL}/strategy/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Strategy API error: ${res.statusText}`);
  }
  return res.json();
}
