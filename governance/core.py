"""GovernanceEngine — the central orchestrator for fail-closed governance.

The engine receives proposals, evaluates them against registered rules,
records decisions in the audit trail, and returns structured results.

If no rule matches a proposal, the engine raises NoRuleError (fail-closed).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from governance.audit import AuditTrail
from governance.decisions import ActionResult, Decision, Proposal, Verdict
from governance.exceptions import (
    ForbiddenZoneError,
    HumanApprovalRequired,
    NoRuleError,
    OwnershipError,
)
from governance.rules import RuleRegistry


class Principle(Enum):
    """The 10 operational governance principles."""

    REGULATED_COMPONENT = "regulated_component"
    DOCUMENTARY_SOVEREIGNTY = "documentary_sovereignty"
    DETERMINISM = "determinism"
    FORBIDDEN_ZONES = "forbidden_zones"
    EVIDENCE_NOT_PERSUASION = "evidence_not_persuasion"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"
    OWNERSHIP = "ownership"
    PROPORTIONAL_CHANGE = "proportional_change"
    EVOLUTION_WITH_PROCESS = "evolution_with_process"
    META_GOVERNANCE = "meta_governance"

    @property
    def description(self) -> str:
        return _PRINCIPLE_DESCRIPTIONS[self]


_PRINCIPLE_DESCRIPTIONS: dict[Principle, str] = {
    Principle.REGULATED_COMPONENT: "AI proposes, never decides. Every action requires documentary basis.",
    Principle.DOCUMENTARY_SOVEREIGNTY: "Sovereign documents prevail over code, config, and output.",
    Principle.DETERMINISM: "Checks first. Fail-closed on ambiguity. No creative compensation for failures.",
    Principle.FORBIDDEN_ZONES: "Write only in permitted areas. No operations in protected zones.",
    Principle.EVIDENCE_NOT_PERSUASION: "Verifiable output. Qualify as FACT, INFERENCE, or UNCONFIRMED.",
    Principle.HUMAN_IN_THE_LOOP: "Critical/irreversible actions require human confirmation.",
    Principle.OWNERSHIP: "Every artefact has a human owner. Decisions recorded: who, when, why, authority.",
    Principle.PROPORTIONAL_CHANGE: "Impact analysis mandatory. Principle > policy > procedure > reference.",
    Principle.EVOLUTION_WITH_PROCESS: "Feedback loops. Periodic review. Sunset clauses on experimental rules.",
    Principle.META_GOVERNANCE: "Explicit hierarchy. Referential integrity. Governance that paralyzes has failed.",
}


@dataclass
class GovernanceEngine:
    """The fail-closed governance engine.

    Usage:
        engine = GovernanceEngine(registry=my_rules)
        decision = engine.evaluate(proposal)
        if decision.is_approved:
            result = engine.record_execution(decision, success=True, output="done")
    """

    registry: RuleRegistry
    audit: AuditTrail

    def __init__(self, registry: RuleRegistry | None = None) -> None:
        self.registry = registry or RuleRegistry()
        self.audit = AuditTrail()

    def evaluate(self, proposal: Proposal) -> Decision:
        """Evaluate a proposal against all registered rules.

        Implements the fail-closed principle: if no rule matches the
        proposed action, a NoRuleError is raised.

        Args:
            proposal: The action proposal to evaluate.

        Returns:
            A Decision recording the verdict and reasons.

        Raises:
            NoRuleError: If no rule exists for the proposed action.
            OwnershipError: If the proposal has no owner (Principle 7).
        """
        # Principle 7 — Ownership check
        if not proposal.owner:
            self.audit.append(
                event_type="violation",
                actor=proposal.proposed_by,
                action=proposal.action,
                target=proposal.target,
                outcome="denied",
                details={"reason": "No owner specified", "principle": "ownership"},
            )
            raise OwnershipError(
                action=proposal.action,
                reason="Proposal must have an owner. Principle 7 requires ownership attribution.",
            )

        # Find matching rule (Principle 3 — fail-closed)
        match = self.registry.find_rule(proposal.action)

        if match is None:
            self.audit.append(
                event_type="violation",
                actor=proposal.proposed_by,
                action=proposal.action,
                target=proposal.target,
                outcome="denied",
                details={"reason": "No matching rule (fail-closed)", "principle": "determinism"},
            )
            raise NoRuleError(
                action=proposal.action,
                reason=f"No rule found for action {proposal.action!r}. Fail-closed: action blocked.",
            )

        domain, rule = match
        verdict, reasons = rule.evaluate(proposal)

        decision = Decision(
            proposal=proposal,
            verdict=verdict,
            reasons=reasons,
            decided_by=f"rule:{domain}/{rule.name}",
            authority=f"principles:{','.join(rule.principles)}",
        )

        # Record in audit trail
        self.audit.append(
            event_type="decision",
            actor=proposal.proposed_by,
            action=proposal.action,
            target=proposal.target,
            outcome=verdict.value,
            details={
                "rule": rule.name,
                "domain": domain,
                "reasons": list(reasons),
                "owner": proposal.owner,
                "rationale": proposal.rationale,
            },
        )

        # Principle 6 — Human-in-the-loop
        if decision.needs_human:
            raise HumanApprovalRequired(
                action=proposal.action,
                reason=f"Action {proposal.action!r} requires human approval. "
                f"Reasons: {'; '.join(reasons)}",
            )

        # Principle 4 — Forbidden zones (if verdict is denied with zone info)
        if decision.is_denied:
            for reason in reasons:
                if "forbidden zone" in reason.lower():
                    raise ForbiddenZoneError(
                        action=proposal.action,
                        reason=reason,
                        zone=proposal.target,
                    )

        return decision

    def record_execution(
        self,
        decision: Decision,
        success: bool,
        output: str = "",
        error: str = "",
    ) -> ActionResult:
        """Record the execution result of an approved decision.

        Args:
            decision: The approved decision that was executed.
            success: Whether the execution succeeded.
            output: Output of the execution (if successful).
            error: Error message (if failed).

        Returns:
            An ActionResult recorded in the audit trail.
        """
        result = ActionResult(
            decision=decision,
            success=success,
            output=output,
            error=error,
        )

        self.audit.append(
            event_type="execution",
            actor=decision.proposal.proposed_by,
            action=decision.proposal.action,
            target=decision.proposal.target,
            outcome="success" if success else "failure",
            details={
                "output": output,
                "error": error,
                "rule": decision.decided_by,
            },
        )

        return result
