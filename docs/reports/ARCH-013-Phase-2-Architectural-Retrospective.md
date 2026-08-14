# Status

Architecture Review Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — this is a retrospective evaluation of decisions
already recorded in `docs/ADR.md` (ADR-001 through ADR-010). It records
no new architectural decision of its own; where it identifies technical
debt or a Phase 3 readiness gap, it explicitly does not decide how or
whether to address either.

Recommended Next Sprint:
No single sprint is pre-selected. Section 6 (Technical Debt) and Section
8 (Phase 3 Readiness) each name candidates, but per this sprint's own
constraint ("without recommending that they be implemented"), none is
put forward as the next approved sprint. That selection is a Phase 3
planning decision, not this retrospective's to make.

Wait for engineering review before treating any finding here as
approved for implementation.

---

## 1. Executive Summary

Phase 2 took NetworkMapper from a working but evidence-poor discovery
tool to a system with a canonical, per-service evidence model (ADR-009),
a deterministic and explainable rule engine (ADR-002/003/004), a
structured knowledge repository (KNOW-003), runtime telemetry (OBS-002),
versioned Markdown/CSV reporting (REPORT-001/002/003), a
discovery/enrichment provider split proven against a second, structurally
different evidence source (ADR-010, SNMP), and — as of this session — a
first complete round-trip of that evidence lifecycle: SNMP evidence is
now collected (FEAT-005), selectively consumed by classification
(RULE-004), measured for real operational value (BENCH-003), and
surfaced in the reports a technician actually delivers (REPORT-003).

Thirty-eight test modules and 384 tests pass today (`python -m
unittest discover -s tests`, confirmed in this session), covering ten
accepted ADRs' worth of architecture. That is the headline number this
retrospective can point to as evidence Phase 2's architecture is not
just documented but exercised.

