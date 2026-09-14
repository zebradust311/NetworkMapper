# Status

Plan Proposed — Pending Review

Approval: Not yet architect-reviewed. Written as investigation authority in the style PLAN-025/PLAN-026 established. Do not implement against this plan until it is approved.

Authority: [ARCH-025](../reports/ARCH-025-Canonical-Identity-Relationship-Presentation-Architecture.md) Section 8 ("Multi-Format Semantics"), and [PLAN-026](PLAN-026-Canonical-CSV-Presentation-Implementation.md) Section 4 ("Slice 2 — Designed, Implementation Deferred"), which fully specified this artifact's schema, one-row semantics, and ordering but explicitly deferred its implementation because producing a new report artifact requires touching `report_run.py` and `application.py` — a broader-touching class of change than PLAN-026's own single-file Slice 1. This plan re-grounds PLAN-026 Section 4's design directly against the current codebase (`canonical_presentation.py`, `markdown_exporter.py`, `csv_exporter.py`, `report_run.py`, `application.py`, `test_csv_exporter.py`, `test_report_run.py`, `test_application_cli.py`) and resolves the design questions PLAN-026 Section 4.2/8 left open (provenance representation, exact column semantics), so that a follow-on FEAT can implement without re-investigating.

Implements: The fourth item of ARCH-025 Section 17's sequence and the remainder of PLAN-026 Section 1's two-part split — "a separate relationship CSV artifact," the item PLAN-026 designed in full (its own Section 4) but explicitly did not build (PLAN-026 Section 1: "Slice 2... implementation deferred to a follow-on plan").

Production Code Modified: No. This is a planning sprint only; no source or test files are changed by this plan.

