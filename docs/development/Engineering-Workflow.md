# Status

Draft — Corrected Pending Formal Verification

Investigation: Complete (DOC-001B)

Correction Pass: One pass applied, resolving Findings F1–F9 from the
DOC-001B adversarial review — see Section 12 for the resolution status of
each.

Governs: How engineering work moves through NetworkMapper — from
investigation to a committed, pushed deliverable — and what each
artifact type (ADR, ARCH, PLAN, FEAT, VERIFY, DOC) means, when it's
created, when it becomes authoritative, and what freezes it.

Does Not Govern: Who may make which edits autonomously. That is
[DOC-001A (Change Authority Policy)](Change-Authority-Policy.md)'s
subject, referenced throughout below rather than restated.

Production Code Modified: No — this document is process/workflow only.

ADR Required: No, for the same reason DOC-001A's own status block gives
and ARCH-001A gave before it: this concerns engineering *process*, not a
product-architecture decision. Every existing ADR (001–013) records a
decision about the running system; this document records a decision
about how work gets produced, which already has a home in
`ENGINEERING.md`/`docs/process/` and now `docs/development/`.

This document has now been through one investigation, one adversarial
review, and one correction pass responding to it. It has **not** yet
undergone the formal verification pass that will precede its Freeze —
that is deliberately the next step, not this one. Until then, the
existing scattered evidence in `docs/process/*`, `docs/reports/README.md`,
`docs/ADR.md`, `ENGINEERING.md`, and `docs/AI-DEVELOPMENT-GUIDE.md`
remains authoritative for workflow questions, exactly as DOC-001A's own
equivalent documents remained authoritative for authority questions
until DOC-001A itself was adopted.

---

## 1. Purpose

Three things already define pieces of NetworkMapper's engineering
workflow, none completely: `docs/process/sprint-lifecycle.md` gives a
six-stage diagram (Investigation → Architecture Review → Implementation →
Validation → Human Review → Commit); `docs/reports/README.md` defines
what an Investigation Report and an Implementation Report are and how
they age; `docs/ADR.md` defines what an ADR is and how it's recorded. None
of the three describes the fuller shape that has actually emerged in this
project's most recent lineage — ADR-010 through ADR-013, ARCH-020 through
ARCH-024, and now a `PLAN-` artifact type and a `VERIFY` practice that
didn't exist when `sprint-lifecycle.md` was written, plus DOC-001A's own
freshly-lived cycle (Investigation → Adversarial Review → Correction →
Verification → Freeze) for a governance document specifically.

This document's purpose is to write down what that fuller shape actually
is — grounded in the ARCH-024 → PLAN-012B → FEAT-012B → VERIFY → Commit
lineage as one live example, and in DOC-001A's own production as a second,
independently-observed example of a related but not identical cycle — not
to prescribe a new one. Where the two examples disagree, or where the
proposed nine-stage lifecycle in the sprint prompt doesn't match either of
them, that disagreement is investigated and reported (Section 3), not
smoothed over. Nor is either example treated as describing this project's
full engineering history — Section 3 states explicitly how narrow that
evidentiary base actually is, and where it does and doesn't extend.

---

## 2. Engineering Principles

DOC-001A's own Guiding Principles govern *editing authority* — who may
act without asking, who must propose and wait, who must stop. This
document does not restate them. The principles below govern *workflow
shape* specifically, and are additive to DOC-001A's, not a parallel
version of them.

- **An artifact's authority comes from what created it, not from where it
  lives.** A PLAN is binding because an engineer approved it, not because
  it sits in `docs/plans/`. An ARCH report is historical because
  `docs/reports/README.md`'s own Guiding Principle says reports "do not
  supersede ADRs or other architecture documents" — not because of a
  naming convention. Section 4 is built on this distinction.
- **Traceability is a citation discipline, not a tool.** Every artifact
  in the ARCH-024 → PLAN-012B → FEAT-012B → VERIFY lineage cites the
  specific section of its predecessor it depends on — not just the
  document. This is demonstrated practice (Section 8), not yet an
  enforced one: nothing in this repository checks that a cited section
  number actually exists, or that a FEAT's code actually implements what
  its PLAN says. VERIFY currently does this checking manually, once, per
  sprint.
- **Freezing an artifact and freezing its *effect* are different
  events.** ARCH-024 froze as an investigation report once its status
  read "Investigation Complete" — but its recommendation didn't become
  operative for any actual work until the engineer separately chose to
  act on it (and, in this instance, chose a different next-sprint label
  than ARCH-024 itself recommended). Section 7 treats these as two
  distinct freeze events, not one.
