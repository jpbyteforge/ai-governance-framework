"""Decision records — proposals, verdicts, and action results.

Every action in a governed system follows the cycle:
    Proposal -> Decision (with Verdict) -> ActionResult

Nothing executes without a recorded decision. Nothing decides without a proposal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
