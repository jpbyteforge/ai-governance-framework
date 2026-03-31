"""AI Readiness Gate — continuous scoring for AI system health.

A system scales only if it passes 4 tests:
1. Direction: AI influences real decisions (>= 30%)
2. Truth: decisions are reproducible (>= 95%)
3. Impact: improvement versus baseline (> 0)
4. Marginal Value: incremental gain per cycle (> 0)

Scoring: 4/4 OK, 3/4 DEGRADED, <=2/4 CRITICAL.
Continuity: 2 consecutive failing cycles -> mandatory review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from governance.decisions import AIDecisionRecord


class ReadinessStatus(Enum):
    """Overall readiness gate outcome."""

    OK = "ok"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass(frozen=True)
class GateTestResult:
    """Result of a single readiness gate test."""

    name: str
    passed: bool
    measured_value: float
    threshold: float
    details: str


@dataclass(frozen=True)
class ReadinessGateConfig:
    """Configurable thresholds for the readiness gate."""

    direction_threshold: float = 0.30
    truth_threshold: float = 0.95
    impact_min_delta: float = 0.0
    marginal_value_min_delta: float = 0.0


@dataclass(frozen=True)
class ReadinessGateResult:
    """Full result of a readiness gate evaluation cycle."""

    status: ReadinessStatus
    tests: tuple[GateTestResult, ...]
    passed_count: int
    cycle_id: str
    evaluated_at: datetime
    continuity_flag: bool
    recommended_action: str

    @property
    def is_ok(self) -> bool:
        return self.status == ReadinessStatus.OK


class ReadinessGate:
    """AI Readiness Gate: evaluates AI system health across 4 tests.

    Stateless with respect to records — caller passes in the records.
    Stateful only for continuity tracking (consecutive failing cycles).
    """

    def __init__(self, config: ReadinessGateConfig | None = None) -> None:
        self._config = config or ReadinessGateConfig()
        self._cycle_history: list[ReadinessGateResult] = []

    def evaluate(
        self,
        records: tuple[AIDecisionRecord, ...],
        baseline_impact: float,
        previous_impact: float | None,
        cycle_id: str,
    ) -> ReadinessGateResult:
        """Run all 4 gate tests and return the aggregate result."""
        tests = (
            self._test_direction(records),
            self._test_truth(records),
            self._test_impact(records, baseline_impact),
            self._test_marginal_value(records, previous_impact),
        )

        passed_count = sum(1 for t in tests if t.passed)
        status = self._determine_status(passed_count)
        continuity_flag = self._check_continuity(tests)

        result = ReadinessGateResult(
            status=status,
            tests=tests,
            passed_count=passed_count,
            cycle_id=cycle_id,
            evaluated_at=datetime.now(timezone.utc),
            continuity_flag=continuity_flag,
            recommended_action=self._recommended_action(
                status, continuity_flag
            ),
        )
        self._cycle_history.append(result)
        return result

    def _test_direction(
        self, records: tuple[AIDecisionRecord, ...]
    ) -> GateTestResult:
        """Direction Test: % decisions influenced by AI >= threshold."""
        total = len(records)
        if total == 0:
            return GateTestResult(
                name="direction",
                passed=False,
                measured_value=0.0,
                threshold=self._config.direction_threshold,
                details="No records to evaluate.",
            )
        influenced = sum(1 for r in records if r.influenced_decision)
        rate = influenced / total
        return GateTestResult(
            name="direction",
            passed=rate >= self._config.direction_threshold,
            measured_value=rate,
            threshold=self._config.direction_threshold,
            details=f"{influenced}/{total} decisions influenced.",
        )

    def _test_truth(
        self, records: tuple[AIDecisionRecord, ...]
    ) -> GateTestResult:
        """Truth Test: % reproducible decisions >= threshold."""
        total = len(records)
        if total == 0:
            return GateTestResult(
                name="truth",
                passed=False,
                measured_value=0.0,
                threshold=self._config.truth_threshold,
                details="No records to evaluate.",
            )
        reproducible = sum(1 for r in records if r.reproducible)
        rate = reproducible / total
        return GateTestResult(
            name="truth",
            passed=rate >= self._config.truth_threshold,
            measured_value=rate,
            threshold=self._config.truth_threshold,
            details=f"{reproducible}/{total} decisions reproducible.",
        )

    def _test_impact(
        self,
        records: tuple[AIDecisionRecord, ...],
        baseline_impact: float,
    ) -> GateTestResult:
        """Impact Test: improvement versus baseline > 0."""
        outcomes: list[float] = []
        for r in records:
            if r.outcome is not None and isinstance(
                r.outcome.observed_result, (int, float)
            ):
                outcomes.append(float(r.outcome.observed_result))

        if not outcomes:
            return GateTestResult(
                name="impact",
                passed=False,
                measured_value=0.0,
                threshold=self._config.impact_min_delta,
                details="No measurable outcomes.",
            )

        mean_outcome = sum(outcomes) / len(outcomes)
        delta = mean_outcome - baseline_impact
        return GateTestResult(
            name="impact",
            passed=delta > self._config.impact_min_delta,
            measured_value=delta,
            threshold=self._config.impact_min_delta,
            details=f"Mean outcome {mean_outcome:.4f} vs baseline "
            f"{baseline_impact:.4f}, delta={delta:.4f}.",
        )

    def _test_marginal_value(
        self,
        records: tuple[AIDecisionRecord, ...],
        previous_impact: float | None,
    ) -> GateTestResult:
        """Marginal Value Test: incremental gain versus previous cycle > 0."""
        if previous_impact is None:
            return GateTestResult(
                name="marginal_value",
                passed=True,
                measured_value=0.0,
                threshold=self._config.marginal_value_min_delta,
                details="First cycle — marginal value assumed positive.",
            )

        outcomes: list[float] = []
        for r in records:
            if r.outcome is not None and isinstance(
                r.outcome.observed_result, (int, float)
            ):
                outcomes.append(float(r.outcome.observed_result))

        if not outcomes:
            return GateTestResult(
                name="marginal_value",
                passed=False,
                measured_value=0.0,
                threshold=self._config.marginal_value_min_delta,
                details="No measurable outcomes for marginal comparison.",
            )

        mean_outcome = sum(outcomes) / len(outcomes)
        delta = mean_outcome - previous_impact
        return GateTestResult(
            name="marginal_value",
            passed=delta > self._config.marginal_value_min_delta,
            measured_value=delta,
            threshold=self._config.marginal_value_min_delta,
            details=f"Current {mean_outcome:.4f} vs previous "
            f"{previous_impact:.4f}, gain={delta:.4f}.",
        )

    def _check_continuity(
        self, current_tests: tuple[GateTestResult, ...]
    ) -> bool:
        """Return True if 2 consecutive cycles have impact or marginal_value failing."""
        if len(self._cycle_history) < 1:
            return False

        previous = self._cycle_history[-1]
        prev_tests = {t.name: t.passed for t in previous.tests}
        curr_tests = {t.name: t.passed for t in current_tests}

        impact_failing = (
            not prev_tests.get("impact", True)
            and not curr_tests.get("impact", True)
        )
        marginal_failing = (
            not prev_tests.get("marginal_value", True)
            and not curr_tests.get("marginal_value", True)
        )
        return impact_failing or marginal_failing

    @staticmethod
    def _determine_status(passed_count: int) -> ReadinessStatus:
        if passed_count == 4:
            return ReadinessStatus.OK
        if passed_count == 3:
            return ReadinessStatus.DEGRADED
        return ReadinessStatus.CRITICAL

    @staticmethod
    def _recommended_action(
        status: ReadinessStatus, continuity_flag: bool
    ) -> str:
        if continuity_flag:
            return "mandatory_review"
        match status:
            case ReadinessStatus.OK:
                return "scale_permitted"
            case ReadinessStatus.DEGRADED:
                return "enhanced_monitoring"
            case ReadinessStatus.CRITICAL:
                return "automatic_downgrade"

    @property
    def cycle_history(self) -> tuple[ReadinessGateResult, ...]:
        return tuple(self._cycle_history)
