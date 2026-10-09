# Status

Investigation Complete. **Architect ruling accepted (2026-10-09).**

Implementation: Not Started

Production Code Modified: No

ADR Required: **Yes. ADR-011 Amendment 1 — Replay Observation Export**, now **applied** to `docs/ADR.md` with status Accepted. Section 5 records the draft as originally proposed, and Section 11 lists how the accepted text differs.

Architect rulings (2026-10-09):
- FEAT-OBSERVATION-JSON-EXPORT is not authorized by the ADRs as they stood before the amendment.
- Authorization is a narrow ADR-011 amendment. **No ADR-013 amendment is needed.**
- The authorized concept is a **write-once replay artifact, not project persistence**.
- `observations.json` is written **on every run** into the run output directory, with no opt-in flag.
- A read-only `python -m devtools replay-observations <run_dir>` command is authorized for the implementation.
- Raw observation artifacts are production-sensitive and must **never be committed**.

Recommended Next Sprint:
**FEAT-OBSERVATION-JSON-EXPORT**, authorized by ADR-011 Amendment 1. As the amendment requires, it needs its own approved implementation plan before any code is written. OPS-001 (`e266e2b`) stays blocked until that FEAT is implemented and verified.

Baseline: `HEAD` `e266e2b`.

---

## 1. Recommendation

FEAT-OBSERVATION-JSON-EXPORT is **not** authorized by the existing ADRs.

- **ADR-011's withholding is explicit.** Its Future Work lists "Persistence/storage format for retained observations" and "Any change to `ProjectSerializer` or existing serialization" as "explicitly deferred and … not authorized by this ADR". It also requires that each such item get "its own approved sprint and … its own updates to … `docs/ADR.md`".
- **Any replay export defines that format.** However narrow, an on-disk replay artifact is literally a storage format for retained observations.
- **ADR-013 points back to ADR-011.** It defers "Observation storage design" as "shared with ADR-011's own deferred scope".

The export *is* materially narrower than project persistence (Section 3), so it does not need a full persistence design. **It needs a narrow ADR-011 amendment** that authorizes exactly one write-once, run-scoped, replay-only artifact and leaves everything else deferred. **No ADR-013 amendment is needed:** ADR-013 defers observation storage to ADR-011, and its separate deferral of persisting *relationship interpretations* is left untouched, because the export contains observations only.

A standalone ARCH report (this one) records the investigation, but it cannot by itself override an ADR line that says "not authorized". Following ADR-013 Amendment 1's precedent, a deferred ADR item is settled by an additive amendment.

**A counter-precedent, noted honestly.** ADR-011 also deferred "Concrete observation class names, field lists, and type definitions", yet FEAT-007A implemented `IdentityObservation`/`RelationshipObservation` under ARCH-017 without an ADR update. The precedent is therefore inconsistent. An on-disk format is different in kind from in-memory types, though: it is an external, longer-lived contract that later code and later readers depend on. The cautious path is the amendment.

---

## 2. Direct Answers

**1. Do ADR-011 or ADR-013 forbid all observation persistence, or only project persistence and serializer integration?**
Neither *forbids* persistence. Both *withhold authorization* for it pending a separate decision.
- **ADR-011** says "Persistence strategy is not yet decided by this ADR" (Consequences), and defers the storage format and any `ProjectSerializer` change (Future Work).
- **ADR-013** defers "Persistence strategy for relationship interpretations or observations", "Any serialization change" and "Observation storage design".

The deferral covers **any** observation storage format, not only `.nmproj` or serializer integration. A separate export file is still inside it.

**2. Is a write-once replay artifact materially different from adding observations to the `.nmproj` project model?**
**Yes, in architecture. No, in authorization.** The comparison is in Section 3. Briefly, the export:
- is never read back into `Project`;
- creates no cross-run store;
- assigns no observation identifiers;
- involves no retention policy;
- leaves `.nmproj` and `ProjectSerializer` unchanged.

These differences justify a *narrow* amendment instead of a persistence design. They do not remove the need for authorization.

**3. What is the narrowest acceptable scope?** One versioned JSON file per run, written to the run's report directory, containing every observation in `Project.observations` with full provenance. Also one loader that returns observation objects **only** to a replay function, which re-runs the committed resolvers. No other consumer. (Section 4.)

**4. Which authorization path?** **ADR-011 Amendment 1.** No ADR-013 amendment and no further ARCH report beyond this one. (Section 1.)

**5. What must be excluded?** See Section 6.

**6. What replay guarantees must the artifact provide?** See Section 7. In short: a lossless round trip, the multiset of observations preserved, exact timestamp and timezone fidelity, and exact reproduction of `canonical_identities` and `canonical_relationships`.

