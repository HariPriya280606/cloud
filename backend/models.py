"""Domain data models and enums for Cloud Cost Optimization Agent."""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Supported user request intent classifications."""
    COST_OPTIMIZATION = "cost_optimization"
    SCALE_FOR_TRAFFIC = "scale_for_traffic"
    PROTECT_LATENCY = "protect_latency"
    CONDITIONAL_SCALING = "conditional_scaling"
    INVESTIGATE_ONLY = "investigate_only"


class ActionType(str, Enum):
    """Supported agent actions."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    STOP_IDLE_SERVICE = "stop_idle_service"
    RESIZE = "resize"
    DELAY_BATCH_WORKLOAD = "delay_batch_workload"
    NO_ACTION = "no_action"
    ESCALATE = "escalate"


class ActionStatus(str, Enum):
    """Execution status of an action."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NOT_SUPPORTED = "not_supported"
    SKIPPED = "skipped"


class ReportStatus(str, Enum):
    """Overall status of an optimization run."""
    COMPLETED = "completed"
    NO_ACTION = "no_action"
    BLOCKED = "blocked"
    FAILED = "failed"
    REQUIRES_ATTENTION = "requires_attention"


class FinalDecision(str, Enum):
    """Final conclusion/action category."""
    ACTION_TAKEN = "action_taken"
    NO_SAFE_ACTION = "no_safe_action"
    STALE_DATA = "stale_data"
    ACTION_FAILED = "action_failed"
    ESCALATED = "escalated"
    INVESTIGATION_ONLY = "investigation_only"


class ProblemType(str, Enum):
    """Classification of detected infrastructure issue."""
    COST_WASTE = "cost_waste"
    CAPACITY_RISK = "capacity_risk"
    TRAFFIC_GROWTH = "traffic_growth"
    LATENCY_RISK = "latency_risk"
    STALE_OBSERVATIONS = "stale_observations"
    ACTION_FAILURE = "action_failure"
    NO_ISSUE = "no_issue"


class ToolResult(BaseModel):
    """Uniform return format for observation and action tools."""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str
    source: str = "simulated-cloud-api"
    error: Optional[str] = None
