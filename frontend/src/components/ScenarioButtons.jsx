import React from 'react';
import { Play, TrendingDown, TrendingUp, AlertTriangle, XCircle } from 'lucide-react';

const SCENARIOS = [
  {
    id: 'scenario_a',
    name: 'Demo: Scenario A (Idle Cost Waste)',
    badge: 'Cost Waste',
    badgeClass: 'badge-cost',
    icon: TrendingDown,
    desc: 'reports-worker has 0 traffic and low CPU. Safe scale-down with verified savings.',
  },
  {
    id: 'scenario_b',
    name: 'Demo: Scenario B (Traffic Growth Surge)',
    badge: 'Traffic Surge',
    badgeClass: 'badge-traffic',
    icon: TrendingUp,
    desc: 'orders-api traffic doubled (+100%). Preventative scale-up to protect latency target.',
  },
  {
    id: 'scenario_c',
    name: 'Demo: Scenario C (Stale Metrics Telemetry)',
    badge: 'Stale Refusal',
    badgeClass: 'badge-stale',
    icon: AlertTriangle,
    desc: 'checkout-api old 900 rpm metric vs fresh 5,200 rpm traffic. Scaling safely blocked.',
  },
  {
    id: 'scenario_d',
    name: 'Demo: Scenario D (Capacity Failure Mode)',
    badge: 'Escalation',
    badgeClass: 'badge-failure',
    icon: XCircle,
    desc: 'payment-api hits 91% CPU. Scale-up fails with capacity_unavailable -> escalates.',
  },
];

export default function ScenarioButtons({ currentScenario, onSelectScenario, onRunScenario, loading }) {
  return (
    <div className="scenario-selector">
      <div className="section-label">Optional: Load Demo Data</div>
      <div className="scenario-grid">
        {SCENARIOS.map((sc) => {
          const Icon = sc.icon;
          const isActive = currentScenario === sc.id;
          return (
            <div
              key={sc.id}
              className={`scenario-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelectScenario(sc.id)}
            >
              <div className="scenario-btn-header">
                <span className="scenario-name">{sc.name}</span>
                <span className={`scenario-badge ${sc.badgeClass}`}>{sc.badge}</span>
              </div>
              <p className="scenario-desc">{sc.desc}</p>
              <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  className="btn-secondary"
                  style={{ padding: '4px 10px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRunScenario(sc.id);
                  }}
                  disabled={loading}
                >
                  <Play size={12} />
                  Run Directly
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
