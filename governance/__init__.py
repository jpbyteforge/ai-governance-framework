"""AI Governance Framework — fail-closed governance for AI-integrated systems."""

from governance.audit import AuditEntry, AuditTrail
from governance.core import GovernanceEngine, Principle
from governance.decisions import ActionResult, Decision, Proposal, Verdict
from governance.exceptions import (
    ForbiddenZoneError,
    GovernanceViolation,
    NoRuleError,
    OwnershipError,
)
from governance.rules import Rule, RuleRegistry, RuleSet

__all__ = [
    "ActionResult",
    "AuditEntry",
    "AuditTrail",
    "Decision",
    "ForbiddenZoneError",
    "GovernanceEngine",
    "GovernanceViolation",
    "NoRuleError",
    "OwnershipError",
    "Principle",
    "Proposal",
    "Rule",
    "RuleRegistry",
    "RuleSet",
    "Verdict",
]

__version__ = "0.1.0"
