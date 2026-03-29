"""Tests for the fail-closed principle — the core of the governance framework.

Fail-closed means: if there is no explicit rule permitting an action,
the action is denied. This is the opposite of fail-open, where anything
not explicitly forbidden is allowed.
"""

import pytest

from governance.core import GovernanceEngine
from governance.decisions import Proposal, Verdict
from governance.exceptions import ForbiddenZoneError, HumanApprovalRequired, NoRuleError
from governance.rules import (
    ForbiddenZoneEvaluator,
    Rule,
    RuleRegistry,
    RuleSet,
    deny_unacceptable_risk,
    require_human_approval,
)


def make_proposal(
    action: str = "read",
    target: str = "/data/report.txt",
    owner: str = "jorge.pessoa",
    **kwargs: object,
) -> Proposal:
    return Proposal(
        action=action,
        target=target,
        rationale="Test proposal",
        proposed_by="test_agent",
        owner=owner,
        **kwargs,  # type: ignore[arg-type]
    )


class TestFailClosed:
    """The fundamental fail-closed behavior."""

    def test_no_rules_means_everything_denied(self) -> None:
        """With an empty registry, ALL actions are denied."""
        engine = GovernanceEngine(registry=RuleRegistry())

        with pytest.raises(NoRuleError):
            engine.evaluate(make_proposal(action="read"))

        with pytest.raises(NoRuleError):
            engine.evaluate(make_proposal(action="write"))

        with pytest.raises(NoRuleError):
            engine.evaluate(make_proposal(action="deploy"))

    def test_only_explicit_actions_permitted(self) -> None:
        """Only actions with matching rules are permitted."""
        registry = RuleRegistry()
        rule_set = RuleSet(
            name="restricted",
            rules=(
                Rule(
                    name="allow_read",
                    description="Only reads allowed",
                    principles=("determinism",),
                    actions=frozenset({"read"}),
                    evaluator=lambda p: (Verdict.APPROVED, ("OK",)),
                ),
            ),
        )
        registry.register("restricted", rule_set)
        engine = GovernanceEngine(registry=registry)

        # read is allowed
        decision = engine.evaluate(make_proposal(action="read"))
        assert decision.is_approved

        # write is denied (no rule)
        with pytest.raises(NoRuleError):
            engine.evaluate(make_proposal(action="write"))

    def test_fail_closed_records_violation(self) -> None:
        """Denied actions are recorded in the audit trail."""
        engine = GovernanceEngine(registry=RuleRegistry())

        with pytest.raises(NoRuleError):
            engine.evaluate(make_proposal(action="deploy"))

        assert len(engine.audit) == 1
        entry = engine.audit.entries[0]
        assert entry.event_type == "violation"
        assert entry.details["principle"] == "determinism"


class TestForbiddenZones:
    """Principle 4 — actions targeting forbidden zones are denied."""

    def test_write_to_forbidden_zone_denied(self) -> None:
        forbidden = ForbiddenZoneEvaluator(zones=frozenset({"/secrets", "/config/production"}))
        registry = RuleRegistry()
        rule_set = RuleSet(
            name="zones",
            rules=(
                Rule(
                    name="zone_check",
                    description="Check forbidden zones",
                    principles=("forbidden_zones",),
                    actions=frozenset({"write", "delete"}),
                    evaluator=forbidden,
                ),
            ),
        )
        registry.register("zones", rule_set)
        engine = GovernanceEngine(registry=registry)

        with pytest.raises(ForbiddenZoneError):
            engine.evaluate(make_proposal(action="write", target="/secrets/api_key.env"))

    def test_write_to_allowed_zone_ok(self) -> None:
        forbidden = ForbiddenZoneEvaluator(zones=frozenset({"/secrets"}))
        registry = RuleRegistry()
        rule_set = RuleSet(
            name="zones",
            rules=(
                Rule(
                    name="zone_check",
                    description="Check forbidden zones",
                    principles=("forbidden_zones",),
                    actions=frozenset({"write"}),
                    evaluator=forbidden,
                ),
            ),
        )
        registry.register("zones", rule_set)
        engine = GovernanceEngine(registry=registry)

        decision = engine.evaluate(make_proposal(action="write", target="/data/report.txt"))
        assert decision.is_approved


