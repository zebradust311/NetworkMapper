# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: Possibly — Section 8 (Architectural Assessment) finds a
generalized observation model justified, but only for a bounded scope
(identity and relationship resolution), not as a universal replacement
for how `Device` or classification currently work. Whether that bounded
scope is formalized as an ADR is an engineering-review decision; per
this sprint's explicit scope ("Do not create ADRs. Wait for engineering
review."), none is recorded here.

Recommended Next Sprint:
Not pre-selected, per this investigation's own scope constraint. The
natural next step, if engineering review agrees with Section 8's bounded
finding, is design of the single shared retained-observation/provenance
mechanism ARCH-014 (Section 8, item 3) and ARCH-015 (Section 8, item 3)
both already called for independently — this investigation adds the
finding that its scope should be bounded and its relationship to the
existing `networkmapper.knowledge.models.Observation` class (Section 2,
Section 7) resolved explicitly rather than left to collide silently.
That sequencing and scope decision belongs to engineering review, not
this investigation.

---

## 1. Executive Summary

ARCH-014 and ARCH-015 each independently reached the same structural
conclusion from different starting points — relationships and device
identity, respectively — without being asked to reconcile them: both
require retaining individually-attributed evidence rather than
collapsing it into one merged value, both need that evidence's
provenance to judge independence for corroboration, and both explicitly
recommended, in their own Section 8, that a shared provenance mechanism
be designed once rather than twice. This investigation was chartered to
answer the question both left implicit: **what is an observation**, and
is it one coherent architectural concept or two similar-looking ones
wearing the same name.

