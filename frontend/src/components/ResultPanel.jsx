import React from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  ShieldAlert, 
  ShieldCheck, 
  Download, 
  ArrowRight, 
  Cpu, 
  Clock, 
  DollarSign, 
  Layers, 
  Activity,
  FileJson
} from 'lucide-react';

export default function ResultPanel({ report, loading, onDownloadReport }) {
  if (loading) {
    return (
      <div className="panel" style={{ justifyContent: 'center', alignItems: 'center', minHeight: '380px' }}>
        <div style={{ textAlign: 'center' }}>
          <Activity size={38} className="animate-spin" color="#38bdf8" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Executing Autonomous Optimization Agent</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '6px' }}>
            Observing telemetry → Checking freshness → Validating safety policies → Verifying post-action state...
          </p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="panel" style={{ justifyContent: 'center', alignItems: 'center', minHeight: '380px', color: 'var(--text-muted)' }}>
        <div style={{ textAlign: 'center' }}>
          <Layers size={36} color="var(--border-color)" style={{ margin: '0 auto 12px' }} />
          <p style={{ fontSize: '0.95rem' }}>Select a scenario or click "Analyze and Optimize" to generate report.</p>
        </div>
      </div>
    );
  }

  const getStatusClass = (status) => {
    switch (status) {
      case 'completed': return 'status-completed';
      case 'blocked':
      case 'no_action': return 'status-blocked';
      case 'failed':
      case 'requires_attention': return 'status-failed';
      default: return 'status-investigating';
    }
  };

  const getStatusBadgeColor = (decision) => {
    switch (decision) {
      case 'action_taken': return { bg: 'rgba(16, 185, 129, 0.2)', color: '#34d399' };
      case 'stale_data':
      case 'no_safe_action': return { bg: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24' };
      case 'action_failed':
      case 'escalated': return { bg: 'rgba(244, 63, 94, 0.2)', color: '#fb7185' };
      default: return { bg: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8' };
    }
  };

  const decisionBadge = getStatusBadgeColor(report.final_decision);

  return (
    <div className="panel">
      {/* Top Header Card */}
      <div className={`result-header-card ${getStatusClass(report.status)}`}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span 
              className="pill-badge" 
              style={{ backgroundColor: decisionBadge.bg, color: decisionBadge.color }}
            >
              {report.final_decision?.replace('_', ' ')}
            </span>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Report ID: {report.report_id}
            </span>
          </div>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, marginTop: '6px' }}>
            Intent: {report.intent?.replace('_', ' ').toUpperCase()}
          </h2>
        </div>
        <button 
          className="btn-download" 
          onClick={() => onDownloadReport(report.report_id)}
          title="Download the full verified JSON report"
        >
          <Download size={16} />
          Download JSON Report
        </button>
      </div>

      {/* Summary */}
      <div className="result-section-card">
        <div className="card-title">
          <Activity size={16} color="#38bdf8" /> Executive Summary
        </div>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>
          {report.summary}
        </p>
      </div>

      {/* Observed Problem */}
      {report.observed_problem && (
        <div className="result-section-card">
          <div className="card-title">
            <AlertTriangle size={16} color="#f59e0b" /> Observed Problem Investigation
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
            <strong>Type:</strong> <span style={{ textTransform: 'capitalize', color: 'var(--text-primary)' }}>{report.observed_problem.type?.replace('_', ' ')}</span>
          </p>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {report.observed_problem.description}
          </p>
          {report.observed_problem.affected_services?.length > 0 && (
            <div style={{ marginTop: '6px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Affected Services: {report.observed_problem.affected_services.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* Selected Action & Financials */}
      {report.selected_action ? (
        <div className="result-section-card" style={{ borderLeft: '4px solid #38bdf8' }}>
          <div className="card-title">
            <Cpu size={16} color="#38bdf8" /> Selected Safe Action
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {report.selected_action.action?.replace('_', ' ').toUpperCase()} on {report.selected_action.service_id}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Instances: <span style={{ fontWeight: 600 }}>{report.selected_action.previous_instances}</span> → <span style={{ fontWeight: 700, color: '#38bdf8' }}>{report.selected_action.requested_instances}</span>
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Reason: {report.selected_action.reason}
              </div>
            </div>

            {report.verification && (
              <div style={{ textAlign: 'right' }}>
                <div className="savings-highlight">
                  ${report.verification.estimated_hourly_savings > 0 ? report.verification.estimated_hourly_savings.toFixed(2) : '0.00'}
                  <span className="savings-sub">/ hr savings</span>
                </div>
                <div style={{ fontSize: '0.78rem', color: '#34d399' }}>
                  Est. ${(report.verification.estimated_hourly_savings * 730).toFixed(2)} / month
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}

      {/* Deterministic Policy Checks */}
      <div className="result-section-card">
        <div className="card-title">
          <ShieldCheck size={16} color="#10b981" /> Deterministic Safety Policy Gates
        </div>
        <div className="policy-list">
          {report.policy_checks?.map((chk, idx) => (
            <div key={idx} className={`policy-item ${chk.passed ? 'passed' : 'failed'}`}>
              {chk.passed ? (
                <CheckCircle2 size={16} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />
              ) : (
                <XCircle size={16} color="#f43f5e" style={{ flexShrink: 0, marginTop: '2px' }} />
              )}
              <div>
                <strong style={{ textTransform: 'capitalize' }}>{chk.check.replace(/_/g, ' ')}: </strong>
                <span>{chk.message}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Verification Matrix */}
      {report.verification && report.verification.performed && (
        <div className="result-section-card">
          <div className="card-title">
            <Activity size={16} color="#818cf8" /> Post-Action Verification Checks
          </div>
          <div className="policy-list">
            {Object.entries(report.verification.checks || {}).map(([key, item]) => (
              <div key={key} className={`policy-item ${item.passed ? 'passed' : 'failed'}`}>
                {item.passed ? (
                  <CheckCircle2 size={16} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />
                ) : (
                  <XCircle size={16} color="#f43f5e" style={{ flexShrink: 0, marginTop: '2px' }} />
                )}
                <div>
                  <strong style={{ textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}: </strong>
                  <span>{item.message}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations?.length > 0 && (
        <div className="result-section-card">
          <div className="card-title">
            <ArrowRight size={16} color="#38bdf8" /> Operational Recommendations
          </div>
          <ul style={{ paddingLeft: '20px', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            {report.recommendations.map((rec, idx) => (
              <li key={idx}>{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Audit Trail Timeline */}
      {report.audit_trail?.length > 0 && (
        <div className="result-section-card">
          <div className="card-title">
            <Clock size={16} color="var(--text-muted)" /> Agent Orchestration Audit Trail
          </div>
          <div className="timeline">
            {report.audit_trail.map((item, idx) => (
              <div key={idx} className="timeline-item">
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span className="timeline-step">{item.step}</span>
                  <span className="timeline-time">{item.timestamp?.split('T')[1]?.substring(0, 8)}</span>
                </div>
                <div style={{ color: 'var(--text-secondary)', marginTop: '2px' }}>{item.details}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
