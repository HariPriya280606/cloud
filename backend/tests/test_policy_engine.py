"""Unit tests for Deterministic Safety Policy Engine."""
import pytest
from datetime import datetime, timezone, timedelta
from backend.models import ActionType
from backend.schemas import (
    ServiceMetric,
    TrafficObservation,
    EnvironmentConstraints,
)
from backend.policy_engine import PolicyEngine


@pytest.fixture
def policy_eng():
    return PolicyEngine()


@pytest.fixture
def default_constraints():
    return EnvironmentConstraints(
        maximum_observation_age_seconds=900,
        maximum_scale_step=2,
        require_healthy_for_scale_down=True,
        require_fresh_metrics_for_action=True,
        latency_safety_margin_percent=20.0,
        minimum_availability_percent=99.0,
        max_action_retries=1,
        cooldown_seconds=300,
    )


@pytest.fixture
def base_service():
    now_iso = datetime.now(timezone.utc).isoformat()
    return ServiceMetric(
        service_id="test-service",
        cpu_percent=15.0,
        memory_percent=20.0,
        requests_per_minute=0.0,
        latency_ms=50.0,
        instances=4,
        cost_per_hour=10.0,
        min_instances=1,
        max_instances=8,
        max_latency_ms=300.0,
        healthy=True,
        availability_percent=99.99,
        timestamp=now_iso,
    )


def test_scale_down_cannot_go_below_min_instances(policy_eng, default_constraints, base_service):
    """Test requirement 4: Scale-down cannot go below minimum instances."""
    is_approved, checks, target = policy_eng.validate_action(
        service=base_service,
        action=ActionType.SCALE_DOWN,
        target_instances=0,  # Below min_instances=1
        constraints=default_constraints,
    )
    assert not is_approved
    bounds_check = next(c for c in checks if c.check == "instance_bounds")
    assert not bounds_check.passed


def test_scale_up_cannot_exceed_max_instances(policy_eng, default_constraints, base_service):
    """Test requirement 5: Scale-up cannot exceed maximum instances."""
    is_approved, checks, target = policy_eng.validate_action(
        service=base_service,
        action=ActionType.SCALE_UP,
        target_instances=10,  # Above max_instances=8
        constraints=default_constraints,
    )
    assert not is_approved
    bounds_check = next(c for c in checks if c.check == "instance_bounds")
    assert not bounds_check.passed


def test_scale_down_capped_by_max_step(policy_eng, default_constraints, base_service):
    """Test that requesting scale down larger than max_scale_step is safely capped."""
    # Current instances: 4, requesting target: 1 (delta 3 > max_step 2)
    is_approved, checks, target = policy_eng.validate_action(
        service=base_service,
        action=ActionType.SCALE_DOWN,
        target_instances=1,
        constraints=default_constraints,
    )
    assert is_approved
    assert target == 2  # Capped 4 - 2 = 2


def test_unhealthy_services_cannot_be_scaled_down(policy_eng, default_constraints, base_service):
    """Test requirement 6: Unhealthy services cannot be scaled down."""
    unhealthy = base_service.model_copy(update={"healthy": False})
    is_approved, checks, target = policy_eng.validate_action(
        service=unhealthy,
        action=ActionType.SCALE_DOWN,
        target_instances=2,
        constraints=default_constraints,
    )
    assert not is_approved
    health_check = next(c for c in checks if c.check == "health")
    assert not health_check.passed


def test_latency_safety_margin_enforced(policy_eng, default_constraints, base_service):
    """Test scale-down rejected when latency is within safety margin of max_latency."""
    # max_latency: 300ms, margin: 20% -> threshold is 240ms. If latency is 250ms, reject scale-down.
    high_latency = base_service.model_copy(update={"latency_ms": 250.0, "max_latency_ms": 300.0})
    is_approved, checks, target = policy_eng.validate_action(
        service=high_latency,
        action=ActionType.SCALE_DOWN,
        target_instances=2,
        constraints=default_constraints,
    )
    assert not is_approved
    lat_check = next(c for c in checks if c.check == "latency_safety_margin")
    assert not lat_check.passed


def test_rapid_traffic_increase_prevents_scale_down(policy_eng, default_constraints, base_service):
    """Test requirement 8: Rapidly increasing traffic prevents scale-down."""
    surging = base_service.model_copy(update={
        "requests_per_minute": 2000.0,
        "previous_requests_per_minute": 1000.0,  # 100% surge
    })
    is_approved, checks, target = policy_eng.validate_action(
        service=surging,
        action=ActionType.SCALE_DOWN,
        target_instances=2,
        constraints=default_constraints,
    )
    assert not is_approved
    traf_check = next(c for c in checks if c.check == "traffic_stability")
    assert not traf_check.passed


def test_stale_metrics_rejected(policy_eng, default_constraints, base_service):
    """Test requirement 7: Stale metrics result in safety check failure."""
    old_time = (datetime.now(timezone.utc) - timedelta(seconds=2000)).isoformat()
    stale_service = base_service.model_copy(update={"timestamp": old_time})
    is_approved, checks, target = policy_eng.validate_action(
        service=stale_service,
        action=ActionType.SCALE_DOWN,
        target_instances=2,
        constraints=default_constraints,
        reference_timestamp=datetime.now(timezone.utc),
    )
    assert not is_approved
    fresh_check = next(c for c in checks if c.check == "observation_freshness")
    assert not fresh_check.passed
