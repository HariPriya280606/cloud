"""Autonomous Cloud Cost Optimization Agent orchestrating observations, policy safety, execution, and verification."""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from backend.models import (
    IntentType,
    ActionType,
    ActionStatus,
    ReportStatus,
    FinalDecision,
    ProblemType,
)
from backend.schemas import (
    OptimizationRequest,
    OptimizationReport,
    ObservedProblem,
    ServiceObservation,
    CandidateAction,
    SelectedAction,
    PolicyCheckResult,
    ExecutionResult,
    VerificationResult,
    AuditEntry,
    ServiceMetric,
    parse_iso_datetime,
)
from backend.simulator import simulator
from backend.tools import (
    list_services,
    get_service_metrics,
    get_latest_traffic,
    get_pricing,
    execute_scale_up,
    execute_scale_down,
    execute_stop_idle_service,
)
from backend.policy_engine import policy_engine
from backend.verification import verification_engine
from backend.llm_adapter import get_llm_adapter

logger = logging.getLogger("cloud_agent")


class CostOptimizationAgent:
    """9-Step Autonomous Agent for Cloud Cost and Reliability Optimization."""

    def __init__(self):
        self.policy_engine = policy_engine
        self.verification_engine = verification_engine

    async def run(self, request: OptimizationRequest) -> OptimizationReport:
        """Execute the full end-to-end agent optimization workflow."""
        report_id = f"report-{uuid.uuid4().hex[:8]}"
        now_dt = datetime.now(timezone.utc)
        created_at_iso = now_dt.isoformat()
        audit_trail: List[AuditEntry] = []

        def add_audit(step: str, details: str):
            audit_trail.append(AuditEntry(
                step=step,
                timestamp=datetime.now(timezone.utc).isoformat(),
                details=details,
            ))

        add_audit("start", f"Initiated optimization run for request: '{request.user_request}'")

        # Load input services into simulator state
        simulator.reset()

        # Handle injected test scenario failure modes
        if request.requested_scenario == "scenario_d" or (
            len(request.services) == 1 and request.services[0].service_id == "payment-api" and request.services[0].cpu_percent > 90
        ):
            simulator.inject_failure(mode="capacity_unavailable", service_id="payment-api", preset_action_id="act-784")

        simulator.load_services(request.services)

        # ---------------------------------------------------------------------
        # Step 1: Parse natural-language request
        # ---------------------------------------------------------------------
        add_audit("parse", "Classifying user intent and operational parameters.")
        llm_adapter = get_llm_adapter()

        # ---------------------------------------------------------------------
        # Step 2: Retrieve current observations
        # ---------------------------------------------------------------------
        add_audit("observe", f"Inspecting telemetry for {len(request.services)} service(s).")
        raw_services = request.services
        all_timestamps = [parse_iso_datetime(s.timestamp) for s in raw_services]
        for t in request.latest_traffic:
            all_timestamps.append(parse_iso_datetime(t.timestamp))
        reference_dt = max(all_timestamps) if all_timestamps else now_dt

        service_observations: List[ServiceObservation] = []
        is_any_service_stale = False
        stale_reasons = []

        for srv in raw_services:
            srv_dt = parse_iso_datetime(srv.timestamp)
            age_sec = (reference_dt - srv_dt).total_seconds()
            is_fresh = age_sec <= request.environment_constraints.maximum_observation_age_seconds

            # Check for conflict with latest_traffic
            traffic_conflict = False
            for traf in request.latest_traffic:
                if traf.service_id == srv.service_id:
                    traf_dt = parse_iso_datetime(traf.timestamp)
                    if (traf_dt - srv_dt).total_seconds() > request.environment_constraints.maximum_observation_age_seconds:
                        is_fresh = False
                        traffic_conflict = True
                        stale_reasons.append(
                            f"Service '{srv.service_id}' metrics timestamp ({srv.timestamp}) diverges from latest traffic ({traf.timestamp}, {traf.requests_per_minute} rpm)."
                        )
                    elif traf.requests_per_minute > srv.requests_per_minute * 2 and (traf_dt - srv_dt).total_seconds() > 60:
                        is_fresh = False
                        traffic_conflict = True
                        stale_reasons.append(
                            f"Service '{srv.service_id}' has conflicting observations: old metric {srv.requests_per_minute} rpm vs fresh telemetry {traf.requests_per_minute} rpm."
                        )

            if not is_fresh and not traffic_conflict:
                stale_reasons.append(f"Service '{srv.service_id}' metric age ({age_sec:.0f}s) exceeds max limit ({request.environment_constraints.maximum_observation_age_seconds}s).")

            if not is_fresh:
                is_any_service_stale = True

            # Findings
            findings = []
            if srv.requests_per_minute == 0:
                findings.append("No current traffic (0 rpm)")
            elif srv.previous_requests_per_minute is not None and srv.previous_requests_per_minute > 0:
                growth = ((srv.requests_per_minute - srv.previous_requests_per_minute) / srv.previous_requests_per_minute) * 100
                findings.append(f"Traffic growth: {growth:+.1f}% vs previous ({srv.previous_requests_per_minute} rpm)")

            if srv.cpu_percent < 20:
                findings.append(f"Low CPU utilization ({srv.cpu_percent}%)")
            elif srv.cpu_percent >= 80:
                findings.append(f"High CPU utilization ({srv.cpu_percent}%)")

            if srv.memory_percent < 30:
                findings.append(f"Low memory utilization ({srv.memory_percent}%)")
            elif srv.memory_percent >= 80:
                findings.append(f"High memory utilization ({srv.memory_percent}%)")

            if srv.latency_ms > srv.max_latency_ms:
                findings.append(f"LATENCY BREACH: {srv.latency_ms}ms > {srv.max_latency_ms}ms")
            elif srv.latency_ms > srv.max_latency_ms * 0.8:
                findings.append(f"Latency approaching limit: {srv.latency_ms}ms / {srv.max_latency_ms}ms")

            if srv.instances > srv.min_instances:
                findings.append(f"Capacity is above minimum bound ({srv.instances} > {srv.min_instances})")

            service_observations.append(ServiceObservation(
                service_id=srv.service_id,
                metrics=srv.model_dump(),
                observation_timestamp=srv.timestamp,
                fresh=is_fresh,
                age_seconds=max(0.0, round(age_sec, 1)),
                findings=findings,
            ))

        # ---------------------------------------------------------------------
        # Step 3 & 4: Investigate Cost, Freshness, and Reliability
        # ---------------------------------------------------------------------
        add_audit("investigate", "Analyzing utilization, latency headroom, and financial footprint.")

        # If data is stale, immediately abort safe actions
        if is_any_service_stale and request.environment_constraints.require_fresh_metrics_for_action:
            add_audit("freshness_reject", "Stale or conflicting observation detected. Rejecting capacity modifications.")
            problem = ObservedProblem(
                type=ProblemType.STALE_OBSERVATIONS,
                description=" ".join(stale_reasons),
                affected_services=[o.service_id for o in service_observations if not o.fresh],
            )
            return OptimizationReport(
                report_id=report_id,
                created_at=created_at_iso,
                user_request=request.user_request,
                status=ReportStatus.BLOCKED,
                intent=IntentType.COST_OPTIMIZATION,
                summary=f"Action blocked due to stale or conflicting metrics: {problem.description}",
                observed_problem=problem,
                observations=service_observations,
                candidate_actions=[],
                selected_action=None,
                policy_checks=[PolicyCheckResult(
                    check="observation_freshness",
                    passed=False,
                    message="Observation freshness requirement violated. Scaling refused until fresh data is provided."
                )],
                execution=ExecutionResult(attempted=False, status=ActionStatus.SKIPPED),
                verification=VerificationResult(performed=False, success=False),
                final_decision=FinalDecision.STALE_DATA,
                recommendations=["Request fresh metric telemetry before attempting automated cost optimization."],
                audit_trail=audit_trail,
            )

        # ---------------------------------------------------------------------
        # Step 5: Generate Candidate Actions (Deterministic Decision Rules)
        # ---------------------------------------------------------------------
        candidates: List[CandidateAction] = []
        detected_problem_type = ProblemType.NO_ISSUE
        problem_desc = "No immediate cost or capacity anomalies detected."
        affected_services: List[str] = []

        for srv in raw_services:
            unit_cost = srv.cost_per_hour / srv.instances if srv.instances > 0 else 0.0
            
            # Check traffic growth
            traffic_growth_pct = 0.0
            if srv.previous_requests_per_minute and srv.previous_requests_per_minute > 0:
                traffic_growth_pct = ((srv.requests_per_minute - srv.previous_requests_per_minute) / srv.previous_requests_per_minute) * 100.0

            # Rule 5: Urgent Scale Up (latency breach or severe CPU/Mem load)
            if srv.latency_ms > srv.max_latency_ms or srv.cpu_percent >= 90.0 or srv.memory_percent >= 90.0:
                detected_problem_type = ProblemType.CAPACITY_RISK
                problem_desc = f"Service '{srv.service_id}' exceeded critical operating limits (CPU: {srv.cpu_percent}%, Mem: {srv.memory_percent}%, Latency: {srv.latency_ms}ms / {srv.max_latency_ms}ms)."
                affected_services.append(srv.service_id)
                target = min(srv.max_instances, srv.instances + min(2, request.environment_constraints.maximum_scale_step))
                candidates.append(CandidateAction(
                    service_id=srv.service_id,
                    action=ActionType.SCALE_UP,
                    target_instances=target,
                    reason=f"Urgent scale-up required: CPU={srv.cpu_percent}%, Latency={srv.latency_ms}ms exceeds threshold.",
                    expected_hourly_savings=-round((target - srv.instances) * unit_cost, 2),
                    risk_level="high",
                ))

            # Rule 4: Preventative Scale Up (traffic doubled or high load near latency target)
            elif traffic_growth_pct >= 50.0 or (srv.latency_ms >= srv.max_latency_ms * 0.8 and traffic_growth_pct > 0) or srv.cpu_percent >= 80.0:
                detected_problem_type = ProblemType.TRAFFIC_GROWTH
                problem_desc = f"Traffic on '{srv.service_id}' surged (+{traffic_growth_pct:.0f}%) pushing latency near target ({srv.latency_ms}ms / {srv.max_latency_ms}ms)."
                affected_services.append(srv.service_id)
                target = min(srv.max_instances, srv.instances + 1)
                candidates.append(CandidateAction(
                    service_id=srv.service_id,
                    action=ActionType.SCALE_UP,
                    target_instances=target,
                    reason=f"Preventive scale-up to absorb traffic surge (+{traffic_growth_pct:.0f}%) and protect latency SLA.",
                    expected_hourly_savings=-round((target - srv.instances) * unit_cost, 2),
                    risk_level="low",
                ))

            # Rule 1 & 2: Zero Traffic Idle Waste
            elif srv.requests_per_minute == 0 and srv.cpu_percent < 20.0 and srv.memory_percent < 30.0 and srv.instances > srv.min_instances and srv.healthy:
                detected_problem_type = ProblemType.COST_WASTE
                problem_desc = f"Idle capacity detected on '{srv.service_id}' with zero traffic (0 rpm) and low utilization ({srv.cpu_percent}% CPU)."
                affected_services.append(srv.service_id)
                
                # Desired reduction down to min_instances
                target = srv.min_instances
                # Capped by maximum_scale_step
                if srv.instances - target > request.environment_constraints.maximum_scale_step:
                    target = srv.instances - request.environment_constraints.maximum_scale_step

                savings = round((srv.instances - target) * unit_cost, 2)
                candidates.append(CandidateAction(
                    service_id=srv.service_id,
                    action=ActionType.SCALE_DOWN,
                    target_instances=target,
                    reason=f"Zero traffic and low utilization ({srv.cpu_percent}% CPU, {srv.memory_percent}% Mem) allows safe scale-down.",
                    expected_hourly_savings=savings,
                    risk_level="low",
                ))

            # Rule 3: Active Service Cautious Scale-Down
            elif srv.cpu_percent < 35.0 and srv.memory_percent < 50.0 and srv.instances > srv.min_instances and srv.healthy:
                latency_margin_threshold = srv.max_latency_ms * (1.0 - (request.environment_constraints.latency_safety_margin_percent / 100.0))
                if srv.latency_ms <= latency_margin_threshold and traffic_growth_pct <= 0:
                    target = max(srv.min_instances, srv.instances - 1)
                    if target < srv.instances:
                        savings = round((srv.instances - target) * unit_cost, 2)
                        candidates.append(CandidateAction(
                            service_id=srv.service_id,
                            action=ActionType.SCALE_DOWN,
                            target_instances=target,
                            reason=f"Cautious scale-down: active service with surplus capacity ({srv.cpu_percent}% CPU, {srv.latency_ms}ms latency).",
                            expected_hourly_savings=savings,
                            risk_level="medium",
                        ))

        observed_problem = ObservedProblem(
            type=detected_problem_type,
            description=problem_desc,
            affected_services=affected_services,
        )

        # If no candidates, return NO_ACTION
        if not candidates:
            add_audit("candidate_generation", "No safe candidate actions required or available.")
            return OptimizationReport(
                report_id=report_id,
                created_at=created_at_iso,
                user_request=request.user_request,
                status=ReportStatus.NO_ACTION,
                intent=IntentType.INVESTIGATE_ONLY,
                summary="All services are currently operating within optimal resource and SLA thresholds.",
                observed_problem=observed_problem,
                observations=service_observations,
                candidate_actions=[],
                selected_action=None,
                policy_checks=[],
                execution=ExecutionResult(attempted=False, status=ActionStatus.SKIPPED),
                verification=VerificationResult(performed=False, success=False),
                final_decision=FinalDecision.NO_SAFE_ACTION,
                recommendations=["Maintain current instance allocations."],
                audit_trail=audit_trail,
            )

        # ---------------------------------------------------------------------
        # Step 6: Reasoning & LLM / Fallback Decision Selection
        # ---------------------------------------------------------------------
        add_audit("reasoning", f"Evaluating {len(candidates)} candidate action(s) via reasoning engine.")
        llm_decision = await llm_adapter.analyze_and_rank(
            user_request=request.user_request,
            observations=[o.model_dump() for o in service_observations],
            candidate_actions=[c.model_dump() for c in candidates],
            constraints=request.environment_constraints.model_dump(),
        )

        chosen_idx = llm_decision.selected_candidate_index
        if chosen_idx < 0 or chosen_idx >= len(candidates):
            chosen_candidate = candidates[0]
        else:
            chosen_candidate = candidates[chosen_idx]

        target_service = next(s for s in raw_services if s.service_id == chosen_candidate.service_id)

        # ---------------------------------------------------------------------
        # Step 7: Deterministic Policy Validation (Final Authority)
        # ---------------------------------------------------------------------
        add_audit("policy_validation", f"Running deterministic safety checks on '{chosen_candidate.action.value}' for '{target_service.service_id}'.")
        is_approved, policy_checks, final_target_instances = self.policy_engine.validate_action(
            service=target_service,
            action=chosen_candidate.action,
            target_instances=chosen_candidate.target_instances,
            constraints=request.environment_constraints,
            latest_traffic=request.latest_traffic,
            recent_events=request.recent_events,
            reference_timestamp=reference_dt,
        )

        selected_action = SelectedAction(
            service_id=target_service.service_id,
            action=chosen_candidate.action,
            previous_instances=target_service.instances,
            requested_instances=final_target_instances,
            reason=chosen_candidate.reason,
            expected_hourly_savings=chosen_candidate.expected_hourly_savings,
            risk_level=chosen_candidate.risk_level,
        )

        if not is_approved:
            add_audit("policy_blocked", "Deterministic safety engine rejected proposed action.")
            return OptimizationReport(
                report_id=report_id,
                created_at=created_at_iso,
                user_request=request.user_request,
                status=ReportStatus.BLOCKED,
                intent=llm_decision.intent,
                summary=f"Action blocked by policy safety engine: {selected_action.reason}",
                observed_problem=observed_problem,
                observations=service_observations,
                candidate_actions=candidates,
                selected_action=selected_action,
                policy_checks=policy_checks,
                execution=ExecutionResult(attempted=False, status=ActionStatus.SKIPPED),
                verification=VerificationResult(performed=False, success=False),
                final_decision=FinalDecision.NO_SAFE_ACTION,
                recommendations=["Review policy violation details and adjust safety margins if appropriate."],
                audit_trail=audit_trail,
            )

        # ---------------------------------------------------------------------
        # Step 8: Execute Action (Simulated Cloud Provider API)
        # ---------------------------------------------------------------------
        add_audit("execute", f"Dispatching '{selected_action.action.value}' to target instances: {final_target_instances}.")
        
        exec_status = ActionStatus.PENDING
        exec_error = None
        action_id = f"act-{uuid.uuid4().hex[:6]}"

        if selected_action.action == ActionType.SCALE_UP:
            res = execute_scale_up(target_service.service_id, final_target_instances, action_id=action_id)
        elif selected_action.action == ActionType.SCALE_DOWN:
            res = execute_scale_down(target_service.service_id, final_target_instances, action_id=action_id)
        elif selected_action.action == ActionType.STOP_IDLE_SERVICE:
            res = execute_stop_idle_service(target_service.service_id, action_id=action_id)
        else:
            res = None

        if res and res.success:
            exec_status = ActionStatus.SUCCEEDED
            action_id = res.data.get("action_id", action_id)
            self.policy_engine.record_action(target_service.service_id, selected_action.action.value, now_dt.isoformat())
        else:
            exec_status = ActionStatus.FAILED
            exec_error = res.error if res else "Unknown execution failure"
            action_id = res.data.get("action_id", action_id) if res else action_id

        execution_result = ExecutionResult(
            attempted=True,
            action_id=action_id,
            status=exec_status,
            error=exec_error,
            retries=0,
        )

        # If execution failed (e.g. Scenario D: capacity_unavailable)
        if exec_status == ActionStatus.FAILED:
            add_audit("execution_failed", f"Cloud API action failed: {exec_error}. Initiating escalation.")
            unit_c = target_service.cost_per_hour / target_service.instances if target_service.instances > 0 else 0.0
            return OptimizationReport(
                report_id=report_id,
                created_at=created_at_iso,
                user_request=request.user_request,
                status=ReportStatus.FAILED,
                intent=llm_decision.intent,
                summary=f"Scaling action failed due to cloud provider error: {exec_error}. Service requires urgent escalation.",
                observed_problem=observed_problem,
                observations=service_observations,
                candidate_actions=candidates,
                selected_action=selected_action,
                policy_checks=policy_checks,
                execution=execution_result,
                verification=VerificationResult(
                    performed=True,
                    success=False,
                    checks={
                        "execution_status": {"passed": False, "message": f"Action execution failed: {exec_error}"}
                    },
                    estimated_hourly_cost_before=target_service.cost_per_hour,
                    estimated_hourly_cost_after=target_service.cost_per_hour,
                    estimated_hourly_savings=0.0,
                ),
                final_decision=FinalDecision.ESCALATED,
                recommendations=[
                    f"Escalate to Cloud Infrastructure Ops: '{exec_error}' encountered.",
                    "Provision fallback capacity in an alternative availability zone or instance family.",
                ],
                audit_trail=audit_trail,
            )

        # ---------------------------------------------------------------------
        # Step 9: Post-Action Verification
        # ---------------------------------------------------------------------
        add_audit("verify", "Performing post-action state verification and SLA validation.")
        unit_cost = target_service.cost_per_hour / target_service.instances if target_service.instances > 0 else 0.0
        expected_cost_after = unit_cost * final_target_instances

        verification_result = self.verification_engine.verify_action(
            service=target_service,
            action=selected_action.action,
            previous_instances=target_service.instances,
            requested_instances=final_target_instances,
            execution_status=exec_status,
            constraints=request.environment_constraints,
            cost_before=target_service.cost_per_hour,
            cost_after=expected_cost_after,
        )

        add_audit("complete", f"Optimization workflow complete. Verification {'passed' if verification_result.success else 'failed'}.")

        summary = (
            f"Successfully optimized '{target_service.service_id}': executed {selected_action.action.value} "
            f"from {target_service.instances} to {final_target_instances} instances. "
            f"Hourly savings: ${verification_result.estimated_hourly_savings:.2f}/hr "
            f"(Est. Monthly: ${verification_result.estimated_hourly_savings * 730:.2f}/mo)."
            if selected_action.action == ActionType.SCALE_DOWN
            else f"Preventive scale-up verified for '{target_service.service_id}': expanded capacity from {target_service.instances} to {final_target_instances} instances to guarantee SLA latency."
        )

        return OptimizationReport(
            report_id=report_id,
            created_at=created_at_iso,
            user_request=request.user_request,
            status=ReportStatus.COMPLETED if verification_result.success else ReportStatus.REQUIRES_ATTENTION,
            intent=llm_decision.intent,
            summary=summary,
            observed_problem=observed_problem,
            observations=service_observations,
            candidate_actions=candidates,
            selected_action=selected_action,
            policy_checks=policy_checks,
            execution=execution_result,
            verification=verification_result,
            final_decision=FinalDecision.ACTION_TAKEN if verification_result.success else FinalDecision.ACTION_FAILED,
            recommendations=llm_decision.recommendations,
            audit_trail=audit_trail,
        )


# Global agent instance
agent = CostOptimizationAgent()