- **A stage that produces a durable artifact tends to have its own
  internal micro-cycle — an emerging pattern in the most recent lineage,
  not yet a confirmed universal one (Section 3).** ARCH-024's own commit
  message *records* it being "adversarially reviewed... then verified
  across three full-document consistency passes" before that single
  commit landed — repository evidence that this happened, not a process
  this investigation itself watched happen. DOC-001A's own cycle was
  observed directly, turn by turn, in this session — stronger evidence
  than a commit message's self-description. Both are real evidence for a
  recurring pattern in this project's most recent work; neither, nor
  both together, establishes that the pattern held for the project's
  earlier history, which `ARCH-001A` documents as following a simpler
  shape (Section 3).
- **Do not manufacture uniformity repository evidence doesn't support.**
  Where the ARCH-024 lineage and the DOC-001A lineage genuinely differ —
  most importantly, the strength of evidence for a formally-invoked
  "Adversarial Review" stage in ARCH/PLAN work versus DOC work — this
  document says so (Section 9), rather than assuming one example
  generalizes to the other, or that a directly-observed cycle and a
  self-reported one carry equal weight.

---

## 3. Canonical Lifecycle

**The proposed nine-stage chain — Investigation → Adversarial Review →
Correction → Verification → Freeze → Implementation → Implementation
Audit → Commit → Push — is not rejected, but it is refined.** Applied
literally as one flat sequence, it doesn't match the evidence in two
specific ways:

**1. It conflates two things that are demonstrated separately: producing
an artifact, and consuming one to produce the next.** ARCH-024's own
commit message *records* an Investigation → Adversarial Review →
Correction → Verification shape having happened *inside the production
of a single ARCH document*, before that document was ever frozen — this
is repository evidence of the shape, not a process this investigation
directly watched happen (Section 9 keeps that distinction explicit
throughout). PLAN-012B shows a related but not identical shape, directly
observed: drafted, corrected once — resolving three separately identified
issues in that one pass — through direct engineer review, not a
separately-invoked adversarial pass (Section 9), then approved. DOC-001A shows the fullest version of the cycle, and the only
one observed turn-by-turn in this exact form: one adversarial review, one
formal verification audit, five correction passes in total. In every
case — regardless of how strongly each is evidenced — this multi-stage
micro-cycle is how *one artifact* gets produced and frozen; it is not, by
itself, the whole sprint. The outer shape is a *chain of frozen
artifacts*: ADR (standing constraint) → ARCH (frozen investigation) →
PLAN (frozen implementation authority) → FEAT (implementation, validated,
then frozen by commit) → VERIFY (audit, currently not itself a
frozen/persisted artifact — Section 11) → Commit → Push. Each link in that
outer chain may internally run its own copy of the inner micro-cycle.
Section 4 develops this two-layer picture further.

**2. "Implementation" and "Implementation Audit" are not stages every
artifact type goes through — they are specific to FEAT.** A PLAN document
is not "implemented" separately from being drafted and corrected — the
drafting *is* the deliverable. The same is true of an ARCH report and of
a DOC governance document: for all three, "Correction" and
"Implementation" would refer to the identical act of editing the same
file. Only FEAT has a genuine build step distinct from its authorizing
document (PLAN) — code is written that PLAN did not itself contain, and
that code is then separately validated and audited (VERIFY) against both
ARCH and PLAN. Applying "Implementation" and "Implementation Audit" as
mandatory stages for ARCH/PLAN/DOC as well would be inventing structure
this repository's evidence doesn't show.

### Refined model

```
   Per-artifact production cycle              Outer artifact chain
   (runs once per ARCH / PLAN / DOC)          (chains frozen artifacts)

   Investigation / Draft                       ADR (standing constraint)
          │                                           │
          ▼                                           ▼
   Review                                        ARCH (investigates
   (Adversarial Review, directly                    against ADRs;
    observed for DOC; recorded but                    recommends)
    not directly observed for ARCH;                    │
    direct engineer correction,                         ▼
    observed for PLAN — Section 9)             PLAN (translates an
          │                                       accepted ARCH into
          ▼                                         file-level commitments)
   Correction                                           │
          │                                             ▼
          ▼                                     FEAT (implements the
   Verification                                   PLAN; its own build +
          │                                       validate loop)
          ▼
   Freeze  ──────────────────────────────────────────►│
   (artifact becomes                                   ▼
    authoritative for                            VERIFY (audits FEAT
    whatever it authorizes)                        against ARCH + PLAN)
                                                         │
                                                         ▼
                                                   Commit  (human-triggered,
                                                         │  per DOC-001A §5)
                                                         ▼
                                                   Push    (same)
```

