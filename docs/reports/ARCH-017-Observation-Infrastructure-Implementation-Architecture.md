# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — this investigation determines how ADR-011, ADR-012,
and ADR-013 should be introduced into the existing codebase; it does not
reconsider or extend any of their decisions. Per this sprint's explicit
scope, no new ADR is created here.

Recommended Next Sprint:
Stage 1 as defined in the Migration Plan below — introducing the
observation model with zero behavior change, and, as part of that same
stage, explicitly resolving the naming collision with
`networkmapper.knowledge.models.Observation` that ADR-011 already
required be resolved before concrete types are introduced. This is
offered as this investigation's recommendation, not a decision — per
scope, engineering review selects the next sprint.

---

## 1. Executive Summary

ADR-011, ADR-012, and ADR-013 established what canonical observations,
identity, and relationships are and how they relate to one another. None
of them specified how to introduce that architecture into a codebase
that already has a mature, tested, three-phase discovery pipeline
(`DiscoveryProvider` → `EnrichmentProvider` → classification, ADR-001/
ADR-010) writing directly into `Device`. This investigation finds that
pipeline can absorb the new architecture with a small, well-isolated
blast radius — but only if the charter's own illustrative pipeline
ordering is corrected in one specific respect.

The charter's proposed pipeline — Discovery → Observation Collection →
Observation Retention → Identity Resolution → Relationship Resolution →
Canonical Device Interpretation → Classification → Reporting — is
directionally consistent with ADR-011/012/013's dependency structure
(identity depends on observations; relationships depend on identity),
but read as a literal, single-run temporal sequence it would require
`Device` construction to wait on identity and relationship resolution
completing. This investigation finds that would violate ADR-001 (host
discovery establishes the authoritative device list immediately),
ADR-010 (`EnrichmentProvider` already operates on already-discovered
devices, before any identity concept exists), and ARCH-016's own finding
that classification and reporting have no demonstrated need to consume
anything but canonical `Device`/`Project` state. The corrected
architecture (Section 4) keeps today's discovery → enrichment →
classification → reporting path intact and unblocked, and runs
observation retention, identity resolution, and relationship resolution
as a **decoupled, additive interpretation pass** over the same
underlying evidence — one that may lag behind a single run entirely,
since its core value (cross-run corroboration) requires evidence
accumulated across multiple runs, not just the one that just completed.

The second finding is that this decoupling makes the migration
genuinely low-risk in a way this investigation can demonstrate rather
than assert: `BenchmarkRunner.load_inventory()`
(`networkmapper/developer/benchmark_runner.py:47-83`) constructs `Device`
objects directly from curated JSON and never touches
`DiscoveryProvider`, `EnrichmentProvider`, or anything this migration
introduces — the benchmark suite ADR-006 protects is structurally
isolated from this work by construction, not merely by careful staging.

The third finding is a real, non-obvious sequencing tension the charter's
own illustrative stages do not surface: ADR-011 correctly defers
*designing* observation persistence, but this investigation finds that
deferral cannot extend indefinitely without undermining the entire
premise. Identity and relationship resolution's value is cross-run
corroboration; if observations are never persisted beyond one run's
in-memory lifetime, every later stage only ever sees one run's evidence,
and corroboration never has more than one data point to work with. This
investigation recommends persistence be sequenced as an early, not late,
concern — while still not designing it here.

No production code is proposed for change by this report.

---

## 2. Current Architecture Assessment

**Provider boundaries.** `DiscoveryProvider.discover(self) -> list[Device]`
(`networkmapper/discovery/provider.py`) takes no input and returns
finished `Device` objects; `NmapProvider` is the only implementation.
`EnrichmentProvider.enrich(self, devices: Sequence[Device]) -> None`
(`networkmapper/discovery/enrichment_provider.py`) mutates an
already-assembled device set in place, fallback-only, never introducing
or removing a device (ADR-010). Both contracts are narrow, single-method
interfaces with no observation concept anywhere in their signatures
today.

