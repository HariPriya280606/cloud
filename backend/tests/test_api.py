"""Integration tests for FastAPI REST Endpoints using httpx and TestClient."""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.sample_data import SCENARIOS

client = TestClient(app)


def test_root_and_health():
    """Test GET / and GET /health."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Cloud Bill That Wouldn't Stop Growing" in res_root.json()["project"]

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"


def test_api_optimize_scenario_a():
    """Test POST /api/optimize with Scenario A payload."""
    payload = SCENARIOS["scenario_a"]
    res = client.post("/api/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["selected_action"]["service_id"] == "reports-worker"
    assert data["selected_action"]["action"] == "scale_down"
    assert data["verification"]["success"] is True
    assert "download_url" in data


def test_api_optimize_download():
    """Test requirement 15: Direct download endpoint POST /api/optimize/download."""
    payload = SCENARIOS["scenario_a"]
    res = client.post("/api/optimize/download", json=payload)
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
    assert "attachment; filename=cloud_optimization_report_" in res.headers.get("content-disposition", "")
    json_data = res.json()
    assert json_data["selected_action"]["service_id"] == "reports-worker"


def test_api_scenario_endpoints():
    """Test POST /api/scenarios/{scenario_name} for all 4 scenarios."""
    # Scenario A
    res_a = client.post("/api/scenarios/scenario_a")
    assert res_a.status_code == 200
    assert res_a.json()["final_decision"] == "action_taken"

    # Scenario B
    res_b = client.post("/api/scenarios/scenario_b")
    assert res_b.status_code == 200
    assert res_b.json()["selected_action"]["action"] == "scale_up"

    # Scenario C
    res_c = client.post("/api/scenarios/scenario_c")
    assert res_c.status_code == 200
    assert res_c.json()["final_decision"] == "stale_data"

    # Scenario D
    res_d = client.post("/api/scenarios/scenario_d")
    assert res_d.status_code == 200
    assert res_d.json()["final_decision"] == "escalated"


def test_api_report_retrieval_and_download():
    """Test GET /api/reports/{id} and GET /api/reports/{id}/download."""
    res_opt = client.post("/api/scenarios/scenario_a")
    report_id = res_opt.json()["report_id"]

    res_get = client.get(f"/api/reports/{report_id}")
    assert res_get.status_code == 200
    assert res_get.json()["report_id"] == report_id

    res_dl = client.get(f"/api/reports/{report_id}/download")
    assert res_dl.status_code == 200
    assert "attachment;" in res_dl.headers.get("content-disposition", "")


def test_api_validation_error_empty_services():
    """Test 422 error on empty services list."""
    bad_payload = {
        "user_request": "Optimize costs",
        "services": [],
    }
    res = client.post("/api/optimize", json=bad_payload)
    assert res.status_code == 422


def test_api_validation_error_duplicate_service_ids():
    """Test 422 error on duplicate service IDs."""
    bad_payload = {
        "user_request": "Optimize costs",
        "services": [
            {
                "service_id": "dup-service",
                "cpu_percent": 10.0,
                "memory_percent": 10.0,
                "requests_per_minute": 0.0,
                "latency_ms": 10.0,
                "instances": 2,
                "min_instances": 1,
                "max_instances": 4,
                "max_latency_ms": 200.0,
                "cost_per_hour": 5.0,
                "timestamp": "2026-09-17T10:30:00Z",
            },
            {
                "service_id": "dup-service",
                "cpu_percent": 20.0,
                "memory_percent": 20.0,
                "requests_per_minute": 0.0,
                "latency_ms": 10.0,
                "instances": 2,
                "min_instances": 1,
                "max_instances": 4,
                "max_latency_ms": 200.0,
                "cost_per_hour": 5.0,
                "timestamp": "2026-09-17T10:30:00Z",
            },
        ],
    }
    res = client.post("/api/optimize", json=bad_payload)
    assert res.status_code == 422


def test_api_unknown_scenario_404():
    """Test 404 error when requesting unknown scenario."""
    res = client.post("/api/scenarios/scenario_xyz")
    assert res.status_code == 404


def test_api_reset_and_services():
    """Test POST /api/reset and GET /api/services."""
    res_reset = client.post("/api/reset")
    assert res_reset.status_code == 200

    res_services = client.get("/api/services")
    assert res_services.status_code == 200
    assert "services" in res_services.json()
