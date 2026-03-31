"""Tests for the AI Readiness Gate (governance.scoring)."""

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
from governance.scoring import (
    ReadinessGate,
    ReadinessGateConfig,
    ReadinessGateResult,
    ReadinessStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    *,
    influenced: bool = True,
    reproducible: bool = True,
    outcome_value: float | None = None,
) -> AIDecisionRecord:
    """Build an AIDecisionRecord with controllable scoring properties."""
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
        final_decision="reject", override=True, override_reason="test override"
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


def _make_records(
    n: int,
    *,
    influenced: bool = True,
    reproducible: bool = True,
    outcome_value: float | None = None,
) -> tuple[AIDecisionRecord, ...]:
    return tuple(
        _make_record(
            influenced=influenced, reproducible=reproducible, outcome_value=outcome_value
        )
        for _ in range(n)
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReadinessGate:
    def test_all_four_pass_returns_ok(self) -> None:
        """4/4 tests passing → OK status, action=scale_permitted."""
        gate = ReadinessGate()
        records = _make_records(4, influenced=True, reproducible=True, outcome_value=1.0)
        result = gate.evaluate(records, baseline_impact=0.5, previous_impact=None, cycle_id="c1")

        assert result.status == ReadinessStatus.OK
        assert result.passed_count == 4
        assert result.recommended_action == "scale_permitted"

    def test_three_pass_returns_degraded(self) -> None:
        """3/4 tests passing → DEGRADED status, action=enhanced_monitoring."""
        gate = ReadinessGate()
        # direction fails: 0 influenced → 0% (threshold 30%)
        records = _make_records(4, influenced=False, reproducible=True, outcome_value=1.0)
        result = gate.evaluate(records, baseline_impact=0.5, previous_impact=None, cycle_id="c1")

        assert result.status == ReadinessStatus.DEGRADED
        assert result.passed_count == 3
        assert result.recommended_action == "enhanced_monitoring"

    def test_two_pass_returns_critical(self) -> None:
        """<=2 tests passing → CRITICAL status, action=automatic_downgrade."""
        gate = ReadinessGate()
        # direction fails (0% influenced), impact fails (outcome 0.0 <= baseline 0.5)
        records = _make_records(4, influenced=False, reproducible=True, outcome_value=0.0)
        result = gate.evaluate(records, baseline_impact=0.5, previous_impact=None, cycle_id="c1")

        assert result.status == ReadinessStatus.CRITICAL
        assert result.passed_count <= 2
        assert result.recommended_action == "automatic_downgrade"

    def test_direction_test_threshold(self) -> None:
        """Below 30% influenced decisions → direction test fails."""
        gate = ReadinessGate()
        # 1 influenced out of 4 = 25% < 30%
        records = (
            _make_record(influenced=True),
            _make_record(influenced=False),
            _make_record(influenced=False),
            _make_record(influenced=False),
        )
        result = gate.evaluate(
            records, baseline_impact=0.0, previous_impact=None, cycle_id="c1"
        )
        direction = next(t for t in result.tests if t.name == "direction")

        assert not direction.passed
        assert direction.measured_value == pytest.approx(0.25)

    def test_truth_test_threshold(self) -> None:
        """Below 95% reproducible decisions → truth test fails."""
        gate = ReadinessGate()
        # 3 reproducible out of 4 = 75% < 95%
        records = (
            _make_record(reproducible=True),
            _make_record(reproducible=True),
            _make_record(reproducible=True),
            _make_record(reproducible=False),
        )
        result = gate.evaluate(
            records, baseline_impact=0.0, previous_impact=None, cycle_id="c1"
        )
        truth = next(t for t in result.tests if t.name == "truth")

        assert not truth.passed
        assert truth.measured_value == pytest.approx(0.75)

    def test_impact_test_positive_delta(self) -> None:
        """Mean outcome above baseline → impact test passes."""
        gate = ReadinessGate()
        records = _make_records(4, outcome_value=1.0)
        result = gate.evaluate(records, baseline_impact=0.5, previous_impact=None, cycle_id="c1")
        impact = next(t for t in result.tests if t.name == "impact")

        assert impact.passed
        assert impact.measured_value == pytest.approx(0.5)

    def test_impact_test_zero_delta_fails(self) -> None:
        """Zero improvement over baseline → impact test fails (delta must be > 0)."""
        gate = ReadinessGate()
        records = _make_records(4, outcome_value=0.5)
        result = gate.evaluate(records, baseline_impact=0.5, previous_impact=None, cycle_id="c1")
        impact = next(t for t in result.tests if t.name == "impact")

        assert not impact.passed
        assert impact.measured_value == pytest.approx(0.0)

    def test_marginal_value_first_cycle_passes(self) -> None:
        """previous_impact=None (first cycle) → marginal_value test always passes."""
        gate = ReadinessGate()
        records = _make_records(4, outcome_value=0.5)
        result = gate.evaluate(records, baseline_impact=0.5, previous_impact=None, cycle_id="c1")
        mv = next(t for t in result.tests if t.name == "marginal_value")

        assert mv.passed

    def test_marginal_value_no_improvement_fails(self) -> None:
        """Same or lower outcome than previous cycle → marginal_value fails."""
        gate = ReadinessGate()
        records = _make_records(4, outcome_value=0.5)
        result = gate.evaluate(
            records, baseline_impact=0.0, previous_impact=0.5, cycle_id="c1"
        )
        mv = next(t for t in result.tests if t.name == "marginal_value")

        assert not mv.passed

    def test_continuity_flag_after_two_consecutive_failing_cycles(self) -> None:
        """Two consecutive cycles with failing impact → continuity_flag=True."""
        gate = ReadinessGate()
        # Both cycles: outcome_value=0.0 <= baseline 0.5 → impact fails
        records = _make_records(4, outcome_value=0.0)
        gate.evaluate(records, baseline_impact=0.5, previous_impact=None, cycle_id="c1")
        result2 = gate.evaluate(
            records, baseline_impact=0.5, previous_impact=0.5, cycle_id="c2"
        )

        assert result2.continuity_flag is True

    def test_continuity_flag_not_set_after_one_cycle(self) -> None:
        """A single failing cycle does not trigger the continuity flag."""
        gate = ReadinessGate()
        records = _make_records(4, outcome_value=0.0)
        result = gate.evaluate(records, baseline_impact=0.5, previous_impact=None, cycle_id="c1")

        assert result.continuity_flag is False

    def test_gate_result_is_frozen(self) -> None:
        """ReadinessGateResult is a frozen dataclass."""
        gate = ReadinessGate()
        records = _make_records(4, outcome_value=1.0)
        result = gate.evaluate(records, baseline_impact=0.5, previous_impact=None, cycle_id="c1")

        with pytest.raises(dataclasses.FrozenInstanceError):
            result.status = ReadinessStatus.CRITICAL  # type: ignore[misc]
