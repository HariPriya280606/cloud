"""Deterministic Safety Policy Engine enforcing strict infrastructure guardrails."""
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

from backend.models import ActionType
from backend.schemas import (
    ServiceMetric,
    TrafficObservation,
    EventObservation,
    EnvironmentConstraints,
    PolicyCheckResult,
    parse_iso_datetime,
)


class PolicyEngine:
    """Evaluates proposed actions against deterministic safety boundaries."""

    def __init__(self):
        self._action_history: List[Dict[str, Any]] = []

    def reset(self) -> None:
        """Clear action history."""
        self._action_history = []

    def record_action(self, service_id: str, action: str, timestamp: str) -> None:
        """Record executed action timestamp for cooldown tracking."""
        self._action_history.append({
            "service_id": service_id,
            "action": action,
            "timestamp": timestamp,
        })

    def validate_action(
        self,
        service: ServiceMetric,
        action: ActionType,
        target_instances: int,
        constraints: EnvironmentConstraints,
        latest_traffic: Optional[List[TrafficObservation]] = None,
        recent_events: Optional[List[EventObservation]] = None,
        reference_timestamp: Optional[datetime] = None,
    ) -> Tuple[bool, List[PolicyCheckResult], int]:
        """
        Validate proposed action against all deterministic safety policies.
        Returns:
            (is_approved, list_of_policy_checks, adjusted_target_instances)
        """
        checks: List[PolicyCheckResult] = []
        is_approved = True
        adjusted_target = target_instances

        # 1. Freshness Check (Metric age and Traffic-Metric inconsistency)
        freshness_passed, freshness_msg = self._check_freshness(
            service=service,
            constraints=constraints,
            latest_traffic=latest_traffic,
            reference_timestamp=reference_timestamp,
        )
        checks.append(PolicyCheckResult(
            check="observation_freshness",
            passed=freshness_passed,
            message=freshness_msg,
        ))
        if not freshness_passed:
            is_approved = False

        # If action is NO_ACTION or ESCALATE, we don't need scaling policy checks
        if action in (ActionType.NO_ACTION, ActionType.ESCALATE):
            return is_approved, checks, adjusted_target

        # 2. Instance Bounds Check
        bounds_passed, bounds_msg, capped_by_bounds = self._check_instance_bounds(
            service=service,
            action=action,
            target_instances=target_instances,
        )
        checks.append(PolicyCheckResult(
            check="instance_bounds",
            passed=bounds_passed,
            message=bounds_msg,
        ))
        if not bounds_passed:
            is_approved = False
        else:
            adjusted_target = capped_by_bounds

        # 3. Maximum Change Step Size (Cap or reject)
        step_passed, step_msg, step_adjusted = self._check_max_step(
            service=service,
            action=action,
            target_instances=adjusted_target,
            max_step=constraints.maximum_scale_step,
        )
        checks.append(PolicyCheckResult(
            check="maximum_scale_step",
            passed=step_passed,
            message=step_msg,
        ))
        if not step_passed:
            is_approved = False
        else:
            adjusted_target = step_adjusted

        # 4. Health Check
        health_passed, health_msg = self._check_health(
            service=service,
            action=action,
            require_healthy=constraints.require_healthy_for_scale_down,
        )
        checks.append(PolicyCheckResult(
            check="health",
            passed=health_passed,
            message=health_msg,
        ))
        if not health_passed:
            is_approved = False

        # 5. Latency Safety Margin Check
        latency_passed, latency_msg = self._check_latency(
            service=service,
            action=action,
            safety_margin_percent=constraints.latency_safety_margin_percent,
        )
        checks.append(PolicyCheckResult(
            check="latency_safety_margin",
            passed=latency_passed,
            message=latency_msg,
        ))
        if not latency_passed:
            is_approved = False

        # 6. Availability Check
        avail_passed, avail_msg = self._check_availability(
            service=service,
            action=action,
            min_avail_percent=constraints.minimum_availability_percent,
        )
        checks.append(PolicyCheckResult(
            check="availability_requirement",
            passed=avail_passed,
            message=avail_msg,
        ))
        if not avail_passed:
            is_approved = False

        # 7. Traffic Surge Check
        traffic_passed, traffic_msg = self._check_traffic_trend(
            service=service,
            action=action,
            latest_traffic=latest_traffic,
        )
        checks.append(PolicyCheckResult(
            check="traffic_stability",
            passed=traffic_passed,
            message=traffic_msg,
        ))
        if not traffic_passed:
            is_approved = False

        # 8. Cooldown Check
        cooldown_passed, cooldown_msg = self._check_cooldown(
            service=service,
            cooldown_seconds=constraints.cooldown_seconds,
            reference_timestamp=reference_timestamp,
        )
        checks.append(PolicyCheckResult(
            check="cooldown_period",
            passed=cooldown_passed,
            message=cooldown_msg,
        ))
        if not cooldown_passed:
            is_approved = False

        return is_approved, checks, adjusted_target

    def _check_freshness(
        self,
        service: ServiceMetric,
        constraints: EnvironmentConstraints,
        latest_traffic: Optional[List[TrafficObservation]],
        reference_timestamp: Optional[datetime],
    ) -> Tuple[bool, str]:
        """Validate observation age and detect conflicts with newer external traffic."""
        try:
            srv_time = parse_iso_datetime(service.timestamp)
        except Exception as e:
            return False, f"Invalid service metric timestamp '{service.timestamp}': {e}"

        ref_time = reference_timestamp or datetime.now(srv_time.tzinfo or None)

        # Check age
        age_seconds = (ref_time - srv_time).total_seconds()
        if age_seconds > constraints.maximum_observation_age_seconds:
            return (
                False,
                f"Observation is stale: age {age_seconds:.0f}s exceeds max allowed "
                f"{constraints.maximum_observation_age_seconds}s (metric: {service.timestamp}, ref: {ref_time.isoformat()}).",
            )

        # Check traffic timestamp conflict
        if latest_traffic:
            for traf in latest_traffic:
                if traf.service_id == service.service_id:
                    try:
                        traf_time = parse_iso_datetime(traf.timestamp)
                        time_diff = (traf_time - srv_time).total_seconds()
                        if time_diff > constraints.maximum_observation_age_seconds:
                            return (
                                False,
                                f"Inconsistent observations: service metric is from {service.timestamp} ({service.requests_per_minute} rpm) "
                                f"but latest telemetry is from {traf.timestamp} ({traf.requests_per_minute} rpm).",
                            )
                        # If traffic surged dramatically in recent telemetry while metric is older
                        if traf.requests_per_minute > service.requests_per_minute * 2 and time_diff > 60:
                            return (
                                False,
                                f"Stale metric conflict: metric reports {service.requests_per_minute} rpm but newer telemetry reports {traf.requests_per_minute} rpm.",
                            )
                    except Exception as e:
                        return False, f"Invalid traffic timestamp '{traf.timestamp}': {e}"

        return True, f"Observation is fresh (age: {max(0, age_seconds):.0f}s <= {constraints.maximum_observation_age_seconds}s)."

    def _check_instance_bounds(
        self,
        service: ServiceMetric,
        action: ActionType,
        target_instances: int,
    ) -> Tuple[bool, str, int]:
        """Validate target instances within min_instances and max_instances."""
        if action == ActionType.STOP_IDLE_SERVICE:
            if service.interruptible or service.service_type == "worker":
                return True, "Stop idle workload permitted for interruptible/worker service.", 0
            return False, "stop_idle_service rejected: service is not marked as interruptible or worker.", service.instances

        if target_instances < service.min_instances:
            return (
                False,
                f"Target instances ({target_instances}) violates minimum instance limit ({service.min_instances}).",
                service.min_instances,
            )

        if target_instances > service.max_instances:
            return (
                False,
                f"Target instances ({target_instances}) exceeds maximum instance limit ({service.max_instances}).",
                service.max_instances,
            )

        return True, f"Target instances ({target_instances}) is within safe bounds [{service.min_instances}, {service.max_instances}].", target_instances

    def _check_max_step(
        self,
        service: ServiceMetric,
        action: ActionType,
        target_instances: int,
        max_step: int,
    ) -> Tuple[bool, str, int]:
        """Cap or enforce the maximum instance step change."""
        current = service.instances
        delta = abs(target_instances - current)

        if delta > max_step:
            if action == ActionType.SCALE_DOWN:
                capped = max(service.min_instances, current - max_step)
                return True, f"Scale-down request ({current} -> {target_instances}) capped to safe step: {current} -> {capped}.", capped
            elif action == ActionType.SCALE_UP:
                capped = min(service.max_instances, current + max_step)
                return True, f"Scale-up request ({current} -> {target_instances}) capped to safe step: {current} -> {capped}.", capped

        return True, f"Instance delta ({delta}) is within maximum scale step ({max_step}).", target_instances

    def _check_health(
        self,
        service: ServiceMetric,
        action: ActionType,
        require_healthy: bool,
    ) -> Tuple[bool, str]:
        """Ensure unhealthy services are not scaled down or stopped."""
        if action in (ActionType.SCALE_DOWN, ActionType.STOP_IDLE_SERVICE):
            if require_healthy and not service.healthy:
                return False, f"Cannot scale down unhealthy service '{service.service_id}'."

        return True, f"Service '{service.service_id}' health state ({'healthy' if service.healthy else 'unhealthy'}) permits proposed action."

    def _check_latency(
        self,
        service: ServiceMetric,
        action: ActionType,
        safety_margin_percent: float,
    ) -> Tuple[bool, str]:
        """Ensure latency margin is preserved during scale down."""
        if action == ActionType.SCALE_DOWN:
            threshold = service.max_latency_ms * (1.0 - (safety_margin_percent / 100.0))
            if service.latency_ms > threshold:
                return (
                    False,
                    f"Latency ({service.latency_ms}ms) is too close to max ({service.max_latency_ms}ms). "
                    f"Scale-down safety threshold is {threshold:.1f}ms (safety margin: {safety_margin_percent}%).",
                )

        return True, f"Latency ({service.latency_ms}ms) is within safe limits (max: {service.max_latency_ms}ms)."

    def _check_availability(
        self,
        service: ServiceMetric,
        action: ActionType,
        min_avail_percent: float,
    ) -> Tuple[bool, str]:
        """Ensure availability meets the minimum requirement."""
        if action == ActionType.SCALE_DOWN:
            if service.availability_percent < min_avail_percent:
                return (
                    False,
                    f"Availability ({service.availability_percent}%) is below minimum requirement ({min_avail_percent}%).",
                )

        return True, f"Availability ({service.availability_percent}%) meets SLA requirement ({min_avail_percent}%)."

    def _check_traffic_trend(
        self,
        service: ServiceMetric,
        action: ActionType,
        latest_traffic: Optional[List[TrafficObservation]],
    ) -> Tuple[bool, str]:
        """Detect rapid traffic growth to prevent dangerous scale-downs."""
        if action == ActionType.SCALE_DOWN:
            # Check previous_requests_per_minute
            if service.previous_requests_per_minute is not None and service.previous_requests_per_minute > 0:
                growth = ((service.requests_per_minute - service.previous_requests_per_minute) / service.previous_requests_per_minute) * 100.0
                if growth >= 50.0:
                    return False, f"Cannot scale down: rapid traffic growth detected (+{growth:.1f}%)."

            # Check latest_traffic
            if latest_traffic:
                for traf in latest_traffic:
                    if traf.service_id == service.service_id and service.requests_per_minute > 0:
                        growth = ((traf.requests_per_minute - service.requests_per_minute) / service.requests_per_minute) * 100.0
                        if growth >= 50.0:
                            return False, f"Cannot scale down: telemetry shows rapid traffic surge (+{growth:.1f}%)."

        return True, "Traffic trend permits proposed action."

    def _check_cooldown(
        self,
        service: ServiceMetric,
        cooldown_seconds: int,
        reference_timestamp: Optional[datetime],
    ) -> Tuple[bool, str]:
        """Check if service is in cooldown from a recent scaling action."""
        if cooldown_seconds <= 0:
            return True, "Cooldown check bypassed (cooldown=0)."

        now_dt = reference_timestamp or datetime.now()
        for act in reversed(self._action_history):
            if act.get("service_id") == service.service_id:
                try:
                    act_dt = parse_iso_datetime(act.get("timestamp"))
                    diff = (now_dt - act_dt).total_seconds()
                    if 0 <= diff < cooldown_seconds:
                        # Allow bypass only if critical constraint violation
                        if service.latency_ms > service.max_latency_ms or not service.healthy or service.cpu_percent >= 90.0:
                            return True, f"Cooldown bypassed due to critical performance threshold breach."
                        return False, f"Service is in cooldown period ({diff:.0f}s < {cooldown_seconds}s)."
                except Exception:
                    pass

        return True, "Cooldown requirements satisfied."


# Global policy engine instance
policy_engine = PolicyEngine()
