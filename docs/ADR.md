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
Network discovery operates in environments shaped by years of accumulated operational decisions, legacy systems, and inconsistent naming conventions. Rather than attempting to encode every possible convention into automated logic, NetworkMapper preserves objective discovery while allowing engineers to adjust interpretations explicitly and transparently. The software's goal is not to eliminate engineering judgment, but to support and preserve it.

---

## ADR-009 — Per-Service Discovery Evidence Is a Correlated Record

**Status:** Accepted

### Context

During FEAT-003A (Discovery Capability Assessment), the two highest-value
near-term discovery improvements identified were: recovering service
product/version/CPE data that Nmap's `-sV` already returns during
STANDARD-profile enrichment but that `NmapProvider._extract_detected_services()`
currently discards
([networkmapper/discovery/nmap_provider.py](../networkmapper/discovery/nmap_provider.py)),
and adding a small number of targeted NSE scripts (`http-title`,
`ssl-cert`, `smb-os-discovery`) on ports already scanned. Both are
inherently per-port facts.

FEAT-003B (Discovery Evidence Model Investigation) found that `Device`'s
existing representation of per-port evidence —
`open_ports: list[int]` and `detected_services: list[str]`
([networkmapper/core/models.py](../networkmapper/core/models.py)) — are
two independent lists, each built by a separate loop over Nmap's scan
result and independently sorted (`open_ports` numerically,
`detected_services` alphabetically). No code anywhere in the repository
correlates a specific entry in one list to a specific entry in the other;
every existing classification rule only asks "is port P open?" or "is
service S present?" as independent yes-or-no signals. This has never
surfaced as a defect because no evidence collected so far has needed the
correlation — but product, version, HTTP title, and TLS certificate
evidence all do: they are meaningless, or actively misleading, without
knowing which port they were observed on.

ARCH-002A (Per-Service Discovery Evidence Architecture Review) evaluated
three representations against this requirement and against existing
repository patterns, and recommended a correlated per-service record.

### Decision

Per-service discovery evidence is represented as a list of explicitly
named, typed records on `Device` — one record per observed open port —
rather than as independent parallel lists. Each record correlates, at
minimum, the port, the protocol used to reach it, and whatever
service/product/version evidence discovery obtained for that port.

Fields are added to this record the same way fields have always been
added to `Device`: as explicit, named attributes. A generic, untyped
metadata dictionary is explicitly rejected as the shape of this record
(see Alternatives Considered).

This decision establishes the representational principle only. It does
not itself change `Device`, `NmapProvider`, `ProjectSerializer`,
`BenchmarkRunner`, the Classification Workbench, or any classification
rule — see Future Work.

### Alternatives Considered

**Retain the parallel-list model (no change).** Zero migration cost, but
structurally unable to express the evidence this decision exists to
support — a device with product/version data on some but not all open
ports has no way to express which entry in a third or fourth parallel
list corresponds to which port. Rejected: the correlation gap this ADR
resolves would simply be inherited by any new field added this way,
compounding rather than closing it.

**A generic per-port metadata dictionary** (e.g., a list of dicts with an
open-ended `metadata` key). No precedent exists anywhere in the current
codebase for a generic, untyped model field — every field ever added to
`Device` is explicitly named and typed. A generic dictionary also works
against the explainability the classification subsystem is built around:
`RuleResult.reason` strings describe named evidence, and
[docs/architecture/classification.md](architecture/classification.md)
names explainability as a defining characteristic of the subsystem.
Rejected in favor of explicitly named fields.

**A dict-based port-to-evidence correlation index** (e.g., a separate
`dict[int, str]` per attribute). Functionally equivalent to the record
approach but untyped, and would require a new dict per new attribute,
recreating the parallel-list problem one level down. Dominated by the
selected record approach on every evaluated criterion; rejected without
extended analysis.

**An independent, device-external service entity** (a second top-level
collection alongside `NetworkGraph`, cross-referenced by device IP). No
repository evidence supports it: `NetworkGraph` has exactly one
collection today, keyed by device IP, and nothing about per-service
evidence requires independent addressability. Rejected as an unjustified
abstraction.

### Rationale

- This decision does not modify ADR-001 (Two-Phase STANDARD Discovery).
  It changes what the enrichment phase writes into, not the two-phase
  structure itself.
- This decision extends, without modifying, ADR-008 (Discovery is
  Immutable, Interpretation is Adjustable). ADR-008 explicitly deferred
  "a persisted schema that structurally separates discovery fields from
  interpretation fields" as future work requiring its own approved
  sprint. This ADR is that follow-on work, scoped narrowly to the
  per-service portion of the discovery record; it does not undertake the
  full discovery/interpretation schema separation ADR-008 left open, and
  `device_type` remains outside this decision's scope entirely.
- This decision does not modify ADR-002 (RuleResult), ADR-003 (First
  Match Wins Classification), or ADR-004 (Read-Only Evidence API).
  Classification rules gain the option to consume correlated evidence;
  the rule contract, evaluation order, and evidence API are unaffected.
- Explicit, named fields over a generic metadata container is consistent
  with [ENGINEERING.md](../ENGINEERING.md)'s coding standards ("Prefer
  dataclasses for models," "Prefer explicit names") and with the
  incremental, named-field pattern every prior `Device` field has
  followed.
