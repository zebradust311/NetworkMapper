# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — this investigation concerns engineering *process* (how humans and AI collaborate, what documents get updated when), not NetworkMapper's product architecture. Every existing ADR (001–008) records a decision about the running system (discovery phasing, classification determinism, evidence structure, benchmarking, developer tooling). Process guidance already has its own, correctly-scoped home in `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md`; introducing an ADR for it would blur a distinction the repository already draws correctly (see `docs/reports/README.md`'s Guiding Principle).

Recommended Next Sprint:
ARCH-001B – Engineering Workflow Documentation

---

# Executive Summary

NetworkMapper's engineering workflow works, and this investigation found real evidence of that: sprints in this series repeatedly followed a de facto Investigation → Architecture Decision → Implementation → Validation → Human Approval → (Commit) sequence, correctly stopped and asked when a sprint's own instructions contradicted themselves (FEAT-002B) or rested on a premise that didn't exist in the repository (KNOW-001's UDR example), and produced increasingly disciplined, evidence-grounded artifacts (`docs/knowledge/`, `docs/reports/`, ADR-008).

But the workflow that actually happened is only partially the workflow that's *written down*. Three documents currently claim to define it — `ENGINEERING.md`, `docs/AI-DEVELOPMENT-GUIDE.md`, and (implicitly) `docs/reports/README.md` — and none of them has been updated to reflect capabilities the project now depends on: `docs/knowledge/` doesn't appear in `AI-DEVELOPMENT-GUIDE.md`'s Documentation Checklist at all; `python -m devtools validate --all` doesn't exist anywhere in either document's validation guidance, which still describes plain `validate` as sufficient; and `docs/reports/` — now containing a real investigation report — isn't mentioned in either document's list of what architecture changes should update. `ROADMAP.md`'s "Current Priority" section has pointed at a sprint (`DEV-002`) that was actually completed years of sprint-work ago, unnoticed and uncorrected through eleven subsequent sprints in this series alone.

The recommendation is not to invent a new process — it's to formalize, cross-reference, and de-duplicate the one that's already demonstrably working, and to close the specific, evidenced staleness gaps found below.

**Architecture review outcome:** the investigation's original recommendation — patching `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` in place — has been refined. The approved direction is to promote a canonical Engineering Handbook under `docs/process/`, with `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` becoming concise entry points that reference it rather than each independently defining the workflow. This report has been revised throughout to reflect that decision, along with newly approved Engineering Principles, Role Definitions, and Mandatory Stop Conditions sections, and a revised (now mandatory) Implementation Report standard.

---

# Current Engineering Workflow

Development in this repository currently follows a pattern visible in git history and in this session's own sprint sequence, but that pattern is described in three overlapping places rather than one canonical one:

