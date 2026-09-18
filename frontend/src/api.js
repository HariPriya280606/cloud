/**
 * API client module for communicating with the backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function optimizeServices(requestData) {
  const res = await fetch(`${API_BASE}/api/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || (err.details && err.details.join(', ')) || 'Optimization request failed');
  }
  return res.json();
}

export async function runScenarioApi(scenarioName) {
  const res = await fetch(`${API_BASE}/api/scenarios/${scenarioName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Scenario run failed');
  }
  return res.json();
}

export async function resetSimulatorApi() {
  const res = await fetch(`${API_BASE}/api/reset`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Reset failed');
  return res.json();
}

export async function fetchSimulatedServices() {
  const res = await fetch(`${API_BASE}/api/services`);
  if (!res.ok) throw new Error('Failed to fetch services');
  return res.json();
}

export async function downloadReportFile(reportId) {
  const url = `${API_BASE}/api/reports/${reportId}/download`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to download report file');
  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `cloud_optimization_report_${reportId}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}

export async function optimizeAndDirectDownload(requestData) {
  const res = await fetch(`${API_BASE}/api/optimize/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestData),
  });
  if (!res.ok) throw new Error('Failed to download optimization report');
  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = 'cloud_optimization_report.json';
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}