The left cycle is what "Investigation → Adversarial Review → Correction →
Verification → Freeze" actually describes — evidenced, at varying
strength, three times (ARCH-024 via commit-message record; PLAN-012B via
direct engineer correction, not adversarial review; DOC-001A via a fully
observed adversarial-review-and-verification cycle), each producing one
frozen document. The right chain is what "Implementation → Implementation
Audit → Commit → Push" actually describes — evidenced once, completely,
in the ARCH-024 → PLAN-012B → FEAT-012B → VERIFY → Commit → Push sequence
this session lived through. DOC-001A is on the left cycle only — a
governance document doesn't get "implemented" by a separate FEAT; once
frozen, it takes effect immediately as the thing it is.

### Evidentiary scope of this model

**This refined model describes an emerging, recently demonstrated
workflow pattern — not a confirmed universal description of
NetworkMapper's engineering history.** Its evidentiary base is narrow:
three artifact-production cycles (ARCH-024, PLAN-012B, DOC-001A) and one
complete outer chain (ARCH-024 → PLAN-012B → FEAT-012B → VERIFY → Commit
→ Push), all from the same recent period. `ARCH-001A` — this document's
own cited authority for the older sprint-lifecycle evidence — already
surveyed a much larger body of this project's history (FEAT-001 Phase
A/B, FEAT-002A/B, TEST-001/002, KNOW-001/002, DEV-002, and others), and
none of those sprints is described there as having gone through a PLAN
artifact or a separately-invoked adversarial-review stage at all. They
instead followed the simpler shape `docs/process/sprint-lifecycle.md`
still documents as canonical: Investigation → Architecture Review
(producing an ADR, or a note that none was needed) → Implementation →
Validation → Human Review → Commit. That simpler shape remains the one
documented in standing process artifacts today; the refined model above
describes what the most recent, most elaborate lineage in this project's
history has actually done, not a claim that all prior or future work
follows it. **The two are not in conflict** — the refined model can be
read as a *specialization* the PLAN/VERIFY-era work has added on top of
the older shape, for the specific kind of work (SNMP relationship
evidence, and now governance documents) that has recently needed it — not
a replacement for the older shape, and not yet shown to be the general
case going forward either.

### Alternatives considered

**Treating the nine stages as one flat, universal sequence applied to
every artifact type** (the literal reading of the sprint prompt) was
considered and rejected for the reasons above — it would require
inventing an "Implementation" stage for ARCH/PLAN/DOC that nothing in
this repository's history shows happening, and it would obscure the
genuinely useful observation that the same four-stage micro-cycle recurs
at the artifact level.

**Treating PRODUCT work (ADR/ARCH/PLAN/FEAT/VERIFY) and GOVERNANCE work
(DOC) as two entirely separate lifecycles with no shared vocabulary** was
also considered, since DOC-001A's own production never touched
PLAN/FEAT/VERIFY at all. Rejected because the two share the *identical*
inner micro-cycle (Investigation → Review → Correction → Verification →
Freeze) — DOC-001A is not a different kind of lifecycle, it is an
instance of the same per-artifact cycle that ARCH and PLAN also go
through, just one that happens not to feed into a FEAT/VERIFY step
afterward. One model with an optional right-hand extension, as diagrammed
above, fits both without inventing a second vocabulary.

---

## 4. Artifact Flow

| Artifact | Authorizes | Descriptive or Normative | Frozen how (Section 7) |
|---|---|---|---|
| **ADR** | Everything downstream, as a standing constraint — not a per-sprint step. ARCH/PLAN/FEAT must not contradict an Accepted ADR. | Normative. `docs/ADR.md`: "Only accepted architectural decisions are recorded here." | Permanent once Accepted (Section 7). |
| **ARCH** | A PLAN, once its recommendation is accepted by the engineer — but the acceptance is a separate, later event from the report's own freeze. | **Descriptive/historical, explicitly not normative.** `docs/reports/README.md`'s own Guiding Principle: reports "are historical engineering artifacts. They are not normative architecture documentation and do not supersede ADRs or other architecture documents." | Frozen at "Investigation Complete," editable only for factual/reference/formatting corrections (Section 7). |
| **PLAN** | A FEAT, once approved as the implementation authority. | Normative for the FEAT it authorizes, but only after approval — before that, it's a proposal with no more standing than an ARCH's recommendation. | Frozen at explicit approval, but *revisable in place* via the same approval process afterward (Section 7) — unlike ARCH. |
| **FEAT** | Nothing further downstream in the artifact sense — it is the terminal deliverable for its unit of work. | Normative the moment it's committed (the running system *is* what FEAT decided); descriptive of nothing beyond itself. | Frozen by `git commit` — an immutable history event, not an editable document (Section 7). |
| **VERIFY** | Nothing directly — it never modifies anything (Level 0 per DOC-001A). Its findings authorize *new*, separate corrective work, which may target the FEAT, the PLAN, or (in principle, though not yet observed) the ARCH. | Descriptive: a report on whether FEAT actually matches ARCH + PLAN. | Not currently frozen as a durable artifact at all — Section 11. |
| **DOC** | Future Claude behavior, once adopted — but only within its own subject (DOC-001A governs editing authority; this document, once adopted, governs workflow shape). Does not authorize any specific PLAN or FEAT. | Normative once adopted, for its own subject only. | Frozen at explicit adoption, revisable in place afterward like PLAN — Section 7. |

