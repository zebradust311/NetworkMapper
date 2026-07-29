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

---

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

This provides structured evidence for every evaluated rule and enables
explainable classification.

### Consequences

- Developer tooling can display rule evidence.
- Future confidence scoring can build on the existing model.
- Classification behavior remains deterministic.

---

## ADR-003 — First Match Wins Classification

**Status:** Accepted

### Decision

Classification evaluates rules in deterministic order and stops after the
first matching `RuleResult`.

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

---

## ADR-006 — Benchmark Framework

**Status:** Accepted

### Decision

Benchmarking is implemented as developer tooling separate from production
classification.

### Rationale

Accuracy measurement should never modify production behavior.

### Consequences

- Benchmark datasets become regression assets.
- Classification quality becomes measurable.
- Future reporting can build on the same framework.

---

## ADR-007 — Developer Platform

**Status:** Accepted

### Decision

Developer automation is implemented through the `devtools` package using a
single command entry point:

```text
python -m devtools
```

Individual developer workflows are exposed as subcommands rather than
standalone scripts.

Current commands include:

- validate
- benchmark
- compare

### Rationale

As NetworkMapper evolved, developer workflows became increasingly repetitive
and difficult to maintain when implemented as individual commands or
IDE-specific procedures.

A single automation interface provides a consistent experience for both human
developers and AI assistants while keeping engineering workflows independent
of any specific development environment.

Developer automation should orchestrate existing project services rather than
duplicate production logic.

### Consequences

- Developer workflows have one canonical entry point.
- Validation, benchmarking, and comparison share a consistent interface.
- Future developer tooling extends the existing platform rather than creating
  standalone scripts.
- Engineering workflows become easier to document, automate, and maintain.
- Development workflows are independent of IDE-specific validation mechanisms.

---

## ADR-008 — Discovery is Immutable, Interpretation is Adjustable

**Status:** Accepted

### Context

During FEAT-001 Phase A, we recognized that legacy classifier rules contained a mixture of product identifiers, operational conventions, and customer-specific naming patterns accumulated over the project's evolution. For example `vsh` (a single observed customer
convention), `vmhost` (generic administrator naming), `esx` (legacy VMware
naming), `esxi` (current VMware naming), `vcenter` (a high-confidence product
identifier), and `vm` (vendor-agnostic virtualization terminology).

These conventions are not equivalent. Some are one-time observations, some
are generic patterns, and some are strong product identifiers. Encoding all
of them as permanent classification rule keywords conflates what was actually
observed with what NetworkMapper concludes that observation means.

This conflation already exists structurally today. `Device`
([networkmapper/core/models.py](../networkmapper/core/models.py)) stores raw
discovery facts (`hostname`, `vendor`, `open_ports`, `detected_services`,
`operating_system`) and the derived `device_type` on the same mutable object,
and `DeviceClassifier.classify()` overwrites `device_type` in place (see
[docs/architecture/classification.md](architecture/classification.md)).
There is currently no structural separation between what was discovered and
what NetworkMapper concluded from it.

The project has already accepted this same kind of separation in narrower
form: `RuleResult` separates a rule's evidence from its conclusion within a
single classification pass (ADR-002), and presentation logic never mutates
stored discovery or classification state (ADR-005). The Knowledge Framework
([docs/knowledge/](knowledge/README.md)) separately distinguishes raw Field
Observations from corroborated Knowledge. This ADR generalizes the same
principle to the relationship between discovery and interpretation across
the device's lifetime, including rescans and any future manual override
capability.

### Decision

NetworkMapper treats discovery and interpretation as two distinct categories
of information:

- **Discovery** is the record of what was directly observed — hostnames,
  vendors, open ports, detected services, operating system signatures, and
  similar raw facts obtained from a `DiscoveryProvider`.
- **Interpretation** is any engineering conclusion drawn from discovery —
  device type classification, operational role, confidence, and similar
  derived judgments.

