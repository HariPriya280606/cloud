"""Comprehensive end-to-end tests for Agent scenarios and workflows."""
import pytest
from pydantic import ValidationError

from backend.agent import CostOptimizationAgent
from backend.models import (
    ActionType,
    FinalDecision,
    ReportStatus,
    ActionStatus,
)
from backend.schemas import OptimizationRequest, ServiceMetric
from backend.sample_data import get_scenario_request
from backend.report_generator import save_report, load_report


@pytest.fixture
def agent():
    return CostOptimizationAgent()


def test_valid_service_input():
    """Test requirement 1: Valid service input correctly parses."""
    req = get_scenario_request("scenario_a")
    assert len(req.services) == 2
    assert req.services[0].service_id == "orders-api"
    assert req.services[1].service_id == "reports-worker"


def test_invalid_cpu_value_above_100():
    """Test requirement 2: Invalid CPU value above 100 raises validation error."""
    with pytest.raises(ValidationError):
        ServiceMetric(
            service_id="bad-cpu-service",
            cpu_percent=105.0,  # Invalid: > 100
            memory_percent=50.0,
            requests_per_minute=100.0,
            latency_ms=50.0,
            instances=2,
            cost_per_hour=10.0,
            min_instances=1,
            max_instances=4,
            max_latency_ms=200.0,
            timestamp="2026-09-17T10:30:00Z",
        )


def test_invalid_instance_count_below_minimum():
    """Test requirement 3: Instances below min_instances raises validation error."""
    with pytest.raises(ValidationError):
        ServiceMetric(
            service_id="bad-instances-service",
            cpu_percent=50.0,
            memory_percent=50.0,
            requests_per_minute=100.0,
            latency_ms=50.0,
            instances=1,  # Invalid: below min_instances=2
            min_instances=2,
            max_instances=4,
            max_latency_ms=200.0,
            cost_per_hour=10.0,
            timestamp="2026-09-17T10:30:00Z",
        )


@pytest.mark.asyncio
async def test_scenario_a_cost_reduction(agent):
    """Test requirement 16: Test Input A produces a cost-reduction action."""
    req = get_scenario_request("scenario_a")
    report = await agent.run(req)

    assert report.status == ReportStatus.COMPLETED
    assert report.final_decision == FinalDecision.ACTION_TAKEN
    assert report.selected_action is not None
    assert report.selected_action.service_id == "reports-worker"
    assert report.selected_action.action == ActionType.SCALE_DOWN
    # Scaled down from 4 to 2 (safe max step of 2)
    assert report.selected_action.requested_instances in (1, 2)
    assert report.verification.performed is True
    assert report.verification.success is True
    assert report.verification.estimated_hourly_savings > 0.0


@pytest.mark.asyncio
async def test_scenario_b_scale_up_for_traffic(agent):
    """Test requirement 17: Test Input B produces a scale-up action."""
    req = get_scenario_request("scenario_b")
    report = await agent.run(req)

    assert report.status == ReportStatus.COMPLETED
    assert report.final_decision == FinalDecision.ACTION_TAKEN
    assert report.selected_action is not None
    assert report.selected_action.service_id == "orders-api"
    assert report.selected_action.action == ActionType.SCALE_UP
    assert report.selected_action.requested_instances == 5
    assert report.verification.performed is True
    assert report.verification.success is True


@pytest.mark.asyncio
async def test_scenario_c_stale_data_refusal(agent):
    """Test requirement 18: Test Input C refuses unsafe scale-down."""
    req = get_scenario_request("scenario_c")
    report = await agent.run(req)

    assert report.status == ReportStatus.BLOCKED
    assert report.final_decision == FinalDecision.STALE_DATA
    assert report.execution.attempted is False
    assert report.verification.success is False
    # Verify explanation mentions traffic divergence or stale observation
    assert "5200" in report.summary or "stale" in report.summary.lower() or "conflict" in report.summary.lower()


@pytest.mark.asyncio
async def test_scenario_d_capacity_unavailable_escalation(agent):
    """Test requirement 19: Test Input D reports action failure and escalation."""
    req = get_scenario_request("scenario_d")
    report = await agent.run(req)

    assert report.status == ReportStatus.FAILED
    assert report.final_decision == FinalDecision.ESCALATED
    assert report.execution.attempted is True
    assert report.execution.status == ActionStatus.FAILED
    assert report.execution.error == "capacity_unavailable"
    assert report.verification.success is False
    assert len(report.recommendations) > 0


@pytest.mark.asyncio
async def test_report_generation_and_persistence(agent):
    """Test requirement 14: Report JSON file is created and readable."""
    req = get_scenario_request("scenario_a")
    report = await agent.run(req)
    file_path = save_report(report)

    assert file_path.exists()
    loaded = load_report(report.report_id)
    assert loaded is not None
    assert loaded["report_id"] == report.report_id
    assert loaded["selected_action"]["service_id"] == "reports-worker"
