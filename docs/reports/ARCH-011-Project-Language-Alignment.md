# Status

Investigation Complete

Implementation: Completed

Production Code Modified: No

ADR Required: No — this sprint reviews and corrects human-facing wording
and documentation navigation. It does not change behavior, architecture,
or any production class, module, or API.

Recommended Next Sprint:
No single sprint is pre-selected. Two follow-ups surfaced during this
review are recommended but out of scope here — see Risk Assessment: a
policy-consistency fix to `docs/AI-DEVELOPMENT-GUIDE.md`'s Safe Commands
list, and a rebuild of `docs/classification-rules.md` as an accurate,
current rule catalog.

---

## Summary

NetworkMapper's human-facing documentation was already substantially
aligned with the project's evidence-driven, technician-first philosophy
before this sprint — README.md, ROADMAP.md, ENGINEERING.md, `docs/ADR.md`,
`docs/architecture/`, `docs/knowledge/`, `docs/process/`, the CLI output in
`networkmapper/application.py`/`cli_renderer.py`, and the generated
Markdown report in `markdown_exporter.py` all already use consistent,
concise, non-marketing language, including the deliberate, repeated
"NetworkMapper is not simply a network scanner" framing. This is the
expected result of prior sprints (REPORT-001, ARCH-001B, KNOW-001/002)
that already did this kind of alignment work for their respective areas.

Given that, this sprint's real findings are narrower than the objective
implied: not scattered bad word choices, but two concrete, low-risk gaps
where documentation had drifted from what the project actually is —
1. README.md's "Planned Features" list still claimed several
   already-delivered capabilities as future work.
2. Both README.md's and `docs/README.md`'s documentation indexes omitted
   `docs/knowledge/`, `docs/process/`, and (in `docs/README.md`) most of
   `docs/architecture/`, despite these being current, actively-referenced,
   "living" documents per `docs/reports/README.md`'s own classification.

A third finding — `docs/classification-rules.md` describes one rule in a
pre-`RuleResult` format and is not a current rule catalog — was corrected
with a signpost to the canonical architecture doc rather than rewritten,
since rebuilding it is a content-authoring task beyond this sprint's
language-alignment scope.

Several terminology pairs the objective flagged as examples (Scan vs.
Evidence Collection, Detect vs. Identify, Data vs. Evidence) were
investigated and found to already be used correctly and consistently;
no changes were made where none were warranted. See Terminology
Decisions.

## Files Changed

- `README.md` — trimmed "Planned Features" to remove items already listed
  under "Current Capabilities" a few sections above (automatic discovery,
  Nmap host detection, device inventory export, offline operation); added
  a pointer to ROADMAP.md as the authoritative backlog; added
  `docs/knowledge/`, `docs/process/`, `docs/reports/` to the Documentation
  table.
- `docs/README.md` — added entries for `docs/architecture/`, `docs/ADR.md`,
  `docs/process/`, `docs/knowledge/`, `docs/reports/`; updated the
  Recommended Reading Order and Documentation Philosophy table to point at
  the current, maintained documents; marked `ARCHITECTURE.md`,
  `classification-rules.md`, and `field-notes.md` explicitly as
  earlier-generation documents kept for historical narrative.
- `docs/classification-rules.md` — added a top-of-file note clarifying the
  document predates the `RuleResult`/evidence architecture, is not a
  current rule catalog, and pointing to
  `docs/architecture/classification.md` and
  `networkmapper/classification/rules/` instead.

No production code, tests, CLI output, generated report headings, ADRs,
`docs/architecture/`, `docs/knowledge/`, or `docs/process/` content
required changes — see Investigation below for why.

---

## Investigation

Reviewed for language and terminology, by area:

- **README.md, ROADMAP.md, ENGINEERING.md** — already carry the intended
  identity consistently ("not simply a network scanner," "discovery
  gathers facts, classification interprets them," technician-first
  framing). No edits needed beyond the two Files Changed above.
- **`docs/ADR.md`** — nine ADRs, consistent terminology throughout
  (Discovery vs. Interpretation is itself the subject of ADR-008).
  No edits needed.
- **`docs/architecture/`** (`README.md`, `overview.md`, `classification.md`)
  — current, actively maintained, precise. No edits needed.
- **`docs/knowledge/`** (`README.md`, `FIELD-OBSERVATIONS.md`,
  `KNOWLEDGE-LIFECYCLE.md`) — current, precise, deliberately distinguishes
  "raw scan result," "Knowledge," and "classification rule." No edits
  needed.
- **`docs/process/`** (engineering handbook, principles, roles, stop
  conditions, validation workflow, prompt templates) — this *is* the
  sprint-template material the objective asked about. Already concise,
  technician/engineer-voiced, no marketing language. No edits needed.
