"""Basic usage — propose an action, validate it, inspect the audit trail.

This example demonstrates the core governance flow:
1. Create a governance engine with rules
2. Submit a proposal
3. Get a decision (approved/denied)
4. Record execution results
5. Verify audit trail integrity
"""

from governance.core import GovernanceEngine
from governance.decisions import Evidence, EvidenceQualifier, Proposal, Verdict
from governance.exceptions import NoRuleError
from governance.rules import Rule, RuleRegistry, RuleSet, require_owner


def main() -> None:
    # --- Step 1: Define rules ---
    registry = RuleRegistry()

    data_rules = RuleSet(
        name="data_operations",
        rules=(
            Rule(
                name="allow_read",
                description="Permit read access to non-sensitive data",
                principles=("regulated_component", "determinism"),
                actions=frozenset({"read", "list", "search"}),
                evaluator=lambda p: (Verdict.APPROVED, ("Read operations permitted.",)),
            ),
            Rule(
                name="write_with_owner",
                description="Permit writes only with verified ownership",
                principles=("ownership", "regulated_component"),
                actions=frozenset({"write", "update"}),
                evaluator=require_owner,
            ),
        ),
    )
    registry.register("data", data_rules)

    # --- Step 2: Create the governance engine ---
    engine = GovernanceEngine(registry=registry)

    # --- Step 3: Submit a proposal ---
    proposal = Proposal(
        action="read",
        target="/reports/quarterly_review.pdf",
        rationale="Generate summary for board meeting",
        proposed_by="ai_assistant",
        owner="jorge.pessoa",
        evidence=(
            Evidence(
                content="Board meeting scheduled for next Monday",
                qualifier=EvidenceQualifier.FACT,
                source="calendar_api",
            ),
        ),
    )

    decision = engine.evaluate(proposal)
    print(f"Decision: {decision.verdict.value}")
    print(f"Reasons: {decision.reasons}")
    print(f"Decided by: {decision.decided_by}")
    print()

    # --- Step 4: Record execution ---
    result = engine.record_execution(
        decision,
        success=True,
        output="Report read successfully. 42 pages.",
    )
    print(f"Execution: {'success' if result.success else 'failure'}")
    print(f"Output: {result.output}")
    print()

    # --- Step 5: Try an unregistered action (fail-closed) ---
    delete_proposal = Proposal(
        action="delete",
        target="/reports/quarterly_review.pdf",
        rationale="Clean up after processing",
        proposed_by="ai_assistant",
        owner="jorge.pessoa",
    )

    try:
        engine.evaluate(delete_proposal)
    except NoRuleError as e:
        print(f"BLOCKED: {e}")
        print("  (This is fail-closed working correctly)")
    print()

    # --- Step 6: Verify audit trail ---
    is_valid, msg = engine.audit.verify_integrity()
    print(f"Audit trail: {msg}")
    print(f"Total entries: {len(engine.audit)}")
    for entry in engine.audit.entries:
        print(f"  [{entry.sequence}] {entry.event_type}: {entry.action} -> {entry.outcome}")


if __name__ == "__main__":
    main()