New ADR Required: No (Section 9 below re-runs ARCH-025 Section 15's six-point check against this slice specifically, as PLAN-026 Section 9 flagged as a to-do for whichever plan implements Slice 2).

---

## 1. Proposed Sprint Name

**PLAN-027 / FEAT-027 — Canonical Relationship CSV Export**, implementing a new `RelationshipCsvExporter` that writes `relationships.csv` as a dedicated, additive report artifact alongside the existing `devices.csv` and `report.md`.

---

## 2. Current-State Findings

Grounded directly against the current repository (all line numbers as of `06239de`/`fc4b690`, the FEAT-026 commit):

- **`CanonicalPresentation.relationships`** (`networkmapper/reporting/canonical_presentation.py:129-158, 195-225`) already exposes everything this slice needs, unmodified by FEAT-026: `presentation.relationships: tuple[RelationshipPresentation, ...]`, each with `subject: str`, `device: Device | None`, `category: str`, `category_label: str`, `state: RelationshipCorroborationState`, and `related: tuple[RelatedSubjectPresentation, ...]` (each with `related_subject: str`, `device: Device | None`, `observations: tuple[RelationshipObservation, ...]`). **No change to `canonical_presentation.py` is required.**
- **`presentation.relationships` ordering is confirmed deterministic**, and confirmed *not* simply "insertion order": `RelationshipResolver._resolve()` (`networkmapper/relationships/resolver.py:120-123`) builds it via `sorted(relationships, key=lambda r: (r.subject, r.category))`, and `CanonicalPresentation.from_project()` maps that tuple 1:1 with no re-sort. This is the primary row order.
- **`relationship.related` ordering, verified precisely** (this matters — PLAN-026 Section 4.3 asserted this order is deterministic but did not trace its exact key, and the instructions for this plan require verifying rather than assuming): `CanonicalRelationship.observations` is sorted by `RelationshipResolver._resolve_group()` (`resolver.py:153-161`) using key `(provenance.provider, provenance.collection_method, related_subject)` — **not** `related_subject` alone. `canonical_presentation._group_related_subjects()` (`canonical_presentation.py:208-225`) then walks that already-sorted tuple and emits one `RelatedSubjectPresentation` per **first-seen** distinct `related_subject`. Net effect: `relationship.related` order is deterministic (a pure function of the input observation set, independent of scan/collection order) but is ordered by **first appearance under a (provider, collection_method, related_subject) sort**, not alphabetically by `related_subject`. This is unlike `IdentityPresentation.properties`, which the identity resolver does sort by `property_name` directly (PLAN-026 Section 3.3's closing paragraph) — the two presentations' internal tuples are deterministic by different underlying keys, and this plan's ordering guarantee must be stated in those terms, not assumed to match Slice 1's alphabetical case.
- **`related.observations` ordering, verified**: for a fixed `related_subject`, the subsequence of `relationship.observations` sharing that `related_subject` is already sorted by `(provider, collection_method)` (since `related_subject` is constant within the subsequence, the resolver's three-key sort degenerates to a two-key sort over exactly this data). This is the order `Provenance` will render in — already fixed upstream, no re-sort needed.
- **`MarkdownExporter._render_canonical_relationships()`** (`markdown_exporter.py:425-450`) is `CanonicalPresentation.relationships`'s only current consumer. It renders one Markdown section per `CanonicalRelationship`, one `- related:` line per `RelatedSubjectPresentation`, and one provenance line per observation (`_format_provenance`, line 467-472: `f"{provider} / {collection_method} ({observed_at:%Y-%m-%d %H:%M:%S})"` — full timestamp, human-facing). This confirms PLAN-026 Section 3.2/4.2's division of labor is already live in code: Markdown carries full per-observation detail including timestamps; CSV (Slice 1, already shipped) carries only fixed-vocabulary summary tokens. This plan's CSV Provenance column follows the same division (Section 5).
- **`CsvExporter`** (`networkmapper/exporters/csv_exporter.py`, extended by FEAT-026) is device-row-only and reads `presentation.identities`, never `presentation.relationships`. FEAT-026 established the working precedent this plan follows: construct `CanonicalPresentation.from_project(project)` exactly once, never import either resolver, never read `project.canonical_identities`/`project.canonical_relationships`/`project.observations` directly. **No change to `csv_exporter.py` is needed or proposed** — this is a new, separate exporter class, not a method added to the existing one (re-affirming PLAN-026 Section 4.5's reasoning: folding an edge-shaped artifact into the device-row-shaped `CsvExporter` would blur its single responsibility).
- **`ReportRunPaths`** (`networkmapper/reporting/report_run.py:27-33`) currently has exactly three fields: `run_directory`, `markdown_path`, `csv_path`. `build_report_run_paths()` (lines 36-71) computes the run directory once (keyed on `<timestamp>_<scan_profile>`, created via `mkdir(parents=True, exist_ok=True)`) and returns all three paths from that one directory. Adding a fourth path is a same-shaped, in-place addition — no new directory-naming logic, no new collision-avoidance logic, since the run directory is already the shared parent for every artifact.
- **`Application.run()`** (`networkmapper/application.py:219-242`) calls `build_report_run_paths("output", run_metadata)` once, then `CsvExporter().export(project, str(report_paths.csv_path))`, then `MarkdownExporter().export(project, str(report_paths.markdown_path), run_metadata=run_metadata)`, then prints two `✓ ... exported to ...` lines, all inside the single `REPORT_GENERATION` phase (bracketed by `_publish(..., PHASE_STARTED, ...)` / `_publish(..., PHASE_COMPLETED)`). **Neither existing exporter call is wrapped in a `try`/`except`** — an exporter exception propagates uncaught and aborts the run. This is confirmed by direct reading of lines 225-242; there is no exporter-specific error handling anywhere in `Application.run()` to be consistent with or diverge from.
- **`tests/test_report_run.py`** tests `RunMetadata` and `build_report_run_paths()` directly (`BuildReportRunPathsTest`, lines 34-133): run-directory naming, path construction relative to the run directory, directory creation, and non-collision across consecutive/simultaneous runs. None of these tests construct `ReportRunPaths` directly with positional-only assumptions that a new field would break; they all go through `build_report_run_paths()`.
- **`tests/test_application_cli.py`** constructs a *literal* `ReportRunPaths(...)` by keyword (`_fake_report_run_paths()`, lines 18-31) as a mock return value, and asserts on it in `test_report_artifacts_are_written_to_a_unique_run_directory` (lines 130-151): it asserts `csv_exporter_mock.return_value.export.assert_called_once_with(...)`, `markdown_exporter_mock.return_value.export.assert_called_once_with(...)`, and the two `✓ ... exported to ...` stdout lines. **Adding a required field to `ReportRunPaths` will break `_fake_report_run_paths()`'s construction call** (`TypeError: missing 1 required positional argument`) unless that helper is updated in the same change — this is a concrete, verified impact, not a hypothetical one (Section 7).
- **`tests/test_csv_exporter.py`** (FEAT-026) established the local test pattern this plan's new test file will mirror: a private `_export_rows()` helper writing to a `tempfile.TemporaryDirectory()`, direct construction of `CanonicalIdentity`/`PropertyCorroboration` (here: `CanonicalRelationship`/`RelationshipObservation`) rather than running a real resolver except in the one determinism test, and a dedicated `*NoReResolutionGuardTest` class asserting `hasattr(module, "IdentityResolver"/"RelationshipResolver")` is `False`.
- **Category vocabulary, verified**: `_CATEGORY_LABELS` (`canonical_presentation.py:46-50`) currently names exactly three categories in production use — `arp_neighbor`, `connected_to`, `bridge_fdb` — each produced by a real discovery provider (`arp_neighbor_provider.py`, `lldp_neighbor_provider.py`, `bridge_fdb_provider.py`). `_category_label()` falls back to a deterministic title-cased label for any unmapped category, confirming the codebase already treats `category` as an open, provider-extensible string rather than a closed enum — this plan's CSV `Category` column (raw string, Section 4) requires no fallback logic of its own, since it never needs the friendly label at all.
- **Symmetric double-WEAK relationships, verified as current, documented, unfixed behavior**: `RelationshipResolver` groups strictly by `(subject, category)` (`resolver.py`, confirmed by the sort key at line 122 and the docstring at `resolver.py:66-68`), so a symmetric category (`connected_to`) reported from both link ends necessarily produces two independent `CanonicalRelationship` records (one per subject), each `WEAK` rather than one `CONFIRMED` bidirectional record. ARCH-025 Section 7/16 and PLAN-025 Section 4 (item, "known cardinality limitation") both concluded presentation must render this faithfully, not merge it. This plan's row-expansion (Section 3) inherits that conclusion unchanged: two `CanonicalRelationship` records produce two independent row groups, never merged into one.

---

## 3. Exact Row-Expansion Semantics

Starting from PLAN-026 Section 4.1's design and re-verifying it against the structures traced in Section 2 above:

```python
for relationship in presentation.relationships:   # one CanonicalRelationship, in (subject, category) order
    for related in relationship.related:            # one distinct related_subject, in first-seen (provider, method, related_subject) order
        # -> exactly one CSV row
```

- **One row per distinct `(subject, category, related_subject)` claim** — confirmed achievable directly from `CanonicalPresentation`'s existing structure with no additional grouping logic in the exporter: `relationship.related` is already exactly this grouping (`_group_related_subjects`, Section 2).
- **`WEAK`/`CONFIRMED` relationship → exactly one row.** Verified in VER-025 and re-confirmed by `_group_related_subjects`'s construction: `WEAK`/`CONFIRMED` states are only reachable (per `_resolve_group`, `resolver.py:140-151`) when `distinct_values` has exactly one member, so `relationship.related` has exactly one element.
- **`CONFLICTING` relationship with N distinct related subjects → exactly N rows**, each sharing the same `Subject`/`Subject Hostname`/`Category`/`Corroboration State` (all `= "conflicting"`), differing only in `Related Subject`/`Related Subject Hostname`/`Provenance`. No related subject is preferred, dropped, or merged — this is the direct CSV analog of "never collapse a CONFLICTING group to one value," already the codebase's established rule for identities (PLAN-026 Section 3.2) and now applied identically to relationships.
- **Multiple observations supporting the same related subject never produce duplicate rows.** This is not new exporter logic — `_group_related_subjects` already performs this grouping upstream in `CanonicalPresentation` (Section 2); the exporter consumes one `RelatedSubjectPresentation` per row and reads its `.observations` tuple only to build the `Provenance` cell (Section 5), never to iterate additional rows.
- **Symmetric double-WEAK relationships remain two separate row groups**, never merged (Section 2's finding, restated as a row-expansion rule): `presentation.relationships` already contains two distinct `RelationshipPresentation` records for a symmetric link (one per subject/direction), and the exporter's outer loop naturally emits each as its own row group — no detection-and-merge logic is added or would be correct to add (PLAN-025 Section 4's conclusion applies identically here).
- **Zero canonical relationships → zero data rows, header row only** (Section 6).

---

## 4. Exact Proposed CSV Schema

| # | Column | Source | Empty when |
|---|---|---|---|
| 1 | `Subject` | `relationship.subject` (raw string, e.g. an IP address) — never replaced with a hostname | Never (a `CanonicalRelationship` always has a subject) |
| 2 | `Subject Hostname` | `relationship.device.hostname` if `relationship.device is not None` **and** `.hostname` is truthy | `relationship.device is None` (no matching `Device` for this subject), or a matching `Device` exists but has no hostname |
| 3 | `Category` | `relationship.category` (raw string, e.g. `connected_to`, `arp_neighbor`, `bridge_fdb`, or any future provider-introduced value) — never the friendly `category_label` | Never |
| 4 | `Related Subject` | `related.related_subject` (raw string) — never replaced with a hostname | Never |
| 5 | `Related Subject Hostname` | `related.device.hostname` if `related.device is not None` **and** `.hostname` is truthy | Same rule as column 2, applied to the related endpoint |
| 6 | `Corroboration State` | `relationship.state.value` (raw, lowercase: `weak`/`confirmed`/`conflicting`) — passed through unmodified, never recomputed | Never (every `CanonicalRelationship` has a state) |
| 7 | `Provenance` | See Section 5 | The related-subject group has no observations — structurally unreachable (`RelatedSubjectPresentation` is only constructed from a non-empty observation group, Section 2), so this column is never blank in practice, but no special-case code is added to guarantee it |

**Column ordering rationale**: `Subject`/`Subject Hostname` precede `Category`, which precedes `Related Subject`/`Related Subject Hostname`, which precede `Corroboration State`/`Provenance` — this groups each endpoint's raw identifier with its own hostname enrichment immediately, mirroring how the existing device CSV places `IP Address` immediately before `Hostname` (`csv_exporter.py`'s existing column 1/2 pair). This is a fresh file with no prior column order to preserve (unlike Slice 1's append-only constraint on `devices.csv`), so this ordering is a clean design choice, not a compatibility constraint.

**Deliberately excluded** (re-affirming and finalizing PLAN-026 Section 4.2's proposals, now as this plan's own decision rather than a carried-forward open question):
- **`Category Label`** — excluded. Per PLAN-026 Section 4.2 and re-confirmed here: the existing CSV convention (`Device Type` in Slice 1's `devices.csv`, `Canonical Identity State` in FEAT-026) is raw/machine value, not the title-cased Markdown label. Treated as a separate, explicit future decision if a consumer specifically asks for it — not bundled in here by default (per this plan's own instructions).
- **A rolled-up "Independent Source Count"** — excluded, same reasoning as Slice 1 (ARCH-025 Finding 3): the resolver's internally-computed-and-discarded count is not recomputed or exposed.
- **Per-observation timestamps as a column** — resolved (not merely carried forward) in Section 5.

---

## 5. Row-Expansion Detail and Provenance Representation Decision

### 5.1 Provenance: one field, precisely defined

**Provenance is a single CSV column** (column 7), not multiple columns and not a repeated-row-per-observation approach — a single field is required by the row-expansion in Section 3 (one row per distinct related subject, not per observation), so this is a single string that must summarize potentially several observations.

**Content**: for each observation in `related.observations` (already in the deterministic `(provider, collection_method)` order established in Section 2 for a fixed `related_subject`), render the token `f"{provenance.provider}/{provenance.collection_method}"`.

**Provider + collection_method are sufficient; timestamps are excluded.** Decided, not left open: `observed_at` is not rendered in this column. Rationale, made explicit per this plan's own requirement not to invent an aggregation rule silently:
- Including one timestamp per observation would require choosing which one wins if several tokens repeat (see dedup below) — no such choice is needed if timestamps are omitted entirely.
- Including all timestamps (one per observation, undeduplicated) would make this column's cardinality track raw observation count again, defeating the one-row-per-related-subject design and re-introducing exactly the "variable-length, unbounded-content" risk PLAN-026 Section 3.2 rejected for identity values.
- Markdown's existing `_format_provenance()` (Section 2) already renders full per-observation timestamps for every related subject — a reader who needs timestamp-level detail already has a correct, existing surface for it. This CSV column's job is the same "small, fixed-vocabulary token" role `Discovery Sources` and `Conflicting Identity Properties` already play, not a full audit log.
- This is the same division of labor ARCH-025 Section 8 and PLAN-026 Section 3.2 established for identities, applied identically here — not a new principle.

**Multiple supporting observations for one row are joined, deduplicated by exact `(provider, collection_method)` pair, first-seen order, comma-separated.** Precisely:

```python
seen: set[tuple[str, str]] = set()
tokens: list[str] = []
for observation in related.observations:              # already deterministically ordered (Section 2)
    key = (observation.provenance.provider, observation.provenance.collection_method)
    if key not in seen:
        seen.add(key)
        tokens.append(f"{key[0]}/{key[1]}")
provenance_cell = ",".join(tokens)
```

- **Deduplication is by exact `(provider, collection_method)` pair, not by observation.** Rationale: `RelationshipResolver._resolve_group()`'s own independence judgment is keyed identically on `(provider, collection_method)` (`resolver.py:137`, Section 2) — two observations sharing both are, by the resolver's own corroboration logic, "the same underlying claim" for whichever related subject they support. Rendering both tokens in one row's `Provenance` cell would suggest that row's related subject has two distinct supporting sources when, by the resolver's own key, it has one. This is not a new independence judgment invented in presentation — it reuses the resolver's own existing key verbatim, applied only to formatting that one row's own observation subset, never to `state`.
- **Provenance deduplication is presentation-level compression only — it does not recompute, explain, validate, or derive `Corroboration State`.** `Corroboration State` belongs to the entire canonical `(subject, category)` group (`CanonicalRelationship`) and is passed through unchanged from `RelationshipPresentation.state` (Section 4 column 6), independent of what any single row's `Provenance` cell contains. Each emitted row represents only one `related_subject` (Section 3), so its `Provenance` cell necessarily describes only the observations supporting that one related subject — never the complete observation set underlying the group's `state`:
  - **`WEAK`/`CONFIRMED` (exactly one related subject, Section 3):** a row's deduplicated `Provenance` list *may happen to* enumerate the same independent source pairs the resolver considered when computing `state`, simply because there is only one related subject in the group for that state to have been computed from. The exporter does not depend on or assert this equivalence anywhere — it is an incidental consequence of the single-related-subject case, not a guarantee this plan relies on or a fact the exporter checks.
  - **`CONFLICTING` (multiple related subjects):** `state` was computed from independent sources spread across *every* distinct related subject in the group, while any one row's `Provenance` cell reflects only the subset of observations tied to that row's own related subject. A reader must not infer, from one row's `Provenance` list, either the full evidence behind the group's `CONFLICTING` state or a count of the sources that produced it. The fuller, per-related-subject picture across the whole group remains `MarkdownExporter._render_canonical_relationships()`'s responsibility (Section 2), which already renders every related subject's observations under the same relationship heading.
- **Ordering is exactly `related.observations` tuple order** (already deterministic, Section 2) — no additional `sorted()` call. This mirrors PLAN-026 Section 3.3's "no independent re-sort" rule for identity properties, applied to relationships' own already-fixed order.
- **Delimiter**: `/` separates `provider` and `collection_method` within one token (matching PLAN-026 Section 4.2's original proposal exactly); `,` separates tokens (matching `Discovery Sources` and `Conflicting Identity Properties`'s existing comma-join convention in the same file family). `csv.writer` (used by both `CsvExporter` and, by this plan's design, `RelationshipCsvExporter`) automatically RFC-4180-quotes any cell containing a comma, so a multi-token `Provenance` cell round-trips correctly through any standard CSV reader without additional escaping code in this exporter.
- **No escaping rule is added for `/` or `,` appearing *inside* a `provider`/`collection_method` value itself.** Verified against every current production call site (Section 2's `collection_method` value survey: `sysDescr`-family field names, `ipNetToPhysicalTable`, `dot1d_tp_fdb`-style constants, LLDP method strings) — none currently contain `/` or `,`. This is flagged as an accepted, documented limitation (Section 10) rather than solved with generic delimiter-escaping machinery, consistent with this plan's prohibition on generic export-framework work; a future provider introducing such a value would need this revisited, not silently mis-render.

### 5.2 Hostname enrichment, precisely

Both `Subject Hostname` and `Related Subject Hostname` use `CanonicalPresentation`'s existing device enrichment (`relationship.device`, `related.device`) exclusively — never a fallback inference from any observation's raw value, never a lookup performed independently by `RelationshipCsvExporter` itself. This mirrors Slice 1's identity-side rule (never infer, only consume what `CanonicalPresentation` already enriched) applied to the relationship-side fields `CanonicalPresentation` already computes via the identical `network_graph.get_device(subject)` call (`canonical_presentation.py:174, 200, 221`, Section 2). A lookup miss renders blank and never drops the row (Section 3 restates this for the row itself; this subsection restates it for the two hostname cells specifically).

---

## 6. Zero-Relationship Behavior

Adopting the preferred default stated in this plan's own instructions, and finding no current-architecture reason to diverge:

- `relationships.csv` **is still created** on every run, unconditionally, exactly like `devices.csv` and `report.md` always are today (`Application.run()` calls all three exporters unconditionally, Section 2).
- When `presentation.relationships == ()`, the file contains **the header row only** — zero data rows, not an error, not a placeholder row, not an omitted file.
- **Absence of rows means "no canonical relationship claims were available for export this run,"** never "confirmed no relationships exist" — the same non-conclusion PLAN-026 Section 3.2 established for a blank `Canonical Identity State` cell, applied at the file level here since there is no device-row axis to attach a per-row blank to.
- This mirrors `MarkdownExporter._render_canonical_relationships()`'s existing empty-state handling exactly (`"No canonical relationship evidence collected."`, Section 2) — both renderers already agree on how an empty `presentation.relationships` is represented; this plan does not introduce a new empty-state convention.

---

## 7. Report-Run / Application Integration Changes

### 7.1 `networkmapper/reporting/report_run.py`

- `ReportRunPaths` gains a fourth field: `relationships_csv_path: Path`, added after `csv_path` (the two existing artifact-path fields stay in their current position/order; the new field is appended, not interleaved — the same append-only discipline Slice 1 applied to CSV *columns* applied here to a dataclass's *fields*). Added as a required field (no default), matching `markdown_path`/`csv_path`'s own un-defaulted style — `ReportRunPaths` has exactly one production constructor (`build_report_run_paths()`, confirmed in Section 2), so there is no risk of an existing caller needing a default to keep compiling; test call sites that construct it directly are enumerated in Section 7.4 and must be updated in the same change.
- `build_report_run_paths()` gains one line: `relationships_csv_path=run_directory / "relationships.csv"`, alongside the existing `markdown_path`/`csv_path` computation. No change to the run-directory-naming logic itself (Section 2 confirms one shared directory already backs every artifact path).

### 7.2 `networkmapper/application.py`

- One new import: `from networkmapper.exporters.relationship_csv_exporter import RelationshipCsvExporter`.
- One new export call, placed **between** the existing `CsvExporter().export(...)` call and the `MarkdownExporter().export(...)` call (Section 2's line numbers: after line 230, before line 232) — grouping the two CSV-shaped artifacts adjacently before the richer Markdown narrative is generated last:
  ```python
  RelationshipCsvExporter().export(
      project,
      str(report_paths.relationships_csv_path),
  )
  ```
- One new `print()` line, following the exact existing pattern and placed with the other two success lines (after both exports, before `_publish(..., PHASE_COMPLETED)`):
  ```python
  print(f"✓ Relationships exported to {report_paths.relationships_csv_path}")
  ```
- **No `try`/`except` is added around any of the three exporter calls.** Per Section 2's finding, the two existing exporters already have no failure handling of their own — an exception from `RelationshipCsvExporter.export()` propagates exactly the same way an exception from `CsvExporter`/`MarkdownExporter` already does today (aborts `Application.run()` uncaught). This is answering this plan's own question ("does failure to write the relationship CSV fail the run the same way as other exporter failures?") directly from current code: **yes, identically, because no exporter — old or new — has special-cased failure handling.** Adding any would be a behavior change to the *existing* exporters' failure contract, out of this plan's scope.
- No CLI/`argparse` change (no new flag; the artifact is unconditional, exactly like `devices.csv`/`report.md` — PLAN-026 Section 1's own reasoning for why this was deferred, not because it needs a flag, but because it needs `application.py`/`report_run.py` touched at all).

### 7.3 Console success message

Yes — `Application` prints a success message for the new artifact, `✓ Relationships exported to <path>`, in the exact same format/verb pattern (`✓ <Artifact> exported to <path>`) as the two existing lines. This keeps the three artifacts' run-completion output visually and structurally consistent, and gives a technician the same at-a-glance confirmation for all three files.

### 7.4 Test impact (established by direct inspection, Section 2)

- `tests/test_report_run.py`: `BuildReportRunPathsTest` needs one new assertion (e.g. `self.assertEqual(paths.relationships_csv_path, paths.run_directory / "relationships.csv")`), most naturally added to the existing `test_markdown_and_csv_paths_live_inside_the_run_directory` test (renamed or extended) rather than a wholly new test class, since it is testing the same `build_report_run_paths()` call with one more field to check.
- `tests/test_application_cli.py`: `_fake_report_run_paths()` **must** gain `relationships_csv_path=Path("output/fake-run/relationships.csv")` or every test using it breaks immediately at construction (`TypeError`, Section 2 — this is not optional cleanup, it is required for the existing suite to keep passing). `_run_application()`'s `patch(...)` block gains one more entry (`patch("networkmapper.application.RelationshipCsvExporter")`), and `test_report_artifacts_are_written_to_a_unique_run_directory` gains assertions mirroring its existing CSV/Markdown ones (`relationship_csv_exporter_mock.return_value.export.assert_called_once_with(ANY, str(fake_paths.relationships_csv_path))`, and the new stdout line).

---

## 8. Determinism

- **Row order**: `presentation.relationships` order, then `relationship.related` order — both already deterministic properties of `CanonicalPresentation`'s current, verified output (Section 2's precise key-tracing). `RelationshipCsvExporter` adds no `sorted()` call of its own anywhere.
- **`Provenance` cell order**: `related.observations` tuple order, already deterministic (Section 2); deduplication (Section 5.1) preserves first-seen order and does not reorder.
- **No ordering step is added that does not already exist upstream** — this plan requires zero new sort logic in the exporter itself, only sequential consumption of already-ordered tuples, which is the same posture Slice 1 achieved for identity properties (PLAN-026 Section 6).
- A determinism test (Section 11, item 5) is required specifically for `Provenance`, since it is the one column this plan defines with new logic (deduplication) rather than pure pass-through — the test constructs the same observation set in original vs. shuffled input order, resolves via the real `RelationshipResolver`, and asserts the two runs' `Provenance` cells are identical per `(subject, category, related_subject)` row.

---

## 9. ADR-Trigger Check (re-running ARCH-025 Section 15's six points, per PLAN-026 Section 9's explicit to-do)

1. No new view-model layer — reuses `CanonicalPresentation` entirely unmodified (Section 2). No trigger.
2. A new exporter reading `canonical_relationships` (via `CanonicalPresentation`) — explicitly anticipated by ARCH-025 Section 17's own recommended sequencing and by PLAN-026 Section 4's full design. No trigger.
3. No persistence change, no reload-then-export path — `ProjectSerializer` untouched (Section 2, Section 10). No trigger.
4. No change to either resolver's behavior — both remain unmodified and uncalled by the new code (Section 2, Section 10). No trigger.
5. A dedicated `RelationshipCsvExporter` class, one `(subject, category, related_subject)` row per iteration, provenance rendered via a documented dedup rule keyed on the resolver's own existing independence key (Section 5.1) — a presentation-formatting decision only, using a key the resolver already treats as authoritative for independence, rather than inventing a new one. This dedup governs one row's own `Provenance` cell only; it is not a re-derivation, explanation, or validation of the group-level `Corroboration State` (Section 5.1 states this distinction explicitly). No trigger, but flagged for explicit architect attention in review (Section 12) precisely because it is the one place this plan adds logic beyond pure pass-through.
6. `report_run.py`/`application.py` wiring (Section 7) touches a different surface than PLAN-026 Section 15 evaluated (that plan touched neither) — evaluated fresh here: one additive dataclass field with a single production constructor, one additive, unconditional export call with no new failure-handling branch, one additive print line, no CLI/argparse change. This is the same class of change ARCH-025 Section 15 point 3/6 already covers (no persisted-state or canonical-model change; no reload-then-export path) — re-confirmed as a no-trigger case specifically for the wiring surface, not just the exporter logic.

**Conclusion: no ADR is required for this slice**, with the one item (5) called out above as worth explicit architect sign-off on the *specific* dedup rule chosen (Section 5.1), even though it does not itself cross an ADR-trigger threshold.

---

## 10. Explicit Non-Goals

Restating this plan's own required prohibitions, cross-referenced to where each is upheld:

- **No `RelationshipResolver` calls from the exporter** — `RelationshipCsvExporter` reads only `CanonicalPresentation.from_project(project).relationships`; a no-re-resolution guard test (Section 11, item 14) asserts the module has no `RelationshipResolver`/`IdentityResolver` attribute, mirroring FEAT-026's identical guard.
- **No reading `Project.observations` directly** — never referenced anywhere in the new exporter; only `related.observations` (already-resolved, already-grouped `RelationshipObservation` tuples exposed via `CanonicalPresentation`) is read, and only for the `Provenance` cell.
- **No provider-specific relationship interpretation** — `Category` renders the raw string verbatim (Section 4); no provider-name branching exists anywhere in the exporter.
- **No merging symmetric double-WEAK relationships** — Section 3 explicitly preserves two independent row groups; no detection-and-merge logic is added.
- **No promoting `WEAK` to `CONFIRMED` in presentation** — `Corroboration State` passes through `relationship.state.value` unmodified (Section 4 column 6). The `Provenance` dedup rule (Section 5.1) never feeds back into, recomputes, explains, validates, or derives `state`; a row's `Provenance` cell describes only that row's own related subject's observations, never the complete evidence behind a `CONFLICTING` relationship's group-level state (Section 5.1).
- **No selecting a "best" related subject from `CONFLICTING` data** — every distinct related subject gets its own row (Section 3); none is preferred or dropped.
- **No creating topology semantics** — the exporter renders claims as flat rows; it does not construct a graph, does not compute reachability/paths, and does not infer a network topology beyond what `CanonicalPresentation` already exposes as discrete relationship records.
- **No adding new relationship categories** — `Category` is read verbatim from whatever `RelationshipResolver` already produced; no new category string is introduced, mapped, or synthesized anywhere in this plan.
- **No modifying canonical models** (`CanonicalIdentity`, `PropertyCorroboration`, `CanonicalRelationship`, `IdentityObservation`, `RelationshipObservation`, `ObservationProvenance`) — every column in Section 4 is derived entirely from fields these types (and `CanonicalPresentation`) already expose; none gains a new field.
- **No modifying discovery providers** — `arp_neighbor_provider.py`, `lldp_neighbor_provider.py`, `bridge_fdb_provider.py`, `nmap_provider.py`, `snmp_provider.py` are all untouched.
- **No modifying identity resolution or relationship resolution** — `networkmapper/identity/resolver.py` and `networkmapper/relationships/resolver.py` are untouched.
- **No generic export-framework work** — `RelationshipCsvExporter` is a concrete, single-purpose class with the same `export(project, output_path) -> None` shape `CsvExporter`/`MarkdownExporter` already use; no registry, no format-negotiation layer, no shared base class is introduced.
- **No modifying `CanonicalPresentation`, `Project`, `Device`, `NetworkGraph`** — confirmed throughout Section 2's grounding; none require or receive changes.
- **No modifying the existing device CSV schema** (`csv_exporter.py`) — untouched; `devices.csv`'s eleven columns (nine original + two from FEAT-026) are unaffected.
- **No modifying `MarkdownExporter`'s rendered content** — untouched; `report.md`'s output is byte-for-byte identical before and after this slice's implementation.
- **No modifying `ProjectSerializer` or persistence format** — untouched.
- **No `Category Label` column** — deliberately excluded (Section 4); revisable only as a separate, explicit future decision.
- **No per-observation timestamp column** — deliberately excluded and resolved, not merely deferred (Section 5.1's rationale).

---

## 11. Testing Requirements (for the follow-on implementation FEAT to satisfy)

Mapped to this plan's own required list, each grounded in a specific mechanism this plan already specifies:

1. **One canonical relationship, one related subject → one CSV row** — a `WEAK` or `CONFIRMED` `CanonicalRelationship` with a single `RelatedSubjectPresentation` renders exactly one data row (Section 3).
2. **`CONFIRMED` relationship state passes through** — `Corroboration State = "confirmed"` rendered verbatim, never recomputed (Section 4 column 6).
3. **`CONFLICTING` relationship, multiple related subjects → one row per distinct related subject** — construct a `CanonicalRelationship` with `state=CONFLICTING` and two/three-element `related` (via direct `RelationshipObservation` construction across two `(provider, collection_method)` pairs), assert N rows sharing `Subject`/`Category`/`Corroboration State` and differing only in `Related Subject`/`Related Subject Hostname`/`Provenance` (Section 3).
4. **Multiple observations for one related subject do not create duplicate relationship rows** — construct one related-subject group backed by 2+ observations (e.g. two `(provider, collection_method)` pairs, or the same pair repeated), assert exactly one row for that related subject, with `Provenance` reflecting the dedup rule (Section 5.1).
5. **Provenance aggregation is deterministic** — the determinism test described in Section 8: build observations, resolve via the real `RelationshipResolver` twice (original vs. shuffled input order), assert identical `Provenance` cells per row.
6. **Subject hostname enrichment works when a `Device` exists** — a `Device` matching `relationship.subject`'s IP renders its hostname in `Subject Hostname` (Section 5.2).
7. **Related-subject hostname enrichment works when a `Device` exists** — same rule applied to `related.related_subject` (Section 5.2).
8. **Missing `Device` enrichment leaves hostname blank** — no matching device (or a matching device with no hostname) renders `""` in the relevant hostname column, never an error or placeholder (Section 4 column 2/5).
9. **Unknown category exports safely** — a `CanonicalRelationship` with a category absent from `_CATEGORY_LABELS` (e.g. a synthetic `"future_category"`) still renders that raw string verbatim in `Category`, with no exception and no fallback-label substitution (Section 4 column 3 — CSV never needs `category_label`, so the Markdown-side fallback logic is irrelevant here by construction).
10. **Symmetric double-WEAK relationships remain two separate canonical relationship claims** — two independent `CanonicalRelationship` records (same category, opposite `subject`/related pairing, both `WEAK`) render as two independent row groups, never merged into one `CONFIRMED`-looking row (Section 3, Section 10).
11. **Empty canonical relationship set emits a header-only file** — `presentation.relationships == ()` produces a file with exactly one row (the header) and zero data rows (Section 6).
12. **Existing device CSV (`devices.csv`) remains unchanged** — a full run of `CsvExporter` (unmodified, per Section 2) against the same `Project` produces byte-identical output to its current FEAT-026 behavior; this plan touches no file `CsvExporter`'s own test suite (`test_csv_exporter.py`) covers.
13. **Markdown remains unchanged** — `MarkdownExporter`'s existing test suite (`test_markdown_exporter.py`) continues to pass unmodified, and `report.md`'s rendered content is unaffected by this slice (Section 2, Section 10).
14. **No resolver import/call path from the relationship CSV exporter** — a guard test asserting `networkmapper.exporters.relationship_csv_exporter` has no `IdentityResolver`/`RelationshipResolver` attribute, mirroring `CsvExporterNoReResolutionGuardTest` (FEAT-026) exactly.
15. **`report_run`/`application` wiring produces the new artifact exactly once** — `RelationshipCsvExporter().export()` (mocked, per the existing `test_application_cli.py` pattern) is asserted `called_once_with(ANY, str(report_paths.relationships_csv_path))`, and the `✓ Relationships exported to ...` stdout line is asserted present exactly once per run (Section 7.4).

Full regression: `pytest tests/ -q` must show zero new failures against the full suite (647+ tests as of FEAT-026), plus every new test above.

---

## 12. Files Likely Affected (Implementation FEAT, Not This Plan)

**New files:**
- `networkmapper/exporters/relationship_csv_exporter.py` — new `RelationshipCsvExporter` class.
- `tests/test_relationship_csv_exporter.py` — new test suite (Section 11).

**Modified files:**
- `networkmapper/reporting/report_run.py` — add `relationships_csv_path` field to `ReportRunPaths`; set it in `build_report_run_paths()` (Section 7.1).
- `networkmapper/application.py` — one new import, one new export call, one new print line, placed between the existing `CsvExporter`/`MarkdownExporter` calls (Section 7.2).
- `tests/test_report_run.py` — one new/extended assertion on `relationships_csv_path` (Section 7.4).
- `tests/test_application_cli.py` — update `_fake_report_run_paths()` (required, not optional — Section 2/7.4), add a `RelationshipCsvExporter` patch, extend `test_report_artifacts_are_written_to_a_unique_run_directory` (Section 7.4).
- `docs/architecture/overview.md` — one short paragraph naming `RelationshipCsvExporter` as `CanonicalPresentation`'s third consumer, mirroring the one-paragraph additions FEAT-025/FEAT-026 each made to the same "Reporting Path" section.

**Confirmed unaffected** (Section 10 restates why): `canonical_presentation.py`, `csv_exporter.py`, `markdown_exporter.py`, `project/models.py`, `core/models.py`, `core/network_graph.py`, `identity/resolver.py`, `relationships/resolver.py`, `identity/models.py`, `relationships/models.py`, `observations/models.py`, `observations/provenance.py`, `project/serializer.py`, every discovery provider, and `application.py`'s `argparse` setup / CLI surface.

---

## 13. Acceptance Criteria

1. `RelationshipCsvExporter.export(project, output_path)` writes one CSV row per distinct `(subject, category, related_subject)` claim, expanded exactly per Section 3.
2. All seven columns (Section 4) are populated exactly per their defined source and blank rule; `Category` and `Corroboration State` are always raw/machine values, never friendly labels.
3. `Provenance` is built exactly per the deduplication and ordering rule in Section 5.1 — no alternate aggregation is substituted without a plan amendment.
4. `Provenance` deduplication is presentation-level compression only: it never recomputes, explains, validates, or derives `Corroboration State`. `Corroboration State` is passed through unchanged from `RelationshipPresentation.state` regardless of what any row's `Provenance` cell contains; for a `CONFLICTING` relationship, each row's `Provenance` describes only that row's own related subject's observations, never the complete evidence behind the group's `state` (Section 5.1).
5. `Subject Hostname`/`Related Subject Hostname` use `CanonicalPresentation` device enrichment exclusively; no independent hostname inference is added anywhere in the new exporter.
6. A `CONFLICTING` `CanonicalRelationship` never collapses to one row; every distinct related subject gets its own row.
7. Symmetric double-WEAK relationships remain two independent row groups.
8. `relationships.csv` is emitted unconditionally, including a header-only file when `presentation.relationships == ()`.
9. `ReportRunPaths` gains `relationships_csv_path`; `build_report_run_paths()` sets it to `<run_directory>/relationships.csv`.
10. `Application.run()` calls `RelationshipCsvExporter().export()` exactly once per run, alongside (not replacing) the existing `CsvExporter`/`MarkdownExporter` calls, and prints one corresponding `✓ Relationships exported to ...` line.
11. `RelationshipCsvExporter` never imports or calls `IdentityResolver`/`RelationshipResolver`, and never reads `project.canonical_relationships`/`project.observations` directly — values are sourced exclusively from `CanonicalPresentation.from_project(project).relationships`.
12. No existing column, row, or file behavior of `devices.csv` (`CsvExporter`) changes.
13. No existing `report.md` (`MarkdownExporter`) content changes.
14. No new field is added to `CanonicalIdentity`, `PropertyCorroboration`, `CanonicalRelationship`, `IdentityObservation`, `RelationshipObservation`, `ObservationProvenance`, `Project`, `Device`, or `NetworkGraph`.
15. `pytest tests/ -q` and `python -m devtools validate --all` both pass with zero regressions once implemented.

---

## 14. Open Questions Carried Forward / Newly Raised

- **`Category Label` in CSV** (carried forward from PLAN-026 Section 8): still deliberately excluded; unchanged position.
- **Provenance timestamp column** (carried forward from PLAN-026 Section 8, now resolved rather than merely restated): this plan decides *not* to add one (Section 5.1); a future `First Observed`/`Last Observed` column remains a possible later revision, not committed here.
- **The `(provider, collection_method)` dedup rule for `Provenance`** (new, Section 5.1/9): this is the one place this plan introduces logic beyond pure pass-through of already-computed `CanonicalPresentation` data. It reuses the resolver's own existing independence key rather than inventing a new one, but is flagged explicitly for architect sign-off as its own line item, separate from the rest of the schema, since it is the part of this plan most likely to warrant a specific yes/no rather than blanket approval.
- **Export call ordering** (new, Section 7.2): this plan places `RelationshipCsvExporter` between `CsvExporter` and `MarkdownExporter`. This is a judgment call (grouping the two CSV artifacts adjacently) rather than a requirement derived from any current code constraint — an architect preferring a different order (e.g., after `MarkdownExporter`) can change this with no other section of this plan affected.
- **Whether `relationships.csv` should eventually be renamed or namespaced** (e.g. `relationships/` subdirectory) if a further artifact is added later — not addressed here; out of scope until a third CSV-shaped artifact is actually proposed.
- **`CsvExporter` row ordering in general** (carried forward from PLAN-026 Section 8, unrelated to this slice): still unresolved, still out of scope here.

---

## 15. Implementation Order (Proposed, for the Follow-On FEAT — Not Executed by This Plan)

1. `networkmapper/exporters/relationship_csv_exporter.py` — new exporter, per Sections 3-5.
2. `tests/test_relationship_csv_exporter.py` — new test suite, per Section 11.
3. `networkmapper/reporting/report_run.py` — add `relationships_csv_path` (Section 7.1).
4. `tests/test_report_run.py` — extend for the new path field (Section 7.4).
5. `networkmapper/application.py` — wire the new export call and print line (Section 7.2).
6. `tests/test_application_cli.py` — update `_fake_report_run_paths()`, add the new mock/assertions (Section 7.4).
7. Full existing test suite + `python -m devtools validate --all` run to confirm zero regressions.
8. `docs/architecture/overview.md` — one-paragraph follow-on note (Section 12).
