"""Rule engine — define, compose, and evaluate governance rules.

Rules are the backbone of fail-closed governance. An action without
a matching rule is denied by default (Principle 3 — Determinism).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from governance.decisions import Proposal, Verdict


class RiskLevel(Enum):
    """EU AI Act risk classification levels."""

    UNACCEPTABLE = "unacceptable"
    HIGH = "high"
    LIMITED = "limited"
    MINIMAL = "minimal"


class RuleEvaluator(Protocol):
    """Protocol for rule evaluation functions.

    A rule evaluator receives a proposal and returns a tuple of
    (verdict, reasons). This enables composable, testable rules.
    """

    def __call__(self, proposal: Proposal) -> tuple[Verdict, tuple[str, ...]]: ...


@dataclass(frozen=True)
class Rule:
    """A named governance rule with an evaluator function.

    Rules are immutable and self-documenting. Each rule references
    the principle(s) it implements.
    """

    name: str
    description: str
    principles: tuple[str, ...]
    actions: frozenset[str]
    evaluator: RuleEvaluator
    risk_level: RiskLevel = RiskLevel.MINIMAL

    def matches(self, action: str) -> bool:
        """Check if this rule applies to the given action."""
        return action in self.actions or "*" in self.actions

    def evaluate(self, proposal: Proposal) -> tuple[Verdict, tuple[str, ...]]:
        """Evaluate a proposal against this rule."""
        return self.evaluator(proposal)


class RuleSet:
    """An ordered collection of rules evaluated sequentially.

    Evaluation stops at the first matching rule. If no rule matches,
    the fail-closed principle applies — the action is denied.
    """

    def __init__(self, name: str, rules: tuple[Rule, ...] = ()) -> None:
        self._name = name
        self._rules: list[Rule] = list(rules)

    @property
    def name(self) -> str:
        return self._name

    @property
    def rules(self) -> tuple[Rule, ...]:
        return tuple(self._rules)

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the set."""
        self._rules.append(rule)

    def find_matching(self, action: str) -> Rule | None:
        """Find the first rule matching the given action."""
        for rule in self._rules:
            if rule.matches(action):
                return rule
        return None

    def __len__(self) -> int:
        return len(self._rules)

    def __repr__(self) -> str:
        return f"RuleSet(name={self._name!r}, rules={len(self._rules)})"


class RuleRegistry:
    """Global registry of rule sets, organized by domain.

    Principle 10 — Meta-governance: explicit hierarchy.
    Rule sets are registered by domain and evaluated in priority order.
    """

    def __init__(self) -> None:
        self._domains: dict[str, RuleSet] = {}
        self._priority: list[str] = []

    def register(self, domain: str, rule_set: RuleSet, priority: int | None = None) -> None:
        """Register a rule set for a domain.

        Args:
            domain: The domain name (e.g., 'document_management', 'deployment').
            rule_set: The set of rules to register.
            priority: Optional priority index. Lower = evaluated first.
        """
        self._domains[domain] = rule_set
        if domain not in self._priority:
            if priority is not None and 0 <= priority <= len(self._priority):
                self._priority.insert(priority, domain)
            else:
                self._priority.append(domain)

    def find_rule(self, action: str) -> tuple[str, Rule] | None:
        """Find the first matching rule across all domains, in priority order.

        Returns:
            A tuple of (domain, rule) if found, None otherwise.
        """
        for domain_name in self._priority:
            rule_set = self._domains[domain_name]
            rule = rule_set.find_matching(action)
            if rule is not None:
                return (domain_name, rule)
        return None

    @property
    def domains(self) -> tuple[str, ...]:
        """Return domain names in priority order."""
        return tuple(self._priority)

    def get_domain(self, domain: str) -> RuleSet | None:
        """Get a rule set by domain name."""
        return self._domains.get(domain)

    def __len__(self) -> int:
        return len(self._domains)

    def __repr__(self) -> str:
        return f"RuleRegistry(domains={self._priority})"


# --- Built-in rule evaluators ---


def require_owner(proposal: Proposal) -> tuple[Verdict, tuple[str, ...]]:
    """Principle 7 — Ownership: reject proposals without an owner."""
    if not proposal.owner:
        return (Verdict.DENIED, ("Proposal has no owner. Principle 7 requires ownership.",))
    return (Verdict.APPROVED, ("Owner verified.",))


def require_human_approval(proposal: Proposal) -> tuple[Verdict, tuple[str, ...]]:
    """Principle 6 — Human-in-the-loop: flag proposals needing human confirmation."""
    if proposal.requires_human_approval:
        return (
            Verdict.PENDING_HUMAN_APPROVAL,
            ("Action requires human confirmation before execution.",),
        )
    return (Verdict.APPROVED, ("No human approval required for this action.",))


def deny_unacceptable_risk(proposal: Proposal) -> tuple[Verdict, tuple[str, ...]]:
    """EU AI Act: deny actions classified as unacceptable risk."""
    risk = proposal.metadata.get("risk_level", "")
    if risk == RiskLevel.UNACCEPTABLE.value or risk == RiskLevel.UNACCEPTABLE:
        return (
            Verdict.DENIED,
            ("Action classified as UNACCEPTABLE risk under EU AI Act. Blocked.",),
        )
    return (Verdict.APPROVED, ("Risk level acceptable.",))


@dataclass(frozen=True)
class ForbiddenZoneEvaluator:
    """Principle 4 — Forbidden Zones: deny writes to protected areas.

    This is a callable dataclass — it holds configuration (the set of
    forbidden zones) and evaluates proposals as a function.
    """

    zones: frozenset[str] = field(default_factory=frozenset)

    def __call__(self, proposal: Proposal) -> tuple[Verdict, tuple[str, ...]]:
        target = proposal.target
        for zone in self.zones:
            if target.startswith(zone) or target == zone:
                return (
                    Verdict.DENIED,
                    (f"Target {target!r} is in forbidden zone {zone!r}.",),
                )
        return (Verdict.APPROVED, ("Target is not in a forbidden zone.",))


def require_override_reason(proposal: Proposal) -> tuple[Verdict, tuple[str, ...]]:
    """Principle 5 — Evidence, not persuasion: override reasons must be documented.

    Prevents silent override — when a human overrides an AI recommendation
    without documenting why, the feedback loop is corrupted.
    """
    is_override = proposal.metadata.get("override", False)
    override_reason = proposal.metadata.get("override_reason", "")
    if is_override and not override_reason:
        return (
            Verdict.DENIED,
            ("Override requires a documented reason. Silent overrides violate Principle 5.",),
        )
    return (Verdict.APPROVED, ("Override reason verified.",))
