# Status

Draft — Corrected Pending Formal Verification

Investigation: Complete (DOC-001A)

Correction Pass: Three passes applied. The first resolved Findings F1–F14
from the DOC-001A adversarial review. The second resolved two secondary
inconsistencies the first pass's own consistency re-read surfaced — a
composition-rule asymmetry between Sections 4 and 7, and a classification/
authorization-state conflation in Section 9's historical examples. The
third resolved Findings 1–5 from the formal verification audit — a
Status-block self-contradiction, two mislabeled/uncounted new governance
principles, an unexplained provenance gap in the commit/push resolution,
and an incomplete self-tracking summary. See Section 10 for the
resolution status of each.

Governs: What Claude may change autonomously versus what requires explicit
engineer approval, across NetworkMapper's engineering artifacts (ADR, ARCH,
PLAN, FEAT, VERIFY, source code, tests, documentation).

Production Code Modified: No — this document is process/governance only.

ADR Required: No. This is a process document, the same category
`ARCH-001A`'s own status block already places itself in ("process guidance
already has its own, correctly-scoped home in `ENGINEERING.md` and
`docs/AI-DEVELOPMENT-GUIDE.md`; introducing an ADR for it would blur a
distinction the repository already draws correctly"). This document extends
that home rather than recording a product-architecture decision.

This document has now been through one adversarial review, a formal
verification audit, and three correction passes responding to them. It
has **not** yet been re-verified against this latest pass — that is
deliberately the next step, not this one. Until adopted, it does not
itself carry authority — the existing scattered guidance in
`ENGINEERING.md`, `docs/AI-DEVELOPMENT-GUIDE.md`, and `docs/process/`
remains authoritative.

**A note on project naming.** This prompt referred to "the Dominion
project." Nothing in this repository — no file, no `git log` entry, no
remote — uses that name anywhere; every artifact identifies the project as
NetworkMapper. Per this project's own stop-conditions.md ("Repository
contradicts the prompt... stop rather than fabricating it"), this document
is written for NetworkMapper, the name the evidence actually supports,
rather than inventing a "Dominion" identity to match the prompt. This is
flagged here rather than silently resolved either way.

---

## 1. Purpose

NetworkMapper's engineering process already has a demonstrated shape:
`docs/process/sprint-lifecycle.md` defines Investigation → Architecture
Review → Implementation → Validation → Human Review → Commit; `docs/ADR.md`
records accepted architecture decisions; `docs/reports/` records
investigation and implementation history; and, in the SNMP
relationship-evidence lineage most recently worked (ADR-010 through
ADR-013, ARCH-020 through ARCH-024, FEAT-010A through FEAT-012B), that
lifecycle has visibly specialized further into a five-stage pattern: an
**ADR** records the accepted policy, an **ARCH** report investigates one
sprint's design question against it, a **PLAN** document translates an
approved ARCH into a concrete, file-level implementation commitment, a
**FEAT** implementation executes that plan, and a **VERIFY** pass audits
the finished implementation against both the ARCH and the PLAN before
commit.