The single clearest finding, evidenced independently by three separate
investigations (ARCH-002A, FEAT-003E/ARCH-003, ARCH-012) rather than
asserted once: **NetworkMapper's canonical evidence model has no
representation for relationships between devices.** `NetworkGraph` is a
flat, IP-keyed `dict[str, Device]` (confirmed directly,
`networkmapper/core/network_graph.py:13`) with no `Interface` or `Link`
model, despite both being named as intended in `ENGINEERING.md`'s own
Core Principles ("Models contain data. Examples: Device, Interface,
Link, Network") since before Phase 2 began. Every investigation that has
approached topology/relationship evidence — SNMP `ifTable`, LLDP/CDP,
interface enumeration — has independently hit this same wall and
deferred, not because the evidence is unavailable, but because there is
nowhere in the canonical model for it to go. This is Section 6's leading
technical-debt item and Section 8's leading Phase 3 constraint.

The second clearest finding: Phase 2's recurring engineering discipline
— collect evidence before interpreting it, corroborate rather than
override, require observed evidence (not plausibility) before writing a
keyword — is not aspirational language in `ENGINEERING.md`. It is
directly, repeatedly demonstrated in shipped code and, in BENCH-003's
case, *measured* working as designed rather than merely claimed to.

---

## 2. Architectural Timeline

This is not a complete sprint log (see `git log` and `docs/reports/`
for that); it traces the decision lineage that produced Phase 2's
current architecture, grouped by the capability each chain built.

### 2.1 Foundation → Classification (pre-Phase-2 through CLASS-/EVID-/INTEL- series)

`Device`, `NetworkGraph`, `Project`, `DiscoveryProvider`/`DiscoveryEngine`,
and a first classifier existed before the sprint series this retrospective
covers in detail. `CLASS-001` through `CLASS-007` migrated classification
onto the `RuleResult` contract (ADR-002), preserving first-match-wins
behavior throughout the migration (ADR-003) rather than changing behavior
and structure at the same time. `EVID-001` added the read-only evidence
API (ADR-004). This sequence matters to the retrospective because it
establishes the pattern Phase 2 repeats constantly: **migrate structure
without changing behavior, then change behavior as a separate, later
step.**

### 2.2 The evidence-model chain: FEAT-003A → ADR-009 → FEAT-003C..I

This is Phase 2's longest, most-referenced decision lineage, and the one
every later evidence-collection sprint (including this session's SNMP
work) explicitly cites rather than re-derives:

- **FEAT-003A** (Discovery Capability Assessment) found Nmap's `-sV`
  product/version data was being parsed and discarded, and — separately
  — that `Device.operating_system` was fully wired end-to-end but had no
  producer and no consumer, calling it out explicitly as "a cautionary
  precedent for adding new evidence fields without a corresponding
  consumer."
- **FEAT-003B** found the structural blocker: `open_ports`/
  `detected_services` were independent, positionally-uncorrelated lists,
  incapable of representing "this product/version was observed on this
  specific port." This was recognized as a genuine, unanticipated
  architecture question and escalated rather than resolved inline — a
  direct, real instance of `docs/process/stop-conditions.md`'s "an ADR
  becomes unexpectedly necessary" condition firing correctly.
- **ARCH-002A/ARCH-002B** evaluated three representations and recorded
  **ADR-009 — Per-Service Discovery Evidence Is a Correlated Record**:
  explicitly-named, typed fields on a per-port record, never a generic
  metadata dictionary. The rejection of the generic-dict alternative was
  explicit and reasoned, not just a default choice (`docs/ADR.md`
  ADR-009 Alternatives Considered).
- **FEAT-003C** implemented `ServiceEvidence`, removing the old parallel
  lists outright rather than keeping both representations alive
  side-by-side.
- **FEAT-003D through FEAT-003I** each added one more evidence type
  (product/version consumption, HTTP title, TLS subject/issuer,
  VMware-version, HTTP auth realm, SMB identity, RDP NTLM identity) —
  and every one of them states, in its own Status block, **"ADR
  Required: No"**, citing ADR-009 or `Device`'s existing incremental-field
  pattern as already settling the question. Six-plus sprints reused one
  architectural decision without needing to revisit it.

### 2.3 Observability: DISC-001 → OBS-001 → OBS-002

**DISC-001** found that missing evidence was overwhelmingly operational
(wrong profile, curated port set, target behavior) rather than a
parser/storage defect — and that finding shaped what got built next:
not a parser fix, but visibility into *why* a scan produced what it
did. **OBS-001** added run/host diagnostics built entirely from data
already produced during discovery (no new collection). **OBS-002** added
a publish/subscribe `RuntimeEventBus` and `RuntimeTelemetryRecorder`
that every subsequent enrichment source (SNMP, in FEAT-005) reused
without modification — `SnmpEnrichmentProvider` publishes to the same
bus, and `RuntimeTelemetryRecorder` computed its phase durations with
"zero SNMP-specific code," per ARCH-012's own framing, later confirmed
directly in this session's BENCH-003 measurements.

### 2.4 Reporting: REPORT-001 → REPORT-002 → REPORT-003

**REPORT-001** redesigned the Markdown report around per-device
Identity/Evidence/Classification blocks — a presentation-only change
that introduced no new field or model. **REPORT-002** added versioned,
non-overwriting report output paths and `RunMetadata`, embedded directly
in each report "so a single Markdown file can stand alone." **REPORT-003**
(this session) is the clearest evidence yet that this reporting
architecture is stable under new evidence types: extending it to surface
four new SNMP fields required one new helper method and four new CSV
columns — no new report section, no layout change, confirmed by 384/384
tests passing and a byte-for-byte-unchanged output for every device
without SNMP evidence.

### 2.5 Knowledge: KNOW-001/002/003

**KNOW-003** built the Observation → Knowledge → Rule lifecycle's first
stage (structured, validated, version-controlled JSON observations under
`knowledge/observations/`) but left it **deliberately inert**: nothing
in the runtime calls `capture_unresolved_device()` — confirmed directly
in this session (`grep` for the function's only callers finds test files
and the package's own `__init__.py` export, nothing in
`networkmapper/application.py` or `discovery_engine.py`). This was an
explicit scope boundary in KNOW-003's own report, not an oversight — see
Section 6.

### 2.6 Discovery expansion: ARCH-010/FEAT-004 (DEEP) and ARCH-012/ADR-010/FEAT-005 (SNMP)

**ARCH-010/FEAT-004** defined and implemented the DEEP scan profile as
STANDARD's argument set extended along approved axes — no parallel
implementation, one shared `_discover_with_enrichment()` method for both
profiles.

**ARCH-012** is Phase 2's second full Investigation → Architecture
Review → ADR → Implementation → Consumption → Measurement → Presentation
cycle, and the more architecturally significant one: SNMP is
"architecturally unlike every discovery source NetworkMapper has
integrated so far" (ARCH-012's own framing) because it only ever
enriches hosts another source found — it has no host-discovery role.
This produced **ADR-010 — Enrichment Providers Operate on
Already-Discovered Devices**, a new `EnrichmentProvider` abstraction
structurally distinct from `DiscoveryProvider`, with a mandatory
fallback-only merge rule generalized from a pattern `NmapProvider`
already used privately for its own SMB/RDP merge. **FEAT-005**
implemented it. **RULE-004** (this session) wired `sysDescr` into five
existing rules' identifier tiers, explicitly declining to add new
independent-trigger keywords without evidence (Section 6, RULE-004's own
report). **BENCH-003** (this session) measured the real cost/benefit
with a purpose-built, throwaway SNMPv2c test agent — not an estimate.
**REPORT-003** (this session) closed the loop by surfacing the collected
evidence in the deliverable report.

This full chain — one new evidence source, from architecture decision
through measured operational value through customer-facing presentation
— is the single most complete demonstration of Phase 2's engineering
discipline operating end-to-end, and this retrospective leans on it
heavily in Sections 4 and 5 for exactly that reason: it is not a
single sprint's claim, it is five independent sprints' worth of
converging evidence.

### 2.7 Process: ARCH-001A/001B, DOC-001, ARCH-011

Phase 2 also spent real effort on its own process discipline:
`ARCH-001A/001B` consolidated three overlapping workflow documents into
a canonical Engineering Handbook and recorded Mandatory Stop Conditions
(`docs/process/stop-conditions.md`) directly from real incidents already
observed in this project's history (the KNOW-001 UDR example that didn't
exist, the DEV-002 checkbox that stayed unmarked for eleven sprints).
`DOC-001` retroactively reconciled `ROADMAP.md` with already-shipped work.
`ARCH-011` corrected stale "planned" claims in customer-facing
documentation for capability that had already shipped. All three are
instances of the same underlying problem recurring — see Section 6.