- The compositional shape — a model containing a list of smaller typed
  records — is not new to the codebase: `Project` already contains
  `NetworkGraph` as a nested field, and `NetworkGraph` already contains a
  keyed collection of `Device` objects.

### Consequences

- Future per-port or per-interface discovery evidence (service
  version/product now; SNMP, LLDP/CDP, or other per-interface evidence
  later) has an established representational pattern to follow, rather
  than each future sprint re-deriving or inconsistently resolving the
  same correlation question.
- `open_ports` and `detected_services`, as independent parallel lists,
  are superseded as the representation for per-port evidence. Whether
  they are removed outright, retained temporarily as derived convenience
  views during a migration, or deprecated gradually is implementation
  work deferred to FEAT-003C.
- Classification rules that currently call
  `first_matching_port`/`first_matching_service` against the flat lists
  will need to be migrated, or those helpers re-implemented against the
  new structure, as part of FEAT-003C — not part of this decision.
- `ProjectSerializer`, `BenchmarkRunner.load_inventory()`, and the
  Classification Workbench display will each need updates to read/write
  the new structure as part of FEAT-003C. This ADR does not design those
  changes.
- FEAT-003B separately identified that `open_ports`/`detected_services`
  are not currently persisted by `ProjectSerializer` at all (a
  pre-existing defect, not introduced by this decision). Whether and how
  that gap is closed is a FEAT-003C implementation decision this ADR does
  not resolve.

### Future Work

The following are explicitly deferred and are not authorized by this ADR:

- The exact field set and types of the per-service record (this ADR
  establishes that it is a named, typed record — not a generic
  dictionary — but not its final field list).
- Whether `open_ports`/`detected_services` are removed, retained as
  derived views, or deprecated gradually.
- Migration of `NmapProvider`, `ProjectSerializer`, `BenchmarkRunner`,
  the Classification Workbench, and existing classification rules to the
  new structure.
- Any new NSE-script-driven evidence collection (`http-title`,
  `ssl-cert`, `smb-os-discovery`) — this ADR settles only how such
  evidence would be represented once collected, not the collection work
  itself.
- Fixing the pre-existing `open_ports`/`detected_services` persistence
  gap identified in FEAT-003B.

Each of the above belongs to FEAT-003C and, per
[ENGINEERING.md](../ENGINEERING.md), any further architectural questions
it surfaces should stop and report rather than be resolved silently
mid-implementation.

---

## ADR-010 — Enrichment Providers Operate on Already-Discovered Devices

**Status:** Accepted

### Context

ARCH-012 (SNMP Provider Architecture) evaluated how to integrate SNMP as
NetworkMapper's first evidence source that is structurally unlike Nmap.
ARCH-003/BENCH-002 had already established that SNMP's highest-value
evidence (`sysDescr`/`sysObjectID`) is only useful as enrichment of hosts
another source already found — SNMP has no host-discovery role of its
own.

`DiscoveryProvider`
([networkmapper/discovery/provider.py](../networkmapper/discovery/provider.py))
defines exactly one method, `discover(self) -> list[Device]`, with no
input. Every implementation is expected to be fully self-contained: it
decides what to scan, scans it, and returns finished `Device` objects.
`DiscoveryEngine`
([networkmapper/discovery/discovery_engine.py](../networkmapper/discovery/discovery_engine.py))
concatenates every provider's returned devices into one flat list before
classifying and inserting each into `NetworkGraph`. `NetworkGraph.add_device`
([networkmapper/core/network_graph.py](../networkmapper/core/network_graph.py))
is a first-write-wins keyed dict.

This composes safely today only because exactly one `DiscoveryProvider`
(`NmapProvider`) is ever registered. `NmapProvider` itself already
contains, privately, the exact shape SNMP needs: `_discover_with_enrichment()`
builds an IP-keyed `devices_by_ip` dict from its own host-discovery
phase, then writes enrichment evidence (`services`, `operating_system`,
`computer_name`, `domain`, `smb_signing`) into those same objects by
IP — a merge pattern scoped privately inside one class rather than a
capability `DiscoveryEngine` understands. Adding SNMP as a second,
independent `DiscoveryProvider` would not be safe: a `Device` it
produced for an IP `NmapProvider` already found would either silently
overwrite that device's evidence or be silently dropped by
`NetworkGraph.add_device`, depending on registration order, with no
merge logic anywhere to prevent either outcome.

### Decision

NetworkMapper distinguishes two provider roles: `DiscoveryProvider`
(unchanged — finds hosts and returns `Device` objects) and a new
`EnrichmentProvider`, which receives the already-discovered device set
and adds evidence to it in place. An `EnrichmentProvider`:

- never introduces a `Device` for an IP not already present in the set
  it was given, and never removes one — it has no host-discovery role,
  structurally, not by convention;
- merges evidence field-by-field, fallback-only — an `EnrichmentProvider`
  never overwrites a field another source already populated, only fills
  fields left empty, generalizing the precedent `NmapProvider` already
  established internally for its SMB/RDP identity merge
  ([networkmapper/discovery/nmap_provider.py:266-284](../networkmapper/discovery/nmap_provider.py));
- must never raise out of its enrichment call for an expected per-device
  failure (a timeout, a malformed response, a missing credential) — a
  failure for one device must degrade to "no additional evidence for
  this device" and must not affect any other device or stop the run;