**Is this a directed workflow, or something else?** Neither term alone
fits. ADR is not a *step* in a per-sprint sequence — it's an accumulating
set of standing constraints every later stage must consult, closer to a
shared context than a pipeline stage. ARCH → PLAN → FEAT → VERIFY *is*
close to a directed chain, for one unit of work — but with a real,
demonstrated backward edge: VERIFY's finding during FEAT-012B's audit
(that PLAN-012B had never been persisted as a citable file) produced new
corrective work on the *PLAN* artifact, after FEAT had already been
implemented and initially verified. A strictly forward-only directed
graph doesn't have a place for that edge. The most accurate model found
during this investigation is: **ADR as standing context; ARCH → PLAN →
FEAT → VERIFY as a directed chain with an allowed backward-correction
edge from VERIFY to any upstream artifact its audit implicates; DOC as a
structurally similar but orthogonal cycle that doesn't sit on this chain
at all.** Section 9 discusses whether backward correction from VERIFY
should be a formally named path rather than something this investigation
had to infer from one instance of it happening.

---

## 5. Entry Criteria

Grounded in what actually gated the start of each stage in the lineages
observed, not invented from first principles. Each criterion below is
marked by evidentiary category — observed once, recommended, or required
by an existing rule — rather than presented uniformly:

- **ARCH begins** when a design question exists that an ADR doesn't
  already answer, and a prior investigation (or the current one) hasn't
  already answered it either — `docs/process/stop-conditions.md`'s
  "existing implementation already satisfies the sprint" condition is a
  related, though not identical, precedent: that condition concerns code
  already existing, not a design question already being answered, but
  the same underlying instinct applies — if the question is already
  answered, ARCH doesn't begin, a report of that fact does.
