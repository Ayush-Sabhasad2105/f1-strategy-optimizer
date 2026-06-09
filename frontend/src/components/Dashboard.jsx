// frontend/src/components/Dashboard.jsx
import React from "react";
import {
  Flag, Timer, AlertTriangle, TrendingDown, Activity, Layers,
} from "lucide-react";
import KpiCard from "./KpiCard";
import RiskDistributionChart from "./RiskDistributionChart";
import TrackClusterChart from "./TrackClusterChart";

function formatRaceTime(seconds) {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = (seconds % 60).toFixed(1);
  return `${h}h ${m}m ${s}s`;
}

function buildStrategyLabel(events) {
  if (!events || events.length === 0) return "0-Stop";
  const laps = events.map(e => `L${e.lap}`).join(", ");
  return `${events.length}-Stop: ${laps}`;
}

export default function Dashboard({ result, tracks, selectedTrack, isLoading }) {

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="dashboard-grid">
        <div className="kpi-row">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="kpi-card" style={{ minHeight: 110 }}>
              <div className="skeleton" style={{ height: 14, width: "50%", marginBottom: 12 }} />
              <div className="skeleton" style={{ height: 32, width: "80%", marginBottom: 8 }} />
              <div className="skeleton" style={{ height: 10, width: "60%" }} />
            </div>
          ))}
        </div>
        <div className="chart-grid">
          <div className="chart-card">
            <div className="skeleton" style={{ height: 14, width: "40%", marginBottom: 20 }} />
            <div className="skeleton" style={{ height: 280 }} />
          </div>
          <div className="chart-card">
            <div className="skeleton" style={{ height: 14, width: "40%", marginBottom: 20 }} />
            <div className="skeleton" style={{ height: 280 }} />
          </div>
        </div>
      </div>
    );
  }

  // ── Initial / empty state ─────────────────────────────────────────────────
  if (!result) {
    return (
      <div className="dashboard-grid">
        {/* Track Cluster chart is always visible once tracks load */}
        <div className="chart-grid" style={{ gridTemplateColumns: "1fr" }}>
          <div className="chart-card">
            <div className="chart-header">
              <div>
                <div className="chart-title">Track Cluster Map</div>
                <div className="chart-subtitle">k-Means (k=4) — Tire Degradation vs Pit-Lane Loss</div>
              </div>
              <div className="chart-legend">
                <span className="legend-item"><span className="legend-dot" style={{ background: "#f59e0b" }} />Power</span>
                <span className="legend-item"><span className="legend-dot" style={{ background: "#8b5cf6" }} />Technical</span>
                <span className="legend-item"><span className="legend-dot" style={{ background: "#10b981" }} />Long Pit</span>
                <span className="legend-item"><span className="legend-dot" style={{ background: "#ef4444" }} />Extreme Deg</span>
              </div>
            </div>
            <TrackClusterChart tracks={tracks} selectedTrack={selectedTrack} />
          </div>
        </div>

        <div className="empty-state">
          <div className="empty-state-icon">🏎️</div>
          <h3>Ready to Compute Strategy</h3>
          <p>Select a Grand Prix, adjust parameters and chaos variables in the sidebar, then click <strong>Run Analysis</strong>.</p>
        </div>
      </div>
    );
  }

  // ── Results ───────────────────────────────────────────────────────────────
  const stratLabel    = buildStrategyLabel(result.optimal_strategy);
  const deltaSign     = result.time_delta_s >= 0 ? "+" : "";
  const deltaClass    = result.time_delta_s >= 0 ? "positive" : "negative";

  return (
    <div className="dashboard-grid">
      {/* KPI Row */}
      <div className="kpi-row">
        <KpiCard
          label="Optimal Strategy"
          value={stratLabel}
          sub={`${result.stop_count} pit stop${result.stop_count !== 1 ? "s" : ""} · ${result.cluster_label}`}
          accent="accent-red"
          large
          icon={<Flag size={18} />}
        />
        <KpiCard
          label="MDP Race Time"
          value={formatRaceTime(result.mdp_expected_time_s)}
          sub="Expected (mean of 1000 simulations)"
          accent="accent-blue"
          icon={<Timer size={18} />}
        />
        <KpiCard
          label="Time Delta vs Baseline"
          value={`${deltaSign}${result.time_delta_s.toFixed(1)}s`}
          sub="Negative = MDP is faster"
          accent="accent-green"
          valueClass={deltaClass}
          icon={<TrendingDown size={18} />}
        />
        <KpiCard
          label="MDP Risk of Ruin"
          value={`${result.mdp_risk_of_ruin_pct.toFixed(1)}%`}
          sub={`Baseline: ${result.baseline_risk_of_ruin_pct.toFixed(1)}%`}
          accent="accent-amber"
          valueClass={result.mdp_risk_of_ruin_pct > 10 ? "negative" : "positive"}
          icon={<AlertTriangle size={18} />}
        />
        <KpiCard
          label="Track Cluster"
          value={`C${result.cluster}`}
          sub={result.cluster_label}
          accent="accent-violet"
          icon={<Layers size={18} />}
        />
      </div>

      {/* Pit-stop timeline strip */}
      <div className="chart-card" style={{ padding: "16px 24px" }}>
        <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: 10, fontWeight: 700 }}>
          Pit Stop Schedules
        </div>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 11, color: "var(--accent-red)", marginBottom: 6, fontWeight: 600 }}>MDP Optimal</div>
            <div className="pit-timeline">
              {result.optimal_strategy.length === 0
                ? <span className="pit-chip mdp">Zero-Stop</span>
                : result.optimal_strategy.map(e => (
                  <span key={e.lap} className="pit-chip mdp">L{e.lap}</span>
                ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "var(--accent-blue)", marginBottom: 6, fontWeight: 600 }}>Baseline (Even Split)</div>
            <div className="pit-timeline">
              {result.baseline_strategy.map(e => (
                <span key={e.lap} className="pit-chip baseline">L{e.lap}</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Chart Row */}
      <div className="chart-grid">
        {/* Chart 1: Risk Distribution */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">Monte Carlo Risk Distribution</div>
              <div className="chart-subtitle">1,000 simulated race outcomes — MDP vs Baseline strategy</div>
            </div>
            <div className="chart-legend">
              <span className="legend-item"><span className="legend-dot" style={{ background: "#e8002d" }} />MDP Optimal</span>
              <span className="legend-item"><span className="legend-dot" style={{ background: "#00b4ff" }} />Baseline</span>
            </div>
          </div>
          <RiskDistributionChart
            mdpData={result.mdp_sim_distribution}
            baselineData={result.baseline_sim_distribution}
          />
        </div>

        {/* Chart 2: Track Cluster Scatter */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">Track Cluster Map</div>
              <div className="chart-subtitle">k-Means (k=4) — Tire Deg vs Pit-Lane Loss</div>
            </div>
          </div>
          <TrackClusterChart tracks={tracks} selectedTrack={selectedTrack} />
        </div>
      </div>
    </div>
  );
}