- **`ENGINEERING.md`** defines Sprint Workflow (Planning → Implementation → Focused tests → Focused regression → Human review → Commit → Push), a separate Validation Workflow, an AI Execution Policy, Developer Platform guidance, and Canonical Developer Commands.
- **`docs/AI-DEVELOPMENT-GUIDE.md`** independently defines its own Sprint Workflow diagram (Plan → Prompt → Implementation → Focused Tests → Focused Regression → Human Review → Commit → Push — nearly but not exactly the same sequence and wording as `ENGINEERING.md`'s), its own AI Prompt Guidelines, Execution Policy, Review Process, Validation Rules, Safe/Review/Never-Approve command lists, and a Documentation Checklist.
- **`docs/reports/README.md`** defines a third, narrower workflow specifically for investigation reports (naming convention, status block, lifecycle rules).

In practice, across this series of sprints, the lived workflow has been:

1. A sprint arrives with an ID and prefix (`KNOW-`, `ARCH-`, `FEAT-`, `TEST-`, and, in git history, `DEV-`, `DOC-`, `DOCS-`, `INTEL-`, `CLASS-`, `ACC-`, `EVID-`, `DISC-`) and an informal but consistent shape: Objective, Tasks, Constraints, Validation, Deliverables.
2. Required reading is checked first (`ENGINEERING.md`, `ROADMAP.md`, `docs/ADR.md`, `docs/architecture/`, and — for investigation sprints — prior reports).
3. A duplicate-work check runs before anything else (per `ENGINEERING.md`'s AI Execution Policy) — this caught real discrepancies twice in this series: the DEV-002 checkbox never being marked complete despite the work already existing, and the UDR field-observation example in KNOW-001 not actually existing anywhere in the repository.
4. Investigation-only sprints produce either a chat report (FEAT-001 Phase A/B, FEAT-002A) or, once `docs/reports/README.md` existed, a persisted Markdown file (TEST-001, and now this report).
5. Architecture-only sprints produce an ADR (ARCH-001 → ADR-008) with minimal, targeted cross-references — not a rewrite of surrounding documents.
6. Implementation sprints touch only what's in scope, add or update tests and (where relevant) benchmark fixtures, and run validation.
7. Validation results, a `git diff`, and a concise summary are reported back; nothing is committed by the assistant — commits happen afterward, outside the assistant's turn (visible in git log: every sprint in this series has a corresponding commit, made after the assistant stopped and reported).

This is a real, working lifecycle. It just isn't written down as one coherent document anywhere.

---

# Workflow Assessment

## Strengths

- **The duplicate-work gate is real and has already paid for itself twice** in this series alone (the DEV-002 ROADMAP discrepancy; the fabricated-premise UDR example). This is the single most valuable process control observed.
- **Investigation-before-implementation is consistently honored.** FEAT-001 (Phase A → Phase B) and TEST-001 both produced grounded findings before any code changed, and both were referenced correctly by the implementation sprints that followed (FEAT-001C, TEST-002).
- **Constraints are respected precisely, not loosely.** FEAT-002B, TEST-002, and the presentation-only follow-up all correctly distinguished "changing behavior" from "changing presentation," including catching a subtle recursive self-inclusion bug in a test that would have gone unnoticed without exact attention to what "the full test suite" actually includes.
- **The assistant escalates instead of guessing when a sprint's premise is broken** — the FEAT-002B contradiction (implementation tasks vs. a report-only Deliverables block) was surfaced and clarified rather than silently resolved one way.
- **Evidence-driven investigation is genuinely evidence-driven.** TEST-001's "intentional vs. technical debt" conclusion was backed by git-blame chronology, not assumption; FEAT-001 Phase B's vendor-OUI caveat came from checking actual benchmark data, not a general assumption about VMware.

## Weaknesses

- **No single canonical workflow document.** `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` each define a Sprint Workflow independently, with different step names and different diagrams. Neither references the other.
- **Meta-documentation lags the workflow it describes.** Three concrete, dated examples found in this investigation:
  - `ROADMAP.md`'s "Current Priority → Next Sprint" still names `DEV-002 — Shared Evidence Helper Library`, work that was already implemented before this session's very first sprint (confirmed via git-log chronology in a prior investigation). It has not been corrected across eleven subsequent sprints.
  - `docs/AI-DEVELOPMENT-GUIDE.md`'s Documentation Checklist and Validation Rules make no mention of `docs/knowledge/`, `docs/reports/`, or `python -m devtools validate --all` — all three now load-bearing parts of the actual workflow.
  - `docs/architecture/README.md`'s "Planned Documentation" list (`discovery.md`, `benchmarking.md`, `developer-platform.md`) is unchanged even though discovery (VMware port expansion), benchmarking (`devtools benchmark`/`compare`), and the developer platform (`devtools validate --all`) have all seen substantive work since that list was written.
- **Overlapping, un-reconciled knowledge sources.** `docs/field-notes.md` and `docs/knowledge/FIELD-OBSERVATIONS.md` cover materially the same ground (hypervisor and Ubiquiti naming conventions) without cross-referencing each other, despite `docs/reports/README.md`'s own stated principle that these document types "should not duplicate content."
- **No persisted artifact for implementation sprints.** Investigation sprints get a permanent file under `docs/reports/`; architecture sprints get an ADR. Implementation sprints (FEAT-001C, FEAT-002B, TEST-002) produce only a chat-turn summary and a `git diff` — valuable at the time, but nothing durable survives in the repository connecting a commit back to the reasoning that produced it, beyond the commit message itself.
- **No sprint-ID taxonomy.** At least eleven distinct prefixes appear in git history (`DISC-`, `CLASS-`, `EVID-`, `INTEL-`, `ACC-`, `DOCS-`/`DOC-`, `DEV-`, `KNOW-`, `ARCH-`, `FEAT-`, `TEST-`) with no registry explaining what each means or when a new one should be introduced versus reusing an existing one.

## Repetitive Manual Work

- **Benchmark JSON syntax validation** was performed by hand (`python -c "import json; json.load(...)"`) in every sprint that touched a benchmark fixture, with no devtools command doing this automatically.
- **Running all three benchmark datasets individually** was manual, repeated overhead in every implementation sprint before TEST-002 introduced `validate --all` — this specific pain point is a good example of the workflow correctly self-improving once it was actually investigated.
- **Markdown link verification** (checking that every relative link in a new/changed doc resolves) was re-implemented as an ad hoc shell loop at least three separate times (KNOW-001, KNOW-002, ARCH-001), never becoming a reusable script or devtools command.
- **"Is this already implemented?" checks** are performed freshly each sprint via improvised `git log`/`grep` combinations — valuable and correctly done every time, but with no shared method or tooling, so its thoroughness depends on what the assistant happens to think to check.
- **Test-coverage archaeology** (which test file actually exercises which subsystem) had to be reconstructed from scratch during TEST-001 by cross-referencing every test file against every rule/module by hand — this is exactly the kind of map that, once built, tends to go stale the same way `STANDARD_REGRESSION_TESTS` did, unless it's kept as a living artifact rather than a one-time investigation output.

---

# Standard Sprint Lifecycle

The requested lifecycle — Investigation → Architecture Review → Implementation → Validation → Human Review → Commit — is not a new invention; it is what this series of sprints already did in its most disciplined runs (TEST-001 → TEST-002; FEAT-001 Phase A/B → ARCH-001 → FEAT-001C). Recommended as the permanent, canonical version:

```
Investigation
    │  (docs/reports/<ID>-<Description>.md — only when genuinely warranted;
    │   trivial sprints may skip straight to Implementation)
    ▼
Architecture Review
    │  (only when the investigation surfaces a product-architecture question;
    │   produces an ADR if a decision is made, or a note that none was needed)
    ▼
Implementation
    │  (scoped strictly to the approved sprint; no unrelated cleanup)
    ▼
Validation
    │  (python -m devtools validate, or validate --all when the change
    │   touches anything outside classification — see Validation Workflow below)
    ▼
Human Review
    │  (git diff + concise summary; approval requested explicitly)
    ▼
Commit
```

Two refinements over the current, split description:

1. **Not every sprint needs every stage.** A one-line documentation fix does not need a full Investigation report. The lifecycle should name its stages clearly enough that a sprint author can explicitly say "skip Architecture Review — no product-architecture question here" (as ARCH-001A itself does, above) rather than the stage being silently absent with no record that it was considered.
2. **"Commit" and "Push" should be separated from the assistant's default responsibility.** Every sprint in this series stopped before committing, on explicit instruction. The lifecycle diagram should reflect that Commit is a distinct, human-triggered step rather than implying the assistant routinely reaches it (both `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` currently list "Commit → Push" as if they were AI-executed steps, which is not how any sprint in this series actually worked).

Per the architecture review, this lifecycle becomes the canonical version documented once, in `docs/process/sprint-lifecycle.md`, rather than described independently in `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md`.

---

# Engineering Principles

The architecture review approved a formal Engineering Principles section within the Handbook. Each principle below is grounded in something this investigation already observed happening in this series, not stated as aspiration:

- **Investigate before implementing.** FEAT-001 (Phase A → Phase B) and TEST-001 both produced grounded findings before any code changed, and both were referenced correctly by the implementation sprints that followed.
- **Evidence over assumptions.** TEST-001's "intentional vs. technical debt" conclusion was backed by git-blame chronology, not assumption; FEAT-001 Phase B's vendor-OUI caveat came from checking actual benchmark data rather than a general assumption about VMware.
- **Keep changes narrowly scoped.** Every implementation sprint in this series (FEAT-001C, FEAT-002B, TEST-002) touched only what was in scope; ARCH-001 deliberately limited its documentation cross-references rather than rewriting surrounding architecture docs.
- **Preserve backwards compatibility whenever practical.** TEST-002 preserved `validate`'s exact existing behavior while adding `validate --all`; the presentation-only follow-up preserved validation logic, discovery, and exit codes while changing only output.
- **Validate before review.** Every implementation sprint ran validation and reported results before requesting approval.
- **Human approval before commit.** No sprint in this series was committed by the assistant; every commit visible in git log happened after the assistant stopped and reported.
- **Benchmark classifier changes.** FEAT-001C and FEAT-002B both added benchmark coverage alongside their classifier/discovery changes, not just unit tests.
- **Stop and ask rather than guess.** FEAT-002B's self-contradictory Deliverables block and KNOW-001's fabricated UDR premise were both surfaced for clarification rather than resolved by guessing.

Per the architecture review, this becomes `docs/process/engineering-principles.md`.

---

# Role Definitions

The architecture review also approved formal role definitions, distinguishing responsibilities that have so far been implicit in how this series actually ran:

- **Human Architect** — owns product-architecture and process decisions: approves ADRs, approves sprints, and decides when to override or refine an investigation's recommendation (as this architecture review itself does to the original ARCH-001A). Holds final authority over scope and direction.
- **AI Investigator** — performs investigation-only sprints: reads required documents, gathers evidence directly from the repository (git history, code, tests, benchmarks), and reports findings without modifying anything. Responsible for surfacing discrepancies rather than resolving them unilaterally.
- **AI Implementer** — performs implementation sprints within an approved, scoped sprint: writes code, tests, and benchmark fixtures; runs validation; reports results and a `git diff`. Does not commit and does not expand scope beyond what was approved.
- **AI Reviewer** — validates a completed implementation before it's reported as ready for human approval: confirms scope stayed within bounds, confirms validation actually covered the right areas (e.g., choosing `validate --all` over `validate` when a change touches more than classification), and confirms no unrelated files changed.

Across this session, one assistant played all three AI roles in sequence within most sprints (investigate, then implement, then validate its own work) rather than these being separate actors. Worth naming explicitly so a future sprint can deliberately choose to split them — e.g., a dedicated review-only pass, which is effectively what this architecture-review turn already is.

Per the architecture review, this becomes `docs/process/role-definitions.md`.

---

# Mandatory Stop Conditions

The architecture review approved a dedicated, mandatory set of stop conditions. Several of these already occurred, correctly, in this series — they are the direct evidence for codifying them rather than leaving them as implicit judgment calls:

- **Requirements contradict themselves.** Occurred in FEAT-002B: the sprint's Tasks/Constraints/Validation described an implementation, while its Deliverables described an investigation-only report whose status block declared no code was modified. Work stopped and the contradiction was surfaced before proceeding.
- **Repository contradicts the prompt.** Occurred in KNOW-001: the sprint asked for a field-observation example (a Ubiquiti UDR operational-role discussion) that did not exist anywhere in the repository or git history. Work stopped rather than fabricating it.
- **Existing implementation already satisfies the sprint.** Occurred when DEV-002 was investigated: `evidence_helpers.py` and its consuming rules already existed, despite `ROADMAP.md` listing DEV-002 as an unstarted "Next Sprint." Work stopped, the discrepancy was reported, and no duplicate implementation was produced.
- **Scope expands beyond the approved sprint.** Implied throughout this series — e.g., FEAT-001 Phase B explicitly separated what belonged in the immediate implementation sprint from what should defer to a future one (OS detection, SNMP), rather than implementing everything an investigation surfaced.
- **An ADR becomes unexpectedly necessary.** ARCH-001 was scoped explicitly to produce an ADR once a genuine architectural principle was discovered (ADR-008); this report's own original conclusion — that no ADR was needed for a process-only recommendation — shows the same judgment applied in the other direction.
- **Validation contradicts implementation.** Implicit in TEST-002's rigor: a synthetic test that caused unbounded recursive self-inclusion (a test discovering and re-running itself) surfaced as a validation problem and was fixed before being reported as passing, rather than being reported as a pass despite the anomaly.
- **An engineering principle would be violated.** Implicit throughout — e.g., "no schema changes" in FEAT-002A/FEAT-002B repeatedly ruled out otherwise-reasonable evidence-collection ideas (OS detection, service banners) specifically because they would have required a `Device` schema change.

Each of these should stop work immediately and require explicit human direction before continuing — not a judgment call to reason around.

Per the architecture review, this becomes `docs/process/stop-conditions.md`.

---

# Report Standards

`docs/reports/README.md` already defines a good, working standard for **Investigation reports**: naming convention, status block, and a default section list, with sprint-specific section lists allowed to override it (exactly as TEST-001 and this report both do). Recommended: keep this as-is; it works.

Two report types are missing a defined standard:

**Implementation reports.** Revised by the architecture review: rather than the optional, sprint-discretion format originally recommended here, Implementation Reports are now **mandatory for every implementation sprint** — but deliberately kept lightweight, so the mandate doesn't reintroduce the overhead this investigation otherwise warns against (see Risks below):
```
# Status
(same block as investigation reports, with Implementation: Completed)

Summary
Files Changed
Validation Performed
Known Issues
Next Recommended Sprint
```
This is intentionally shorter than the format originally proposed here (no separate Executive Summary or Risks Accepted section) — a mandatory artifact only stays lightweight if it's actually small. "Known Issues" replaces "Risks Accepted" to also capture pre-existing, out-of-scope problems surfaced incidentally (e.g., the `test_csv_exporter.py` failure found during TEST-002), not just risks the sprint itself introduced.

**Architecture Reviews.** `ENGINEERING.md` already specifies what one should contain (Executive Summary, Completed Objectives, Architecture Assessment, Testing Assessment, Documentation Assessment, Technical Debt, Risks, Recommendations, Overall Grade, Approval Status) but doesn't say where it lives or when one is triggered versus a plain ADR. Recommend: Architecture Reviews are periodic (milestone-based, not per-sprint) and live under `docs/reports/` using the same naming convention (`ARCH-REVIEW-<milestone>.md` or similar), distinct from the ADRs they may reference.

---

# Prompt Template Strategy

**Recommendation: yes, prompt templates should live in the repository — but as one canonical file, not several.**

`docs/AI-DEVELOPMENT-GUIDE.md` already contains an "AI Prompt Guidelines" section with a Bad/Good example and a required-fields list (Objective, Requirements, Constraints, Validation, Execution Policy). This is a prompt template in substance, but not in a form anyone can copy directly — and it doesn't match the shape actually used throughout this session (Objective / Tasks / Constraints / Validation / Deliverables — "Requirements" vs. "Tasks," "Execution Policy" folded into `ENGINEERING.md`'s AI Execution Policy rather than repeated per-prompt). Recommend consolidating into a single, literal, copy-pasteable template per sprint *type* (Investigation, Architecture, Implementation), since this session's actual prompts already implicitly varied by type.

**Revised by the architecture review:** rather than a standalone `docs/templates/` directory, these templates now belong inside the Handbook, as `docs/process/prompt-templates.md`, cross-referenced from `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` rather than duplicated into either.

---

# Validation Workflow

Current, correct usage pattern (established by TEST-001/TEST-002, not yet reflected in `ENGINEERING.md`'s or `docs/AI-DEVELOPMENT-GUIDE.md`'s validation guidance, both of which still describe only plain `validate`):

- **`python -m devtools validate`** — fast, classifier-only regression. Use while iterating on classification rules, the classifier, or RuleResult evidence. Does not exercise discovery, exporters, the CLI, benchmark infrastructure, the workbench, comparison, or reporting.
- **`python -m devtools validate --all`** — comprehensive: every discovered test module plus every discovered benchmark dataset. Use whenever a sprint touches anything outside the classification layer, and always before considering a sprint complete, regardless of what it touched.
- **`python -m devtools benchmark [dataset]`** — use to inspect one dataset's classification accuracy in detail (per-device-type breakdown), or after a classifier change to see specific impact. `validate --all` runs every dataset but only reports pass/fail per dataset, not the full accuracy report.
- **`python -m devtools diagnostics`** — quick environment sanity check (imports, project structure, one benchmark dataset). Not a substitute for `validate --all`.

Per the architecture review, this becomes `docs/process/validation-workflow.md`.

---

# Knowledge Workflow

Synthesizing `docs/knowledge/KNOWLEDGE-LIFECYCLE.md`'s stages against how this session actually used them:

- **ADRs** — create when a sprint is explicitly architecture-scoped and a genuine product-architecture decision is being made (ARCH-001 → ADR-008). Not for process/workflow decisions (see this report's own status block) and not for every design choice within an implementation sprint (e.g., TEST-002's fast/full validation split was reasoned through in TEST-001 and implemented without a new ADR, since it extends an already-accepted decision, ADR-007, rather than introducing a new one).
- **Knowledge entries** (`docs/knowledge/FIELD-OBSERVATIONS.md`, `docs/knowledge/vendors/`) — create a Field Observation when a technician or investigation surfaces a genuinely new, specific operational fact — and only promote it to Vendor Knowledge once multiple independent observations corroborate it (per `KNOWLEDGE-LIFECYCLE.md`'s own Observation → Knowledge distinction). Do not fabricate an observation to fit a requested example — this investigation's own predecessor sprint (KNOW-001) correctly stopped and asked rather than inventing the requested UDR example from nothing.
- **Benchmark additions** — create alongside any classifier or discovery change that alters what evidence is available or how it's matched, so the change is measured, not just unit-tested (every implementation sprint in this series did this correctly: FEAT-001C, FEAT-002B).
- **Investigation reports** — create when a sprint is explicitly investigation-only and produces findings substantial enough to be worth preserving for a later sprint to reference (as TEST-001 was referenced by TEST-002, and as this report will presumably be referenced by ARCH-001B). Trivial or purely exploratory investigation does not need a permanent file — the chat-turn report used for FEAT-001 Phase A/B and FEAT-002A was proportionate to those sprints.

---

# Repository Additions

**Revised by the architecture review.** The original recommendation here was to patch `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` in place. The approved direction instead promotes a canonical Engineering Handbook, giving `docs/` this overall shape:

```
docs/
    architecture/
    knowledge/
    process/
    reports/
```

With `docs/process/` containing:

```
docs/process/
    engineering-handbook.md
    engineering-principles.md
    role-definitions.md
    stop-conditions.md
    validation-workflow.md
    prompt-templates.md
    sprint-lifecycle.md
```

`engineering-handbook.md` becomes the authoritative entry point tying the other six together; `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` become concise pointers into it rather than each independently defining Sprint Workflow, validation rules, and prompt guidance (closing the "no single canonical workflow document" weakness identified above).

Recommended for ARCH-001B (not implemented here):

1. Create `docs/process/` with the seven files above, populated from this report's Standard Sprint Lifecycle, Engineering Principles, Role Definitions, Mandatory Stop Conditions, Validation Workflow, and Prompt Template Strategy sections.
2. Reduce `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` to concise entry points referencing the handbook, removing their duplicated/divergent Sprint Workflow diagrams and validation guidance in favor of a single canonical version in `docs/process/sprint-lifecycle.md` and `docs/process/validation-workflow.md`.
3. Add the mandatory Implementation Report format to `docs/reports/README.md`, alongside the existing Investigation format.
4. Correct `ROADMAP.md`'s "Current Priority" section, and consider whether Human Review should explicitly include confirming ROADMAP reflects the sprint just completed, so it doesn't silently drift again.
5. Add a short sprint-ID taxonomy (a table of prefix → meaning → example) within `engineering-handbook.md` rather than as a separate file.
6. Note, but do not necessarily resolve in ARCH-001B: `docs/field-notes.md` and `docs/classification-rules.md` predate `docs/knowledge/` and `docs/architecture/classification.md` respectively and now materially overlap with them — worth a deliberate decision (migrate, cross-reference, or formally retire) rather than continued silent duplication.

---

# Risks

- **Formalization can slow the exact thing that's working.** This session's actual strength was judgment — stopping on a broken premise, recognizing when a constraint like "no schema changes" ruled out an otherwise-reasonable idea. A heavier, more prescriptive process risks converting judgment calls into checklist items that get followed mechanically even when they stop fitting the situation.
- **New meta-documents can go stale exactly like the old ones did.** A seven-file Handbook is a larger surface than the two-document patch originally proposed here — this investigation's central finding is that the repository has a demonstrated pattern of letting meta-documentation drift. Promoting the Handbook makes this risk larger, not smaller, unless keeping it current becomes part of the lifecycle itself (e.g., via Human Review, per Repository Additions above), not a one-time ARCH-001B effort.
- **Mandating Implementation Reports reintroduces overhead if the format isn't kept genuinely lightweight.** The architecture review accepted this tradeoff deliberately — mandatory, but deliberately smaller than this report's original optional proposal (no Executive Summary, no separate Risks section) — specifically to keep the mandate proportionate. If future sprints find the six-field format expanding in practice, that's a sign the mandate is being treated as a report requirement rather than a lightweight one, and worth revisiting.
- **The Handbook promotion is a larger migration than the original two-document patch.** ARCH-001B now creates seven new files and migrates two existing documents toward referencing them, rather than editing two documents in place. It should still avoid becoming a wholesale rewrite of `ENGINEERING.md` or `docs/AI-DEVELOPMENT-GUIDE.md`'s other content (Coding Standards, Architecture Policy, Product Vision, etc., in `ENGINEERING.md`; the Commit/Review checklists in `docs/AI-DEVELOPMENT-GUIDE.md`) — only the workflow-defining sections identified in this report move to the Handbook.

---

# Recommended Implementation Sprint

**ARCH-001B – Engineering Workflow Documentation**

**Revised by the architecture review:** ARCH-001B now creates the complete Engineering Handbook and migrates existing engineering documentation toward it, rather than only patching `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` in place.

Scope:
- Create `docs/process/` containing `engineering-handbook.md`, `engineering-principles.md`, `role-definitions.md`, `stop-conditions.md`, `validation-workflow.md`, `prompt-templates.md`, and `sprint-lifecycle.md`, populated from this report's corresponding sections.
- Reduce `ENGINEERING.md` and `docs/AI-DEVELOPMENT-GUIDE.md` to concise entry points that reference the Handbook, removing their independently-defined (and currently divergent) Sprint Workflow diagrams and validation guidance in favor of the single canonical versions in `docs/process/`.
- Add the mandatory Implementation Report format (Status / Summary / Files Changed / Validation Performed / Known Issues / Next Recommended Sprint) to `docs/reports/README.md`.
- Correct `ROADMAP.md`'s stale "Current Priority" entry.
- Add a short sprint-ID taxonomy table within `engineering-handbook.md`.

Explicitly out of scope for ARCH-001B: rewriting the non-workflow content of `ENGINEERING.md` or `docs/AI-DEVELOPMENT-GUIDE.md` (Coding Standards, Architecture Policy, Product Vision, Commit/Review checklists, etc.) — only workflow-defining sections move to the Handbook; resolving the `docs/field-notes.md`/`docs/knowledge/` overlap (flag it, don't fix it there); any devtools or production code change; any ADR.
