// frontend/src/components/TrackClusterChart.jsx
import React from "react";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ZAxis, Cell,
} from "recharts";

const CLUSTER_COLORS = ["#f59e0b", "#8b5cf6", "#10b981", "#ef4444"];
const CLUSTER_LABELS = ["Power Circuit", "Technical/Street", "Long Pit Lane", "Extreme Deg"];

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div style={{
      background: "var(--bg-card)",
      border: "1px solid var(--border-subtle)",
      borderRadius: "8px",
      padding: "10px 14px",
      fontSize: "12px",
      minWidth: 160,
    }}>
      <p style={{ fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>{d.name}</p>
      <p style={{ color: "var(--text-muted)" }}>Deg/lap: <span style={{ color: "var(--text-primary)" }}>{d.x} ms</span></p>
      <p style={{ color: "var(--text-muted)" }}>Pit loss: <span style={{ color: "var(--text-primary)" }}>{d.y.toFixed(0)} ms</span></p>
      <p style={{ color: CLUSTER_COLORS[d.cluster], marginTop: 4, fontWeight: 600 }}>
        Cluster {d.cluster}: {CLUSTER_LABELS[d.cluster]}
      </p>
    </div>
  );
};

/**
 * @param {Array} tracks  - Array of TrackInfo objects from the API
 * @param {string} selectedTrack - Currently selected circuit name
 */
export default function TrackClusterChart({ tracks, selectedTrack }) {
  if (!tracks || tracks.length === 0) {
    return (
      <div className="empty-state" style={{ padding: 40 }}>
        <p>No track data available</p>
      </div>
    );
  }

  const points = tracks.map(t => ({
    x: t.tire_deg_ms_per_lap,
    y: t.pit_loss_ms / 1000,          // convert to seconds for readability
    name: t.circuit_name,
    cluster: t.cluster,
    isSelected: t.circuit_name.toLowerCase() === selectedTrack?.toLowerCase(),
  }));

  // Group by cluster for separate Scatter series (enables individual legend items)
  const clusters = [0, 1, 2, 3].map(c => points.filter(p => p.cluster === c));

  return (
    <>
      <div style={{ width: "100%", height: 240 }}>
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 4, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis
              type="number"
              dataKey="x"
              name="Tire Degradation"
              tick={{ fill: "var(--text-muted)", fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: "var(--border-subtle)" }}
              tickFormatter={v => `${v}ms`}
              label={{ value: "Tire Deg (ms/lap)", position: "insideBottom", offset: -2, fill: "var(--text-muted)", fontSize: 10 }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Pit Loss"
              tick={{ fill: "var(--text-muted)", fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={v => `${v}s`}
              width={36}
            />
            <ZAxis range={[40, 120]} />
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3" }} />

            {clusters.map((clusterPoints, cIdx) => (
              <Scatter
                key={cIdx}
                name={CLUSTER_LABELS[cIdx]}
                data={clusterPoints}
                fill={CLUSTER_COLORS[cIdx]}
              >
                {clusterPoints.map((p, i) => (
                  <Cell
                    key={i}
                    fill={CLUSTER_COLORS[cIdx]}
                    opacity={p.isSelected ? 1 : 0.5}
                    stroke={p.isSelected ? "white" : "none"}
                    strokeWidth={p.isSelected ? 2 : 0}
                    r={p.isSelected ? 8 : 5}
                  />
                ))}
              </Scatter>
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Cluster legend */}
      <div className="cluster-legend">
        {CLUSTER_LABELS.map((label, i) => (
          <div key={i} className="cluster-legend-item">
            <div className="cluster-color-chip" style={{ background: CLUSTER_COLORS[i] }} />
            <span>Cluster {i}: {label}</span>
          </div>
        ))}
      </div>
    </>
  );
}
