# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — every question this sprint's charter poses is either
already settled by ADR-011/ADR-012/ADR-013 (identity is a prerequisite for
relationship resolution; retained observations are never persisted; a
derived interpretation must remain traceable to retained observations) or
is ordinary wiring detail — which two files change, what order two already-
built pure functions are called in, whether two new fields belong on
`Project`. None of it is a new policy question. Section 11 records the one
genuine ambiguity this investigation found and declines to resolve.

Recommended Next Sprint:
FEAT-009B — Relationship Runtime Integration (Stage 2 wiring), scoped to
exactly the two-file change Section 4 and Section 12 specify: `Project`
gains two run-scoped fields, `Application.run()` calls `IdentityResolver`
and `RelationshipResolver` once, in that order, and stores their output on
the `Project` it already constructs. No new `RuntimePhase`, no exporter
change, no serializer change, no new provider. Offered as a recommendation,
not a decision — per scope, engineering review selects the next sprint.

---

## 1. Executive Summary

FEAT-009A left `RelationshipResolver` exactly where ARCH-018 and
`IdentityResolver` before it left off: a pure, fully tested,
independently-callable function that nothing in the running application
calls. This investigation traced `Application.run()` line by line
(`networkmapper/application.py:48-209`) and confirms a fact worth stating
plainly because it is easy to assume otherwise from ARCH-017/ARCH-018's own
pipeline diagrams: **neither `IdentityResolver` nor `RelationshipResolver`
executes inside `Application.run()` today.** `Project.observations` is
populated (line 136) and then never read again anywhere in `Application`.
The only place either resolver is currently invoked against a real,
Application-produced `Project` is inside
`tests/test_identity_pipeline.py`, and it invokes `IdentityResolver`
directly in the test body against a *captured* `Project` object — not
through any code path `Application.run()` itself executes. Integrating
`RelationshipResolver` into the runtime therefore also means, for the first
time, actually wiring `IdentityResolver` into the runtime — not a scope
expansion, but ADR-012's own prerequisite relationship made concrete: you
cannot call `RelationshipResolver.resolve(observations, identities)`
without first producing a real `identities` argument, and today nothing
produces one at runtime.

The integration this investigation recommends is small by construction,
not by effort-limiting: both resolvers are pure functions over data
`Application.run()` already has in hand (`engine.observations`, soon to be
`project.observations`) the moment `Project(...)` is constructed
(`application.py:133-137`). The minimal change is to compute both resolver
outputs at that exact point and pass them into the `Project` constructor
as two new fields, mirroring the `observations` field's own established
pattern exactly: run-scoped, not persisted, not consumed elsewhere yet.
This touches two files — `networkmapper/project/models.py` and
`networkmapper/application.py` — and adds no new runtime phase, no
exporter change, no serializer change, and no change to `DiscoveryEngine`,
`NetworkGraph`, `Device`, classification, or either resolver's own code
(both already meet the contract this integration needs).

The one substantive design question this investigation had to answer
rather than merely observe is where canonical identities and relationships
live once computed. Section 5 finds the answer is already implied by
precedent rather than open: `Project.observations` already establishes
that retained, run-derived state that cannot survive a save/load
round-trip belongs on `Project` as an explicitly non-persisted field, not
nowhere and not force-fit into the persisted schema. Persisting canonical
relationships while `Project.observations` (their entire evidentiary
basis) is not persisted would silently violate ADR-011/ADR-012's
traceability principle the moment a saved project is reloaded — an
interpretation with no observations behind it to explain it. Section 7
works through why this makes backward compatibility a non-event rather
than a risk to mitigate.

No production code is proposed for change by this report.

---

## 2. Direct Answers to the Charter Questions

**1. Where does the current runtime flow trace, and where does
`RelationshipResolver` belong?** `Application.run()` →
`DiscoveryEngine.discover()` (discovery, enrichment, classification) →
`Project(...)` construction → workbench/report/persistence I/O. Both
resolvers belong immediately after `engine.observations` is final and
before `Project(...)` is constructed — concretely, between line 94
(`graph = engine.discover()`) and line 133 (`project = Project(...)`
begins), computed from `engine.observations` and passed into that same
`Project(...)` call as constructor arguments, never assigned to `project`
afterward. Section 3.

