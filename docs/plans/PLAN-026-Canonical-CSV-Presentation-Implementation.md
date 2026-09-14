# Status

Approved — Architect-Reviewed

Approval: Architect-approved for Slice 1 implementation (FEAT-026). Written as investigation + implementation authority in the style PLAN-025 established.

Authority: [ARCH-025](../reports/ARCH-025-Canonical-Identity-Relationship-Presentation-Architecture.md) (Investigation Complete) Section 8 ("Multi-Format Semantics") and Section 12 ("Architectural Impact"), which named `CsvExporter` identity-corroboration columns and a separate relationship-CSV artifact as the explicit follow-on to PLAN-025/FEAT-025. Re-grounded directly against the current codebase for this slice (`exporters/csv_exporter.py`, `reporting/canonical_presentation.py`, `reporting/report_run.py`, `application.py`, `tests/test_csv_exporter.py`, `tests/test_report_run.py`), and against [VER-025](../reports/VER-025-Canonical-Identity-Relationship-Presentation-Verification.md)'s confirmation that `CanonicalPresentation` is verified correct, pure, and side-effect-free.

Implements: The third and fourth items of ARCH-025 Section 17's three-part sequence — "(3) `CsvExporter` identity summary columns" plus the previously-deferred "separate relationship CSV artifact." PLAN-025/FEAT-025 implemented (1) and (2) only and explicitly deferred all `CsvExporter` work to this plan (FEAT-025 commit message: "CsvExporter is unchanged, sequenced as a follow-on FEAT").

Production Code Modified: Yes, for Slice 1 only (Section 1). Slice 2 is fully designed here but its implementation is explicitly out of this plan's own scope — see Section 1.