**Enrichment boundaries.** `DiscoveryEngine.discover()`
(`networkmapper/discovery/discovery_engine.py:49-85`) is the single
orchestration point: it runs every `DiscoveryProvider`, deduplicates by
IP into `devices_by_ip`, runs every `EnrichmentProvider` against that set
inside a bare `try/except Exception: pass` (a provider defect degrades to
"contributed nothing," per ADR-010), then classifies. This is the one
place in the codebase that already knows about the full discovered
device set at once — the natural seam for anything that needs to observe
"every device this run produced," including a future observation
pipeline.

**Canonical Device construction.** `Device` is written at three points,
all before classification: `NmapProvider._build_device()`
(`networkmapper/discovery/nmap_provider.py:336-345`, initial IP/hostname/
MAC/vendor), `NmapProvider._discover_with_enrichment()`
(`networkmapper/discovery/nmap_provider.py:262-295`, services and SMB/RDP
identity fields, already itself a private fallback-merge), and
`EnrichmentProvider.enrich()` implementations
(e.g. `SnmpEnrichmentProvider._merge()`,
`networkmapper/discovery/snmp_provider.py:146-155`, also fallback-only).
None of these three write points retains anything beyond the final
merged value — confirmed directly, per ARCH-016's own finding, that
`_merge()` discards the raw response the moment it is written.

**Serialization boundaries.** `ProjectSerializer`
(`networkmapper/project/serializer.py`) reads and writes `Device` fields
1:1 with no observation concept. `Application.run()`
(`networkmapper/application.py:186-205`) confirms directly that
`ProjectSerializer.load()` is called exactly once, solely to verify a
just-saved project round-trips for a console message — never to merge a
new scan against a prior project. There is no rescan-reconciliation code
path today, reconfirming ARCH-015 Section 9's finding directly against
this session's re-read of `application.py`.

**Reporting boundaries.** `CsvExporter`/`MarkdownExporter`
(`networkmapper/exporters/`) consume `Project`/`Device` state only,
per ADR-005's presentation-never-mutates boundary. Neither reads
`discovery_sources` beyond display, and neither has any observation
concept to consume even if one existed today.

**Where retained observations naturally integrate:** at
`DiscoveryEngine.discover()`, alongside — not inside — the existing
provider/enrichment/classification sequence. This is the one point that
already sees the complete device set before classification, has an
existing `RuntimeEventBus` publish/subscribe mechanism proven safe to
extend without behavior change (OBS-002), and does not require touching
`NmapProvider`, `SnmpEnrichmentProvider`, `DeviceClassifier`, or any
exporter to add a new, optional, subscriber-driven side channel.

---

## 3. Integration Strategy

The governing constraint, drawn directly from ADR-011's Canonical Device
Boundary and ADR-012/ADR-013's identical "supports, does not replace"
framing: this investigation treats observation retention, identity
resolution, and relationship resolution as an **additive interpretation
layer** that reads the same evidence the existing pipeline already
produces, rather than a replacement stage the existing pipeline must be
routed through. Concretely, this means:

- `Device` continues to be constructed exactly as it is today, by the
  same three write points (Section 2), on the same timeline, with the
  same immediate availability to classification and reporting.
- Observation retention is a **parallel consumer** of the same evidence
  those three write points already produce or receive — not a
  replacement for how they write into `Device`.
- Identity resolution and relationship resolution run against the
  retained observation set independently of any single run's
  classification/reporting timeline, since their value depends on
  evidence accumulated across multiple runs (Section 1; expanded in
  Section 5, Observation Lifetime).

This directly answers the charter's "should transitional
implementations support both" question for providers: yes, but not as a
permanent, parallel-forever duplication — Section 6 (Migration Plan)
proposes a specific, bounded point at which the dual-write collapses
back into one path.

---

## 4. Pipeline Architecture

The charter's proposed pipeline —

```
Discovery Provider
    ↓
Observation Collection
    ↓
Observation Retention
    ↓
Identity Resolution
    ↓
Relationship Resolution
    ↓
Canonical Device Interpretation
    ↓
Classification
    ↓
Reporting
```

— is **consistent with ADR-011/012/013 as a dependency graph** (an
identity interpretation cannot be computed before observations exist to
support it; a relationship interpretation cannot be computed before its
endpoints' identities are resolved, per ADR-013's own Relationship
Endpoints section). It is **not consistent with ADR-001, ADR-010, or
ARCH-016's own findings if read as a literal, single-run temporal
sequence** that gates `Device` construction and classification behind
identity and relationship resolution:

