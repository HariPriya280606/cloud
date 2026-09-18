# Cloud Bill That Wouldn't Stop Growing 💸☁️

> **Autonomous Cloud Cost-Optimization Agent with Deterministic Safety Verification**

An enterprise-grade autonomous cloud cost-optimization system. The agent analyzes natural-language cloud operations requests alongside structured telemetry metrics, investigates unexpected or unnecessary cloud spending, proposes actions, validates them against strict deterministic safety policies, executes simulated cloud modifications, verifies post-action state and SLA compliance, and generates downloadable audit reports.

---

## 🏛️ Architecture Overview

```
User Request
    ↓
Agent Orchestrator (9-Step Workflow)
    ↓
Observation Tools (Metrics, Telemetry, Pricing, Health)
    ↓
Investigation and Candidate Generation (Cost Waste, Headroom, Traffic Trends)
    ↓
Deterministic Policy Engine (Freshness, Bounds, Health, Latency Safety Margin, Availability)
    ↓
Simulated Cloud Action API (Scale-Up, Scale-Down, Stop Idle Workload)
    ↓
Post-Action Verification (Instance Confirmation, SLA Checks, Rollback Guarantee)
    ↓
JSON Report and Download (reports/cloud_optimization_report_<id>.json)
```

---

## ✨ Key Features

- **Autonomous Multi-Intent Reasoning**: Interprets natural language requests (cost reduction, traffic surge scaling, latency protection, conditional scaling).
- **Deterministic Safety Guarantee**: LLMs never execute infrastructure actions directly. All candidate actions are validated and bounded by a strict rule engine.
- **Zero-External-Dependency Fallback**: Runs completely offline out-of-the-box using the built-in deterministic fallback engine, with plug-and-play support for any OpenAI-compatible API.
- **Data Freshness & Inconsistency Shield**: Detects stale metrics and diverging traffic telemetry, preventing dangerous scale-downs based on outdated observations.
- **Post-Action Verification & Rollback**: Re-queries telemetry post-scaling to verify instance counts, health checks, latency thresholds, and availability before reporting success.
- **Realistic Cloud Failure Injection**: Accurately simulates provider failure modes (e.g. `capacity_unavailable`) and triggers automated ops escalation.
- **Downloadable JSON Reports**: Persists UTF-8 JSON audit documents to `reports/` with direct single-click downloads and REST endpoints.
- **High-Fidelity Dashboard**: Interactive React + Vite interface with live resource gauges, inline JSON validation, preset scenarios, and step-by-step audit timelines.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn, python-dotenv, httpx |
| **Testing** | pytest, pytest-asyncio, FastAPI TestClient |
| **AI Reasoning** | OpenAI-compatible API Adapter + Offline Deterministic Rule Engine |
| **Frontend** | React 18, Vite, Lucide Icons, Vanilla CSS Design System |
| **Containerization** | Docker, Docker Compose |

---

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Backend Setup

```bash
# Clone the repository
git clone <repo-url>
cd cloud-cost-agent

# Install Python dependencies
pip install -r requirements.txt

# (Optional) Configure environment variables
cp .env.example .env

# Run FastAPI backend server
uvicorn backend.main:app --reload --port 8000
```
Backend will be available at `http://localhost:8000` with Swagger UI at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
Frontend dashboard will be running at `http://localhost:5173`.

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` to configure optional external LLM integration:

```ini
# Leave blank to use the offline deterministic fallback reasoning engine
LLM_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=10.0

