# Status

Plan Approved

Approval: This plan (with the Section 4 category-label correction — `connected_to` → "Connected To", no provider suffix — incorporated) was architect-approved and served as the implementation authority for FEAT-025.

Authority: [ARCH-025](../reports/ARCH-025-Canonical-Identity-Relationship-Presentation-Architecture.md) (Investigation Complete), re-grounded directly against the current codebase for this slice (`project/models.py`, `identity/models.py`, `relationships/models.py`, `observations/models.py`, `core/network_graph.py`, `reporting/project_summary.py`, `exporters/markdown_exporter.py`, `exporters/csv_exporter.py`, `application.py`, `tests/test_markdown_exporter.py`).

Implements: The first implementation slice of ARCH-025's recommended presentation/view-model layer — sprint (1) of ARCH-025 Section 17's three-part sequence ("(1) the shared view-model layer, (2) `MarkdownExporter` identity and relationship rendering, (3) `CsvExporter` identity summary columns"). This plan bundles (1) and (2) only.

Production Code Modified: Yes (Section 5).

New ADR Required: No — re-confirmed against this narrower slice specifically; see Section 9. ARCH-025 Section 15 already found no ADR trigger for the full recommendation, and this slice is a subset of it.

---

## 1. Scope of This Slice

ARCH-025's full recommendation has three sequenced parts. This plan implements only the first two:

1. A new, shared presentation/view-model layer that projects `Project.canonical_identities` and `Project.canonical_relationships` into technician-legible, device-enriched records — read-only, deriving nothing the resolvers didn't already conclude.
2. `MarkdownExporter` consuming that view-model to render canonical identity and relationship content, so the layer has a real production consumer from the moment it exists.

**Explicitly deferred to a follow-on FEAT** (not part of this plan):

- `CsvExporter` identity-corroboration summary columns (ARCH-025 Section 8/12, sequence item 3).
- The separate relationship CSV artifact (one row per distinct `(subject, category, related_subject)` claim — ARCH-025 Section 8).

This split is deliberate, not a simplification made for its own sake: ARCH-025 Section 8 itself already treats the relationship CSV as "a distinct, secondary deliverable... a structurally separate problem (a new output file, not new columns on an existing one)," and CSV identity columns are a separate, smaller design surface with no dependency the Markdown work needs. Bundling either into this slice would widen it without giving the view-model layer a second consumer that changes its design — Markdown alone already exercises every structural requirement (corroboration-state passthrough, conflict display, device enrichment with fallback, category labeling, deterministic ordering). Adding CSV now would be building ahead of the requirement that justifies it.

Topology visualization, graph layout, and any non-Markdown/non-CSV renderer are out of scope, per ARCH-025 and per this plan's own instructions — no such consumer exists yet, and none is added here.

---

## 2. Current-State Grounding (re-verified against code, not re-quoted from ARCH-025)

