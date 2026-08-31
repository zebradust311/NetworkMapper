# Status

Draft — Corrected Pending Formal Verification

Investigation: Complete (DOC-001C)

Correction Pass: Two passes applied. The first resolved Findings F1–F17
from the DOC-001C adversarial review. The second resolved Findings 1–3
from the formal verification audit that followed. See Section 11 for the
resolution status of each.

Governs: Nothing yet. This document catalogs and classifies NetworkMapper's
engineering-documentation artifact types, their purposes, and their
relationships. It does not itself grant or restrict editing authority
(that is [DOC-001A](Change-Authority-Policy.md)'s subject) and does not
itself define the sprint lifecycle (that is
[DOC-001B](Engineering-Workflow.md)'s subject). Where this document's
findings overlap those two, it cites them rather than restating or
re-deciding their conclusions.

Production Code Modified: No — this document is documentation/process
investigation only.

ADR Required: No, for the same reason DOC-001A's and DOC-001B's own status
blocks give: this concerns documentation taxonomy, not a product-architecture
decision. `docs/reports/README.md`, `docs/ADR.md`, and `docs/process/` already
have this document's correct home.

This document has now been through one investigation, one adversarial
review, one formal verification audit, and two correction passes
responding to them. It has **not** yet undergone a second formal
verification pass or engineer approval — that is deliberately the next
step, not this one. Per the correction-pass instructions, no repository
file other than this one was modified in either pass.

---

## 1. Purpose

NetworkMapper's engineering documentation is not one system — it is several
overlapping ones, each grounded in its own README or status-block convention,
that have never been inventoried together in one place. `docs/ADR.md` defines
what an ADR is. `docs/reports/README.md` defines what a report is (and
implicitly, via its own Naming Convention and Investigation Status sections,
what an investigation and an implementation report are). `docs/architecture/README.md`
defines what an architecture document is. `docs/process/engineering-handbook.md`
defines a Sprint Prefix Taxonomy. `docs/knowledge/README.md` defines what
Knowledge is. [DOC-001A](Change-Authority-Policy.md) and
[DOC-001B](Engineering-Workflow.md) each, in the course of answering a
narrower question (editing authority; workflow shape), inventoried pieces of
this landscape as evidence — DOC-001B Section 4 in particular already
tabulates ADR/ARCH/PLAN/FEAT/VERIFY/DOC — but neither set out to catalog
NetworkMapper's documentation as a whole, and DOC-001B's own Known Gaps
(Section 11, items 1 and 2) name two taxonomy questions it deliberately left
open rather than resolved.

This investigation's task is narrower than "redesign the taxonomy" and
broader than DOC-001A/DOC-001B's own scope: catalog every artifact type
actually in use, ground each in the evidence for its purpose, and name where
the existing evidence is inconsistent or silent — without inventing new
artifact types or proposing repository restructuring the evidence doesn't
already call for. Several of this document's findings sharpen gaps
DOC-001A/DOC-001B already named in the abstract into concrete, named
instances; where that happens, it is noted explicitly rather than presented
as a new discovery.

---

## 2. Scope and Method

This investigation read: `docs/ADR.md` (all thirteen ADRs); `docs/reports/README.md`;
`docs/architecture/README.md`, `overview.md`, and `classification.md`'s
headers; `ENGINEERING.md`; `docs/AI-DEVELOPMENT-GUIDE.md`; every file under
`docs/process/`; `docs/knowledge/README.md` and `FIELD-OBSERVATIONS.md`;
`docs/development/Change-Authority-Policy.md` (DOC-001A) and
`Engineering-Workflow.md` (DOC-001B) in full; `docs/reports/DOC-001-Sprint-Catalog-Cleanup.md`;
`docs/plans/PLAN-012B-Bridge-MIB-Forwarding-Table-Relationship-Provider.md`;
`docs/reports/ARCH-023-LLDP-Relationship-Provider-Architecture.md`;
`docs/reports/ARCH-001A-Engineering-Workflow-Investigation.md`; the
directory listing of `docs/reports/` in full (every filename present); the
git log messages for the ARCH-023 → FEAT-012A → ARCH-024 → FEAT-012B →
DOC-001A → DOC-001B commit sequence; `ROADMAP.md`'s section headers and its
SNMP/LLDP/ARP-related content specifically; and, for root-level and
`docs/`-level documents whose type was otherwise unclear, the opening lines
of `docs/ARCHITECTURE.md`, `docs/classification-rules.md`,
`docs/field-notes.md`, `docs/DEPENDENCIES.md`, and `docs/LAB.md`.

Not read in full: the bodies of most individual `docs/reports/*.md` files
(their titles, naming pattern, and status-block conventions were sampled,
not every finding independently re-verified); `docs/knowledge/vendors/`
contents beyond its directory listing; `knowledge/observations/`'s JSON
schema. Where a conclusion below rests on a title or a directory listing
rather than a fully-read document, that is the evidentiary basis — this is
named, not smoothed over, consistent with DOC-001A's and DOC-001B's own
discipline about evidentiary strength.

**Correction-pass addendum.** Responding to the adversarial review, this
investigation additionally: read `docs/reports/ARCH-024-Bridge-MIB-Relationship-Provider-Architecture.md`'s
status block directly; confirmed line counts for `ENGINEERING.md` (782) and
`docs/AI-DEVELOPMENT-GUIDE.md` (479) against `docs/process/engineering-handbook.md`
(45); re-read `docs/reports/ARCH-001A-Engineering-Workflow-Investigation.md`
beyond the excerpt originally sampled; confirmed via `git ls-files` that
`review.diff`, `review.patch`, and `test_results.txt` are tracked repository
files; and confirmed the absence of `RULE-001` and `BENCH-001` against the
`docs/reports/` directory listing already obtained. These are named here as
evidence gathered during correction specifically — not represented as part
of the original investigation's reading, per Finding F5.

---

## 3. Complete Artifact Type Inventory

Every engineering artifact type this investigation found evidence of
currently being in use, grounded in the cited file or convention:

| Type | Where it lives | What it is |
|---|---|---|
| **ADR** | `docs/ADR.md` (single file, thirteen numbered entries) | A recorded, accepted architectural decision — the project's standing constraints. Per `docs/ADR.md`'s own header: "Only accepted architectural decisions are recorded here... ADRs are recorded in chronological order and are never renumbered." |
| **ARCH** (report) | `docs/reports/ARCH-*.md` (e.g. `ARCH-001A`, `ARCH-012`, `ARCH-020` through `ARCH-024`) | An investigation report answering a design question, per `docs/reports/README.md`'s Investigation Report format. May recommend an ADR, a PLAN, or a FEAT. Historical once frozen (Section 4, below). |
| **PLAN** | `docs/plans/PLAN-*.md` (one instance: `PLAN-012B`) | A file-level implementation commitment translating an approved ARCH into a concrete change inventory, per PLAN-012B's own status block ("the implementation plan for FEAT-012B, produced against ARCH-024"). Not yet in the Sprint Prefix Taxonomy table (Section 9). |
| **FEAT** (investigation) | `docs/reports/FEAT-*A.md`, `FEAT-*B.md`, etc., plus at least one unsuffixed instance (`FEAT-003A` through `FEAT-003I`, and `FEAT-004`, which carries no letter suffix — corrected per F13/F14) | An Investigation Report, structurally identical to an ARCH report (independently confirmed against `FEAT-003A`'s own status block during the correction pass), scoped to a feature question rather than a pure-architecture one. The Sprint Prefix Taxonomy table describes `FEAT-` as covering both "Feature investigation/implementation" under one prefix. |
| **FEAT** (implementation) | Source commits (e.g. `FEAT-003C`, `FEAT-010A`, `FEAT-011A`, `FEAT-012A`, `FEAT-012B`); should also produce `docs/reports/FEAT-*.md` Implementation Reports per `docs/reports/README.md`'s mandatory format | The actual code/test change implementing an approved ARCH or PLAN. `docs/reports/README.md` states Implementation Reports are mandatory for every implementation sprint — Section 8 documents that this has not happened for the most recent four FEAT sprints (corrected per F1; a recurrence of a pattern with deeper history — see Section 9, item 8). |
| **TEST** | `docs/reports/TEST-*.md` | Investigation/implementation reports scoped to validation and test infrastructure (`TEST-001`, `TEST-003`). The series skips `TEST-002` — see Section 9, item 8. |
| **BENCH** | `docs/reports/BENCH-*.md` | Benchmark comparative-analysis reports (`BENCH-002`, `BENCH-003`). Not present in the Sprint Prefix Taxonomy table (Section 9); the series begins at `002` — see Section 9, item 8. |
| **DISC** | `docs/reports/DISC-*.md` | Discovery-subsystem investigation reports (`DISC-001`). Present in the Sprint Prefix Taxonomy table as "Discovery subsystem work." |
| **KNOW** | `docs/reports/KNOW-*.md`; also `docs/knowledge/` itself (Section 3, Knowledge documents, below) | Knowledge Framework reports. Only `KNOW-003` exists as a persisted file; `ARCH-001A`'s own text references `KNOW-001`/`KNOW-002` as earlier sprints in this series, but no corresponding file exists under `docs/reports/`, consistent with `ARCH-001A`'s own finding that early investigation sprints were sometimes chat-only and never persisted — see Section 9, item 8, for how much further this pattern extends. |
| **RULE** | `docs/reports/RULE-*.md` | Classification-maturation reports (`RULE-002` through `RULE-004`). Not present in the Sprint Prefix Taxonomy table; the series begins at `002` — see Section 9, item 8. |
| **STAB** | `docs/reports/STAB-*.md` | An evidence-pipeline-cleanup report (`STAB-001`). Not present in the Sprint Prefix Taxonomy table. |
| **OBS** | `docs/reports/OBS-*.md` | Discovery-observability/runtime-telemetry reports (`OBS-001`, `OBS-002`). Not present in the Sprint Prefix Taxonomy table. |
| **REPORT** | `docs/reports/REPORT-*.md` | Reports about the *product's own reporting/export subsystem* (`REPORT-001` through `REPORT-003`) — a different concept from "a `docs/reports/` artifact" generally. Not present in the Sprint Prefix Taxonomy table. See Section 9 for the naming ambiguity this creates. |
| **DOC** (lightweight) | `docs/reports/DOC-*.md` (one instance: `DOC-001-Sprint-Catalog-Cleanup.md`) | Matches the Sprint Prefix Taxonomy table's stated definition exactly: "Documentation-only changes," example "Refresh project documentation." `DOC-001`'s own status block: "Production Code Modified: No... this sprint adds retrospective roadmap bookkeeping." |
| **DOC** (governance) | `docs/development/*.md` (`Change-Authority-Policy.md` = DOC-001A; `Engineering-Workflow.md` = DOC-001B; this file = DOC-001C) | A structurally different, much heavier artifact than the lightweight DOC report above: a governance investigation with its own adversarial-review/formal-verification/correction-pass cycle (DOC-001A Section 12; DOC-001B Section 12), living in a directory (`docs/development/`) the Sprint Prefix Taxonomy table and `docs/process/engineering-handbook.md`'s "Where Process Documentation Lives" list do not mention at all. See Section 9. Normative once adopted, for its own stated subject only; revisable in place afterward, unlike ARCH (DOC-001A Section 10; DOC-001B Section 7) — merged from a separately-listed "Governance document" row per Finding F3, since both described the same three files. |
| **VERIFY** | No persisted format exists | An audit pass checking a completed FEAT against its authorizing ARCH and PLAN. Currently exists only as chat-turn output (DOC-001A Section 7's VERIFY row; DOC-001B Section 11, item 5). Not a file type yet, in the sense every other row in this table is. |
| **Architecture document** | `docs/architecture/overview.md`, `docs/architecture/classification.md` | Canonical, living documentation of *implemented* system structure. Explicitly distinct from an ARCH report: `docs/architecture/README.md`'s Documentation Scope states these documents "describe implemented behavior only" and "should not... speculate about planned architecture... describe code that does not exist" — the opposite posture from an ARCH report, which exists specifically to investigate a not-yet-implemented question. |
| **Knowledge document** | `docs/knowledge/README.md`, `FIELD-OBSERVATIONS.md`, `KNOWLEDGE-LIFECYCLE.md`, `OBSERVATION-TEMPLATE.md`, `OBSERVATION-REPOSITORY.md`, `vendors/*.md`; also `knowledge/observations/*.json` | Structured, reviewable operational experience — per `docs/knowledge/README.md`, "not a raw scan result, and... not a classification rule. It sits between the two." Living; matures through a defined lifecycle (Observation → Knowledge → Benchmark → Classification → Validation → Architecture Review, per `docs/knowledge/KNOWLEDGE-LIFECYCLE.md`, cited by ADR-011's Rationale). **Corrected per F16:** `docs/knowledge/vendors/` currently contains only its own `README.md` and `VENDOR-TEMPLATE.md` — no populated vendor-knowledge file exists yet, so this category is real but currently mostly scaffolding rather than populated content. |
| **Process document** | `docs/process/*.md` (`sprint-lifecycle.md`, `engineering-handbook.md`, `engineering-principles.md`, `role-definitions.md`, `stop-conditions.md`, `validation-workflow.md`, `prompt-templates.md`) | Defines the engineering workflow itself — living, normative, and per `docs/process/engineering-handbook.md`, the "authoritative entry point" for how humans and AI collaborate. |
| **Roadmap** | `ROADMAP.md` | Tracks completed milestones and planned work — per `docs/architecture/README.md`'s own cross-reference list. Living; explicitly named as something "Architectural changes update" in both `ENGINEERING.md`'s Documentation section and `docs/AI-DEVELOPMENT-GUIDE.md`'s Documentation Checklist. |
| **Entry-point guide** | `ENGINEERING.md`, `docs/AI-DEVELOPMENT-GUIDE.md` | Per `docs/process/engineering-handbook.md`: these two "cover engineering standards, coding conventions, and product philosophy" / "AI-specific behavioral guidance," and reference the handbook for workflow "rather than each independently defining it." Living. **Corrected per F10:** despite that stated intent, neither is actually thin in practice — `ENGINEERING.md` is 782 lines and `docs/AI-DEVELOPMENT-GUIDE.md` is 479 lines, both substantially longer than `docs/process/engineering-handbook.md` itself (45 lines) and both carrying extensive original content (e.g. `ENGINEERING.md`'s Coding Standards, Git Workflow, Product Vision; `docs/AI-DEVELOPMENT-GUIDE.md`'s command-approval lists and four separate checklists) well beyond merely referencing the handbook. |
| **Lab / research document** | `docs/LAB.md` | Explicitly pre-roadmap: "Ideas recorded here are observations, hypotheses, and product concepts. They are **not** approved features... Ideas graduate into the implementation roadmap only after architectural investigation, engineering review, and an explicit roadmap decision." Living, but structurally outside the ADR→ARCH→PLAN→FEAT chain entirely — it is upstream of an ARCH even existing. |
| **Root architecture narrative** | `docs/ARCHITECTURE.md` | A high-level, apparently free-standing architecture narrative, cross-referenced by `docs/architecture/README.md` as "an existing high-level architecture narrative" but not otherwise integrated into that directory's own Current/Planned Documents lists. Its relationship to `docs/architecture/overview.md` specifically (redundant narrative vs. distinct audience/purpose) was not resolved by this investigation — see Section 10. |
| **Legacy/superseded reference document** | `docs/classification-rules.md`, `docs/field-notes.md` | Two documents that predate or duplicate current canonical equivalents. `docs/classification-rules.md` carries its own header notice: it "predates NetworkMapper's `RuleResult`/evidence-based classification architecture," documents only one rule "in an older pseudo-code format," and is "not a current catalog." `docs/field-notes.md`'s stated purpose ("captures real-world observations made during customer engagements... may later improve NetworkMapper's intelligence") substantially overlaps `docs/knowledge/FIELD-OBSERVATIONS.md`'s canonical, structured successor — see Section 9. |
| **Reference/misc document** | `docs/DEPENDENCIES.md` | A small, living reference table (dependency name, reason, replaceability) — not part of the ADR/ARCH/PLAN/FEAT chain, not versioned by sprint ID. |
| **Ad hoc snapshot artifact** | `review.diff`, `review.patch`, `test_results.txt` (repository root; tracked in git, confirmed via `git ls-files`) | **Added per F12**, a type missing from the original inventory. Committed diff/patch/test-log snapshots with no naming convention, no stated purpose, and no cross-reference from any `.md` file this investigation found. `review.diff` is a raw git-diff snapshot against `ROADMAP.md`. Not part of any documented artifact taxonomy; found only by direct repository inspection during the correction pass, not by reading any document. (`test_results.log` also exists on disk but is untracked, per `.gitignore`.) |

---

## 4. Normative vs. Historical

Grounded directly in each type's own stated lifecycle, not inferred:

- **Normative (binding on future work):** ADR (always, once Accepted); Architecture documents (`docs/architecture/`, describing current implemented behavior); Process documents (`docs/process/`); Governance documents (`docs/development/`, once adopted — neither DOC-001A nor DOC-001B has reached that state yet, per their own status blocks); an approved PLAN, for the FEAT it authorizes specifically; a committed FEAT, as the running system itself; ROADMAP.md, as the record of what is and isn't approved for implementation.
- **Historical (descriptive, non-binding):** ARCH reports and every other `docs/reports/*` report type (FEAT investigation reports, TEST, BENCH, DISC, KNOW, RULE, STAB, OBS, REPORT, and the lightweight `DOC-001`). `docs/reports/README.md`'s own Guiding Principle states this explicitly and generally: reports "are historical engineering artifacts. They are not normative architecture documentation and do not supersede ADRs or other architecture documents."
- **Provisional, not yet either:** Knowledge documents. `docs/knowledge/README.md` describes Knowledge as "provisional — an observation is not automatically true everywhere; it matures through use." Field Observations specifically are pre-Knowledge and carry no authority until corroborated (`docs/knowledge/KNOWLEDGE-LIFECYCLE.md`, cited but not independently re-read in full by this investigation).
- **Explicitly sub-normative, by design:** `docs/LAB.md`. Its own header states ideas there carry "No roadmap commitment" and are "not approved features" — the document exists specifically to hold ideas that are not yet, and may never become, normative.
- **A caveat this classification does not resolve on its own (added per F11):** "Normative" above describes stated authority, not current accuracy. Section 8 independently shows both `ROADMAP.md` and `docs/architecture/` are presently stale relative to the completed ARP/LLDP/Bridge-FDB lineage. A document can hold normative authority while its content is out of date; this section's binary does not capture that distinction, and neither bullet above should be read as certifying that document's current content is accurate.
- **Unclear / not independently determined by this investigation:** `docs/ARCHITECTURE.md`'s status relative to `docs/architecture/overview.md`; `docs/classification-rules.md`'s and `docs/field-notes.md`'s standing (each carries some signal of being superseded-in-spirit but neither has been formally retired) — see Section 10.

---

## 5. Supersession

Two genuinely different supersession mechanisms are demonstrated:

1. **Freeze-and-supersede-by-new-artifact — ADR, and reports generally (illustrated by ARCH) (corrected per formal verification Finding 3 — the label previously named only ADR and ARCH while this item's own body already covers the broader report family).** `docs/ADR.md`: ADRs are "never renumbered." `docs/reports/README.md`: reports are "not updated after completion except to: Correct factual errors. Fix broken references. Correct formatting issues... If a later investigation revisits the same topic, create a new report rather than modifying an existing one." **Not yet demonstrated in this repository:** every existing ADR reads "Accepted"; none has ever been marked superseded or deprecated. DOC-001B Section 7, item 1 already names this as an untested mechanic — this investigation independently confirms the same absence and does not add new evidence either way. This pattern is not limited to ADR and ARCH specifically: Section 4 and Section 6 both treat every `docs/reports/*` type, including the lightweight `DOC-001`, under the same historical/report lifecycle — `DOC-001` belongs here, not in item 2 below (corrected per F2).
2. **Approval-gated, revise-in-place — PLAN and DOC (governance only).** PLAN-012B was corrected in place, before and after approval, rather than becoming a `-v2` file (DOC-001B Section 7, item 2). The same is true, directly observed, of DOC-001A (three correction passes) and DOC-001B (one correction pass so far). **Corrected per F2:** an earlier draft of this item also placed the lightweight `DOC-001` report here. That was an error — `DOC-001`'s own status block shows no correction-pass history, and Section 4 already classifies it as Historical alongside every other `docs/reports/*` type, which follows item 1's pattern instead.

A document that is explicitly marked as superseded-in-spirit without a formal supersession event is a third, apparently unplanned case: `docs/classification-rules.md`'s own header notice functions as an informal supersession marker, but no ADR, ARCH, or DOC artifact records the decision to supersede it, and the file has not been removed, archived, or formally retired — see Section 9.

---

## 6. Permanent-Accumulation Artifacts

Artifacts that grow monotonically, by design, and are never pruned:

- **ADR** — `docs/ADR.md` accumulates every Accepted decision, chronologically, forever (per its own "never renumbered" rule).
- **`docs/reports/`** — every ARCH/FEAT/TEST/BENCH/DISC/KNOW/RULE/STAB/OBS/REPORT/DOC(-lightweight) report ever produced accumulates as a permanent historical record; `docs/reports/README.md` never describes pruning or archival.
- **Knowledge** — `docs/knowledge/FIELD-OBSERVATIONS.md` and `docs/knowledge/vendors/` accumulate observations over the product's operational lifetime by design; this is the explicit purpose of the Knowledge Framework.
- **`knowledge/observations/`** — the structured JSON repository underlying Field Observations (only its directory listing, one file, was examined; its accumulation model was not independently verified against `OBSERVATION-REPOSITORY.md`'s full text).

Artifacts that are bounded, small, and expected to stay that way:

- **PLAN** — one instance exists. **Uncertain, not resolved (corrected per F4):** this bullet's original claim is in tension with Section 3 and Section 7, both of which describe PLAN as ARCH's structural analog (translating an approved ARCH into a FEAT-level commitment) — and ARCH is itself catalogued above as permanently accumulating. If that analogy holds, PLAN would be expected to accumulate the same way, not stay bounded. With only one instance, the evidence does not distinguish "PLAN accumulates like ARCH" from "PLAN stays small"; this document does not resolve which is correct.
- **Governance documents (`docs/development/`)** — three files exist; each is revised in place rather than accumulating new versions per revision.
- **Process documents** — a fixed set of seven files under `docs/process/`, revised in place.

---

## 7. Expected Citation Relationships

Demonstrated across the ARCH-023 → FEAT-012A → ARCH-024 → PLAN-012B →
FEAT-012B lineage and confirmed by DOC-001B Section 8's identical finding,
though the specific *mechanism* is not fully uniform across it (corrected
per F6 — see the FEAT bullet below):

- **An ARCH cites the ADRs and prior ARCH reports it depends on, by number** — ARCH-024 cites ADR-010 through ADR-013 and ARCH-021 directly; ARCH-023 cites ARCH-021 and ARCH-022.
- **A PLAN cites its authorizing ARCH, by section** — PLAN-012B's status block names "ARCH-024-Bridge-MIB-Relationship-Provider-Architecture.md (design authority)"; its body cites specific ARCH-024 sections throughout (e.g. "Section 8," "Section 9," "Section 3/6/7").
- **A FEAT cites its authorizing PLAN and/or ARCH, both in commit-message metadata and in code.** The FEAT-012B commit message carries explicit `Authority:` and `Implements:` trailer fields naming ARCH-024 and PLAN-012B respectively; DOC-001B Section 8 independently confirms in-code comments cite PLAN sections directly (`BRIDGE_FDB_TABLE_MAX_ROWS`'s comment citing "PLAN-012B Section 5, uncertainty #3"). **The mechanism differs by instance, not just the practice (corrected per F6):** `FEAT-012A`'s own commit message cites its authority only as a prose sentence ("Implements ARCH-023 (3a6e48a)"), with no structured trailer field — the `Authority:`/`Implements:` trailer format is confirmed only for `FEAT-012B`. The underlying discipline (cite your authority) holds in both; the specific citation mechanism does not.
- **An ADR cites the ARCH investigation(s) that motivated it** — ADR-009 cites ARCH-002A; ADR-010 cites ARCH-012; ADR-011 cites ARCH-014, ARCH-015, and ARCH-016 explicitly as three independently-converging investigations; ADR-012 cites ARCH-015; ADR-013 cites ARCH-014.
- **A later ADR states explicitly whether it modifies, extends, or leaves an earlier one unmodified** — every ADR from ADR-009 onward carries a "Rationale" subsection enumerating exactly this, by number, for every plausibly-related prior ADR.
- **Governance documents (DOC) cite the process documents they formalize, and each other** — DOC-001B's own Section 2 states its principles are "additive to DOC-001A's, not a parallel version of them," and cites DOC-001A by section throughout rather than restating its content.
- **What is not enforced:** DOC-001B Section 8 states this directly and this investigation found no contrary evidence — "no tooling in this repository currently enforces" any of the above; every citation is a manual writing discipline, checked (when checked at all) only by a VERIFY pass reading the cited source directly.

---

## 8. Expected Production Relationships

What each artifact type is supposed to cause to be updated, per the
project's own stated rules, and whether the evidence shows that happening:

- **An ADR is supposed to be accompanied by updates to `ROADMAP.md`, `docs/architecture/`, and `docs/ADR.md`** — stated identically in `ENGINEERING.md`'s Documentation section, `docs/AI-DEVELOPMENT-GUIDE.md`'s Documentation Checklist, and repeated at the end of every ADR's own Future Work section ("Each of the above requires its own approved sprint and... its own updates to `ROADMAP.md`, `docs/architecture/`, and `docs/ADR.md`.").
- **This investigation found this is not currently happening for the most recent ADR/ARCH/FEAT lineage.** `ROADMAP.md` line 186–189 still lists "SNMP enrichment (architected — ARCH-012/ADR-010; implementation not started)," "LLDP discovery," and "ARP enrichment" as unchecked, planned items — even though ARP (FEAT-010A), LLDP (FEAT-012A), and Bridge-MIB forwarding-table relationships (FEAT-012B) have all already been implemented and committed (confirmed directly in `git log`). `ARCH-001A` originally found and named this same staleness pattern for the `DEV-002` entry ("pointed at a sprint that was actually completed... unnoticed and uncorrected through eleven subsequent sprints"). **Corrected during formal verification:** an earlier draft of this sentence treated `DEV-002` as a resolved, purely historical example, contrasted with the SNMP/LLDP/ARP items as the current instance. That is not accurate — `DEV-002` remains unfixed today: `ROADMAP.md` line 135 still reads `- ⬜ DEV-002 Shared evidence helper library` (unchecked), and `ROADMAP.md`'s own "Current Priority" section (lines 325–327) explicitly acknowledges this without the checkbox ever having been corrected ("DEV-002 was completed as part of the DEV-003 sprint... but was never marked complete here"). `DEV-002` is therefore a second, still-open, self-acknowledged-but-unfixed instance of the same staleness pattern, not a closed predecessor to the SNMP/LLDP/ARP one. `docs/architecture/README.md`'s own Planned Documentation list independently corroborates the same gap from the architecture-documentation side: none of its three planned documents (`discovery.md`, `benchmarking.md`, `developer-platform.md`) mention ARP, LLDP, Bridge-FDB, or the observation/identity/relationship subsystem ADR-010 through ADR-013 established — a gap DOC-001B Section 11, item 2 already named. This investigation independently confirms both the `ROADMAP.md` and `docs/architecture/` sides of that same production gap.
- **A FEAT implementation is supposed to produce a mandatory `docs/reports/FEAT-*.md` Implementation Report** (`docs/reports/README.md`). Confirmed absent for `FEAT-010A`, `FEAT-011A`, `FEAT-012A`, and `FEAT-012B` — already named by DOC-001A Section 7's compliance-gap note and DOC-001B Section 6/11, item 6; this investigation independently confirms the same four filenames are absent from the `docs/reports/` directory listing obtained directly for this investigation.
- **An ARCH is supposed to produce, at minimum, a stated ADR-required determination and a recommended next sprint** (`docs/reports/README.md`'s Investigation Status block). Confirmed present in the two ARCH reports this investigation actually read in full (ARCH-001A, ARCH-023). **Corrected per F5:** an earlier draft of this item also listed `ARCH-024` as "sampled" during the original investigation; Section 2's own Scope and Method never lists `ARCH-024` as read, so that claim exceeded this investigation's disclosed evidence base. `ARCH-024`'s status block was checked directly during the correction pass and does contain both elements (Recommended Next Sprint: `FEAT-013A`) — a fact verified now, during correction, not one the original investigation actually sampled.
- **A Knowledge observation is supposed to eventually produce a benchmark dataset case and, downstream, a classification change** (`docs/knowledge/KNOWLEDGE-LIFECYCLE.md`, cited but not independently re-verified end-to-end by this investigation).
- **A DOC governance document is supposed to change future Claude behavior once adopted, within its own subject only** (DOC-001B Section 4's own Artifact Flow table). Neither DOC-001A nor DOC-001B has reached adoption yet, so no production relationship from either has been exercised.

---

## 9. Taxonomy Inconsistencies and Undocumented Artifact Types

Named here, not resolved, consistent with this project's established
practice of naming an unreached decision rather than silently absorbing or
ignoring it (a practice DOC-001A Section 10 and DOC-001B Section 11 both
cite as precedent, tracing back to ARCH-024 Section 10, item 7):

1. **Five active report prefixes have no entry in the Sprint Prefix Taxonomy table.** `docs/process/engineering-handbook.md`'s table lists `DISC-`, `CLASS-`, `EVID-`, `INTEL-`, `ACC-`, `DEV-`, `DOC-`/`DOCS-`, `KNOW-`, `ARCH-`, `FEAT-`, `TEST-`. Actually present in `docs/reports/`, with real, multi-instance history, but absent from that table: `BENCH-` (two reports), `OBS-` (two reports), `REPORT-` (three reports), `RULE-` (three reports), `STAB-` (one report). **Corrected per F7 — this is a related but not identical category of gap** to the one DOC-001A/DOC-001B already named for `PLAN` and `VERIFY`: `PLAN` and `VERIFY` lack any established persisted-artifact format at all, a structural gap; `BENCH`/`OBS`/`REPORT`/`RULE`/`STAB`, by contrast, are ordinary, well-formed `docs/reports/*.md` reports that already fit the established format — their gap is a missing row in one taxonomy table, not an unresolved artifact shape. Both are real gaps, but the second is narrower than the first.
2. **The inverse gap also holds: several taxonomy-table prefixes have no corresponding persisted report.** `CLASS-`, `EVID-`, `INTEL-`, `ACC-`, `DEV-` all appear in the taxonomy table (and in `ENGINEERING.md`'s own Git Workflow commit-message examples) but no `docs/reports/CLASS-*`, `EVID-*`, `INTEL-*`, `ACC-*`, or `DEV-*` file exists in the current directory listing. **Confirmed, not merely inferred (corrected per F8):** `ARCH-001A` line 68 states this directly for implementation sprints specifically — "No persisted artifact for implementation sprints... Implementation sprints (`FEAT-001C`, `FEAT-002B`, `TEST-002`) produce only a chat-turn summary and a `git diff`... nothing durable survives in the repository" — direct, first-source evidence for the same explanation this item previously offered only as an unverified hedge. See item 8 below for how much further this same pattern extends.
3. **The `DOC-` prefix names two structurally unrelated artifact types that happen to share both a prefix and, in one case, a number.** `docs/reports/DOC-001-Sprint-Catalog-Cleanup.md` matches the Sprint Prefix Taxonomy table's stated definition exactly (lightweight, documentation-only, roadmap bookkeeping). `docs/development/Change-Authority-Policy.md` and `Engineering-Workflow.md` self-identify, in their own text and in their commit messages, as `DOC-001A` and `DOC-001B` — governance investigations with a multi-pass adversarial-review-and-verification cycle, living in a different, unregistered directory (`docs/development/`), and explicitly *not* matching the taxonomy table's "Documentation-only changes" definition. DOC-001B Section 11, item 1 already named this mismatch in the abstract ("a much lighter-weight category than what DOC-001A and this document actually are"); this investigation sharpens it into a concrete collision — `DOC-001` (report) and `DOC-001A` (governance document) are two different artifacts, of two different weights, in two different directories, distinguished from each other only by a letter suffix that itself has no stated rule (why `A`/`B` rather than `002`/`003`, and whether that suffix convention is reserved for governance documents specifically or could collide with a future lightweight `DOC-001A` report, is not addressed anywhere this investigation found).
4. **`docs/development/` itself is an unregistered location.** `docs/process/engineering-handbook.md`'s "Where Process Documentation Lives" section names exactly four locations — `docs/process/`, `docs/architecture/`, `docs/knowledge/`, `docs/reports/` — and does not mention `docs/development/`, even though it is where DOC-001A, DOC-001B, and this document all live. No document this investigation read explains why governance documents were placed in a new, fourth-plus-one location rather than in `docs/process/` (where the workflow they formalize already lives) or `docs/reports/` (where DOC-001's own lighter-weight sibling lives).
5. **`REPORT-` (the sprint prefix for the product's reporting/export subsystem) and `docs/reports/` (the directory every investigation and implementation report lives in) share a name with no stated relationship between them.** They are unrelated concepts — one is a feature area, the other is a documentation directory — but nothing distinguishes them for a reader encountering "the REPORT-001 report" for the first time. This is a naming-collision risk, not a functional defect: no evidence was found of anyone actually confusing the two in practice.
6. **Two documents with near-identical stated purposes exist at different locations with different formats.** `docs/field-notes.md` ("captures real-world observations made during customer engagements... may later improve NetworkMapper's intelligence") and `docs/knowledge/FIELD-OBSERVATIONS.md` ("recorded field observations using NetworkMapper's canonical observation format") describe substantially the same activity. Neither document states a relationship to the other, cross-references the other, or explains whether `field-notes.md` is superseded, a lighter-weight staging area, or a parallel, still-live channel. `classification-rules.md` is a cleaner, partially-resolved instance of the same underlying pattern — it explicitly documents its own supersession in a header notice — but even there, no ADR, ARCH, or DOC artifact formally records the decision to supersede it, and it has not been removed or archived (Section 5).
7. **`docs/ARCHITECTURE.md`'s relationship to `docs/architecture/overview.md` is asserted but not explained.** `docs/architecture/README.md` cross-references `docs/ARCHITECTURE.md` as providing "an existing high-level architecture narrative," but does not state whether it is a summary of `overview.md`, a predecessor to it, or an independently-maintained document covering different ground. This investigation did not read either document in full and does not resolve which is the case.
8. **The "referenced but never persisted" pattern recurs across at least five prefix families, not just `KNOW` (added per Findings F8/F9).** Section 3's `KNOW` row already names `KNOW-001`/`KNOW-002` as referenced-but-unpersisted. Independent re-verification during the correction pass found the same pattern is both larger and more widespread than that one instance:
   - The entire `FEAT-001`/`FEAT-002` sprint arc — `FEAT-001` (Phase A/B), `FEAT-001C`, `FEAT-002A`, `FEAT-002B` — is referenced repeatedly by `ARCH-001A` and directly by `ADR-008`'s own Context section (`FEAT-001 Phase A`), but no `docs/reports/FEAT-001*` or `FEAT-002*` file exists anywhere in the repository. Persisted `FEAT-*` reports begin only at `FEAT-003A`.
   - `TEST-002` is likewise named directly by `ARCH-001A` as the implementation counterpart to `TEST-001`, but no `docs/reports/TEST-002` file exists; the persisted `TEST-*` series jumps from `TEST-001` to `TEST-003`.
   - `RULE-001` and `BENCH-001` are absent, with no persisted file and no reference to either found anywhere in the documents this investigation read; the persisted series begin at `RULE-002` and `BENCH-002` respectively, with no stated explanation for the missing first entry in either case.

   `ARCH-001A` line 68's explanation (item 2, above) accounts directly for the `FEAT-001`/`FEAT-002`/`TEST-002` instances, all of which are implementation sprints predating the mandatory-Implementation-Report policy `ARCH-001A` itself recommended and `ARCH-001B` then adopted. **Corrected during formal verification:** `RULE-002`–`004` were checked directly and are themselves Implementation Reports (`Implementation: Completed`, `Production Code Modified: Yes`), so `RULE-001`'s absence plausibly extends this same explanation rather than sitting outside it. `BENCH-002`/`003`, by contrast, verified as investigation-style reports (`Implementation: Not Started`) — the category `ARCH-001A` describes as reliably persisted — so `ARCH-001A`'s explanation does not obviously cover `BENCH-001`. That narrower gap is named, not resolved — see Section 10, item 7.

---

## 10. Unresolved Questions

Named rather than answered, per the sprint's instructions, and distinct
from Section 9's inconsistencies (which are gaps in what's documented;
these are genuine open questions this investigation could not settle from
existing evidence alone):

1. **Should `BENCH-`, `OBS-`, `REPORT-`, `RULE-`, and `STAB-` be added to the Sprint Prefix Taxonomy table, folded into an existing prefix, or left as an acknowledged gap?** This investigation did not find evidence favoring one answer over another — each has multiple real instances, but none was designed against a taxonomy decision the way `DISC-`/`ARCH-`/`FEAT-` apparently were.
2. **Is the `DOC-001`/`DOC-001A` collision (Section 9, item 3) a naming defect that should be corrected going forward (e.g., reserving a different prefix for governance documents), or an acceptable one-time coincidence not worth disturbing three already-adopted-or-near-adopted filenames over?** DOC-001A's own Section 2 warns that "a governing document cannot authorize its own expansion" — by the same logic, this document should not decide its own naming convention unilaterally either.
3. **Should `docs/development/` be formally registered as a fifth documentation location in `docs/process/engineering-handbook.md`'s "Where Process Documentation Lives" list, or should governance documents be relocated into an existing, already-registered location?** Both directions have real costs: registering a new location for three files is a small taxonomy addition; relocating DOC-001A/DOC-001B after they were written specifically to *not* live in `docs/reports/` (a directory whose own README states reports "are not normative architecture documentation") would contradict the reason `docs/development/` was apparently chosen in the first place, though no document states that reason explicitly — it is this investigation's inference, not a recorded decision.
4. **What is the actual relationship between `docs/field-notes.md` and `docs/knowledge/FIELD-OBSERVATIONS.md`?** Whether `field-notes.md` should be formally superseded, merged, or is intentionally kept as a lighter-weight or different-audience channel is not answered by any document this investigation read.
5. **What is the actual relationship between `docs/ARCHITECTURE.md` and `docs/architecture/overview.md`?** Not resolved — see Section 9, item 7.
6. **Does the `ROADMAP.md`/`docs/architecture/` staleness this investigation confirmed for the ARP/LLDP/Bridge-FDB lineage (Section 8) warrant its own follow-up sprint?** (Reworded per F17 — the original phrasing named `DOC-001-Sprint-Catalog-Cleanup.md` as a precedent in a way that edged toward recommending a specific remedy shape rather than only naming the question.) This investigation surfaces the gap; deciding whether, when, and how to close it is exactly the kind of decision `ENGINEERING.md`'s AI-Assisted Development section reserves for explicit sprint approval, not something a documentation-taxonomy investigation should settle by itself.
7. **Why is `BENCH-001` absent, with no reference to it found anywhere in the documents this investigation read (added per F9; narrowed during formal verification — see below)?** Unlike `FEAT-001`/`FEAT-002`/`TEST-002` (Section 9, item 8), `ARCH-001A`'s "implementation sprints were chat-only" explanation does not obviously apply to `BENCH-001` — `BENCH-002`/`003` were checked directly and both read `Implementation: Not Started` / `Production Code Modified: No`, i.e. genuinely investigation-style, the category `ARCH-001A` describes as reliably persisted. Whether a `BENCH-001` ever existed and was lost, was renumbered, or never existed at all is not answered by any evidence this investigation gathered. **Corrected during formal verification:** an earlier draft of this item treated `RULE-001`'s absence as equally unexplained, on the claim that `RULE-002`–`004` "read as investigation-style reports" the same way `BENCH-002`/`003` do. That claim was checked directly against all three files' status blocks and found wrong: `RULE-002`, `RULE-003`, and `RULE-004` all read `Implementation: Completed` / `Production Code Modified: Yes` — they are Implementation Reports, not investigation-style reports. Since `ARCH-001A`'s own explanation (item 2, above, and Section 9 item 2) is specifically about implementation sprints not reliably producing persisted output, `RULE-001`'s absence plausibly extends that same, already-documented pattern (Section 9, item 8) rather than sitting outside it the way `BENCH-001`'s does.

---

## 11. Summary

NetworkMapper's engineering documentation is not one taxonomy but several
adjacent ones that grew for different reasons at different times: a
product-architecture chain (ADR → ARCH → PLAN → FEAT → VERIFY, per
DOC-001B Section 3–4), a much wider `docs/reports/` prefix family with
eleven distinct prefixes in active use (corrected per F15 — not merely "at
least" eleven; only six of which are registered in
`docs/process/engineering-handbook.md`'s taxonomy table), a living-document
set (`docs/architecture/`, `docs/knowledge/`, `docs/process/`, `ROADMAP.md`)
that describes current, approved state, a research document (`docs/LAB.md`)
deliberately upstream of that whole chain, a small, newly-created
governance-document family (`docs/development/`) that is itself not yet
registered anywhere in the taxonomy it exists to describe, and — found
during the correction pass, per F12 — a small set of tracked but
undocumented ad hoc snapshot files at the repository root.

Every artifact type found has a demonstrable purpose grounded in its own
stated rules or its observed use. What this investigation adds is not a new
type or a restructuring — none was found to be required by the evidence —
but a single place naming eight concrete taxonomy inconsistencies (Section
9) and seven genuinely unresolved questions (Section 10), several of which
sharpen gaps DOC-001A and DOC-001B already named in the abstract into
specific, citable instances: the `DOC-001`/`DOC-001A` collision, the five
unregistered report prefixes, `docs/development/`'s own unregistered
status, the broader "referenced but never persisted" pattern spanning
`FEAT-001`/`002`, `TEST-002`, `RULE-001`, and `BENCH-001` (Section 9, item
8), and — independently confirmed here rather than merely inferred —
`ROADMAP.md`'s current staleness relative to the completed ARP/LLDP/
Bridge-FDB lineage.

### Resolution status of the adversarial review's findings

F1 (wrong "Section 6" cross-reference) is resolved by correcting it to
Section 8, in Section 3. F2 (the lightweight `DOC-001` incorrectly grouped
with PLAN/DOC-governance under the approval-gated pattern) is resolved in
Section 5 by narrowing item 2 to PLAN and DOC (governance) only and noting
`DOC-001` belongs under item 1's report-freeze pattern instead. F3 (duplicate
"DOC (governance)"/"Governance document" rows) is resolved by merging the
two into the single "DOC (governance)" row in Section 3. F4 (PLAN's
expected-growth classification in tension with its own ARCH-analog framing)
is resolved by naming the tension explicitly in Section 6 rather than
asserting either reading. F5 (`ARCH-024` claimed as "sampled" beyond the
investigation's disclosed reading) is resolved in Section 8 by distinguishing
what was directly read from what was independently checked during the
correction pass. F6 (overstated citation-mechanism uniformity) is resolved
in Section 7 by noting `FEAT-012A`'s prose citation differs from
`FEAT-012B`'s structured trailer fields. F7 (PLAN/VERIFY's gap conflated
with BENCH/OBS/REPORT/RULE/STAB's gap) is resolved in Section 9, item 1, by
distinguishing the two gap types. F8 and F9 (the `KNOW-001`/`002` pattern
understating a larger, better-evidenced pattern spanning `FEAT-001`/`002`,
`TEST-002`, `RULE-001`, and `BENCH-001`) are resolved together by
strengthening Section 9 item 2 with a direct `ARCH-001A` citation and adding
a new Section 9 item 8 documenting the full pattern; the still-unexplained
`RULE-001`/`BENCH-001` absence is additionally named as a new unresolved
question (Section 10, item 7). F10 ("deliberately thin" mischaracterization
of `ENGINEERING.md`/`docs/AI-DEVELOPMENT-GUIDE.md`) is resolved in Section 3
with the actual line counts. F11 (unqualified "Normative" classification not
acknowledging Section 8's own staleness findings) is resolved by adding a
caveat bullet to Section 4. F12 (the missing `review.diff`/`review.patch`/
`test_results.txt` artifact type) is resolved by adding a new row to
Section 3. F13 and F14 (the FEAT-investigation example range and
naming-pattern description) are resolved together by correcting the example
range and noting `FEAT-004`'s exception in Section 3. F15 ("at least eleven"
imprecision) is resolved above by stating the exact count. F16
(`vendors/*.md` overstating Knowledge Framework population) is resolved
with a clarifying note in Section 3. F17 (Section 10 item 6's borderline
recommendation) is resolved by removing the implied-precedent phrasing.

### Resolution status of the formal verification audit's findings

A subsequent formal verification pass, run against the state above, found
three further issues, none reopening F1–F17: Section 8's `DEV-002`
sentence read as though `DEV-002` were a resolved historical example
when `ROADMAP.md` itself (line 135; lines 325–327) shows it is still an
open, unfixed instance of the same staleness (Finding 1); Section 10 item
7 incorrectly claimed `RULE-002`–`004` "read as investigation-style
reports" when their status blocks show they are Implementation Reports,
undermining the item's reasoning for `RULE-001` specifically while leaving
it intact for `BENCH-001` (Finding 2); and Section 5 item 1's bold label
still said "ADR and ARCH reports" after its own body had already been
broadened, during the first correction pass, to cover every
`docs/reports/*` type (Finding 3). All three are resolved in place, at the
locations named in each finding, including the one direct downstream
consequence Finding 2's correction required — Section 9 item 8's closing
paragraph, which previously treated `RULE-001` and `BENCH-001` as equally
unexplained and would otherwise have contradicted the narrowed Section 10
item 7.

This document is a corrected draft, produced through one investigation,
one adversarial review, one formal verification audit, and two correction
passes, and does not carry any authority until it is re-verified against
this latest state and explicitly approved — at which point it would itself
become one of the documents `docs/development/` holds alongside DOC-001A
and DOC-001B.