- is optional purely by construction: it is simply absent from
  `DiscoveryEngine`'s enrichment-provider list when its prerequisites
  (e.g. credentials) are not supplied, the same "safe no-op when nothing
  is wired up" pattern `RuntimeEventBus` already uses for subscribers
  with no subscribers.

`DiscoveryEngine.discover()` runs every registered `DiscoveryProvider`
first and deduplicates their combined output by IP, then runs every
registered `EnrichmentProvider` against that already-built device set,
then classifies. This is an ordering change to shared orchestration
code, not a behavior change for the existing single-provider case —
`NmapProvider` and its internal two-phase enrichment are unaffected.

This decision establishes the representational and orchestration
principle only. It does not itself implement `EnrichmentProvider`, SNMP,
or any change to `NmapProvider` — see ARCH-012's Implementation
Sequence.

### Alternatives Considered

**Extend `DiscoveryProvider.discover()` to accept an optional
already-discovered device list as input** (e.g. `discover(self,
known_devices: list[Device] | None = None)`). Rejected: this forces
every `DiscoveryProvider` implementation, including `NmapProvider`, to
carry a parameter only some implementations use, and does not by itself
solve the merge-by-IP problem — a provider given `known_devices` would
still need to implement the same fallback-merge logic ARCH-012 requires,
just without a distinct type to signal that this provider's contract is
fundamentally different from a host-discovery provider's.

**Bundle SNMP into `NmapProvider` itself**, as another argument/script
addition the way NSE scripts are added today. Rejected: SNMP is a
different transport and technology (UDP/community-string/SNMP PDU
encoding via a dedicated client, not an Nmap NSE script), with its own
credential, timeout, retry, and failure-diagnosis model. Folding it into
`NmapProvider` would couple two unrelated collection technologies inside
one class and work against the sprint's explicit goal that
"SNMP-specific objects must not leak into classification or reporting."

**Do nothing — register SNMP as a second, independent
`DiscoveryProvider`.** Rejected for the reasons in Context: no merge
logic exists to prevent silent evidence loss or overwrite when two
providers produce a `Device` for the same IP.

### Rationale

- This decision does not modify ADR-001 (Two-Phase STANDARD Discovery).
  It generalizes the same "discovery before enrichment" ordering
  ADR-001 already established for Nmap's two internal phases to the
  provider-orchestration level, for enrichment sources external to any
  single provider.
- This decision extends, without modifying, ADR-008 (Discovery is
  Immutable, Interpretation is Adjustable). ADR-008's immutability
  principle concerns a recorded observation across scans — a rescan
  creates a new observation rather than silently overwriting a prior
  one. It does not restrict a single run's own evidence-gathering
  pipeline from writing into a `Device` incrementally as different
  sources contribute, which is already how `NmapProvider`'s own two
  phases behave today.
- This decision extends, without modifying, ADR-009 (Per-Service
  Discovery Evidence Is a Correlated Record). ADR-009 settled how
  per-service evidence is represented once collected; this ADR settles
  a distinct question — how a source that only enriches, and never
  discovers, participates in the collection pipeline that produces the
  `Device` objects ADR-009's records live on.
- The fallback-only merge rule is not new — it generalizes a pattern
  `NmapProvider` already uses for SMB/RDP identity evidence to any
  future `EnrichmentProvider`, rather than each future enrichment source
  re-deriving or inconsistently resolving the same precedence question.

### Consequences

- `EnrichmentProvider` is a new abstract class alongside
  `DiscoveryProvider`; `DiscoveryEngine` gains a second, optional
  provider collection and a second orchestration phase between
  discovery and classification.
- `DiscoveryEngine.discover()`'s internal device-collection step now
  deduplicates by IP before classification, closing a latent gap that
  existed only in principle until now: today, with a single registered
  `DiscoveryProvider`, two providers producing a `Device` for the same
  IP was not a case that could occur.
- SNMP (ARCH-012) becomes the first concrete `EnrichmentProvider`. Any
  future non-Nmap evidence source that only adds evidence to
  already-discovered hosts (rather than finding hosts itself) follows
  this same pattern rather than each proposing its own merge strategy.
- Nothing about `DiscoveryProvider`, `NmapProvider`'s scan behavior, or
  any classification rule changes as a result of this decision.

### Future Work

The following are explicitly deferred and are not authorized by this
ADR:

- The concrete `EnrichmentProvider` implementation, SNMP or otherwise —
  scoped to ARCH-012's Implementation Sequence (FEAT-005).
- Any credential-handling mechanism, telemetry phase, or failure-model
  detail specific to SNMP — see ARCH-012 for those decisions.
- Whether `EnrichmentProvider`s should ever run concurrently with each
  other or with `DiscoveryProvider`s — ARCH-012 recommends serial
  execution for SNMP's first implementation, deferring concurrency
  pending measurement.

---

## ADR-011 — Bounded Canonical Observation Model

**Status:** Accepted

### Context

ARCH-014 (Relationship Evidence Architecture) found that relationship
resolution requires retained, provider-attributed observations, because
corroboration cannot be performed once evidence has been collapsed into
a single merged value — `NetworkGraph.add_device`
([networkmapper/core/network_graph.py:15-19](../networkmapper/core/network_graph.py))
has no representation for a relationship at all, and no collapsed
`Device` field could express one even if it did.

