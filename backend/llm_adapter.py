"""LLM Adapter supporting OpenAI-compatible endpoints with robust deterministic fallback."""
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx
from pydantic import BaseModel, Field

from backend.config import settings
from backend.models import IntentType, ActionType

logger = logging.getLogger("cloud_agent.llm")


class LLMDecisionOutput(BaseModel):
    """Structured response schema expected from LLM or fallback engine."""
    intent: IntentType = Field(default=IntentType.COST_OPTIMIZATION)
    selected_candidate_index: int = Field(default=0)
    reason: str = Field(default="Deterministic policy analysis determined optimal candidate.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    recommendations: List[str] = Field(default_factory=list)


class LLMAdapter(ABC):
    """Abstract interface for agent reasoning adapters."""

    @abstractmethod
    async def analyze_and_rank(
        self,
        user_request: str,
        observations: List[Dict[str, Any]],
        candidate_actions: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> LLMDecisionOutput:
        """Analyze intent and rank candidate actions."""
        pass


class DeterministicFallbackAdapter(LLMAdapter):
    """Offline rule-based reasoning engine providing 100% deterministic analysis."""

    async def analyze_and_rank(
        self,
        user_request: str,
        observations: List[Dict[str, Any]],
        candidate_actions: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> LLMDecisionOutput:
        req_lower = user_request.lower()

        # Intent classification
        if "cost" in req_lower or "reduce" in req_lower or "unnecessary" in req_lower or "waste" in req_lower:
            intent = IntentType.COST_OPTIMIZATION
        elif "increase" in req_lower or "traffic" in req_lower or "surge" in req_lower:
            intent = IntentType.SCALE_FOR_TRAFFIC
        elif "latency" in req_lower or "target" in req_lower:
            intent = IntentType.PROTECT_LATENCY
        elif "only if" in req_lower or "conditional" in req_lower:
            intent = IntentType.CONDITIONAL_SCALING
        elif "investigate" in req_lower or "audit" in req_lower or "inspect" in req_lower:
            intent = IntentType.INVESTIGATE_ONLY
        else:
            intent = IntentType.COST_OPTIMIZATION

        if not candidate_actions:
            return LLMDecisionOutput(
                intent=intent,
                selected_candidate_index=-1,
                reason="No candidate actions satisfy safety constraints or require intervention.",
                confidence=1.0,
                recommendations=["Monitor workload trends for upcoming capacity changes."],
            )

        # Rank candidates: prioritize scale_up for urgent/latency risk, idle waste for cost optimization
        best_idx = 0
        reason = candidate_actions[0].get("reason", "Highest priority candidate selected.")
        recommendations = []

        if intent in (IntentType.SCALE_FOR_TRAFFIC, IntentType.PROTECT_LATENCY):
            for idx, cand in enumerate(candidate_actions):
                if cand.get("action") == ActionType.SCALE_UP.value:
                    best_idx = idx
                    reason = cand.get("reason", "Preventive scale-up selected to satisfy latency and traffic requirements.")
                    break
        elif intent == IntentType.CONDITIONAL_SCALING:
            # Check for urgent scaling candidates first
            for idx, cand in enumerate(candidate_actions):
                if cand.get("action") == ActionType.SCALE_UP.value or cand.get("risk_level") == "high":
                    best_idx = idx
                    reason = cand.get("reason", "Conditional scaling triggered by high resource pressure.")
                    break
        else:
            # For cost optimization, prioritize idle waste candidates (low risk, high savings)
            max_savings = -999999.0
            for idx, cand in enumerate(candidate_actions):
                savings = cand.get("expected_hourly_savings", 0.0)
                priority_bonus = 100.0 if cand.get("risk_level") == "low" else 0.0
                score = savings + priority_bonus
                if score > max_savings:
                    max_savings = score
                    best_idx = idx
                    reason = cand.get("reason", "Strongest cost-waste candidate selected for safe reduction.")

        # Context-aware recommendations
        selected = candidate_actions[best_idx]
        if selected.get("action") == ActionType.SCALE_DOWN.value:
            recommendations.append(f"Consider setting up auto-scaling schedule for '{selected.get('service_id')}'.")
        elif selected.get("action") == ActionType.SCALE_UP.value:
            recommendations.append(f"Monitor traffic peak duration for '{selected.get('service_id')}' to scale down after load subsides.")

        return LLMDecisionOutput(
            intent=intent,
            selected_candidate_index=best_idx,
            reason=reason,
            confidence=0.95,
            recommendations=recommendations,
        )


class OpenAICompatibleAdapter(LLMAdapter):
    """Adapter connecting to any OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float = 10.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.fallback = DeterministicFallbackAdapter()

    async def analyze_and_rank(
        self,
        user_request: str,
        observations: List[Dict[str, Any]],
        candidate_actions: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> LLMDecisionOutput:
        system_prompt = (
            "You are a specialized Cloud Infrastructure AI reasoning engine.\n"
            "Analyze the user's operational request, sanitized service metrics, and proposed candidate actions.\n"
            "You MUST respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "intent": "cost_optimization" | "scale_for_traffic" | "protect_latency" | "conditional_scaling" | "investigate_only",\n'
            '  "selected_candidate_index": integer (0-indexed index of chosen candidate, or -1 if no action),\n'
            '  "reason": "concise explanation of your decision",\n'
            '  "confidence": float (between 0.0 and 1.0),\n'
            '  "recommendations": ["list", "of", "actionable", "recommendations"]\n'
            "}\n"
            "Do not output markdown code fences. Return raw JSON."
        )

        user_content = json.dumps({
            "user_request": user_request,
            "observations": observations,
            "candidate_actions": candidate_actions,
            "constraints": constraints,
        }, indent=2)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                    },
                )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return LLMDecisionOutput.model_validate(parsed)
            else:
                logger.warning(
                    f"LLM API returned status {response.status_code}: {response.text}. Using fallback."
                )
        except Exception as exc:
            logger.warning(f"LLM call failed or timed out: {exc}. Utilizing deterministic fallback engine.")

        # Graceful fallback
        return await self.fallback.analyze_and_rank(
            user_request=user_request,
            observations=observations,
            candidate_actions=candidate_actions,
            constraints=constraints,
        )


def get_llm_adapter() -> LLMAdapter:
    """Factory creating configured LLM adapter or fallback."""
    if settings.LLM_API_KEY and settings.LLM_API_KEY.strip():
        return OpenAICompatibleAdapter(
            api_key=settings.LLM_API_KEY.strip(),
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    return DeterministicFallbackAdapter()
