"""EU AI Act compliance checking — risk classification and governance mapping.

Demonstrates how the governance framework maps to EU AI Act requirements:
- Risk classification (Article 6): unacceptable, high, limited, minimal
- Conformity assessment (Article 43): evidence-based verification
- Human oversight (Article 14): human-in-the-loop for high-risk systems
- Record-keeping (Article 12): immutable audit trail
"""

from governance.core import GovernanceEngine
from governance.decisions import Evidence, EvidenceQualifier, Proposal, Verdict
from governance.exceptions import HumanApprovalRequired
from governance.rules import (
    Rule,
    RiskLevel,
    RuleRegistry,
    RuleSet,
    deny_unacceptable_risk,
)


def high_risk_evaluator(proposal: Proposal) -> tuple[Verdict, tuple[str, ...]]:
    """Evaluate high-risk AI system proposals per EU AI Act Article 6.

    High-risk systems require:
    - Risk management system (Article 9)
    - Data governance (Article 10)
    - Technical documentation (Article 11)
    - Human oversight (Article 14)
    """
    risk = proposal.metadata.get("risk_level", "")
    required_docs = {"risk_assessment", "data_governance", "technical_docs", "oversight_plan"}
    provided_docs = set(proposal.metadata.get("documentation", []))
    missing = required_docs - provided_docs

    if risk in (RiskLevel.HIGH.value, RiskLevel.HIGH):
        if missing:
            return (
                Verdict.DENIED,
                (
                    f"High-risk system missing required documentation: {', '.join(sorted(missing))}. "
                    f"EU AI Act Articles 9-14 require complete documentation before deployment.",
                ),
            )
        return (
            Verdict.PENDING_HUMAN_APPROVAL,
            (
                "High-risk system documentation complete. "
                "Requires human oversight sign-off per Article 14.",
            ),
        )

    if risk in (RiskLevel.LIMITED.value, RiskLevel.LIMITED):
        return (
            Verdict.APPROVED,
            ("Limited-risk system. Transparency obligations apply (Article 52).",),
        )

    return (Verdict.APPROVED, ("Minimal-risk system. No additional requirements.",))


def composite_risk_evaluator(proposal: Proposal) -> tuple[Verdict, tuple[str, ...]]:
    """Two-stage evaluator: unacceptable gate, then detailed classification."""
    # Stage 1: Absolute block on unacceptable risk
    verdict, reasons = deny_unacceptable_risk(proposal)
    if verdict == Verdict.DENIED:
        return verdict, reasons

    # Stage 2: Detailed classification for high/limited/minimal
    return high_risk_evaluator(proposal)


def main() -> None:
    registry = RuleRegistry()

    # Single rule set with composite evaluator — unacceptable gate + classification
    risk_rules = RuleSet(
        name="eu_ai_act_risk",
        rules=(
            Rule(
                name="risk_classification",
                description="EU AI Act risk classification (Articles 5-6)",
                principles=("determinism", "regulated_component", "human_in_the_loop"),
                actions=frozenset({"deploy", "classify", "assess"}),
                evaluator=composite_risk_evaluator,
                risk_level=RiskLevel.HIGH,
            ),
        ),
    )

    registry.register("eu_ai_act", risk_rules)

    engine = GovernanceEngine(registry=registry)

    # --- Scenario 1: Unacceptable risk (social scoring) ---
    print("=== Scenario 1: Unacceptable Risk — Social Scoring System ===")
    decision = engine.evaluate(Proposal(
        action="deploy",
        target="social_scoring_system_v1",
        rationale="Deploy citizen scoring system",
        proposed_by="ai_team",
        owner="jorge.pessoa",
        metadata={"risk_level": "unacceptable"},
        evidence=(
            Evidence(
                content="System performs social scoring based on behavior patterns",
                qualifier=EvidenceQualifier.FACT,
                source="system_specification",
            ),
        ),
    ))
    print(f"  Verdict: {decision.verdict.value}")
    print(f"  Reasons: {decision.reasons}")

    # --- Scenario 2: High risk without documentation ---
    print("\n=== Scenario 2: High Risk — Missing Documentation ===")
    decision = engine.evaluate(Proposal(
        action="deploy",
        target="credit_scoring_model_v3",
        rationale="Deploy credit scoring for loan applications",
        proposed_by="ai_team",
        owner="jorge.pessoa",
        metadata={
            "risk_level": "high",
            "documentation": ["risk_assessment", "technical_docs"],
        },
    ))
    print(f"  Verdict: {decision.verdict.value}")
    print(f"  Reasons: {decision.reasons}")

    # --- Scenario 3: High risk with complete documentation ---
    print("\n=== Scenario 3: High Risk — Complete Documentation ===")
    try:
        engine.evaluate(Proposal(
            action="deploy",
            target="credit_scoring_model_v3",
            rationale="Deploy credit scoring — all documentation complete",
            proposed_by="ai_team",
            owner="jorge.pessoa",
            metadata={
                "risk_level": "high",
                "documentation": [
                    "risk_assessment",
                    "data_governance",
                    "technical_docs",
                    "oversight_plan",
                ],
            },
            evidence=(
                Evidence(
                    content="Conformity assessment passed 2025-01-15",
                    qualifier=EvidenceQualifier.FACT,
                    source="conformity_assessment_report_v3.pdf",
                ),
                Evidence(
                    content="Bias testing shows <2% demographic disparity",
                    qualifier=EvidenceQualifier.FACT,
                    source="fairness_audit_q4_2024.pdf",
                ),
            ),
        ))
    except HumanApprovalRequired as e:
        print(f"  PAUSED for human: {e}")

    # --- Scenario 4: Limited risk (chatbot) ---
    print("\n=== Scenario 4: Limited Risk — Customer Service Chatbot ===")
    decision = engine.evaluate(Proposal(
        action="deploy",
        target="customer_chatbot_v2",
        rationale="Deploy customer service chatbot with transparency notice",
        proposed_by="ai_team",
        owner="jorge.pessoa",
        metadata={"risk_level": "limited"},
    ))
    print(f"  Verdict: {decision.verdict.value}")
    print(f"  Reasons: {decision.reasons}")

    # --- Audit trail ---
    print("\n=== Compliance Audit Trail ===")
    is_valid, msg = engine.audit.verify_integrity()
    print(f"  Integrity: {msg}")
    print(f"  Total records: {len(engine.audit)}")

    for entry in engine.audit.entries:
        print(
            f"  [{entry.sequence}] {entry.event_type} | "
            f"{entry.action} -> {entry.target} | "
            f"outcome={entry.outcome}"
        )


if __name__ == "__main__":
    main()
