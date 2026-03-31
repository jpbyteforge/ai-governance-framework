"""Tests for compute_metrics and MetricsSnapshot (governance.metrics)."""

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
from governance.metrics import MetricsSnapshot, compute_metrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    *,
    influenced: bool = True,
    reproducible: bool = True,
    outcome_value: float | None = None,
) -> AIDecisionRecord:
    proposal = Proposal(
        action="read",
        target="/data/file.txt",
        rationale="test",
        proposed_by="agent",
        owner="owner",
    )
    decision = Decision(
        proposal=proposal,
        verdict=Verdict.APPROVED,
        reasons=("ok",),
        decided_by="rule",
        authority="registry",
    )
    action_result = ActionResult(decision=decision, success=True)

    human = None if influenced else HumanDecisionRecord(
        final_decision="reject", override=True, override_reason="override"
    )
    outcome = OutcomeRecord(observed_result=outcome_value) if outcome_value is not None else None

    return AIDecisionRecord(
        action_result=action_result,
        context=DecisionContext(
            decision_type=DecisionType.ASSISTED,
            cost_of_error=CostLevel.LOW,
            cost_of_latency=CostLevel.LOW,
        ),
        input_tracking=InputTracking(data_version="v1", features_hash="hash"),
        model_tracking=ModelTracking(model_id="m1", model_version="1.0"),
        recommendation=AIRecommendation(output="go", confidence=0.9),
        human_decision=human,
        outcome=outcome,
        reproducible=reproducible,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    def test_empty_records_returns_none_rates(self) -> None:
        """With no records, all rate fields are None."""
        snapshot = compute_metrics(())

        assert snapshot.total_decisions == 0
        assert snapshot.decision_impact_rate is None
        assert snapshot.override_rate is None
        assert snapshot.reproducibility_rate is None
        assert snapshot.outcome_delta is None

    def test_impact_rate_all_influenced(self) -> None:
        """When all records are influenced (no override) the impact rate is 1.0."""
        records = tuple(_make_record(influenced=True) for _ in range(4))
        snapshot = compute_metrics(records)

        assert snapshot.decision_impact_rate == pytest.approx(1.0)

    def test_impact_rate_half_overridden(self) -> None:
        """50% influenced, 50% overridden → impact_rate=0.5, override_rate=0.5."""
        records = (
            _make_record(influenced=True),
            _make_record(influenced=True),
            _make_record(influenced=False),
            _make_record(influenced=False),
        )
        snapshot = compute_metrics(records)

        assert snapshot.decision_impact_rate == pytest.approx(0.5)
        assert snapshot.override_rate == pytest.approx(0.5)

    def test_reproducibility_rate(self) -> None:
        """3 reproducible out of 4 → reproducibility_rate = 0.75."""
        records = (
            _make_record(reproducible=True),
            _make_record(reproducible=True),
            _make_record(reproducible=True),
            _make_record(reproducible=False),
        )
        snapshot = compute_metrics(records)

        assert snapshot.reproducibility_rate == pytest.approx(0.75)

    def test_override_rate_calculation(self) -> None:
        """Explicit override count drives override_rate."""
        records = (
            _make_record(influenced=False),  # overridden
            _make_record(influenced=True),
            _make_record(influenced=True),
            _make_record(influenced=True),
        )
        snapshot = compute_metrics(records)

        assert snapshot.override_rate == pytest.approx(0.25)

    def test_outcome_delta_with_baseline(self) -> None:
        """Numeric outcomes minus mean baseline gives the correct delta."""
        records = tuple(_make_record(outcome_value=1.0) for _ in range(4))
        baseline = (0.5, 0.5, 0.5, 0.5)
        snapshot = compute_metrics(records, baseline_values=baseline)

        # mean outcome = 1.0, mean baseline = 0.5 → delta = 0.5
        assert snapshot.outcome_delta == pytest.approx(0.5)

    def test_outcome_delta_none_when_no_outcomes(self) -> None:
        """outcome_delta is None when records carry no numeric outcomes."""
        records = tuple(_make_record(outcome_value=None) for _ in range(3))
        snapshot = compute_metrics(records, baseline_values=(0.5, 0.5))

        assert snapshot.outcome_delta is None

    def test_metrics_snapshot_is_frozen(self) -> None:
        """MetricsSnapshot is a frozen dataclass — assignment raises FrozenInstanceError."""
        snapshot = compute_metrics(())

        with pytest.raises(dataclasses.FrozenInstanceError):
            snapshot.total_decisions = 99  # type: ignore[misc]
