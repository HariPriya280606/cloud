import React, { useState, useEffect } from 'react';
import Header from './components/Header.jsx';
import ScenarioButtons from './components/ScenarioButtons.jsx';
import RequestForm from './components/RequestForm.jsx';
import ServiceInput from './components/ServiceInput.jsx';
import ServiceTable from './components/ServiceTable.jsx';
import ResultPanel from './components/ResultPanel.jsx';
import ReportHistory from './components/ReportHistory.jsx';
import LiveSimulatorState from './components/LiveSimulatorState.jsx';
import { 
  optimizeServices, 
  runScenarioApi, 
  resetSimulatorApi, 
  downloadReportFile, 
  optimizeAndDirectDownload 
} from './api.js';

// Predefined Scenario Data
const SCENARIO_DATA = {
  scenario_a: {
    user_request: "Review the current services and reduce unnecessary cost without breaking the latency or availability requirements.",
    services: [
      {
        service_id: "orders-api",
        cpu_percent: 22.0,
        memory_percent: 41.0,
        requests_per_minute: 1200.0,
        latency_ms: 180.0,
        instances: 6,
        cost_per_hour: 18.50,
        min_instances: 2,
        max_instances: 8,
        max_latency_ms: 300.0,
        healthy: true,
        availability_percent: 99.99,
        timestamp: "2026-09-17T10:30:00Z"
      },
      {
        service_id: "reports-worker",
        cpu_percent: 9.0,
        memory_percent: 15.0,
        requests_per_minute: 0.0,
        latency_ms: 0.0,
        instances: 4,
        cost_per_hour: 11.00,
        min_instances: 1,
        max_instances: 6,
        max_latency_ms: 900.0,
        healthy: true,
        availability_percent: 99.99,
        timestamp: "2026-09-17T10:30:00Z"
      }
    ],
    latest_traffic: [],
    recent_events: [],
    environment_constraints: {
      maximum_observation_age_seconds: 900,
      maximum_scale_step: 2,
      require_healthy_for_scale_down: true,
      require_fresh_metrics_for_action: true,
      latency_safety_margin_percent: 20.0,
      minimum_availability_percent: 99.0,
      max_action_retries: 1,
      cooldown_seconds: 300
    }
  },
  scenario_b: {
    user_request: "Orders traffic is increasing. Keep the service within its latency target.",
    services: [
      {
        service_id: "orders-api",
        cpu_percent: 28.0,
        memory_percent: 48.0,
        requests_per_minute: 4200.0,
        previous_requests_per_minute: 2100.0,
        latency_ms: 260.0,
        instances: 4,
        cost_per_hour: 18.50,
        min_instances: 2,
        max_instances: 8,
        max_latency_ms: 300.0,
        healthy: true,
        availability_percent: 99.99,
        timestamp: "2026-09-17T10:30:00Z"
      }
    ],
    latest_traffic: [],
    recent_events: [],
    environment_constraints: {
      maximum_observation_age_seconds: 900,
      maximum_scale_step: 2,
      require_healthy_for_scale_down: true,
      require_fresh_metrics_for_action: true,
      latency_safety_margin_percent: 20.0,
      minimum_availability_percent: 99.0,
      max_action_retries: 1,
      cooldown_seconds: 300
    }
  },
  scenario_c: {
    user_request: "Reduce cost if it is safe.",
    services: [
      {
        service_id: "checkout-api",
        cpu_percent: 24.0,
        memory_percent: 39.0,
        requests_per_minute: 900.0,
        latency_ms: 170.0,
        instances: 5,
        cost_per_hour: 20.00,
        min_instances: 2,
        max_instances: 8,
        max_latency_ms: 250.0,
        healthy: true,
        availability_percent: 99.99,
        timestamp: "2026-09-17T08:00:00Z"
      }
    ],
    latest_traffic: [
      {
        service_id: "checkout-api",
        requests_per_minute: 5200.0,
        timestamp: "2026-09-17T10:30:00Z"
      }
    ],
    recent_events: [],
    environment_constraints: {
      maximum_observation_age_seconds: 900,
      maximum_scale_step: 2,
      require_healthy_for_scale_down: true,
      require_fresh_metrics_for_action: true,
      latency_safety_margin_percent: 20.0,
      minimum_availability_percent: 99.0,
      max_action_retries: 1,
      cooldown_seconds: 300
    }
  },
  scenario_d: {
    user_request: "Scale the payment service only if the current state requires it.",
    services: [
      {
        service_id: "payment-api",
        cpu_percent: 91.0,
        memory_percent: 82.0,
        requests_per_minute: 6400.0,
        latency_ms: 410.0,
        instances: 3,
        cost_per_hour: 22.00,
        min_instances: 2,
        max_instances: 8,
        max_latency_ms: 300.0,
        healthy: true,
        availability_percent: 99.5,
        timestamp: "2026-09-17T10:30:00Z"
      }
    ],
    latest_traffic: [],
    recent_events: [],
    environment_constraints: {
      maximum_observation_age_seconds: 900,
      maximum_scale_step: 2,
      require_healthy_for_scale_down: true,
      require_fresh_metrics_for_action: true,
      latency_safety_margin_percent: 20.0,
      minimum_availability_percent: 99.0,
      max_action_retries: 1,
      cooldown_seconds: 300
    }
  }
};

