"""In-memory Cloud API Simulator with controlled failure modes and dynamic metrics."""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid

from backend.models import ActionType, ActionStatus
from backend.schemas import ServiceMetric


class CloudSimulator:
    """Simulates cloud provider API operations, state changes, and error injection."""

    def __init__(self):
        self._services: Dict[str, Dict[str, Any]] = {}
        self._action_history: List[Dict[str, Any]] = []
        self._failure_mode: Optional[str] = None
        self._failure_target_service: Optional[str] = None
        self._preset_action_id: Optional[str] = None
        self.reset()

    def reset(self) -> None:
        """Reset simulator to clean state."""
        self._services = {}
        self._action_history = []
        self._failure_mode = None
        self._failure_target_service = None
        self._preset_action_id = None

    def inject_failure(
        self,
        mode: str,
        service_id: Optional[str] = None,
        preset_action_id: Optional[str] = None
    ) -> None:
        """Configure a controlled failure mode for testing."""
        self._failure_mode = mode
        self._failure_target_service = service_id
        self._preset_action_id = preset_action_id

    def load_services(self, services: List[ServiceMetric]) -> None:
        """Load service metrics into simulated environment."""
        self._services = {s.service_id: s.model_dump() for s in services}

    def list_services(self) -> List[Dict[str, Any]]:
        """List all active simulated services."""
        return list(self._services.values())

    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Fetch raw state for a specific service."""
        return self._services.get(service_id)

    def get_environment_health(self) -> Dict[str, Any]:
        """Aggregate health status of the simulated cloud environment."""
        total = len(self._services)
        healthy = sum(1 for s in self._services.values() if s.get("healthy", True))
        return {
            "total_services": total,
            "healthy_services": healthy,
            "all_healthy": healthy == total if total > 0 else True,
            "status": "HEALTHY" if healthy == total else "DEGRADED",
            "region": "us-east-1",
        }

    def get_pricing(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve unit pricing for a service."""
        srv = self.get_service(service_id)
        if not srv:
            return None
        instances = srv.get("instances", 1)
        total_cost = srv.get("cost_per_hour", 0.0)
        unit_cost = (total_cost / instances) if instances > 0 else total_cost
        return {
            "service_id": service_id,
            "cost_per_instance_hour": round(unit_cost, 4),
            "current_hourly_cost": total_cost,
            "current_instances": instances,
            "currency": "USD",
        }

    def execute_action(
        self,
        action: ActionType,
        service_id: str,
        target_instances: int,
        action_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a simulated scaling or lifecycle action."""
        now_iso = datetime.now(timezone.utc).isoformat()
        act_id = action_id or self._preset_action_id or f"act-{uuid.uuid4().hex[:6]}"

        # Check for injected failure mode
        if self._failure_mode:
            if not self._failure_target_service or self._failure_target_service == service_id:
                err_mode = self._failure_mode
                result = {
                    "action_id": act_id,
                    "action": action.value,
                    "service_id": service_id,
                    "requested_instances": target_instances,
                    "status": ActionStatus.FAILED.value,
                    "error": err_mode,
                    "timestamp": now_iso,
                    "retries": 0,
                }
                self._action_history.append(result)
                return result

        srv = self.get_service(service_id)
        if not srv:
            result = {
                "action_id": act_id,
                "action": action.value,
                "service_id": service_id,
                "requested_instances": target_instances,
                "status": ActionStatus.FAILED.value,
                "error": "invalid_target",
                "timestamp": now_iso,
                "retries": 0,
            }
            self._action_history.append(result)
            return result

        current_instances = srv.get("instances", 1)
        unit_cost = srv.get("cost_per_hour", 0.0)

        if action == ActionType.SCALE_UP:
            srv["instances"] = target_instances
            # Simulated effect: slightly lower CPU and latency
            srv["cpu_percent"] = max(5.0, round(srv["cpu_percent"] * (current_instances / target_instances), 1))
            srv["latency_ms"] = max(10.0, round(srv["latency_ms"] * (current_instances / target_instances) * 0.9, 1))
            srv["healthy"] = True
            srv["timestamp"] = now_iso

        elif action == ActionType.SCALE_DOWN:
            srv["instances"] = target_instances
            # Simulated effect: slightly higher CPU/latency if traffic exists, but stay safe
            if srv.get("requests_per_minute", 0) > 0:
                srv["cpu_percent"] = min(95.0, round(srv["cpu_percent"] * (current_instances / target_instances), 1))
                srv["latency_ms"] = min(srv["max_latency_ms"] * 0.8, round(srv["latency_ms"] * 1.1, 1))
            srv["healthy"] = True
            srv["timestamp"] = now_iso

        elif action == ActionType.STOP_IDLE_SERVICE:
            srv["instances"] = 0
            srv["cost_per_hour"] = 0.0
            srv["healthy"] = True
            srv["timestamp"] = now_iso

        else:
            return {
                "action_id": act_id,
                "action": action.value,
                "service_id": service_id,
                "requested_instances": target_instances,
                "status": ActionStatus.NOT_SUPPORTED.value,
                "error": f"Action {action.value} is not supported by simulator",
                "timestamp": now_iso,
                "retries": 0,
            }

        result = {
            "action_id": act_id,
            "action": action.value,
            "service_id": service_id,
            "previous_instances": current_instances,
            "requested_instances": target_instances,
            "active_instances": srv["instances"],
            "new_cost_per_hour": srv["cost_per_hour"],
            "status": ActionStatus.SUCCEEDED.value,
            "error": None,
            "timestamp": now_iso,
            "retries": 0,
        }
        self._action_history.append(result)
        return result

    def get_action_status(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Find an action in the history by action_id."""
        for act in reversed(self._action_history):
            if act.get("action_id") == action_id:
                return act
        return None

    def get_action_history(self) -> List[Dict[str, Any]]:
        """Return complete list of executed actions."""
        return list(self._action_history)


# Global simulator instance
simulator = CloudSimulator()