class TestHumanInTheLoop:
    """Principle 6 — critical actions require human confirmation."""

    def test_human_approval_required(self) -> None:
        registry = RuleRegistry()
        rule_set = RuleSet(
            name="critical",
            rules=(
                Rule(
                    name="human_check",
                    description="Require human for deploy",
                    principles=("human_in_the_loop",),
                    actions=frozenset({"deploy"}),
                    evaluator=require_human_approval,
                ),
            ),
        )
        registry.register("critical", rule_set)
        engine = GovernanceEngine(registry=registry)

        with pytest.raises(HumanApprovalRequired):
            engine.evaluate(
                make_proposal(action="deploy", requires_human_approval=True)
            )

    def test_non_critical_action_proceeds(self) -> None:
        registry = RuleRegistry()
        rule_set = RuleSet(
            name="critical",
            rules=(
                Rule(
                    name="human_check",
                    description="Check if human needed",
                    principles=("human_in_the_loop",),
                    actions=frozenset({"deploy"}),
                    evaluator=require_human_approval,
                ),
            ),
        )
        registry.register("critical", rule_set)
        engine = GovernanceEngine(registry=registry)

        decision = engine.evaluate(
            make_proposal(action="deploy", requires_human_approval=False)
        )
        assert decision.is_approved


class TestEUAIActRisk:
    """EU AI Act risk classification integration."""

    def test_unacceptable_risk_denied(self) -> None:
        registry = RuleRegistry()
        rule_set = RuleSet(
            name="eu_ai_act",
            rules=(
                Rule(
                    name="risk_check",
                    description="EU AI Act risk classification",
                    principles=("determinism", "regulated_component"),
                    actions=frozenset({"classify", "deploy"}),
                    evaluator=deny_unacceptable_risk,
                ),
            ),
        )
        registry.register("eu_ai_act", rule_set)
        engine = GovernanceEngine(registry=registry)

        proposal = make_proposal(
            action="deploy",
            metadata={"risk_level": "unacceptable"},
        )
        decision = engine.evaluate(proposal)
        assert decision.is_denied

    def test_high_risk_allowed(self) -> None:
        registry = RuleRegistry()
        rule_set = RuleSet(
            name="eu_ai_act",
            rules=(
                Rule(
                    name="risk_check",
                    description="EU AI Act risk classification",
                    principles=("determinism",),
                    actions=frozenset({"deploy"}),
                    evaluator=deny_unacceptable_risk,
                ),
            ),
        )
        registry.register("eu_ai_act", rule_set)
        engine = GovernanceEngine(registry=registry)

        proposal = make_proposal(
            action="deploy",
            metadata={"risk_level": "high"},
        )
        decision = engine.evaluate(proposal)
        assert decision.is_approved


class TestRulePriority:
    """Principle 10 — Meta-governance: rule sets have explicit priority."""

    def test_higher_priority_evaluated_first(self) -> None:
        registry = RuleRegistry()

        # Lower priority (evaluated first) — denies everything
        deny_set = RuleSet(
            name="security",
            rules=(
                Rule(
                    name="deny_all",
                    description="Security: deny all",
                    principles=("determinism",),
                    actions=frozenset({"*"}),
                    evaluator=lambda p: (Verdict.DENIED, ("Security override.",)),
                ),
            ),
        )

        # Higher priority number (evaluated second) — would approve
        allow_set = RuleSet(
            name="operations",
            rules=(
                Rule(
                    name="allow_read",
                    description="Allow reads",
                    principles=("regulated_component",),
                    actions=frozenset({"read"}),
                    evaluator=lambda p: (Verdict.APPROVED, ("OK",)),
                ),
            ),
        )

        registry.register("security", deny_set, priority=0)
        registry.register("operations", allow_set, priority=1)
        engine = GovernanceEngine(registry=registry)

        # Security (priority 0) matches first with wildcard
        decision = engine.evaluate(make_proposal(action="read"))
        assert decision.is_denied
