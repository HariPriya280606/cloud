import React from 'react';
import { Server, Activity, ShieldCheck, ShieldAlert, Clock, DollarSign } from 'lucide-react';

export default function ServiceTable({ services }) {
  if (!services || services.length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '0.88rem', padding: '16px', textAlign: 'center', background: 'rgba(255, 255, 255, 0.02)', border: '1px dashed var(--border-color)', borderRadius: 'var(--radius-md)' }}>
        No input data loaded. Upload or paste the required JSON file to begin.
      </div>
    );
  }

  const getCpuColor = (cpu) => {
    if (cpu >= 80) return '#f43f5e';
    if (cpu <= 20) return '#34d399';
    return '#38bdf8';
  };

  const getMemColor = (mem) => {
    if (mem >= 80) return '#f43f5e';
    if (mem <= 30) return '#34d399';
    return '#818cf8';
  };

  return (
    <div className="table-container">
      <table className="service-table">
        <thead>
          <tr>
            <th>Service ID</th>
            <th>CPU Utilization</th>
            <th>Memory</th>
            <th>Requests (RPM)</th>
            <th>Latency</th>
            <th>Instances</th>
            <th>Cost / Hr</th>
            <th>Health</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {services.map((srv, idx) => {
            const cpuColor = getCpuColor(srv.cpu_percent || 0);
            const memColor = getMemColor(srv.memory_percent || 0);
            const isHealthy = srv.healthy !== false;

            return (
              <tr key={srv.service_id || idx}>
                <td style={{ fontWeight: 600, color: '#f8fafc' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Server size={14} color="#38bdf8" />
                    {srv.service_id}
                  </div>
                </td>
                <td>
                  <div>
                    <span>{srv.cpu_percent}%</span>
                    <div className="progress-bar-container">
                      <div
                        className="progress-bar-fill"
                        style={{ width: `${Math.min(100, srv.cpu_percent || 0)}%`, backgroundColor: cpuColor }}
                      />
                    </div>
                  </div>
                </td>
                <td>
                  <div>
                    <span>{srv.memory_percent}%</span>
                    <div className="progress-bar-container">
                      <div
                        className="progress-bar-fill"
                        style={{ width: `${Math.min(100, srv.memory_percent || 0)}%`, backgroundColor: memColor }}
                      />
                    </div>
                  </div>
                </td>
                <td>{srv.requests_per_minute?.toLocaleString() || 0}</td>
                <td>
                  <span style={{ color: (srv.latency_ms > (srv.max_latency_ms || 300) * 0.8) ? '#fbbf24' : 'inherit' }}>
                    {srv.latency_ms} ms
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}> / {srv.max_latency_ms}ms</span>
                </td>
                <td>
                  <span style={{ fontWeight: 600 }}>{srv.instances}</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}> [{srv.min_instances}-{srv.max_instances}]</span>
                </td>
                <td>${Number(srv.cost_per_hour || 0).toFixed(2)}</td>
                <td>
                  <span className={`health-pill ${isHealthy ? 'healthy' : 'unhealthy'}`}>
                    {isHealthy ? <ShieldCheck size={12} /> : <ShieldAlert size={12} />}
                    {isHealthy ? 'Healthy' : 'Degraded'}
                  </span>
                </td>
                <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {srv.timestamp ? srv.timestamp.replace('T', ' ').replace('Z', '') : '-'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
