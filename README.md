# AI Governance Framework

**A production-ready AI governance framework implementing fail-closed principles for EU AI Act compliance.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Compliant-blue.svg)](docs/eu_ai_act_mapping.md)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy-lang.org/)

---

## The Problem

Most AI systems operate **fail-open**: anything not explicitly forbidden is allowed. This is the wrong default for regulated environments.

When an AI assistant encounters an action with no governing rule, it improvises. It "figures it out." In a consumer app, this is a feature. In healthcare, defense, finance, or government systems, it is a liability.

**Fail-closed governance inverts this default:** if there is no explicit rule permitting an action, the action is blocked. The AI proposes; humans decide. Every action is audited. Every decision has an owner.

This framework implements that model with real, typed, tested Python code.

## Quick Start

```bash
pip install -e .
```

```python
from governance import (
    GovernanceEngine,
    Proposal,
    Rule,
    RuleRegistry,
    RuleSet,
    Verdict,
)

# 1. Define rules — only explicitly permitted actions are allowed
registry = RuleRegistry()
rules = RuleSet(name="operations", rules=(
    Rule(
        name="allow_read",
        description="Permit read access",
        principles=("determinism", "regulated_component"),
        actions=frozenset({"read"}),
        evaluator=lambda p: (Verdict.APPROVED, ("Read permitted.",)),
    ),
))
registry.register("ops", rules)

# 2. Create the governance engine
engine = GovernanceEngine(registry=registry)

# 3. Submit a proposal (AI proposes, never decides)
proposal = Proposal(
    action="read",
    target="/reports/q4_summary.pdf",
    rationale="Generate board briefing",
    proposed_by="ai_assistant",
    owner="jorge.pessoa",
)

# 4. Evaluate — approved, denied, or pending human approval
decision = engine.evaluate(proposal)
print(decision.verdict)  # Verdict.APPROVED

# 5. Try an unregistered action — fail-closed
from governance.exceptions import NoRuleError

try:
    engine.evaluate(Proposal(
        action="delete",
        target="/reports/q4_summary.pdf",
        rationale="Cleanup",
        proposed_by="ai_assistant",
        owner="jorge.pessoa",
    ))
except NoRuleError as e:
    print(e)  # NoRuleError[fail-closed]: no rule found for action='delete'

# 6. Verify audit trail integrity (hash-chained, tamper-evident)
is_valid, msg = engine.audit.verify_integrity()
print(msg)  # "Audit trail verified: 2 entries, chain intact."
```

## The 10 Principles

| # | Principle | Core Idea | Framework Implementation |
|---|---|---|---|
| 1 | **Regulated Component** | AI proposes, never decides | `Proposal` -> `Decision` pipeline |
| 2 | **Documentary Sovereignty** | Documents prevail over code | `ForbiddenZoneEvaluator` protects sovereign docs |
| 3 | **Determinism** | Fail-closed on ambiguity | `NoRuleError` raised when no rule matches |
| 4 | **Forbidden Zones** | No writes to protected areas | `ForbiddenZoneError` on zone violations |
| 5 | **Evidence, not Persuasion** | Qualify all output | `Evidence` with `EvidenceQualifier` (FACT/INFERENCE/UNCONFIRMED) |
| 6 | **Human-in-the-Loop** | Humans approve critical actions | `HumanApprovalRequired` halts execution |
| 7 | **Ownership** | Every artefact has a human owner | `OwnershipError` if no owner on proposal |
| 8 | **Proportional Change** | Impact analysis mandatory | Document-level classification gates |
| 9 | **Evolution with Process** | Governance evolves, with process | Review schedules, sunset clauses |
| 10 | **Meta-governance** | The system governs itself | Priority-ordered `RuleRegistry` |

Full details: [PRINCIPLES.md](PRINCIPLES.md)

## EU AI Act Mapping

The framework maps directly to [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) requirements:

| EU AI Act Article | Framework Feature |
|---|---|
| **Art. 5** — Prohibited practices | `deny_unacceptable_risk()` + forbidden zones |
| **Art. 6** — Risk classification | `RiskLevel` enum (UNACCEPTABLE/HIGH/LIMITED/MINIMAL) |
| **Art. 9** — Risk management | Ownership tracking + periodic review |
| **Art. 12** — Record-keeping | Hash-chained `AuditTrail` (append-only, tamper-evident) |
| **Art. 14** — Human oversight | `Verdict.PENDING_HUMAN_APPROVAL` + `HumanApprovalRequired` |
| **Art. 43** — Conformity assessment | `Evidence` with `EvidenceQualifier` for verifiable compliance |

Full mapping: [docs/eu_ai_act_mapping.md](docs/eu_ai_act_mapping.md)

## Architecture

```
Proposal ──> GovernanceEngine ──> Decision ──> ActionResult
                  │                    │
                  │                    ▼
                  │               AuditTrail
                  │              (append-only,
                  │              hash-chained)
                  ▼
            RuleRegistry
            ┌─────────────────┐
            │ Domain A (p=0)  │  ◄── Higher priority, evaluated first
            │   Rule 1        │
            │   Rule 2        │
            ├─────────────────┤
            │ Domain B (p=1)  │
            │   Rule 3        │
            └─────────────────┘
```

**Key design decisions:**
- **Frozen dataclasses** — proposals, decisions, and audit entries are immutable after creation
- **Hash-chained audit** — each entry's SHA-256 hash includes the previous entry's hash (tamper-evident)
- **Composable rules** — rules are functions (`Protocol`), not configuration. Test them like any other code
- **Typed throughout** — full type hints, compatible with mypy strict mode

## Examples

### Document Approval Workflow

Sovereign documents are protected. Policy changes require evidence. Principle-level changes require board approval.

```bash
python examples/document_approval.py
```

### EU AI Act Compliance Check

Classify AI systems by risk level, validate documentation, enforce human oversight for high-risk deployments.

```bash
python examples/compliance_check.py
```

### Basic Usage

The core governance flow: propose, evaluate, execute, audit.

```bash
python examples/basic_usage.py
```

## Running Tests

```bash
pip install pytest
pytest -v
```

Tests cover:
- **Fail-closed behavior** — unknown actions are always denied
- **Ownership enforcement** — proposals without owners are rejected
- **Forbidden zones** — writes to protected paths are blocked
- **Human-in-the-loop** — critical actions pause for human approval
- **Audit integrity** — hash chain verification detects tampering
- **EU AI Act risk classification** — unacceptable risk is always blocked
- **Rule priority** — higher-priority domains are evaluated first

## Origin

This framework was extracted from a production governance layer applied across 7+ systems in Python, TypeScript, and Kotlin. The principles were developed iteratively: each one exists because its absence caused a real failure in a real system.

It is not a theoretical framework. It is operational governance that runs in production.

## Contributing

Contributions are welcome. Please:

1. Open an issue describing the problem or enhancement
2. Fork and create a feature branch
3. Ensure all tests pass (`pytest -v`)
4. Ensure code quality (`ruff check .` and `mypy governance/`)
5. Submit a pull request with a clear description

## License

[MIT](LICENSE)
