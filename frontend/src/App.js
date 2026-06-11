// frontend/src/App.js
import React, { useState, useEffect, useCallback } from "react";
import "./index.css";
import { fetchTracks, computeStrategy } from "./api";
import Dashboard from "./components/Dashboard";
import { Sun, Moon } from "lucide-react";

// Default param values — mirrors StrategyRequest V3.0
const DEFAULTS = {
  total_laps:      57,
  base_lap_time:   95000,
  pit_loss:        24000,
  deg_penalty:     200,
  // V3.0 race-condition variables
  sc_probability:  0.02,
  traffic_penalty: 1500,
};

export default function App() {
  // ── Theme ──────────────────────────────────────────────────────────────────
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("f1-theme") || "dark";
  });

  // Stamp data-theme on <html> so :root vars (body bg, etc.) are all affected
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => {
      const next = prev === "dark" ? "light" : "dark";
      localStorage.setItem("f1-theme", next);
      return next;
    });
  };

  const [tracks, setTracks]         = useState([]);
  const [selectedTrack, setSelectedTrack] = useState("");

  // Sliders
  const [params, setParams]         = useState(DEFAULTS);

  // API state
  const [result, setResult]         = useState(null);
  const [isLoading, setIsLoading]   = useState(false);
  const [error, setError]           = useState(null);

  // Load track list on mount
  useEffect(() => {
    fetchTracks()
      .then(data => {
        setTracks(data);
        if (data.length > 0) {
          const first = data[0];
          setSelectedTrack(first.circuit_name);
          // Pre-fill params from the selected track
          setParams(p => ({
            ...p,
            base_lap_time: first.base_lap_time_ms,
            pit_loss: first.pit_loss_ms,
            deg_penalty: first.tire_deg_ms_per_lap,
          }));
        }
      })
      .catch(err => setError("Could not load track list. Is the API running?"));
  }, []);

  // When track changes, update the numeric defaults from track data
  const handleTrackChange = useCallback((name) => {
    setSelectedTrack(name);
    const track = tracks.find(t => t.circuit_name === name);
    if (track) {
      setParams(p => ({
        ...p,
        base_lap_time: track.base_lap_time_ms,
        pit_loss: track.pit_loss_ms,
        deg_penalty: track.tire_deg_ms_per_lap,
      }));
    }
    setResult(null);
  }, [tracks]);

  const handleParamChange = (key, value) => {
    setParams(p => ({ ...p, [key]: parseFloat(value) }));
  };

  const handleAnalyze = async () => {
    if (!selectedTrack) return;
    setIsLoading(true);
    setError(null);
    try {
      // Send only the 7 fields V3.0 StrategyRequest accepts
      const payload = {
        track_name:      selectedTrack,
        total_laps:      params.total_laps,
        base_lap_time:   params.base_lap_time,
        pit_loss:        params.pit_loss,
        deg_penalty:     params.deg_penalty,
        sc_probability:  params.sc_probability,
        traffic_penalty: params.traffic_penalty,
      };
      const res = await computeStrategy(payload);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-shell">
      {/* ── Sidebar ────────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        {/* Logo */}
        <div className="sidebar-logo">
          <div className="logo-f1">
            <span>F1</span>
            <span className="logo-badge">STRAT</span>
          </div>
          <div className="logo-subtitle">Race Strategy Optimizer</div>
        </div>

        {/* Grand Prix Selector */}
        <div className="sidebar-section">
          <div className="sidebar-section-title">Grand Prix</div>
          <div className="form-group">
            <label className="form-label">Circuit</label>
            <select
              id="track-select"
              className="form-select"
              value={selectedTrack}
              onChange={e => handleTrackChange(e.target.value)}
            >
              {tracks.map(t => (
                <option key={t.circuit_name} value={t.circuit_name}>{t.circuit_name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Race Parameters */}
        <div className="sidebar-section">
          <div className="sidebar-section-title">Race Parameters</div>

          <div className="form-group">
            <label className="form-label">
              Total Laps <span className="form-value">{params.total_laps}</span>
            </label>
            <input
              id="slider-total-laps"
              type="range" min="20" max="80" step="1"
              className="form-slider"
              value={params.total_laps}
              onChange={e => handleParamChange("total_laps", e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              Base Lap Time <span className="form-value">{(params.base_lap_time / 1000).toFixed(1)}s</span>
            </label>
            <input
              id="slider-base-lap"
              type="range" min="60000" max="130000" step="500"
              className="form-slider"
              value={params.base_lap_time}
              onChange={e => handleParamChange("base_lap_time", e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              Pit Lane Loss <span className="form-value">{(params.pit_loss / 1000).toFixed(1)}s</span>
            </label>
            <input
              id="slider-pit-loss"
              type="range" min="15000" max="45000" step="500"
              className="form-slider"
              value={params.pit_loss}
              onChange={e => handleParamChange("pit_loss", e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              Tire Degradation <span className="form-value">{params.deg_penalty} ms/lap</span>
            </label>
            <input
              id="slider-deg-penalty"
              type="range" min="50" max="600" step="10"
              className="form-slider"
              value={params.deg_penalty}
              onChange={e => handleParamChange("deg_penalty", e.target.value)}
            />
          </div>
        </div>

        {/* V3.0 Race Conditions */}
        <div className="sidebar-section">
          <div className="sidebar-section-title">⚡ Race Conditions <span style={{ color: "#f59e0b", fontSize: 9, letterSpacing: 1 }}>V3.0</span></div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 14, lineHeight: 1.5 }}>
            Control stochastic race events. The Reactive AI automatically adapts; the Static 2-Stop cannot.
          </div>

          <div className="form-group">
            <label className="form-label">
              Safety Car Prob. <span className="form-value sc">{(params.sc_probability * 100).toFixed(1)}%</span>
            </label>
            <input
              id="slider-sc-probability"
              type="range" min="0" max="0.10" step="0.005"
              className="form-slider sc"
              value={params.sc_probability}
              onChange={e => handleParamChange("sc_probability", e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              Dirty Air Penalty <span className="form-value sc">{params.traffic_penalty} ms</span>
            </label>
            <input
              id="slider-traffic-penalty"
              type="range" min="0" max="3000" step="100"
              className="form-slider sc"
              value={params.traffic_penalty}
              onChange={e => handleParamChange("traffic_penalty", e.target.value)}
            />
          </div>
        </div>

        {/* CTA */}
        <div className="sidebar-section" style={{ borderBottom: "none" }}>
          <button
            id="btn-run-analysis"
            className="btn-analyze"
            onClick={handleAnalyze}
            disabled={isLoading || !selectedTrack}
          >
            {isLoading
              ? <><span className="loading-spinner" style={{ marginRight: 8 }} />Solving 10k Sims…</>
              : "▶ Run Analysis"
            }
          </button>
        </div>
      </aside>

      {/* ── Main Content ───────────────────────────────────────────────────── */}
      <div className="main-content">
        {/* Top bar */}
        <div className="top-bar">
          <span className="top-bar-title">
            {selectedTrack ? `${selectedTrack} Grand Prix` : "F1 Strategy Command Center"}
          </span>
          <div className="top-bar-right">
            <button
              id="btn-theme-toggle"
              className="btn-theme-toggle"
              onClick={toggleTheme}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark"
                ? <><Sun size={14} />Light Mode</>
                : <><Moon size={14} />Dark Mode</>
              }
            </button>
            <div className="status-badge">
              <span className="status-dot" />
              MDP + Monte Carlo Engine Active
            </div>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div style={{ padding: "16px 32px 0" }}>
            <div className="error-banner">
              ⚠ {error}
            </div>
          </div>
        )}

        {/* Dashboard */}
        <Dashboard
          result={result}
          tracks={tracks}
          selectedTrack={selectedTrack}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