export default function App() {
  const [currentScenario, setCurrentScenario] = useState('scenario_a');
  const [userRequest, setUserRequest] = useState(SCENARIO_DATA.scenario_a.user_request);
  const [servicesJson, setServicesJson] = useState(JSON.stringify(SCENARIO_DATA.scenario_a.services, null, 2));
  const [trafficJson, setTrafficJson] = useState(JSON.stringify(SCENARIO_DATA.scenario_a.latest_traffic, null, 2));
  const [eventsJson, setEventsJson] = useState(JSON.stringify(SCENARIO_DATA.scenario_a.recent_events, null, 2));
  const [constraintsJson, setConstraintsJson] = useState(JSON.stringify(SCENARIO_DATA.scenario_a.environment_constraints, null, 2));
  
  const [parsedServices, setParsedServices] = useState(SCENARIO_DATA.scenario_a.services);
  const [servicesError, setServicesError] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [generalError, setGeneralError] = useState(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  const [liveRefreshKey, setLiveRefreshKey] = useState(0);

  // Sync parsed services whenever servicesJson changes
  useEffect(() => {
    try {
      const parsed = JSON.parse(servicesJson);
      if (Array.isArray(parsed)) {
        setParsedServices(parsed);
        setServicesError(null);
      } else {
        setServicesError('Services payload must be a JSON array of objects.');
      }
    } catch (e) {
      setServicesError(`Invalid JSON: ${e.message}`);
    }
  }, [servicesJson]);

  // Handle Scenario Selection
  const handleSelectScenario = (scId) => {
    setCurrentScenario(scId);
    const sc = SCENARIO_DATA[scId];
    if (sc) {
      setUserRequest(sc.user_request);
      setServicesJson(JSON.stringify(sc.services, null, 2));
      setTrafficJson(JSON.stringify(sc.latest_traffic, null, 2));
      setEventsJson(JSON.stringify(sc.recent_events, null, 2));
      setConstraintsJson(JSON.stringify(sc.environment_constraints, null, 2));
      setGeneralError(null);
    }
  };

  // Build Payload
  const buildPayload = () => {
    let services, latest_traffic = [], recent_events = [], environment_constraints = {};
    try {
      services = JSON.parse(servicesJson);
    } catch (e) {
      throw new Error(`Services JSON is invalid: ${e.message}`);
    }

    try {
      if (trafficJson.trim()) latest_traffic = JSON.parse(trafficJson);
    } catch (e) {
      throw new Error(`Latest Traffic JSON is invalid: ${e.message}`);
    }

    try {
      if (eventsJson.trim()) recent_events = JSON.parse(eventsJson);
    } catch (e) {
      throw new Error(`Recent Events JSON is invalid: ${e.message}`);
    }

    try {
      if (constraintsJson.trim()) environment_constraints = JSON.parse(constraintsJson);
    } catch (e) {
      throw new Error(`Environment Constraints JSON is invalid: ${e.message}`);
    }

    return {
      user_request: userRequest,
      services,
      latest_traffic,
      recent_events,
      environment_constraints,
      requested_scenario: currentScenario,
    };
  };

  // Load a historical report into the result panel
  const handleLoadHistoryReport = (reportData) => {
    setReport(reportData);
    setGeneralError(null);
    // Scroll result panel into view on mobile
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Run Custom Analysis
  const handleAnalyze = async () => {
    setGeneralError(null);
    setLoading(true);
    try {
      const payload = buildPayload();
      const res = await optimizeServices(payload);
      setReport(res);
      setHistoryRefreshKey((k) => k + 1);
      setLiveRefreshKey((k) => k + 1);
    } catch (err) {
      setGeneralError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Direct Run Scenario
  const handleRunScenarioDirect = async (scId) => {
    handleSelectScenario(scId);
    setGeneralError(null);
    setLoading(true);
    try {
      const res = await runScenarioApi(scId);
      setReport(res);
      setHistoryRefreshKey((k) => k + 1);
      setLiveRefreshKey((k) => k + 1);
    } catch (err) {
      setGeneralError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Direct Download
  const handleDirectDownload = async () => {
    setGeneralError(null);
    try {
      const payload = buildPayload();
      await optimizeAndDirectDownload(payload);
    } catch (err) {
      setGeneralError(err.message);
    }
  };

  // Download Existing Report
  const handleDownloadReport = async (reportId) => {
    try {
      await downloadReportFile(reportId);
    } catch (err) {
      setGeneralError(err.message);
    }
  };

  // Reset Environment
  const handleReset = async () => {
    setIsResetting(true);
    setGeneralError(null);
    try {
      await resetSimulatorApi();
      handleSelectScenario('scenario_a');
      setReport(null);
      setLiveRefreshKey((k) => k + 1);
    } catch (err) {
      setGeneralError('Reset failed: ' + err.message);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="app-container">
      <Header onReset={handleReset} isResetting={isResetting} />

      <ScenarioButtons
        currentScenario={currentScenario}
        onSelectScenario={handleSelectScenario}
        onRunScenario={handleRunScenarioDirect}
        loading={loading}
      />

      <ReportHistory
        key={historyRefreshKey}
        onLoadReport={handleLoadHistoryReport}
      />

      <LiveSimulatorState refreshTrigger={liveRefreshKey} />

      {generalError && (
        <div style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.3)', color: '#fb7185', padding: '12px 16px', borderRadius: '8px', marginBottom: '20px' }}>
          <strong>Error: </strong> {generalError}
        </div>
      )}

      <div className="main-grid">
        {/* Left Column: Inputs & Monitored Services */}
        <div className="panel">
          <RequestForm
            userRequest={userRequest}
            setUserRequest={setUserRequest}
            onAnalyze={handleAnalyze}
            onDirectDownload={handleDirectDownload}
            loading={loading}
          />

          <div className="section-label" style={{ marginTop: '8px' }}>Active Infrastructure Telemetry</div>
          <ServiceTable services={parsedServices} />

          <ServiceInput
            servicesJson={servicesJson}
            setServicesJson={setServicesJson}
            trafficJson={trafficJson}
            setTrafficJson={setTrafficJson}
            eventsJson={eventsJson}
            setEventsJson={setEventsJson}
            constraintsJson={constraintsJson}
            setConstraintsJson={setConstraintsJson}
            servicesError={servicesError}
          />
        </div>

        {/* Right Column: Result Panel */}
        <ResultPanel
          report={report}
          loading={loading}
          onDownloadReport={handleDownloadReport}
        />
      </div>
    </div>
  );
}
