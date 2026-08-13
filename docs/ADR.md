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