- **ADR-001** requires host discovery to establish the authoritative
  device list before enrichment even runs — the device list's existence
  cannot wait on any later interpretation stage.
- **ADR-010** already defines `EnrichmentProvider` as operating on
  "already-discovered devices" — `Device` unambiguously exists, and is
  enrichable, before any identity concept is introduced by this
  investigation's predecessors.
- **ARCH-016 Section 6/8** found no demonstrated need for classification
  or reporting to consume anything but canonical `Device`/`Project`
  state, and explicitly recommended they continue doing so. Placing
  "Canonical Device Interpretation" between relationship resolution and
  classification, read literally, would make classification's ordinary
  operation depend on relationship resolution having already run — a
  new, unjustified dependency ARCH-016 already found no basis for.

This investigation's corrected architecture keeps the existing pipeline
and the new interpretation layer as two related but independently-paced
paths sharing a common evidence source:

```
Discovery Provider ──► Enrichment Provider ──► Device (unchanged) ──► Classification ──► Reporting
        │                       │
        └────────────┬──────────┘
                      ▼
          Observation Emission (additive)
                      ▼
           Observation Retention (Project-wide, Section 5)
                      ▼
              Identity Resolution
                      ▼
            Relationship Resolution
                      ▼
   (optional, additive) Device/Project annotation — e.g. a
   resolved-identity reference — never a rewrite of Device's
   existing discovery fields or their provenance.
```

`Device`'s existing fields and their provenance are never rewritten by
the lower path — consistent with ADR-012's "Device does not become the
identity engine" and ADR-013's identical framing for relationships. The
lower path may run once per scan, on a schedule, or on demand; nothing
about the existing pipeline's timing constrains it, and nothing about
the lower path's timing constrains the existing pipeline.

**Where does "Canonical Device Interpretation" fit, then?** This
investigation finds the charter's own Stage 3 language ("Device
populated from identity interpretation," Migration Strategy section)
needs the same correction applied to it directly (see Migration Plan,
Stage 3) — identity resolution should *annotate* `Device` additively,
never become the mechanism by which `Device`'s existing fields are
populated.

---

## 5. Provider Responsibilities

**Should providers emit observations?** Yes, additively — a provider
that already produces evidence for `Device` is the natural, and only
correct, origin point for the corresponding retained observation, since
it alone knows the collection method and timing (ADR-011's Provenance
requirement).

**Should providers continue populating `Device`?** Yes, unchanged, for
as long as classification and reporting remain canonical-state consumers
(ARCH-016) — which this investigation does not find any reason to
revisit.

**Should transitional implementations support both?** Yes, but the
mechanism does not need to duplicate a provider's write logic. This
investigation finds a directly reusable precedent already in the
codebase: `RuntimeEventBus` (OBS-002) already lets `NmapProvider` and
`SnmpEnrichmentProvider` publish structured events to zero or more
subscribers as a side effect of their existing work, with a proven,
already-exercised "safe no-op when nothing is subscribed" property —
exactly the Stage 1 requirement ("no existing behavior changes"). This
investigation recommends a future implementation evaluate emitting
observations the same optional, side-channel way, rather than changing
`EnrichmentProvider.enrich()`'s signature or `DiscoveryProvider.discover()`'s
return type. This is offered as a directly-precedented option, not a
locked-in design — concrete API design is explicitly out of this
investigation's scope.

**How are ADR-010's provider boundaries preserved?** By construction, if
the option above is adopted: `EnrichmentProvider`'s abstract contract,
its fallback-only merge requirement, and its "never raise for an
expected per-device failure" requirement are all untouched — observation
emission is a new, optional side effect a concrete implementation adds
to its existing `enrich()` body, not a change to the contract every
implementation must satisfy differently.

**The dual-write risk, and how this investigation recommends resolving
it.** Once both `Device`-population and observation-emission exist side
by side, they are two independent code paths that could, in principle,
diverge (a bug fixed in one merge path but not the other). This
investigation recommends the eventual target — not required in the
first stage — be a refactor where `Device`-population becomes a
fallback-only *projection over retained observations*, rather than a
second independent write over the provider's raw response. This is a
strict generalization of ADR-010's existing fallback-only rule (a
fallback-only reducer over retained observations, instead of over raw
provider dicts), not a new merge policy, and it eliminates the
divergence risk structurally rather than by ongoing discipline. Section
6 (Migration Plan) places this refactor at a specific, later stage
rather than requiring it immediately.

