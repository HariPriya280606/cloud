import React from 'react';
import { Sparkles, Download, ArrowRight } from 'lucide-react';

export default function RequestForm({ 
  userRequest, 
  setUserRequest, 
  onAnalyze, 
  onDirectDownload,
  loading 
}) {
  const suggestions = [
    "Review the current services and reduce unnecessary cost without breaking the latency or availability requirements.",
    "Orders traffic is increasing. Keep the service within its latency target.",
    "Scale the payment service only if the current state requires it.",
    "Reduce cost if it is safe."
  ];

  return (
    <div className="form-group">
      <label className="form-label">
        <span>Natural-Language Operations Request</span>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Intent Parser & Reasoning Layer</span>
      </label>
      <textarea
        className="textarea-input"
        value={userRequest}
        onChange={(e) => setUserRequest(e.target.value)}
        rows={3}
        placeholder="Enter natural-language cloud optimization or scaling request..."
      />
      
      {/* Quick Prompts */}
      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
        {suggestions.map((s, idx) => (
          <button
            key={idx}
            type="button"
            className="btn-secondary"
            style={{ fontSize: '0.72rem', padding: '3px 8px', borderRadius: '4px' }}
            onClick={() => setUserRequest(s)}
          >
            {s.substring(0, 42)}...
          </button>
        ))}
      </div>

      <div className="action-buttons" style={{ marginTop: '12px' }}>
        <button
          className="btn-primary"
          onClick={onAnalyze}
          disabled={loading || !userRequest.trim()}
        >
          <Sparkles size={18} />
          {loading ? 'Investigating & Verifying...' : 'Analyze and Optimize'}
        </button>
        <button
          className="btn-download"
          onClick={onDirectDownload}
          disabled={loading || !userRequest.trim()}
          title="Run optimization workflow and download raw JSON report directly"
        >
          <Download size={16} />
          Direct Download
        </button>
      </div>
    </div>
  );
}
