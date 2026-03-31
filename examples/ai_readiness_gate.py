"""AI Readiness Gate — full lifecycle example.

Demonstrates:
1. Creating AI decision records with context, tracking, and outcomes
2. Running the 4-test Readiness Gate (Direction, Truth, Impact, Marginal Value)
3. Computing derived metrics (impact rate, override rate, reproducibility, delta)
4. Detecting degradation across evaluation cycles
5. Audit trail integration with gate events
"""

from governance.core import GovernanceEngine
from governance.decisions import (
    AIDecisionRecord,
    AIRecommendation,
    CostLevel,
    DecisionContext,
    DecisionType,
    HumanDecisionRecord,
    InputTracking,
    ModelTracking,
    OutcomeRecord,
    Proposal,
    Verdict,
)
from governance.exceptions import ReadinessGateCritical
from governance.rules import Rule, RuleRegistry, RuleSet


def make_rule_set() -> RuleSet:
    """Create a simple rule set allowing 'analyze' actions."""
    rule_set = RuleSet("ai_operations")
    rule_set.add_rule(
        Rule(
            name="allow_analyze",
            description="Permit AI analysis actions.",
            principles=("regulated_component",),
            actions=frozenset({"analyze"}),
            evaluator=lambda p: (Verdict.APPROVED, ("Analysis permitted.",)),
        )
    )
    return rule_set


def make_ai_record(
    engine: GovernanceEngine,
    *,
    confidence: float,
    override: bool = False,
    override_reason: str | None = None,
    reproducible: bool = True,
    outcome_value: float | None = None,
    record_id: int = 1,
) -> AIDecisionRecord:
    """Create an AIDecisionRecord through the full governance cycle."""
    proposal = Proposal(
        action="analyze",
        target=f"dataset-{record_id}",
        rationale=f"Routine analysis #{record_id}",
        proposed_by="ai_system",
        owner="operations_team",
    )
    decision = engine.evaluate(proposal)
    result = engine.record_execution(decision, success=True, output="done")

    human = None
    if override:
        human = HumanDecisionRecord(
            final_decision="alternative_action",
            override=True,
            override_reason=override_reason,
        )
    else:
        human = HumanDecisionRecord(
            final_decision="accept",
            override=False,
        )

    record = AIDecisionRecord(
        action_result=result,
        context=DecisionContext(
            decision_type=DecisionType.ASSISTED,
            cost_of_error=CostLevel.MEDIUM,
            cost_of_latency=CostLevel.LOW,
        ),
        input_tracking=InputTracking(
            data_version=f"v{record_id}.0",
            features_hash=f"sha256:abc{record_id:03d}",
            source_ids=(f"source-{record_id}",),
        ),
        model_tracking=ModelTracking(
            model_id="risk-model",
            model_version="2.1.0",
            inference_parameters={"temperature": 0.0},
        ),
        recommendation=AIRecommendation(
            output="recommend_action_A",
            confidence=confidence,
        ),
        human_decision=human,
        reproducible=reproducible,
    )

    if outcome_value is not None:
        record = record.with_outcome(
            OutcomeRecord(observed_result=outcome_value)
        )

    return record


def main() -> None:
    # --- Setup ---
    registry = RuleRegistry()
    registry.register("ai_ops", make_rule_set())
    engine = GovernanceEngine(registry=registry)
    engine.enable_readiness_gate()

    print("=" * 60)
    print("AI READINESS GATE — DEMONSTRATION")
    print("=" * 60)

    # --- Cycle 1: Healthy system ---
    print("\n--- Cycle 1: Healthy System ---\n")

    records = [
        make_ai_record(engine, confidence=0.92, outcome_value=0.85,
                        record_id=1),
        make_ai_record(engine, confidence=0.88, outcome_value=0.82,
                        record_id=2),
        make_ai_record(engine, confidence=0.95, outcome_value=0.90,
                        record_id=3),
        make_ai_record(engine, confidence=0.78, override=True,
                        override_reason="Domain expertise override",
                        outcome_value=0.80, record_id=4),
        make_ai_record(engine, confidence=0.91, outcome_value=0.87,
                        record_id=5),
    ]

    for r in records:
        engine.record_ai_decision(r)

    result = engine.evaluate_readiness(
        baseline_impact=0.70,
        previous_impact=None,
        cycle_id="cycle-1",
    )

    print(f"Status: {result.status.value.upper()}")
    print(f"Passed: {result.passed_count}/4")
    print(f"Action: {result.recommended_action}")
    print()
    for t in result.tests:
        status = "PASS" if t.passed else "FAIL"
        print(f"  [{status}] {t.name}: {t.measured_value:.2%} "
              f"(threshold: {t.threshold:.2%}) — {t.details}")

    # --- Metrics ---
    print("\n--- Derived Metrics ---\n")
    metrics = engine.get_metrics(baseline_values=(0.70, 0.70, 0.70))
    print(f"  Total decisions:       {metrics.total_decisions}")
    print(f"  Decision impact rate:  {metrics.decision_impact_rate:.2%}")
    print(f"  Override rate:         {metrics.override_rate:.2%}")
    print(f"  Reproducibility rate:  {metrics.reproducibility_rate:.2%}")
    if metrics.outcome_delta is not None:
        print(f"  Outcome delta:         {metrics.outcome_delta:+.4f}")

    # --- Cycle 2: Degraded system ---
    print("\n--- Cycle 2: Degraded System ---\n")

    degraded_records = [
        make_ai_record(engine, confidence=0.55, override=True,
                        override_reason="Model unreliable",
                        reproducible=False, outcome_value=0.60,
                        record_id=6),
        make_ai_record(engine, confidence=0.50, override=True,
                        override_reason="Incorrect recommendation",
                        reproducible=False, outcome_value=0.55,
                        record_id=7),
        make_ai_record(engine, confidence=0.60, outcome_value=0.62,
                        reproducible=False, record_id=8),
    ]

    for r in degraded_records:
        engine.record_ai_decision(r)

    try:
        result2 = engine.evaluate_readiness(
            baseline_impact=0.70,
            previous_impact=0.85,
            cycle_id="cycle-2",
        )
        print(f"Status: {result2.status.value.upper()}")
        print(f"Passed: {result2.passed_count}/4")
        print(f"Action: {result2.recommended_action}")
        for t in result2.tests:
            status = "PASS" if t.passed else "FAIL"
            print(f"  [{status}] {t.name}: {t.measured_value:.2%} "
                  f"(threshold: {t.threshold:.2%})")
    except ReadinessGateCritical as e:
        print(f"CRITICAL: {e}")
        print("-> Automatic downgrade triggered.")

    # --- Audit Trail ---
    print("\n--- Audit Trail Summary ---\n")
    gate_events = engine.audit.query(event_type="readiness_gate")
    ai_events = engine.audit.query(event_type="ai_decision")
    print(f"  AI decision events:    {len(ai_events)}")
    print(f"  Readiness gate events: {len(gate_events)}")

    valid, msg = engine.audit.verify_integrity()
    print(f"  Audit chain integrity: {'VALID' if valid else 'BROKEN'}")
    print(f"  Total audit entries:   {len(engine.audit.entries)}")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