The central finding is that NetworkMapper already has a class literally
named `Observation`
(`networkmapper/knowledge/models.py:120-138`), and it is **not** the
concept ARCH-014 and ARCH-015 need, despite the name. The existing
`Observation` is episodic (captured once, only for a device
classification could not resolve — `should_capture()`,
`networkmapper/knowledge/capture.py:24-32`, returns `True` only for
`DeviceType.UNKNOWN`), whole-device in granularity (one record bundles
an entire device's evidence and classification outcome), and built
*from* already-collapsed `Device` state after the fact
(`build_observation()` reads a `Device`, not a raw provider response).
What ARCH-014 and ARCH-015 need is continuous (produced by every
provider read, regardless of classification outcome), per-claim in
granularity (one observation per field or per relationship assertion,
so independence and corroboration can be evaluated), and prior to
`Device` in the data flow, not derived from it. These are genuinely
different things that happen to share a name — a finding this
investigation treats as a real risk for whoever designs the eventual
mechanism, not a pedantic naming complaint.

The second finding is that the stated Observation Philosophy principles
(Section 2) are **internally consistent as a target architecture but not
uniformly true of NetworkMapper today** — several are correctly
identified by ARCH-014/ARCH-015 as recommendations, not descriptions,
and one ("Classification consumes interpreted knowledge rather than raw
observations") is not accurate even as a description of the intended
runtime path: `DeviceClassifier` reads raw `Device` fields directly at
evaluation time (`docs/architecture/classification.md`); Knowledge
influences classification only indirectly, by informing which rules a
human later writes (`KNOWLEDGE-LIFECYCLE.md`). This is not a defect in
either subsystem — it is a distinction the stated principle collapses
that this investigation finds needs to stay separate.

The third finding, and this investigation's answer to its own
"architectural necessity" question: a generalized observation model is
**justified, but only for a bounded scope.** Identity resolution and
relationship resolution both already, independently, hit a wall without
it. Classification and reporting have not, and Section 6 (Observation
Consumers) finds no evidence either should be re-plumbed to consume raw
observations instead of canonical `Device`/`Project` state — doing so
would trade a proven, validated, deterministic subsystem for a
heavier one without a demonstrated need. The recommendation this
investigation supports is narrower than "NetworkMapper needs an
observation layer": it is "identity and relationship resolution need a
shared observation layer; nothing else currently does."

No production code, data model, serialization, or persistence is
proposed for change by this report.

---

## 2. Observation Philosophy

Each stated principle is evaluated on its own, against current code
where current code exists, and against ARCH-014/ARCH-015's own findings
where the principle concerns work those investigations already scoped.

**"An observation represents something directly observed by a
provider."** Consistent with ADR-008's own definition of discovery
("hostnames, vendors, open ports... obtained from a `DiscoveryProvider`").
No inconsistency found.

**"An observation is immutable after collection."** Consistent with
ADR-008 in principle, and with the existing `Observation` class's stated
intent (`ObservationRepository`'s docstring: "Recording an observation...
never affects runtime classification"). But this investigation finds the
principle is **not structurally enforced** by the existing
implementation: `Observation`
(`networkmapper/knowledge/models.py:119-138`) is a plain `@dataclass`,
not `frozen=True`, and `ObservationRepository.save()`
(`networkmapper/knowledge/repository.py:54-62`) explicitly documents
that it "Overwrites any existing file for the same ID." Nothing in
current code exercises that overwrite path today, but the capability
exists by convention only, relying entirely on caller discipline rather
than the type system. `networkmapper.reporting.report_run.ReportRunPaths`
(`@dataclass(frozen=True)`) already demonstrates a proven, low-cost
pattern elsewhere in this same codebase for enforcing exactly this kind
of invariant structurally rather than by convention — worth naming as a
concrete, precedented option for any future observation type (Section
9).

**"Interpretations may evolve. Observations do not."** Consistent with
ADR-008 and with ARCH-014 Section 5's "corroborate rather than override"
principle. This investigation finds it is also the standard the existing
`Observation`'s overwrite-by-ID capability (previous paragraph) is in
tension with: if a future review tool ever used `ObservationRepository.save()`
to alter an observation's `device`/`evidence`/`classification` fields in
place — which nothing prevents today — it would violate this exact
principle. Currently, only `status` and `review_history` are intended to
change post-capture, and those are interpretation-shaped fields riding
on the same record, not the observed facts themselves; the model does
not yet structurally separate the two the way this principle requires.

**"Canonical device state is an interpretation of accumulated
observations."** This is the principle ARCH-014 (Section 2) and ARCH-015
(Section 2) both already state as their recommended target architecture
— and both correctly frame it as a recommendation, not a description of
current code. This investigation confirms that framing was accurate:
today, `Device`'s evidence fields (`hostname`, `mac_address`,
`snmp_sys_descr`, and so on) are not derived from anything more
primitive — they *are* the primitive record, written directly in place
by `NmapProvider._build_device()`
(`networkmapper/discovery/nmap_provider.py:336-345`) and
`EnrichmentProvider.enrich()` implementations
(`networkmapper/discovery/snmp_provider.py:146-155`). `device_type` is
correctly modeled as an interpretation of `Device`'s evidence fields
(ADR-008, `RuleResult`); the evidence fields themselves are not
interpretations of anything — `Device` currently plays both roles at
once. Accurate as target architecture; not descriptive of current code.

**"Identity is an interpretation." / "Relationships are
interpretations."** Both are ARCH-015's and ARCH-014's own stated target
conclusions, respectively, restated here rather than newly asserted.
Neither is true of any shipped code today, because neither identity nor
relationship resolution exists anywhere in the codebase yet — both
remain accurate, unimplemented target statements.

**"Knowledge consumes observations."** True, but with a layering
subtlety this investigation finds worth making explicit: the
`Observation` that `capture_unresolved_device()`
(`networkmapper/knowledge/capture.py:97-120`) writes is built by
`build_observation()` reading an already-fully-formed `Device` — the
consumed input is a snapshot of canonical, already-collapsed state, not
a raw per-provider observation in the ARCH-014/ARCH-015 sense. "Knowledge
consumes observations" is true of the existing pipeline only if
"observations" is read as "device snapshots," which is a narrower,
different claim than the generalized per-provider-claim observation this
investigation was chartered to evaluate.

**"Classification consumes interpreted knowledge rather than raw
observations."** This is the one principle this investigation finds **not
accurate**, even as target architecture, without a caveat the stated
principle omits. `DeviceClassifier` evaluates rules directly against raw
`Device` fields at runtime (`docs/architecture/classification.md`,
"Rule Evaluation Lifecycle") — it does not read from, or depend on, any
Knowledge artifact (`docs/knowledge/`) at evaluation time. Knowledge
influences classification only through `KNOWLEDGE-LIFECYCLE.md`'s
offline path — Observation → Knowledge → Benchmark → **a human writes or
changes a rule** → Classification — a design-time influence on rule
*authorship*, not a runtime data dependency. Stating "classification
consumes interpreted knowledge" without distinguishing these two paths
risks a future reader assuming `DeviceClassifier` has, or should gain, a
runtime dependency on Knowledge artifacts, which would be a materially
different (and unreviewed) architecture change from what
`KNOWLEDGE-LIFECYCLE.md` actually describes.

**Overall consistency assessment:** the seven principles form a
coherent, internally consistent *target* architecture — nothing in them
contradicts another when read as a future direction. They are not
uniformly descriptive of NetworkMapper today, which is expected and
already correctly flagged by ARCH-014/ARCH-015 for the principles they
each already addressed. This investigation's contribution is narrowing
that same finding for the two principles ARCH-014/ARCH-015 did not
directly evaluate (Knowledge and Classification's consumption paths),
and finding the classification principle needs a caveat, not just a
"not yet built" label.

---

## 3. Observation Characteristics

Evaluated against what ARCH-014 (Section 6, Provenance Strategy) and
ARCH-015 (Section 7, Corroboration Strategy) already required, and
against what the existing `Observation`/`RunMetadata` shapes already
provide.

**Architectural necessities** — present in some form across ARCH-014,
ARCH-015, or both, and therefore not provider-specific:

- **Observed subject.** What the observation is about — a single
  device (identity evidence), or a pair of endpoints (relationship
  evidence, per ARCH-014 Section 4's finding that an endpoint may not
  yet resolve to a `Device` at all). Already present in narrower form as
  `ObservationDevice` (`networkmapper/knowledge/models.py:44-56`).
- **Observed property.** Which field or claim is being reported —
  necessary so a resolver can group observations about the *same* claim
  for corroboration (ARCH-015 Section 7) rather than comparing unrelated
  facts.
- **Observed value.** The claim itself.
- **Provider / source attribution.** Already ubiquitous in some form —
  `Device.discovery_sources` (a flat `list[str]`), `ObservationScan`'s
  `profile`/`networkmapper_version`. Both ARCH-014 and ARCH-015 found
  the existing flat-list form insufficient once more than one
  observation about the same subject needs to be distinguished
  individually (ARCH-014 Section 6; ARCH-015 Section 9, item 1).
- **Observation time.** Already present (`Observation.captured_at`,
  `RunMetadata.generated_at`).
- **Collection method.** Not currently modeled anywhere, in any form.
  This investigation finds it is a necessity, not an optional detail,
  specifically because of Section 5 (Observation Independence) below:
  without knowing *how* a value was obtained, a resolver cannot tell
  whether two observations are independent confirmations or two
  surfaces of the same underlying query. This is a genuine gap, not a
  restatement of an already-covered need.

**Provider-specific, not architectural necessities** — useful
supporting detail, but not required for identity, relationship, or
corroboration purposes as scoped by ARCH-014/ARCH-015: SNMP community
string or OID path, the specific WMI class/namespace queried, an NSE
script name, a vCenter MoRef's containing inventory path. A generalized
observation record that tried to pre-declare a named field for every
provider's supporting detail would repeat the growth pattern `Device`
already shows (thirteen optional fields today, one per evidence source)
at a second layer — Section 8 treats this as a real complexity cost
against unbounded generalization, not a reason to avoid the necessities
above.

---

## 4. Observation Lifecycle

**Creation.** By a provider, at the moment a value is obtained —
consistent with ADR-008's framing of discovery as "obtained from a
`DiscoveryProvider`," generalized to any future identity/relationship
source.

**Retention.** Indefinite once created, per ADR-008's immutability
requirement and the existing `ObservationRepository`'s own precedent:
`next_observation_id()`
(`networkmapper/knowledge/repository.py:43-52`) is explicit that IDs are
"never reused even after review changes an observation's status," and
`ARCHIVED` observations are "never deleted." This is a proven, working
precedent for the retention half of the lifecycle; Section 2 already
found the *enforcement* of non-mutation is weaker than the retention
policy around it.

**Supersession.** A later observation about the same subject/property
should **coexist** with, not overwrite, an earlier one — the same
question the charter poses directly ("should observations ever be
modified after collection... or should later observations instead
coexist with earlier ones"). This investigation finds coexistence is the
only answer consistent with Section 2's immutability principle and with
ARCH-014 Section 5's explicit prior conclusion ("collapsing away the
individual observations... would destroy the exact information
corroboration needs"). "Canonical value" is therefore a property of a
*resolver's interpretation* over the retained set at a point in time,
never a property mutated onto any single observation.

**Corroboration.** Multiple observations of the same subject/property
from independent sources increase confidence — Section 5 addresses how
independence itself should be judged.

**Invalidation.** This investigation finds observations should never be
invalidated *in place* — consistent with immutability. What can happen
is that a later, contradicting observation exists (a conflict, per
ARCH-014 Section 5 / ARCH-015 Section 7's shared "Conflicting" tier), or
that an observation simply stops being reconfirmed by recent runs
(staleness, below). Neither should delete or edit the original.

**Historical preservation.** Consistent with, and already proven by,
`ObservationRepository`'s non-deletion policy for `ARCHIVED` records —
this is a working precedent worth carrying forward rather than
reinventing.

**Staleness.** Neither `Device` nor the existing `Observation` has any
"last reconfirmed" or "still current" concept today — a gap ARCH-014
(Section 7) and ARCH-015 (Section 6) each already found independently,
for relationships and identity respectively, and this investigation
reconfirms it as a shared, still entirely unresolved gap rather than one
specific to either prior investigation's subject. This investigation's
own recommendation, consistent with the immutability principle: staleness
should be represented as a property of the *interpretation* built on top
of a set of observations (a corroborated relationship or identity whose
supporting observations haven't been refreshed recently is stale), not
as a mutation of the observation itself — an observation doesn't become
false with age; the conclusion resting on it becomes less current.

---

## 5. Observation Independence

The charter's own worked example — SNMP `sysName`, DNS, and WMI each
reporting a hostname — is this investigation's central test case for
Section 3's finding that **collection method is an architectural
necessity**, not optional metadata. Whether three same-valued
observations represent three independent confirmations or one claim
viewed three ways cannot be answered from the values alone; it depends
on what produced each one.

This investigation finds independence should be judged by tracing each
observation's collection method to its underlying *origin*, and finds
two concrete traps worth naming explicitly for whoever designs the
eventual resolver:

- **Same-source, multiple-surface double-counting.** A single WMI
  session might expose a hostname both as `Win32_ComputerSystem.Name`
  and, separately, through a different WMI class that happens to report
  the same underlying value. Two named fields, one underlying query —
  counting both as independent confirmations would overstate confidence
  without any new information having actually been gathered.
- **Genuinely independent origins can still look identical in shape.**
  SNMP `sysName` (the device's own protocol stack self-reporting its
  name), a WMI-reported computer name (a *different* protocol stack on
  the same device self-reporting), and a DNS PTR record (administrator-
  maintained infrastructure, entirely external to the device) are
  plausibly three independent sources despite superficially looking like
  "three fields called hostname" — two are the device describing itself
  through different channels, and one is a separate system's record
  about the device. Whether "two channels on the same device" should
  count as weaker corroboration than "the device plus an independent
  administrator record" is a real, unresolved design question this
  investigation surfaces rather than answers — but it can only be asked
  at all once collection-method provenance exists to distinguish the
  cases, which is the direct link back to Section 3's necessity finding.

This investigation does not resolve how many independence "tiers" should
exist or how they should be weighted — consistent with the charter's
instruction not to introduce numeric scores and not to propose
implementation — but finds that **without retained, per-observation
collection-method provenance, the independence question posed in the
charter's own example cannot be answered at all**, only guessed at. This
is the same conclusion ARCH-014 (Section 6) and ARCH-015 (Section 7)
each already reached independently; this investigation's contribution is
showing precisely why, with a concrete example of how naive
field-counting fails.

---

## 6. Observation Consumers

**Identity resolution** (ARCH-015) and **relationship resolution**
(ARCH-014) both require raw, retained observations directly — both
investigations already found their respective corroboration models
break down under a collapsed, single-value representation.

**Knowledge generation** (KNOW-003) currently consumes canonical
`Device` state, not raw observations — `build_observation()` reads an
already-fully-formed `Device`, per Section 2's finding. Whether this
should change — shifting Knowledge to consume raw per-provider
observations directly, which would let it capture evidence disagreement
even for devices that *do* classify successfully, not only `UNKNOWN`
ones — is a real question this investigation surfaces but does not
resolve (Section 10).

**Rule evaluation / Classification** should, this investigation finds,
**continue consuming canonical `Device` state, not raw observations
directly.** No finding in this investigation, ARCH-014, or ARCH-015
identifies a need classification currently has that raw observations
would satisfy and canonical state does not. `DeviceClassifier`'s
determinism, explainability, and validated stability (ARCH-013 Section
3's entire "Validated Decisions" section) all rest on evaluating a
single, stable `Device` snapshot per classification pass — re-plumbing
it to reason over a variable-sized set of raw observations per field
would be a substantial complexity increase with no identified benefit,
directly relevant to Section 8's "does the additional abstraction reduce
or increase complexity" question.

**Reporting** (Markdown/CSV exporters) should likewise continue
consuming canonical `Project`/`Device` state, per ADR-005's existing
presentation-never-mutates boundary — for the same reason: no finding
here identifies a reporting need raw observations would meet that
canonical state does not, and a report surfacing every raw contributing
observation for every field would work against, not for, the report's
existing role as a readable, evidence-summarized document rather than a
provenance dump.

**Future lifecycle/change-detection analysis** is the one consumer
category this investigation finds genuinely *cannot* be built on
canonical state alone: detecting "this field changed between run N and
run N+1" requires access to the prior value, which collapsed canonical
state — by construction — no longer has once a newer value has
overwritten it (`EnrichmentProvider`'s fallback-only merge, ADR-010,
only fills empty fields; nothing preserves what a field held before a
same-run overwrite either, though ADR-010's own fallback-only rule means
this rarely occurs within one run). This is the clearest concrete future
capability this investigation finds is foreclosed without retained
observations, independent of identity or relationships.

**Summary answer to the charter's own question** ("should some
components consume canonical state instead of observations"): yes —
classification and reporting should, and already do, by design; identity
resolution, relationship resolution, and future lifecycle analysis
should not, because canonical state has already discarded the
information those three specifically need.

---

## 7. Canonical Device Relationship

**Should `Device` remain the primary canonical representation?** Yes —
nothing in this investigation, ARCH-014, or ARCH-015 argues for
replacing `Device` as the queryable "current believed state" entity that
classification, reporting, persistence, and every developer tool already
depend on. The finding here is narrower: `Device`'s *role* should
conceptually become the output of resolving observations (per Section
2's target-architecture principle), not that `Device` itself should be
restructured — consistent with the charter's explicit "do not redesign
Device" instruction.

**Should observations exist behind `Device`?** Yes, architecturally —
this generalizes, rather than newly proposes, the same conclusion
ARCH-014 (Section 8, item 3) and ARCH-015 (Section 8, item 3) already
reached independently for their respective subjects: both already
recommended a retained-observation layer beneath the canonical layer.
This investigation's contribution is stating that conclusion once, at
the layer both were actually describing, rather than leaving it as two
parallel, subject-specific recommendations.

**Should observations remain accessible after canonical values are
produced?** Yes — required by Section 4's immutability/retention
findings, and required for Section 6's future lifecycle-analysis
consumer case to be possible at all. An observation that becomes
unreachable once `Device` reflects its value would foreclose exactly the
capability Section 6 identifies as uniquely dependent on retained
observations.

This investigation does not propose how `Device` and an observation
layer would be wired together, persisted, or serialized — per the
charter, that is implementation and persistence/serialization design,
explicitly out of scope here.

---

## 8. Architectural Assessment

Answering the charter's five questions directly.

**Is a generalized observation model justified?** Yes, but **bounded**,
not universal. Justified for identity resolution (ARCH-015) and
relationship resolution (ARCH-014), both of which already, independently,
found they cannot function without one. Not currently justified for
classification or reporting (Section 6) — neither has an identified,
demonstrated need for it. The recommendation this investigation supports
is scoped: an observation layer serving identity and relationship
resolution specifically, not a wholesale replacement for how `Device` is
populated or consumed everywhere.

**Does the additional abstraction reduce or increase architectural
complexity?** Both, depending on scope. Bounded to identity/relationship
resolution, it is likely net-neutral-to-positive: it replaces what would
otherwise become two independent, ad hoc provenance schemes (one built
for ARCH-014's relationship work, one for ARCH-015's identity work) with
one shared foundation — genuinely less total complexity than building
both separately, which is the situation NetworkMapper is in *today*,
with two investigations each independently recommending the same
mechanism. Applied universally — to every `Device` field, regardless of
whether anything consumes its provenance — it would be a net complexity
increase with no identified consumer to justify it (Section 6), echoing
the same "collected but unconsumed" pattern ARCH-013 (Section 5) already
named as a deliberate, acceptable Phase 2 outcome only when a specific
future consumer is anticipated, not as a default posture for every
field.

**Can the architecture remain deterministic?** Yes. Nothing evaluated
here requires non-determinism: corroboration tiers (ARCH-014 Section 5,
ARCH-015 Section 7) are ordered, rule-like, evidence-hierarchy checks —
the same family as `first_matching_identifier`
(`networkmapper/classification/evidence_helpers.py:67-104`) and
`RuleResult`'s first-match-wins evaluation (ADR-002/ADR-003), not a
departure from either.

**Does the observation model preserve explainability?** Yes, and this
investigation finds it likely *improves* explainability where it
applies: an observation layer with named collection-method provenance
(Section 3) is a strict improvement over `EnrichmentProvider`'s current
behavior, where a provider's raw response is read and immediately
discarded the moment it is merged into `Device`
(`networkmapper/discovery/snmp_provider.py:146-155`), leaving only a
flat `discovery_sources` list — sufficient to say *that* SNMP
contributed something, not *which* field, *when*, or via *what specific
query*.

**Which future capabilities would depend on observations?** Directly:
identity resolution (ARCH-015) and relationship resolution (ARCH-014).
Newly identified by this investigation: lifecycle/change-detection
analysis (Section 6) and, as an open rather than resolved question,
possibly Knowledge generation gaining the ability to capture evidence
disagreement for devices beyond the currently `UNKNOWN`-only scope
(Section 6).

---

## 9. Technical Debt

Confirmed against current repository state; not created by this
investigation.

**1. `EnrichmentProvider.enrich()` already performs an un-reified
observation-to-interpretation collapse in a single step, with no
retained provenance beyond a flat provider-name list.** Confirmed
directly at `networkmapper/discovery/snmp_provider.py:146-155`
(`_merge()`): a provider's raw response is read and written directly
into `Device` in the same method, with only `"snmp"` appended to
`discovery_sources` surviving afterward — no per-field attribution, no
timestamp, no collection-method detail. Every capability Section 6 and
Section 8 identify as depending on retained observations (identity,
relationships, lifecycle analysis) is blocked by this today.

**2. `networkmapper.knowledge.models.Observation` shares a name, but not
a shape, trigger condition, or data-flow direction, with the generalized
observation concept ARCH-014 and ARCH-015 need.** Section 1 and Section
2 detail the mismatch (episodic/`UNKNOWN`-only/whole-device/
derived-from-`Device` versus continuous/per-claim/prior-to-`Device`).
This is not a defect in KNOW-003's own, deliberately narrower scope —
it is a real risk that a future implementer, finding a class already
named `Observation`, extends or reuses it without recognizing the
mismatch, rather than designing the distinct concept this investigation
and its two predecessors actually require.

**3. `Observation`'s immutability is a stated convention, not a
structural guarantee.** Confirmed directly: the dataclass is not
`frozen=True`, and `ObservationRepository.save()`
(`networkmapper/knowledge/repository.py:54-62`) explicitly permits
overwriting an existing ID's file. No current code path exploits this,
but nothing prevents a future one from doing so, in direct tension with
the immutability principle Section 2 otherwise finds this class
correctly upholds by convention. `ReportRunPaths`
(`networkmapper/reporting/report_run.py`, `@dataclass(frozen=True)`)
already demonstrates a proven, low-cost, precedented fix pattern
elsewhere in this same codebase.

**4. No staleness/"last reconfirmed" concept exists anywhere in `Device`
or `Observation`.** Independently found by ARCH-014 (Section 7) and
ARCH-015 (Section 6) for their respective subjects; this investigation
reconfirms it as a single shared gap affecting any future observation
model generally, not two separate gaps.

---

## 10. Future Work

Explicitly deferred, and not authorized by this investigation:

- The ADR formalizing a *bounded* (identity- and relationship-scoped,
  not universal) generalized observation model, per Section 8's
  finding — an engineering-review decision on whether and how to
  proceed, not made here.
- Design of the shared retained-observation/provenance mechanism
  ARCH-014 and ARCH-015 both already called for, now informed by this
  investigation's scope-boundedness finding (Section 8) and its explicit
  requirement to resolve its relationship to
  `networkmapper.knowledge.models.Observation` (Section 9, item 2)
  rather than silently colliding with or duplicating it.
- Whether Knowledge generation (KNOW-003) should shift from consuming
  canonical `Device` snapshots to consuming raw per-provider
  observations directly (Section 6) — named as an open question, not
  decided here.
- Structural immutability enforcement (e.g., `frozen=True`) for any
  future observation type, following the `ReportRunPaths` precedent
  (Section 9, item 3) — a specific, low-cost recommendation for that
  future design, not implemented now.
- A staleness/"last reconfirmed" model, shared across identity,
  relationship, and any other future observation-consuming subsystem
  (Section 9, item 4) — a gap all three investigations in this series
  have now independently found and none has resolved.
- Any concrete collection-method/independence taxonomy for corroboration
  (Section 5) — this investigation names why it is needed and the traps
  a naive design would fall into, but does not define one.