What has never been written down in one place is *who decides what* at
each of those stages — specifically, which edits Claude may make without
asking, and which require an engineer's explicit go-ahead first. That gap
is real: it was directly observed during FEAT-012B, where an unprompted
correction to the implementation plan (Section 3's file inventory) had to
be distinguished, after the fact, from a correction that had gone through
proper review (the same section, after the engineer's approval).

This document exists to close that gap by writing down the authority model
already implicit in how NetworkMapper's engineering process actually
runs — not to invent a new one, except where an adversarial review of this
document's own first draft found a genuine gap that formalization itself
exposed (Section 2 notes the two places this happened explicitly, rather
than presenting them as though they were always implicit practice). Its
purpose is narrow: define, for every category of edit Claude might make,
whether it may proceed unasked, must be proposed and approved first, or
must stop and escalate without proceeding at all.

---

## 2. Guiding Principles

Most of these are drawn directly from `docs/process/engineering-principles.md`,
`ENGINEERING.md`'s AI-Assisted Development section, and
`docs/AI-DEVELOPMENT-GUIDE.md`'s Core Principle. **Three are not** — the
self-referential floor, "silence is not consent," and "low confidence
overrides available authority" — and are labeled as such in their own
bullets below, not just here. The first two were mischaracterized as
restatements in the original draft, per the DOC-001A adversarial review's
Finding F4; the third was added afterward, as an explicitly new
principle, and was never labeled as new at all until the formal
verification audit caught the gap (Finding 3). All three exist because no
existing NetworkMapper document actually states them before DOC-001A.

- **Authority follows consequence, not effort.** A change is gated by how
  hard it would be to undo or how far its effects reach, not by how much
  work it took to produce. A five-line PLAN correction that changes what
  gets implemented outranks a two-hundred-line mechanical test update that
  changes nothing about behavior.

- **New governance principle, adopted through this review — not a
  restatement of existing policy: silence is not consent, for Level 2 and
  Level 3.** No existing NetworkMapper document states this rule before
  DOC-001A — the original draft mischaracterized it as restated, the same
  gap Finding F4 found in the self-referential floor below (this bullet's
  own provenance was left uncorrected until Finding 2 of the formal
  verification audit caught it). The absence of an objection to a
  proposal is not the same as approval of it; Levels 2 and 3 require an
  affirmative signal from an engineer before Claude proceeds. Level 1 is
  a deliberate, bounded exception to this, not a violation of it: a Level
  1 edit proceeds without a *per-edit* signal, but only when it falls
  inside a unit of work the engineer already affirmatively authorized
  (Section 3 defines this precisely). The engineer's authorization of
  that unit of work — not the mere absence of any objection to any
  particular edit inside it — is the affirmative signal this principle
  requires. (Scope corrected per Finding F1: the original draft stated
  this principle broadly enough to contradict Level 1's own definition;
  this version scopes it correctly and ties it to Section 3's boundary
  rule.)

- **Reversibility is not sufficient justification for autonomy on its
  own.** Git makes almost everything reversible; that does not make
  everything autonomous. `docs/AI-DEVELOPMENT-GUIDE.md`'s Review Commands
  category (`git reset`, `git clean`, bulk deletes) lists these commands
  with no rationale of its own stated anywhere in that document. The
  reading that they sit there because they are reversible-but-still-risky
  is **DOC-001A's own inference**, not the source document's stated
  reasoning — labeled as such per Finding F5, which found the original
  draft attributing this rationale to the source as if the source had
  said it. This policy treats reversibility alone as insufficient
  justification for autonomy on its own merits, independent of whether
  `docs/AI-DEVELOPMENT-GUIDE.md` explains its own list the same way.

- **New governance principle, adopted through this review — not a
  restatement of existing policy: a governing document cannot authorize
  its own expansion.** No existing NetworkMapper document states this
  rule before DOC-001A. It is introduced here because drafting this
  policy surfaced the need for it directly (Finding F4): without it, an
  AI operating under an authority policy could, in principle, use that
  same policy's own Level 1 housekeeping allowance to loosen the policy
  itself, one individually reasonable edit at a time. Once adopted, no
  edit to this document, or to any other document that itself defines
  Claude's operating authority (`ENGINEERING.md`,
  `docs/AI-DEVELOPMENT-GUIDE.md`, everything under `docs/process/`), may
  be made autonomously if the effect is to grant additional autonomy,
  weaken a restriction, or change what counts as an authorized unit of
  work. See Section 7 for how this interacts with Level 1's cosmetic-edit
  allowance for authority-defining documents specifically.

- **When multiple governing artifacts disagree, the most specific, most
  recently approved one wins — but a disagreement is itself information,
  not something to resolve silently.** ARCH-024 already demonstrates
  this: it applied ADR-010 through ADR-013 directly, named exactly one
  place where a future need might exceed ADR-012's existing credential
  model, and explicitly declined to resolve that gap itself. This policy
  treats a genuine conflict between approved artifacts as a
  Stop-and-Escalate condition (Section 6), not a judgment call — with one
  such conflict already found and explicitly resolved rather than left
  open: commit/push authority, recorded as its own governance decision in
  Section 5 rather than reconciled by interpretation (Finding F2 found
  the original draft violating this very principle on that exact
  question).

- **Formalization must not convert judgment into a checklist followed
  past the point it still fits.** `ARCH-001A`'s own Risks section names
  this directly: the project's actual strength has been judgment —
  recognizing a broken premise, recognizing when a constraint rules out an
  otherwise-reasonable idea. This policy is written as a decision
  framework for classifying an edit, not as an exhaustive list intended to
  replace that judgment; Section 8 exists specifically for what a list
  cannot anticipate.

- **New governance principle, adopted through this review — not a
  restatement of existing policy: low confidence overrides available
  authority.** No existing NetworkMapper document states this rule before
  DOC-001A either. It was added during the post-adversarial correction
  process as an additional governance principle adopted through DOC-001A
  review, and the original draft never labeled it as new at all — not mischaracterized as
  restated, simply unlabeled either way, which the formal verification
  audit caught as Finding 3 (the intro paragraph above's "two are not"
  count previously missed this principle entirely). Even where Level 1
  would normally permit an edit, if Claude cannot establish with high
  confidence that the change is mechanical, behavior-preserving,
  architecture-preserving, and uniquely implied by already-approved work,
  it must ask rather than act. A level being *available* for a category of
  edit is necessary but not sufficient — confidence that this specific
  edit actually qualifies is independently required, and the default
  under any doubt is to ask (Section 8).

---

## 3. Authority Levels

Four levels, matching the four the investigation was asked to consider,
with names chosen to describe the *behavior* at each level rather than
just its number — because the number alone doesn't travel well through a
document this long, and the existing project vocabulary (`AI Investigator`
/ `AI Implementer` / `AI Reviewer` in `role-definitions.md`; `Safe` /
`Review` / `Never Approve` commands in `docs/AI-DEVELOPMENT-GUIDE.md`)
gives at least two precedents for descriptive naming over bare numbers.
(Narrowed per Finding F13: the original draft generalized this into an
unsupported claim about the project's overall naming preference from just
those two examples.)

| Level | Name | What it means |
|---|---|---|
| **0** | **Observation** | Read-only. Investigation, verification, auditing. Nothing in the working tree changes. |
| **1** | **Autonomous Housekeeping** | Inside an already-authorized unit of work (see below), Claude makes a behavior-preserving edit without asking first — but always reports what changed. |
| **2** | **Engineer Approval Required** | Claude proposes a specific, concrete change and waits for explicit approval before making it. |
| **3** | **Stop and Escalate** | Claude does not propose a resolution at all. It reports the condition and waits for direction, because no artifact currently approved gives it the authority to choose a path forward. |

### Level 1's precise boundary — authorized units of work

**Level 1 autonomous housekeeping is permitted only within an
already-authorized unit of work.** An authorized unit of work is any task
the engineer has explicitly set in motion — an approved FEAT
implementation, a PLAN-drafting task, a requested documentation revision,
a requested audit, or any other explicit engineer instruction. The
engineer's authorization of that unit of work *is* the affirmative signal
Section 2's "silence is not consent" principle requires; Level 1 does not
additionally require a separate signal for each individual edit inside
it.

**Outside an authorized unit of work, Claude has no standing permission to
roam the repository making unrelated housekeeping edits.** Noticing a
stale cross-reference while doing something else does not, by itself,
license fixing it, unless fixing it is itself part of the current unit of
work — otherwise it is reported and left for the engineer to decide,
per Section 8's default when uncertain.

This resolves an ambiguity the DOC-001A adversarial review identified
(Findings F1 and F3): "Level 1 = act without asking" does not mean "act on
anything, anywhere, without ever having been asked to work in that area at
all." It means "once given a unit of work, do not seek line-item approval
for its behavior-preserving sub-steps." A mechanical test-fixture update
made while implementing an approved FEAT, or a PLAN drafted after being
asked to plan a FEAT, are both Level 1 for this reason — they are
behavior-preserving sub-steps of a unit of work the engineer already
authorized, not freestanding autonomous initiative reaching outside it.
Being inside an authorized unit of work is necessary for Level 1, but not
sufficient on its own — it does not, by itself, make *every* sub-step of
that unit of work Level 1. Writing a *new* test with new behavioral
assertions during that same FEAT is a different case: still inside the
authorized unit of work, but substantive rather than mechanical, and
therefore Level 2 in classification (with its approval already satisfied
by the plan, not by being Level 1). Section 4 and Section 7 draw this
line precisely; Section 9 works through the concrete case where an
earlier draft of this document conflated the two.

### Alternatives considered

**A three-level model** (collapsing Observation into Autonomous
Housekeeping, on the reasoning that both are "things Claude can just do")
was considered and rejected. Observation and Housekeeping have different
failure modes: a bad Observation produces a wrong report, which a human
reads and can catch before anything changes; a bad Housekeeping edit
changes the repository directly. Collapsing them would blur exactly the
distinction the VERIFY stage exists to preserve — VERIFY (Observation) is
only trustworthy as an independent check because it is guaranteed not to
have touched what it's checking.

**A five-level model** (splitting Level 2 into "propose" and "execute
after approval" as two separate levels) was also considered, since that
distinction is real — PLAN-012B's own correction cycle shows a proposal
being reviewed, corrected, and only then executed. It was rejected as its
own top-level tier because that propose/execute split is not a difference
in *authority*, it is the normal internal shape of Level 2 itself: every
Level 2 action already has a propose sub-step and an execute sub-step, and
splitting them into separate numbered levels would suggest they could
carry different authority requirements, which they don't — both still
require the same engineer approval.

**Naming the levels after the existing AI Investigator / Implementer /
Reviewer roles** (`role-definitions.md`) was considered instead of numeric
levels. Rejected because those are *roles a sprint assigns to a turn* (who
is doing the work), while this policy classifies *edits* (what kind of
change is being made) — the same role can make Level 0, 1, and 2 edits
within a single sprint, exactly as this session's own FEAT-012B/PLAN-012B
work did (Level 1 — persisting the already-approved PLAN-012B content into
a committed file; Level 2 — the substantive provider implementation and
the PLAN's own file-inventory correction; Level 0 — the final audit; all
inside one continuous AI Implementer/Reviewer stretch). Numbered levels
avoid conflating the two axes.

Adding a fifth level to separately track "inside an authorized unit of
work" versus "not" (rather than folding it into Level 1's own definition,
above) was also considered while resolving Findings F1/F3, and rejected
for the same reason as the propose/execute split: it is a precondition for
Level 1 applying at all, not a distinct authority tier with its own
approval requirement — the smallest correction was to define Level 1
precisely, not to add a level.

---

## 4. Automatic Housekeeping Changes (Level 1)

The required authority level for any edit is determined by the single
model stated in full in Section 7 — edit type, artifact sensitivity, and
lifecycle state together, with the most restrictive applicable rule
winning. This section supplies the edit-type input to that model for
housekeeping-shaped edits; it does not define a separate or competing
rule. Classification (what level an edit requires) is a distinct question
from authorization state (whether that requirement has already been
satisfied) — see Section 7 for the full statement of that distinction,
which principle 5 below applies directly.

### Governing principles

An edit qualifies for Level 1 only when **all** of the following hold —
these are the reason each example below is safe, not a substitute for
checking them:

1. **The edit is behavior-preserving under any reasonable reading.** Not
   "probably fine" — the edit must have no plausible interpretation under
   which it changes what the system does, what a test verifies, or what a
   reader would conclude about intent. A comment that merely restates code
   is Level 1 to clarify; a comment that records a non-obvious constraint
   is not safe to "clarify" into something that drops that constraint.
2. **The edit is mechanically and uniquely implied by an already-approved
   change — not discretionary propagation.** This is the distinction
   between "mechanically updating tests after already-approved interface
   changes" (Level 1 — the interface change already cleared Level 2, and
   there is exactly one correct way to update the dependent test to match
   it) and updating something because Claude judged it would be more
   *consistent* to do so (Level 2, because that judgment was never
   approved, even if the underlying motivating change was). **If more
   than one reasonable downstream change exists, Level 1 authority ends
   and engineer approval is required** — this is the actual test for
   whether an edit is still "mechanical," not just a description of the
   category. (Tightened per Finding F7: the original draft's "documentation
   consistency edits" example had no such boundary and could be stretched
   to cover discretionary rewording.) **An edit's level is inherited from
   the decision that necessitates it, not from the file type it happens to
   touch** — this is why formalizing an already-corrected, already-cited
   PLAN into a committed file (as this session did for PLAN-012B) was
   Level 1 work, done inside the authorized unit of work of persisting an
   already-approved plan: the content had already cleared Level 2 in the
   conversation that produced it, and there was exactly one way to persist
   it faithfully.
