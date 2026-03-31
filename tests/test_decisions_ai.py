"""Tests for AI decision dataclasses introduced in governance.decisions."""

import dataclasses

import pytest

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


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


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


def make_decision(proposal: Proposal | None = None) -> Decision:
    p = proposal or make_proposal()
    return Decision(
        proposal=p,
        verdict=Verdict.APPROVED,
        reasons=("Allowed by rule.",),
        decided_by="allow_read",
        authority="rule_registry",
    )


def make_action_result(decision: Decision | None = None) -> ActionResult:
    d = decision or make_decision()
    return ActionResult(decision=d, success=True, output="ok")


@pytest.fixture
def ai_record() -> AIDecisionRecord:
    """A minimal valid AIDecisionRecord for use across tests."""
    return AIDecisionRecord(
        action_result=make_action_result(),
        context=DecisionContext(
            decision_type=DecisionType.ASSISTED,
            cost_of_error=CostLevel.MEDIUM,
            cost_of_latency=CostLevel.LOW,
        ),
        input_tracking=InputTracking(
            data_version="v1.0",
            features_hash="abc123",
            source_ids=("src-1", "src-2"),
        ),
        model_tracking=ModelTracking(
            model_id="model-x",
            model_version="1.0.0",
        ),
        recommendation=AIRecommendation(output="approve", confidence=0.87),
        reproducible=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAIDecisionRecord:
    def test_ai_decision_record_is_immutable(self, ai_record: AIDecisionRecord) -> None:
        """Assigning to any field on a frozen dataclass raises FrozenInstanceError."""
        with pytest.raises(dataclasses.FrozenInstanceError):
            ai_record.reproducible = False  # type: ignore[misc]

    def test_with_outcome_returns_new_record(self, ai_record: AIDecisionRecord) -> None:
        """with_outcome() returns a different object; original is unchanged."""
        outcome = OutcomeRecord(observed_result=0.95)
        updated = ai_record.with_outcome(outcome)

        assert updated is not ai_record
        assert updated.outcome == outcome
        assert ai_record.outcome is None

    def test_with_human_decision_returns_new_record(
        self, ai_record: AIDecisionRecord
    ) -> None:
        """with_human_decision() returns a different object; original is unchanged."""
        human = HumanDecisionRecord(final_decision="approve", override=False)
        updated = ai_record.with_human_decision(human)

        assert updated is not ai_record
        assert updated.human_decision == human
        assert ai_record.human_decision is None

    def test_influenced_decision_when_no_human(self, ai_record: AIDecisionRecord) -> None:
        """influenced_decision is True when human_decision is None (AI accepted)."""
        assert ai_record.human_decision is None
        assert ai_record.influenced_decision is True

    def test_not_influenced_when_overridden(self, ai_record: AIDecisionRecord) -> None:
        """influenced_decision is False when the human set override=True."""
        human = HumanDecisionRecord(
            final_decision="reject", override=True, override_reason="Policy change"
        )
        overridden = ai_record.with_human_decision(human)

        assert overridden.influenced_decision is False

    def test_was_overridden_false_when_accepted(self, ai_record: AIDecisionRecord) -> None:
        """was_overridden is False when human accepted the AI recommendation."""
        human = HumanDecisionRecord(final_decision="approve", override=False)
        accepted = ai_record.with_human_decision(human)

        assert accepted.was_overridden is False

    def test_decision_context_fields(self) -> None:
        """DecisionContext stores and exposes its three fields correctly."""
        ctx = DecisionContext(
            decision_type=DecisionType.AUTONOMOUS,
            cost_of_error=CostLevel.HIGH,
            cost_of_latency=CostLevel.MEDIUM,
        )

        assert ctx.decision_type == DecisionType.AUTONOMOUS
        assert ctx.cost_of_error == CostLevel.HIGH
        assert ctx.cost_of_latency == CostLevel.MEDIUM

    def test_input_tracking_source_ids_immutable(self) -> None:
        """source_ids is stored as a tuple (immutable sequence)."""
        tracking = InputTracking(
            data_version="v2",
            features_hash="deadbeef",
            source_ids=("a", "b", "c"),
        )

        assert isinstance(tracking.source_ids, tuple)
        assert tracking.source_ids == ("a", "b", "c")

    def test_ai_recommendation_confidence_stored(self) -> None:
        """Confidence value round-trips through AIRecommendation unchanged."""
        rec = AIRecommendation(output="buy", confidence=0.612)

        assert rec.confidence == pytest.approx(0.612)

    def test_cost_level_enum_values(self) -> None:
        """All three CostLevel members exist with expected string values."""
        assert CostLevel.HIGH.value == "high"
        assert CostLevel.MEDIUM.value == "medium"
        assert CostLevel.LOW.value == "low"