- **PLAN begins** once an ARCH exists whose recommendation the engineer
  has decided to act on. Observed once, in this lineage: PLAN-012B's own
  first draft opened by citing ARCH-024 as its authority, and was
  requested only after the engineer had reviewed ARCH-024 and chosen to
  proceed (with a different sprint label than ARCH-024's own "Recommended
  Next Sprint," confirming this is the engineer's decision to make, not
  an automatic consequence of ARCH's recommendation existing).
  Recommended as the working entry criterion; not yet confirmed across
  multiple independent lineages.
- **FEAT begins** once a PLAN is approved as the implementation authority
  — not before. This is DOC-001A's own account of the event, not
  PLAN-012B's own file: DOC-001A Section 9 describes "the corrected plan
  became the implementation authority only once the engineer explicitly
  approved it" as the canonical Level 2 example. Observed once, in this
  one lineage. **Recommended as the working entry criterion, not yet
  confirmed across multiple independent lineages: implementation should
  not begin until the PLAN it implements has been approved, in writing,
  as the implementation authority — not merely drafted.**
- **VERIFY begins** once FEAT reports itself complete and validated
  (tests passing) — not before, and not as a substitute for FEAT's own
  validation step. VERIFY audits a claim of completeness; it doesn't
  establish one from nothing. Observed once, for FEAT-012B specifically;
  recommended as the working entry criterion, not yet confirmed across
  multiple independent FEAT lineages.
- **Commit begins** only on a separate, explicit engineer instruction —
  this is a required practice, per DOC-001A Section 5, not merely
  observed or recommended here. This document does not restate DOC-001A's
  reasoning for it; it only notes that VERIFY passing is a *precondition*
  for requesting commit, not an entry criterion for commit itself, which
  remains entirely engineer-triggered.

---

## 6. Exit Criteria

- **ARCH is complete when** its status block reads "Investigation
  Complete," it has stated explicitly whether an ADR is required, and (per
  `docs/reports/README.md`'s own default structure) it has produced
  findings and a recommendation — not necessarily an accepted one. This
  criterion is grounded in standing process documentation
  (`docs/reports/README.md`), not only in one instance; ARCH-024
  satisfies this shape exactly: Status block, ADR-required call, a
  Recommended Next Sprint.
- **PLAN is complete when** the engineer has explicitly approved it as
  the implementation authority — not when Claude judges it internally
  consistent. This is a required practice: the same standard DOC-001A's
  own Level 2 approval requires, applied to a specific artifact type.
  PLAN-012B's own history shows this criterion actually being enforced,
  observed once: an internally-plausible first draft was not treated as
  complete until the engineer found and required three corrections.
- **FEAT is complete when** the code and tests exist, the appropriate
  validation target has been run (`docs/process/validation-workflow.md`),
  and results have been reported — matching `docs/process/sprint-lifecycle.md`'s
  existing Validation stage, a required practice grounded in standing
  process documentation. **Not** complete, per a gap this investigation
  reconfirms rather than discovers: `docs/reports/README.md` already
  requires a persisted Implementation Report as part of this exit
  criterion, and the FEAT-010A → FEAT-012B lineage has not produced one
  for any of its four sprints (the same compliance gap DOC-001A's Section
  7 already named — referenced here, not re-litigated).
- **VERIFY is complete when** every claim FEAT makes about matching its
  ARCH and PLAN has been independently checked against the actual code,
  tests, and file inventory — not merely against FEAT's own summary of
  itself. The FEAT-012B VERIFY pass demonstrates what this criterion
  means in practice, observed once; it is not yet confirmed as a general
  standard across multiple independent VERIFY passes. In that one
  instance, VERIFY re-derived file lists from `git status` rather than
  trusting the prior turn's claimed inventory, and re-ran the test suite
  fresh rather than citing an earlier pass's result.
- **An artifact-production cycle (the left side of Section 3's diagram)
  is complete when Verification (not Correction) reports no remaining
  issues** — DOC-001A's own five-pass history is the clearest evidence
  for treating Verification, not Correction, as the actual exit gate,
  observed in that one lineage: two correction passes each surfaced
  further issues on their own re-read, and only the pass that produced
  zero remaining findings was treated as reaching Freeze.

---

## 7. Freeze Points

Four distinct freeze behaviors are demonstrated, not one uniform rule:

1. **Permanent, edit-only-for-corrections, revise by superseding —
   ADR and ARCH (reports).** `docs/ADR.md`: "ADRs are recorded in
   chronological order and are never renumbered." `docs/reports/README.md`:
   reports are "not updated after completion except to: Correct factual
   errors. Fix broken references. Correct formatting issues... If a later
   investigation revisits the same topic, create a new report." **Not yet
   demonstrated in this repository:** every ADR currently reads
   "Accepted" — none has ever been marked superseded or deprecated, so
   the mechanics of *how* an ADR would be revised once genuinely wrong
   are inferred from the naming convention's intent, not from an observed
   example. Named as an open question, not resolved here.
2. **Approval-gated, revisable in place afterward — PLAN and DOC.**
   Freezes at explicit engineer approval, but unlike ADR/ARCH, further
   correction happens *to the same document*, through the same approval
   process, rather than by creating a new one. PLAN-012B was corrected in
   place once before approval — resolving three separately identified
   issues in that one correction event — and once more after (the
   file-inventory/citation-traceability fix); DOC-001A was corrected in
   place across three separate correction passes after its own initial
   freeze-candidate state. Neither ever became a "-v2" file.
3. **Immutable-history freeze — FEAT (source code and tests).** Freezes
   at `git commit`, which is itself an append-only, supersede-not-edit
   mechanism — structurally the same shape as ADR/ARCH's freeze, just
   enforced by git rather than by a documented convention. Any further
   change is a new commit, never a rewrite of a merged one (matching this
   project's own git safety norms).
4. **Not yet a durable artifact — VERIFY.** Because no persisted VERIFY
   report format exists (Section 11; already named in DOC-001A Section 7),
   there is currently nothing to freeze. A VERIFY finding is durable only
   insofar as it's acted on and the resulting correction is itself frozen
   under one of the three rules above.

**A general rule these four cases share:** an artifact freezes when the
role that approves it — an engineer for PLAN/DOC/commit, or the act of
`git commit` itself for FEAT — has acted, never automatically upon
Claude's own assessment that something is "done." This mirrors DOC-001A's
own "silence is not consent" principle, applied here to artifacts rather
than to individual edits.

---

## 8. Traceability

**Demonstrated, consistently, across every artifact in the ARCH-024
lineage:** each stage cites the specific section of its predecessor it
depends on, not just the document name. ARCH-024 cites ADR-010 through
ADR-013 by number. PLAN-012B cites specific ARCH-024 sections throughout
(e.g., its Section 6 ADR-requirement discussion cites ARCH-024 Section
10's per-decision list generally, then cites ARCH-024 Section 12
specifically for the one named, deliberately-unreached VLAN-scoping
trigger). FEAT-012B's code comments cite PLAN-012B sections directly
(`snmp_client.py`'s `BRIDGE_FDB_TABLE_MAX_ROWS` comment cites "PLAN-012B
Section 5, uncertainty #3" precisely). VERIFY explicitly checked that
every such citation resolved to real content before treating FEAT-012B as
ready.

**Should this become an explicit requirement, not just an observed
habit?** Recommended: yes, with one caveat about enforcement. The
citation discipline demonstrably caught real problems when it was
checked, observed in this one lineage — the FEAT-012B VERIFY pass exists
in large part *because* citation accuracy mattered enough to verify. But
**no tooling in this repository currently enforces it**: nothing checks
that a cited section number exists, that a cited document has been
committed, or that a FEAT's behavior actually matches what it cites.
Every instance of citation-checking observed so far was a manual VERIFY
pass, done once, by re-reading the cited source directly. Recommending
traceability as a required *practice* (cite the specific section, not
just the document) is well-supported by this evidence, thin as it is.
Recommending it as a *tooling-enforced gate* would not be — that would be
inventing infrastructure this repository has never built, in tension with
`ENGINEERING.md`'s "avoid opportunistic refactoring" and this document's
own instruction not to optimize for complexity. Named here as a
legitimate future `DEV-`-prefix sprint (per the existing taxonomy in
`engineering-handbook.md`), not decided here.

---

## 9. Required Review Stages

Three distinct review mechanisms are demonstrated, each with a different
evidentiary strength:

1. **Direct engineer correction** — an engineer reads a draft artifact,
   finds specific issues, and directs specific fixes, without a
   separately-invoked "break this" framing. Directly observed for
   PLAN-012B (three issues, corrected, approved in one exchange).
2. **Adversarial review** — a separately-invoked, explicitly skeptical
   pass ("Your objective is NOT to confirm the document. Your objective
   is to break it.") that traces every claim back to its cited evidence
   and searches deliberately for contradictions, loopholes, and
   unsupported assumptions. **Directly observed, turn-by-turn, only for
   DOC-001A** in this session. ARCH-024's own commit message records that
   one occurred for it too — repository evidence that the practice
   predates this session, but evidence of a different, weaker kind: a
   self-reported outcome from a process this investigation did not itself
   watch, versus a fully observed multi-turn cycle for DOC-001A. Both are
   real evidence; they are not equally strong evidence, and this document
   does not claim otherwise.
3. **Formal verification** — a confirmatory, checklist-driven pass
   against a specific set of properties, distinct from adversarial review
   in stance (confirming a corrected state is now consistent) rather than
   purpose (hunting for defects that haven't been found yet). Directly
   observed for both FEAT-012B (against its ARCH and PLAN) and DOC-001A
   (against its own resolved findings).

**Should adversarial review become required for ARCH and PLAN, not just
DOC?** This investigation found real value in it where it was directly
observed — DOC-001A's adversarial review found a genuine internal
contradiction (F1 of that review) that an earlier, direct-correction-only
pass had not caught. ARCH-024's own commit message suggests the same
practice predates this session for ARCH work specifically, though, as
above, that is a self-report rather than something this investigation
watched happen. For PLAN specifically: the lighter-weight direct-correction
cycle observed for PLAN-012B resolved the three issues that were
identified, but it was never tested against a comparably adversarial
review — its absence of further discovered problems is not evidence that
none existed to find, only that none were found by the process actually
used. `ARCH-001A`'s own Risks section warns explicitly against
"converting judgment calls into checklist items that get followed
mechanically even when they stop fitting the situation" — the same
warning DOC-001A's own Section 2 states. **Recommendation, not a settled
rule:** make adversarial review *available at the Human Architect's
discretion* for any artifact, with a soft trigger toward using it for
governance-shaped or unusually high-stakes ARCH/PLAN work — the same
"mandatory-but-lightweight vs. discretionary-but-available" tradeoff
ARCH-001A already resolved for Implementation Reports (mandatory, kept
deliberately small) versus Architecture Reviews (milestone-based,
discretionary). Adversarial review for PLAN work specifically remains
discretionary unless stronger evidence of need emerges across more than
one instance. This document does not decide which category adversarial
review belongs in generally; it names what's actually known — DOC:
directly observed working; ARCH: recorded as having happened at least
once, on weaker evidence; PLAN: not used, without demonstrated cost, but
also untested — and leaves the generalization to the Human Architect,
consistent with role-definitions.md's own allocation of that authority.

**Should VERIFY's backward-correction path (Section 4) become a formally
named review stage of its own?** Also not decided here — it was observed
working once (the PLAN-012B persistence fix), never named in advance, and
never tested against a harder case (VERIFY implicating the ARCH itself).
Named as an open question in Section 11.

---

## 10. Exceptions

`docs/process/sprint-lifecycle.md` already states the governing principle
directly: "Not every sprint needs every stage. A one-line documentation
fix does not need a full Investigation report... When a stage is
skipped, say so explicitly... rather than leaving its absence
unexplained." This document adds no new exception mechanism; it applies
that existing principle to the fuller lifecycle described in Section 3.
Each exception below is separated into what standing process
documentation permits versus what this investigation's own examined
lineage directly demonstrates:

- **ADR not required** — the default, not the exception: `ARCH-001A`'s
  own status block, and ARCH-024's, both demonstrate stating "ADR
  Required: No" explicitly and giving the reason, rather than silently
  proceeding without one. Required only when a genuine, new
  product-architecture decision is being made, per `ENGINEERING.md`'s
  Architectural Decision Records section — this exception is directly
  demonstrated, repeatedly, in the lineage examined.
- **ARCH not required** — when the design question is already answered
  by an existing ADR or a prior ARCH, or when the change is small enough
  that a PLAN (or direct implementation) can cite existing architecture
  without needing new investigation. `docs/process/sprint-lifecycle.md`'s
  "trivial sprints may skip straight to Implementation" already covers
  this — standing process documentation permits it. No example of a
  FEAT/PLAN skipping ARCH was observed within the ARCH-020–024 lineage
  this investigation examined (every FEAT in it was preceded by an ARCH);
  this exception rests on process documentation, not on direct precedent
  within that specific lineage.
- **PLAN not required** — for work small enough that FEAT's own scope is
  unambiguous from an ARCH (or from no ARCH at all, for genuinely small
  fixes) without needing a separate file-level commitment document.
  Standing process documentation (`sprint-lifecycle.md`'s general
  principle) permits this. No example of a PLAN-scale sprint skipping
  PLAN was observed in the lineage this investigation examined either;
  this exception, like the one above, rests on process documentation, not
  on direct precedent within that specific lineage.
- **Small bug fixes, documentation-only work, housekeeping** — these are
  exactly DOC-001A's own Level 1 territory (behavior-preserving,
  mechanical, inside an authorized unit of work); this document doesn't
  redefine that boundary, only notes that such work legitimately enters
  the lifecycle at Implementation (or the equivalent point for a
  documentation edit) without needing ARCH or PLAN first, provided
  DOC-001A's own governing principles for what counts as Level 1 still
  hold.

---

## 11. Known Gaps

Named, not resolved, consistent with this project's established practice
(ARCH-024 Section 10, item 7; DOC-001A Section 10) of surfacing an
unreached decision rather than silently absorbing or ignoring it:

1. **The `DOC-` artifact type has no registered place in the existing
   taxonomy either — a third instance of the same gap DOC-001A already
   found for `PLAN` and `VERIFY`.** `docs/process/engineering-handbook.md`'s
   Sprint Prefix Taxonomy lists `DOC-` / `DOCS-` as meaning
   "Documentation-only changes" (example: "Refresh project
   documentation") — a much lighter-weight category than what DOC-001A
   and this document actually are (governance investigations with their
   own adversarial-review-and-verification cycle). Whether `DOC-` should
   be redefined, or a new prefix introduced, is not decided here.
2. **`docs/architecture/` has not been updated to describe the SNMP
   relationship-evidence subsystem at all.** Its own README states
   architecture documents there "describe implemented behavior only," and
   lists three other planned-but-deferred documents (`discovery.md`,
   `benchmarking.md`, `developer-platform.md`) — none of which mention
   observation/identity/relationship resolution, ARP/LLDP/Bridge-FDB
   providers, or anything from ADR-010 through ADR-013. The canonical,
   "describes what's actually running" documentation is now stale
   relative to a substantial, shipped subsystem.
3. **No ADR in this repository has ever been superseded or deprecated,**
   so the freeze-and-revise mechanics Section 7 infers for ADRs from the
   naming convention's intent have never actually been exercised. Whether
   the intended mechanism (a new ADR, ADR.md's own convention implies) is
   the right one remains untested.
4. **Traceability is a manual practice with no tooling enforcement**
   (Section 8) — a citation can go stale or wrong and nothing catches it
   except a VERIFY pass choosing to check it.
5. **VERIFY has no persisted artifact format** (already named in
   DOC-001A Section 7, referenced here because it also directly affects
   Section 7's freeze-point analysis above) — and, newly observed here,
   **no formally named path for VERIFY findings that implicate an
   upstream artifact (ARCH or PLAN) rather than the FEAT itself.** The one
   observed instance (PLAN-012B's persistence gap) was handled well, but
   ad hoc — there is no written rule for what happens when VERIFY finds a
   PLAN- or ARCH-level problem rather than a FEAT-level one.
6. **Implementation Reports remain mandatory and unproduced** for the
   entire FEAT-010A → FEAT-012B lineage — the same gap DOC-001A's Section
   7 already named, restated here only because it is also, precisely, an
   Exit Criteria failure under Section 6 above, not a new finding.
7. **This document's own "refined model" (Section 3) has a narrow
   evidentiary base** — three artifact-production cycles and one complete
   delivery chain, all from the same recent period — relative to the much
   larger body of older sprint history `ARCH-001A` already surveyed and
   found following a simpler, pre-PLAN/pre-VERIFY shape. Whether the
   refined model should be treated as the project's general-going-forward
   workflow, or remains specific to PLAN/VERIFY-era work, is not decided
   here.

---

## 12. Summary

The proposed nine-stage lifecycle is real, but it describes two things at
once that are worth separating: a **per-artifact production cycle**
(Investigation → Review → Correction → Verification → Freeze), evidenced
for ARCH-024 (via its own commit-message record), PLAN-012B, and DOC-001A
(the latter two directly observed; ARCH-024's evidence is a self-report
of the same shape, not directly watched); and an **outer artifact chain**
(ADR as standing context → ARCH → PLAN → FEAT → VERIFY → Commit → Push),
evidenced completely once, in the ARCH-024 lineage this session lived
through — with a real backward edge from VERIFY back to PLAN that a
strictly forward pipeline doesn't accommodate. **This is an emerging
pattern in the project's most recent, PLAN/VERIFY-era work, not a
confirmed universal description of NetworkMapper's engineering
history** — `ARCH-001A`'s own broader survey of earlier sprints (FEAT-001,
FEAT-002A/B, TEST-001/002, and others) shows none of them going through a
PLAN artifact or a separately-invoked adversarial review; they followed
the simpler shape `sprint-lifecycle.md` still documents. The refined
model is a specialization observed in recent work, not a replacement for
that older, still-standing description.

ADR and ARCH freeze permanently, revised only by superseding, never
editing (ARCH's revision mechanism is fully demonstrated; ADR's is
inferred but never yet exercised). PLAN and DOC freeze at approval but
remain revisable in place through the same approval process afterward.
FEAT freezes at commit, an immutable-history event structurally like
ADR/ARCH's freeze but enforced by git rather than convention. VERIFY does
not yet freeze at all, because it has nowhere durable to freeze into.

Seven gaps are named rather than resolved: `DOC-`'s own missing taxonomy
entry (a third instance of a pattern DOC-001A already found twice);
`docs/architecture/`'s staleness relative to the SNMP subsystem;
ADR's untested supersession mechanism; traceability's lack of tooling
enforcement; VERIFY's missing artifact format and missing named
backward-correction path; the still-unproduced, still-mandatory
Implementation Reports for FEAT-010A through FEAT-012B; and this
document's own refined model's narrow evidentiary base relative to the
project's fuller sprint history. None of the seven is resolved by this
document — each is exactly the kind of decision `ENGINEERING.md`'s
AI-Assisted Development section reserves for explicit sprint approval,
not something a workflow investigation should settle by itself.

### Resolution status of the DOC-001B adversarial review's findings

F1 (Sections 2/3 vs. Section 9 disagreeing on whether ARCH adversarial
review has been demonstrated) is resolved by adopting one consistent
distinction throughout — directly observed for DOC-001A, recorded but not
directly observed for ARCH-024 — threaded through Sections 2, 3, and 9.
F2 (the PLAN-012B quote actually belonging to DOC-001A) is resolved by
correcting the attribution in Section 5. F3 (the ARCH-024 Section 10
item 7 citation PLAN-012B doesn't actually make) is resolved in Section 8
by citing what PLAN-012B's Section 6 actually references — Section 10
generally, Section 12 specifically. F4 (the checklist-vs-judgment warning
misattributed to this document's own Section 2) is resolved in Section 9
by attributing it to DOC-001A's Section 2 instead. F5 (the refined
model's narrow evidentiary base presented without adequate scope) is
resolved by a new "Evidentiary scope of this model" subsection in Section
3, an added Known Gap (item 7 above), and updated framing here in the
Summary. F6 (PLAN and VERIFY entry criteria overstated as established
rather than single-instance) is resolved in Section 5 by adding
observed-once/recommended/not-yet-confirmed framing to both. F7 (the
claim that PLAN-012B's lighter review "worked," implying sufficiency) is
resolved in Section 9 by replacing it with "resolved the issues that were
identified... never tested against a comparably adversarial review."
F8 (asymmetric hedging between ARCH-not-required and PLAN-not-required)
is resolved in Section 10 by applying the same process-documentation-vs-
direct-precedent distinction to both. F9 (the stop-conditions.md analogy
overstated as a "negative-space definition") is resolved in Section 5 by
softening it to "a related, though not identical, precedent."

This document is a corrected draft, produced through one investigation,
one adversarial review, and one correction pass, and — like DOC-001A
before it — does not carry any authority until it goes through formal
verification against this corrected state and is explicitly approved.