**2. Which existing components require modification, and which must
remain untouched?** Modified: `networkmapper/project/models.py` (two new
fields), `networkmapper/application.py` (two resolver calls plus two
imports), and the permanent integration test. Untouched: `DiscoveryEngine`,
`NetworkGraph`, `Device`, every `DiscoveryProvider`/`EnrichmentProvider`,
`DeviceClassifier`, `CsvExporter`, `MarkdownExporter`, `ProjectSerializer`,
`RuntimeEventBus`/`RuntimePhase`, and both resolvers' own implementations
(already correct for this use). Section 4.

**3. How should canonical relationships become part of `Project`?** As a
new `canonical_relationships: tuple[CanonicalRelationship, ...]` field
(alongside a `canonical_identities: tuple[CanonicalIdentity, ...]` field
identity resolution needs first), constructed alongside `observations` at
`Project(...)` call time, never mutated afterward, and — following
`observations`'s own precedent directly — never serialized by
`ProjectSerializer`. Section 5.

**4. What is the required execution order, and why?** `IdentityResolver`
before `RelationshipResolver`, both after `DiscoveryEngine.discover()`
returns. This is not a style preference: `RelationshipResolver.resolve()`
takes `identities: Sequence[CanonicalIdentity]` as a required positional
parameter — a type-level dependency, not merely a documented one — and an
empty or stale `identities` argument does not error, it silently excludes
every relationship observation during preprocessing (`relationships/
resolver.py:103-109`), producing a misleadingly empty result rather than a
loud failure. Section 6.

**5. What must remain true for backward compatibility?** Everything,
trivially: `ProjectSerializer.save()`/`load()` build and read an explicit,
hand-enumerated JSON payload (`project/serializer.py:18-56`, `74-106`)
that never touches `observations` today and would not touch the two new
fields either, since this investigation does not propose changing the
serializer. Every existing `Project(...)` call site in the codebase (nine
files, confirmed by search) uses keyword arguments exclusively, so two new
defaulted fields cannot break any of them positionally. Section 7.

**6. What testing does runtime integration need?** No new unit tests for
either resolver — FEAT-008A and FEAT-009A already cover both exhaustively
in isolation. What's missing, and what this integration specifically
requires, is a permanent test that exercises `Application.run()`'s *actual*
internal call to both resolvers — something `test_identity_pipeline.py`
does not currently do (Section 1). Section 8.

**7. What is explicitly out of scope?** Exactly the eight items the
charter names, confirmed against the current codebase as items this
investigation touches nothing of: no new relationship provider, no
LLDP/CDP/ARP implementation, no stable identity correlation, no multi-scan
history, no executive reporting changes, no LAB research items, plus (not
separately charter-named but load-bearing) no `RelationshipResolver` or
`IdentityResolver` algorithm changes — both are correct and complete as
FEAT-009A left them. Section 9.

**8. What are the architectural risks, and what should be deferred?**
Three: wiring a resolver into a code path that raises on unexpected defects
changes today's failure characteristics (Section 10); `canonical_relationships`
will be an empty tuple on every real scan until a Stage 3 provider exists,
so this sprint's value is proving the wiring contract, not producing
relationship data yet (Section 10); and a `RuntimePhase`/OBS-002 parity
question this investigation surfaces but declines to settle (Section 11).
Recommended for deferral: any OBS-002 phase/progress-event addition for
resolution, and any exporter/report consumption of the new fields —
neither is needed to satisfy this sprint's own charter. Section 10, 12.

---

## 3. Current Runtime Flow

Traced directly against `networkmapper/application.py` and
`networkmapper/discovery/discovery_engine.py`, not inferred from prior
reports.

```
Application.run()                                    [application.py:48]
    │
    ├─ parse CLI args, resolve scan profile            [63-76]
    ├─ construct NmapProvider (+ SnmpEnrichmentProvider if --snmp)
    │                                                   [78-86]
    ├─ engine = DiscoveryEngine(providers, enrichment_providers)
    │                                                   [88-92]
    │
    ├─ graph = engine.discover()                        [94]
    │       │
    │       └─ DiscoveryEngine.discover()          [discovery_engine.py:51]
    │              ├─ run every DiscoveryProvider.discover()
    │              │    + collect_observations()          [72-78]
    │              ├─ run every EnrichmentProvider.enrich()
    │              │    + collect_observations()          [82-97]
    │              └─ _classify_devices() → NetworkGraph   [99, 103-138]
    │
    │       At this point: `graph` is final. `engine.observations`
    │       (list[IdentityObservation | RelationshipObservation]) is
    │       final. Neither IdentityResolver nor RelationshipResolver
    │       has been called anywhere in this call chain.
    │
    ├─ print diagnostics, classification summary        [96-131]
    │
    │       ← IdentityResolver / RelationshipResolver belong here
    │         (Section 6): computed from engine.observations, passed
    │         into the Project(...) call below as constructor
    │         arguments — never assigned to project afterward
    │
    ├─ project = Project(                                [133-137]
    │       customer_name=...,
    │       network_graph=graph,
    │       observations=engine.observations,
    │       canonical_identities=...,
    │       canonical_relationships=...,
    │   )
    │
    ├─ (optional) ClassificationWorkbench export         [139-146]
    ├─ CsvExporter().export(project, ...)                [163-166]
    ├─ MarkdownExporter().export(project, ..., run_metadata) [168-172]
    ├─ ProjectSerializer.save(project, ...)              [187]
    ├─ loaded_project = ProjectSerializer.load(...)      [189-191]
    └─ persistence validation (device count only)        [193-206]
```

