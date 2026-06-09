// frontend/src/components/KpiCard.jsx
import React from "react";

/**
 * A single KPI metric card.
 * @param {string}  label     - Small label above the value
 * @param {string}  value     - Large primary value
 * @param {string}  sub       - Small sub-text below value
 * @param {string}  accent    - CSS class: accent-red | accent-blue | accent-green | accent-amber | accent-violet
 * @param {React.ReactNode} icon  - SVG icon node (lucide-react)
 * @param {string}  valueClass - Additional class on kpi-value (positive / negative / neutral)
 * @param {boolean} large     - If true, uses smaller font for long values
 */
export default function KpiCard({ label, value, sub, accent = "accent-red", icon, valueClass = "", large = false }) {
  return (
    <div className={`kpi-card ${accent}`}>
      {icon && <div className="kpi-icon">{icon}</div>}
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value ${large ? "lg" : ""} ${valueClass}`}>{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}
