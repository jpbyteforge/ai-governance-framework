"""Governance exceptions — typed error hierarchy for governance violations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class GovernanceViolation(Exception):
    """Base exception for all governance violations.

    Every violation is a structured record — not just an error message.
    This enables audit trails to capture violations with full context.
    """

    principle: str = ""
    action: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __str__(self) -> str:
        return (
            f"GovernanceViolation[{self.principle}]: "
            f"action={self.action!r}, reason={self.reason!r}"
        )


@dataclass(frozen=True)
class NoRuleError(GovernanceViolation):
    """Raised when no rule exists for a proposed action (fail-closed).

    Principle 3 — Determinism: if there is no explicit rule permitting an action,
    the action is blocked. This is the core of fail-closed governance.
    """

    principle: str = "determinism"

    def __str__(self) -> str:
        return (
            f"NoRuleError[fail-closed]: no rule found for action={self.action!r}. "
            f"Reason: {self.reason!r}"
        )


@dataclass(frozen=True)
class ForbiddenZoneError(GovernanceViolation):
    """Raised when an action targets a forbidden zone.

    Principle 4 — Forbidden Zones: write operations are only permitted
    in explicitly allowed areas.
    """

    zone: str = ""
    principle: str = "forbidden_zones"

    def __str__(self) -> str:
        return (
            f"ForbiddenZoneError: zone={self.zone!r}, action={self.action!r}. "
            f"Reason: {self.reason!r}"
        )


@dataclass(frozen=True)
class OwnershipError(GovernanceViolation):
    """Raised when an action lacks proper ownership attribution.

    Principle 7 — Ownership: every artefact has a human owner.
    Actions without ownership attribution are rejected.
    """

    principle: str = "ownership"

    def __str__(self) -> str:
        return (
            f"OwnershipError: action={self.action!r} has no owner. "
            f"Reason: {self.reason!r}"
        )


@dataclass(frozen=True)
class HumanApprovalRequired(GovernanceViolation):
    """Raised when an action requires human-in-the-loop confirmation.

    Principle 6 — Human-in-the-loop: critical or irreversible actions
    require explicit human confirmation before execution.
    """

    principle: str = "human_in_the_loop"

    def __str__(self) -> str:
        return (
            f"HumanApprovalRequired: action={self.action!r} requires human confirmation. "
            f"Reason: {self.reason!r}"
        )


@dataclass(frozen=True)
class ReadinessGateCritical(GovernanceViolation):
    """Raised when the AI Readiness Gate enters CRITICAL status (<=2/4 tests passing).

    Principle 9 — Evolution with Process: automatic downgrade when AI system
    performance falls below minimum viability thresholds.
    """

    cycle_id: str = ""
    passed_count: int = 0
    principle: str = "evolution_with_process"

    def __str__(self) -> str:
        return (
            f"ReadinessGateCritical[cycle={self.cycle_id!r}]: "
            f"only {self.passed_count}/4 readiness tests passed. "
            f"Automatic downgrade triggered. Reason: {self.reason!r}"
        )


@dataclass(frozen=True)
class MandatoryReviewRequired(GovernanceViolation):
    """Raised when 2 consecutive cycles have Impact<=0 or MarginalValue<=0.

    Principle 9 — Evolution with Process: persistent underperformance requires
    structured human review before the AI system may continue operating.
    """

    cycle_id: str = ""
    principle: str = "evolution_with_process"

    def __str__(self) -> str:
        return (
            f"MandatoryReviewRequired[cycle={self.cycle_id!r}]: "
            f"2 consecutive cycles with failing impact/marginal value. "
            f"Human review mandatory before resuming. Reason: {self.reason!r}"
        )