**What already reads `Project.observations`?** Nothing in this call chain.
`ClassificationWorkbench`, `CsvExporter`, and `MarkdownExporter` all
consume `project.network_graph` (confirmed for `MarkdownExporter` via
`ProjectSummary.from_project(project)`,
`networkmapper/exporters/markdown_exporter.py:45`, which is a
`Device`/`NetworkGraph` summary, not an observation one).
`ProjectSerializer` does not read `observations` either (Section 7).
`project.observations` exists today purely so a future consumer — this
sprint's resolvers — has something to read; nothing currently reads it.

**Where `RelationshipResolver` belongs.** Immediately before `Project`
construction (`application.py:133`), computed from `engine.observations`
and passed into that same `Project(...)` call as a constructor argument —
never assigned to `project` after the fact. Section 6 states why:
constructing `Project` fully formed, in one call, is preferred to a
construct-then-mutate alternative that would leave `project` briefly
incomplete relative to its own declared fields for no benefit. This is not
a discretionary placement: it is the first point at which
`engine.observations` (equal by reference to what `project.observations`
will hold) is available inside `Application.run()`'s own scope, and
placing the calls here means resolver output already exists as part of
`project` from the moment `project` exists — available to any consumer
added later (out of this sprint's scope, per Section 9) without needing to
re-plumb `project` through an additional call or mutation.

---

## 4. Integration Boundaries

**Modified.**

- `networkmapper/project/models.py` — two new fields on `Project`
  (Section 5). No behavior change to existing fields or methods.
- `networkmapper/application.py` — two new imports
  (`networkmapper.identity.resolver.IdentityResolver`,
  `networkmapper.relationships.resolver.RelationshipResolver`) and
  approximately four new lines between the existing `graph =
  engine.discover()` call and the existing `project = Project(...)` call
  (Section 6). No change to any existing line's behavior.
- The permanent architectural integration test (Section 8) — either
  `tests/test_identity_pipeline.py` extended, or a sibling file, per
  ARCH-018 Section 10's own precedent, which left this exact choice to
  implementation time.

**Untouched, and why each is safe to leave untouched.**

- `DiscoveryEngine` — already exposes everything this integration needs
  (`self.observations`, unchanged since ARCH-017). Neither resolver reads
  `Device` or `NetworkGraph` (both resolvers' own docstrings and Section 3
  above confirm this), so nothing about discovery, enrichment, or
  classification changes.
- `NetworkGraph`, `Device` — neither resolver constructs, mutates, or
  reads either type. Confirmed directly: `IdentityResolver.resolve()` and
  `RelationshipResolver.resolve()` both take only observation/identity
  sequences as parameters (`identity/resolver.py:49-52`,
  `relationships/resolver.py:79-83`).
- `DeviceClassifier` and the classification phase — no dependency in
  either direction. `RelationshipResolver` does not run before
  classification finishes (it runs after `Project` construction, which is
  itself after classification), and classification does not read
  `Project.observations`, `canonical_identities`, or
  `canonical_relationships`.
- `CsvExporter`, `MarkdownExporter` — both are presentation layers over
  `Device`/`NetworkGraph` (`ProjectSummary.from_project`, confirmed
  Section 3). Adding two unread fields to `Project` does not change either
  exporter's output. Consuming the new fields in either exporter is
  explicitly excluded from this sprint's scope (charter: "executive
  reporting changes"; Section 9).
- `ProjectSerializer` — Section 7 shows this in full: the serializer's
  payload is a hand-enumerated allowlist that already omits
  `observations`, and this investigation does not propose adding the two
  new fields to it either, for the same traceability reason
  `observations` was already omitted.
- `RuntimeEventBus` / `RuntimePhase` — Section 11 surfaces, and declines
  to resolve, whether resolution should get its own `RuntimePhase` for
  OBS-002 observability parity. This investigation's recommendation is
  that Stage 2 wiring does not need one (Section 10), so no change to
  `runtime/events.py` is proposed.
- `IdentityResolver`, `RelationshipResolver`, and their model modules
  (`identity/models.py`, `relationships/models.py`,
  `observations/models.py`) — both resolvers already satisfy exactly the
  contract this integration calls them with. No algorithmic, interface, or
  type change is needed or proposed.

This keeps the architectural surface area to two files with real changes
and one test file — the smallest change this investigation could construct
that actually satisfies "`RelationshipResolver` runs as part of a real
scan," which is the charter's own stated goal.

---

## 5. Project Model

**The question, stated precisely.** `RelationshipResolver.resolve()`
produces `tuple[CanonicalRelationship, ...]` (and, as a precondition,
`IdentityResolver.resolve()` produces `tuple[CanonicalIdentity, ...]`).
Nothing in the codebase today holds either output anywhere a second caller
could reach it — calling both resolvers inside `Application.run()` without
storing the result anywhere would prove the call succeeds without
exception, but would produce nothing usable by anything else, including
the permanent integration test this sprint also needs (Section 8). The
output has to live somewhere.

**Why `Project` is the answer, not a new design choice.**
`Project.observations` already established the precedent this
investigation follows directly, not by analogy: it is "run-scoped only ...
does not survive a save/load round-trip. Not consumed by classification,
reporting, or any existing subsystem" (`project/models.py:19-24`, its own
docstring). Canonical identities and relationships are one interpretive
step further downstream of exactly that same run-scoped evidence, with the
identical lifecycle: valid only for the run that produced the
observations behind them, not persisted, not yet consumed elsewhere. This
investigation finds no reason the storage location should differ from
where the evidence it interprets already lives.