---

## 3. Validated Decisions

Each entry names the decision, the ADR or report that made it, and the
concrete, later evidence that it held up in practice — not just that it
was reasoned well at the time.

**ADR-009 (Per-service correlated evidence) — validated by reuse, not
just by the decision itself.** Six-plus subsequent sprints (FEAT-003D
through FEAT-003I, and FEAT-005's `Device`-level fields) extended the
evidence model using ADR-009's incremental-named-field pattern and
explicitly declared "ADR Required: No" each time. An architectural
decision that keeps paying for itself across many later sprints without
needing revisiting is strong evidence it was the right one — the
counterfactual (a generic metadata dict, explicitly considered and
rejected in ADR-009) would have required no such reuse discipline and
was rejected specifically because it would have undermined
explainability.

**ADR-010 (EnrichmentProvider) — validated by a second, structurally
different provider working without touching `NmapProvider`.** FEAT-005
added `SnmpEnrichmentProvider` and a two-phase orchestration change to
`DiscoveryEngine.discover()`; `NmapProvider`'s own behavior is
unaffected — confirmed by ARCH-012's own regression coverage
requirement and reconfirmed by this session's BENCH-003, which measured
STANDARD's real single-host timing (Host Discovery 0.26s, Service
Enrichment 9.12s) and found it unchanged from BENCH-002's pre-SNMP
measurement (0.21s/9.00s) to within normal variance.

**ADR-002/003/004 (RuleResult, first-match-wins, read-only evidence
API) — validated by every classification sprint since.** RULE-002,
RULE-003, and RULE-004 each add or reorder rules without touching the
`ClassificationRule`/`RuleResult` contract or the evaluation model; each
sprint's own Status block confirms this explicitly. First-match-wins
determinism is also what let BENCH-003 explain, with certainty rather
than guesswork, *why* five SNMP-responsive devices in its fixture showed
zero classification change: each device's higher-precedence evidence
(vendor, product string, or HTTP auth realm) was checked earlier in a
deterministic priority chain and returned first.

**The fallback-only merge rule (first established informally in
`NmapProvider`'s SMB/RDP merge, formalized as part of ADR-010) —
validated by direct code inspection three times over.** FEAT-003I's SMB/
RDP merge, FEAT-005's SNMP `sysName`→`hostname` fallback, and this
session's BENCH-003 Track A (which queried a real SNMP agent and
confirmed `device.hostname` was set from `sysName` only because it had
been empty) all independently confirm the same rule holds under real
execution, not just under unit-test mocks.

