"""AI Governance Framework — fail-closed governance for AI-integrated systems."""

from governance.audit import AuditEntry, AuditTrail
from governance.core import GovernanceEngine, Principle
from governance.decisions import (
    AIDecisionRecord,
    AIRecommendation,
    ActionResult,
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
from governance.exceptions import (
    ForbiddenZoneError,
    GovernanceViolation,
    MandatoryReviewRequired,
    NoRuleError,
    OwnershipError,
    ReadinessGateCritical,
)
from governance.metrics import MetricsSnapshot, compute_metrics
from governance.rules import Rule, RuleRegistry, RuleSet
from governance.scoring import (
    GateTestResult,
    ReadinessGate,
    ReadinessGateConfig,
    ReadinessGateResult,
    ReadinessStatus,
)

__all__ = [
    "AIDecisionRecord",
    "AIRecommendation",
    "ActionResult",
    "AuditEntry",
    "AuditTrail",
    "CostLevel",
    "Decision",
    "DecisionContext",
    "DecisionType",
    "ForbiddenZoneError",
    "GateTestResult",
    "GovernanceEngine",
    "GovernanceViolation",
    "HumanDecisionRecord",
    "InputTracking",
    "MandatoryReviewRequired",
    "MetricsSnapshot",
    "ModelTracking",
    "NoRuleError",
    "OutcomeRecord",
    "OwnershipError",
    "Principle",
    "Proposal",
    "ReadinessGate",
    "ReadinessGateConfig",
    "ReadinessGateResult",
    "ReadinessGateCritical",
    "ReadinessStatus",
    "Rule",
    "RuleRegistry",
    "RuleSet",
    "Verdict",
    "compute_metrics",
]

__version__ = "0.2.0"
