# AI Governance Failure Modes

Codified failure modes are observable patterns where governance structure exists but produces false assurance or perverse outcomes. Each mode is named, has detection signals, and has a remediation strategy aligned to framework principles.

---

## 1. Metric Inversion

**Definition:** The metric being optimised becomes detached from the underlying objective it was designed to measure. Optimising the score destroys its validity (Goodhart's Law).

**Observable signals:**
- Decision impact rate rising while outcome quality is falling.
- Override rate dropping because humans stop reviewing, not because AI improved.

**Framework lever:** `reproducibility_rate` as a cross-check; audit trail queries on `ai_decision` entries with `outcome=influenced` correlated against actual outcome deltas.

**Remediation:** Introduce secondary metrics not visible to the system being optimised. Periodic blind outcome review.

---

## 2. Local Optimisation / Global Degradation

**Definition:** The AI system maximises performance within its evaluation window while degrading the broader system it participates in.

**Observable signals:**
- High readiness gate scores locally.
- Negative `outcome_delta` when measured over a longer window or adjacent process.

**Framework lever:** `baseline_impact` parameter in `evaluate_readiness()` must be recalculated against the full system, not the AI subsystem alone.

**Remediation:** Expand outcome measurement scope. Require cross-domain impact analysis as evidence on proposals.

---

## 3. Epistemic Drift

**Definition:** The model's internal distribution shifts relative to the deployment context, but this is not surfaced as an override or reproducibility failure. Recommendations remain internally consistent but become systematically wrong.

**Observable signals:**
- Truth threshold (reproducibility) passing.
- Direction threshold passing.
- But `outcome_delta` degrading over time.

**Framework lever:** Require `features_hash` in `InputTracking` and compare across cycles. A stable hash with declining delta is a drift signal.

**Remediation:** Add a drift evaluator rule that checks feature distribution checksums. Trigger `MandatoryReviewRequired` on anomaly.

---

## 4. Governance Theatre

**Definition:** The audit trail, readiness gate, and override mechanism are all populated, but the human review step is perfunctory. Governance exists structurally but not functionally.

**Observable signals:**
- Override rate of 0% sustained over many cycles.
- `HumanApprovalRequired` always resolved with identical override_reason strings.
- Audit entries with zero review time (inferred from timestamp proximity).

**Framework lever:** This failure mode cannot be fully detected by code — it requires a process audit. However, `override_rate == 0.0` for extended periods is a flag.

**Remediation:** Require sampled human review with documented deliberation evidence attached as `Evidence` objects on proposals. Rotate reviewers.

---

## 5. Silent Override

**Definition:** AI recommendations are systematically overridden but `override_reason` is null or contains boilerplate. The real reasons are invisible to the governance record, corrupting the feedback loop.

**Observable signals:**
- High `override_rate`.
- `override_reason` is null or repeated identical strings.
- `audit_notes` empty on `AIDecisionRecord`.

**Framework lever:** The `require_override_reason` evaluator in `rules.py` enforces non-empty override reasons at proposal evaluation time.

**Remediation:** Make `override_reason` required (non-null) by rule. Treat null override reasons as a `GovernanceViolation`.

---

## Architecture Layers

The framework implements four operational layers:

1. **Data (Truth):** `InputTracking`, `features_hash`, `data_version` — ensures the factual basis of decisions is reproducible and versioned.
2. **Decision (Execution):** `Proposal` -> `Decision` -> `ActionResult` -> `AIDecisionRecord` — the governed execution chain.
3. **Audit (Control):** `AuditTrail` with hash-chained `AuditEntry` objects — tamper-evident record of all governance events.
4. **Feedback (Learning):** `ReadinessGate`, `MetricsSnapshot` — closes the loop between execution outcomes and system evolution.

Critical insight: most organisations build layers 1 and 2. Almost none have layers 3 and 4 functioning.
