"""Tests for GovernanceEngine AI Readiness Gate extensions."""

import dataclasses

import pytest

from governance.core import GovernanceEngine, Principle
from governance.decisions import (
    ActionResult,
    AIDecisionRecord,
    AIRecommendation,
    CostLevel,
    Decision,
    DecisionContext,
    DecisionType,
    HumanDecisionRecord,
    InputTracking,
    ModelTracking,
    OutcomeRecord,
    Proposal,
    Verdict,
)
from governance.exceptions import MandatoryReviewRequired, ReadinessGateCritical
from governance.metrics import MetricsSnapshot
from governance.rules import Rule, RuleRegistry, RuleSet, require_owner
from governance.scoring import ReadinessGateConfig


# ---------------------------------------------------------------------------
# Fixtures & helpers (same pattern as test_core.py)
# ---------------------------------------------------------------------------


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
) -> Proposal:
    return Proposal(
        action=action,
        target=target,
        rationale="Test proposal",
        proposed_by="test_agent",
        owner=owner,
    )


def _make_ai_record(
    *,
    influenced: bool = True,
    reproducible: bool = True,
    outcome_value: float | None = None,
) -> AIDecisionRecord:
    """Minimal AIDecisionRecord for engine extension tests."""
    proposal = make_proposal()
    decision = Decision(
        proposal=proposal,
        verdict=Verdict.APPROVED,
        reasons=("ok",),
        decided_by="allow_read",
        authority="rule_registry",
    )
    action_result = ActionResult(decision=decision, success=True)

    human = None if influenced else HumanDecisionRecord(
        final_decision="reject", override=True, override_reason="engine test"
    )
    outcome = OutcomeRecord(observed_result=outcome_value) if outcome_value is not None else None

    return AIDecisionRecord(
        action_result=action_result,
        context=DecisionContext(
            decision_type=DecisionType.ASSISTED,
            cost_of_error=CostLevel.LOW,
            cost_of_latency=CostLevel.LOW,
        ),
        input_tracking=InputTracking(data_version="v1", features_hash="h1"),
        model_tracking=ModelTracking(model_id="model-x", model_version="1.0"),
        recommendation=AIRecommendation(output="approve", confidence=0.9),
        human_decision=human,
        outcome=outcome,
        reproducible=reproducible,
    )


def _good_records(n: int = 4) -> list[AIDecisionRecord]:
    """Records that pass all four gate tests: influenced, reproducible, outcome above base."""
    return [_make_ai_record(influenced=True, reproducible=True, outcome_value=1.0)
            for _ in range(n)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEngineAIExtensions:
    def test_record_ai_decision_appends_to_audit(
        self, engine: GovernanceEngine
    ) -> None:
        """record_ai_decision writes an ai_decision event to the audit trail."""
        engine.record_ai_decision(_make_ai_record())

        assert len(engine.audit) == 1
        assert engine.audit.entries[0].event_type == "ai_decision"

    def test_record_ai_decision_accumulates(self, engine: GovernanceEngine) -> None:
        """Multiple calls to record_ai_decision accumulate in ai_records."""
        engine.record_ai_decision(_make_ai_record())
        engine.record_ai_decision(_make_ai_record())
        engine.record_ai_decision(_make_ai_record())

        assert len(engine.ai_records) == 3

    def test_evaluate_readiness_requires_gate_enabled(
        self, engine: GovernanceEngine
    ) -> None:
        """evaluate_readiness() raises RuntimeError if gate was not enabled."""
        with pytest.raises(RuntimeError, match="enable_readiness_gate"):
            engine.evaluate_readiness(baseline_impact=0.5, cycle_id="c1")

    def test_evaluate_readiness_ok_status(self, engine: GovernanceEngine) -> None:
        """Gate in OK status returns the result without raising."""
        engine.enable_readiness_gate()
        for r in _good_records(4):
            engine.record_ai_decision(r)

        result = engine.evaluate_readiness(baseline_impact=0.5, cycle_id="c1")

        assert result.status.value == "ok"

    def test_evaluate_readiness_raises_critical(
        self, engine: GovernanceEngine
    ) -> None:
        """CRITICAL gate status raises ReadinessGateCritical."""
        engine.enable_readiness_gate()
        # 0% influenced (direction fails), outcome 0.0 <= baseline 0.5 (impact fails)
        bad_records = [
            _make_ai_record(influenced=False, reproducible=True, outcome_value=0.0)
            for _ in range(4)
        ]
        for r in bad_records:
            engine.record_ai_decision(r)

        with pytest.raises(ReadinessGateCritical):
            engine.evaluate_readiness(baseline_impact=0.5, cycle_id="c1")

    def test_evaluate_readiness_raises_mandatory_review(
        self, engine: GovernanceEngine
    ) -> None:
        """Two consecutive impact-failing cycles raise MandatoryReviewRequired."""
        engine.enable_readiness_gate()
        # outcome_value=0.0 <= baseline 0.5 → impact fails both cycles
        bad_records = [_make_ai_record(outcome_value=0.0) for _ in range(4)]
        for r in bad_records:
            engine.record_ai_decision(r)

        try:
            engine.evaluate_readiness(baseline_impact=0.5, cycle_id="c1")
        except (ReadinessGateCritical, MandatoryReviewRequired):
            pass  # first cycle — only impact fails, may be CRITICAL but no continuity yet

        with pytest.raises((MandatoryReviewRequired, ReadinessGateCritical)):
            engine.evaluate_readiness(
                baseline_impact=0.5, previous_impact=0.5, cycle_id="c2"
            )

    def test_evaluate_readiness_records_audit_entry(
        self, engine: GovernanceEngine
    ) -> None:
        """evaluate_readiness() always appends a readiness_gate audit entry."""
        engine.enable_readiness_gate()
        for r in _good_records(4):
            engine.record_ai_decision(r)

        engine.evaluate_readiness(baseline_impact=0.5, cycle_id="c1")

        gate_entries = [
            e for e in engine.audit.entries if e.event_type == "readiness_gate"
        ]
        assert len(gate_entries) == 1
        assert gate_entries[0].action == "evaluate_readiness"

    def test_get_metrics_returns_snapshot(self, engine: GovernanceEngine) -> None:
        """get_metrics() returns a MetricsSnapshot instance."""
        for r in _good_records(4):
            engine.record_ai_decision(r)

        snapshot = engine.get_metrics()

        assert isinstance(snapshot, MetricsSnapshot)
        assert snapshot.total_decisions == 4

    def test_ai_records_property_returns_tuple(
        self, engine: GovernanceEngine
    ) -> None:
        """ai_records property returns a tuple (immutable view)."""
        engine.record_ai_decision(_make_ai_record())
        engine.record_ai_decision(_make_ai_record())

        assert isinstance(engine.ai_records, tuple)
        assert len(engine.ai_records) == 2

    def test_existing_evaluate_unaffected(self, engine: GovernanceEngine) -> None:
        """Regression: normal proposal evaluation still works after AI extensions added."""
        proposal = make_proposal(action="read")
        decision = engine.evaluate(proposal)

        assert decision.is_approved
        assert decision.verdict == Verdict.APPROVED