**Proposed shape** (for engineering review to authorize in FEAT-009B, not
implemented here):

```python
@dataclass
class Project:
    customer_name: str
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: datetime = field(default_factory=datetime.now)
    network_graph: NetworkGraph = field(default_factory=NetworkGraph)
    observations: list[IdentityObservation | RelationshipObservation] = field(default_factory=list)
    canonical_identities: tuple[CanonicalIdentity, ...] = field(default_factory=tuple)
    canonical_relationships: tuple[CanonicalRelationship, ...] = field(default_factory=tuple)
```

Both new fields default to an empty tuple, so every existing `Project(...)`
call site — nine files, confirmed by search, all keyword-argument-only —
continues to work unmodified (Section 7). `tuple`, not `list`, matches
both resolvers' own return types exactly and signals (consistent with
`CanonicalIdentity`/`CanonicalRelationship` themselves being frozen
dataclasses) that this is finished, resolved output for the run, not
something a caller should be mutating in place the way `observations` is
occasionally appended to in tests (`tests/test_project.py:41`).

**Import-cycle check.** `networkmapper/identity/models.py` and
`networkmapper/relationships/models.py` import only from
`networkmapper.observations.models` (confirmed by reading both files in
full) — neither imports anything from `networkmapper.project`. Adding
`from networkmapper.identity.models import CanonicalIdentity` and `from
networkmapper.relationships.models import CanonicalRelationship` to
`project/models.py` introduces no cycle.

**What this investigation does not propose.** No change to
`network_graph`, `created_date`, `modified_date`, `customer_name`, or any
existing field or method on `Project`. No new type beyond the two field
annotations above — `CanonicalIdentity` and `CanonicalRelationship`
already exist and need no modification. This is the full extent of "how
canonical relationships become part of `Project`"; the charter's caution
("do not redesign `Project` beyond what integration requires") is read
here as an upper bound this proposal stays inside, not a lower bound it
needs to justify meeting.

---

## 6. Runtime Ordering

**Required order:** `DiscoveryEngine.discover()` → `IdentityResolver.resolve()`
→ `RelationshipResolver.resolve()` → `Project(...)` construction (or,
equivalently in effect, `Project(...)` constructed with all three
precomputed values as arguments — Section 3's diagram places the resolver
calls textually before the `Project(...)` call for exactly this reason).

**Why this order is correct, not merely conventional.** Two independent
reasons, one architectural and one mechanical:

1. ADR-012's "Relationship with Future ADRs" section states identity
   resolution is a prerequisite for relationship resolution because "a
   relationship can't be recognized as the same relationship across scans
   unless its endpoints can first be recognized as the same devices" —
   already the accepted architectural reason, restated here because it is
   the reason, not merely cited for completeness.
2. Mechanically, `RelationshipResolver.resolve()`'s signature
   (`relationships/resolver.py:79-83`) makes this a type-level
   requirement, not a documented convention a caller could reorder without
   consequence: it requires `identities: Sequence[CanonicalIdentity]` as
   an explicit argument. There is no version of "call
   `RelationshipResolver` first" that type-checks without first having
   produced identities from somewhere. The only way to violate the
   required order is to pass a *wrong* `identities` value — e.g., stale
   identities from a previous run, or an empty sequence — which the
   resolver accepts without error (Section 1's "silently excludes every
   relationship observation" finding) rather than rejecting. This makes
   correct sequencing a caller discipline this investigation must state
   explicitly for `Application.run()`, since nothing in the resolver
   itself will catch a caller that gets it wrong.

**Concretely, in `Application.run()`:**

```python
identities = IdentityResolver().resolve(engine.observations)
relationships = RelationshipResolver().resolve(engine.observations, identities)

project = Project(
    customer_name="Test Network",
    network_graph=graph,
    observations=engine.observations,
    canonical_identities=identities,
    canonical_relationships=relationships,
)
```

`engine.observations`, not `project.observations`, is used as the input to
both calls — they are the same list object (`Project.observations` is
assigned `engine.observations` directly, not copied), so this is a choice
between two identical values, not two different ones. This investigation
recommends resolving before `Project` construction and passing all three
derived values into the constructor, rather than constructing `Project`
first and mutating it afterward with `project.canonical_identities = ...`.
The former keeps `Project` fully formed at construction time, consistent
with how `observations` itself is already passed in rather than assigned
after the fact; the latter would introduce a `Project` instance that is
briefly incomplete relative to its own declared fields, a state this
investigation sees no reason to introduce when the alternative is no more
code.

**Is there a case for running these resolvers concurrently, or
independently of one another?** No — considered and rejected. Both are
single-threaded, in-process, pure functions over already-in-memory data
(no I/O, no network call); there is no latency to hide by parallelizing,
and `RelationshipResolver`'s hard input dependency on `IdentityResolver`'s
output makes concurrent execution not merely unnecessary but incorrect.

---

## 7. Backward Compatibility

**Existing `.nmproj` files.** `ProjectSerializer.load()`
(`project/serializer.py:62-108`) constructs a `Project` by reading a fixed,
explicit set of keys from the JSON payload — `customer_name`,
`created_date`, `modified_date`, and a `devices` list — and does not read
an `observations`, `canonical_identities`, or `canonical_relationships`
key today, nor would it after this integration, since this investigation
does not propose changing the serializer (Section 5). A `Project` loaded
from a file saved before this integration ships is indistinguishable from
one saved after: both come back with `observations = []`,
`canonical_identities = ()`, `canonical_relationships = ()` — the fields'
own dataclass defaults, never populated by `load()` either way. No
migration, versioning, or compatibility shim is needed because there is no
schema change to be compatible with; the persisted schema does not change
at all.

**Existing reports.** `CsvExporter` and `MarkdownExporter` read only
`project.network_graph` (Section 4); this integration adds fields to
`Project` that neither exporter reads before or after. Report output is
byte-identical for identical discovery input, whether or not this
integration ships.

**Existing call sites.** Confirmed by search across the repository. Nine
files construct `Project(...)`
(`networkmapper/application.py`, `networkmapper/project/serializer.py`,
and seven test files); every one uses keyword arguments exclusively —
none constructs `Project` positionally past `customer_name`. Two new
fields with `field(default_factory=tuple)` defaults are additive to every
one of these call sites without modification.

**Why persisting the new fields would be a real compatibility problem,
not just extra scope.** This investigation considered, and rejects,
extending `ProjectSerializer` to persist `canonical_identities`/
`canonical_relationships` as part of this same sprint. `observations` is
not persisted today (`Project`'s own docstring states this as a deliberate
ADR-011 deferral, not an oversight). If a future reload only reconstructs
`network_graph` and never `observations`, then persisting
`canonical_relationships` — an interpretation whose entire evidentiary
basis is `observations` — would produce a reloaded `Project` carrying
conclusions with no retained evidence behind them to explain them,
directly contradicting ADR-011/ADR-012's traceability requirement ("a
canonical relationship is traceable to specific retained observations,"
ADR-013's Relationship Principles). Keeping both new fields unpersisted,
exactly like `observations`, is therefore not a gap this investigation is
leaving for later — it is the only choice consistent with the
architecture already in place, and revisiting it requires first revisiting
whether `observations` itself should be persisted (ADR-011's own
explicitly deferred question, out of this sprint's scope).

---

## 8. Testing Strategy

**No new unit tests for either resolver.** `tests/test_identity_resolver.py`
and `tests/test_relationship_resolver.py` already exercise both resolvers'
correctness exhaustively (FEAT-008A, FEAT-009A). This integration changes
neither resolver's code, so neither test file needs a change.

**What is actually missing: a test of `Application.run()`'s own wiring.**
Section 1's central finding — that today's "permanent" integration test
calls `IdentityResolver` from inside the test body against a captured
`Project`, not through any path `Application.run()` itself executes — means
no existing test would catch a regression in the wiring this sprint adds
(e.g., resolvers called in the wrong order, or their output never assigned
to `Project`). This is the one piece of new test surface this integration
genuinely requires, and it is proportional to the change: extending
`tests/test_identity_pipeline.py`'s existing `_FakeNetworkProvider`-based
harness (`tests/test_identity_pipeline.py:58-86`), the same real
`DiscoveryEngine` fed a fake, network-free `DiscoveryProvider` pattern
already proven there, to additionally assert:

- `Application.run()` completes without exception with the new wiring in
  place (extends the existing `try/except` assertion at
  `test_identity_pipeline.py:115-119`).
- The captured `Project` (already captured via the existing
  `ProjectSerializer.save` patch, `test_identity_pipeline.py:104-111`) has
  non-empty `canonical_identities` when the fake provider's observations
  resolve to identities — reusing the existing fake provider's two-device,
  three-observation fixture (`test_identity_pipeline.py:81-86`), which
  already produces the `CONFIRMED`/`WEAK` identity split the test asserts
  today.
- `canonical_relationships` is present (as an empty tuple) and does not
  raise, given the existing fake provider emits no
  `RelationshipObservation`s. Extending the fake provider to also emit a
  `RelationshipObservation` (mirroring `tests/test_relationship_resolver.py`'s
  own `_relationship_observation` helper) is worth doing in the same
  change, so this test exercises a non-empty `canonical_relationships`
  result at least once through the real `Application.run()` path, not only
  through direct resolver unit tests.
- A `ProjectSerializer.load()` round-trip (already exercised by
  `Application.run()` itself, lines 189-191) produces a `Project` whose
  `canonical_identities`/`canonical_relationships` are the field defaults
  (`()`), not whatever the pre-save `Project` held — making Section 7's
  "not persisted" claim an explicit, checked assertion rather than an
  implicit silence a future change could break unnoticed.

Whether this is implemented as an extension of the existing test class or
a new sibling file is an implementation-time call, not an architectural
one — ARCH-018 Section 10 already left the identical choice open for its
own Stage 2 test, and this investigation finds no new reason to decide it
now.

**Regression testing.** `tests/test_application_cli.py`,
`tests/test_project.py`, `tests/test_project_serializer.py`,
`tests/test_markdown_exporter.py`, `tests/test_csv_exporter.py`,
`tests/test_classification_workbench.py`, `tests/test_project_summary.py`,
and `tests/test_project_comparator.py` all construct `Project` with
keyword arguments only (Section 7) and none asserts on the full set of
`Project`'s fields via equality (spot-checked `test_project.py`, which
asserts on individual attributes, e.g. `project.observations`) — this
investigation expects all of them to pass unmodified, and recommends
running the full suite as confirmation rather than assuming it, consistent
with FEAT-008A/FEAT-009A's own validation posture
(`python -m devtools validate --all`).

**Benchmark risk.** None, by the same structural argument ARCH-017 Section
7 and ARCH-018 Section 11 already made and this investigation confirms
still holds: `BenchmarkRunner.load_inventory()` does not construct
`Project` or call `Application.run()` (neither resolver call sits anywhere
near the classification path the benchmark suite measures), so this
integration cannot regress benchmark accuracy by construction.

---

## 9. Scope Control

Confirmed against the current codebase as things this investigation's
recommendation does not touch, add, or require:

- **New relationship providers.** Zero exist today (ARCH-018 Section 3,
  reconfirmed unchanged); this investigation adds none. Wiring
  `RelationshipResolver` into the runtime with no provider emitting
  `RelationshipObservation`s means `canonical_relationships` will be an
  empty tuple on every real scan until Stage 3 (ARCH-018 Section 15)
  ships — named again in Section 10 as a risk, not hidden here.
- **LLDP/CDP/ARP implementation.** Not touched; no such provider exists
  and none is proposed.
- **Stable identity correlation.** `IdentityResolver` remains exactly the
  single-run, subject-scoped Stage 1 implementation FEAT-008A shipped
  (`identity/resolver.py:22-34`'s own docstring, unchanged). This
  integration calls that existing implementation; it does not extend or
  alter its correlation scope.
- **Multi-scan history.** `Project` remains a single-run snapshot; nothing
  here introduces cross-run storage, comparison, or history.
- **Executive reporting changes.** `CsvExporter`/`MarkdownExporter`
  untouched (Section 4); the two new `Project` fields have no consumer in
  either exporter.
- **LAB research items.** `docs/LAB.md`'s "Stable Device & Identity
  Correlation" entry is unaffected — this investigation neither advances
  nor depends on resolving it (Section 6's ordering argument holds
  regardless of that item's eventual outcome).
- **Resolver algorithm changes.** Neither `IdentityResolver` nor
  `RelationshipResolver`'s internal logic changes. Both already accept
  exactly the inputs this integration calls them with.

---

## 10. Risk Review

**`canonical_relationships` is an empty tuple on every real scan today.**
Not a defect — a direct, restated consequence of ARCH-018 Section 3/11's
already-confirmed finding that zero providers emit
`RelationshipObservation`s. This integration's value is proving the
runtime wiring contract (both resolvers are called, in the correct order,
against real `Application`-produced data, and their output lands somewhere
a future consumer can reach) — not producing non-empty relationship data,
which remains blocked on a Stage 3 provider sprint this investigation does
not authorize (Section 9). Worth naming plainly so this sprint is not
mistaken for delivering relationship *evidence*, only relationship
*wiring*. **This is the strongest argument for deferring this integration
entirely until a Stage 3 provider exists** — an option this investigation
surfaces rather than dismisses (see below), rather than a case for
resolving it here.

**Failure-mode change: exceptions now propagate through a new path.**
`EnrichmentProvider` failures are caught and degraded at the
`DiscoveryEngine` level (`discovery_engine.py:93-97`, an explicit
try/except with a comment naming it a deliberate run-level safety net).
Classification has no equivalent guard — a classifier defect propagates
and fails the run. Both resolvers are new code in `Application.run()`'s
call chain with no precedent either way *for this specific call site*.
This investigation recommends treating a resolver exception the same as a
classification exception (propagate, fail loudly) rather than the same as
an enrichment-provider exception (catch, degrade), because both resolvers
are pure functions over already-validated, already-in-memory data — a
resolver raising indicates a genuine internal defect (the kind unit tests
should have already caught), not an expected, per-host, externally-caused
failure the way an unreachable SNMP host is.

**Decision (resolved by follow-up review): resolver exceptions propagate
uncaught.** Enrichment's catch-and-degrade posture is exceptional, not
the default, because it exists specifically to absorb an irreducible
external-I/O failure mode — network unreliability that no amount of
pre-production testing can eliminate. Neither resolver crosses any such
boundary: both are deterministic, in-memory transforms over already-
collected, already-validated evidence, placing them with classification's
posture, not enrichment's. Catching a resolver exception and substituting
empty/default canonical output would also risk actively masking the
defect it was hiding: Stage 1 has zero relationship-evidence providers
(Section 9), so an empty `canonical_relationships` tuple is already the
universal, expected result on every real scan today — a caught exception
producing that same empty output would be indistinguishable from
ordinary, correct behavior for as long as the underlying defect persists.
No try/except is introduced around either resolver call in Stage 2.

**Opportunity to simplify: is Stage 2 wiring premature?** Named directly
rather than argued around: since Stage 1's own resolver is proven correct
by unit test alone, and Stage 2 wiring's only currently-observable effect
on a real scan is an always-empty `canonical_relationships` tuple, this
investigation finds a legitimate case for deferring runtime wiring until
immediately before or alongside the first real relationship-evidence
provider (ARCH-018 Section 15's Stage 3), at which point wiring and
evidence would ship together and every field this sprint adds would be
observably non-empty from day one. The competing consideration —
validating the wiring contract early and cheaply, while the change is
still small and low-risk, rather than bundling it with a larger provider
sprint later — is exactly what this investigation was chartered to
evaluate, and it does not resolve the tradeoff; it surfaces it for
engineering review's explicit call, consistent with the charter's own
instruction to recommend deferral where complexity cannot yet justify
itself.

**No `Interface`/port, no cross-run correlation, no non-`Device` endpoint
support.** All three carried forward unchanged from ARCH-014/ARCH-018;
none are affected by, or block, this integration, since Stage 2 wiring
changes nothing about either resolver's own scope or limitations.

---

## 11. Ambiguity Surfaced, Not Resolved

Per the charter's own instruction, this is recorded rather than decided.

**Should resolution get its own `RuntimePhase` for OBS-002 observability
parity?** `RuntimePhase` (`runtime/events.py:17-23`) currently names every
phase a technician watches progress on: Application Startup, Host
Discovery, Service Enrichment, SNMP Enrichment, Classification, Report
Generation, Completion. Every one of these represents either network I/O
or a per-device loop worth a progress bar. Both resolvers are neither —
single-pass, in-memory, and (per Section 10) currently always fast and
often trivial (zero relationship observations to process on any real
scan today). This investigation's tentative recommendation is that Stage 2
does not need a new phase, on the grounds that OBS-002 observability
exists to give a technician visibility into operations with meaningful
duration or failure modes, and resolution currently has neither. But this
investigation did not evaluate what happens once a real provider makes
`Project.observations` large (hundreds of relationship observations across
many devices) — at that scale, "always fast" may no longer hold, and the
absence of any observability into a resolution pass that suddenly takes
noticeable time would be a real gap, not a hypothetical one. This
investigation declines to resolve the question because it cannot be
answered against Stage 2's own scope (no provider exists to generate that
scale, Section 9) — it should be revisited when Stage 3 (a real provider)
is scoped, not decided speculatively here. This is now the only
unresolved ambiguity this investigation records — Section 10's follow-up
review settled resolver failure semantics (propagate uncaught, matching
classification), so it no longer appears here.

---

## 12. Suggested Implementation Roadmap

Mirroring ARCH-018 Section 15's own staging convention.

**Stage 2 (this investigation's subject; not authorized here) — Runtime
wiring.** `Project` gains `canonical_identities` and
`canonical_relationships` fields (Section 5); `Application.run()` calls
`IdentityResolver().resolve()` then `RelationshipResolver().resolve()`
between `DiscoveryEngine.discover()` returning and `Project(...)`
construction (Section 6); the permanent integration test is extended to
exercise this path through `Application.run()` itself, not only through
direct resolver calls (Section 8). No `RuntimePhase` addition, no exporter
change, no serializer change (Sections 4, 7, 11).

**Stage 3 (separate future sprint, not authorized here, unchanged from
ARCH-018 Section 15) — first relationship-evidence provider.**
ARP-corroborated-gateway remains the cleanest near-term candidate per
ARCH-018 Section 5; this is the point at which `canonical_relationships`
becomes observably non-empty on a real scan, and the point at which
Section 11's OBS-002-phase-parity question should be revisited against
real evidence volume rather than speculatively.

**Stage 4 and beyond** — unchanged from ARCH-018 Section 15/16: an
`Interface`/port model, MAC-to-identity resolution, non-`Device` endpoints,
topology rendering, and any consumption of `canonical_relationships` by a
report or CLI diagnostic. None designed or authorized here.

---

## 13. Future Work

Explicitly deferred, and not authorized by this investigation:

- The Stage 2 implementation sprint itself (Section 12) — the two-file
  change and test extension this document specifies but does not write.
- Resolving whether resolution needs its own `RuntimePhase` (Section 11),
  deferred to Stage 3 when real evidence volume exists to evaluate it
  against — the sole remaining unresolved ambiguity this investigation
  records.
- Any relationship-evidence provider (Stage 3, ARCH-018 Section 15,
  unchanged).
- Any exporter or report consuming `canonical_identities`/
  `canonical_relationships` — explicitly excluded from this sprint's
  charter (Section 9) and not designed here.
- Persisting `canonical_identities`/`canonical_relationships` — Section 7
  finds this inconsistent with the current, unpersisted state of
  `Project.observations` and does not propose revisiting either without
  first revisiting ADR-011's own deferred persistence question.
- Whether Stage 2 wiring should be deferred until Stage 3 (Section 10) —
  surfaced as a legitimate option, not decided.
- Everything ARCH-018 Section 16 already deferred and this investigation
  finds no new reason to revisit: `Interface`/port model,
  MAC-to-canonical-identity resolution, non-`Device` endpoints,
  cross-run/cross-subject identity correlation, topology rendering.