**KNOWLEDGE-LIFECYCLE.md's "knowledge before rules" bar — validated by
a real refusal, not just a stated policy.** RULE-003's `NetworkApplianceRule`
recognizes exactly one NAS identifier (`"readynas"`) because BENCH-002
produced exactly one corroborated case; RULE-004 explicitly declined to
add a bare `"cisco"` `sysDescr` keyword despite ARCH-012 itself citing a
Cisco IOS `sysDescr` example, because that keyword's risk (collision
with phone/AP/firewall classification) was concretely identified during
implementation, not hypothetically. Both are documented refusals, not
silent omissions — a meaningfully stronger form of validation than "the
policy exists."

---

## 4. Lessons Learned

**Assumptions validated:**

- **"Corroboration, not replacement" is safe to state as a design
  principle before it is ever measured, and it held up when it finally
  was.** ADR-010 stated this as a requirement in the abstract; BENCH-003
  measured it directly and found exactly the predicted behavior — every
  SNMP-responsive device in its fixture that already had stronger
  evidence showed byte-identical classification reasoning before and
  after SNMP enrichment. The principle was not weakened or complicated
  by contact with real execution.
- **An architecture decision that generalizes an already-working private
  pattern is lower-risk than inventing a new one.** ADR-010's
  fallback-only merge rule and its `EnrichmentProvider` boundary were
  both explicitly derived from `NmapProvider`'s own internal SMB/RDP
  merge, already proven in production. This is called out directly in
  ADR-010's own Rationale ("generalizes a pattern `NmapProvider` already
  uses... rather than each future enrichment source re-deriving or
  inconsistently resolving the same precedence question") and is a
  repeatable lesson, not a one-off.
- **Investigation-first sequencing catches real, expensive mistakes
  before they reach production code.** FEAT-003B's escalation of the
  parallel-list correlation gap, caught during an investigation sprint
  rather than discovered mid-implementation of FEAT-003C, is the clearest
  example — but BENCH-002's own tooling bug (a `json.dumps`/`json.loads`
  round-trip silently converting an integer port key to a string,
  breaking RDP evidence extraction) shows the same discipline applied at
  smaller scale: caught by inspecting intermediate data rather than
  trusting a first result.

**Assumptions disproven, or found narrower than expected:**

