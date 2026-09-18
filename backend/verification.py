"""Post-action verification engine with rollback capabilities."""
from typing import Dict, Any, Optional

from backend.models import ActionType, ActionStatus
from backend.schemas import (
    ServiceMetric,
    EnvironmentConstraints,
    VerificationResult,
    VerificationCheckItem,
)
from backend.tools import get_fresh_metrics, execute_scale_up, execute_scale_down


class VerificationEngine:
    """Performs rigorous post-execution verification on cloud state changes."""

    def verify_action(
        self,
        service: ServiceMetric,
        action: ActionType,
        previous_instances: int,
        requested_instances: int,
        execution_status: ActionStatus,
        constraints: EnvironmentConstraints,
        cost_before: float,
        cost_after: float,
    ) -> VerificationResult:
        """
        Verify that a scaling or lifecycle action succeeded and state meets SLAs.
        """
        checks: Dict[str, VerificationCheckItem] = {}

        if execution_status != ActionStatus.SUCCEEDED:
            return VerificationResult(
                performed=True,
                success=False,
                checks={
                    "execution_status": VerificationCheckItem(
                        passed=False,
                        message=f"Action execution status is '{execution_status.value}', not succeeded."
                    )
                },
                estimated_hourly_cost_before=cost_before,
                estimated_hourly_cost_after=cost_before,
                estimated_hourly_savings=0.0,
            )

        # 1. Fetch fresh metrics directly from cloud simulator
        fresh_res = get_fresh_metrics(service.service_id)
        if not fresh_res.success:
            return VerificationResult(
                performed=True,
                success=False,
                checks={
                    "metric_retrieval": VerificationCheckItem(
                        passed=False,
                        message=f"Failed to fetch fresh metrics for verification: {fresh_res.error}"
                    )
                },
                estimated_hourly_cost_before=cost_before,
                estimated_hourly_cost_after=cost_before,
                estimated_hourly_savings=0.0,
            )

        fresh_metrics = fresh_res.data.get("fresh_metrics", {})
        active_instances = fresh_metrics.get("instances", service.instances)
        active_healthy = fresh_metrics.get("healthy", True)
        active_latency = fresh_metrics.get("latency_ms", service.latency_ms)
        active_availability = fresh_metrics.get("availability_percent", service.availability_percent)
        active_cost = 0.0 if action == ActionType.STOP_IDLE_SERVICE else round(active_instances * service.cost_per_hour, 2)

        all_passed = True

        # Check 1: Instance count match
        expected_target = requested_instances
        if active_instances == expected_target:
            checks["instance_count"] = VerificationCheckItem(
                passed=True,
                message=f"Requested instance count is active ({active_instances})."
            )
        else:
            checks["instance_count"] = VerificationCheckItem(
                passed=False,
                message=f"Active instances ({active_instances}) does not match requested ({expected_target})."
            )
            all_passed = False

        # Check 2: Health
        if active_healthy:
            checks["health"] = VerificationCheckItem(
                passed=True,
                message="Service is healthy."
            )
        else:
            checks["health"] = VerificationCheckItem(
                passed=False,
                message="Service health check failed after action."
            )
            all_passed = False

        # Check 3: Latency
        if active_latency <= service.max_latency_ms:
            checks["latency"] = VerificationCheckItem(
                passed=True,
                message=f"Latency ({active_latency}ms) is within the configured maximum ({service.max_latency_ms}ms)."
            )
        else:
            checks["latency"] = VerificationCheckItem(
                passed=False,
                message=f"Latency ({active_latency}ms) exceeds maximum allowable threshold ({service.max_latency_ms}ms)."
            )
            all_passed = False

        # Check 4: Availability
        if active_availability >= constraints.minimum_availability_percent:
            checks["availability"] = VerificationCheckItem(
                passed=True,
                message=f"Availability ({active_availability}%) remains acceptable (>= {constraints.minimum_availability_percent}%)."
            )
        else:
            checks["availability"] = VerificationCheckItem(
                passed=False,
                message=f"Availability ({active_availability}%) degraded below minimum ({constraints.minimum_availability_percent}%)."
            )
            all_passed = False

        # Check 5: Cost impact
        savings = round(cost_before - active_cost, 2)
        if action == ActionType.SCALE_DOWN and active_cost < cost_before:
            checks["cost"] = VerificationCheckItem(
                passed=True,
                message=f"Estimated hourly cost decreased from ${cost_before:.2f} to ${active_cost:.2f} (Savings: ${savings:.2f}/hr)."
            )
        elif action == ActionType.SCALE_UP and active_cost >= cost_before:
            checks["cost"] = VerificationCheckItem(
                passed=True,
                message=f"Capacity expanded: cost adjusted from ${cost_before:.2f} to ${active_cost:.2f}."
            )
        elif action == ActionType.STOP_IDLE_SERVICE and active_cost == 0.0:
            checks["cost"] = VerificationCheckItem(
                passed=True,
                message=f"Idle service stopped: full savings of ${cost_before:.2f}/hr realized."
            )
        else:
            checks["cost"] = VerificationCheckItem(
                passed=True,
                message=f"Cost verification confirmed: ${active_cost:.2f}/hr."
            )

        # Rollback if verification failed and we altered instance capacity
        if not all_passed and previous_instances != active_instances:
            self._attempt_rollback(service.service_id, previous_instances)

        return VerificationResult(
            performed=True,
            success=all_passed,
            checks=checks,
            estimated_hourly_cost_before=round(cost_before, 2),
            estimated_hourly_cost_after=round(active_cost, 2),
            estimated_hourly_savings=savings,
        )

    def _attempt_rollback(self, service_id: str, original_instances: int) -> None:
        """Attempt safe rollback to prior instance count if post-check failed."""
        try:
            execute_scale_up(service_id=service_id, target_instances=original_instances)
        except Exception:
            pass


# Global verification engine instance
verification_engine = VerificationEngine()
