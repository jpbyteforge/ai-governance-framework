"""Derived governance metrics computed from AI decision records.

Four metrics measure AI system health:
- Decision Impact Rate: how often AI influences real decisions
- Override Rate: how often humans override AI recommendations
- Reproducibility Rate: how many decisions are fully reproducible
- Outcome Delta: improvement versus baseline without AI
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from governance.decisions import AIDecisionRecord


@dataclass(frozen=True)
class MetricsSnapshot:
    """Point-in-time snapshot of AI governance metrics.

    All rates are in range [0.0, 1.0]. None indicates insufficient data.
    """

    total_decisions: int
    decision_impact_rate: float | None
    override_rate: float | None
    reproducibility_rate: float | None
    outcome_delta: float | None
    computed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def compute_metrics(
    records: tuple[AIDecisionRecord, ...],
    baseline_values: tuple[float, ...] | None = None,
) -> MetricsSnapshot:
    """Compute governance metrics from a collection of AI decision records.

    Args:
        records: All AIDecisionRecord objects in the evaluation window.
        baseline_values: Optional baseline outcome values for delta calculation.

    Returns:
        An immutable MetricsSnapshot.
    """
    total = len(records)
    if total == 0:
        return MetricsSnapshot(
            total_decisions=0,
            decision_impact_rate=None,
            override_rate=None,
            reproducibility_rate=None,
            outcome_delta=None,
        )

    influenced = sum(1 for r in records if r.influenced_decision)
    overridden = sum(1 for r in records if r.was_overridden)
    reproducible = sum(1 for r in records if r.reproducible)

    outcome_delta = _compute_outcome_delta(records, baseline_values)

    return MetricsSnapshot(
        total_decisions=total,
        decision_impact_rate=influenced / total,
        override_rate=overridden / total,
        reproducibility_rate=reproducible / total,
        outcome_delta=outcome_delta,
    )


def _compute_outcome_delta(
    records: tuple[AIDecisionRecord, ...],
    baseline_values: tuple[float, ...] | None,
) -> float | None:
    """Compute mean outcome delta versus baseline."""
    outcomes: list[float] = []
    for r in records:
        if r.outcome is not None and isinstance(r.outcome.observed_result, (int, float)):
            outcomes.append(float(r.outcome.observed_result))

    if not outcomes:
        return None
    if baseline_values is None or len(baseline_values) == 0:
        return None

    mean_outcome = sum(outcomes) / len(outcomes)
    mean_baseline = sum(baseline_values) / len(baseline_values)
    return mean_outcome - mean_baseline