New ADR Required: No, for Slice 1 (re-verified against ARCH-025 Section 15's six-point check, applied to this narrower slice; see Section 9). Slice 2's ADR posture is a live question for whichever plan implements it (Section 10).

---

## 1. Scope of This Slice

ARCH-025 Section 8 named two CSV-shaped deliverables and explicitly recommended sequencing them separately, "as a distinct, secondary deliverable rather than bundled into the same change... since it is a structurally separate problem (a new output file, not new columns on an existing one)." That reasoning is re-applied here, one level down from where PLAN-025 applied it (PLAN-025 deferred *all* CSV work; this plan is that deferral coming due, but the same internal split still holds):

**Slice 1 (this plan's implementation scope): identity-corroboration summary columns on the existing device-row CSV** (`networkmapper/exporters/csv_exporter.py`). This is a single-file, internal change with the same low blast radius PLAN-025's Markdown slice had: `CsvExporter.export(project, output_path)`'s signature does not change, no caller changes, and — critically — **no change to `application.py` or `report_run.py` is required**, because this slice adds columns to a file that is already produced, rather than a new file.

**Slice 2 (designed here, implementation deferred to a follow-on plan): a separate relationship CSV artifact**, one row per distinct `(subject, category, related_subject)` claim, per ARCH-025 Section 8's recommendation. This slice is fully specified in Section 4 of this plan — schema, one-row semantics, ordering, and the new exporter's shape — so a follow-on plan can implement it without re-investigating the design. It is deferred, not merely sequenced-later-in-the-same-plan, for a reason specific to this slice (not a generic reluctance to do more work): **producing a new report artifact during a real run requires touching `networkmapper/reporting/report_run.py` (a new path field) and `networkmapper/application.py` (a new export call in `Application.run()`)** — the same file that hosts this project's `ArgumentParser` (confirmed: `application.py` is the only production module besides `developer/benchmark_runner.py` importing `argparse`). This plan's constraints instruct "do not change... CLI," and while a single additive export-call line in an existing phase is not an argument-parsing or flag change, it is a materially different, broader-touching class of change than Slice 1's single-file, zero-caller-impact addition. Splitting here keeps this plan's own implementation footprint as narrow as PLAN-025's, and keeps the CLI/wiring question (Section 4.5, Section 10) visible and decided explicitly by whoever approves the follow-on, rather than folded into a plan whose primary goal is the CSV column addition.

This is the same "investigate and decide, implement narrowly" pattern PLAN-025 used for its own CSV deferral — the difference is this plan resolves the *design* questions ARCH-025 left open for both artifacts, even though it only carries one of them through to an approved implementation.

---

## 2. Current-State Grounding

- `CsvExporter.export(project, output_path)` (`networkmapper/exporters/csv_exporter.py:12-53`) writes exactly one CSV, one row per `project.network_graph.all_devices()`, nine columns: `IP Address, Hostname, Vendor, Device Type, Discovery Sources, SNMP Description, SNMP Location, SNMP Contact, SNMP Uptime`. The last four were appended by REPORT-003 specifically so "any existing tooling reading these columns by position is unaffected" — the established precedent for this codebase's CSV evolution is append-only, never interleaved, never reordered, never renamed.
- **`CsvExporter` does not sort its device rows.** `all_devices()` returns `list(self._devices.values())` over a plain dict populated in `add_device()` call order — unlike `MarkdownExporter._group_devices_by_type()`, which explicitly re-sorts by `(hostname, ip_address)`. This is pre-existing behavior, unrelated to and unaffected by this plan; Slice 1 adds columns to whatever row already exists in whatever order it already has, and introduces no new ordering dependency of its own (Section 6).
- `CanonicalPresentation.from_project(project)` (`networkmapper/reporting/canonical_presentation.py`, FEAT-025, verified in VER-025) already exposes everything Slice 1 needs: `presentation.identities: tuple[IdentityPresentation, ...]`, each carrying `subject: str`, `state: IdentityCorroborationState`, `device: Device | None`, and `properties: tuple[IdentityPropertyPresentation, ...]` (each with `property_name: str` and `state: IdentityCorroborationState`). **No change to `canonical_presentation.py` is needed for Slice 1** — it already iterates `canonical_identities` directly, already enriches with `Device` via `NetworkGraph.get_device()`, and already exposes per-property state without recomputing anything.
- `presentation.relationships: tuple[RelationshipPresentation, ...]` likewise already exposes everything Slice 2 needs: `subject`, `device`, `category`, `category_label`, `state`, and `related: tuple[RelatedSubjectPresentation, ...]` (each with `related_subject`, `device`, `observations`). No change to `canonical_presentation.py` is needed for Slice 2 either.
- `IdentityCorroborationState`/`RelationshipCorroborationState` are `StrEnum`s. The existing CSV already has a convention for rendering enum-like fields: `Device Type` renders `device.device_type.value` (e.g. `"server"`, lowercase, machine-friendly) — explicitly *not* `MarkdownExporter`'s title-cased `_display_title()` convention. This plan follows the CSV's own established convention, not Markdown's, for consistency within the file (Section 3, Section 4).
- `report_run.py`'s `ReportRunPaths` (`markdown_path`, `csv_path`) and `build_report_run_paths()` are unchanged by Slice 1. Slice 2 would need a third field (Section 4.5) — this is exactly the "new output file" cost Section 1 uses to justify deferring Slice 2.
- `application.py:227-230` calls `CsvExporter().export(project, str(report_paths.csv_path))` exactly once. Slice 1 requires zero changes here since the method signature is unchanged. Slice 2 would require a second export call — deferred (Section 1).
- **Column-count changes are not byte-compatible the way PLAN-025's Markdown sections were.** PLAN-025's acceptance criterion 3 required "every existing test in `tests/test_markdown_exporter.py` continues to pass unmodified," achievable because new Markdown *sections* are pure appends to the document, leaving every existing section's text untouched. A CSV column addition cannot satisfy the equivalent literal claim: appending a column to the header row and to *every* data row necessarily changes every row's length and trailing content, so existing `tests/test_csv_exporter.py` assertions that check full row lists (e.g. `self.assertEqual(rows[1], ["192.168.1.10", "DC-01", ...])`) will fail unless updated to include the new trailing (blank, since none of those tests populate `canonical_identities`) columns. This is flagged explicitly (Section 5) because it changes what "preserve existing CSV output compatibility" can honestly mean for this slice: compatibility here means *column position/order/semantics of the nine existing columns is unchanged and new columns are strictly appended*, not *the file is byte-identical to before*. Existing tests are updated additively (extended row assertions), not left unmodified.

---

## 3. Slice 1 — Identity Summary Columns on the Device CSV

### 3.1 Exact schema

Two columns appended after the existing nine (position 10, 11 — after `SNMP Uptime`), following the REPORT-003 append-only precedent exactly:

| Column | Source | Empty when |
|---|---|---|
| `Canonical Identity State` | `identity.state.value` (raw `IdentityCorroborationState` value: `weak`/`probable`/`confirmed`/`conflicting`) for the `IdentityPresentation` whose `subject == device.ip_address`, if one exists | No `CanonicalIdentity` resolved for this device's IP (no identity evidence collected this run, or this device wasn't a resolvable subject) |
| `Conflicting Identity Properties` | Comma-joined `property_name` values from that identity's `properties` where `property.state == IdentityCorroborationState.CONFLICTING`, taken in `properties` tuple order (Section 3.3 fixes this order precisely; no independent sort is applied) | No matching identity, or the identity has no property in `CONFLICTING` state |

Full header (Slice 1, in order):

```
IP Address, Hostname, Vendor, Device Type, Discovery Sources,
SNMP Description, SNMP Location, SNMP Contact, SNMP Uptime,
Canonical Identity State, Conflicting Identity Properties
```

### 3.2 Why exactly these two columns, and nothing richer

Directly re-applying ARCH-025 Section 8's constraint ("must preserve the canonical identity/corroboration state, must never substitute a preferred conflicting value, and must never imply that an existing single-valued `Device` field... resolves a canonical conflict"):

- **`Canonical Identity State` never substitutes for `Hostname`.** The existing `Hostname` column continues to render `device.hostname` exactly as today (untouched) — a value populated independently of identity resolution, with no relationship to `CanonicalIdentity` anywhere in the codebase (per ARCH-025 Section 8's own observation). The new column is additive context, deliberately named `Canonical Identity ...` (not merged into or renamed from any existing column) so a reader cannot mistake it for a property of `Hostname` resolving a conflict.
- **No conflicting *value* is ever rendered in CSV.** `Conflicting Identity Properties` lists property *names* only (`hostname`, `domain`, ...) — a small, fixed-vocabulary set of short tokens, safely comma-joinable exactly like the existing `Discovery Sources` column already does for provider names. It never lists the disagreeing *values* themselves (e.g. `dc-01` vs `dc-99`), because a variable-length, unbounded-content list is exactly the "delimiter-hack" ARCH-025 Section 8 rejected for relationship data, and doing that here would risk exactly the collapsing-into-a-single-cell problem this whole initiative exists to avoid. A reader who sees `hostname` in this column and wants to know what the conflicting values actually are is directed to the Markdown report's `# Canonical Identity` section (FEAT-025), which already renders every distinct value with full provenance — this is a deliberate cross-format division of labor, not a coverage gap (ARCH-025 Section 8: "different renderers consume different-depth projections of one correct underlying derivation").
- **No independent-source count.** Consistent with FEAT-025 and ARCH-025 Finding 3, the resolver's internally-computed-and-discarded independent-source count is not recomputed or exposed here either.
- **A device with no canonical identity at all renders both new columns blank** — not `"unknown"`, not `"weak"` — exactly matching the existing CSV's blank-for-missing convention (`device.hostname or ""`) and PLAN-025's requirement that an absent record never implies a resolved conclusion. Blank here means "no identity evidence resolved for this subject," never "confirmed weak" or "confirmed no conflicts."

### 3.3 Row-to-identity matching, precisely (required contract)

This section is the complete, exclusive specification of how an existing device CSV row acquires canonical identity data. Nothing outside this section may introduce an additional matching path.

- **Row axis is unchanged and is the only row axis.** `CsvExporter.export()` continues to iterate `project.network_graph.all_devices()` exactly as it does today (Section 2) and emits exactly one row per existing device, in the same order it already produces. Slice 1 never iterates `presentation.identities` to produce rows, and never adds a row for a canonical identity that has no corresponding device. An `IdentityPresentation` whose `subject` matches no device's `ip_address` is simply never looked up and never rendered anywhere in this CSV — it is not an error, and it is not represented by a synthetic or placeholder row (consistent with Section 8's "Unmatched canonical identities in CSV form," restated here as the authoritative statement for Slice 1 rather than left implicit).
- **The single matching rule, and no other.** A device row is associated with canonical identity data if and only if:

  ```
  IdentityPresentation.subject == Device.ip_address
  ```

  `CsvExporter.export()` builds one local, read-only lookup once per call:

  ```python
  presentation = CanonicalPresentation.from_project(project)
  identity_by_subject = {identity.subject: identity for identity in presentation.identities}
  ```

  Then, per device row, looks up `identity_by_subject.get(device.ip_address)`. This mirrors exactly the same `subject`-as-IP matching convention `canonical_presentation.py` itself already uses for `Device` enrichment (`network_graph.get_device(identity.subject)`) — Slice 1 introduces no new identity convention, just the reverse-direction lookup over data `CanonicalPresentation` already computed.
- **No other matching path is permitted.** Explicitly, this lookup is never performed, supplemented, or overridden by: `device.hostname` / `identity` property values named `hostname`; `device.mac_address` or any MAC-derived key; any `Device` reference held by the `Device` enrichment already attached to a `CanonicalIdentity`; the *value* of any `IdentityObservation`/property; or any other heuristic, fuzzy match, or fallback. If `subject == ip_address` does not hold, the identity is unmatched for that row, full stop — there is no secondary attempt to associate it by any other field.
- **`IdentityPresentation.device` is optional enrichment, not a matching signal, and is not used for this lookup.** `canonical_presentation.py` populates `identity.device` by performing this exact same `subject == ip_address` lookup itself (`network_graph.get_device(identity.subject)`) — it is a *result* of the matching rule, computed once already, not an independent or alternative way of discovering which device an identity belongs to. Using `identity.device` here would therefore be circular (re-deriving, via a `Device` object, the same association `subject`/`ip_address` already establishes) and would risk being misread as a second, object-identity-based matching path that could diverge from the string-equality rule above. `CsvExporter` performs its own `subject == device.ip_address` comparison directly and never reads or branches on `identity.device` for matching purposes; the plain string comparison is both sufficient and the only authoritative rule.
- **Matched vs. unmatched output, restated as the exhaustive contract:**
  - No `IdentityPresentation` has `subject == device.ip_address` for a given device row → `Canonical Identity State` = blank, `Conflicting Identity Properties` = blank (Section 3.1).
  - Exactly one `IdentityPresentation` has `subject == device.ip_address` → `Canonical Identity State` = that identity's `state.value`, passed through unmodified from `CanonicalPresentation` (never recomputed — Section 7); `Conflicting Identity Properties` = the `property_name` of every `properties` entry whose `state == IdentityCorroborationState.CONFLICTING`, and no other entries.
  - Two `IdentityPresentation`s cannot share a `subject` (`presentation.identities` is keyed by subject, itself sourced from `IdentityResolver`'s own subject-keyed, deduplicated output — Section 3.3's closing paragraph below), so "exactly one or none" is the only reachable case; there is no tie-breaking rule to define because no tie can occur.
- **Ordering of `Conflicting Identity Properties`, made explicit.** The list is built by filtering `identity.properties` — already in the fixed, deterministic order `CanonicalPresentation` exposes it in (Section 3.1's cross-reference) — down to entries with `state == CONFLICTING`, preserving that tuple's existing order, and taking each surviving entry's `property_name`. No additional `sorted()` call is introduced. This order is already deterministic and already alphabetical by `property_name` in practice, because `IdentityResolver._resolve_subject()` (`networkmapper/identity/resolver.py:80-88`) constructs `CanonicalIdentity.properties` via `sorted(..., key=lambda property_corroboration: property_corroboration.property_name)`, and `canonical_presentation.py` maps that tuple 1:1 into `IdentityPresentation.properties` without re-sorting (`canonical_presentation.py:162-168`). Re-sorting in `CsvExporter` would therefore be redundant work reproducing an order the resolver already guarantees, not a correctness requirement — the documented reason *not* to sort again is that the order is already fixed, upstream, by code this plan does not touch and must not duplicate.
- **No resolver calls, no presentation-time inference.** `CsvExporter` calls `CanonicalPresentation.from_project(project)` exactly once per `export()` call to obtain `presentation.identities`, and performs no other identity computation — restating and cross-referencing Section 7's broader no-re-resolution guard specifically for this matching step: the string-equality comparison above is the only logic Slice 1 adds; it resolves nothing.

If two devices somehow shared an IP (`NetworkGraph.add_device` already prevents this — it silently ignores a second `add_device` call for a duplicate IP, existing behavior, unrelated to this plan), the dict comprehension above is keyed correctly regardless, since `canonical_identities` is itself keyed by subject/IP already deduplicated by `IdentityResolver`.

---

## 4. Slice 2 (Designed, Implementation Deferred) — Relationship CSV Artifact

### 4.1 One-row semantics, precisely

One row per **distinct `(subject, category, related_subject)` claim**, exactly as ARCH-025 Section 8 specifies — not one row per `CanonicalRelationship`, because a `CONFLICTING` `CanonicalRelationship` has more than one distinct `related_subject` and cannot be represented in one row without collapsing it. Concretely, using the already-computed `CanonicalPresentation`:

```python
for relationship in presentation.relationships:        # one CanonicalRelationship
    for related in relationship.related:                # one distinct related_subject
        # → exactly one CSV row
```

For a `WEAK`/`CONFIRMED` relationship, `relationship.related` already has exactly one element (per FEAT-025's own grouping, verified in VER-025), so this produces exactly one row. For `CONFLICTING`, it produces one row per distinct `related_subject`, each carrying the *same* `subject`, `category`, and `state=CONFLICTING` — matching ARCH-025 Section 8's exact specification — and each row's provenance reflects only the observations under that specific `related` group (`related.observations`), never the whole `CanonicalRelationship`'s undifferentiated observation set.

### 4.2 Exact schema (designed, not yet implemented)

| Column | Source |
|---|---|
| `Subject` | `relationship.subject` (raw string) |
| `Subject Hostname` | `relationship.device.hostname` if `relationship.device` is not `None`, else blank |
| `Category` | `relationship.category` (raw string, e.g. `connected_to`) |
| `Related Subject` | `related.related_subject` (raw string) |
| `Related Subject Hostname` | `related.device.hostname` if `related.device` is not `None`, else blank |
| `Corroboration State` | `relationship.state.value` (raw, lowercase — matching the Slice 1 / `Device Type` convention, Section 2) |
| `Provenance` | Comma-joined `f"{o.provenance.provider}/{o.provenance.collection_method}"` for each `o` in `related.observations`, in that tuple's existing (already resolver-fixed) order, deduplicated only if identical (should not normally occur, since independence is already keyed on `(provider, collection_method)` by the resolver) |

Deliberately **excluded** from this schema, and why:
- **`Category Label`** (the friendly `"Connected To"`/`"ARP Neighbor"` labels `canonical_presentation.py` already computes) — omitted from CSV to match the existing CSV's raw/machine-value convention (`Device Type` uses `.value`, not a friendly label), keeping this file's audience as "spreadsheet/tooling consumer" and leaving human-friendly labeling to Markdown, consistent with Section 3's identical choice for `Canonical Identity State`.
- **Per-observation timestamps** — `observed_at` is available per observation but is not included as a column here, since summarizing multiple observations' timestamps into one cell would require picking a summarization rule (earliest? latest? all of them, comma-joined?) that ARCH-025 never specified and that isn't needed to satisfy the one-row-per-claim requirement. Left as an explicit open question (Section 8) rather than decided by default.

### 4.3 Ordering, precisely

Primary order: `presentation.relationships` order, which is already the resolver's own deterministic `(subject, category)` sort (verified in VER-025 Section 6) — the relationship CSV exporter must not re-sort this. Secondary order (within one `CanonicalRelationship`'s expanded rows): `relationship.related` tuple order, which `canonical_presentation.py`'s `_group_related_subjects()` already produces deterministically (first-seen order over the resolver's already-sorted `observations` tuple, verified in VER-025 Section 6) — again, no additional sort is introduced or needed. This directly satisfies ARCH-025 Section 8's Finding 9 requirement for a deterministic secondary order without adding a new one: the order Slice 2 needs already exists in `CanonicalPresentation`'s current output.

### 4.4 Unmatched endpoints

Both `Subject Hostname` and `Related Subject Hostname` render blank on an enrichment miss; the row itself is never dropped, never gated on a `Device` match existing for either endpoint — directly satisfying the "no-suppression" invariant ARCH-025 Section 8 confirms this artifact already gets "for free" by iterating `canonical_relationships` directly rather than `network_graph.all_devices()`.

### 4.5 New exporter shape and wiring (deferred implementation)

A new, dedicated class — `RelationshipCsvExporter` in a new file `networkmapper/exporters/relationship_csv_exporter.py`, sibling to `CsvExporter` and `MarkdownExporter`, with the same `export(project, output_path) -> None` signature shape both existing exporters already use. A new method bolted onto `CsvExporter` was considered and rejected: `CsvExporter` already has an established, singular meaning (the device-row CSV); folding an unrelated artifact (a relationship-edge CSV) into the same class would blur single-responsibility for no benefit, and a dedicated class costs nothing extra given `export(project, output_path)` is already the established per-exporter contract.

Wiring this in for real (making a real run actually produce `relationships.csv`) requires, when a follow-on plan takes this up:
- `ReportRunPaths` (`reporting/report_run.py`) gains a `relationships_csv_path: Path` field; `build_report_run_paths()` sets it to `run_directory / "relationships.csv"`.
- `Application.run()` (`application.py`) gains one additional `RelationshipCsvExporter().export(project, str(report_paths.relationships_csv_path))` call alongside the existing `CsvExporter`/`MarkdownExporter` calls in the same "Generating Markdown and CSV reports" phase, plus a corresponding `print(f"✓ Relationships exported to {report_paths.relationships_csv_path}")` line matching the existing two.

No argument parsing changes, no new CLI flag, no discovery/enrichment/topology change — the wiring is a same-shaped addition to an existing phase, not a new capability the user opts into. This is named explicitly here so the follow-on plan does not need to re-derive it, but it is **not implemented by this plan** (Section 1).

---

## 5. Preserving Existing CSV Output Compatibility

Applied per-slice, since the two slices have different compatibility shapes:

- **Slice 1** changes the *existing* `devices.csv` artifact. Compatibility means: all nine existing columns keep their exact position, order, header text, and per-row value semantics; the two new columns are strictly appended at the end; no existing column is renamed, reordered, removed, or reinterpreted. This matches the REPORT-003 precedent exactly. It does **not** mean the file is byte-identical to today's output (Section 2) — any tool parsing this CSV by fixed column *count* (rather than by name or by the first nine positions) will see a wider row than before, exactly as happened when REPORT-003 added its four SNMP columns. This is the same compatibility contract this codebase already accepted once.
- **Slice 2** (deferred) introduces an entirely new file (`relationships.csv`) alongside the existing `devices.csv`/`report.md`; it changes nothing about either existing artifact's content, and a technician or tool not expecting the new file simply doesn't encounter it (it lives in the same per-run directory, requiring no new top-level output location).
- Neither slice changes discovery, enrichment, classification, or `ProjectSerializer` output. Neither slice changes `MarkdownExporter`'s output (verified: no changes to `markdown_exporter.py` proposed anywhere in this plan).

---

## 6. Determinism

- **Slice 1**: introduces no new ordering — device row order is exactly whatever `project.network_graph.all_devices()` already returns today (Section 2's noted pre-existing, unsorted-by-this-exporter behavior, unchanged). The new columns are a per-row, order-independent dict lookup (`identity_by_subject.get(device.ip_address)`), so permuting the input `observations`/`canonical_identities` sequence before resolution cannot change which row gets which value, only (transitively, via the resolver's own already-verified determinism, VER-025 Section 6) guarantees the *value* itself is order-independent. A determinism test asserts this directly: build two `Project`s from a shuffled vs. unshuffled observation sequence (mirroring `CanonicalPresentationDeterminismTest`), resolve, and assert the two CSVs' new-column values are identical per IP regardless of device row order.
- **Slice 2** (deferred): ordering fully addressed in Section 4.3 — both the primary and secondary order are already deterministic properties of `CanonicalPresentation`'s existing, verified output; the new exporter adds no sorting of its own and must not add any (a code-review checklist item for whoever implements it, mirroring FEAT-025's no-re-resolution guard pattern).

