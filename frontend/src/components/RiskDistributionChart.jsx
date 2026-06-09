// frontend/src/components/RiskDistributionChart.jsx
import React, { useMemo } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";

/**
 * Converts raw simulation arrays (race times in seconds) into histogram bins
 * for display as an overlapping area chart.
 */
function buildHistogram(mdpData, baselineData, bins = 60) {
  const all = [...mdpData, ...baselineData];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const binWidth = (max - min) / bins;

  const mdpBins   = new Array(bins).fill(0);
  const baseBins  = new Array(bins).fill(0);

  for (const v of mdpData) {
    const idx = Math.min(Math.floor((v - min) / binWidth), bins - 1);
    mdpBins[idx]++;
  }
  for (const v of baselineData) {
    const idx = Math.min(Math.floor((v - min) / binWidth), bins - 1);
    baseBins[idx]++;
  }

  return Array.from({ length: bins }, (_, i) => ({
    raceTime: parseFloat((min + i * binWidth + binWidth / 2).toFixed(1)),
    mdp: mdpBins[i],
    baseline: baseBins[i],
  }));
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--bg-card)",
      border: "1px solid var(--border-subtle)",
      borderRadius: "8px",
      padding: "10px 14px",
      fontSize: "12px",
    }}>
      <p style={{ color: "var(--text-muted)", marginBottom: 6 }}>~{label}s</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name === "mdp" ? "MDP Optimal" : "Baseline"}: <strong>{p.value}</strong> runs
        </p>
      ))}
    </div>
  );
};

export default function RiskDistributionChart({ mdpData, baselineData }) {
  const chartData = useMemo(() => buildHistogram(mdpData, baselineData), [mdpData, baselineData]);

  const mdpMean     = (mdpData.reduce((a, b) => a + b, 0) / mdpData.length).toFixed(1);
  const baseMean    = (baselineData.reduce((a, b) => a + b, 0) / baselineData.length).toFixed(1);

  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="mdpGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#e8002d" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#e8002d" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="baseGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#00b4ff" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#00b4ff" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />

          <XAxis
            dataKey="raceTime"
            tick={{ fill: "var(--text-muted)", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "var(--border-subtle)" }}
            tickFormatter={v => `${v}s`}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "var(--text-muted)", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={30}
          />

          <Tooltip content={<CustomTooltip />} />

          <ReferenceLine
            x={parseFloat(mdpMean)}
            stroke="#e8002d"
            strokeDasharray="4 2"
            label={{ value: `MDP μ`, fill: "#e8002d", fontSize: 10, position: "top" }}
          />
          <ReferenceLine
            x={parseFloat(baseMean)}
            stroke="#00b4ff"
            strokeDasharray="4 2"
            label={{ value: `Base μ`, fill: "#00b4ff", fontSize: 10, position: "top" }}
          />

          <Area
            type="monotone"
            dataKey="baseline"
            name="baseline"
            stroke="#00b4ff"
            strokeWidth={2}
            fill="url(#baseGrad)"
          />
          <Area
            type="monotone"
            dataKey="mdp"
            name="mdp"
            stroke="#e8002d"
            strokeWidth={2}
            fill="url(#mdpGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