- **CLI messages** — `networkmapper/application.py`,
  `networkmapper/runtime/cli_renderer.py`, `networkmapper/runtime/events.py`,
  `devtools/__main__.py` — all print plain, technician-facing status text
  ("Host Discovery," "Classification Summary," "Discovery Diagnostics").
  No edits needed.
- **Report headings** — `networkmapper/exporters/markdown_exporter.py`
  (the actual customer-facing generated report) uses exactly the
  vocabulary this sprint asked for: Identity / Evidence / Classification
  per device, "No rule matched" instead of any guessed fallback. This was
  REPORT-001's deliverable and needs no further changes.
- **`docs/README.md`, README.md's Documentation table,
  `docs/classification-rules.md`** — the three files edited; see Files
  Changed.
- **`docs/reports/`** — deliberately excluded from this review.
  `docs/reports/README.md` defines these as historical, non-living
  artifacts that are only ever corrected for factual errors, broken
  references, or formatting — not restyled. Dozens of reports use "scan
  profile" and other phrasing that reads slightly informal by today's
  standard; that is expected and correct given their own stated lifecycle,
  not a defect this sprint should fix.

---

## Terminology Decisions

**Scan vs. Discovery/Evidence Collection.** "Scan" is precise and correct
when referring to the literal Nmap operation and its FAST/STANDARD/DEEP
depth setting (`ScanProfile`, "Scan Profile" in CLI/report output —
42 occurrences across code, tests, and reports vs. 4 informal "discovery
profile" mentions in report titles). This is not legacy scanner-centric
language; it is the accurate name for a real, literal scan. It was
investigated as a candidate rename and rejected — see Risk Assessment.
"Discovery" is the correct term one level up: the overall process of
finding and evidencing a network, of which the Nmap scan is one
provider's implementation. The product is never described as "a
scanner"; the operation it performs is accurately called a scan.

**Data vs. Evidence.** "Evidence" is used, correctly, wherever information
supports or explains a classification decision (`RuleResult.reason`,
`ServiceEvidence`, "Discovery Evidence," ADR-008/ADR-009). "Data" remains
appropriate for neutral, pre-interpretation payloads with no evidentiary
claim attached (JSON project serialization, benchmark dataset, dependency
table). No change needed; the distinction is already applied correctly
throughout.

**Classification vs. Interpretation.** "Classification" names the current
mechanism (`DeviceClassifier`, `RuleResult`, ordered rules).
"Interpretation" is ADR-008's broader architectural term for any
conclusion drawn from discovery, of which classification is currently the
only implementation. Documentation already keeps this distinction
straight; no change needed.

**Detect vs. Identify vs. Guess.** "Detect" is used correctly for literal,
deterministic technical detection (open ports, services, configuration
drift) performed by a tool. "Identify" is used for what NetworkMapper
does to a device end-to-end. "Guess" appears exactly once, in
`engineering-principles.md`, used correctly in the negative ("stop and ask
rather than guess"). `ProgressMeasurement` (runtime/events.py) explicitly
documents that it is "never an estimate." No change needed.

**"Not simply a network scanner."** Confirmed as a deliberate, repeated
identity statement (README.md, ROADMAP.md, ENGINEERING.md), not filler.
Retained verbatim everywhere it appears.

---

## Project Style Guide

A short vocabulary for future contributors, distilled from the decisions
above and from what the codebase already does consistently:

1. **Discovery** finds devices and gathers evidence about them. **Scan**
   is a specific, literal operation one discovery provider (Nmap)
   performs — use it only at that level of specificity, never as a
   synonym for the product or for discovery as a whole.
2. **Evidence** is anything that supports or explains a conclusion
   (a classification, a report line, a diagnostic). **Data** is neutral
   storage/transport with no evidentiary claim. If a sentence is
   explaining *why* something is true, it's evidence.
3. **Classification** is the deterministic, rule-ordered mechanism that
   exists today. **Interpretation** is the broader architectural category
   (ADR-008) that classification currently fully implements. Use
   "classification" unless deliberately speaking at ADR-008's level.
4. Never describe an unclassified or missing result as a **guess**.
   Say what's actually true: "no rule matched," "not determined," "no
   evidence collected." NetworkMapper explains absence of information
   rather than papering over it.
5. Report and CLI headings are short, plain nouns (Identity, Evidence,
   Classification, Discovery Diagnostics) — not sentences, not
   marketing taglines.
6. "NetworkMapper is not simply a network scanner" is a fixed identity
   statement. Don't paraphrase it; reuse it.
7. When two documents could describe the same thing, one must be
   canonical and the other must say so explicitly (see `docs/architecture/`
   vs. `docs/ARCHITECTURE.md`, and the correction applied to
   `docs/classification-rules.md` this sprint). Silence about which one
   is current is itself a language-clarity defect.

---

## Mission Statement

NetworkMapper already has one, stated in `ENGINEERING.md`'s opening lines,
and it does not need replacing:

> NetworkMapper exists to reduce the time, effort, and uncertainty
> required to understand an undocumented network. Every architectural and
> implementation decision should support that mission.

Paired with README.md's framing of the same idea in technician terms:

> Walk into an unfamiliar network and leave with documentation that didn't
> exist when you arrived.

These two sentences are consistent, already load-bearing (cited across
ROADMAP.md, ENGINEERING.md, and multiple ADRs), and satisfy this sprint's
own bar — technician-oriented, concise, no marketing language. Introducing
a third, competing mission statement would itself be a language-alignment
regression. Recommendation: treat the `ENGINEERING.md` sentence as the
canonical mission statement and the README.md sentence as its
technician-facing restatement; no new text needed.

---

## Examples of Improved Language

**README.md — Planned Features (before):**
```
- Automatic network discovery
- Nmap-based host detection
- Device identification
- Network relationship mapping
- Draw.io topology generation
- Device inventory export
- Change detection between scans
- Professional documentation package generation
- Offline operation
- Portable Windows executable
```

**README.md — Planned Features (after):**
```
- Full network relationship mapping (beyond today's inventory-level NetworkGraph)
- Draw.io topology generation
- Change detection between runs
- Professional documentation package generation
- Portable Windows executable

See ROADMAP.md for the complete, current backlog. The list above is a
short summary, not a duplicate source of truth — automatic discovery,
Nmap host detection, device inventory export, and offline operation
already appear under Current Capabilities above and are intentionally
not repeated here.
```
Four items were removed because they contradicted the "Current
Capabilities" section a few dozen lines above the one being edited — the
same document claiming a capability was both done and not-yet-done. This
is the clearest instance found of documentation "reflecting earlier
assumptions" in the sense the sprint objective described.

**`docs/classification-rules.md` (before):** opened directly with `## Rule
12`, presenting a single rule in `If / Then / Confidence / Reason`
pseudo-code with no context that this predates the current architecture.

**`docs/classification-rules.md` (after):** opens with an explicit note
that the file is historical, is not a current catalog, and names the
document that is current (`docs/architecture/classification.md`) and the
directory that is authoritative (`networkmapper/classification/rules/`).

---

## Risk Assessment

**Low risk — applied this sprint.** All three edits are additive or
corrective prose in living documentation: no renames, no restructuring,
no behavior change, no production code touched. Worst case if reverted:
documentation indexes are incomplete again, which is the pre-existing
state.

**Investigated and deliberately not changed — `ScanProfile`.** The class
`ScanProfile` (`networkmapper/discovery/scan_profile.py`), the CLI flag
`--scan-profile`, the printed labels "Scan Profile," and matching test
file names are consistent with each other and are the dominant term
project-wide (42 occurrences vs. 4 informal "discovery profile" mentions
confined to report titles). Renaming this would touch a public CLI flag
and a production enum across many files and tests for a rename this
review does not think is justified — "scan" is the accurate word for what
literally happens. This is exactly the "use judgment, don't mechanically
replace words" case the sprint objective warned about.

**Flagged, not fixed — `docs/AI-DEVELOPMENT-GUIDE.md` Safe Commands list.**
This document's "Safe Commands" section lists `git commit` and `git push`
as commands to "normally approve." That directly contradicts the current,
more authoritative policy in `docs/process/sprint-lifecycle.md` ("Commit
is a distinct, human-triggered step. AI assistants do not commit on their
own initiative") and `engineering-principles.md` ("Human approval before
commit"). This is a governance/safety inconsistency, not a wording
inconsistency, and correcting it changes what an AI assistant is told is
permitted — that deserves its own explicitly scoped, human-reviewed
sprint rather than being folded into a language-alignment pass. Recorded
here so it isn't lost.

**Flagged, not fixed — `docs/classification-rules.md` content gap.** Its
own header now says it's not a current catalog, but the underlying gap
(no document currently lists NetworkMapper's actual ~9 classification
rules in one place, in the current `RuleResult` format) is unresolved.
Rebuilding it is a content-authoring task, not a language-alignment edit,
and is recommended as its own sprint.

**Scope discipline.** `docs/reports/` (dozens of files) was intentionally
excluded per that directory's own documented lifecycle policy
(historical, corrected only for factual/reference/formatting errors, never
restyled). Restyling them would have been the largest, lowest-value, and
explicitly-against-policy way to inflate this sprint's diff.