---

## 7. Never Re-Resolving — Guard, Restated for CSV

Restating PLAN-025 Section 5's load-bearing constraint for this slice specifically:

- `CsvExporter` (Slice 1) and `RelationshipCsvExporter` (Slice 2, when implemented) read only `CanonicalPresentation.from_project(project)` — never `project.canonical_identities`/`project.canonical_relationships` directly, and never `project.observations`. This is a deliberate choice to route through the already-verified view-model rather than re-deriving anything from raw canonical records a second time, even though the fields are technically reachable — using the same single, tested seam `MarkdownExporter` already uses means any future correction to grouping/enrichment logic (in `canonical_presentation.py`) automatically applies to every exporter, rather than requiring each exporter to independently get it right.
- Neither exporter module may import `IdentityResolver` or `RelationshipResolver`, mirroring `CanonicalPresentationNoReResolutionGuardTest` exactly. A parallel guard test is added for `tests/test_csv_exporter.py` (Slice 1, in this plan) and specified for the Slice 2 follow-on's test file.
- `identity.state` / `property.state` / `relationship.state` are read and rendered as-is (`.value`); neither slice recomputes a corroboration state, an independent-source count, or a "confirmed" label from raw observations.
- No `CONFLICTING` value is ever collapsed to one in either slice's cells — Slice 1 lists property *names* only (never values, Section 3.2); Slice 2 expands to multiple rows rather than collapsing `related_subject` values (Section 4.1).

