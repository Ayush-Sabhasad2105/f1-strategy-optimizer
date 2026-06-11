// frontend/src/components/Dashboard.jsx
import React from "react";
import {
  Flag, Timer, AlertTriangle, TrendingDown, Layers,
  Cpu, ShieldCheck, ShieldAlert, Zap,
} from "lucide-react";
import KpiCard from "./KpiCard";
import RiskDistributionChart from "./RiskDistributionChart";
import TrackClusterChart from "./TrackClusterChart";

function formatRaceTime(seconds) {
  if (!seconds && seconds !== 0) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = (seconds % 60).toFixed(1);
  return `${h}h ${m}m ${s}s`;
}

// ── AI Advantage Hero Card ────────────────────────────────────────────────────
function AiAdvantageBanner({ winner, timeAdv, riskRed, aiRuin, staticRuin }) {
  const isAiWin     = winner === "AI";
  const isStaticWin = winner === "Static";
  const isTie       = winner === "Tie";

  const accentColor = isAiWin ? "#e8002d" : isStaticWin ? "#00b4ff" : "#f59e0b";
  const glowColor   = isAiWin
    ? "rgba(232,0,45,0.12)"
    : isStaticWin ? "rgba(0,180,255,0.10)" : "rgba(245,158,11,0.10)";

  const headlineIcon = isAiWin ? <Cpu size={22} /> : isStaticWin ? <Flag size={22} /> : <Timer size={22} />;
  const headline     = isAiWin
    ? "Reactive AI Wins"
    : isStaticWin ? "Static 2-Stop Wins"
    : "Statistical Tie";
  const sub = isTie
    ? "< 0.5 s separation across 10,000 simulations — strategies are equivalent at this SC rate"
    : isAiWin
      ? `AI is ${Math.abs(timeAdv).toFixed(2)} s faster on average`
      : `Static is ${Math.abs(timeAdv).toFixed(2)} s faster — low SC rate favours commitment`;

  return (
    <div style={{
      background: `linear-gradient(135deg, ${glowColor} 0%, transparent 70%)`,
      border: `1px solid ${accentColor}35`,
      borderLeft: `5px solid ${accentColor}`,
      borderRadius: "var(--radius-lg)",
      padding: "20px 28px",
      display: "grid",
      gridTemplateColumns: "auto 1fr auto auto",
      alignItems: "center",
      gap: 20,
    }}>

      {/* Icon circle */}
      <div style={{
        width: 52, height: 52, borderRadius: "50%",
        background: `${accentColor}14`,
        border: `2px solid ${accentColor}30`,
        display: "flex", alignItems: "center", justifyContent: "center",
        color: accentColor, flexShrink: 0,
      }}>
        {headlineIcon}
      </div>

      {/* Text */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <span style={{
            fontFamily: "'Orbitron', monospace", fontSize: 16,
            fontWeight: 900, color: accentColor, letterSpacing: 0.3,
          }}>
            {headline}
          </span>
          <span style={{
            fontSize: 9, fontWeight: 800, letterSpacing: 2,
            padding: "3px 8px", borderRadius: 4,
            background: `${accentColor}18`, color: accentColor,
            border: `1px solid ${accentColor}35`,
          }}>
            V3.0 REACTIVE AI
          </span>
        </div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>{sub}</div>
      </div>

      {/* Time advantage pill */}
      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        background: `${accentColor}10`,
        border: `1px solid ${accentColor}25`,
        borderRadius: "var(--radius-md)",
        padding: "10px 18px", gap: 2,
      }}>
        <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 600, letterSpacing: 1 }}>TIME ADV.</div>
        <div style={{
          fontFamily: "'Orbitron', monospace", fontSize: 22,
          fontWeight: 900, color: accentColor, lineHeight: 1,
        }}>
          {timeAdv >= 0 ? "+" : ""}{timeAdv.toFixed(2)}s
        </div>
        <div style={{ fontSize: 10, color: "var(--text-muted)" }}>Static − AI</div>
      </div>

      {/* Risk reduction pill */}
      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        background: riskRed >= 0 ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
        border: `1px solid ${riskRed >= 0 ? "rgba(34,197,94,0.25)" : "rgba(239,68,68,0.25)"}`,
        borderRadius: "var(--radius-md)",
        padding: "10px 18px", gap: 2,
      }}>
        <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 600, letterSpacing: 1 }}>RISK RED.</div>
        <div style={{
          fontFamily: "'Orbitron', monospace", fontSize: 22,
          fontWeight: 900,
          color: riskRed >= 0 ? "#22c55e" : "#ef4444",
          lineHeight: 1,
        }}>
          {riskRed >= 0 ? "+" : ""}{riskRed.toFixed(1)}%
        </div>
        <div style={{ fontSize: 10, color: "var(--text-muted)" }}>AI vs Static ruin</div>
      </div>
    </div>
  );
}

