import React, { useState, useRef } from 'react';
import { ChevronDown, ChevronRight, Check, AlertCircle, Code, UploadCloud, FileJson } from 'lucide-react';

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
  const [fileName, setFileName] = useState(null);
  const fileInputRef = useRef(null);

  const formatJson = (setter, val) => {
    try {
      const parsed = JSON.parse(val);
      setter(JSON.stringify(parsed, null, 2));
    } catch (e) {
      // Keep as-is if invalid
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setFileName(file.name);
    
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target.result);
        // The uploaded file could be a full OptimizationRequest or just a list of services.
        if (parsed.services && Array.isArray(parsed.services)) {
          // Full request payload format
          setServicesJson(JSON.stringify(parsed.services, null, 2));
          if (parsed.latest_traffic) setTrafficJson(JSON.stringify(parsed.latest_traffic, null, 2));
          if (parsed.recent_events) setEventsJson(JSON.stringify(parsed.recent_events, null, 2));
          if (parsed.environment_constraints) setConstraintsJson(JSON.stringify(parsed.environment_constraints, null, 2));
        } else if (Array.isArray(parsed)) {
          // Just the services array
          setServicesJson(JSON.stringify(parsed, null, 2));
        } else {
          // Fallback, stringify whatever it is and let App.jsx throw validation error
          setServicesJson(JSON.stringify(parsed, null, 2));
        }
      } catch (err) {
        setServicesJson("Invalid JSON file uploaded.");
      }
    };
    reader.readAsText(file);
    // Reset input so the same file can be uploaded again if needed
    e.target.value = null;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* File Upload Control */}
      <div className="form-group" style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px dashed var(--border-color)', borderRadius: 'var(--radius-md)', padding: '16px', textAlign: 'center' }}>
        <input 
          type="file" 
          accept=".json" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          onChange={handleFileUpload} 
        />
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
          <UploadCloud size={28} color="#38bdf8" />
          <div style={{ fontSize: '0.92rem', fontWeight: 600 }}>
            Upload JSON Input File
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Upload a file containing service metrics or a full optimization request payload.
          </div>
          <button 
            type="button" 
            className="btn-secondary"
            onClick={() => fileInputRef.current?.click()}
            style={{ marginTop: '8px' }}
          >
            Select File
          </button>
          {fileName && (
            <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', color: '#34d399', background: 'rgba(52, 211, 153, 0.1)', padding: '4px 10px', borderRadius: '4px' }}>
              <FileJson size={14} />
              Loaded: {fileName}
            </div>
          )}
        </div>
      </div>

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
