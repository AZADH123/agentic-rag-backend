"""
Agent policies: hard limits and safety checks.

These are deliberately separated from the ToolRegistry so the orchestrator
can apply them at the run level (not just per-tool).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class AgentPolicies:
    max_steps: int = 6
    max_query_refinements: int = 1
    allow_tools: bool = True


def load_policies() -> AgentPolicies:
    settings = get_settings()
    return AgentPolicies(
        max_steps=settings.max_agent_steps,
        max_query_refinements=settings.max_query_refinements,
        allow_tools=True,
    )


def enforce_step_limit(state: "AgentPolicies", step_count: int, max_steps: int) -> None:
    """Raise if we've exceeded the step budget."""
    if step_count >= max_steps:
        log.warning("agent_step_limit_hit", step_count=step_count, max=max_steps)
        raise ForbiddenError(
            f"Agent exceeded max steps ({max_steps}). "
            "Reduce the question scope or increase MAX_AGENT_STEPS."
        )