// ── Dual Risk-of-Ruin Panel ───────────────────────────────────────────────────
function DualRuinPanel({ aiRuin, staticRuin, riskReduction, baselineLaps }) {
  const aiSafe     = aiRuin <= 10;
  const staticSafe = staticRuin <= 10;
  const aiColor    = aiSafe     ? "#22c55e" : "#ef4444";
  const staticColor = staticSafe ? "#22c55e" : "#ef4444";
  const lapLabel   = baselineLaps && baselineLaps.length
    ? `[Lap ${baselineLaps.join(", Lap ")}]` : "[Lap 19, Lap 38]";

  return (
    <div className="chart-card" style={{ padding: "20px 24px" }}>
      <div style={{
        fontSize: 11, fontWeight: 700, color: "var(--text-muted)",
        textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: 16,
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <ShieldAlert size={13} /> Risk of Ruin — Reactive AI vs Static 2-Stop
        <span style={{ marginLeft: "auto", fontSize: 10, color: "var(--text-muted)", fontWeight: 400 }}>
          Ruin = exceeding 5% over the theoretical race minimum
        </span>
      </div>

      <div style={{ display: "flex", gap: 16, alignItems: "stretch" }}>

        {/* AI */}
        <div style={{
          flex: 1, padding: "16px 18px",
          background: `${aiColor}08`,
          border: `1px solid ${aiColor}28`,
          borderRadius: "var(--radius-md)",
          display: "flex", flexDirection: "column", gap: 6,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-muted)", fontWeight: 700 }}>
            <Cpu size={12} />  REACTIVE AI
          </div>
          <div style={{
            fontFamily: "'Orbitron', monospace",
            fontSize: 30, fontWeight: 900, color: aiColor, lineHeight: 1,
          }}>
            {aiRuin.toFixed(1)}%
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {aiSafe ? "✓ Within safe zone" : "⚠ Elevated risk"}
          </div>
          <div style={{ height: 4, background: "var(--bg-elevated)", borderRadius: 2, marginTop: 4 }}>
            <div style={{
              height: "100%", width: `${Math.min(aiRuin, 100)}%`,
              background: aiColor, borderRadius: 2, transition: "width 0.4s ease",
            }} />
          </div>
        </div>

        {/* Delta */}
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "center",
          justifyContent: "center", gap: 4, flexShrink: 0, minWidth: 60,
        }}>
          <div style={{ fontSize: 9, color: "var(--text-muted)", letterSpacing: 1 }}>ΔRUIN</div>
          <div style={{
            fontFamily: "'Orbitron', monospace", fontSize: 14, fontWeight: 900,
            color: riskReduction >= 0 ? "#22c55e" : "#ef4444",
          }}>
            {riskReduction >= 0 ? "+" : ""}{riskReduction.toFixed(1)}%
          </div>
          <div style={{ fontSize: 9, color: "var(--text-muted)", textAlign: "center", maxWidth: 52 }}>
            {riskReduction >= 0 ? "AI safer" : "Static safer"}
          </div>
        </div>

        {/* Static */}
        <div style={{
          flex: 1, padding: "16px 18px",
          background: `${staticColor}08`,
          border: `1px solid ${staticColor}28`,
          borderRadius: "var(--radius-md)",
          display: "flex", flexDirection: "column", gap: 6,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-muted)", fontWeight: 700 }}>
            <Flag size={12} /> STATIC 2-STOP {lapLabel}
          </div>
          <div style={{
            fontFamily: "'Orbitron', monospace",
            fontSize: 30, fontWeight: 900, color: staticColor, lineHeight: 1,
          }}>
            {staticRuin.toFixed(1)}%
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {staticSafe ? "✓ Within safe zone" : "⚠ Elevated risk"}
          </div>
          <div style={{ height: 4, background: "var(--bg-elevated)", borderRadius: 2, marginTop: 4 }}>
            <div style={{
              height: "100%", width: `${Math.min(staticRuin, 100)}%`,
              background: staticColor, borderRadius: 2, transition: "width 0.4s ease",
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
        <div className="skeleton" style={{ height: 100, borderRadius: "var(--radius-lg)" }} />
        <div className="kpi-row">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="kpi-card" style={{ minHeight: 110 }}>
              <div className="skeleton" style={{ height: 14, width: "50%", marginBottom: 12 }} />
              <div className="skeleton" style={{ height: 32, width: "80%", marginBottom: 8 }} />
              <div className="skeleton" style={{ height: 10, width: "60%" }} />
            </div>
          ))}
        </div>
        <div className="skeleton" style={{ height: 130, borderRadius: "var(--radius-lg)" }} />
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
          <div className="empty-state-icon">🤖</div>
          <h3>Reactive AI Ready</h3>
          <p>Select a Grand Prix, set race conditions, then click <strong>Run Analysis</strong>.</p>
          <p style={{ marginTop: 6, fontSize: 11, opacity: 0.6 }}>
            V3.0 · 3D MDP Policy Matrix · Live SC Reaction · 10,000 Monte Carlo Simulations
          </p>
        </div>
      </div>
    );
  }

  // ── Results ───────────────────────────────────────────────────────────────
  const aiDeltaSign  = result.time_advantage_s >= 0 ? "+" : "";
  const aiDeltaClass = result.time_advantage_s >= 0 ? "positive" : "negative";

  return (
    <div className="dashboard-grid">

      {/* ── AI Advantage Hero ─────────────────────────────────────────────── */}
      <AiAdvantageBanner
        winner={result.winner}
        timeAdv={result.time_advantage_s}
        riskRed={result.risk_reduction_pct}
        aiRuin={result.ai_risk_of_ruin_pct}
        staticRuin={result.static_risk_of_ruin_pct}
      />

      {/* ── KPI Row ───────────────────────────────────────────────────────── */}
      <div className="kpi-row">
        <KpiCard
          label="Reactive AI Race Time"
          value={formatRaceTime(result.ai_expected_time_s)}
          sub="Expected · mean of 10,000 simulations"
          accent="accent-red"
          icon={<Cpu size={18} />}
        />
        <KpiCard
          label="Static 2-Stop Race Time"
          value={formatRaceTime(result.static_expected_time_s)}
          sub={`Fixed: Lap ${result.baseline_laps ? result.baseline_laps.join(" & Lap ") : "19 & 38"} · no SC reaction`}
          accent="accent-blue"
          icon={<Flag size={18} />}
        />
        <KpiCard
          label="AI Time Advantage"
          value={`${aiDeltaSign}${result.time_advantage_s.toFixed(2)}s`}
          sub={result.time_advantage_s >= 0 ? "AI is faster" : "Static is faster at low SC rates"}
          accent="accent-green"
          valueClass={aiDeltaClass}
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

      {/* ── Dual Risk-of-Ruin Panel ───────────────────────────────────────── */}
      <DualRuinPanel
        aiRuin={result.ai_risk_of_ruin_pct}
        staticRuin={result.static_risk_of_ruin_pct}
        riskReduction={result.risk_reduction_pct}
        baselineLaps={result.baseline_laps}
      />

      {/* ── MDP Reference Strategy strip ─────────────────────────────────── */}
      {result.mdp_reference_strategy && result.mdp_reference_strategy.length > 0 && (
        <div className="chart-card" style={{ padding: "16px 24px" }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: 10, fontWeight: 700 }}>
            MDP Policy Reference Schedule <span style={{ color: "var(--text-muted)", fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(AI deviates from this in real-time)</span>
          </div>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--accent-red)", marginBottom: 6, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                <Cpu size={11} /> Reactive AI (deterministic trace)
              </div>
              <div className="pit-timeline">
                {result.mdp_reference_strategy.map(e => (
                  <span key={e.lap} className="pit-chip mdp">L{e.lap}</span>
                ))}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--accent-blue)", marginBottom: 6, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                <Flag size={11} /> Static Baseline {result.baseline_laps ? `[Lap ${result.baseline_laps.join(", Lap ")}]` : "[Lap 19, Lap 38]"}
              </div>
              <div className="pit-timeline">
                {(result.baseline_laps || [19, 38]).map(l => (
                  <span key={l} className="pit-chip baseline">L{l}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Chart Row ─────────────────────────────────────────────────────── */}
      <div className="chart-grid">
        {/* Chart 1: Risk Distribution */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">Monte Carlo Race Time Distribution</div>
              <div className="chart-subtitle">
                10,000 simulations · Reactive AI (red, leaning left) vs Static 2-Stop
                {result.baseline_laps ? ` [Lap ${result.baseline_laps.join(", Lap ")}]` : " [Lap 19, Lap 38]"}
                (blue, fatter SC tail)
              </div>
            </div>
            <div className="chart-legend">
              <span className="legend-item"><span className="legend-dot" style={{ background: "#e8002d" }} />Reactive AI</span>
              <span className="legend-item"><span className="legend-dot" style={{ background: "#00b4ff" }} />Static 2-Stop</span>
            </div>
          </div>
          <RiskDistributionChart
            mdpData={result.ai_sim_distribution}
            baselineData={result.static_sim_distribution}
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
