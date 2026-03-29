# EU AI Act Compliance Mapping

How the AI Governance Framework maps to [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) — the EU AI Act.

**Enforcement timeline:** August 2026 (full application for high-risk AI systems).

---

## Risk Classification (Article 6)

The framework implements EU AI Act risk tiers through `RiskLevel` and rule evaluators:

| EU AI Act Tier | Framework Implementation | Behavior |
|---|---|---|
| **Unacceptable** (Art. 5) | `deny_unacceptable_risk()` evaluator | Absolute block. No override possible. |
| **High** (Art. 6) | `high_risk_evaluator()` with documentation gates | Requires complete documentation + human sign-off |
| **Limited** (Art. 52) | Standard rule evaluation | Transparency obligations flagged |
| **Minimal** | Default approved path | No additional requirements |

### Code reference

```python
from governance.rules import RiskLevel, deny_unacceptable_risk

# Unacceptable risk — always denied
rule = Rule(
    name="unacceptable_block",
    actions=frozenset({"deploy"}),
    evaluator=deny_unacceptable_risk,
    risk_level=RiskLevel.UNACCEPTABLE,
)
```

---

## Article-by-Article Mapping

### Article 5 — Prohibited AI Practices

| Requirement | Framework Principle | Implementation |
|---|---|---|
| Ban on social scoring | Principle 3 (Determinism) | `deny_unacceptable_risk` — fail-closed block |
| Ban on real-time biometric ID | Principle 4 (Forbidden Zones) | Configurable forbidden zones per deployment |
| No manipulation/exploitation | Principle 1 (Regulated Component) | AI proposes, never decides autonomously |

### Article 9 — Risk Management System

| Requirement | Framework Principle | Implementation |
|---|---|---|
| Continuous risk identification | Principle 9 (Evolution with Process) | Periodic review, feedback loops, sunset clauses |
| Risk mitigation measures | Principle 8 (Proportional Change) | Impact analysis mandatory before changes |
| Documentation of risk decisions | Principle 7 (Ownership) | Every decision recorded with owner, timestamp, authority |

### Article 10 — Data and Data Governance

| Requirement | Framework Principle | Implementation |
|---|---|---|
| Training data quality | Principle 5 (Evidence, not Persuasion) | All evidence qualified as FACT/INFERENCE/UNCONFIRMED |
| Bias examination | Principle 3 (Determinism) | Checks first, fail-closed on ambiguity |
| Data governance practices | Principle 2 (Documentary Sovereignty) | Sovereign documents define data policies |

### Article 11 — Technical Documentation

| Requirement | Framework Principle | Implementation |
|---|---|---|
| System description | Principle 2 (Documentary Sovereignty) | Sovereign documents as source of truth |
| Development process | Principle 9 (Evolution with Process) | All changes tracked with process |
| Risk management info | Principle 8 (Proportional Change) | Impact analysis creates documentation trail |

### Article 12 — Record-Keeping

| Requirement | Framework Principle | Implementation |
|---|---|---|
| Automatic logging | `AuditTrail` | Hash-chained, append-only, tamper-evident |
| Traceability | Principle 7 (Ownership) | Actor, owner, timestamp on every entry |
| Log integrity | `AuditTrail.verify_integrity()` | SHA-256 hash chain verification |
| Retention | `AuditEntry` (immutable) | Frozen dataclasses, no delete/modify API |

### Article 14 — Human Oversight

| Requirement | Framework Principle | Implementation |
|---|---|---|
| Human-in-the-loop | Principle 6 | `HumanApprovalRequired` exception halts execution |
| Override capability | Principle 1 (Regulated Component) | AI proposes, human decides |
| Intervention ability | `Verdict.PENDING_HUMAN_APPROVAL` | Decision pipeline pauses for human input |

### Article 43 — Conformity Assessment

| Requirement | Framework Principle | Implementation |
|---|---|---|
| Evidence of compliance | Principle 5 (Evidence, not Persuasion) | `Evidence` with `EvidenceQualifier` |
| Assessment documentation | `AuditTrail` | Complete decision history, exportable |
| Third-party audit support | `AuditTrail.query()` | Filter by event type, actor, action |

---

## Principle-to-Article Cross-Reference

| # | Principle | EU AI Act Articles |
|---|---|---|
| 1 | Regulated Component | Art. 5, 14 |
| 2 | Documentary Sovereignty | Art. 10, 11 |
| 3 | Determinism (fail-closed) | Art. 5, 6, 9, 10 |
| 4 | Forbidden Zones | Art. 5 |
| 5 | Evidence, not Persuasion | Art. 10, 43 |
| 6 | Human-in-the-Loop | Art. 14 |
| 7 | Ownership | Art. 9, 12 |
| 8 | Proportional Change | Art. 9, 11 |
| 9 | Evolution with Process | Art. 9, 11 |
| 10 | Meta-governance | Art. 6 (risk hierarchy) |

---

## Implementation Checklist

For organizations preparing for EU AI Act compliance (August 2026):

- [ ] **Inventory** all AI systems and classify by risk level
- [ ] **Configure** forbidden zones for prohibited use cases
- [ ] **Implement** fail-closed rules — deny by default, permit by exception
- [ ] **Enable** human-in-the-loop for all high-risk decisions
- [ ] **Deploy** audit trail with hash-chain integrity verification
- [ ] **Attach** evidence (qualified) to all governance decisions
- [ ] **Assign** human owners to every AI system and artefact
- [ ] **Schedule** periodic reviews with sunset clauses on experimental rules
- [ ] **Document** the governance hierarchy (meta-governance)
- [ ] **Test** — run `pytest` to verify all governance constraints hold

---

## Running the Compliance Example

```bash
python examples/compliance_check.py
```

This demonstrates the full EU AI Act risk classification flow with real governance decisions.