ARCH-015 (Canonical Device Identity Investigation) independently reached
the same structural conclusion for device identity: no single field is
unconditionally safe as identity evidence, and resolving identity
requires the same retained-observation capability — provenance,
corroboration across independent sources, and an explainable, non-scored
confidence outcome — that ARCH-014 already required for relationships.

ARCH-016 (Canonical Observation Architecture) evaluated whether this
convergence implies a universal observation layer throughout
NetworkMapper, and found it does not. Its conclusion was narrower: a
generalized observation model is justified for identity resolution and
relationship resolution specifically. It is not currently justified as a
replacement for `Device`, classification, reporting, project
serialization, or any other already-stable, already-validated Phase 2
subsystem (ARCH-013's own Section 3, "Validated Decisions," is the
direct evidence those subsystems are working as designed and have no
demonstrated need for raw observations).

ARCH-016 also found a concrete naming collision that this ADR must
record explicitly rather than leave implicit:
`networkmapper.knowledge.models.Observation`
([networkmapper/knowledge/models.py:120-138](../networkmapper/knowledge/models.py))
already exists, but is a different concept from the one ARCH-014/
ARCH-015 require — it is whole-device, episodic (captured only for
`DeviceType.UNKNOWN` devices, per `should_capture()`,
[networkmapper/knowledge/capture.py:24-32](../networkmapper/knowledge/capture.py)),
and built *from* already-collapsed `Device` state after the fact, rather
than retained *before* interpretation.

Separately, ARCH-016 confirmed directly that `EnrichmentProvider`
implementations already discard provenance the moment evidence is
merged: `SnmpEnrichmentProvider._merge()`
([networkmapper/discovery/snmp_provider.py:146-155](../networkmapper/discovery/snmp_provider.py))
reads a provider's raw response and writes it directly into `Device` in
the same step, leaving only a flat, unattributed provider-name list
(`Device.discovery_sources: list[str]`) as any trace that collection
occurred at all — no per-field timestamp, method, or independence
information survives.

This ADR formalizes the bounded architectural boundary ARCH-014,
ARCH-015, and ARCH-016 converged on, so that any future implementation
work proceeds against one recorded decision rather than three separate,
unreconciled investigation reports.

### Decision

NetworkMapper introduces a first-class retained observation concept,
scoped specifically to the subsystems that require individual,
provider-attributed evidence:

- canonical identity resolution (ARCH-015);
- relationship resolution (ARCH-014);
- future lifecycle/change-detection analysis, where reasoning about
  historical evidence (not just current state) is required.

The observation layer does **not** replace `Device`. `Device` remains
the canonical current-state representation used by classification,
reporting, project serialization, and developer tooling, unless a future
ADR explicitly changes that boundary.

#### Observation Semantics

A retained observation represents one direct claim produced by an
evidence source. An observation must conceptually carry enough
information to answer: what subject was observed; what property or
relationship was observed; what value or claim was reported; which
provider produced it; how it was collected; when it was observed; and
what source/run it belongs to. This ADR does not define a concrete
class, field list, or persistence format for that record — the exact
implementation shape is deferred (see Future Work).

#### Immutability

