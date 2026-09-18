import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Server, Activity, ShieldCheck, ShieldAlert, RefreshCw, Radio } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const POLL_INTERVAL_MS = 6000;

/**
 * LiveSimulatorState — polls GET /api/services and shows the current
 * in-memory simulator state with delta indicators for changed values.
 * Refreshed automatically on mount, after every action (via refreshTrigger),
 * and on a 6-second background poll while the component is visible.
 */
export default function LiveSimulatorState({ refreshTrigger }) {
  const [services, setServices] = useState([]);
  const [prevServices, setPrevServices] = useState({});
  const [loading, setLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [error, setError] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const timerRef = useRef(null);

  const fetchServices = useCallback(async (isPolling = false) => {
    if (!isPolling) setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/services`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const incoming = data.services || [];

      setServices((prev) => {
        // Build delta map from previous state
        const prevMap = {};
        prev.forEach((s) => { prevMap[s.service_id] = s; });
        setPrevServices(prevMap);
        return incoming;
      });
      setLastRefresh(new Date());
      setError(null);
    } catch (err) {
      setError(`Failed to fetch live state: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch on mount and whenever refreshTrigger changes (after each agent run)
  useEffect(() => {
    fetchServices(false);
  }, [fetchServices, refreshTrigger]);

  // Background poll every 6 seconds
  useEffect(() => {
    timerRef.current = setInterval(() => fetchServices(true), POLL_INTERVAL_MS);
    return () => clearInterval(timerRef.current);
  }, [fetchServices]);

  const getCpuColor = (v) => {
    if (v >= 80) return '#f43f5e';
    if (v >= 60) return '#fbbf24';
    if (v <= 25) return '#34d399';
    return '#38bdf8';
  };

  const getMemColor = (v) => {
    if (v >= 80) return '#f43f5e';
    if (v >= 60) return '#fbbf24';
    if (v <= 30) return '#34d399';
    return '#818cf8';
  };

  // Returns delta indicator element: ↑ red for increase, ↓ green for decrease
  const DeltaBadge = ({ current, previous, unit = '', invert = false }) => {
    if (previous === undefined || previous === null) return null;
    const diff = current - previous;
    if (Math.abs(diff) < 0.01) return null;
    const isIncrease = diff > 0;
    // invert=true means increase is bad (cost, cpu, latency)
    const color = (isIncrease ? !invert : invert) ? '#34d399' : '#f43f5e';
    return (
      <span style={{
        fontSize: '0.7rem',
        fontWeight: 700,
        color,
        marginLeft: '4px',
        animation: 'deltaFade 1s ease-out',
      }}>
        {isIncrease ? '▲' : '▼'}{Math.abs(diff).toFixed(unit === '' ? 0 : 2)}{unit}
      </span>
    );
  };

  const totalCost = services.reduce((sum, s) => sum + (s.cost_per_hour || 0), 0);
  const healthyCount = services.filter((s) => s.healthy !== false).length;

  return (
    <div className="live-sim-panel">
      {/* Header */}
      <div className="live-sim-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <div className="live-sim-title">
          <Radio size={15} color="#34d399" style={{ flexShrink: 0 }} />
          <span>Live Simulator State</span>
          <span className="live-sim-pulse" />
          {services.length > 0 && (
            <span className="live-sim-summary-badge">
              {services.length} svc · ${totalCost.toFixed(2)}/hr · {healthyCount}/{services.length} healthy
            </span>
          )}
        </div>
        <div className="live-sim-header-right">
          {lastRefresh && (
            <span className="live-sim-ts">
              {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <button
            className="btn-icon"
            title="Refresh now"
            onClick={(e) => { e.stopPropagation(); fetchServices(false); }}
            disabled={loading}
          >
            <RefreshCw size={14} style={loading ? { animation: 'spin 1s linear infinite' } : {}} />
          </button>
          <span className="history-chevron">{isCollapsed ? '▶' : '▼'}</span>
        </div>
      </div>

      {!isCollapsed && (
        <div className="live-sim-body">
          {error && (
            <div className="history-error">{error}</div>
          )}

          {!loading && services.length === 0 && !error && (
            <div className="history-empty">
              No services loaded. Run a scenario to populate the simulator.
            </div>
          )}

          {services.length > 0 && (
            <div className="table-container" style={{ background: 'transparent', border: 'none' }}>
              <table className="service-table">
                <thead>
                  <tr>
                    <th>Service</th>
                    <th>CPU %</th>
                    <th>Memory %</th>
                    <th>Latency</th>
                    <th>Instances</th>
                    <th>Cost / hr</th>
                    <th>Health</th>
                  </tr>
                </thead>
                <tbody>
                  {services.map((srv) => {
                    const prev = prevServices[srv.service_id];
                    const cpu = srv.cpu_percent || 0;
                    const mem = srv.memory_percent || 0;
                    const isHealthy = srv.healthy !== false;

                    return (
                      <tr key={srv.service_id} className="live-sim-row">
                        {/* Service ID */}
                        <td style={{ fontWeight: 600, color: '#f8fafc' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Server size={13} color="#38bdf8" />
                            {srv.service_id}
                          </div>
                        </td>

                        {/* CPU */}
                        <td>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                              <span style={{ color: getCpuColor(cpu) }}>{cpu}%</span>
                              <DeltaBadge current={cpu} previous={prev?.cpu_percent} unit="%" invert={true} />
                            </div>
                            <div className="progress-bar-container">
                              <div
                                className="progress-bar-fill"
                                style={{ width: `${Math.min(100, cpu)}%`, backgroundColor: getCpuColor(cpu), transition: 'width 0.6s ease' }}
                              />
                            </div>
                          </div>
                        </td>

                        {/* Memory */}
                        <td>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                              <span style={{ color: getMemColor(mem) }}>{mem}%</span>
                              <DeltaBadge current={mem} previous={prev?.memory_percent} unit="%" invert={true} />
                            </div>
                            <div className="progress-bar-container">
                              <div
                                className="progress-bar-fill"
                                style={{ width: `${Math.min(100, mem)}%`, backgroundColor: getMemColor(mem), transition: 'width 0.6s ease' }}
                              />
                            </div>
                          </div>
                        </td>

                        {/* Latency */}
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center' }}>
                            <span style={{
                              color: srv.latency_ms > (srv.max_latency_ms || 300) * 0.8 ? '#fbbf24' : 'inherit'
                            }}>
                              {srv.latency_ms ?? 0} ms
                            </span>
                            <DeltaBadge current={srv.latency_ms || 0} previous={prev?.latency_ms} unit="ms" invert={true} />
                          </div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            max {srv.max_latency_ms}ms
                          </div>
                        </td>

                        {/* Instances */}
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center' }}>
                            <span style={{ fontWeight: 700, fontSize: '1.05rem' }}>{srv.instances}</span>
                            <DeltaBadge current={srv.instances || 0} previous={prev?.instances} invert={false} />
                          </div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            [{srv.min_instances}–{srv.max_instances}]
                          </div>
                        </td>

                        {/* Cost */}
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center' }}>
                            <span style={{ fontWeight: 600, color: '#34d399' }}>
                              ${(srv.cost_per_hour || 0).toFixed(2)}
                            </span>
                            <DeltaBadge
                              current={srv.cost_per_hour || 0}
                              previous={prev?.cost_per_hour}
                              unit=""
                              invert={true}
                            />
                          </div>
                        </td>

                        {/* Health */}
                        <td>
                          <span className={`health-pill ${isHealthy ? 'healthy' : 'unhealthy'}`}>
                            {isHealthy ? <ShieldCheck size={12} /> : <ShieldAlert size={12} />}
                            {isHealthy ? 'Healthy' : 'Degraded'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes deltaFade {
          from { opacity: 1; transform: translateY(-3px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        .live-sim-row { transition: background 0.3s ease; }
        .live-sim-row:hover { background: rgba(56, 189, 248, 0.04); }
      `}</style>
    </div>
  );
}