---

## 8. Open Questions Carried Forward

- **Slice 2's implementation vehicle**: whether the follow-on that implements Section 4 is itself called `PLAN-027`/`FEAT-026B` or something else is left to whoever schedules it; this plan only fixes the design, not its own sprint numbering for that future work.
- **Slice 2's provenance timestamp summarization** (Section 4.2): whether `relationships.csv` should eventually gain an `Observed At` (or `First Observed`/`Last Observed`) column, and which summarization rule to use if so, is explicitly left undecided rather than defaulted.
- **Unmatched canonical identities in CSV form** (ARCH-025 Section 8/16, restated): the device-row CSV structurally cannot carry a canonical identity with no matching `Device` (there is no row to attach it to), and this plan does not propose a separate "unmatched identities" CSV artifact to close that gap — Markdown remains the representable surface for that case (per FEAT-025/VER-025). Revisit only if real usage indicates a need; inventing a placeholder device row remains explicitly rejected (ARCH-025 Section 8).
- **`Category Label` in CSV** (Section 4.2): deliberately excluded from Slice 2's schema in favor of raw `category`; revisable if a future consumer specifically wants CSV-native friendly labels, but not decided as a requirement here.
- **CsvExporter row ordering in general** (Section 2's noted pre-existing gap): whether `CsvExporter` should eventually sort device rows deterministically the way `MarkdownExporter` already does is a pre-existing question this plan surfaces but does not resolve — out of scope for a canonical-presentation-focused plan, unrelated to identity/relationship data.

---

## 9. ADR-Trigger Check — Slice 1

Walking ARCH-025 Section 15's six points against Slice 1 specifically:

1. No new view-model layer — Slice 1 reuses `CanonicalPresentation` entirely unmodified. No trigger.
2. `CsvExporter` reading `canonical_identities` (via `CanonicalPresentation`) — explicitly anticipated by ADR-012's own Future Work section and by ARCH-025 Section 17's own recommended sequencing. No trigger.
3. No persistence change, no reload-then-export path — Slice 1 touches nothing in `ProjectSerializer` or `application.py`. No trigger.
4. No change to either resolver's behavior — both remain unmodified and uncalled by the new code. No trigger.
5. No relationship-CSV code ships in this plan (Slice 2 deferred) — nothing to trigger here yet; re-evaluate at Slice 2's own implementation time.
6. Two new appended columns, populated via a read-only dict lookup over already-resolved data — a presentation-formatting decision only, no persisted-state or canonical-model change. No trigger.

**Conclusion: no ADR is required for Slice 1.** Slice 2's own ADR-trigger check (its `report_run.py`/`application.py` wiring touches a different surface than anything ARCH-025 Section 15 evaluated) should be re-run explicitly by whichever plan implements it — flagged here as a to-do, not resolved.

---

## 10. Non-Goals (Explicit)

- Modifying `IdentityResolver` or `RelationshipResolver` in any way.
- Adding any new field to `CanonicalIdentity`, `PropertyCorroboration`, `CanonicalRelationship`, `IdentityObservation`, `RelationshipObservation`, or `ObservationProvenance` — every column in both schemas (Sections 3, 4) is derived entirely from fields those types (and `CanonicalPresentation`) already expose.
- Modifying `Project`, `Device`, or `NetworkGraph`.
- Modifying `MarkdownExporter` or any content it renders.
- Modifying `ProjectSerializer` or any persistence behavior.
- Modifying discovery, enrichment, classification, or any CLI argument/flag.
- Implementing Slice 2 (the relationship CSV artifact) — designed in full (Section 4), not built, by this plan.
- Modifying `report_run.py` or `application.py` — required only for Slice 2, which is deferred (Section 1).
- Building a generic/pluggable export framework — both slices are concrete, single-purpose exporter classes following the existing `export(project, output_path)` shape; no new abstraction layer, registry, or format-negotiation mechanism is introduced.
- Sorting or otherwise changing existing `CsvExporter` device-row order (Section 8's open question, explicitly not resolved here).
- Rendering conflicting identity *values* (as opposed to property *names*) in CSV, or friendly relationship category labels in CSV (Section 3.2, Section 4.2).

---

## 11. Testing Strategy — Slice 1 (this plan's implementation scope)

All achievable with no discovery execution and no network access, following `tests/test_csv_exporter.py`'s and `tests/test_canonical_presentation.py`'s existing patterns:

- **Existing-row extension**: every existing `tests/test_csv_exporter.py` assertion that checks a full row list is updated (additively) to include two trailing blank values, proving the two new columns default to blank and don't disturb the nine existing columns' values or order (Section 5).
- **Header row**: assert the header row is exactly the eleven columns in the exact order given in Section 3.1.
- **Populated, non-conflicting identity**: a device whose IP matches a `CanonicalIdentity` with `state=CONFIRMED` and no conflicting property renders `Canonical Identity State="confirmed"`, `Conflicting Identity Properties=""`.
- **Conflicting identity**: a `CanonicalIdentity` with one `CONFLICTING` property (`hostname`) and one non-conflicting property (`domain`, `WEAK`) renders `Canonical Identity State="conflicting"` (the identity-level rollup) and `Conflicting Identity Properties="hostname"` — `domain` is absent since only the conflicting property name is listed.
- **Multiple conflicting properties**: two properties both `CONFLICTING` render both names, comma-joined, in `identity.properties` tuple order (Section 3.3) — which is already alphabetical because the resolver produces it that way, not because `CsvExporter` sorts.
- **Unmatched identity (no `CanonicalIdentity` for this device's IP)**: both new columns render blank — not `"weak"`, not an error.
- **No canonical identity evidence at all (empty `canonical_identities`)**: every device row's two new columns render blank; mirrors the existing, currently-passing tests that never populate `canonical_identities` and must continue to pass once updated (Section 5).
- **Determinism**: construct observations, shuffle them, resolve, export to CSV twice (unshuffled vs. shuffled input) and assert the new-column values are identical per IP (Section 6).
- **No-re-resolution guard**: a test asserting `networkmapper.exporters.csv_exporter` has no `IdentityResolver`/`RelationshipResolver` attribute, mirroring `CanonicalPresentationNoReResolutionGuardTest` exactly.
- **Full regression run**: `pytest tests/ -q` must show zero new failures against the full suite (639+ tests as of VER-025), plus the additive/updated CSV tests above.

Slice 2's testing strategy is specified in Section 4 alongside its schema (one-row-per-claim expansion, ordering, unmatched-endpoint handling) and should be finalized in detail by whichever follow-on plan implements it; not repeated here as a formal acceptance criterion since Slice 2 is not this plan's implementation scope.

---

## 12. Acceptance Criteria

**Slice 1 (this plan's implementation scope):**

1. `CsvExporter.export()` renders two additional columns, `Canonical Identity State` and `Conflicting Identity Properties`, appended after the existing nine columns in the exact order given in Section 3.1.
2. Values are sourced exclusively from `CanonicalPresentation.from_project(project)` — `CsvExporter` never imports or calls `IdentityResolver`/`RelationshipResolver`, and never reads `project.canonical_identities`/`project.observations` directly.
3. `Canonical Identity State` renders the identity-level `state.value` (raw, lowercase) exactly as resolved — never recomputed, never a substitute value.
4. `Conflicting Identity Properties` lists only property *names* (never values) for properties in `CONFLICTING` state, comma-joined, in `identity.properties` tuple order with no additional sort applied (Section 3.3), never dropping or picking among the identity's actual `CONFLICTING` properties.
5. A device with no matching `CanonicalIdentity` renders both new columns blank, without error and without a misleading non-blank default.
6. All nine existing columns retain their exact names, order, and per-row value semantics — verified by updated (not literally byte-unchanged, per Section 5) existing tests.
7. Determinism: permuting input observations before resolution does not change any row's `Canonical Identity State`/`Conflicting Identity Properties` value for a given IP.
8. No new field is added to `Project`, `Device`, `NetworkGraph`, `CanonicalIdentity`, `PropertyCorroboration`, `CanonicalRelationship`, or any observation/provenance type.
9. `MarkdownExporter`, `application.py`, and `report_run.py` are byte-for-byte unmodified by this plan's implementation.

**Slice 2 (specified, not implemented by this plan — acceptance criteria for the follow-on to adopt or refine):**

10. A new `RelationshipCsvExporter.export(project, output_path)` writes one row per distinct `(subject, category, related_subject)` claim per Section 4.1, using the exact schema in Section 4.2.
11. A `CONFLICTING` `CanonicalRelationship` expands into multiple rows sharing `subject`/`category`/`state`, one per distinct `related_subject`, each row's `Provenance` reflecting only that `related_subject`'s own observations.
12. Row order is exactly `presentation.relationships` order, then `relationship.related` order — no additional sort introduced.
13. Unmatched `subject`/`related_subject` endpoints render blank hostname columns without being dropped.
14. `RelationshipCsvExporter` never imports or calls either resolver, and never reads `project.canonical_relationships`/`project.observations` directly.

---

## 13. Implementation Order (Slice 1 only)

1. `networkmapper/exporters/csv_exporter.py` — add the two-column extension, sourced from `CanonicalPresentation.from_project(project)`.
2. `tests/test_csv_exporter.py` — update existing row assertions (additive trailing blanks) and add the new populated/conflicting/unmatched/determinism/no-re-resolution cases (Section 11).
3. Full existing test suite run to confirm zero regressions elsewhere (`MarkdownExporter`, `ProjectSummary`, report_run, application-level tests untouched).
4. `docs/architecture/overview.md` — a short follow-on note, mirroring PLAN-025's own Section 6, documenting `CsvExporter` as a second `CanonicalPresentation` consumer.

Slice 2 is not scheduled by this plan (Section 1); its implementation order should be proposed by the follow-on plan that adopts Sections 4/9/12(10-14).