**7. What sanitization applies?** The artifact *is* a raw production artifact. It is never committed (architect ruling D4, as recorded in OPS-001). Tests and fixtures use only synthetic, documentation-reserved values. (Section 8.)

---

## 3. Export Compared With Project Persistence

| Property | `.nmproj` project persistence (deferred) | Replay observation export (proposed) |
|---|---|---|
| Loaded back into `Project` / normal workflow | Yes (that is its purpose) | **No.** Only a replay function reads it. |
| Changes the `.nmproj` schema or `ProjectSerializer` | Yes | **No** |
| Cross-run store or accumulation | Implied (cross-run corroboration, ARCH-017) | **No.** One file per run, never merged. |
| Observation identifiers | Needed | **None.** Observations are value objects. |
| Retention policy | Needed | **None.** The file sits beside the run's other report artifacts. |
| Persists interpretations (canonical records) | Open question (ARCH-019 kept them unpersisted) | **No.** Observations only. |
| Mutability | Rewritten on save | **Write-once** |
| Consumers | Every later run | Replay and verification only |

---

## 4. Narrowest Acceptable Scope

1. **Artifact.** `observations.json`, written once per run into the run's report directory (`output/<YYYY-MM-DD_HHMMSS>_<profile>/`), beside `report.md`, `devices.csv` and `relationships.csv`.
2. **Content.** Every element of `Project.observations`, both `IdentityObservation` and `RelationshipObservation`, including relationship observations whose endpoints never resolve. **Duplicates are kept.**
3. **Per-observation fields, all verbatim:**
   - the type discriminator;
   - `subject`;
   - `property_name` and `value` (identity), or `related_subject` and `category` (relationship);
   - `provenance.provider`, `provenance.collection_method`, `provenance.source_run`;
   - `provenance.observed_at` as `datetime.isoformat()`, preserving naive or aware exactly (Section 7).
4. **Envelope:** `{"format": "networkmapper.retained-observations", "format_version": 1, "observations": [...]}`. **No wall-clock or host fields** in the file, so that identical observation sets produce identical bytes.
5. **Determinism.** Observations are sorted by a total key over all fields, and serialized with sorted keys, a fixed separator style and UTF-8. The resolvers are order-independent (ADR-012/013), so sorting does not affect replay.
6. **Writer.** A read-only exporter consuming `Project.observations` (ADR-005: exporters are read-only consumers), invoked by `Application.run()` with the other report exporters. `ReportRunPaths` gains one path.
7. **Loader and replay.** One loader that reconstructs the frozen observation objects, and one replay function that feeds them to the committed `IdentityResolver` and `RelationshipResolver`. The loader never constructs a `Project`.

---

## 5. Draft: ADR-011 Amendment 1 (as originally proposed; superseded)

> **Superseded by the accepted text in `docs/ADR.md`** (ADR-011, Amendment 1 — Replay Observation Export). The draft below is kept as the investigation record. Section 11 lists how the accepted text differs.

The accepted amendment was appended after ADR-011's Future Work section, with a one-line "Amended by" pointer under ADR-011's Status line, following the ADR-013 Amendment 1 precedent. No existing ADR-011 text changed.