Interpretation may originate from automated classification or from explicit engineering judgment, but it must always remain traceable to the discovery evidence that informed it.

A recorded observation is immutable. A subsequent scan creates a new observation. Interpretation is adjustable — through re-classification, through evolving classification rules, or through any
future manual override capability — without altering the discovery record it
was derived from.

### Rationale

- Naming conventions and deployment patterns observed in the field (see
  FEAT-001 Phase A and [docs/knowledge/](knowledge/README.md)) vary by
  customer, vendor, and era, and can never be fully enumerated as
  classification rules. Treating every observed convention as a permanent
  rule change conflates a single observation with a durable engineering
  conclusion.
- Keeping discovery immutable preserves an authoritative, replayable record
  of what was actually seen, independent of how NetworkMapper's
  interpretation of that evidence evolves over time.
- Keeping interpretation adjustable allows classification to improve through
  the Knowledge Framework's lifecycle — Observation → Knowledge → Benchmark
  → Classification → Validation → Architecture Review (see
  [docs/knowledge/KNOWLEDGE-LIFECYCLE.md](knowledge/KNOWLEDGE-LIFECYCLE.md))
  — without requiring discovery to be re-run or discarded.
- This is consistent with, and extends, decisions already accepted elsewhere
  in the project: ADR-002 separates evidence from conclusion within a single
  classification pass; ADR-005 ensures presentation never mutates stored
  state. This ADR extends the same discipline across time — across rescans
  and any future manual override capability.

### Consequences

- Rescans must be able to update discovery without silently discarding
  engineering knowledge attached to interpretation, such as a manual
  override or the rationale for a prior classification. How that is
  preserved is future work; this ADR establishes only the principle.
- Any future manual override capability adjusts interpretation, never
  discovery. An override changes what NetworkMapper concludes about a
  device, not what was actually observed about it.
- Classification rules remain the current mechanism for producing
  interpretation from discovery (ADR-002, ADR-003) and are unchanged by this
  ADR. This ADR does not modify `DeviceClassifier`, `RuleResult`, or any
  classification rule.
- The current `Device` model does not yet structurally separate discovery
  fields from `device_type`. This ADR does not change that model now; it
  establishes the principle that future schema, persistence, or UI work must
  follow.
- This ADR does not implement persistence, configuration, database schema,
  or UI. Those remain explicitly deferred.

### Future Work

The following are explicitly deferred and are not authorized by this ADR:

- A persisted schema that structurally separates discovery fields from
  interpretation fields.
- A mechanism for recording, storing, and reconciling manual overrides with
  subsequent rescans.
- A merge strategy for how a rescan reconciles newly discovered facts with
  previously recorded discovery, without discarding interpretation history.
- Any UI or reporting concepts for presenting discovery separately from
  interpretation.

Each of the above requires its own approved sprint and, per
[ENGINEERING.md](../ENGINEERING.md), its own updates to `ROADMAP.md`,
`docs/architecture/`, and `docs/ADR.md`.

### Engineering Philosophy

This decision reinforces existing NetworkMapper principles rather than
introducing new ones. [ENGINEERING.md](../ENGINEERING.md) already states that
discovery gathers facts, intelligence interprets facts, and exporters present
facts. It also already calls for evidence-driven engineering: classification
changes should be justified by corroborated evidence, not accumulated as
permanent rule exceptions for every observed convention.

Explainability remains the deciding constraint. Because interpretation is
kept separate and adjustable, NetworkMapper can explain not only what it
concluded, but that the conclusion is distinct from, and does not overwrite,
what was actually observed.

"If you can't make it perfect, make it adjustable."
Network discovery operates in environments shaped by years of accumulated operational decisions, legacy systems, and inconsistent naming conventions. Rather than attempting to encode every possible convention into automated logic, NetworkMapper preserves objective discovery while allowing engineers to adjust interpretations explicitly and transparently. The software's goal is not to eliminate engineering judgment, but to support and preserve it