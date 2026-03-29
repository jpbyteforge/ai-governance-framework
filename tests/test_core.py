"""Tests for GovernanceEngine — the central orchestrator."""

import pytest

from governance.core import GovernanceEngine, Principle
from governance.decisions import Proposal, Verdict
from governance.exceptions import NoRuleError, OwnershipError
from governance.rules import Rule, RuleRegistry, RuleSet, require_owner


@pytest.fixture
def basic_registry() -> RuleRegistry:
    """Registry with a simple approve-all rule for 'read' actions."""
    registry = RuleRegistry()
    rule_set = RuleSet(
        name="basic",
        rules=(
            Rule(
                name="allow_read",
                description="Allow all read operations",
                principles=("regulated_component",),
                actions=frozenset({"read"}),
                evaluator=lambda p: (Verdict.APPROVED, ("Read operations are permitted.",)),
            ),
            Rule(
                name="ownership_check",
                description="Verify ownership on write operations",
                principles=("ownership",),
                actions=frozenset({"write"}),
                evaluator=require_owner,
            ),
        ),
    )
    registry.register("basic", rule_set)
    return registry


@pytest.fixture
def engine(basic_registry: RuleRegistry) -> GovernanceEngine:
    return GovernanceEngine(registry=basic_registry)


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


class TestGovernanceEngine:
    def test_approved_proposal(self, engine: GovernanceEngine) -> None:
        proposal = make_proposal(action="read")
        decision = engine.evaluate(proposal)

        assert decision.is_approved
        assert decision.verdict == Verdict.APPROVED
        assert len(decision.reasons) > 0

    def test_fail_closed_unknown_action(self, engine: GovernanceEngine) -> None:
        proposal = make_proposal(action="delete")

        with pytest.raises(NoRuleError) as exc_info:
            engine.evaluate(proposal)

        assert "delete" in str(exc_info.value)
        assert exc_info.value.principle == "determinism"

    def test_ownership_required(self, engine: GovernanceEngine) -> None:
        proposal = make_proposal(action="write", owner="")

        with pytest.raises(OwnershipError):
            engine.evaluate(proposal)

    def test_audit_trail_records_decisions(self, engine: GovernanceEngine) -> None:
        proposal = make_proposal(action="read")
        engine.evaluate(proposal)

        assert len(engine.audit) == 1
        entry = engine.audit.entries[0]
        assert entry.event_type == "decision"
        assert entry.outcome == "approved"

    def test_audit_trail_records_violations(self, engine: GovernanceEngine) -> None:
        proposal = make_proposal(action="delete")

        with pytest.raises(NoRuleError):
            engine.evaluate(proposal)

        assert len(engine.audit) == 1
        entry = engine.audit.entries[0]
        assert entry.event_type == "violation"
        assert entry.outcome == "denied"

    def test_record_execution(self, engine: GovernanceEngine) -> None:
        proposal = make_proposal(action="read")
        decision = engine.evaluate(proposal)
        result = engine.record_execution(decision, success=True, output="File read OK")

        assert result.success
        assert result.output == "File read OK"
        assert len(engine.audit) == 2  # decision + execution

    def test_denied_proposal_with_owner(self, engine: GovernanceEngine) -> None:
        """A proposal with owner but for a rule that denies it."""
        # 'write' action goes to ownership_check which uses require_owner
        proposal = make_proposal(action="write", owner="jorge.pessoa")
        decision = engine.evaluate(proposal)
        assert decision.is_approved  # has owner, so approved


class TestPrinciple:
    def test_all_principles_have_descriptions(self) -> None:
        for principle in Principle:
            assert principle.description, f"{principle.name} has no description"

    def test_principle_count(self) -> None:
        assert len(Principle) == 10
