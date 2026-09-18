"""Observation and action tool layer simulating cloud API endpoints."""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from backend.models import ToolResult, ActionType
from backend.simulator import simulator


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_services() -> ToolResult:
    """Retrieve all monitored cloud services."""
    services = simulator.list_services()
    return ToolResult(
        success=True,
        data={"services": services, "count": len(services)},
        timestamp=_now_iso(),
        source="simulated-cloud-api",
        error=None,
    )


def get_service_metrics(service_id: str) -> ToolResult:
    """Fetch current metric snapshot for a given service."""
    srv = simulator.get_service(service_id)
    if not srv:
        return ToolResult(
            success=False,
            data={},
            timestamp=_now_iso(),
            source="simulated-cloud-api",
            error=f"Service '{service_id}' not found",
        )
    return ToolResult(
        success=True,
        data={"service_id": service_id, "metrics": srv},
        timestamp=_now_iso(),
        source="simulated-cloud-api",
        error=None,
    )


def get_latest_traffic(service_id: str, external_traffic: Optional[List[Dict[str, Any]]] = None) -> ToolResult:
    """Retrieve the newest traffic sample for a given service."""
    if external_traffic:
        for t in external_traffic:
            if t.get("service_id") == service_id:
                return ToolResult(
                    success=True,
                    data={"service_id": service_id, "traffic": t},
                    timestamp=t.get("timestamp", _now_iso()),
                    source="traffic-telemetry",
                    error=None,
                )

    srv = simulator.get_service(service_id)
    if not srv:
        return ToolResult(
            success=False,
            data={},
            timestamp=_now_iso(),
            source="traffic-telemetry",
            error=f"Service '{service_id}' not found",
        )

    return ToolResult(
        success=True,
        data={
            "service_id": service_id,
            "requests_per_minute": srv.get("requests_per_minute", 0),
            "timestamp": srv.get("timestamp", _now_iso()),
        },
        timestamp=_now_iso(),
        source="traffic-telemetry",
        error=None,
    )


def get_recent_events(service_id: str, external_events: Optional[List[Dict[str, Any]]] = None) -> ToolResult:
    """Retrieve recent infrastructure events for a service."""
    matching_events = []
    if external_events:
        matching_events = [e for e in external_events if e.get("service_id") == service_id]

    return ToolResult(
        success=True,
        data={"service_id": service_id, "events": matching_events},
        timestamp=_now_iso(),
        source="event-stream",
        error=None,
    )


def get_pricing(service_id: str) -> ToolResult:
    """Retrieve current unit pricing for a service."""
    pricing = simulator.get_pricing(service_id)
    if not pricing:
        return ToolResult(
            success=False,
            data={},
            timestamp=_now_iso(),
            source="pricing-api",
            error=f"Service '{service_id}' not found for pricing lookup",
        )
    return ToolResult(
        success=True,
        data=pricing,
        timestamp=_now_iso(),
        source="pricing-api",
        error=None,
    )


def get_environment_health() -> ToolResult:
    """Check overall environment health and capacity status."""
    health_data = simulator.get_environment_health()
    return ToolResult(
        success=True,
        data=health_data,
        timestamp=_now_iso(),
        source="simulated-cloud-api",
        error=None,
    )


def execute_scale_up(service_id: str, target_instances: int, action_id: Optional[str] = None) -> ToolResult:
    """Execute scale-up action against the cloud simulator."""
    res = simulator.execute_action(
        action=ActionType.SCALE_UP,
        service_id=service_id,
        target_instances=target_instances,
        action_id=action_id,
    )
    return ToolResult(
        success=res.get("status") == "succeeded",
        data=res,
        timestamp=_now_iso(),
        source="simulated-cloud-api",
        error=res.get("error"),
    )


def execute_scale_down(service_id: str, target_instances: int, action_id: Optional[str] = None) -> ToolResult:
    """Execute scale-down action against the cloud simulator."""
    res = simulator.execute_action(
        action=ActionType.SCALE_DOWN,
        service_id=service_id,
        target_instances=target_instances,
        action_id=action_id,
    )
    return ToolResult(
        success=res.get("status") == "succeeded",
        data=res,
        timestamp=_now_iso(),
        source="simulated-cloud-api",
        error=res.get("error"),
    )


def execute_stop_idle_service(service_id: str, action_id: Optional[str] = None) -> ToolResult:
    """Execute stop action for idle service."""
    res = simulator.execute_action(
        action=ActionType.STOP_IDLE_SERVICE,
        service_id=service_id,
        target_instances=0,
        action_id=action_id,
    )
    return ToolResult(
        success=res.get("status") == "succeeded",
        data=res,
        timestamp=_now_iso(),
        source="simulated-cloud-api",
        error=res.get("error"),
    )


def get_action_status(action_id: str) -> ToolResult:
    """Lookup the status of a previously executed action."""
    status_data = simulator.get_action_status(action_id)
    if not status_data:
        return ToolResult(
            success=False,
            data={},
            timestamp=_now_iso(),
            source="simulated-cloud-api",
            error=f"Action '{action_id}' not found",
        )
    return ToolResult(
        success=True,
        data=status_data,
        timestamp=_now_iso(),
        source="simulated-cloud-api",
        error=status_data.get("error"),
    )


def get_fresh_metrics(service_id: str) -> ToolResult:
    """Fetch fresh post-action metrics directly from the cloud environment."""
    srv = simulator.get_service(service_id)
    if not srv:
        return ToolResult(
            success=False,
            data={},
            timestamp=_now_iso(),
            source="simulated-cloud-api",
            error=f"Service '{service_id}' not found",
        )
    return ToolResult(
        success=True,
        data={"service_id": service_id, "fresh_metrics": dict(srv)},
        timestamp=_now_iso(),
        source="simulated-cloud-api",
        error=None,
    )
