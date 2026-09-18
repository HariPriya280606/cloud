import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Check, AlertCircle, Code } from 'lucide-react';

export default function ServiceInput({
  servicesJson,
  setServicesJson,
  trafficJson,
  setTrafficJson,
  eventsJson,
  setEventsJson,
  constraintsJson,
  setConstraintsJson,
  servicesError,
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const formatJson = (setter, val) => {
    try {
      const parsed = JSON.parse(val);
      setter(JSON.stringify(parsed, null, 2));
    } catch (e) {
      // Keep as-is if invalid
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Monitored Services JSON */}
      <div className="form-group">
        <div className="form-label">
          <span>Monitored Services Metric Payload (JSON Array)</span>
          <button
            type="button"
            className="btn-secondary"
            style={{ fontSize: '0.72rem', padding: '2px 6px' }}
            onClick={() => formatJson(setServicesJson, servicesJson)}
          >
            <Code size={12} style={{ marginRight: '4px' }} /> Format JSON
          </button>
        </div>
        <textarea
          className="textarea-input textarea-code"
          value={servicesJson}
          onChange={(e) => setServicesJson(e.target.value)}
          rows={8}
          placeholder="Paste JSON array of ServiceMetric objects..."
        />
        {servicesError && (
          <div className="json-error">
            <AlertCircle size={14} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
            {servicesError}
          </div>
        )}
      </div>

      {/* Advanced Telemetry & Constraints Toggle */}
      <div>
        <div
          className="details-toggle"
          onClick={() => setShowAdvanced(!showAdvanced)}
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <span>Advanced Telemetry & Environment Constraints</span>
          {showAdvanced ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>

        {showAdvanced && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '12px' }}>
            {/* Latest Traffic */}
            <div className="form-group">
              <label className="form-label">Latest External Traffic Telemetry (JSON)</label>
              <textarea
                className="textarea-input textarea-code"
                value={trafficJson}
                onChange={(e) => setTrafficJson(e.target.value)}
                rows={3}
                placeholder="[ { 'service_id': 'checkout-api', 'requests_per_minute': 5200, ... } ]"
              />
            </div>

            {/* Recent Events */}
            <div className="form-group">
              <label className="form-label">Recent Infrastructure Events (JSON)</label>
              <textarea
                className="textarea-input textarea-code"
                value={eventsJson}
                onChange={(e) => setEventsJson(e.target.value)}
                rows={2}
                placeholder="[ { 'service_id': 'orders-api', 'event_type': 'scale_up', ... } ]"
              />
            </div>

            {/* Environment Constraints */}
            <div className="form-group">
              <label className="form-label">Deterministic Environment Constraints (JSON)</label>
              <textarea
                className="textarea-input textarea-code"
                value={constraintsJson}
                onChange={(e) => setConstraintsJson(e.target.value)}
                rows={4}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
