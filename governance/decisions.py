"""Decision records — proposals, verdicts, and action results.

Every action in a governed system follows the cycle:
    Proposal -> Decision (with Verdict) -> ActionResult

Nothing executes without a recorded decision. Nothing decides without a proposal.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Verdict(Enum):
    """Outcome of evaluating a proposal against governance rules."""

    APPROVED = "approved"
    DENIED = "denied"
    PENDING_HUMAN_APPROVAL = "pending_human_approval"


class EvidenceQualifier(Enum):
    """Principle 5 — Evidence, not persuasion.

    Every piece of evidence attached to a decision must be qualified.
    """

    FACT = "fact"
    INFERENCE = "inference"
    UNCONFIRMED = "unconfirmed"


@dataclass(frozen=True)
class Evidence:
    """A qualified piece of evidence supporting a decision."""

    content: str
    qualifier: EvidenceQualifier
    source: str = ""

    def __str__(self) -> str:
        tag = self.qualifier.value.upper()
        src = f" (source: {self.source})" if self.source else ""
        return f"[{tag}] {self.content}{src}"


@dataclass(frozen=True)
class Proposal:
    """A request to perform an action in a governed system.

    Principle 1 — Regulated Component: AI proposes, never decides.
    A Proposal is the only way to request action.
    """

    action: str
    target: str
    rationale: str
    proposed_by: str
    owner: str
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: tuple[Evidence, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    requires_human_approval: bool = False

    def with_evidence(self, *items: Evidence) -> Proposal:
        """Return a new Proposal with additional evidence attached."""
        return Proposal(
            action=self.action,
            target=self.target,
            rationale=self.rationale,
            proposed_by=self.proposed_by,
            owner=self.owner,
            metadata=self.metadata,
            evidence=self.evidence + items,
            timestamp=self.timestamp,
            requires_human_approval=self.requires_human_approval,
        )


@dataclass(frozen=True)
class Decision:
    """The governance engine's verdict on a proposal.

    Records who decided, when, why, and on what authority (Principle 7).
    """

    proposal: Proposal
    verdict: Verdict
    reasons: tuple[str, ...]
    decided_by: str
    authority: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_approved(self) -> bool:
        return self.verdict == Verdict.APPROVED

    @property
    def is_denied(self) -> bool:
        return self.verdict == Verdict.DENIED

    @property
    def needs_human(self) -> bool:
        return self.verdict == Verdict.PENDING_HUMAN_APPROVAL


@dataclass(frozen=True)
class ActionResult:
    """The outcome of executing an approved action.

    Only created after a Decision with APPROVED verdict.
    Immutable record for the audit trail.
    """

    decision: Decision
    success: bool
    output: str = ""
    error: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# --- AI Decision Event Schema ---
# Extends the Proposal -> Decision -> ActionResult cycle with AI-specific tracking
# for continuous scoring, override detection, and outcome measurement.


class CostLevel(Enum):
    """Cost classification for decision context."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionType(Enum):
    """How the decision is made."""

    AUTONOMOUS = "autonomous"
    ASSISTED = "assisted"
    HUMAN_ONLY = "human_only"


@dataclass(frozen=True)
class DecisionContext:
    """Context classifying the decision by type and cost profile."""

    decision_type: DecisionType
    cost_of_error: CostLevel
    cost_of_latency: CostLevel


@dataclass(frozen=True)
class InputTracking:
    """Tracks the data inputs to an AI decision for reproducibility."""

    data_version: str
    features_hash: str
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelTracking:
    """Tracks the model used for an AI recommendation."""

    model_id: str
    model_version: str
    inference_parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIRecommendation:
    """The AI system's recommendation before human decision."""

    output: Any
    confidence: float


@dataclass(frozen=True)
class HumanDecisionRecord:
    """Records the human's final decision and whether it overrode the AI."""

    final_decision: Any
    override: bool
    override_reason: str | None = None


@dataclass(frozen=True)
class OutcomeRecord:
    """Observed outcome after a decision was executed."""

    observed_result: Any
    outcome_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True)
class AIDecisionRecord:
    """Full lifecycle record for an AI-assisted decision.

    Composes existing governance objects with AI-specific tracking.
    This is the primary record for AI Readiness Gate scoring and metrics.
    """

    action_result: ActionResult
    context: DecisionContext
    input_tracking: InputTracking
    model_tracking: ModelTracking
    recommendation: AIRecommendation
    human_decision: HumanDecisionRecord | None = None
    outcome: OutcomeRecord | None = None
    reproducible: bool = False
    audited: bool = False
    audit_notes: str | None = None

    @property
    def was_overridden(self) -> bool:
        """True if the human overrode the AI recommendation."""
        return self.human_decision is not None and self.human_decision.override

    @property
    def influenced_decision(self) -> bool:
        """True if AI recommendation was accepted (not overridden)."""
        if self.human_decision is None:
            return True
        return not self.human_decision.override

    def with_outcome(self, outcome: OutcomeRecord) -> AIDecisionRecord:
        """Return a new record with the observed outcome attached."""
        return replace(self, outcome=outcome)

    def with_human_decision(
        self, human_decision: HumanDecisionRecord
    ) -> AIDecisionRecord:
        """Return a new record with the human decision attached."""
        return replace(self, human_decision=human_decision)
