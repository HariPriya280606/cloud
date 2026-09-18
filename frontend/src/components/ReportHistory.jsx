import React, { useState, useEffect, useCallback } from 'react';

/**
 * ReportHistory — lists all persisted reports from the backend and allows
 * the user to load a report into the result panel or download it as JSON.
 */
export default function ReportHistory({ onLoadReport }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loadingId, setLoadingId] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/reports`);
      if (!res.ok) throw new Error(`Failed to fetch reports: ${res.statusText}`);
      const data = await res.json();
      setReports(data.reports || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [API_BASE]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleLoad = async (reportId) => {
    setLoadingId(reportId);
    try {
      const res = await fetch(`${API_BASE}/api/reports/${reportId}`);
      if (!res.ok) throw new Error('Report not found');
      const data = await res.json();
      onLoadReport(data);
    } catch (err) {
      setError(`Load failed: ${err.message}`);
    } finally {
      setLoadingId(null);
    }
  };

  const handleDownload = async (reportId) => {
    setDownloadingId(reportId);
    try {
      const url = `${API_BASE}/api/reports/${reportId}/download`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `cloud_optimization_report_${reportId}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      setError(`Download failed: ${err.message}`);
    } finally {
      setDownloadingId(null);
    }
  };

  // Parse timestamp from report ID format: <uuid>_<yyyymmdd>_<hhmmss>
  const formatTimestamp = (reportId) => {
    const parts = reportId.split('_');
    if (parts.length >= 3) {
      const datePart = parts[parts.length - 2];
      const timePart = parts[parts.length - 1];
      if (datePart && timePart && datePart.length === 8 && timePart.length === 6) {
        const y = datePart.slice(0, 4);
        const mo = datePart.slice(4, 6);
        const d = datePart.slice(6, 8);
        const h = timePart.slice(0, 2);
        const mi = timePart.slice(2, 4);
        const s = timePart.slice(4, 6);
        return `${y}-${mo}-${d} ${h}:${mi}:${s}`;
      }
    }
    return reportId;
  };

  return (
    <div className="history-panel">
      <div className="history-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <div className="history-title">
          <span>🗂</span>
          <span>Report History</span>
          {reports.length > 0 && (
            <span className="history-count-badge">{reports.length}</span>
          )}
        </div>
        <div className="history-header-actions">
          <button
            className="btn-icon"
            title="Refresh"
            onClick={(e) => { e.stopPropagation(); fetchReports(); }}
            disabled={loading}
          >
            {loading ? '⏳' : '↻'}
          </button>
          <span className="history-chevron">{isCollapsed ? '▶' : '▼'}</span>
        </div>
      </div>

      {!isCollapsed && (
        <div className="history-body">
          {error && (
            <div className="history-error">{error}</div>
          )}

          {!loading && reports.length === 0 && !error && (
            <div className="history-empty">
              No reports generated yet. Run an analysis to create one.
            </div>
          )}

          {reports.length > 0 && (
            <div className="history-list">
              {reports.map((reportId) => (
                <div key={reportId} className="history-item">
                  <div className="history-item-info">
                    <div className="history-item-id">{reportId.slice(0, 8)}…</div>
                    <div className="history-item-ts">{formatTimestamp(reportId)}</div>
                  </div>
                  <div className="history-item-actions">
                    <button
                      className="btn-history-load"
                      onClick={() => handleLoad(reportId)}
                      disabled={loadingId === reportId}
                      title="Load report into result panel"
                    >
                      {loadingId === reportId ? '…' : '⬆ Load'}
                    </button>
                    <button
                      className="btn-history-dl"
                      onClick={() => handleDownload(reportId)}
                      disabled={downloadingId === reportId}
                      title="Download JSON file"
                    >
                      {downloadingId === reportId ? '…' : '↓'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