PORT=8000
HOST=0.0.0.0
ENVIRONMENT=development
REPORTS_DIR=reports
```

---

## 🧪 Test Scenarios

The system includes 4 benchmark scenarios:

| Scenario | Request / Context | Expected Decision & Agent Behavior |
|---|---|---|
| **Scenario A: Idle Cost Waste** | *"Reduce cost without breaking latency/SLA"* with 0 rpm worker | Identifies `reports-worker` as cost waste candidate. Safely scales down from 4 to 2 (max step) with verified $22-$33/hr savings. |
| **Scenario B: Traffic Growth** | *"Orders traffic is increasing. Protect latency"* (2100 → 4200 rpm) | Detects +100% surge and approaching latency limits. Executes preventive scale-up from 4 to 5 instances. |
| **Scenario C: Stale Metrics Conflict** | Old metric (900 rpm @ 08:00) vs fresh traffic (5200 rpm @ 10:30) | Detects timestamp divergence and stale data. **Rejects scale-down** to prevent outage. Final decision: `stale_data`. |
| **Scenario D: Capacity Failure Mode** | `payment-api` at 91% CPU requires scale-up | Attempts scale-up, encounters simulated `capacity_unavailable`. Marks verification failed and escalates to ops. |

---

## 🛡️ Deterministic Safety Policies

Every candidate action passes through `backend/policy_engine.py`:

1. **Observation Freshness**: Rejects actions when metric age exceeds `maximum_observation_age_seconds` (default: 900s) or telemetry timestamps diverge.
2. **Instance Boundaries**: Strictly enforces `min_instances <= target_instances <= max_instances`.
3. **Scale Step Capping**: Restricts maximum instance change in a single run to `maximum_scale_step` (default: 2).
4. **Health Gate**: Prohibits scaling down or stopping degraded or unhealthy services (`healthy == false`).
5. **Latency Safety Margin**: Enforces headroom buffer (e.g. 20% margin: `latency <= max_latency * 0.8`).
6. **Availability Requirement**: Blocks scale-down if availability is below `minimum_availability_percent` (default: 99.0%).
7. **Traffic Surge Shield**: Blocks scale-down if traffic growth is +50% or doubling.
8. **Cooldown Period**: Prevents thrashing by enforcing a cooldown window between scaling actions.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root status and project info |
| `GET` | `/health` | Health check & environment status |
| `POST` | `/api/optimize` | Run 9-step optimization agent and return JSON report |
| `POST` | `/api/optimize/download` | Run optimization and download formatted JSON report file |
| `GET` | `/api/reports` | List all persisted report IDs |
| `GET` | `/api/reports/{report_id}` | Retrieve stored report JSON |
| `GET` | `/api/reports/{report_id}/download` | Download report JSON file |
| `POST` | `/api/scenarios/{scenario_name}` | Execute predefined scenario (`scenario_a` to `scenario_d`) |
| `GET` | `/api/services` | List active simulated cloud services |
| `POST` | `/api/reset` | Reset simulator state and action history |
| `GET` | `/docs` | OpenAPI / Swagger interactive documentation |

---

## 💻 Example Curl Request

```bash
curl -X POST "http://localhost:8000/api/optimize/download" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Reduce unnecessary cloud cost without breaking latency or availability.",
    "services": [
      {
        "service_id": "reports-worker",
        "cpu_percent": 9,
        "memory_percent": 15,
        "requests_per_minute": 0,
        "latency_ms": 0,
        "instances": 4,
        "cost_per_hour": 11.0,
        "min_instances": 1,
        "max_instances": 6,
        "max_latency_ms": 900,
        "healthy": true,
        "availability_percent": 99.99,
        "timestamp": "2026-09-17T10:30:00Z"
      }
    ],
    "latest_traffic": [],
    "recent_events": [],
    "environment_constraints": {
      "maximum_observation_age_seconds": 900,
      "maximum_scale_step": 2,
      "require_healthy_for_scale_down": true,
      "require_fresh_metrics_for_action": true,
      "latency_safety_margin_percent": 20,
      "minimum_availability_percent": 99.0,
      "max_action_retries": 1,
      "cooldown_seconds": 300
    }
  }' \
  --output cloud_optimization_report.json
