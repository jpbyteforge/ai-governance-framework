# The 10 Principles of Operational AI Governance

These principles were developed through real-world application across 7+ production systems (Python, TypeScript, Kotlin). They are not theoretical — each principle exists because its absence caused a concrete failure.

The core insight: **AI governance must be fail-closed**. In security, fail-closed means "if in doubt, deny." Applied to AI governance: if there is no explicit rule permitting an action, the action is blocked. This is the opposite of how most AI systems operate today.

---

## 1. Regulated Component

> AI proposes, never decides. Every action requires documentary basis.

The AI system is a regulated component within a larger human-governed process. It can analyze, recommend, and draft — but it cannot execute decisions autonomously. Every action requires an explicit rule and an audit trail entry.

**Implementation:** `Proposal` objects are the only way to request action. The `GovernanceEngine` evaluates them against rules before any execution occurs.

## 2. Documentary Sovereignty

> Sovereign documents prevail over code, configuration, and output.

When a governance document (policy, principle, regulation) conflicts with code behavior, the document wins. AI systems must not alter sovereign documents without explicit human instruction and an Architecture Decision Record (ADR).

**Implementation:** `ForbiddenZoneEvaluator` protects sovereign document paths. The rule hierarchy (principle > policy > procedure > reference) is enforced through `RuleRegistry` priority ordering.

## 3. Determinism

> Checks first. Fail-closed on ambiguity. No creative compensation for failures.

Before any action, run all applicable checks (validation, linting, governance rules). If no rule exists for an action, the action is denied — not approximated. The system does not "figure it out" or apply creative workarounds.

**Implementation:** `GovernanceEngine.evaluate()` raises `NoRuleError` when no rule matches. The `RuleRegistry` returns `None` for unmatched actions, triggering the fail-closed path.

## 4. Forbidden Zones

> Write only in permitted areas. No operations in protected zones.

Certain areas (credentials, sovereign documents, production configurations) are off-limits to AI operations. These zones are defined declaratively and enforced at the governance layer — before code execution.

**Implementation:** `ForbiddenZoneEvaluator` holds a frozen set of protected paths. Any proposal targeting a forbidden zone is denied with `ForbiddenZoneError`.

## 5. Evidence, Not Persuasion

> Verifiable output. Qualify as FACT, INFERENCE, or UNCONFIRMED.

AI output must be evidence-based and explicitly qualified. A "fact" has a verifiable source. An "inference" is a logical derivation. "Unconfirmed" means the system cannot verify. Mixing these categories without labels is a governance violation.

**Implementation:** `Evidence` dataclass with `EvidenceQualifier` enum (FACT, INFERENCE, UNCONFIRMED). Proposals can carry evidence tuples, and rules can require evidence before approval.

## 6. Human-in-the-Loop

> Critical or irreversible actions require human confirmation.

Deployment, deletion, policy changes, and any action marked as critical must pause for human approval. The system surfaces the decision to a human and waits — it does not proceed with a timeout or default.

**Implementation:** `Verdict.PENDING_HUMAN_APPROVAL` and `HumanApprovalRequired` exception. The `require_human_approval` evaluator checks the `requires_human_approval` flag on proposals.

## 7. Ownership

> Every artefact has a human owner. Decisions recorded: who, when, why, authority.

No anonymous actions. No unattributed decisions. Every proposal must name an owner. Every decision records the deciding authority. The audit trail captures the complete chain: actor, owner, rule, timestamp, outcome.

**Implementation:** `Proposal.owner` is checked by `GovernanceEngine.evaluate()`. Missing ownership raises `OwnershipError`. `AuditEntry` records actor, action, outcome, and details including owner.

## 8. Proportional Change

> Impact analysis mandatory. Principle > policy > procedure > reference.

Changes to higher-level governance documents require proportionally more rigorous review. A procedure change needs standard approval. A principle change needs board-level sign-off. Every change includes impact analysis.

**Implementation:** Rule evaluators can inspect `metadata["document_level"]` and apply proportional gates. The `RuleRegistry` priority system enforces the governance hierarchy.

## 9. Evolution with Process

> Feedback loops. Periodic review. Sunset clauses on experimental rules.

Governance is not static. Rules have review dates. Experimental rules have sunset clauses (automatic expiration if not renewed). The system supports evolution — but through documented process, not ad-hoc changes.

**Implementation:** Rules can carry metadata for review schedules. The `RuleRegistry` supports dynamic addition of rule sets. Sunset logic can be implemented via rule evaluators that check dates.

## 10. Meta-governance

> Explicit hierarchy. Referential integrity. Governance that paralyzes has failed.

The governance system itself is governed. Rule sets have explicit priority ordering. The hierarchy is declared, not implicit. And critically: if governance becomes so restrictive that it prevents all useful work, that itself is a governance failure.

**Implementation:** `RuleRegistry` with priority-ordered domains. `RuleSet` with named, documented rules. The framework is designed to be configured for the appropriate level of control — not maximally restrictive by default.

---

## Design Philosophy

These principles follow a specific design philosophy:

1. **Deny by default, permit by exception** — the opposite of most software defaults
2. **Structured records, not log messages** — every event is a typed, queryable object
3. **Immutable history** — the audit trail is append-only and hash-chained
4. **Composable rules** — rules are functions, not configuration files
5. **Type-safe** — full type hints, frozen dataclasses, enum-based classifications
