# Status

Architecture Decision Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: This Sprint — recorded as ADR-009 in
[docs/ADR.md](../ADR.md).

Recommended Next Sprint:
FEAT-003C – Per-Service Discovery Evidence Implementation

---

# Executive Summary

This sprint drafted and recorded ADR-009 — Per-Service Discovery Evidence
Is a Correlated Record, formalizing the decision ARCH-002A's architecture
review recommended: per-service discovery evidence is represented as a
list of explicitly named, typed records on `Device` (one record per
observed open port, correlating port, protocol, and available
service/product/version evidence), replacing the current independent
`open_ports`/`detected_services` lists as the representation for that
category of evidence. A generic, untyped metadata dictionary was
evaluated and rejected as the record's shape.

The ADR is appended to `docs/ADR.md` as ADR-009, following the project's
established single-file, chronological ADR convention (see Report
Corrections below). It does not modify ADR-001, ADR-002, ADR-003, ADR-004,
or ADR-008 — it extends ADR-008 into the specific area that ADR explicitly
deferred, and leaves the other four untouched because nothing about the
classification contract, evidence API, or two-phase discovery structure
changes.

No production code, tests, benchmarks, or the `Device` model were
modified. FEAT-003C is now unblocked to proceed with implementation
against a settled architectural principle, with specific implementation
decisions (exact field set, migration sequencing, whether
`open_ports`/`detected_services` are removed or retained transitionally)
explicitly deferred to that sprint.

---

# Report Corrections

Two discrepancies between this sprint's instructions and established
repository convention were found and corrected rather than treated as
blockers, consistent with this project's practice of reporting deviations
rather than silently complying with or silently overriding them:

1. **ADR location.** The sprint instructions specify creating the ADR
   "under `docs/architecture/`." The repository's actual, unbroken
   convention — confirmed by reading `docs/ADR.md` directly — is a single
   cumulative file containing all eight prior ADRs in chronological order
   ("ADRs are recorded in chronological order and are never renumbered,"
   `docs/ADR.md:16`). No per-decision ADR files exist anywhere in the
   repository; `docs/architecture/` contains architecture *narrative*
   documents (`overview.md`, `classification.md`), not ADRs. This ADR was
   appended to `docs/ADR.md` as ADR-009 rather than created as a new file
   under `docs/architecture/`, to preserve the single-source-of-truth
   convention the project has used without exception since ADR-001.

2. **Sprint ID collision.** This sprint's instructions title it
   "ARCH-002A," matching the sprint ID already used by the completed
   Architecture Review
   ([ARCH-002A-Per-Service-Discovery-Evidence-Architecture-Review.md](ARCH-002A-Per-Service-Discovery-Evidence-Architecture-Review.md)).
   Both that report and FEAT-003B's own recommendation named this
   follow-on ADR sprint "ARCH-002B." This report and its filename use
   `ARCH-002B` to avoid reusing an already-claimed sprint ID and to match
   the ID both predecessor reports already committed to.

Neither correction changed the substance of the work requested; both were
naming/location conventions, applied for consistency with the existing
report and ADR history.

---

# Investigation

This sprint did not reopen FEAT-003A, FEAT-003B, or ARCH-002A's settled
findings, per this sprint's own instruction not to revisit previously-
settled questions without new repository evidence. No new repository
evidence was found that would require doing so. The ADR's Context and
Alternatives Considered sections restate, rather than re-derive, the
evidence already established:

- `NmapProvider._extract_detected_services()` discards `-sV` product/
  version/CPE data (FEAT-003A).
- `open_ports` and `detected_services` are independent, positionally
  uncorrelated lists with no code anywhere joining them (FEAT-003B).
- No generic metadata-dictionary pattern exists anywhere in the current
  codebase (ARCH-002A).
- `Project` and `NetworkGraph` already demonstrate nested dataclass
  composition, which the recommended record extends rather than
  introduces (ARCH-002A).

One additional cross-check was performed for this sprint specifically: a
repository search confirmed no ADR-009 (or any ADR beyond ADR-008)
existed prior to this sprint, and no file under `docs/architecture/`
follows an ADR format — both checks needed to resolve the two corrections
above before drafting.

---

# Findings

The seven questions this sprint's scope required the ADR to answer are
addressed directly in ADR-009's own sections:

| Question | Where answered in ADR-009 |
|---|---|
| Canonical representation of a discovered network service | Decision |
| Why the parallel-list model is insufficient | Context |
| Architecture selected | Decision |
| Alternatives considered | Alternatives Considered |
| Why alternatives were rejected | Alternatives Considered |
| Alignment with existing ADRs | Rationale |
| Implementation work intentionally deferred | Future Work |

No question required new investigation beyond what FEAT-003A, FEAT-003B,
and ARCH-002A had already established; this sprint's work was recording
the decision, not discovering it.

---

# Recommendations

Proceed to **FEAT-003C — Per-Service Discovery Evidence Implementation**.
ADR-009 provides the architectural boundary FEAT-003C needs to proceed
without further design decisions about *representation*: a named, typed,
per-port record, not a generic dictionary, not parallel lists. FEAT-003C's
own investigation phase should still resolve the implementation questions
ADR-009 explicitly left open (exact field set, migration sequencing for
the 8 existing classification rules, whether the pre-existing
`open_ports`/`detected_services` persistence gap is closed in the same
sprint) — those are implementation decisions, not architectural ones, and
were intentionally kept out of this ADR.

---

# Risks

- **Deferred-scope creep.** ADR-009's Future Work section lists five
  explicitly deferred items (exact field set, list-retention decision,
  migration of five consuming modules, NSE-script collection work, and
  the persistence-gap fix). FEAT-003C should treat each as a decision to
  make deliberately, not as implicitly pre-approved simply because this
  ADR named it as future work.
- **Convention corrections.** The two corrections in this report (ADR
  location, sprint ID) were judgment calls made to preserve existing
  repository conventions rather than introduce new ones. If either
  correction is not what was intended, the affected artifact (ADR-009 in
  `docs/ADR.md`, or this report's filename) can be relocated without
  content changes.

---

# Assumptions

- FEAT-003A's and FEAT-003B's evidence remains current — no production
  code changed between those investigations and this sprint that would
  invalidate their findings.
- "This Sprint" in the Status block's `ADR Required` field is read as
  "the ADR this sprint was scoped to produce has been recorded," matching
  this sprint's Architecture Decision Complete status.

---

# ADR Considerations

ADR-009 — Per-Service Discovery Evidence Is a Correlated Record — has
been recorded in [docs/ADR.md](../ADR.md), immediately following ADR-008.
It is additive: no existing ADR (001–008) was revised, renumbered, or
reopened. Per `docs/ADR.md`'s own stated convention, ADRs are never
renumbered, and this sprint preserved that.
