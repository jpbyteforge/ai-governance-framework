"""Document approval workflow — sovereign documents and forbidden zones.

Demonstrates:
- Documentary sovereignty (Principle 2): sovereign documents prevail
- Forbidden zones (Principle 4): protected areas cannot be written to
- Human-in-the-loop (Principle 6): critical approvals need human confirmation
- Proportional change (Principle 8): impact analysis before modification
"""

from governance.core import GovernanceEngine
from governance.decisions import Evidence, EvidenceQualifier, Proposal, Verdict
from governance.exceptions import ForbiddenZoneError, HumanApprovalRequired
from governance.rules import (
    ForbiddenZoneEvaluator,
    Rule,
    RuleRegistry,
    RuleSet,
    require_human_approval,
)


def classify_document_change(proposal: Proposal) -> tuple[Verdict, tuple[str, ...]]:
    """Evaluate document modifications based on proportional change principle.

    Higher-level documents require more rigorous approval:
    - Principle documents -> human approval required
    - Policy documents -> evidence required
    - Procedure documents -> standard approval
    """
    doc_level = proposal.metadata.get("document_level", "reference")

    if doc_level == "principle":
        return (
            Verdict.PENDING_HUMAN_APPROVAL,
            ("Principle-level document requires board approval.",),
        )

    if doc_level == "policy":
        if not proposal.evidence:
            return (
                Verdict.DENIED,
                ("Policy changes require evidence. Attach impact analysis.",),
            )
        return (Verdict.APPROVED, ("Policy change approved with evidence.",))

    return (Verdict.APPROVED, (f"Document level '{doc_level}' approved via standard process.",))


def main() -> None:
    # --- Set up rules ---
    registry = RuleRegistry()

    # Forbidden zones — sovereign documents that AI cannot modify
    sovereign_zones = ForbiddenZoneEvaluator(
        zones=frozenset({
            "/governance/manifesto",
            "/governance/constitution",
            "/legal/contracts",
        })
    )

    zone_rules = RuleSet(
        name="document_zones",
        rules=(
            Rule(
                name="sovereign_protection",
                description="Protect sovereign documents from AI modification",
                principles=("documentary_sovereignty", "forbidden_zones"),
                actions=frozenset({"write", "delete", "modify"}),
                evaluator=sovereign_zones,
            ),
        ),
    )

    approval_rules = RuleSet(
        name="document_approval",
        rules=(
            Rule(
                name="document_classification",
                description="Classify and gate document changes",
                principles=("proportional_change", "human_in_the_loop"),
                actions=frozenset({"approve_document", "review_document"}),
                evaluator=classify_document_change,
            ),
            Rule(
                name="publish_gate",
                description="Publishing requires human sign-off",
                principles=("human_in_the_loop",),
                actions=frozenset({"publish"}),
                evaluator=require_human_approval,
            ),
        ),
    )

    # Zone rules at higher priority — evaluated first
    registry.register("zones", zone_rules, priority=0)
    registry.register("approval", approval_rules, priority=1)

    engine = GovernanceEngine(registry=registry)

    # --- Scenario 1: Try to modify a sovereign document ---
    print("=== Scenario 1: Modify sovereign document ===")
    try:
        engine.evaluate(Proposal(
            action="write",
            target="/governance/manifesto/principles.md",
            rationale="Update principle wording",
            proposed_by="ai_assistant",
            owner="jorge.pessoa",
        ))
    except ForbiddenZoneError as e:
        print(f"  BLOCKED: {e}")

    # --- Scenario 2: Approve a procedure document (standard) ---
    print("\n=== Scenario 2: Approve procedure document ===")
    decision = engine.evaluate(Proposal(
        action="approve_document",
        target="/procedures/deployment_checklist.md",
        rationale="Updated deployment steps for v2.0",
        proposed_by="ai_assistant",
        owner="jorge.pessoa",
        metadata={"document_level": "procedure"},
    ))
    print(f"  Result: {decision.verdict.value} — {decision.reasons}")

    # --- Scenario 3: Approve a policy document without evidence ---
    print("\n=== Scenario 3: Policy change without evidence ===")
    decision = engine.evaluate(Proposal(
        action="approve_document",
        target="/policies/data_retention.md",
        rationale="Extend retention period",
        proposed_by="ai_assistant",
        owner="jorge.pessoa",
        metadata={"document_level": "policy"},
    ))
    print(f"  Result: {decision.verdict.value} — {decision.reasons}")

    # --- Scenario 4: Policy change WITH evidence ---
    print("\n=== Scenario 4: Policy change with evidence ===")
    decision = engine.evaluate(Proposal(
        action="approve_document",
        target="/policies/data_retention.md",
        rationale="Extend retention period to comply with EU regulation",
        proposed_by="ai_assistant",
        owner="jorge.pessoa",
        metadata={"document_level": "policy"},
        evidence=(
            Evidence(
                content="EU regulation 2024/1689 requires 5-year retention",
                qualifier=EvidenceQualifier.FACT,
                source="eur-lex.europa.eu",
            ),
        ),
    ))
    print(f"  Result: {decision.verdict.value} — {decision.reasons}")

    # --- Scenario 5: Principle-level change (needs human) ---
    print("\n=== Scenario 5: Principle-level change ===")
    try:
        engine.evaluate(Proposal(
            action="approve_document",
            target="/governance/principles/fail_closed.md",
            rationale="Redefine fail-closed scope",
            proposed_by="ai_assistant",
            owner="jorge.pessoa",
            metadata={"document_level": "principle"},
        ))
    except HumanApprovalRequired as e:
        print(f"  PAUSED: {e}")

    # --- Audit summary ---
    print("\n=== Audit Trail ===")
    is_valid, msg = engine.audit.verify_integrity()
    print(f"  Integrity: {msg}")
    for entry in engine.audit.entries:
        print(f"  [{entry.sequence}] {entry.event_type}: {entry.action} on {entry.target} -> {entry.outcome}")


if __name__ == "__main__":
    main()