---

## 6. Migration Plan

**Stage 1 — Introduce the observation model. No existing behavior
changes.** Define the observation concept ADR-011 described
conceptually (subject, property, value, provider, collection method,
timestamp, source/run identity) as an actual type, with no production
code path yet constructing or consuming one. This investigation adds one
concrete requirement to this stage beyond the charter's own framing:
**the naming collision with `networkmapper.knowledge.models.Observation`
must be resolved as part of this same stage, not deferred** — ADR-011
already required this be addressed before concrete types are introduced,
and Stage 1 is precisely the moment a concrete type is first introduced.
Deferring it risks the new type inheriting the same name by accident,
the exact risk ADR-011/ARCH-016 flagged.

**Stage 2 — Providers emit observations additively. `Device` remains
authoritative and unchanged.** `NmapProvider` and
`SnmpEnrichmentProvider` (and any future `EnrichmentProvider`) begin
emitting observations for the fields identity/relationship resolution
will eventually need, via the additive side-channel option in Section 5
or an equivalent mechanism, while continuing to write `Device` fields
exactly as today. Dual-write exists during this stage by design; Section
5 already names this as a bounded, not permanent, condition.

**Stage 3 — Identity resolver introduced.** Consumes retained
observations and produces identity interpretations, per ADR-012. This
investigation corrects the charter's own illustrative framing here:
identity interpretation should **annotate** `Device` additively (e.g., a
reference to a resolved identity and its corroboration state), not
become the mechanism that populates `Device`'s existing discovery
fields. `Device`'s existing fields continue to come from Stage 2's
(unchanged) provider writes. This is also the natural point to consider
the Section 5 dual-write-elimination refactor, once an identity
resolver's real requirements are known concretely enough to design a
projection over observations rather than deferring that refactor
indefinitely.

