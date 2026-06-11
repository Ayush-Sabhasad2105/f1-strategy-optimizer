// frontend/src/components/Dashboard.jsx
import React from "react";
import {
  Flag, Timer, AlertTriangle, TrendingDown, Layers,
  Trophy, ShieldAlert, ShieldCheck,
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

// ── Winner Banner ─────────────────────────────────────────────────────────────
function WinnerBanner({ winner, timeDelta, mdpRuin, baselineRuin }) {
  const config = {
    MDP: {
      label: "MDP Strategy Wins",
      sub: `${Math.abs(timeDelta).toFixed(1)}s faster than baseline`,
      color: "#e8002d",
      glow: "rgba(232,0,45,0.18)",
      icon: <Trophy size={20} />,
      badge: "OPTIMAL",
    },
    Baseline: {
      label: "Baseline Strategy Wins",
      sub: `${Math.abs(timeDelta).toFixed(1)}s faster — consider fewer stops`,
      color: "#00b4ff",
      glow: "rgba(0,180,255,0.15)",
      icon: <Trophy size={20} />,
      badge: "BASELINE",
    },
    Tie: {
      label: "Statistical Tie",
      sub: `< 0.5s difference across 10,000 simulations`,
      color: "#f59e0b",
      glow: "rgba(245,158,11,0.15)",
      icon: <Timer size={20} />,
      badge: "TIE",
    },
  };

  const c = config[winner] || config["Tie"];

  return (
    <div style={{
      background: `linear-gradient(135deg, ${c.glow}, transparent)`,
      border: `1px solid ${c.color}40`,
      borderLeft: `4px solid ${c.color}`,
      borderRadius: "var(--radius-lg)",
      padding: "18px 24px",
      display: "flex",
      alignItems: "center",
      gap: 16,
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: "50%",
        background: `${c.color}18`,
        border: `2px solid ${c.color}40`,
        display: "flex", alignItems: "center", justifyContent: "center",
        color: c.color, flexShrink: 0,
      }}>
        {c.icon}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
          <span style={{
            fontFamily: "'Orbitron', monospace",
            fontSize: 15,
            fontWeight: 900,
            color: c.color,
            letterSpacing: 0.5,
          }}>
            {c.label}
          </span>
          <span style={{
            fontSize: 10, fontWeight: 700, letterSpacing: 1.5,
            padding: "2px 8px", borderRadius: 4,
            background: `${c.color}20`, color: c.color,
            border: `1px solid ${c.color}40`,
          }}>
            {c.badge}
          </span>
        </div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{c.sub}</div>
      </div>
      {/* Risk comparison pill */}
      <div style={{
        display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4,
        fontSize: 11, color: "var(--text-muted)", flexShrink: 0,
      }}>
        <span>MDP ruin: <strong style={{ color: mdpRuin > 10 ? "#ef4444" : "#22c55e" }}>{mdpRuin.toFixed(1)}%</strong></span>
        <span>Base ruin: <strong style={{ color: baselineRuin > 10 ? "#ef4444" : "#22c55e" }}>{baselineRuin.toFixed(1)}%</strong></span>
      </div>
    </div>
  );
}

// ── Dual Risk-of-Ruin Panel ───────────────────────────────────────────────────
function DualRuinPanel({ mdpRuin, baselineRuin, ruinDelta }) {
  const mdpSafe    = mdpRuin <= 10;
  const baseSafe   = baselineRuin <= 10;
  const mdpColor   = mdpSafe   ? "#22c55e" : "#ef4444";
  const baseColor  = baseSafe  ? "#22c55e" : "#ef4444";
  const deltaColor = ruinDelta >= 0 ? "#22c55e" : "#ef4444";  // positive = MDP safer

  return (
    <div className="chart-card" style={{ padding: "20px 24px" }}>
      <div style={{
        fontSize: 11, fontWeight: 700,
        color: "var(--text-muted)", textTransform: "uppercase",
        letterSpacing: "1.5px", marginBottom: 16,
      }}>
        ⚠ Risk of Ruin — Both Strategies
      </div>

      <div style={{ display: "flex", gap: 16, alignItems: "stretch" }}>
        {/* MDP */}
        <div style={{
          flex: 1, padding: "16px 18px",
          background: `${mdpColor}10`,
          border: `1px solid ${mdpColor}30`,
          borderRadius: "var(--radius-md)",
          display: "flex", flexDirection: "column", gap: 6,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-muted)", fontWeight: 600 }}>
            {mdpSafe ? <ShieldCheck size={13} /> : <ShieldAlert size={13} />}
            MDP OPTIMAL
          </div>
          <div style={{
            fontFamily: "'Orbitron', monospace",
            fontSize: 28, fontWeight: 900, color: mdpColor, lineHeight: 1,
          }}>
            {mdpRuin.toFixed(1)}%
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {mdpSafe ? "Within acceptable risk" : "High ruin probability"}
          </div>
          {/* Mini bar */}
          <div style={{ height: 4, background: "var(--bg-elevated)", borderRadius: 2, marginTop: 4 }}>
            <div style={{
              height: "100%", width: `${Math.min(mdpRuin, 100)}%`,
              background: mdpColor, borderRadius: 2,
              transition: "width 0.4s ease",
            }} />
          </div>
        </div>

        {/* Divider with delta */}
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "center",
          justifyContent: "center", gap: 4, flexShrink: 0,
        }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)" }}>DELTA</div>
          <div style={{
            fontFamily: "'Orbitron', monospace",
            fontSize: 15, fontWeight: 900,
            color: deltaColor,
          }}>
            {ruinDelta >= 0 ? "+" : ""}{ruinDelta.toFixed(1)}%
          </div>
          <div style={{ fontSize: 9, color: "var(--text-muted)", textAlign: "center", maxWidth: 48 }}>
            {ruinDelta >= 0 ? "MDP safer" : "Base safer"}
          </div>
        </div>

        {/* Baseline */}
        <div style={{
          flex: 1, padding: "16px 18px",
          background: `${baseColor}10`,
          border: `1px solid ${baseColor}30`,
          borderRadius: "var(--radius-md)",
          display: "flex", flexDirection: "column", gap: 6,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-muted)", fontWeight: 600 }}>
            {baseSafe ? <ShieldCheck size={13} /> : <ShieldAlert size={13} />}
            BASELINE
          </div>
          <div style={{
            fontFamily: "'Orbitron', monospace",
            fontSize: 28, fontWeight: 900, color: baseColor, lineHeight: 1,
          }}>
            {baselineRuin.toFixed(1)}%
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {baseSafe ? "Within acceptable risk" : "High ruin probability"}
          </div>
          {/* Mini bar */}
          <div style={{ height: 4, background: "var(--bg-elevated)", borderRadius: 2, marginTop: 4 }}>
            <div style={{
              height: "100%", width: `${Math.min(baselineRuin, 100)}%`,
              background: baseColor, borderRadius: 2,
              transition: "width 0.4s ease",
            }} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard({ result, tracks, selectedTrack, isLoading }) {

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="dashboard-grid">
        <div className="skeleton" style={{ height: 88, borderRadius: "var(--radius-lg)" }} />
        <div className="kpi-row">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="kpi-card" style={{ minHeight: 110 }}>
              <div className="skeleton" style={{ height: 14, width: "50%", marginBottom: 12 }} />
              <div className="skeleton" style={{ height: 32, width: "80%", marginBottom: 8 }} />
              <div className="skeleton" style={{ height: 10, width: "60%" }} />
            </div>
          ))}
        </div>
        <div className="skeleton" style={{ height: 120, borderRadius: "var(--radius-lg)" }} />
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
          <p style={{ marginTop: 4, fontSize: 11, opacity: 0.6 }}>V2.0 — 3D MDP · Safety Car · Dirty Air · 10,000 Monte Carlo Simulations</p>
        </div>
      </div>
    );
  }

  // ── Results ───────────────────────────────────────────────────────────────
  const stratLabel = buildStrategyLabel(result.optimal_strategy);
  const deltaSign  = result.time_delta_s >= 0 ? "+" : "";
  const deltaClass = result.time_delta_s >= 0 ? "positive" : "negative";

  return (
    <div className="dashboard-grid">

      {/* ── Winner Banner ──────────────────────────────────────────────────── */}
      <WinnerBanner
        winner={result.winner}
        timeDelta={result.time_delta_s}
        mdpRuin={result.mdp_risk_of_ruin_pct}
        baselineRuin={result.baseline_risk_of_ruin_pct}
      />

      {/* ── KPI Row ────────────────────────────────────────────────────────── */}
      <div className="kpi-row">
        <KpiCard
          label="MDP Optimal Strategy"
          value={stratLabel}
          sub={`${result.stop_count} stop${result.stop_count !== 1 ? "s" : ""} · ${result.cluster_label}`}
          accent="accent-red"
          large
          icon={<Flag size={18} />}
        />
        <KpiCard
          label="MDP Race Time"
          value={formatRaceTime(result.mdp_expected_time_s)}
          sub="Expected · mean of 10,000 simulations"
          accent="accent-blue"
          icon={<Timer size={18} />}
        />
        <KpiCard
          label="Time Delta vs Baseline"
          value={`${deltaSign}${result.time_delta_s.toFixed(1)}s`}
          sub={result.time_delta_s >= 0 ? "MDP is faster" : "Baseline is faster"}
          accent="accent-green"
          valueClass={deltaClass}
          icon={<TrendingDown size={18} />}
        />
        <KpiCard
          label="Track Cluster"
          value={`C${result.cluster}`}
          sub={result.cluster_label}
          accent="accent-violet"
          icon={<Layers size={18} />}
        />
      </div>

      {/* ── Dual Risk-of-Ruin Panel ────────────────────────────────────────── */}
      <DualRuinPanel
        mdpRuin={result.mdp_risk_of_ruin_pct}
        baselineRuin={result.baseline_risk_of_ruin_pct}
        ruinDelta={result.ruin_delta_pct}
      />

      {/* ── Pit-stop timeline strip ────────────────────────────────────────── */}
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

      {/* ── Chart Row ─────────────────────────────────────────────────────── */}
      <div className="chart-grid">
        {/* Chart 1: Risk Distribution */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">Monte Carlo Risk Distribution</div>
              <div className="chart-subtitle">10,000 simulated race outcomes — MDP vs Baseline · SC + Dirty Air included</div>
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
