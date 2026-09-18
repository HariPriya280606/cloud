"""Pydantic v2 schemas for OptimizationRequest and OptimizationReport."""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from backend.models import (
    IntentType,
    ActionType,
    ActionStatus,
    ReportStatus,
    FinalDecision,
    ProblemType,
)


def parse_iso_datetime(value: Union[str, datetime]) -> datetime:
    """Validate and convert ISO-8601 string or datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        val = value.strip()
        if val.endswith("Z"):
            val = val[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(val)
        except ValueError as exc:
            raise ValueError(f"Invalid ISO-8601 datetime format: {value}") from exc
    raise ValueError(f"Expected datetime or ISO string, got {type(value)}")


class ServiceMetric(BaseModel):
    """Observation and baseline metric for a single simulated service."""
    service_id: str = Field(..., min_length=1, description="Unique non-empty service identifier")
    cpu_percent: float = Field(..., ge=0.0, le=100.0, description="CPU utilization percentage (0-100)")
    memory_percent: float = Field(..., ge=0.0, le=100.0, description="Memory utilization percentage (0-100)")
    requests_per_minute: float = Field(..., ge=0.0, description="Requests per minute (>= 0)")
    latency_ms: float = Field(..., ge=0.0, description="Response latency in ms (>= 0)")
    instances: int = Field(..., gt=0, description="Currently running instances (> 0)")
    cost_per_hour: float = Field(..., ge=0.0, description="Current hourly cost for this service (>= 0)")
    min_instances: int = Field(..., gt=0, description="Minimum instance bound (> 0)")
    max_instances: int = Field(..., description="Maximum instance bound (>= min_instances)")
    max_latency_ms: float = Field(..., gt=0.0, description="Maximum allowable latency in ms (> 0)")
    healthy: bool = Field(default=True, description="Service health state")
    availability_percent: float = Field(default=99.99, ge=0.0, le=100.0, description="Availability percentage (0-100)")
    timestamp: str = Field(..., description="Observation timestamp in ISO-8601 format")

    # Optional fields
    previous_requests_per_minute: Optional[float] = Field(default=None, ge=0.0)
    error_rate_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    service_type: Optional[str] = Field(default="api", description="Service type: api, worker, batch, etc.")
    interruptible: Optional[bool] = Field(default=False, description="Whether workload is interruptible")
    current_size: Optional[str] = Field(default=None, description="Instance sizing or flavor")
    previous_action: Optional[str] = Field(default=None, description="Last action taken")
    expected_hourly_cost: Optional[float] = Field(default=None, ge=0.0)
    region: Optional[str] = Field(default="us-east-1")
    tags: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        parse_iso_datetime(v)
        return v

    @model_validator(mode="after")
    def validate_instance_bounds(self) -> "ServiceMetric":
        if self.max_instances < self.min_instances:
            raise ValueError(
                f"max_instances ({self.max_instances}) must be >= min_instances ({self.min_instances})"
            )
        if self.instances < self.min_instances or self.instances > self.max_instances:
            raise ValueError(
                f"instances ({self.instances}) must be between min_instances ({self.min_instances}) "
                f"and max_instances ({self.max_instances})"
            )
        return self


class TrafficObservation(BaseModel):
    """Latest external traffic sample for a service."""
    service_id: str = Field(..., min_length=1)
    requests_per_minute: float = Field(..., ge=0.0)
    timestamp: str = Field(..., description="ISO-8601 timestamp")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        parse_iso_datetime(v)
        return v


class EventObservation(BaseModel):
    """Historical or recent event in the cloud environment."""
    service_id: str = Field(..., min_length=1)
    event_type: str
    timestamp: str
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        parse_iso_datetime(v)
        return v


class EnvironmentConstraints(BaseModel):
    """Deterministic environment safety boundaries."""
    maximum_observation_age_seconds: int = Field(default=900, ge=10)
    maximum_scale_step: int = Field(default=2, ge=1)
    require_healthy_for_scale_down: bool = Field(default=True)
    require_fresh_metrics_for_action: bool = Field(default=True)
    latency_safety_margin_percent: float = Field(default=20.0, ge=0.0, le=100.0)
    minimum_availability_percent: float = Field(default=99.0, ge=0.0, le=100.0)
    max_action_retries: int = Field(default=1, ge=0)
    cooldown_seconds: int = Field(default=300, ge=0)


class OptimizationRequest(BaseModel):
    """Top-level input request for cloud cost optimization."""
    user_request: str = Field(..., min_length=1, description="Natural language operation request")
    services: List[ServiceMetric] = Field(..., min_length=1, description="List of monitored services")
    latest_traffic: List[TrafficObservation] = Field(default_factory=list)
    recent_events: List[EventObservation] = Field(default_factory=list)
    environment_constraints: EnvironmentConstraints = Field(default_factory=EnvironmentConstraints)
    requested_scenario: Optional[str] = Field(default=None, description="Optional preset scenario name")

    @field_validator("user_request")
    @classmethod
    def validate_user_request(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_request must be a non-empty string.")
        return v.strip()

    @field_validator("services")
    @classmethod
    def validate_unique_service_ids(cls, v: List[ServiceMetric]) -> List[ServiceMetric]:
        if not v:
            raise ValueError("services list must contain at least one service.")
        ids = [s.service_id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate service_id detected: {ids}")
        return v


# Output & Report Schemas

class ObservedProblem(BaseModel):
    """Detailed description of detected cloud problem."""
    type: ProblemType
    description: str
    affected_services: List[str] = Field(default_factory=list)


class ServiceObservation(BaseModel):
    """Sanitized observation summary for a single service."""
    service_id: str
    metrics: Dict[str, Any]
    observation_timestamp: str
    fresh: bool
    age_seconds: float
    findings: List[str] = Field(default_factory=list)


class CandidateAction(BaseModel):
    """A proposed optimization candidate."""
    service_id: str
    action: ActionType
    target_instances: int
    reason: str
    expected_hourly_savings: float = 0.0
    risk_level: str = "low"  # low, medium, high


class SelectedAction(BaseModel):
    """The action selected by reasoning engine for policy validation."""
    service_id: str
    action: ActionType
    previous_instances: int
    requested_instances: int
    reason: str
    expected_hourly_savings: Optional[float] = 0.0
    risk_level: Optional[str] = "low"


class PolicyCheckResult(BaseModel):
    """Result of an individual safety policy rule."""
    check: str
    passed: bool
    message: str


class ExecutionResult(BaseModel):
    """Status of cloud tool execution."""
    attempted: bool = False
    action_id: Optional[str] = None
    status: ActionStatus = ActionStatus.SKIPPED
    error: Optional[str] = None
    retries: int = 0


class VerificationCheckItem(BaseModel):
    """Single verification check status."""
    passed: bool
    message: str


class VerificationResult(BaseModel):
    """Post-action verification summary."""
    performed: bool = False
    success: bool = False
    checks: Dict[str, VerificationCheckItem] = Field(default_factory=dict)
    estimated_hourly_cost_before: float = 0.0
    estimated_hourly_cost_after: float = 0.0
    estimated_hourly_savings: float = 0.0


class AuditEntry(BaseModel):
    """Step-by-step audit record."""
    step: str
    timestamp: str
    details: str


class OptimizationReport(BaseModel):
    """Comprehensive, downloadable output report."""
    report_id: str
    created_at: str
    user_request: str
    status: ReportStatus
    intent: IntentType
    summary: str
    observed_problem: ObservedProblem
    observations: List[ServiceObservation]
    candidate_actions: List[CandidateAction]
    selected_action: Optional[SelectedAction] = None
    policy_checks: List[PolicyCheckResult] = Field(default_factory=list)
    execution: ExecutionResult = Field(default_factory=ExecutionResult)
    verification: VerificationResult = Field(default_factory=VerificationResult)
    final_decision: FinalDecision
    recommendations: List[str] = Field(default_factory=list)
    audit_trail: List[AuditEntry] = Field(default_factory=list)
    download_url: Optional[str] = None