- `Project` (`networkmapper/project/models.py:13-49`) already carries `observations`, `canonical_identities: tuple[CanonicalIdentity, ...]`, and `canonical_relationships: tuple[CanonicalRelationship, ...]`, populated once in `application.py:192-200` immediately after `IdentityResolver`/`RelationshipResolver` run, and passed to both exporters before `ProjectSerializer` ever touches the project (`application.py:227-232`, unchanged since ARCH-025 traced it).
- **Neither exporter reads any of the three fields today.** `MarkdownExporter.export()` (`markdown_exporter.py:25-54`) builds a `ProjectSummary` and walks `project.network_graph.all_devices()` exclusively. `CsvExporter.export()` (`csv_exporter.py:12-53`) does the same. `ProjectSummary.from_project()` (`project_summary.py:22-54`) also only reads `network_graph`.
- `CanonicalIdentity` / `PropertyCorroboration` and `CanonicalRelationship` are all `@dataclass(frozen=True)` (`identity/models.py`, `relationships/models.py`) — mutation is structurally impossible, not just conventionally avoided.
- Neither canonical type stores a single resolved value: `PropertyCorroboration.observations` and `CanonicalRelationship.observations` retain every contributing `IdentityObservation`/`RelationshipObservation`; a displayed value must be derived from those, never read off a collapsed field.
- `CanonicalRelationship` has no `related_subject` field — it lives only inside `observations` (`relationships/models.py`), because a `CONFLICTING` group can carry more than one distinct `related_subject`.
- **`NetworkGraph.get_device(ip_address)` already exists** (`core/network_graph.py:19-21`) and is exactly the read-only, dictionary-backed lookup ARCH-025 Section 6/9 described building — no new lookup structure needs to be built; the view-model calls this existing method directly, since `subject`/`related_subject` are IP-address strings today (per `identity/resolver.py`'s and `relationships/resolver.py`'s own subject convention) and `NetworkGraph` is already keyed by IP address. This is a smaller footprint than ARCH-025 Section 9 anticipated (it described "building a lookup dictionary"; the dictionary already exists as `NetworkGraph._devices`, reachable via the existing accessor).
- `MarkdownExporter._display_value`/`_display_title` already establish the "render `None`/blank sensibly" convention this plan's rendering code should reuse rather than re-invent a fourth implementation of the same rule (ARCH-025 Section 4 flagged three near-duplicates already existing; a fourth is avoidable here since the new rendering lives in the same class).
- Existing tests (`tests/test_markdown_exporter.py`) construct `Project` directly (not via `Application.run()`) and rely on `canonical_identities`/`canonical_relationships` defaulting to empty tuples (`project/models.py:47-48`'s `default_factory=tuple`). Every existing test therefore already exercises the "no relationship evidence collected" empty case implicitly — this plan's empty-tuple handling must not change what those tests currently assert.

---

## 3. Presentation Model — Exact Inputs

The view-model's builder takes exactly one `Project` and reads exactly these fields, nothing else:

- `project.canonical_identities: tuple[CanonicalIdentity, ...]` — the sole iteration axis for identity presentation. Every `CanonicalIdentity` the resolver produced is a presentation candidate; `network_graph.all_devices()` is never the axis identity presentation iterates (ARCH-025 Section 6).
- `project.canonical_relationships: tuple[CanonicalRelationship, ...]` — the sole iteration axis for relationship presentation, same reasoning (ARCH-025 Section 7).
- `project.network_graph` — read only through the existing `get_device(ip_address) -> Device | None` accessor, for enrichment lookups keyed by `subject` / `related_subject`. No new field is added to `NetworkGraph`, and `all_devices()` is not called during this build (it remains the axis for `ProjectSummary` and the existing device inventory, unaffected).

Nothing else from `Project` is read by the builder — not `observations` directly (raw `IdentityObservation`/`RelationshipObservation` are reached only *through* an already-resolved `CanonicalIdentity.properties[*].observations` or `CanonicalRelationship.observations`, never independently queried), not `customer_name`/`created_date`/`modified_date` (those remain `ProjectSummary`'s concern).

For each `CanonicalIdentity`, the builder carries forward, unmodified:
- `subject` (raw string, always retained even when a `Device` match exists)
- `state` (the resolver's identity-level rollup — `WEAK`/`PROBABLE`/`CONFIRMED`/`CONFLICTING`)
- `properties` — for each `PropertyCorroboration`: `property_name`, `state`, and `observations` (retained in full — `value`, `provenance.provider`, `provenance.collection_method`, `provenance.observed_at`)

For each `CanonicalRelationship`, the builder carries forward, unmodified:
- `subject`, `category`, `state`
- `observations` (retained in full, same fields as above, plus `related_subject`)

None of these values is recomputed, reinterpreted, or overridden. They pass through exactly as the resolvers produced them.

---

## 4. Derived / Display-Only Fields Permitted in This Layer

The following are the *only* computations this layer is permitted to perform. Each is a pure projection of already-resolved data — never a new conclusion about identity or relationship truth:

1. **Device enrichment reference.** `network_graph.get_device(subject)` (and, separately, `get_device(related_subject)` per related endpoint) — a read-only lookup returning an existing `Device` or `None`. On a miss, the raw subject string is carried instead; the record is never dropped (ARCH-025 Section 6/7 no-suppression requirement).
2. **Distinct-value grouping for display.** Where a `PropertyCorroboration` or a `CanonicalRelationship` observation set contains more than one distinct `value`/`related_subject` (the `CONFLICTING` case), the view-model may group observations by their distinct value so a renderer can show "all distinct values, side by side" without re-scanning the raw tuple itself. This groups already-present data; it introduces no new value.
3. **Deterministic category label.** A fixed, hard-coded mapping from known `category` strings (`arp_neighbor`, `connected_to`, `bridge_fdb`) to a friendly label ("ARP Neighbor", "Connected To", "Bridge Forwarding Entry"), with a deterministic generic fallback (title-casing the raw category string) for any category absent from the mapping — required so a future category renders with zero code changes (ARCH-025 Section 7, Finding 5). This is string formatting over an already-decided `category` value, not a relationship-shape decision. The label must describe the canonical category itself, never the provider currently producing evidence for it — `connected_to` is deliberately labeled "Connected To" with no protocol suffix, since LLDP is not the only provider that may ever resolve to this category (a future CDP provider would corroborate the same canonical category, not a different one). Provider/collection-method provenance remains available underneath each observation (Section 3) and may be rendered there — this restriction is on the category label only, not on suppressing provenance generally.
4. **Deterministic secondary ordering.** Where the resolvers' own ordering (`identity/resolver.py` sorts identities by subject, properties by name, observations by `(provider, method, value)`; `relationships/resolver.py` sorts relationships by `(subject, category)`, observations by `(provider, method, related_subject)`) does not fully determine an order the view-model additionally needs (e.g., ordering distinct grouped values within a `CONFLICTING` set), the view-model may impose one *additional, stated, deterministic* tiebreaker. It must never depend on input/observation arrival order, and must never override an order the resolver already fixed.

Nothing else is computed. In particular, no independent-source count, no recomputed corroboration state, no synthesized "confirmed" label, and no invented related-subject or property value — all four are explicitly named as *not* permitted in Section 5.

---

## 5. Explicit Prohibition — No Re-Resolution

This is the load-bearing constraint of the entire slice, restated as concrete rules the implementation and its review must check line by line:

- The view-model **must never call, reimplement, or approximate** any logic from `IdentityResolver` or `RelationshipResolver`. It consumes `CanonicalIdentity`/`CanonicalRelationship` objects only; it never constructs one, and never derives an identity or relationship conclusion from raw `IdentityObservation`/`RelationshipObservation` data independently of an already-resolved canonical record.
- `IdentityCorroborationState` and `RelationshipCorroborationState` values are read directly from `CanonicalIdentity.state` / `PropertyCorroboration.state` / `CanonicalRelationship.state` and rendered as-is. The view-model never computes its own corroboration state, confidence level, or "confirmed by N sources" count (ARCH-025 Finding 3 — the resolver computes and discards that count internally; re-deriving it here would silently couple presentation to resolver internals with no shared, tested guarantee they stay in agreement).
- A `CONFLICTING` state is **never** collapsed to one displayed value. All distinct values/related-subjects must render, unconditionally. Picking a "best" or "most likely" value would be exactly the re-resolution ADR-012/ADR-013 forbid — the resolver deliberately declined to pick one, and presentation does not get to make that call on the resolver's behalf.
- Device enrichment is optional context, never a filter and never a prerequisite. A `CanonicalIdentity`/`CanonicalRelationship` endpoint with no matching `Device` still renders, using its raw subject string — enrichment failing is not treated as identity resolution failing.
- Raw `IdentityObservation`/`RelationshipObservation` data may be read **only** as provenance evidence *underneath* an already-resolved `CanonicalIdentity`/`CanonicalRelationship` (i.e., `canonical_record.properties[i].observations` / `canonical_record.observations`) — never queried from `Project.observations` directly, and never used to build a relationship or identity conclusion the resolvers didn't already reach. This is the exact ADR-013 "Relationship with Future Topology" boundary — "it must not shortcut relationship interpretation by reasoning from provider output directly" — applied here to Markdown instead of a future topology renderer.
- No provider-specific branching. The view-model must not special-case behavior by `provenance.provider` or `provenance.collection_method` in a way that changes which values are considered valid or how corroboration reads — those fields are provenance to display, not inputs to a decision.
- The known `RelationshipResolver` cardinality limitation (a symmetric `connected_to` reported from both ends surfaces as two independent `WEAK` records, not one `CONFIRMED` bidirectional one) is rendered faithfully, exactly as ARCH-025 Section 7 concluded. The view-model must not attempt to detect and merge these into one record — doing so would be exactly the resolver-level correction ARCH-025 explicitly scoped out, performed instead in presentation by the back door.

Code review for this slice should treat any of the above as a correctness defect, not a style preference.

---

## 6. Files Likely Affected

**New:**
- `networkmapper/reporting/canonical_presentation.py` — the view-model module: frozen dataclasses for the projected identity/relationship records, plus a `CanonicalPresentation.from_project(project: Project) -> CanonicalPresentation` builder. Sibling to `project_summary.py`, same package, same "derive reusable data, then let exporters render it" pattern.
- `tests/test_canonical_presentation.py` — unit tests for the builder, constructing synthetic `CanonicalIdentity`/`CanonicalRelationship`/`Device`/`Project` values directly (no discovery, no `Application.run()`), following `tests/test_identity_resolver.py`'s existing pattern.

**Modified:**
- `networkmapper/exporters/markdown_exporter.py` — `_render_markdown()` gains two additional top-level sections (Section 7 explains placement), sourced from `CanonicalPresentation.from_project(project)`. New private render methods only; no existing method's signature or behavior changes.
- `networkmapper/reporting/__init__.py` — export the new view-model type(s) alongside `ProjectSummary`.
- `tests/test_markdown_exporter.py` — additive test cases only (new methods), covering the new sections; no existing test method is modified, per Section 8's regression requirement.
- `docs/architecture/overview.md` — a short follow-on note added once this ships, documenting the new reporting-path consumer of `canonical_identities`/`canonical_relationships` (ARCH-025 Section 10 already flagged this document as silent on observations/identity/relationship pending implementation). This is a documentation update, not a behavior change, and can be sequenced at the end of implementation rather than blocking it.

**Not modified** (carried forward from ARCH-025 Section 12, re-confirmed for this narrower slice): `Project`, `Device`, `NetworkGraph`, `CanonicalIdentity`, `PropertyCorroboration`, `CanonicalRelationship`, `IdentityObservation`, `RelationshipObservation`, `IdentityResolver`, `RelationshipResolver`, `ProjectSerializer`, `ProjectComparator`, `CsvExporter`, `application.py`, `ProjectSummary`.

---

## 7. Placement of New Markdown Content — A Decision This Plan Makes

ARCH-025 Section 6/12 left open whether a matched canonical record renders inside its device's existing block (alongside Identity/Evidence/Classification) or as a separate section, calling this a "PLAN-025 layout decision." This plan resolves it for the first slice:

**Decision: two new top-level sections, added after the existing Device Inventory section** — `# Canonical Identity` and `# Canonical Relationships` — each iterating `canonical_identities`/`canonical_relationships` directly (per Section 3), rendering a device reference inline (hostname/IP from the matched `Device`, when present) rather than interleaving into `_render_device_section`.

**Why not in-device-context for this slice:** interleaving would require changing `_render_device_section`'s signature and content for every device, touching a code path every existing `test_markdown_exporter.py` test already exercises and asserts against — directly conflicting with this plan's goal 6 ("preserve existing report behavior unless the plan explicitly identifies a required migration"). No migration is required to satisfy ARCH-025's substantive requirements (every field ARCH-025 named — value(s), state, provenance, conflict display, device enrichment — is representable in a standalone section just as faithfully as inline). Standalone sections are strictly additive: existing sections, their order, and their content are byte-for-byte unchanged; the new sections are pure appends.

This is flagged again in Section 10 as revisable — moving to in-device-context presentation later is a rendering-layout change only, not a view-model change, since the view-model already exposes device enrichment as a field regardless of how a renderer chooses to use it.

---

## 8. Acceptance Criteria

1. `CanonicalPresentation.from_project()` exists, is pure (no I/O, no mutation), and is fully unit-testable against synthetic `CanonicalIdentity`/`CanonicalRelationship`/`Device`/`Project` values with no discovery or network access.
2. `MarkdownExporter` renders a `# Canonical Identity` section (one entry per `CanonicalIdentity`, corroboration state and per-property values/state/provenance shown, all distinct values shown for `CONFLICTING`, device-enriched when matched, raw subject otherwise) and a `# Canonical Relationships` section (one entry per `CanonicalRelationship`, directional, category-labeled with deterministic fallback, corroboration state, all distinct related subjects for `CONFLICTING`, device-enriched when matched, raw subject otherwise).
3. Every existing test in `tests/test_markdown_exporter.py` continues to pass unmodified — proving the new sections are additive and do not alter existing report content, section order, or existing section text.
4. A `Project` with legitimately empty `canonical_relationships` (no relationship-evidence flags enabled) renders the `# Canonical Relationships` section without error and without a misleading "confirmed no relationships" message (ARCH-025 Section 5's named reachable case).
5. A `Project` with legitimately empty `canonical_identities` renders equivalently for the `# Canonical Identity` section.
6. A `CanonicalRelationship` with a category absent from the friendly-label mapping renders using the deterministic generic fallback, without error and without a code change.
7. Permuting the input `observations`/`identities`/`relationships` sequence before resolution does not change the view-model's or `MarkdownExporter`'s rendered output (determinism test, mirroring ARCH-025 Section 13).
8. No test or production code path calls into `IdentityResolver`/`RelationshipResolver` from the new view-model or its exporter consumer — the only inputs are already-resolved `CanonicalIdentity`/`CanonicalRelationship` instances (verified by code review against Section 5, not just by test behavior).
9. `CsvExporter` is byte-for-byte unmodified by this slice; its existing tests are unaffected.
10. No new field is added to `Project`, `Device`, or `NetworkGraph`; no existing frozen dataclass gains a mutation path.

---

## 9. ADR-Trigger Check (re-verified for this narrower slice)

Walking ARCH-025 Section 15's six points against this slice specifically:

1. New view-model layer in `reporting/` — additive, within `ProjectSummary`'s already-established pattern. No trigger.
2. `MarkdownExporter` reading `canonical_identities`/`canonical_relationships` — explicitly anticipated future work per ADR-012/ADR-013's own Future Work sections ("UI or reporting presentation of identity" / "UI presentation of relationships or topology"), not a reversal of either decision. No trigger.
3. No persistence change, no reload-then-export path added — this slice touches nothing in `ProjectSerializer`. No trigger.
4. No change to `RelationshipResolver`'s cardinality behavior — rendered as-is (Section 5). No trigger.
5. `CsvExporter` is untouched by this slice (deferred, Section 1) — the CSV-specific ADR-trigger analysis ARCH-025 Section 15 already did for that later work is unaffected and unconsumed here.
6. Iterating `canonical_identities`/`canonical_relationships` directly rather than `network_graph.all_devices()`, with `Device` matching as optional enrichment — a presentation-traversal decision only, changing no persisted state, canonical model, or resolver behavior.

**Conclusion: no ADR is required for this slice**, consistent with ARCH-025's conclusion for the full recommendation. The same two future triggers ARCH-025 Section 15 named (a reload-then-export CLI path; `ProjectComparator` wired for cross-session historical diffing) remain the only identified future triggers, and neither is touched here.

---

## 10. Open Questions Carried Forward (not resolved by this slice)

- **In-device-context vs. standalone-section layout** (Section 7): resolved as standalone sections for this slice; whether to later move to in-device-context presentation is deferred, and would be a rendering-only change if pursued.
- **Symmetric-relationship cardinality** (ARCH-025 Section 7/16): whether `RelationshipResolver` should eventually recognize a bidirectionally-reported pair as one `CONFIRMED` relationship remains a live question for a future resolver investigation, not this slice.
- **Unresolved relationship observations** (endpoint didn't resolve, or self-loop filtered): per ARCH-025 Section 7, these remain diagnostics-only and are not surfaced in the Markdown report by this slice. Revisit only if user feedback on the shipped report indicates a need.
- **Independent-source-count exposure** (ARCH-025 Finding 3): whether `PropertyCorroboration`/`CanonicalRelationship` should eventually expose the resolver's internally-computed-and-discarded independent-source count as a stored field is a future canonical-model question, explicitly not built here — presentation shows `state` alone.
- **CSV representation of unmatched canonical identities**: deferred along with all CSV work (Section 1) to the follow-on FEAT.
- **Exact friendly-label mapping completeness**: only `arp_neighbor`, `connected_to`, `bridge_fdb` are known categories today (the three currently-implemented relationship providers); the mapping is extended, not redesigned, as new categories are added. The deterministic fallback (Section 4, item 3) makes this a non-blocking, low-stakes list to extend later.

---

## 11. Testing Strategy

All of the following require no discovery execution and no network access, mirroring `tests/test_identity_resolver.py` and the existing `tests/test_markdown_exporter.py` pattern:

- **View-model derivation** (`tests/test_canonical_presentation.py`): construct synthetic `CanonicalIdentity`/`CanonicalRelationship`/`Device`/`Project` values covering every corroboration state (`WEAK`/`PROBABLE`/`CONFIRMED`/`CONFLICTING` for identity; `WEAK`/`CONFIRMED`/`CONFLICTING` for relationship); assert the derived records carry the resolver's own state and values unchanged, plus correct device enrichment on a match and a graceful raw-subject fallback on a miss.
- **Exporter rendering** (additive cases in `tests/test_markdown_exporter.py`): construct a synthetic `Project` with populated `canonical_identities`/`canonical_relationships` and assert the new sections' text content, following the existing file's structure and its `_device_section`-style targeted-slice assertion pattern.
- **Unknown-category fallback**: a `CanonicalRelationship` with a category outside the friendly-label mapping renders via the deterministic fallback without error.
- **Determinism**: permuting input `observations` before calling the resolvers, then building the view-model from the result, produces identical rendered output.
- **Empty-tuple handling**: a `Project` with default (empty) `canonical_identities`/`canonical_relationships` — i.e., every existing test's default construction — renders both new sections without error and without a misleading message; this is the regression case proving Section 8, Acceptance Criterion 3.
- **Symmetric-category double-`WEAK` case**: a targeted test asserting two independent single-source relationship records render faithfully as two separate entries, documenting the known resolver limitation is inherited into output on purpose (Section 5, last bullet).
- **No-re-resolution guard**: a test (or code-review checklist item, if not mechanically testable) confirming the view-model module has no import of `IdentityResolver` or `RelationshipResolver`.

---

## 12. Non-Goals (Explicit)

Restated from this plan's own instructions, all confirmed still correctly excluded after grounding against the code:

- Interactive topology UI.
- Graph layout algorithms.
- SVG/PDF/Visio rendering.
- New discovery providers.
- New enrichment providers.
- New identity-resolution heuristics — `IdentityResolver` is not modified, called differently, or reimplemented.
- New relationship-resolution heuristics — `RelationshipResolver` is not modified, called differently, or reimplemented, and the known cardinality limitation is not fixed.
- Persistence-format changes — `ProjectSerializer` is not modified; this slice needs no reload-then-export path (Section 9).
- Speculative generic graph frameworks — no graph/topology abstraction is introduced; the view-model is a flat, technician-report-shaped projection, not a general-purpose graph model.
- `CsvExporter` changes of any kind (Section 1 — sequenced as a follow-on FEAT).
- `ProjectComparator` wiring (unaffected, per ARCH-025 Section 11 — still blocked on non-persistence for its intended cross-session use case, unrelated to this slice).
- `docs/architecture/overview.md`'s broader restructuring — only the narrow addition named in Section 6.

---

## 13. Implementation Order

1. `networkmapper/reporting/canonical_presentation.py` + `tests/test_canonical_presentation.py` — the view-model layer, fully tested in isolation, no exporter changes yet.
2. `networkmapper/reporting/__init__.py` export update.
3. `networkmapper/exporters/markdown_exporter.py` new sections + additive `tests/test_markdown_exporter.py` cases.
4. Full existing test suite run to confirm zero regressions in pre-existing `MarkdownExporter`/`CsvExporter`/`ProjectSummary` tests.
5. `docs/architecture/overview.md` follow-on note.

CSV work (identity summary columns; separate relationship CSV artifact) is not scheduled here — it is the subject of a follow-on FEAT once this slice ships and the view-model's shape has been exercised by a real consumer.