```

---

## 📊 Sample Output Report (`reports/cloud_optimization_report_...json`)

```json
{
  "report_id": "report-9a4f210c",
  "created_at": "2026-09-18T14:15:00.000000+00:00",
  "user_request": "Review the current services and reduce unnecessary cost without breaking the latency or availability requirements.",
  "status": "completed",
  "intent": "cost_optimization",
  "summary": "Successfully optimized 'reports-worker': executed scale_down from 4 to 2 instances. Hourly savings: $22.00/hr (Est. Monthly: $16060.00/mo).",
  "observed_problem": {
    "type": "cost_waste",
    "description": "Idle capacity detected on 'reports-worker' with zero traffic (0 rpm) and low utilization (9.0% CPU).",
    "affected_services": [
      "reports-worker"
    ]
  },
  "observations": [
    {
      "service_id": "reports-worker",
      "metrics": {
        "service_id": "reports-worker",
        "cpu_percent": 9.0,
        "memory_percent": 15.0,
        "requests_per_minute": 0.0,
        "latency_ms": 0.0,
        "instances": 4,
        "cost_per_hour": 11.0,
        "min_instances": 1,
        "max_instances": 6,
        "max_latency_ms": 900.0,
        "healthy": true,
        "availability_percent": 99.99,
        "timestamp": "2026-09-17T10:30:00Z"
      },
      "observation_timestamp": "2026-09-17T10:30:00Z",
      "fresh": true,
      "age_seconds": 0.0,
      "findings": [
        "No current traffic (0 rpm)",
        "Low CPU utilization (9.0%)",
        "Low memory utilization (15.0%)",
        "Capacity is above minimum bound (4 > 1)"
      ]
    }
  ],
  "candidate_actions": [
    {
      "service_id": "reports-worker",
      "action": "scale_down",
      "target_instances": 2,
      "reason": "Zero traffic and low utilization (9.0% CPU, 15.0% Mem) allows safe scale-down.",
      "expected_hourly_savings": 22.0,
      "risk_level": "low"
    }
  ],
  "selected_action": {
    "service_id": "reports-worker",
    "action": "scale_down",
    "previous_instances": 4,
    "requested_instances": 2,
    "reason": "Zero traffic and low utilization (9.0% CPU, 15.0% Mem) allows safe scale-down.",
    "expected_hourly_savings": 22.0,
    "risk_level": "low"
  },
  "policy_checks": [
    {
      "check": "observation_freshness",
      "passed": true,
      "message": "Observation is fresh (age: 0s <= 900s)."
    },
    {
      "check": "instance_bounds",
      "passed": true,
      "message": "Target instances (2) is within safe bounds [1, 6]."
    },
    {
      "check": "maximum_scale_step",
      "passed": true,
      "message": "Instance delta (2) is within maximum scale step (2)."
    },
    {
      "check": "health",
      "passed": true,
      "message": "Service 'reports-worker' health state (healthy) permits proposed action."
    },
    {
      "check": "latency_safety_margin",
      "passed": true,
      "message": "Latency (0.0ms) is within safe limits (max: 900.0ms)."
    },
    {
      "check": "availability_requirement",
      "passed": true,
      "message": "Availability (99.99%) meets SLA requirement (99.0%)."
    }
  ],
  "execution": {
    "attempted": true,
    "action_id": "act-5b23d9",
    "status": "succeeded",
    "error": null,
    "retries": 0
  },
  "verification": {
    "performed": true,
    "success": true,
    "checks": {
      "instance_count": {
        "passed": true,
        "message": "Requested instance count is active (2)."
      },
      "health": {
        "passed": true,
        "message": "Service is healthy."
      },
      "latency": {
        "passed": true,
        "message": "Latency (0.0ms) is within the configured maximum (900.0ms)."
      },
      "availability": {
        "passed": true,
        "message": "Availability (99.99%) remains acceptable (>= 99.0%)."
      },
      "cost": {
        "passed": true,
        "message": "Estimated hourly cost decreased from $44.00 to $22.00 (Savings: $22.00/hr)."
      }
    },
    "estimated_hourly_cost_before": 44.0,
    "estimated_hourly_cost_after": 22.0,
    "estimated_hourly_savings": 22.0
  },
  "final_decision": "action_taken",
  "recommendations": [
    "Consider setting up auto-scaling schedule for 'reports-worker'."
  ],
  "audit_trail": [
    {
      "step": "start",
      "timestamp": "2026-09-18T14:15:00.000000+00:00",
      "details": "Initiated optimization run for request: 'Review the current services and reduce unnecessary cost without breaking the latency or availability requirements.'"
    },
    {
      "step": "observe",
      "timestamp": "2026-09-18T14:15:00.010000+00:00",
      "details": "Inspecting telemetry for 2 service(s)."
    },
    {
      "step": "policy_validation",
      "timestamp": "2026-09-18T14:15:00.020000+00:00",
      "details": "Running deterministic safety checks on 'scale_down' for 'reports-worker'."
    },
    {
      "step": "execute",
      "timestamp": "2026-09-18T14:15:00.030000+00:00",
      "details": "Dispatching 'scale_down' to target instances: 2."
    },
    {
      "step": "verify",
      "timestamp": "2026-09-18T14:15:00.040000+00:00",
      "details": "Performing post-action state verification and SLA validation."
    }
  ],
  "download_url": "/api/reports/report-9a4f210c/download"
}
```

---

## 🧪 Running Automated Tests

Run the full pytest suite covering all unit, integration, scenario, and error cases:

```bash
pytest backend/tests -v
```

Output:
```text
======================= 24 passed in 1.15s =======================
```

---

## 🔒 Security & Safety Controls

- **No Arbitrary Execution**: The agent never executes raw shell commands or direct infrastructure code.
- **Path Traversal Protection**: Report IDs and filenames are strictly alphanumeric sanitized.
- **Credential Hygiene**: API keys are loaded via environment variables and never logged or serialized into reports.
- **SLA Air-Gap**: Verification must independently confirm healthy metrics post-scaling before any success is reported.

---

## 📈 Future Enhancements

- SQLite / PostgreSQL persistence for long-term historical trends.
- Automated multi-AZ load rebalancing.
- Real-time Prometheus / OpenTelemetry ingestion adapters.