**Stage 4 — Relationship resolver introduced.** Consumes canonical
identities (Stage 3's output) and retained relationship observations, per
ADR-013. Depends structurally on Stage 3 being in place first, per
ADR-013's own "Relationship with Future ADRs" section naming ADR-012 a
prerequisite.

**Stage 5 — Topology becomes the first consumer.** Per ADR-013's
"Relationship with Future Topology," topology renders canonical
relationships; it does not participate in producing them. This stage is
explicitly out of this investigation's scope to design (per the ARCH-014
charter's original exclusion of topology rendering, still in force).

**A sequencing addition this investigation makes to the charter's own
list:** persistence for retained observations should be evaluated no
later than the Stage 2 → Stage 3 transition, not treated as an
open-ended "later" concern. Section 1 already found identity/relationship
resolution's value depends on cross-run evidence; if Stage 3 is reached
with observations still only ever retained in-memory for the duration of
one run, Stage 3's resolver would have no more evidence than the current
run alone provides, and corroboration across scans — the motivating case
for this entire investigation lineage — would not yet be possible in
practice. This investigation does not design that persistence (ADR-011
already deferred it, correctly, as a design question) — it finds the
*sequencing* question needs to be decided earlier than "later," and
names it explicitly rather than let it default to last by omission.

**Implementation principles applying across every stage**, per the
charter and this investigation's own findings: small, single-responsibility
commits; every intermediate commit compiles, passes the existing test
suite, and preserves existing benchmark results unmodified (achievable
directly, per Section 7's benchmark-isolation finding); no partially
interpreted identity or relationship is ever exposed to a consumer — an
interpretation is either complete (including its corroboration state,
even if that state is Weak or Conflicting per ADR-012/013) or not yet
produced, never a half-evaluated intermediate value.

---

## 7. Compatibility Analysis

**ADR-008.** Fully compatible, unmodified — this migration is a direct
continuation of ADR-008's evidence/interpretation split, not a departure
from it (ADR-011/012/013's own Rationale sections already establish
this; this investigation introduces no new tension).

**ADR-010.** Fully compatible if provider observation-emission is
additive (Section 5) — `EnrichmentProvider`'s contract, fallback-only
merge rule, and failure-isolation requirement all remain unmodified
through every stage in Section 6.

**RULE-004.** Unaffected. `first_matching_identifier`
(`networkmapper/classification/evidence_helpers.py:67-104`) reads
`Device` fields directly, including SNMP-derived ones; nothing about
observation retention changes what classification reads, consistent with
ARCH-016's finding that classification remains a canonical-state
consumer. Zero changes required at any stage in Section 6.

**Knowledge subsystem (KNOW-003).** Structurally unaffected — 
`capture_unresolved_device()`/`ObservationRepository` continue exactly
as today. The one required interaction is the Stage 1 naming-collision
resolution (Section 6); beyond that, this migration makes no changes to
KNOW-003's own architecture, consistent with ADR-011's explicit
deferral of Knowledge integration changes.

**Benchmark framework.** Structurally isolated by construction, not
merely by careful staging: `BenchmarkRunner.load_inventory()`
(`networkmapper/developer/benchmark_runner.py:47-83`) builds `Device`
objects directly from curated JSON and never invokes
`DiscoveryProvider`, `EnrichmentProvider`, or `DiscoveryEngine` at all.
No stage in Section 6 touches any code path `BenchmarkRunner` exercises,
so ADR-006's "benchmarking must never change production classification
behavior" boundary is not merely preserved by discipline — it cannot be
crossed by this work without a deliberate, separate change to
`BenchmarkRunner` itself.

**Serializer.** Unaffected through Stage 2 (no change to `Device`'s
persisted shape). Will require an explicit, separately-scoped extension
once observation persistence is designed (Section 6's sequencing
finding) — this investigation flags the need and its approximate
placement in the sequence without designing the extension itself, per
ADR-011's existing deferral of serialization changes.

**Exporters.** Unaffected through every stage in Section 6, consistent
with ARCH-016's finding that reporting should remain a canonical-state
consumer. Any future surfacing of identity/relationship information in a
report is new report content requiring its own future `REPORT-*` sprint,
not implied or required by this migration.

---

## 8. Risk Assessment

**Large refactors.** Mitigated by staging: Stage 1 and Stage 2 touch
only provider internals and a new, additive type, never the tested
external contracts of `DeviceClassifier`, exporters, `ProjectSerializer`,
or `BenchmarkRunner`. The one genuinely non-trivial refactor identified
(Section 5's dual-write elimination) is explicitly scoped to the Stage
2→3 transition, not required upfront.

**Provider coupling.** Mitigated — observation emission is per-provider
and additive, the same independence ADR-010 already established for
`Device` merging; no shared cross-provider observation-coordination
mechanism is introduced.

**Duplicate state.** The real risk of Stage 2's dual-write window
(Section 5) — mitigated by explicitly bounding that window to Stage
2→3, and by identifying the specific refactor (a fallback-only
projection over observations) that eliminates it structurally rather
than relying on ongoing discipline to keep two write paths in sync.

**Performance / memory growth.** Retaining individual observations
multiplies stored evidence volume relative to today's collapsed
`Device` fields — already flagged by ARCH-016 Section 8 as a real cost
of any unbounded application of this architecture. Mitigated the same
way ADR-011/013 already bound the model's scope: observation emission
should cover only fields identity/relationship resolution actually
consume, not every `Device` field unconditionally. Memory growth over a
project's lifetime is a real, unresolved concern once persistence exists
(Section 6); this investigation names it rather than resolves it.

**Serialization.** Risk is the sequencing tension identified in Section
6 — mitigated by explicitly surfacing it as an early-required design
question rather than allowing it to default to "last" by omission.

**Benchmark regressions.** Near-zero risk, and uniquely so among the
risks evaluated here: Section 7 shows `BenchmarkRunner` is structurally
isolated from every stage in Section 6 by construction, not merely by
careful sequencing.

**Migration complexity.** Reduced by keeping the existing pipeline and
the new interpretation layer decoupled (Section 4) rather than
threading the new layer through the existing one — the largest single
source of complexity this investigation identified (the dual-write
refactor) is isolated to one transition, not spread across every stage.

---

## 9. Recommended Implementation Order

Mapping Section 6's stages to the future feature areas this
investigation was asked to consider, in dependency order:

1. **Observation Infrastructure** (Stage 1-2) — the model, the naming
   collision resolved, and additive per-provider emission. Prerequisite
   for everything below.
2. **Identity Resolver** (Stage 3) — depends on (1) and, per Section 6's
   sequencing finding, on observation persistence existing by this point
   for cross-run corroboration to have real evidence to work with.
3. **Relationship Resolver** (Stage 4) — depends on (2), per ADR-013's
   own stated prerequisite.
4. **Topology Engine** (Stage 5) — depends on (3); explicitly out of
   this investigation's design scope, consistent with the original
   ARCH-014 charter's exclusion.
5. **Topology Reporting** — depends on (4); a future `REPORT-*` sprint,
   not implied by this migration.
6. **Runbook Generation** — depends on (5) and is the furthest out of
   any feature area considered here; this investigation finds no basis
   yet for reasoning about it further than noting the dependency.

This ordering is a direct consequence of ADR-012/ADR-013's own stated
prerequisites (identity before relationships, relationships before
topology) rather than a new sequencing judgment introduced by this
investigation.

---

## 10. Technical Debt

Confirmed against current repository state; not created by this
investigation.

**1. `NetworkGraph`'s IP-only device keying still has no
rescan-reconciliation path**, reconfirmed directly in this session
against `application.py:186-205` (ARCH-014/ARCH-015's original finding).
This investigation adds that it is now also a concrete implementation
blocker, not only a conceptual one: without it, "the same device across
runs" — required for cross-run identity corroboration (Section 6) — has
no mechanism to work from at all.

**2. `EnrichmentProvider._merge()` (e.g.
`networkmapper/discovery/snmp_provider.py:146-155`) is the concrete
Stage 2→3 refactor target** identified in Section 5 — named here as
debt-in-waiting rather than current debt, since it is correct and
sufficient for today's scope, but will need to change specifically at
the point Section 5/6 identify.

**3. The `networkmapper.knowledge.models.Observation` naming collision
(ADR-011, ARCH-016) remains unresolved as of this investigation**, and
this investigation elevates it from a documented risk to a required
Stage 1 deliverable (Section 6) rather than an open question that could
be addressed at any convenient point.

**4. No staleness/"last confirmed" concept exists anywhere**
(ARCH-014/015/016, reconfirmed). This investigation adds that it
partially blocks realizing Stage 3/4's full value — a corroborated
identity or relationship has no way to signal it needs
re-confirmation — without blocking the stages' basic implementation.

**5. Minor: two import paths resolve to the same `DeviceClassifier`
class.** `networkmapper/classification/classifier.py` re-exports
`networkmapper/classification/device_classifier.py`'s `DeviceClassifier`;
`discovery_engine.py` and `benchmark_runner.py` import from the former,
`capture.py` from the latter. Noticed incidentally while tracing the
pipeline for this investigation; low-impact, unrelated to the
observation migration, named for completeness in the same spirit as
prior sprints' small incidental findings (e.g. STAB-001's dead-code
note).

---

## 11. Future Work

Explicitly deferred, and not authorized by this investigation:

- The Stage 1 implementation sprint itself: the observation model's
  concrete type(s) and the naming-collision resolution (Section 6,
  Section 10 item 3).
- The additive provider-emission mechanism's concrete design (Section
  5) — an `RuntimeEventBus`-like option was named as a precedent, not
  adopted as a design.
- The Stage 2→3 dual-write-elimination refactor's concrete design
  (Section 5, Section 10 item 2).
- Observation persistence design — this investigation found it must be
  *sequenced* earlier than "last" (Section 6) without designing it,
  consistent with ADR-011's existing deferral of the design question
  itself.
- The identity resolver algorithm (ADR-012 Future Work) and relationship
  resolver algorithm (ADR-013 Future Work) — both remain undesigned,
  this investigation only sequences them.
- A staleness/"last confirmed" model (Section 10, item 4) — a gap now
  named by four consecutive investigations (ARCH-014/015/016/017)
  without being resolved by any of them.
- Topology engine, topology reporting, and runbook generation design —
  named in Section 9's dependency order only, not designed here.
- The minor `classifier.py`/`device_classifier.py` import-path cleanup
  (Section 10, item 5) — unrelated to this migration, worth a small,
  separately-scoped cleanup sprint at some point.