Recorded observations are immutable evidence. A later observation never
overwrites an earlier one. A later observation may corroborate it,
contradict it, supersede it for the purpose of current-state
interpretation, or leave an earlier interpretation stale — but the
original observation is always preserved. This generalizes ADR-008's
existing principle ("A recorded observation is immutable. A subsequent
scan creates a new observation") from `Device`-level discovery to the
observation layer directly: interpretations may change; observations do
not.

#### Canonical Device Boundary

`Device` remains the current believed/canonical state of a discovered
device. The observation layer exists behind the consumers that require
retained evidence, not in front of every consumer. Existing `Device`
fields are not required to be reimplemented as observations by this
decision. Classification continues to operate against canonical `Device`
state; reporting continues to operate against canonical `Project`/
`Device` state. This preserves the deterministic, explainable, and
independently validated Phase 2 architecture (ADR-002, ADR-003, ADR-004;
ARCH-013 Section 3) rather than placing new requirements on either
subsystem.

#### Observation Consumers

Direct consumers of retained observations: identity resolution,
relationship resolution, and future lifecycle/change-detection analysis
where historical observations are required.

Consumers of canonical state, unaffected by this decision: classification,
reporting, and existing exporter logic.

Knowledge (KNOW-003) remains an open question and is explicitly
unchanged by this ADR. `capture_unresolved_device()` and
`ObservationRepository` continue to operate exactly as they do today.
This ADR records explicitly that
`networkmapper.knowledge.models.Observation` represents a different
concept from the canonical retained observation described here, and
must not be silently reused as that primitive by a future
implementation.

#### Existing Observation Naming Collision

`networkmapper.knowledge.models.Observation` is whole-device, episodic,
currently focused on unresolved (`UNKNOWN`) classification cases, and
created after `Device` state has already been formed. The canonical
retained observation concept described by this ADR is per-claim or
per-relationship, provider-originated, retained *before* interpretation,
and required independently of classification outcome. These are
architecturally distinct concepts that happen to share a name. This ADR
records the collision; it does not resolve the naming question. Whoever
implements this decision must address it explicitly — by renaming,
namespacing, or otherwise distinguishing the two — before introducing
concrete types.

#### Provenance

Per-observation provenance is required. At minimum, the architecture
must preserve enough context to determine the originating provider, the
collection method, the observation timestamp, and the source/run
identity. `Device.discovery_sources`
([networkmapper/core/models.py:113](../networkmapper/core/models.py)), a
flat `list[str]` of provider names with no per-field or per-observation
attribution, is confirmed insufficient for this purpose — it can say
that a provider contributed *something*, never which specific claim, when,
or by what method.

#### Observation Independence

Corroboration strength depends on independent evidence, not merely the
number of matching fields. Two observations that originate from the same
underlying collection operation must not automatically count as two
independent confirmations. This ADR does not define the independence
taxonomy — it establishes only the architectural requirement that
collection-method provenance must exist so a future resolver can make
that distinction deterministically, rather than by counting fields
alone.

#### Corroboration

The observation layer does not assign numeric confidence scores. Future
identity and relationship resolvers may derive discrete, explainable
states from retained observations — for example, weak, probable,
confirmed, corroborated, or conflicting — but those taxonomies belong to
their own respective future ADRs, not this one. This ADR establishes
only that retained observations are what makes deterministic,
explainable corroboration possible at all, consistent with
NetworkMapper's existing preference for deterministic, explainable
reasoning over confidence scoring (`RuleResult.confidence_contribution`'s
long-standing, deliberate non-use is the existing precedent for this
restraint).

#### Staleness

An observation does not become false merely because it is old. Staleness
belongs to the interpretation built from observations, not to the
observation itself — for example, a device identity not reconfirmed by
any recent scan, or a relationship not re-observed in recent runs, is
stale as an interpretation while every observation that ever supported
it remains a true, unaltered historical record. This ADR does not define
a staleness algorithm.

### Alternatives Considered

**Continue using canonical `Device` fields only (no observation layer).**
Rejected: identity and relationship corroboration lose the source,
history, and independence information they require the moment evidence
is collapsed into a single field — confirmed directly by
`EnrichmentProvider._merge()`'s existing behavior (Context), which is
exactly the collapse ARCH-014 and ARCH-015 each found blocks their
respective resolution work.

**Replace `Device` with a universal observation/event model.** Rejected:
ARCH-016 found no demonstrated need for classification or reporting to
consume raw observations instead of canonical state, and replacing a
proven, independently validated Phase 2 architecture (ARCH-013 Section
3) with a heavier model everywhere would add complexity without an
identified consumer to justify it.

**Build separate retained-evidence systems for identity and
relationships.** Rejected: ARCH-014 and ARCH-015 independently require
the same underlying provenance and retention semantics (per-observation
attribution, immutability, independence-aware corroboration, non-scored
discrete outcomes). Implementing them separately would duplicate
architecture and risk inconsistent corroboration behavior between the
two, rather than one foundation both share.

**Reuse the existing Knowledge `Observation` class directly.** Rejected:
its granularity (whole-device, not per-claim), lifecycle (episodic,
triggered only by `UNKNOWN` classification), and data-flow position
(built from already-collapsed `Device` state) do not match the per-claim,
pre-interpretation observation concept identity and relationship
resolution require, per ARCH-016's direct comparison.

### Rationale

- This decision extends, without modifying, ADR-008 (Discovery is
  Immutable, Interpretation is Adjustable). ADR-008 established the
  evidence/interpretation split for `Device`-level discovery and
  `device_type`; this ADR generalizes the identical split one layer
  earlier, for identity and relationship evidence specifically — the
  same convergence ARCH-014 Section 2, ARCH-015 Section 2, and ARCH-016
  Section 2 each independently found already follows from ADR-008's own
  stated principle.
- This decision does not modify ADR-002 (RuleResult), ADR-003 (First
  Match Wins Classification), or ADR-004 (Read-Only Evidence API).
  Classification continues consuming canonical `Device` state exactly as
  it does today (ARCH-016 Section 6); nothing about rule evaluation,
  ordering, or the evidence API changes.
- This decision does not modify ADR-009 (Per-Service Discovery Evidence
  Is a Correlated Record). `Device`'s existing per-service evidence
  pattern is unaffected, and no existing `Device` field is required to
  be migrated into an observation by this decision (Future Work).
- This decision does not modify ADR-010 (Enrichment Providers Operate on
  Already-Discovered Devices). Providers continue merging evidence into
  `Device` fallback-only, exactly as ADR-010 requires; this ADR adds
  that a provider contributing evidence identity or relationship
  resolution will consume must also preserve that evidence as a retained
  observation, a consequence for future provider work rather than a
  change to `EnrichmentProvider`'s existing contract.
- This decision is not a first architectural conclusion — it is the
  formal record of a conclusion three independent investigations (ARCH-014,
  ARCH-015, ARCH-016) already reached from three different starting
  points without being asked to reconcile with one another, which this
  ADR treats as stronger justification than any one investigation's
  finding alone.

### Consequences

- A shared evidence foundation becomes available for identity resolution
  and relationship resolution, rather than each being designed against
  its own independent provenance scheme.
- Deterministic, explainable corroboration becomes possible for both
  identity and relationships, consistent with NetworkMapper's existing
  preference for deterministic reasoning over confidence scoring.
- Explicit provenance (provider, method, timestamp, source/run) becomes
  available where none exists today beyond `Device.discovery_sources`'s
  flat, unattributed list.
- Future lifecycle/change-detection analysis (e.g., "did this field
  change between scans") becomes architecturally possible; it is not
  possible against collapsed canonical state alone, which by
  construction no longer holds prior values.
- Building one shared mechanism avoids the alternative this ADR rejects
  — two independent, duplicated provenance systems, one each for
  ARCH-014 and ARCH-015's needs.
- The existing classification and reporting architecture, and its
  independently validated determinism and stability (ARCH-013 Section
  3), is preserved unchanged.
- Model and storage complexity increases: a new retained-observation
  concept is introduced alongside `Device`, not in place of it.
- Observation volume may grow substantially once any provider begins
  producing retained observations for identity or relationship
  resolution, since retained evidence is no longer collapsed into a
  single field per provider per device.
- Persistence strategy is not yet decided by this ADR (see Future Work);
  this decision establishes the architectural boundary, not its storage
  representation.
- The naming collision with `networkmapper.knowledge.models.Observation`
  must be resolved by whichever future implementation introduces
  concrete observation types — this ADR records the collision but does
  not resolve it.
- Any future provider that contributes evidence to identity or
  relationship resolution will need to preserve that evidence as a
  retained observation before or alongside merging it into `Device`, a
  behavior change scoped to that future provider work — this ADR does
  not require any existing provider to change today.

### Future Work

The following are explicitly deferred and are not authorized by this
ADR:

- Concrete observation class names, field lists, and type definitions.
- Persistence/storage format for retained observations.
- Observation identifiers and how they are assigned.
- Any database or event-store design.
- Any change to `ProjectSerializer` or existing serialization.
- Retention policies for retained observations.
- A collection-method taxonomy sufficient to evaluate observation
  independence (Observation Independence, above).
- A full independence taxonomy for corroboration weighting.
- Identity corroboration rules — scoped to a future ADR building
  directly on ARCH-015.
- Relationship corroboration rules — scoped to a future ADR building
  directly on ARCH-014.
- Topology rendering or interpretation of any kind.
- Any change to Knowledge/KNOW-003 integration, including whether
  `networkmapper.knowledge.models.Observation` is renamed, wrapped, or
  left as-is once the canonical retained observation concept is
  implemented.
- Migration of any existing `Device` field into an observation-backed
  representation.

Each of the above requires its own approved sprint and, per
[ENGINEERING.md](../ENGINEERING.md), its own updates to `ROADMAP.md`,
`docs/architecture/`, and `docs/ADR.md`.

---

## ADR-012 — Canonical Identity Resolution

**Status:** Accepted

### Context

ADR-011 established retained observations as a bounded architectural
capability supporting identity resolution and relationship resolution,
and recorded that canonical identity should be an interpretation derived
from those observations rather than a field on `Device` itself.

ARCH-015 (Canonical Device Identity Investigation) found, against actual
identity-bearing fields NetworkMapper collects or has already
investigated collecting: no universally stable identifier exists across
all environments (MAC address is reliable for fixed infrastructure but
routinely randomized on modern client operating systems; hardware serial
numbers and SMBIOS UUIDs are strong but not guaranteed distinct across
cloning; directory identifiers such as a Windows machine SID are
regenerated on reimage even when hostname, domain, and physical hardware
are unchanged). Identity therefore cannot be reduced to any single
field, and is itself an interpretation derived from corroborated
observations, not a fact directly observed.

This ADR formalizes those conclusions into architectural policy
governing how canonical identity is derived, without defining the
resolver that will eventually implement it.

### Decision

Canonical device identity is a deterministic interpretation derived from
retained observations (ADR-011). Identity shall never be established
solely because a particular field is present or populated. Instead,
identity results from corroborated observations evaluated under
architectural rules established here and refined by future,
narrower ADRs. No single observation is inherently canonical; canonical
identity is always an interpretation built from the retained observation
set, never a property copied directly from one field.

#### Identity Principles

- **Identity is evidence-driven.** Identity conclusions are traceable to
  specific retained observations, never asserted independently of them.
- **Identity is deterministic.** The same retained observation set
  produces the same identity interpretation every time it is evaluated.
- **Identity is explainable.** An identity interpretation must be
  statable in terms of which observations support it, consistent with
  `RuleResult.reason`'s existing role for classification (ADR-002).
- **Identity evolves only when new observations justify change.**
  Consistent with ADR-008's adjustable-interpretation principle,
  generalized from `device_type` to identity.
- **Interpretations may change. Retained observations do not.** Directly
  restates ADR-011's immutability principle at the identity layer rather
  than introducing a new one.
- **Identity must never depend on provider ordering.** Identity
  resolution must produce the same result regardless of the order in
  which equivalent observations are processed or arrive. This is a
  materially different determinism requirement from classification's:
  `DeviceClassifier` is deterministic *because* rule order is fixed and
  evaluation always stops at the first match (ADR-003) — determinism
  through a stable, order-*dependent* sequence. Identity resolution
  cannot rely on a stable arrival order, because observations may arrive
  from different providers across different runs in no guaranteed
  sequence; its determinism must instead come from order-*independence*
  — the same conclusion regardless of which equivalent observation was
  processed first. Future resolver design must treat this as a hard
  constraint, not an incidental property.

#### Identity Evidence

Observations differ in stability. ARCH-015's Identity Evidence
Assessment evaluated this in detail across Network (IP address, MAC
address), Operating System (hostname, computer name), Hardware (chassis
serial, system UUID), Virtualization (hypervisor identifiers), Directory
(machine identifiers), and Cloud (provider-specific resource
identifiers) categories, and found stability is frequently conditional
on device role or lifecycle event rather than fixed per field (Network
Interface MAC's infrastructure-vs-client split; Hardware UUID's
normal-operation-vs-cloning split).

This ADR deliberately does not prescribe a precedence hierarchy over
these categories. ARCH-015 Section 7 illustrated one possible
resolution shape — an ordered, strongest-evidence-first check, modeled
on `first_matching_identifier`'s existing pattern
([networkmapper/classification/evidence_helpers.py:67-104](../networkmapper/classification/evidence_helpers.py))
— but this ADR treats that as an implementation option for a future
resolver to evaluate, not a ranking this ADR canonicalizes. Future
implementations are required to evaluate corroborated observations
together, not select a winner by absolute field priority alone.

#### Identity Categories

Observations naturally fall into categories reflecting how they should
be weighed — ARCH-015 Section 4 evaluated candidates including
immutable, persistent, contextual, transient, and provider-specific, and
found a two-axis (stability × origin) view more precise than a single
flat list. This ADR does not freeze either ARCH-015's flat category list
or its two-axis model as canonical taxonomy — neither has been
validated against an implementation yet. The architectural decision this
ADR does make is narrower and does not depend on which taxonomy is
eventually adopted: **not all observations contribute equally to
identity**, and any future resolver must account for that difference
rather than treating every retained observation as equally probative.

#### Corroboration

- Independent observations strengthen identity.
- Conflicting observations weaken confidence — they must not be
  silently arbitrated. Consistent with ADR-011's inherited posture (via
  ARCH-014/ARCH-015) that a conflict is retained and surfaced, never
  resolved by silently discarding one side.
- A single observation rarely justifies identity by itself, since no
  field evaluated by ARCH-015 is unconditionally reliable alone.
- Identity conclusions must remain explainable in terms of which
  observations were evaluated and how they corroborated or conflicted.
- No numeric confidence score is introduced by this ADR. Future
  implementations may express corroboration as deterministic, discrete
  states (ARCH-015 Section 7 illustrated a possible shape — weak,
  probable, confirmed, conflicting — without this ADR adopting it as
  final), consistent with `RuleResult.confidence_contribution`'s
  long-standing, deliberate non-use as the existing precedent for
  preferring determinism over scoring.

#### Asset Identity vs. Instance Identity

ARCH-015 identified a real architectural fork this ADR preserves rather
than resolves: a motherboard replacement, a VM clone, and a reimaged
workstation each affect different concepts of identity. A reimaged
workstation typically keeps its chassis serial (the physical asset is
unchanged) while its Windows machine SID or machine GUID is regenerated
(the software instance is new); a motherboard replacement may change a
board-level identifier while the chassis serial persists. **Asset
identity** (tracking the physical or virtual-hardware unit) and
**instance identity** (tracking the running OS/software instance) are
distinct architectural concerns, and this ADR records that distinction
explicitly rather than assuming NetworkMapper's canonical identity
answers only one of them. This ADR does not decide which concept (or
both) NetworkMapper's canonical identity should track — that decision is
left to future work (see Deferred Decisions), because it affects
resolver design directly and none of ARCH-015, ADR-011, or this ADR has
resolved it.

#### Identity Lifecycle

Identity resolution distinguishes several architecturally different
moments, none of which this ADR defines an algorithm for:

- **Creation** — an identity interpretation is first formed from an
  initial retained observation set.
- **Corroboration** — additional independent observations strengthen an
  existing identity interpretation without replacing it.
- **Reinterpretation** — new observations change what an identity
  interpretation concludes, without altering any retained observation
  (ADR-008, ADR-011).
- **Replacement** — evidence indicates the underlying device itself has
  changed (ARCH-015's Device Replacement case), and a new identity is
  warranted rather than a revised interpretation of the same one.
- **Retirement** — an identity interpretation is no longer supported by
  recent observations (a staleness concern, per ADR-011, belonging to
  the interpretation layer, not to any observation becoming false).

Identity changes must result from evidence. Identity must not mutate
arbitrarily — consistent with the determinism and explainability
principles above.

#### Relationship with Device

`Device` remains the canonical current-state representation, per
ADR-011's Canonical Device Boundary. Identity interpretation supports
`Device`; it does not replace it, and `Device` does not become the
identity engine — identity resolution is a distinct interpretive layer
consuming retained observations, not logic added to `Device` or
`NetworkGraph`. This ADR does not redesign either.

#### Relationship with Future ADRs

Relationship resolution (ARCH-014, scoped as future work under ADR-011)
depends on canonical identities: ARCH-014 Section 7 and ARCH-015 Section
1 both already found that a relationship between two devices cannot be
recognized as the same relationship across scans unless its endpoint
devices can first be recognized as the same devices. Topology, in turn,
depends on canonical relationships (ARCH-014 Section 2). This ADR
therefore architecturally precedes, and is a prerequisite for, both a
future relationship-corroboration ADR and any future topology work.

### Alternatives Considered

**Use one universally stable identifier.** Rejected — ARCH-015
demonstrated no such identifier exists across all environments: every
candidate evaluated (MAC, hardware serial, SMBIOS UUID, directory
identifiers) is stable only under specific conditions of device role,
collection method, or lifecycle event, never unconditionally.

**Use IP address as canonical identity.** Rejected — IP addresses
change under ordinary, routine conditions (DHCP lease renewal, static
reassignment) and do not uniquely identify a long-term asset, which is
the exact overloaded use of IP address ARCH-014 and ARCH-015 both
identified as the originating problem this investigation lineage exists
to correct.

**Use first-provider-wins.** Rejected — identity must remain
deterministic regardless of provider ordering (Identity Principles,
above); a first-provider-wins rule would make identity dependent on
incidental scan/enrichment sequencing, which is not guaranteed stable
run over run.

**Treat every identity change as a new device.** Rejected — this
collapses the Identity Lifecycle's distinct Reinterpretation and
Replacement cases into one, and would treat ordinary, routine evidence
changes (a hostname rename, an IP renewal, a newly-corroborating
observation) the same as a genuine hardware replacement, contradicting
the Identity Lifecycle section's explicit distinction.

**Allow provider-specific identity systems.** Rejected — canonical
identity must remain provider-independent, consistent with ADR-010's
existing requirement that `EnrichmentProvider`s not leak
provider-specific concepts into classification or reporting; a
provider-specific identity system would reintroduce exactly the kind of
coupling ADR-010 already ruled out for evidence generally, applied to
identity specifically. ARCH-015 Section 5 separately found some
identity-shaped identifiers (a VMware Managed Object Reference, an Azure/
Entra device ID) are inherently scoped to one management plane and are
not safe as canonical identity for this same reason.

### Rationale

- This decision extends, without modifying, ADR-008 (Discovery is
  Immutable, Interpretation is Adjustable). Identity is the same
  evidence/interpretation split ADR-008 established for `device_type`,
  applied to identity specifically, per ARCH-015 Section 2's own
  framing.
- This decision extends, without modifying, ADR-011 (Bounded Canonical
  Observation Model). ADR-011 established that identity resolution is
  one of the two named consumers of retained observations; this ADR is
  the identity-specific policy ADR-011's own Future Work already
  anticipated.
- This decision does not modify ADR-002 (RuleResult), ADR-003 (First
  Match Wins Classification), or ADR-004 (Read-Only Evidence API).
  Identity resolution is architecturally distinct from classification —
  notably, it requires order-*independence* rather than
  classification's order-*dependent* determinism (Identity Principles,
  above) — and this ADR does not change how `DeviceClassifier` operates.
- This decision does not modify ADR-009 (Per-Service Discovery Evidence)
  or ADR-010 (Enrichment Providers Operate on Already-Discovered
  Devices). `Device`'s evidence-field pattern and `EnrichmentProvider`'s
  fallback-only merge are unaffected; this ADR governs how identity is
  *interpreted* from retained observations, not how evidence is
  collected or merged into `Device`.
- Preferring deterministic, discrete, explainable corroboration states
  over numeric confidence scoring is consistent with
  `RuleResult.confidence_contribution`'s existing, deliberate,
  long-standing non-use — the same restraint already validated for
  classification (ARCH-013 Section 7) applied to identity.

### Consequences

- Identity becomes deterministic and explainable, traceable to specific
  retained observations rather than to an arbitrarily privileged field.
- Identity resolution becomes provider-independent, consistent with
  ADR-010's existing boundary for evidence generally.
- Relationship resolution (a future ADR building on ARCH-014) becomes
  possible to sequence correctly, since it now has a formal, prerequisite
  identity policy to depend on rather than an unresolved open question.
- Future lifecycle analysis (identity creation, corroboration,
  reinterpretation, replacement, retirement) has an architectural home
  to build against.
- This decision is consistent with, and does not require reopening,
  ADR-011.
- Identity becomes an interpretation rather than a field — any future
  consumer that expects a single, directly-readable identity value on
  `Device` will need to consume an interpretation instead, a real shift
  from how every other `Device` field currently behaves.
- Implementation complexity increases: a future resolver must evaluate
  corroboration across a retained observation set rather than reading
  one field.
- Multiple observations about the same subject may remain unresolved —
  a Conflicting or Weak interpretation is an explicit, valid outcome,
  not a failure state requiring forced resolution.
- Future resolvers require the retained observations ADR-011
  established; identity resolution cannot be implemented against
  collapsed `Device` state alone.

### Future Work

The following are explicitly deferred and are not authorized by this
ADR:

- Concrete identity resolution algorithms.
- Scoring or weighting mechanisms for corroboration.
- Observation weighting by category, provider, or collection method.
- Provider-specific identity heuristics.
- Persistence strategy for identity interpretations.
- Any serialization change.
- UI or reporting presentation of identity.
- Topology.
- Relationship resolution implementation (ARCH-014) — this ADR is a
  named prerequisite for that future work, not an implementation of it.
- Whether canonical identity tracks asset identity, instance identity,
  or both (Asset Identity vs. Instance Identity, above).

Each of the above requires its own approved sprint and, per
[ENGINEERING.md](../ENGINEERING.md), its own updates to `ROADMAP.md`,
`docs/architecture/`, and `docs/ADR.md`.