```markdown
### Amendment 1 — Replay Observation Export

**Status:** Proposed

**Date:** <date of acceptance>

**Source:** ARCH-028 (Observation JSON Export Authorization); OPS-001.

**Nature:** This amendment adds to ADR-011. It replaces nothing. Every
section above remains in force exactly as written. It narrowly settles
part of one deferred Future Work item, "Persistence/storage format for
retained observations", for one purpose only. All other deferred items,
including the full persistence and storage design, remain deferred.

#### Context

Retained observations exist only for the duration of one run. Canonical
identities and relationships are interpretations (ADR-012, ADR-013); the
CSV and Markdown reports contain those interpretations and, for
relationships, only observations whose endpoints resolved. Observations
excluded at the relationship resolver's endpoint gate, together with
their `source_run` and full-precision `observed_at`, are lost when the
run ends. Evidence collected from a production network therefore cannot
be re-interpreted later — for example, by a corrected resolver — which
contradicts this ADR's premise that interpretations change while
retained observations do not. OPS-001 is blocked on exactly this gap.

#### Decision

1. **A replay observation export is authorized.** A run may write its
   retained observations to one versioned, write-once file in that run's
   report output directory. The file's sole purpose is replay: re-running
   the committed identity and relationship resolvers against exactly the
   evidence that run collected.

2. **The export is lossless.** It contains every retained observation of
   the run — including relationship observations whose endpoints never
   resolved, and duplicate observations — with every observation field
   and the complete provenance this ADR requires (provider, collection
   method, observation timestamp, source/run identity), recorded
   verbatim. Timestamps keep their exact value and their presence or
   absence of timezone information.

3. **The export is deterministic and versioned.** The same set of
   retained observations always produces the same file. The file carries
   an explicit format identifier and version, and contains no wall-clock,
   host, or credential data of its own.

4. **Replay is the only consumer.** The file may be read only to
   reconstruct observations and re-run resolvers for replay and
   verification. Replaying the file must reproduce the run's canonical
   identities and canonical relationships exactly.

#### Boundaries

This amendment does not authorize, and the following remain deferred
exactly as in Future Work above:

- any change to the `.nmproj` project format or to `ProjectSerializer`;
- loading observations into a `Project` or into any normal run, report,
  or comparison workflow;
- any cross-run observation store, accumulation, or merging, and
  therefore cross-run corroboration;
- observation identifiers and how they are assigned;
- retention policies;
- any database or event-store design;
- persistence of canonical identities or relationships (interpretations).

Providers, observation types, resolvers, classification, and the
existing CSV and Markdown reports are unchanged by this amendment.

#### Relationship to ADR-013

ADR-013's Future Work defers observation storage as shared with this
ADR's deferred scope. This amendment is that decision, for the replay
export only. ADR-013's separate deferral of persisting relationship
*interpretations* is unaffected: the export contains observations only.

#### Data Handling

The export is a raw production artifact: it contains discovery-time
subjects and identity values exactly as observed. It is written only
beneath the run's output directory and is never committed to the
repository. Credentials are never observations and never appear in it.

#### Authorization

This amendment authorizes one implementation sprint,
**observation JSON export**, limited to: the writer, invoked once per
run alongside the existing report exporters; one additional report-run
artifact path; a loader that reconstructs observations for replay only;
a replay function that re-runs the committed resolvers; and tests
proving a lossless round trip, determinism, exact replay, and absence of
credentials.

#### Consequences

- Production evidence becomes re-interpretable: any future resolver can
  be replayed against a past run's exact retained observations.
- OPS-001 can be unblocked once the authorized sprint is implemented and
  verified.
- The export format becomes a versioned contract; a breaking change
  requires a new format version.
- Full observation persistence remains undecided and requires its own
  approved decision.
```

---

## 6. Explicit Exclusions (scope-creep guard)

- **No project format changes.** No `.nmproj` schema change and no `ProjectSerializer` change.
- **No reading observations back into a workflow.** The file is never read into `Project`, `Application.run()`, reports, `ProjectComparator`, the workbench or benchmarks.
- **No cross-run behavior.** No merging across runs, no cross-run corroboration, no observation identifiers, no retention policy.
- **No persisted interpretations.** Canonical identities and relationships are not exported. They are reproduced by replay.
- **No behavior changes.** Providers, observation types, `IdentityResolver`, `RelationshipResolver`, the cardinality policy, classification, `devices.csv`, `relationships.csv` and `report.md` are all unchanged.
- **No credentials or run metadata in the file.** Credentials never appear in it, and neither does any field added "for convenience" (scan targets, hostnames of the scanner, operator), which would break determinism and D4.
- **No gateway inference, topology behavior or heuristic enrichment.**
- **No new CLI scan flags.** The export is always written alongside the other report artifacts. A developer replay command (Section 9, item 6) is optional and limited to developer tooling.

---

## 7. Replay Guarantees

The FEAT's tests must prove each of these:

1. **Lossless round trip.** `load(export(obs))` equals `obs` as a **multiset**. Every field is equal, duplicates are preserved, and nothing is added or dropped.
2. **Timestamp fidelity.** `observed_at` round-trips exactly, with microseconds, and naive values stay naive while aware values stay aware with the same offset. This matters because providers stamp naive `datetime.now()` today, and the resolver's D6 sort compares `observed_at.isoformat()`.
3. **Opaque provenance preserved.** `source_run` (a fresh `uuid4` per provider invocation today) and `collection_method` are preserved byte for byte.
4. **Exact replay.** For any observation set, `IdentityResolver().resolve(loaded)` equals the run's `canonical_identities`, and `RelationshipResolver().resolve(loaded, identities)` equals the run's `canonical_relationships`. This includes observations with unresolved endpoints and every cardinality and state case.
5. **Determinism.** The same observation multiset, in any input order, produces byte-identical files.
6. **Version enforcement.** The loader rejects an unknown `format` or an unsupported `format_version` explicitly, never silently.
7. **Completeness of types.** The loader rejects an unknown observation type explicitly, so a future observation type cannot be silently dropped from replay.
8. **No credential leakage.** A test drives an SNMP provider with a sentinel community string through to the export and asserts the sentinel is absent from the file.

