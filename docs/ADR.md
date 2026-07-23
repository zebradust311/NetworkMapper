# Architecture Decision Records

This document records significant architectural decisions made during the
development of NetworkMapper.

Each ADR captures:

- The decision that was made.
- The reasoning behind the decision.
- The long-term consequences of that decision.

Only accepted architectural decisions are recorded here.

Future ideas and planned features belong in `ROADMAP.md`.

ADRs are recorded in chronological order and are never renumbered.

## ADR-001 — Two-Phase STANDARD Discovery

**Status:** Accepted

### Decision

STANDARD discovery performs host discovery before service enrichment.

### Rationale

Host discovery establishes the authoritative device list.
Service enrichment augments discovered devices but never removes them.

### Consequences

- Host counts remain stable.
- Missing enrichment data does not remove devices.
- Classification always operates on the complete discovered network.

---

## ADR-002 — RuleResult

**Status:** Accepted

### Decision

Every classification rule returns a `RuleResult`.

### Rationale

This provides structured evidence for every evaluated rule and enables explainable classification.

### Consequences

- Developer tooling can display rule evidence.
- Future confidence scoring can build on the existing model.
- Classification behavior remains deterministic.

---

## ADR-003 — First Match Wins Classification

**Status:** Accepted

### Decision

Classification evaluates rules in deterministic order and stops after the
first matching RuleResult.

### Rationale

The project originally used first-match-wins classification. This behavior
was intentionally preserved during the RuleResult migration to ensure
behavioral stability while introducing structured rule evidence.

### Consequences

- Classification remains deterministic.
- Rule ordering remains significant.
- Future confidence-based classification can be introduced without changing
  the RuleResult contract.

---

## ADR-004 — Read-Only Evidence API

**Status:** Accepted

### Decision

DeviceClassifier exposes classification evidence through the public
`get_last_rule_results()` API.

### Rationale

Developer tooling should consume a stable public interface rather than
accessing classifier internals.

This separates evidence consumers from classifier implementation details.

### Consequences

- Internal classifier state remains encapsulated.
- The Classification Workbench can display rule evidence.
- Future developer tools can reuse the same interface.

---

## ADR-005 — Presentation Never Modifies Classification State

**Status:** Accepted

### Decision

Developer-facing reports classify temporary copies of devices rather than
mutating devices stored within the project.

### Rationale

Presentation logic should never modify project data.

Reports should remain deterministic and side-effect free.

### Consequences

- Report generation cannot accidentally alter device classifications.
- Diagnostic tooling is safe to execute repeatedly.
- Exporters remain read-only consumers of project data.