3. **The edit does not foreclose a choice a human might reasonably have
   made differently.** Fixing a typo forecloses nothing. This is the same
   uniqueness test as principle 2, applied to wording rather than to code:
   if a human could reasonably have phrased the "fix" differently in a way
   that changes meaning, it is not a Level 1 edit.
4. **The edit is reported, not silent.** Level 1 means "proceed without
   asking first," not "proceed without saying." Every Level 1 edit is
   still visible in the diff and still described in whatever summary
   follows.
5. **The edit falls within a currently-authorized unit of work
   (Section 3) — a precondition for exercising Level 1 authority, not a
   basis for classifying an edit as Level 1 in the first place.** An edit
   that is behavior-preserving under principles 1–4 is still not
   exercisable as Level 1 if nothing currently in progress authorized
   Claude to be touching that file or area at all. The reverse direction
   matters just as much and cuts the other way: being inside an
   authorized unit of work never turns a substantive, non-housekeeping
   edit into a Level 1 one — it can satisfy that edit's Level 2 approval
   requirement in advance (Section 7), but it does not change what the
   edit *is*. (Added per Findings F1/F3; the reverse-direction sentence
   added in the follow-up pass that resolved the classification/
   authorization-state conflation those findings' first fix left open.)
6. **The edit stays inside the artifact-sensitivity floor for the file it
   touches** (Section 7). A change that would be Level 1 on an ordinary
   source comment is not automatically Level 1 on the text of an Accepted
   ADR, or on a document that itself defines Claude's authority — Section
   7's Documentation row states the precise rule for the latter case
   (Finding F6).

If, after an edit has already been made under Level 1, it turns out one of
these principles did not actually hold — see Section 6's
retroactive-misclassification condition (added per Finding F9). This
section governs classifying an edit *before* it is made; it does not by
itself resolve a misclassification discovered afterward.

### What qualifies

Applying those principles to the examples the investigation was asked to
evaluate, and to the bounded categories Finding F7 requires in place of
the original draft's broader "documentation consistency edits" example:

- **Spelling, grammar, markdown formatting.** Behavior-preserving by
  definition — these never change what a sentence asserts.
- **Stale section references and broken internal cross-references** —
  specifically: a reference that points to the wrong section number or a
  moved/renamed target, where exactly one correct target exists. This is
  the exact category `docs/reports/README.md` already names as an
  allowed correction to an otherwise-frozen historical report ("Fix broken
  references"). Fixing `SnmpBridgeFdbProvider`'s own docstring pointing at
  the wrong ARCH-024 section number would qualify; *renumbering ARCH-024's
  own sections* to make the reference correct the other way would not —
  that changes the referenced artifact, not the reference.
- **Duplicate wording removal, formatting cleanup, comment/docstring
  clarification.** Safe exactly to the extent principle 3 holds — the
  duplication was accidental, not deliberate emphasis, and the
  clarification doesn't add or remove a claim.
- **Import cleanup, lint-only changes.** Behavior-preserving by
  construction, provided the linter/formatter itself isn't reconfigured as
  part of the same change (reconfiguring the linter is a tooling/process
  decision, Level 2).
- **Mechanically updating a test to match an already-approved interface
  change**, bounded to three concrete shapes: updating an exact renamed
  symbol; correcting an exact changed file path; mechanically updating a
  test fixture required by an approved signature change. Each of these has
  exactly one correct outcome once the upstream change is known — there is
  no discretion left to exercise. If the "mechanical" update requires a
  judgment call about what the new expected behavior *should* be, that
  judgment call is Level 2, wearing a test file's clothing, and principle
  2's uniqueness test is what tells them apart. **Writing a *new* test
  that encodes a new behavioral assertion is not this category**, even
  when a PLAN named the test and its intent in advance: deciding what to
  assert, what fixture to construct, and what edge case to cover is
  substantive implementation work, not mechanical maintenance. Such a
  test is Level 2 in classification; its approval requirement may already
  be satisfied wherever the PLAN specified it precisely enough (Section
  7), but that satisfies the approval, not the classification.
- **Verified-cosmetic edits to authority-defining documents specifically**
  (`ENGINEERING.md`, `docs/AI-DEVELOPMENT-GUIDE.md`, `docs/process/*`,
  this document) — narrowly: a typo; broken Markdown; a provably stale
  section number; a malformed internal link. See Section 7's Documentation
  row for the full rule and why the boundary is drawn exactly there.

Removed from this list, per Finding F7: the original draft's
"documentation consistency edits" example (propagating one document's
already-approved change into another document's *description* of it) is
no longer offered as its own Level 1 category. No demonstrated instance of
this specific category was ever found in this project's history, and
unlike the bounded examples above, it has no stated limit on how far the
propagation could reasonably stretch. Where this situation genuinely
arises, it is Level 2 unless it collapses into one of the bounded
categories above (e.g., correcting an exact changed file path).

---

## 5. Engineer Approval Required (Level 2)

### Governing principle

If an edit changes what the system *does*, what it *promises* (an API,
a CLI surface, a persisted format, an observation/failure semantic), or
what the project has *decided* (an ADR, an ARCH's conclusions, a PLAN's
commitments), it requires a proposal and an explicit approval before it
happens — regardless of how small the diff looks. This is not about line
count; ARCH-024's own single-word category name (`bridge_fdb`) is a
one-line change with architectural weight (Section 5: choosing that name
over reusing `arp_neighbor` or `connected_to` was itself the point of that
section), and required exactly the review it got. (Corrected per Finding
F12: the original draft mislabeled `bridge_fdb` as "five-word.")

### Categories, grounded in what has actually required approval in this project's history

- **Runtime behavior.** Anything that changes what a running discovery
  changes or reports — new evidence emitted, a filter's threshold, a
  resolution path. Every provider in this lineage (ARP, LLDP, Bridge-FDB)
  went through an ARCH before a line of provider code was written.
- **Public APIs and CLI behavior.** `docs/AI-DEVELOPMENT-GUIDE.md`'s
  Architecture First section already names this directly: "AI should
  not... Rename public APIs... unless explicitly requested." The
  `--snmp-bridge-fdb` flag added in FEAT-012B is a CLI-surface change and
  was implemented only after PLAN-012B specified it exactly, following the
  same pattern as `--snmp-arp` (FEAT-010A) and `--snmp-lldp` (FEAT-012A)
  before it.
- **Persistence.** Any change to what `Project`, `NetworkGraph`, or the
  observation/identity/relationship models store or how they serialize.
  ADR-011/012/013's careful scoping of the observation-retention layer
  exists specifically because this category carries long-lived
  compatibility weight.
- **Architecture.** Anything ADR-010 through ADR-013, or their successors,
  would need to be consulted to answer. `ENGINEERING.md`'s Architecture
  Policy: "Do not modify architecture unless the sprint explicitly
  requires it."
- **Observation and failure semantics.** What counts as a qualifying row,
  what gets excluded and why, what a client treats as load-bearing versus
  best-effort. ARCH-024 Section 6/7 exist because this project treats
  these as decisions, not implementation details — the self(4)-row
  exclusion design, and the load-bearing/best-effort split for
  `dot1dTpFdbStatus`, were both explicitly reasoned through and reviewed,
  not defaulted.
- **Dependency changes.** Adding, removing, or upgrading a package is a
  supply-chain and compatibility decision outside any single sprint's
  stated scope unless the sprint says so.
- **Abstraction changes.** Introducing a new shared base class, a new
  generic table-walk framework, etc. ARCH-023 Section 8 explicitly
  considered and rejected generalizing the ARP/LLDP provider shape with
  only two similar providers as evidence; ARCH-024 Section 8 reaffirmed
  that rejection with a third. Introducing that abstraction later is a
  real architectural decision, not a refactor Claude should make
  unprompted just because a third near-identical case now exists.
- **Scope changes.** Widening what a sprint touches beyond its own
  approved boundary — `ENGINEERING.md`: "Avoid unrelated cleanup... If
  additional work is discovered, report it separately." PLAN-012B Section
  8 names this explicitly for FEAT-012B: VLAN-aware coverage, the CSI
  workaround, and six other adjacent ideas are all named specifically so
  they are *not* silently absorbed into the approved scope. (Corrected
  per Finding F11: the original draft undercounted this list as "five
  other" against the actual eight total exclusions.)
- **ADR / ARCH / PLAN modifications.** Never edited in place once
  approved and acted on — see Section 7. Superseding one is itself a
  Level 2 (at minimum) decision, made by producing a new artifact, not by
  rewriting the old one.

### What "approval" looks like in practice

A Level 2 proposal states the specific change, cites the artifact section
that authorizes or motivates it, and waits. This session's own PLAN-012B
correction cycle is the concrete template: three specific, scoped
corrections were proposed, the engineer approved them explicitly ("The
FEAT-012B architecture and implementation approach are approved in
principle, but correct three planning issues before implementation"), and
only then were they made.

**Commit and push require explicit engineer authorization — resolved here
as an explicit governance decision, not a textual reconciliation.** The
existing repository documentation is genuinely inconsistent on this point,
and the original draft of this document made the mistake of trying to
reconcile that inconsistency by interpretation instead of naming it
(Finding F2 of the DOC-001A adversarial review). Stated plainly, the
conflict is real: `docs/process/sprint-lifecycle.md` states "AI assistants
do not commit on their own initiative — every sprint stops after Human
Review and waits for explicit direction"; `docs/AI-DEVELOPMENT-GUIDE.md`'s
Safe Commands list places `git commit` and `git push` under "Normally
approve"; and `ENGINEERING.md`'s Definition of Done lists "Changes have
been committed" / "Changes have been pushed" as sprint-completion criteria
with no actor stated. These do not fully reconcile by close reading alone,
and this document does not attempt to make them.

Instead, this policy resolves the conflict by explicit decision:

> **`git commit` and `git push` require explicit engineer authorization,
> given separately from — and after — any approval of the underlying
> change.** A command's appearance in a "safe" or "normally approve" list
> describes operational risk/friction only (how much scrutiny a *proposed*
> invocation of that command should get when Claude does propose it) — it
> does not grant Claude standing authority to decide *when* a commit or
> push should occur. Claude may prepare and recommend a commit (a drafted
> message, a summary of what's ready) but must wait for a separate,
> explicit engineer instruction before executing the commit or push
> itself.

This did not bypass Section 6's Stop-and-Escalate rule, which says Claude
should not reach "the propose a specific change" stage at all for a
genuine artifact conflict. It didn't, in the order it actually happened:
the conflict itself was surfaced through the DOC-001A adversarial review
(Finding F2) and reported there, not resolved. The specific resolution
quoted above was then directed by the engineer's own instruction during
the correction pass that followed, not decided unilaterally by Claude
mid-conflict. What appears above is the record of that engineer-directed
decision, not an instance of Claude resolving a Level 3 condition on its
own authority. (Added per Finding 4 of the formal verification audit,
which found this provenance unclear on the page even though the
underlying process was sound.)

In this session, FEAT-012B was fully implemented, verified, and reported
as ready across several turns before a commit happened — the commit
itself waited for a separate, later, explicit "commit and push." This
governance decision formalizes that observed practice going forward,
rather than leaving three mutually-in-tension documents for a future
reader to reconcile differently each time.

---

## 6. Stop-and-Escalate Conditions (Level 3)

### Governing principle

Level 2 assumes Claude can correctly identify *what* to propose — the
uncertainty is only about whether an engineer agrees. Level 3 is
different: it applies when the currently-approved artifacts do not
contain enough information to construct a correct proposal at all, or
when they actively conflict. Proposing something anyway, and letting the
engineer reject it, is not a safe substitute for stopping, because a
plausible-looking but ungrounded proposal can itself become the thing
that gets rubber-stamped.

This project's `docs/process/stop-conditions.md` already enumerates this
list from real history (the FEAT-002B self-contradiction, the KNOW-001
fabricated-premise example, the DEV-002 already-implemented discovery).
This policy adopts that list directly and maps it onto the ADR → ARCH →
PLAN → FEAT → VERIFY lineage specifically:

- **Implementation contradicts architecture.** A FEAT turns out to
  require something an ARCH/ADR didn't authorize.
- **Approved documents conflict.** Two artifacts that are each
  individually approved disagree about what should happen — this is
  distinct from one document simply being stale (Level 1 fixes staleness;
  Level 3 is for an actual contradiction between two things that are each
  still considered current). Section 5's commit/push resolution is the
  worked example of this condition actually being surfaced and resolved
  explicitly, rather than reasoned around, per Finding F2.
- **Implementation requires architecture expansion.** The FEAT stage
  discovers that satisfying the PLAN as written requires a capability the
  ARCH never scoped in.
- **A new ADR trigger is discovered.** ARCH-024 Section 10 names the
  precise shape of this: a candidate trigger identified and *deliberately
  not reached* by the approved scope, named explicitly rather than
  silently resolved either by ignoring it or by expanding scope to handle
  it. PLAN-012B Section 6 carries the same trigger forward as an explicit
  stop condition for FEAT-012B's own implementation.
- **Live-device (or otherwise external) evidence contradicts a
  documented assumption.** PLAN-012B Section 5's uncertainty #2 — if
  real-device VLAN-scoping behavior shows classic `dot1dTpFdbTable`
  returns too little coverage to be worth shipping as scoped — is written
  as exactly this condition: "that would be genuinely new evidence
  ARCH-024 did not have... the correct response is to stop, report the
  finding, and let engineering review decide... not to quietly widen this
  plan's scope."
- **Uncertainty that cannot be resolved from existing approved
  artifacts.** The residual category: something is unclear, and neither
  reading the code nor reading the ARCH/ADR/PLAN chain resolves it.
- **A past Level 1 edit is discovered not to have been behavior-/
  intent-preserving after all.** Added per Finding F9. This is a stop
  condition, not a repair job Claude can quietly do itself: if an edit
  made under Level 1 authority is later found not to have actually
  satisfied Section 4's governing principles, Claude must report the
  misclassification **immediately** and must **not** silently repair or
  conceal it, however small the original edit was. Further corrective
  action requires engineer review before Claude proceeds. This closes a
  gap Section 4 alone doesn't: that section governs classifying an edit
  *before* it's made, not discovering afterward that a classification was
  wrong.

### What "stop" means concretely

No code or documentation is changed to work around the condition. No
interpretation is silently chosen. The condition is reported — what was
found, which approved artifact it conflicts with or falls outside of, and
why it can't be resolved from what's already approved — and the turn ends
there, waiting for direction. This is the one place in this policy where
Claude does not even reach the "propose a specific change" stage that
defines Level 2. For the retroactive-misclassification condition above,
this also means not quietly reverting or "fixing" the original edit
without saying so — the report comes first, unconditionally.

---

## 7. Artifact Sensitivity

Different artifact types warrant different defaults, because they carry
different kinds of authority once approved.

**The required authority level is determined from the applicable edit
type (Sections 4–6), artifact sensitivity (this table), and lifecycle
state (draft versus approved/accepted/binding). The most restrictive
applicable rule wins.** This is the single composition rule this policy
uses — stated identically here and in Section 4 so it cannot be missed by
a reader who consults only one table or only one section (Finding F10 of
the DOC-001A adversarial review; the earlier draft's asymmetric "Section 7
raises, never lowers Section 4" phrasing has been removed — there is one
rule, not two sections competing to set a floor). The table below gives
each artifact type's default level for a *typical* edit; Sections 4–6
still govern which specific edits within that type actually qualify, and
no row below overrides a more restrictive answer any of those sections
would give.

**Classification is a separate question from authorization state.**
The rule above answers "what level does this edit require" — it does not
answer "has that requirement already been met." Those are different
questions, and conflating them was a real defect in an earlier draft's
Examples table (Section 9), found during a consistency re-read after the
first correction pass. An already-authorized unit of work (Section 3) can
satisfy a Level 2 approval requirement *in advance* — most directly, an
approved PLAN's own content is the Level 2 approval for implementing
exactly what it specifies, so no separate propose-and-wait step is needed
when that implementation happens. But satisfying the approval requirement
this way does not reclassify the underlying action as Level 1. **Level 1
remains autonomous housekeeping only, and only inside an already-
authorized unit of work** (Section 3) — it is never a status substantive
work is promoted into merely because the encompassing sprint was
approved. Section 9 shows both readings applied to the same historical
examples, including one case where the record shows the approval
requirement was not actually satisfied in advance at all.

| Artifact | Default level | Rationale |
|---|---|---|
| **ADR** (`docs/ADR.md`) | Level 2 to create or accept; Level 1 only for the same correction categories reports get (formatting, broken references), and only inside an authorized unit of work | `docs/ADR.md`: "Only accepted architectural decisions are recorded here... ADRs are recorded in chronological order and are never renumbered." An ADR is a decision of record. Content changes to an existing, Accepted ADR are Level 3 if evidence contradicts the decision (see Section 6) — never a quiet edit. |
| **ARCH** (`docs/reports/ARCH-*.md`) | Level 0/1 to investigate and draft, when drafting is itself the authorized task; Level 2 for the engineer to accept its recommendation as authorizing further work | `docs/reports/README.md`: reports are historical artifacts, "not updated after completion except to: Correct factual errors. Fix broken references. Correct formatting issues... If a later investigation revisits the same topic, create a new report rather than modifying an existing one." An ARCH's *drafting* is low-risk when it's the requested task (nothing is committed to yet); an ARCH's *conclusions becoming binding* is a distinct, later, Level 2 event — related to, though not identical with, this project's separately-documented "Architecture Review" stage (that stage is specifically defined around producing an ADR or a note that none was needed; ARCH-024 itself required no ADR and went straight to a PLAN, so the correspondence is related, not exact). (Narrowed per Finding F14.) |
| **PLAN** (this session's `docs/plans/` convention) | Level 1 to draft, but only because drafting is itself the authorized unit of work when an engineer asks for a plan (Section 3); Level 2 for the engineer to approve it as the implementation authority | Newly demonstrated in this lineage, not yet in the formal taxonomy (`docs/process/engineering-handbook.md`'s Sprint Prefix Taxonomy table has no `PLAN` row, and no `PLAN-*` report existed under `docs/reports/` before this session created `docs/plans/PLAN-012B-...md`). PLAN-012B's own history is the direct precedent: the first draft was produced because the engineer explicitly asked for a plan — not unprompted — and did not become the implementation authority until the engineer reviewed it, found three issues, and approved the corrected version (Level 2). **This gap — PLAN having no registered place in the existing taxonomy or artifact-sensitivity conventions — is itself a finding this document surfaces, not a decision it resolves; formally registering the `PLAN-` prefix and its `docs/plans/` location is recommended as separate follow-up work, not settled here.** |
| **VERIFY** (currently ad hoc — no persisted report format exists yet) | Level 0, strictly | A VERIFY pass's entire value is that it is guaranteed not to have touched what it's checking — this session's own audit turn explicitly instructed itself not to modify code, and didn't. A VERIFY finding is never auto-remediated in the same pass; a fix is a new, separate action at whatever level the fix itself requires. **A second gap worth naming: unlike Investigation and (per `docs/reports/README.md`'s mandatory-Implementation-Report rule) Implementation, a VERIFY pass currently has no required persisted artifact at all** — this session's FEAT-012B verification existed only as a chat-turn report until this document's own creation gave it something to be cited from. See the compliance-gap note immediately below the table — the Implementation Report gap this points at turns out to be broader than VERIFY's own missing format. |
| **Source code** (`networkmapper/`) | Level 2 for anything in Section 5; Level 1 only for the narrow Section-4-qualifying edits inside an already-authorized change | Highest scrutiny by design — this is the running product. `docs/AI-DEVELOPMENT-GUIDE.md`'s Architecture First section: "AI should not... Introduce compatibility layers... Refactor unrelated systems... Rename public APIs... unless explicitly requested." |
| **Tests** (`tests/`) | Level 1 only for mechanical maintenance inside the authorized unit of work (F7's bounded shapes: an exact renamed symbol, an exact changed file path, a mechanical fixture update for an approved signature change); Level 2 in classification for writing a new test that encodes new behavioral assertions, with the approval requirement already satisfied wherever a PLAN specified the test precisely enough; Level 2 outright, no satisfied-in-advance exception, to delete or weaken an existing assertion | Corrected in the follow-up pass: the earlier draft treated "adding coverage for already-approved new behavior" as Level 1 across the board, which conflated mechanical maintenance with substantive new test-writing — the same classification/authorization-state distinction Section 7's preamble now states explicitly. `ENGINEERING.md`'s "fixes without tests are incomplete" establishes that writing tests is *expected*, routine work inside an approved change — it establishes that the approval requirement is satisfied, not that the classification is Level 1. Removing or loosening coverage of already-shipped behavior remains Level 2 outright, unaffected by this correction. |
| **Documentation** (`docs/process/`, `docs/architecture/`, `docs/knowledge/`, `ENGINEERING.md`, `docs/AI-DEVELOPMENT-GUIDE.md`, and this document) | Level 1 only for verified-cosmetic edits inside an already-authorized unit of work; Level 2 at minimum for anything that could change authority, interpretation, scope, thresholds, or obligations | **Precise rule (resolves Finding F6, replacing the original draft's ambiguous "floor, not ceiling" phrasing):** a cosmetic edit to an authority-defining document may remain Level 1 only when it is (a) inside an already-authorized unit of work and (b) cannot alter policy meaning under any reasonable reading. Cosmetic examples: a typo; broken Markdown; a provably stale section number; a malformed internal link. Anything semantically meaningful — a changed threshold, a reworded obligation, a broadened or narrowed example, a cross-reference edit that changes what the reference *means* rather than merely fixing where it points — is Level 2 at minimum, regardless of how small the diff looks. **An authority-defining document may never autonomously weaken this restriction**, per Section 2's self-referential floor. |

### Compliance gap identified during this review (not resolved here)

`docs/reports/README.md` makes Implementation Reports **mandatory** for
every implementation sprint. No `docs/reports/FEAT-010A`, `FEAT-011A`,
`FEAT-012A`, or `FEAT-012B` report exists anywhere in the repository — the
entire SNMP relationship-evidence lineage this document draws most of its
evidence from has not produced the artifact an already-approved document
already requires of it (Finding F8 of the DOC-001A adversarial review).
This document does not silently repair that historical gap: closing it is
out of scope for a governance-authority policy, and is recorded here as
follow-up work for a broader engineering-documentation sprint rather than
fixed in passing.

---

## 8. Default Behavior When Uncertain

When it is not obvious which level an edit belongs to, the default is to
resolve the ambiguity **upward** — toward more caution, never toward more
autonomy. Concretely:

- If unsure whether an edit is Level 1 or Level 2, treat it as Level 2:
  propose it and wait, rather than making it and reporting it afterward.
- If unsure whether a Level 2 situation is actually a Level 3 situation
  (i.e., unsure whether a confident proposal can even be constructed from
  the currently-approved artifacts), treat it as Level 3: stop and report
  rather than proposing something built on a guess.
- If unsure whether an edit falls inside the currently-authorized unit of
  work at all (Section 3), treat it as outside — report it and ask, rather
  than assuming the current task's scope stretches to cover it.
- Never resolve ambiguity by choosing whichever level requires the least
  waiting. This directly restates `docs/process/engineering-principles.md`'s
  "Stop and ask rather than guess" and `ENGINEERING.md`'s "When
  architectural uncertainty is discovered: stop, report, await direction"
  — this policy does not relax either.

This is the practical application of Section 2's "low confidence overrides
available authority" principle: a level being *available* in the abstract
for a category of edit does not mean a specific edit clears the confidence
bar required to use it. If uncertainty is only discovered *after* a Level
1 edit was already made — as opposed to before, which this section
covers — that is not resolved here; see Section 6's
retroactive-misclassification condition instead.

This default is deliberately conservative in a way that will sometimes be
wrong in the specific instance (occasionally escalating something that, in
hindsight, was obviously fine). That asymmetry is intentional: the cost of
an unnecessary question is a short delay; the cost of a wrongly-autonomous
change to the wrong category is, per Section 2's Guiding Principles,
measured by how hard it is to undo and how far it reaches — which is
exactly the axis this policy exists to protect.

---

## 9. Examples

Concrete cases, spanning the spectrum, several drawn directly from this
session's own FEAT-012B/PLAN-012B work rather than hypothesized:

| Edit | Level | Why |
|---|---|---|
| Reading ARCH-024 and the current codebase to draft PLAN-012B's first version | 0 → 1 (drafting) | Investigation is read-only (0); writing the draft down is Level 1 because drafting was itself the authorized unit of work — the engineer asked for a plan — not freestanding initiative reaching outside it. |
| The engineer finding three issues in the PLAN-012B draft and Claude correcting them | 2 | The corrected plan became the implementation authority only once the engineer explicitly approved it — this is the canonical Level 2 example in this project's own recent history. |
| Writing `SnmpBridgeFdbProvider`, its dataclasses, and its diagnostics type, per an approved PLAN | 2 in classification; approval already satisfied | Classification: Level 2 — substantive production code, runtime behavior (Section 5). Authorization state: already satisfied — the approved PLAN's own content is the Level 2 approval for implementing exactly what it specifies, so no separate propose-and-wait step was needed. Not Level 1: being inside an authorized unit of work satisfies the approval requirement; it does not reclassify substantive code as housekeeping (Section 7). |
| Writing `test_no_identity_observation_is_ever_emitted` — a new test encoding a new behavioral assertion — while implementing the approved provider | 2 in classification; approval already satisfied | **Reclassified from the original draft's "1"** during the follow-up pass that resolved the classification/authorization-state conflation: deciding what this test asserts and how to construct it is substantive work, not mechanical maintenance, even though PLAN-012B named the test and its intent in advance (Section 4). Same authorization-state analysis as the row above — satisfied by the PLAN, not a separate propose-and-wait cycle — but the same classification as the provider itself, Level 2, not Level 1. |
| Choosing `BRIDGE_FDB_TABLE_MAX_ROWS = 20_000` without a cited vendor specification | 2 in classification; approval requirement not actually satisfied in advance | Classification: Level 2 — an operational/runtime threshold, not housekeeping (Section 5), which PLAN-012B Section 5 explicitly declined to fix, unlike the provider's structure or the named tests above. **Described accurately, not smoothed into an approval narrative:** the value was chosen and disclosed in the same turn it was implemented, not proposed to the engineer and approved beforehand — no prior artifact covered this specific number the way PLAN-012B's own content covered the provider and its tests. Under this policy, this instance would not have satisfied Level 2's requirement; it is named here as a real gap between past practice and the policy being formalized, not papered over. |
| Fixing a docstring that cited "ARCH-024 Section 6" when it meant "Section 7" | 1 | Behavior-preserving reference correction with exactly one correct target — `docs/reports/README.md`'s "fix broken references" category. |
| Renumbering ARCH-024's own sections so a citation elsewhere becomes correct | 2 (or refuse) | This changes the referenced artifact itself, which is frozen per its own report-lifecycle rule — not a reference fix. |
| Noticing a stale cross-reference in an unrelated document while working on something else, with no request to look at that document at all | 2 (report, don't fix) | Outside the currently-authorized unit of work (Section 3) — even though the fix itself would otherwise be a textbook Level 1 edit, Level 1 does not license roaming outside the current task to find things to fix. |
| Fixing a typo in `stop-conditions.md` while implementing an approved FEAT that happens to touch that file | 1 | Verified-cosmetic, inside the authorized unit of work, cannot alter policy meaning — the narrow case Section 7's Documentation row allows. |
| Rewording a `stop-conditions.md` bullet "to read more clearly" | 2 | Not verified-cosmetic — rewording a governing sentence risks changing what it obligates, which Section 7's Documentation row places at Level 2 regardless of intent. |
| Discovering, mid-implementation, that real-device data shows `dot1dTpFdbTable` returns almost nothing on VLAN-segmented switches | 3 | PLAN-012B Section 6's own named stop condition — new evidence ARCH-024 didn't have, contradicting its scoping assumption. Report it; do not quietly pivot to `dot1qTpFdbTable`. |
| Discovering, after the fact, that a Level-1-classified comment edit had actually dropped a non-obvious constraint | 3 | Retroactive misclassification (Section 6, added per Finding F9) — report immediately, do not silently revert or re-fix; further action waits for engineer review. |
| Committing and pushing FEAT-012B after it was implemented, tested, and verified | 2, strict sub-case | Not autonomous even though every underlying change had already cleared its own approval — commit required its own separate, explicit "commit and push" instruction, per the explicit governance decision in Section 5. |
| Editing this Change-Authority-Policy document, after adoption, to make Level 1 cover a broader category of source-code edit | 2, floor per Section 2 | A governance document cannot expand its own grant of autonomy without engineer approval, regardless of how the edit is framed. |

---

## 10. Summary

NetworkMapper already runs on a real, working authority model — this
document's job was to find it and write it down, formalizing new policy
only where drafting it exposed a genuine, necessary gap (Section 2 names
both places this happened).

- **Level 0 (Observation):** investigate, verify, audit — never changes
  the repository.
- **Level 1 (Autonomous Housekeeping):** behavior-preserving edits, inside
  an already-authorized unit of work, whose authority is either
  self-evident (spelling, references, lint) or mechanically and uniquely
  implied by a decision that already cleared Level 2 — always reported,
  never silent, and never a license to work outside the current task.
- **Level 2 (Engineer Approval Required):** anything that changes runtime
  behavior, public surface, persistence, architecture, semantics, scope,
  or an ADR/ARCH/PLAN — proposed specifically, and executed only after
  explicit approval. Commit/push is an explicitly-resolved sub-case: it
  requires its own separate engineer authorization every time, not a
  standing one, per the governance decision in Section 5.
- **Level 3 (Stop and Escalate):** contradictions, gaps, newly surfaced
  evidence, and discovered Level 1 misclassifications that no
  currently-approved artifact resolves — report and wait, without
  proposing a way around it.

Three gaps surfaced in the course of grounding this document, named rather
than resolved here, consistent with this project's own practice of naming
an unreached decision explicitly instead of silently absorbing or ignoring
it (ARCH-024 Section 10, item 7):

1. **PLAN** has no registered place in `docs/process/engineering-handbook.md`'s
   Sprint Prefix Taxonomy or in `docs/reports/README.md`'s artifact table,
   despite now having real precedent (`docs/plans/PLAN-012B-...md`).
2. **VERIFY** has no mandatory persisted report format, unlike
   Investigation and Implementation.
3. **Implementation Reports are already mandatory** per `docs/reports/README.md`,
   and the entire FEAT-010A → FEAT-012B lineage has not produced one —
   a pre-existing compliance gap this document's own evidence-gathering
   found but did not create, and does not repair here (added per Finding
   F8; the original draft named gaps 1 and 2 but missed this sharper,
   already-existing one in the same evidence).

All three are reasonable follow-up work for a broader
engineering-documentation sprint, not decided by this document.

### Resolution status of the DOC-001A adversarial review's findings

F1 (Level 1 vs. "every level requires a signal" contradiction) and F3
(Level 1's unprompted-vs-sub-step ambiguity) are resolved together by
Section 3's authorized-unit-of-work rule, threaded through Sections 2, 4,
7, and 9. F2 (commit/push conflict resolved by interpretation rather than
decision) is resolved by Section 5's explicit governance decision. F4
(misattributed provenance of two new principles) is resolved by relabeling
both in Section 2. F5 (invented rationale attributed to
`docs/AI-DEVELOPMENT-GUIDE.md`) is resolved by labeling it explicitly as
this document's own inference. F6 (ambiguous floor/ceiling wording) is
resolved by Section 7's precise Documentation rule. F7 (unbounded inherited
authority) is resolved by Section 4's uniqueness test and bounded examples.
F8 (missed compliance gap) is now named above. F9 (no retroactive
misclassification handling) is resolved by Section 6's new stop condition.
F10 (buried composition rule) is resolved by stating it prominently in
both Section 4's header and Section 7's preamble. F11–F14 (factual/
editorial errors) are corrected in place at their original locations —
F11 and F12 in Section 5, F13 in Section 3, F14 in Section 7.

A subsequent consistency re-read of the corrected draft surfaced two
further, secondary inconsistencies — not new findings against the
original adversarial review, but defects the first correction pass's own
sharpening of Level 1 had introduced or made visible. Both are resolved
in a targeted follow-up pass: the composition rule's asymmetric "Section 7
raises, never lowers Section 4" phrasing is replaced by one rule, stated
identically in both sections (edit type, artifact sensitivity, lifecycle
state; most restrictive wins), paired with an explicit distinction between
classification and authorization state. Section 9's provider-writing,
test-writing, and `BRIDGE_FDB_TABLE_MAX_ROWS` rows were re-evaluated
against that distinction: substantive new test-writing is now classified
Level 2 (approval already satisfied), matching the provider row it sat
inconsistently beside, rather than Level 1; and the
`BRIDGE_FDB_TABLE_MAX_ROWS` row now states plainly that its approval
requirement was never actually satisfied in advance, rather than folding
it into the same "already satisfied" narrative as the other two. That
same follow-up pass also found and corrected two further stale references
to the pre-correction rule inside Section 3 itself — the "Level 1's
precise boundary" subsection's own illustrative example, and the
FEAT-012B/PLAN-012B illustration in "Alternatives considered" — both of
which still called ordinary test-writing "Level 1" after Sections 4, 7,
and 9 had already been corrected to say otherwise.

A subsequent formal verification audit of the corrected draft found five
further issues, none reopening F1–F14 or the two secondary
inconsistencies above: a Status-block sentence left stating "one
correction pass" after a second pass had already happened (Finding 1);
the "silence is not consent" principle never actually relabeled as new
despite explicit instruction to do so, and the "low confidence overrides
available authority" principle never labeled as new at all, leaving
Section 2's own count of non-preexisting principles stale (Findings 2 and
3); the commit/push resolution's provenance — that its specific wording
was engineer-directed, not decided unilaterally by Claude — left
unstated on the page (Finding 4); and this summary's own prior version
omitting the Section 3 fixes described in the paragraph immediately above
(Finding 5). All five are resolved in place, at the locations named in
each finding.

This document is a corrected draft, produced through one adversarial
review, one formal verification audit, and three correction passes, and
does not carry any authority until it is re-verified against this latest
state and explicitly approved — at which point it would itself become one
of the documents Section 2's self-referential floor protects.
