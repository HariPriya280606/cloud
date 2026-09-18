"""Pre-configured Test Scenarios A, B, C, and D."""
from typing import Dict, Any
from backend.schemas import OptimizationRequest

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "scenario_a": {
        "user_request": "Review the current services and reduce unnecessary cost without breaking the latency or availability requirements.",
        "services": [
            {
                "service_id": "orders-api",
                "cpu_percent": 22.0,
                "memory_percent": 41.0,
                "requests_per_minute": 1200.0,
                "latency_ms": 180.0,
                "instances": 6,
                "cost_per_hour": 18.50,
                "min_instances": 2,
                "max_instances": 8,
                "max_latency_ms": 300.0,
                "healthy": True,
                "availability_percent": 99.99,
                "timestamp": "2026-09-17T10:30:00Z",
            },
            {
                "service_id": "reports-worker",
                "cpu_percent": 9.0,
                "memory_percent": 15.0,
                "requests_per_minute": 0.0,
                "latency_ms": 0.0,
                "instances": 4,
                "cost_per_hour": 11.00,
                "min_instances": 1,
                "max_instances": 6,
                "max_latency_ms": 900.0,
                "healthy": True,
                "availability_percent": 99.99,
                "timestamp": "2026-09-17T10:30:00Z",
            },
        ],
        "latest_traffic": [],
        "recent_events": [],
        "environment_constraints": {
            "maximum_observation_age_seconds": 900,
            "maximum_scale_step": 2,
            "require_healthy_for_scale_down": True,
            "require_fresh_metrics_for_action": True,
            "latency_safety_margin_percent": 20.0,
            "minimum_availability_percent": 99.0,
            "max_action_retries": 1,
            "cooldown_seconds": 300,
        },
        "requested_scenario": "scenario_a",
    },
    "scenario_b": {
        "user_request": "Orders traffic is increasing. Keep the service within its latency target.",
        "services": [
            {
                "service_id": "orders-api",
                "cpu_percent": 28.0,
                "memory_percent": 48.0,
                "requests_per_minute": 4200.0,
                "previous_requests_per_minute": 2100.0,
                "latency_ms": 260.0,
                "instances": 4,
                "cost_per_hour": 18.50,
                "min_instances": 2,
                "max_instances": 8,
                "max_latency_ms": 300.0,
                "healthy": True,
                "availability_percent": 99.99,
                "timestamp": "2026-09-17T10:30:00Z",
            },
        ],
        "latest_traffic": [],
        "recent_events": [],
        "environment_constraints": {
            "maximum_observation_age_seconds": 900,
            "maximum_scale_step": 2,
            "require_healthy_for_scale_down": True,
            "require_fresh_metrics_for_action": True,
            "latency_safety_margin_percent": 20.0,
            "minimum_availability_percent": 99.0,
            "max_action_retries": 1,
            "cooldown_seconds": 300,
        },
        "requested_scenario": "scenario_b",
    },
    "scenario_c": {
        "user_request": "Reduce cost if it is safe.",
        "services": [
            {
                "service_id": "checkout-api",
                "cpu_percent": 24.0,
                "memory_percent": 39.0,
                "requests_per_minute": 900.0,
                "latency_ms": 170.0,
                "instances": 5,
                "cost_per_hour": 20.00,
                "min_instances": 2,
                "max_instances": 8,
                "max_latency_ms": 250.0,
                "healthy": True,
                "availability_percent": 99.99,
                "timestamp": "2026-09-17T08:00:00Z",
            },
        ],
        "latest_traffic": [
            {
                "service_id": "checkout-api",
                "requests_per_minute": 5200.0,
                "timestamp": "2026-09-17T10:30:00Z",
            },
        ],
        "recent_events": [],
        "environment_constraints": {
            "maximum_observation_age_seconds": 900,
            "maximum_scale_step": 2,
            "require_healthy_for_scale_down": True,
            "require_fresh_metrics_for_action": True,
            "latency_safety_margin_percent": 20.0,
            "minimum_availability_percent": 99.0,
            "max_action_retries": 1,
            "cooldown_seconds": 300,
        },
        "requested_scenario": "scenario_c",
    },
    "scenario_d": {
        "user_request": "Scale the payment service only if the current state requires it.",
        "services": [
            {
                "service_id": "payment-api",
                "cpu_percent": 91.0,
                "memory_percent": 82.0,
                "requests_per_minute": 6400.0,
                "latency_ms": 410.0,
                "instances": 3,
                "cost_per_hour": 22.00,
                "min_instances": 2,
                "max_instances": 8,
                "max_latency_ms": 300.0,
                "healthy": True,
                "availability_percent": 99.5,
                "timestamp": "2026-09-17T10:30:00Z",
            },
        ],
        "latest_traffic": [],
        "recent_events": [],
        "environment_constraints": {
            "maximum_observation_age_seconds": 900,
            "maximum_scale_step": 2,
            "require_healthy_for_scale_down": True,
            "require_fresh_metrics_for_action": True,
            "latency_safety_margin_percent": 20.0,
            "minimum_availability_percent": 99.0,
            "max_action_retries": 1,
            "cooldown_seconds": 300,
        },
        "requested_scenario": "scenario_d",
    },
}


def get_scenario_request(name: str) -> OptimizationRequest:
    """Load and validate an OptimizationRequest for a named test scenario."""
    key = name.lower().strip()
    if key not in SCENARIOS:
        raise KeyError(f"Unknown scenario '{name}'. Available: {list(SCENARIOS.keys())}")
    return OptimizationRequest.model_validate(SCENARIOS[key])