- **"SNMP support is complete" (FEAT-005/RULE-004's own framing) turned
  out to mean something narrower than it sounded.** BENCH-003 found that
  in a realistic device mix, SNMP evidence changed zero classifications
  — every SNMP-responsive device already had stronger evidence.
  Completeness of *collection and wiring* is not the same claim as
  completeness of *operational value*, and Phase 2's own sprint sequence
  is the direct evidence this distinction matters: RULE-004 shipped
  believing (correctly, on its own narrow terms) that it had wired SNMP
  into classification; it took a dedicated measurement sprint to learn
  how conditional that value actually is.
- **Collecting evidence "because it's free" (ARCH-012's own justification
  for `sysUpTime`/`sysContact`/`sysLocation` — "the marginal runtime cost...
  is zero, because they ride the same PDU") does not by itself guarantee
  the evidence reaches anyone who benefits from it.** BENCH-003 found, by
  direct source inspection, that none of the five collected SNMP fields
  appeared anywhere in the Markdown or CSV report for two full sprints
  (FEAT-005, RULE-004) after collection began. "Free to collect" and
  "actually delivered to the technician" are independent properties, and
  Phase 2 shipped a real gap between them for a measurable period before
  REPORT-003 closed it.
- **A device-level identity fact does not automatically improve
  classification just because it is now available.** `ServiceEvidence.version`
  has carried an explicit docstring note since FEAT-003C — "not currently
  read by any classification rule" — and still does; `smb_signing`
  carries the same kind of note from FEAT-003H and still does today.
  These are not oversights; ARCH-003 and FEAT-003H both assessed them and
  found no reliable device-type signal. The lesson is that Phase 2's own
  collect-first discipline deliberately produces a standing population of
  collected-but-unconsumed fields, and that population is a feature of
  the discipline working correctly, not a queue of bugs to clear.

**Decisions that measurably reduced later implementation effort:**

- ADR-009 removed a design question (how does new per-service evidence
  get represented?) from at least six subsequent sprints' scope, each of
  which could spend its own investigation effort on the evidence itself
  rather than on where it lives.
- ADR-010/`EnrichmentProvider`'s fallback-only merge rule meant FEAT-005
  needed no new precedence logic — `_merge()` in `snmp_provider.py` is a
  five-line loop reusing a rule the architecture had already settled.
- OBS-002's `RuntimeEventBus`/`RuntimeTelemetryRecorder` meant FEAT-005's
  SNMP phase got real, accurate phase-duration telemetry "with zero
  SNMP-specific code" (ARCH-012's phrase, confirmed directly in this
  session's BENCH-003 measurements) — an entire observability
  requirement satisfied by reuse rather than new implementation.
- The benchmark methodology BENCH-002 established (mock only the
  lowest-level wire call — `nmap.PortScanner.scan()` — and let everything
  downstream execute for real) was directly reusable by BENCH-003 against
  a structurally different provider (`SnmpEnrichmentProvider`/
  `SnmpClient`), because FEAT-005 had already built the matching
  dependency-injection seam (`SnmpClient` as an injectable interface)
  specifically so it *could* be mocked that way. A benchmarking pattern
  and a testability decision made in different sprints (BENCH-002,
  FEAT-005) turned out to compose without coordination, because both
  followed the same underlying principle (`ENGINEERING.md`: "Prefer
  dependency injection").

---

## 5. Recurring Design Patterns

Each pattern below is stated once, then grounded in at least two
independent sprints so it reads as an observed pattern rather than a
single example dressed up as a trend.

**Producer before consumer, and it is acceptable for the gap to persist
indefinitely.** `Device.operating_system` existed, fully wired, from
before FEAT-003A with zero producers until FEAT-003H. `ServiceEvidence.version`
has had zero classification consumers since FEAT-003C and still does.
KNOW-003's entire capture subsystem has had zero runtime callers since
it was built and still does. SNMP's `sysObjectID` has been collected
since FEAT-005 and, by RULE-004/BENCH-003's own explicit, repeated
decision, still has no interpreter anywhere. This is not drift — every
one of these gaps is a documented, deliberate choice, not a discovered
defect, which is what distinguishes this from ordinary unfinished work.

**Canonical evidence: explicit named fields, never a generic
container.** ADR-009 rejected a generic per-port metadata dictionary by
name. Every evidence field added since — `http_title`, `tls_subject`,
`tls_issuer`, `http_auth_realm`, `computer_name`, `domain`, `smb_signing`,
all six SNMP system-group fields — is a new explicitly named attribute,
never a key in an open-ended dictionary. `RuleResult.reason`'s
explainability depends on this directly: a rule can only say what
matched by name because every field it reads has one.

**Provider independence, proven by non-interference.** ADR-010's
`EnrichmentProvider` split exists specifically so a second evidence
source cannot silently corrupt or race the first. The proof this worked
is negative evidence, which is the strongest kind here: FEAT-005 shipped
with zero changes to `NmapProvider`'s own logic, and BENCH-003
independently re-measured STANDARD's timing afterward and found it
unchanged.

**Benchmark-driven engineering, applied to genuinely different
questions each time.** BENCH-002 measured discovery-profile cost/benefit
(FAST/STANDARD/DEEP) and found DEEP's diminishing returns empirically
rather than assuming them from its larger argument set. BENCH-003
measured SNMP's operational value and found its classification payoff
narrower than RULE-004's own framing implied. Both required building
real measurement infrastructure (a real local HTTP server in BENCH-002;
a real, throwaway SNMPv2c agent in BENCH-003) rather than trusting
estimates, and both explicitly separated "real, if narrow, measurement"
from "synthetic, broader coverage" instead of blending the two into one
number.

**Knowledge before rules, enforced as a refusal.** RULE-003's single-
keyword `NetworkApplianceRule` and RULE-004's declined Cisco `sysDescr`
keyword (Section 3) are the same discipline applied in two directions —
one adding a rule because evidence justified it narrowly, one declining
to widen a rule because evidence did not justify it yet.

**Corroboration over replacement, at two different layers.** At the
merge layer, `EnrichmentProvider`'s fallback-only rule means a later
source can fill a gap but never overwrite an earlier source's fact. At
the classification layer, `first_matching_identifier`'s SNMP parameter
(RULE-004) is checked last in its priority chain specifically so a
stronger, earlier-checked source of evidence is always preferred for the
reported reason. Both layers independently arrived at the same
directional bias — earlier/stronger evidence wins — without one being
derived mechanically from the other.

**Investigation → Architecture Review → Implementation → Validation,
completed end-to-end at least twice.** The ADR-009 chain
(FEAT-003A/B → ARCH-002A/B → FEAT-003C onward) and the ADR-010 chain
(ARCH-012 → FEAT-005 → RULE-004 → BENCH-003 → REPORT-003) are both full,
multi-sprint demonstrations of `docs/process/sprint-lifecycle.md`'s
canonical sequence actually being followed under real scope pressure,
not just described.

---

## 6. Technical Debt

Scoped strictly to debt affecting maintainability, correctness, or
extensibility today — not feature requests, not Phase 3 ideas. Each
item is independently verifiable against current repository state, not
asserted from memory of past reports.

**1. No relationship/topology model exists anywhere in the canonical
data model.** `NetworkGraph` is a flat `dict[str, Device]`
(`networkmapper/core/network_graph.py:13`) with `add_device`,
`get_device`, `all_devices`, and `device_count` — no edges, no
`Interface`, no `Link`. `ENGINEERING.md`'s own Core Principles have
named `Interface` and `Link` as intended models since before this
retrospective's sprint series began, and `docs/architecture/overview.md`
already documents the gap plainly: "NetworkGraph is implemented as an
inventory container, not a full topology-analysis system." This is
architectural debt, not a missing feature, because it has now
independently blocked three separate investigations from collecting
evidence they identified as valuable: FEAT-003E/ARCH-003 deferred
SNMP `ifTable`/LLDP/CDP topology evidence specifically because "no
representation exists to receive it"; ARCH-012 reconfirmed the same
finding for SNMP interface inventory without new information. A gap
that independently stops three unrelated investigations at the same
wall is a structural property of the codebase, not a coincidence of
scope.

**2. The Knowledge Repository's capture path is fully built and fully
disconnected from the runtime.** `capture_unresolved_device()`
(`networkmapper/knowledge/capture.py`) is tested and exported from
`networkmapper.knowledge.__init__`, but has no caller anywhere in
`networkmapper/application.py` or `networkmapper/discovery/discovery_engine.py`
— confirmed directly in this session by searching every non-test
caller. KNOW-003 scoped this deliberately ("nothing in the application
calls the capture function automatically either — see Capture Policy
for why that last piece was left as an open decision"), so this is not
an oversight, but the debt is real regardless of intent: an entire
completed subsystem currently produces zero observations from real
runs, meaning the Observation → Knowledge → Benchmark → Classification
lifecycle KNOWLEDGE-LIFECYCLE.md documents has no live input source
today.

**3. `devtools validate`'s fast regression list requires permanent
manual curation, and the pattern that causes it to go stale has already
recurred.** TEST-001 found and named this exact failure mode once
(`STANDARD_REGRESSION_TESTS` silently excluding entire test files) and
its fix — `validate --all`, which discovers every `tests/test_*.py`
module automatically — only solved it for *comprehensive* validation.
The fast list (`devtools/validate.py`'s `STANDARD_REGRESSION_TESTS`,
12 modules today) is still a hardcoded tuple, and it still does not
include `test_csv_exporter`, `test_markdown_exporter`, `test_snmp_provider`,
`test_snmp_client`, or `test_discovery_engine` — confirmed directly
against the current file. This means the canonical fast command
(`python -m devtools validate`, the one `ENGINEERING.md` lists first
under Canonical Developer Commands) would not catch a regression in
either exporter or in SNMP enrichment today. This is the same debt
TEST-001 diagnosed once, in a different subsystem, still present in a
newer one.

**4. `ROADMAP.md`'s "Current Priority" section is stale in a way that
recurs a documented failure pattern.** ARCH-001A already found and
named this exact failure mode once (`ROADMAP.md` pointing at a sprint,
`DEV-002`, that had actually been completed eleven sprints earlier,
unnoticed). As of this retrospective, the same section still describes
ARCH-012 as the most recent milestone and names FEAT-005 as "Next
sprint" — but FEAT-005, RULE-004, BENCH-003, and REPORT-003 have all
since shipped. Phase 6's checklist still marks "SNMP enrichment
(architected — ARCH-012/ADR-010; implementation not started)" as
unchecked, which is now factually incorrect — FEAT-005 implemented it.
This retrospective does not correct `ROADMAP.md` (out of this sprint's
explicit scope), but records the recurrence as debt: the process gap
ARCH-001A identified and reported once has not been structurally
closed, only patched for the specific instance found at the time.

**5. Minor: one small piece of dead code in the CSV exporter.**
`_stringify_value()` in `networkmapper/exporters/csv_exporter.py` has
existed, unused, since before this session — `CsvExporter.export()`
uses inline `value or ""` instead. Low-impact on its own, but worth
naming because it is the same category of small, silently-accumulating
debt TEST-001/STAB-001 were chartered to sweep for once already.

**Explicitly not counted as debt** (per this section's own scope):
`ServiceEvidence.version`'s lack of a classification consumer, `smb_signing`'s
lack of one, and `sysObjectID`'s lack of any interpreter are each the
direct, documented, evidence-gated result of an investigation that
looked and found no justification — not unaddressed gaps. Counting
deliberate, reasoned non-implementation as debt would blur the exact
distinction Section 5's "producer before consumer" pattern depends on.

---

## 7. Phase 2 Engineering Principles

Each principle below is stated only because completed Phase 2 work
demonstrates it, not because it sounds correct in the abstract.

**Collect evidence before interpreting it, and let the gap between the
two persist until real evidence justifies closing it.** Demonstrated by
every field in Section 6, item "Explicitly not counted as debt," and
directly by ARCH-012's own Implementation Sequence, which scoped SNMP
classification consumption (RULE-004) as a distinct, later, evidence-
gated sprint rather than bundling it into collection (FEAT-005).

**Represent evidence as explicit, named facts — never a generic
container — even when it costs more up-front design effort.** ADR-009's
explicit rejection of a generic per-port metadata dictionary, reaffirmed
by name in ARCH-012's own OID-handling guidance ("No vendor-specific OID
database is embedded in the provider... `sysObjectID` is stored
verbatim").

**Prefer deterministic, explainable reasoning over confidence scoring or
heuristics that can't be traced to specific evidence.** `RuleResult.reason`
exists specifically so "why" is always answerable in terms of named
evidence (ADR-002), and `confidence_contribution` has existed, unused,
in every `RuleResult` since ADR-002 was accepted — present in the
contract because the architecture anticipated it might be needed, never
populated because determinism has been sufficient so far.

**Architecture review precedes implementation whenever a sprint
surfaces a genuine, unanticipated design question — and implementation
sprints are expected to recognize that moment and stop.** FEAT-003B
stopping short of implementing FEAT-003C is the clearest single example;
ARCH-012 preceding FEAT-005 is the clearest recent one.

**Measure before concluding, and build real measurement infrastructure
when an estimate would be a guess.** BENCH-002's real single-host Nmap
timing and BENCH-003's real, throwaway SNMP test agent are both cases
where the sprint could have estimated a plausible number and chose not
to.

**Corroborate rather than overwrite, at every layer that merges
evidence from more than one source.** Demonstrated at the provider layer
(ADR-010's fallback-only merge) and, independently, at the
classification layer (RULE-004's SNMP-checked-last priority chain) —
two different subsystems converging on the same directional rule without
one requiring the other.

**A capability is not "done" until it reaches the report a technician
actually delivers.** This principle is not written down anywhere in
`ENGINEERING.md` as of Phase 2's start, but this session's own
FEAT-005 → RULE-004 → BENCH-003 → REPORT-003 chain is the direct
evidence for stating it now: BENCH-003 is what discovered the gap
between "collected and classified" and "visible to the customer," and
REPORT-003 is what closed it. Phase 3 should treat this as an explicit,
now-demonstrated principle, not assume it holds automatically for future
evidence sources.

---

## 8. Phase 3 Readiness Assessment

Evaluated against the four named candidate enrichment sources — WMI,
SSH, Redfish, VMware — without recommending any of them, per this
sprint's explicit instruction.

**The provider/enrichment boundary itself is ready for a second
credential-based, host-level-fact source, and WMI is the closest fit to
what has already been proven.** `EnrichmentProvider.enrich(devices) ->
None` (`networkmapper/discovery/enrichment_provider.py`) has exactly one
concrete implementation today (`SnmpEnrichmentProvider`) — one data
point, not a fully generalized pattern — but every element of that one
implementation generalizes cleanly to a second, structurally similar
source: the fallback-only merge rule, the `RuntimeEventBus`/telemetry
integration (reusable with zero changes, per Section 4), the
runtime-only credential dataclass pattern (`SnmpCredentials`'s
`repr=False` + custom `__repr__`, environment-variable-first supply,
structurally excluded from `Device`/`RunMetadata`/`Observation`), and
the dependency-injection seam that made BENCH-003's real measurement
possible (`SnmpClient` as an injectable interface). WMI's likely
evidence shape — host identity facts (OS, computer name, domain,
installed-software/hardware inventory) reachable via a credentialed
query against an already-discovered host — is architecturally the same
shape SNMP already proved out, including its most valuable near-term
fields (`operating_system`, `computer_name`, `domain`) already having a
fallback-only precedent from *two* prior sources (SMB, RDP) before SNMP
became a third.

**SSH is architecturally the same category as WMI, with a real, unsolved
scoping question SNMP didn't have to answer.** SNMP's evidence surface
was narrowed to six fixed, standard OIDs by ARCH-012's own explicit
design work — a small, enumerable, universally-supported set. SSH has no
equivalent "safe six" by protocol design; an SSH `EnrichmentProvider`
would need its own architecture investigation to answer "which commands,
against which host types, are in scope" before implementation could
follow the same narrow, evidence-gated pattern RULE-004 already
demonstrated for classification consumption. The provider/merge/
credential architecture is ready; the evidence-scoping question is not
yet answered, and answering it is exactly the kind of investigation
Phase 2's own lifecycle (Section 2.6, 2.7) is built to produce.

**Redfish and VMware enrichment are the two candidates most likely to
immediately re-encounter Section 6's leading debt item.** Both APIs'
highest-value evidence is inherently relational — Redfish exposes
chassis/power/drive/network-interface component relationships; a VMware
API exposes host-to-VM relationships — and `NetworkGraph`'s flat,
edge-less model has no field to receive either. This is not a reason
Redfish/VMware enrichment *cannot* be built: whatever subset of their
evidence maps to a single device's own named facts (a Redfish-reported
firmware version, a VMware-reported hypervisor build) would follow the
same `EnrichmentProvider`/ADR-009 pattern SNMP already validated. But
their most differentiating value — the relationships — would land
exactly where SNMP `ifTable`/LLDP/CDP already landed twice before: real
evidence with nowhere in the canonical model to go. A future
architecture investigation into either source should expect to
rediscover this constraint, not be surprised by it.

**REST/HTTPS-based sources (Redfish, and depending on API choice,
VMware) would also be the first test of whether ADR-010's failure model
generalizes beyond SNMP's specific quirks.** `SnmpRunDiagnostics`/
`SnmpHostDiagnostics`'s shape is partly SNMPv2c-specific — most notably,
ARCH-012's finding that a timeout, an unreachable host, and a wrong
credential are indistinguishable under SNMPv2c, which is a protocol
property, not a general `EnrichmentProvider` property. A REST API
failure model (distinguishable HTTP 401/403/5xx/timeout) is materially
richer than what SNMP's diagnostics shape was designed to express. The
architecture doesn't prevent a richer failure model — `EnrichmentProvider`
imposes no diagnostics shape at all, deliberately (`SnmpRunDiagnostics`
is SNMP's own type, not a shared base class) — but no future investigation
should assume `SnmpRunDiagnostics` itself is reusable; it should expect
to design a new diagnostics shape the way ARCH-012 did, informed by
ARCH-012's precedent rather than by ARCH-012's specific type.

**Overall assessment: the architectural boundary is ready; the
canonical evidence model is ready for host-level facts and not ready
for relationship-shaped facts; and the failure-model/diagnostics pattern
is proven exactly once, which is enough precedent to follow but not
enough to assume away a new investigation.**

---

## 9. Conclusions

Phase 2's architecture is not merely internally consistent — it has now
been exercised by a second, structurally different evidence source
(SNMP) across the full Investigation → Architecture Review →
Implementation → Consumption → Measurement → Presentation cycle, and
held up under real measurement rather than only under design review.
That is a meaningfully stronger claim than "Phase 2 shipped a lot of
features," and this retrospective's Section 3 evidence is offered as the
basis for making it.

The project's most disciplined, most consistently demonstrated habit is
narrowness: collect evidence before deciding what it means, corroborate
rather than override, and refuse a keyword or a classification without
an observed case to justify it — demonstrated in Section 5 at multiple
independent layers, not asserted once. The project's most consistently
recurring failure mode is not architectural at all: it is documentation
and process bookkeeping (`ROADMAP.md`, the fast validation list) falling
behind shipped work in a pattern that has now been independently
diagnosed twice (TEST-001, ARCH-001A) without being structurally
prevented either time.

Phase 3's single most consequential open question is not which
enrichment provider to build next — it is whether `NetworkGraph` gains a
relationship/topology model before or after the first Phase 3 provider
that would benefit from one. Every other Phase 3 readiness question this
retrospective examined (credential handling, provider boundary,
telemetry integration, benchmark methodology, classification
consumption pattern, reporting integration) has at least one full,
validated precedent to build from. This one does not, and three
independent investigations reaching the same wall is the evidence for
saying so plainly rather than deferring it a fourth time without
comment.