---

## 8. Sanitization Rules

- **The artifact is never committed.** `observations.json` is a raw production artifact and stays under gitignored `output/` (OPS-001 §11; architect ruling D4).
- **Test fixtures are synthetic only.** Use documentation-reserved address ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), synthetic MACs and placeholder hostnames. No production-derived value may appear in any test, fixture or golden file.
- **Committed reports** about export-based replay (VER and OPS results) follow D4: aggregate counts, provider names, relationship categories and sanitized stable host IDs only.
- **Credentials** are covered by Section 7, guarantee 8, and by OPS-001's leak scan, which already includes the export.

---

## 9. Proposed Implementation Plan (after the amendment is accepted)

**FEAT-OBSERVATION-JSON-EXPORT**, to be formalized as PLAN-029:

| # | Change | File |
|---|---|---|
| 1 | Serializer and loader functions (`export_observations` / `load_observations`), the format constants, the total sort key, and ISO timestamp handling | new `networkmapper/observations/replay_export.py` |
| 2 | A read-only exporter writing `project.observations` to a path (ADR-005 pattern) | new `networkmapper/exporters/observation_json_exporter.py` |
| 3 | Add `observations_json_path` (`<run>/observations.json`) | `networkmapper/reporting/report_run.py` |
| 4 | Invoke the exporter with the other report exporters, and print its path | `networkmapper/application.py` (wiring only) |
| 5 | A replay function: load, then `IdentityResolver`, then `RelationshipResolver`; returns the canonical tuples | in item 1's module, or `networkmapper/observations/replay.py` |
| 6 | A read-only developer command, `python -m devtools replay-observations <run_dir>`, that replays the run's `observations.json` and compares the result with the run's `relationships.csv` (subject, category, related subject, state). **Authorized by the architect ruling and ADR-011 Amendment 1.** It gives OPS-001 step 9 its concrete command. | `devtools/` |
| 7 | Tests for Section 7, guarantees 1–8, plus `report_run` and `application` wiring tests | new `tests/test_observation_json_export.py`; updates to `tests/test_report_run.py`, `tests/test_application_cli.py` |

**Validation gate:**
- `python -m pytest tests/ -q` passes;
- `python -m devtools validate --all` passes with all benchmarks at 100% (benchmarks do not touch observations, ARCH-017);
- a **VER report** is written.

After that, OPS-001 §6 (steps 5 and 9) is updated with the real artifact name and replay command, and OPS-001 is resubmitted.

**Risks:**
- **R1: file size.** Large forwarding and ARP tables could make the export large. It is acceptable: it is local and gitignored. Measuring it is an OPS-001 reporting item.
- **R2: format becomes a contract.** Mitigated by `format_version` and explicit rejection of unknown versions.
- **R3: scope creep toward persistence.** Mitigated by the amendment's Boundaries list and by a test asserting that `ProjectSerializer` output is byte-identical before and after this change.

---

## 10. Questions Resolved by the Architect Ruling (2026-10-09)

1. **Amendment.** Accepted as a narrow ADR-011 amendment, with no ADR-013 amendment. Applied to `docs/ADR.md`.
2. **Developer replay command.** Included: `python -m devtools replay-observations <run_dir>`, read-only.
3. **Opt-in flag.** None. `observations.json` is written on every run into the run output directory.

## 11. Accepted Text Compared With the Section 5 Draft

The accepted ADR-011 Amendment 1 keeps the draft's structure (Context, Decision, Boundaries, Relationship to ADR-013, Data Handling, Authorization, Consequences) and makes these changes from the ruling:

- **Status:** Accepted, dated 2026-10-09, rather than Proposed.
- **Every run:** the artifact is named `observations.json` and is written on every run, not behind an opt-in flag.
- **Exporter as its own decision:** the read-only exporter is now a separate decision point (ADR-005).
- **Exact fidelity spelled out:** exact `observed_at` round trip (sub-second precision and timezone presence) and exact `source_run` round trip are written as explicit requirements.
- **Rejection rule added:** unknown format identifier, version or observation type must be rejected and never silently skipped (a new decision point).
- **Devtools command authorized:** the read-only `python -m devtools replay-observations <run_dir>` command is part of the authorized replay path and of the sprint's scope.
- **Credential rule:** credentials must never appear in the artifact, and this must be tested directly (a separate decision point).
- **Boundaries expanded:** they now cover workbench and benchmark workflows, a long-term evidence database, changes to existing report behavior, gateway inference, topology behavior, and committed raw production artifacts.
- **Plan required:** the authorized sprint must have its own approved implementation plan and verification before OPS-001 may be unblocked.
