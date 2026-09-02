# ARCH-025 — Canonical Identity and Relationship Presentation Architecture

# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — the recommended architecture operates entirely within ADR-005's read-only constraint and ADR-011/012/013's existing observation, identity, and relationship semantics, without expanding persistence, evidence collection, or resolver behavior. A new ADR would only be triggered if a future reload-then-export pathway or a persisted-canonical-data use case (e.g., historical relationship comparison) is later prioritized — see Section 15.

Recommended Next Sprint:
PLAN-025 – Canonical Identity and Relationship Presentation Implementation Plan, translating this report's recommended view-model layer and exporter extensions into a concrete file-level change inventory.

---

## 1. Executive Summary

`IdentityResolver` and `RelationshipResolver` have produced structurally rich, already-corroborated output — `CanonicalIdentity` and `CanonicalRelationship` — since FEAT-008A/FEAT-009A (verified via `git log` against `identity/resolver.py` and `relationships/resolver.py`: each has exactly one commit, and the corroboration logic was present from that commit, not added later), but no presentation surface has ever read either type. This investigation confirms that gap is total: `MarkdownExporter`, `CsvExporter`, `ProjectSummary`, and `ClassificationWorkbench` read only `Project.network_graph`; none touches `Project.observations`, `Project.canonical_identities`, or `Project.canonical_relationships`.

**The data model is not a flat bag waiting to be dumped into a report.** Both canonical types are two-level, evidence-preserving structures — `CanonicalIdentity` nests per-property `PropertyCorroboration` records, each retaining every contributing `IdentityObservation` rather than collapsing to one value; `CanonicalRelationship` retains every contributing `RelationshipObservation` and deliberately has no single `related_subject` field, because a `CONFLICTING` relationship has more than one. Presenting this data honestly requires a rendering layer that understands corroboration state, not a field-by-field transcription.

**No existing seam is a clean fit.** `ProjectSummary` is an aggregate-counts view model consumed only by `MarkdownExporter`; extending it to carry nested per-device/per-relationship detail would break its own "summary" semantics and still leave `CsvExporter` — which doesn't consume `ProjectSummary` today — without a shared path. Direct per-exporter traversal is the pattern already producing three near-duplicate `_display_value` implementations across the codebase; applying it to structurally richer canonical data would compound that duplication. The recommended architecture (Section 4) is a new, purpose-built view-model layer, a sibling to `ProjectSummary` rather than an extension of it.

**The fresh-run/reloaded-project question turned out to have a clean, already-enforced answer.** Tracing `application.py:203-233` directly shows both exporters run *before* `ProjectSerializer.save()`/`load()` in every current invocation — there is no code path today that exports a reloaded `.nmproj`. Since `observations`, `canonical_identities`, and `canonical_relationships` are deliberately non-persisted (ARCH-019, for ADR-011/012 traceability reasons), this means the reload-degradation question this investigation was charged to answer is not yet a reachable scenario at all. No persistence change is required, and none is recommended.

**Presentation can and should render the resolver's output faithfully, including its known limitations, without fixing them.** The `RelationshipResolver`'s one-canonical-relationship-per-`(subject, category)` cardinality rule means a symmetric link (e.g., LLDP `connected_to` reported from both ends) surfaces as two independent `WEAK` records rather than one `CONFIRMED` one — a limitation the resolver's own docstring calls "known, accepted." Presentation does not require correcting this to be correct itself; rendering two `WEAK` records is an honest representation of what the system currently knows. This is noted as a live question (Section 16), not solved here.

**`ProjectComparator` is out of scope.** Its intended use case — diffing a historical run against a current one (ROADMAP Phase 9) — requires the historical `Project` to be reloaded via `ProjectSerializer.load()`, and reloaded projects never carry canonical data (Section 5); that specific path is genuinely blocked, not merely deferred. Identity/relationship-aware diffing is not structurally impossible in general — two fully populated, same-session `Project` instances would diff correctly with no persistence change — but no CLI path invokes `ProjectComparator` that way today either, so wiring it remains out of this report's scope regardless (Section 11).

No production code is proposed for change by this report.

---

## 2. Direct Answers

1. **Presentation boundary (Section 4):** A new, purpose-built presentation/view-model layer — a sibling module to `ProjectSummary` inside `networkmapper/reporting/`, not an extension of it, and not direct per-exporter traversal.
2. **Fresh-run vs. reloaded (Section 5):** Not currently a live distinction — both exporters run only against fresh, in-memory `Project` instances today (`application.py:203-233`, confirmed before the save/load round-trip). No persistence change is required or recommended.
3. **Identity presentation (Section 6):** Structured display, iterating `canonical_identities` directly rather than devices — value(s), the resolver's own corroboration state (never recomputed), and structured provenance — conflicting values shown side-by-side, never silently resolved to one. Matched subjects may render in device context; unmatched subjects remain representable via their raw identifier. Exact layout for both is a PLAN-025 decision.
4. **Relationship presentation (Section 7):** Directional, category-labeled entries, iterating `canonical_relationships` directly rather than devices, grouped by subject, one entry per `CanonicalRelationship`, with related-subject enriched with a device reference when a match exists (never required, never a prerequisite for representability); the known symmetric-link cardinality limitation is rendered faithfully, not corrected.
5. **Multi-format semantics (Section 8):** Structured derivation (grouping, resolver-provided state, device enrichment, structured provenance) is shared; textual formatting and layout are renderer-specific. Identity fits the existing CSV device-row shape as added summary columns, deliberately coarse. Relationships do not fit that shape; the recommended separate CSV artifact emits one row per distinct `(subject, category, related_subject)` claim — not one row per `CanonicalRelationship`, since a `CONFLICTING` record has more than one — sequenced as a follow-on rather than bundled with the primary work.
6. **Read-only compliance (Section 9):** Confirmed. Every canonical/observation dataclass involved is already `frozen=True`; the one new operation (subject→`Device` enrichment lookup, with a raw-subject fallback on a miss) is a read-only dictionary build over `network_graph.all_devices()`.
7. **Existing architecture reconciliation (Section 10):** Fully consistent with ADR-005 and ADR-011/012/013; ADR-012 and ADR-013 each explicitly name "UI or reporting presentation" as deferred future work this report resolves, not settled policy this report revisits. `docs/architecture/overview.md` will need a follow-on update at implementation time (it currently omits observations/identity/relationship entirely) — not part of this investigation.
8. **Testing (Section 13):** Fully unit-testable against synthetically constructed `CanonicalIdentity`/`CanonicalRelationship`/`Device`/`Project` instances, no discovery or network access required, following the pattern already established in `test_identity_resolver.py` and `test_markdown_exporter.py`; coverage must also confirm the presentation layer preserves resolver-guaranteed deterministic ordering rather than redefining it, including a deterministic secondary order for `CONFLICTING` relationships expanded into multiple CSV rows.
9. **Scope exclusions (Section 14):** All eight named exclusions hold. None proved load-bearing; `ProjectComparator` wiring is excluded because nothing invokes it today, and its one anticipated use case (cross-session historical comparison) is specifically blocked by non-persistence — same-session comparison is not structurally impossible, just unreached by any current code path.

---

## 3. Current-State Grounding

`Project` (`networkmapper/project/models.py`) carries `network_graph`, `observations: list[IdentityObservation | RelationshipObservation]`, `canonical_identities: tuple[CanonicalIdentity, ...]`, and `canonical_relationships: tuple[CanonicalRelationship, ...]`. The sole production construction site is `application.py:171-177`, immediately following resolution:

```python
identities = IdentityResolver().resolve(engine.observations)
relationships = RelationshipResolver().resolve(engine.observations, identities)

project = Project(
    customer_name="Test Network",
    network_graph=graph,
    observations=engine.observations,
    canonical_identities=identities,
    canonical_relationships=relationships,
)
```

Every currently implemented presentation-shaped consumer of `Project` — `MarkdownExporter.export()`, `CsvExporter.export()`, `ProjectSummary.from_project()`, `ClassificationWorkbench.generate()` — reads only `project.network_graph.all_devices()` (plus, for `ProjectSummary`, `customer_name`/`created_date`/`modified_date`). None reads `observations`, `canonical_identities`, or `canonical_relationships`. This was a deliberate, named exclusion, not an oversight: ARCH-019 states outright that "Adding two unread fields to `Project` does not change either exporter's output. Consuming the new fields in either exporter is explicitly excluded from this sprint's scope."

**Data model, exact shape** (`networkmapper/identity/models.py`, `networkmapper/relationships/models.py`, `networkmapper/observations/models.py`):

```python
class IdentityCorroborationState(StrEnum):
    WEAK = "weak"; PROBABLE = "probable"; CONFIRMED = "confirmed"; CONFLICTING = "conflicting"

class PropertyCorroboration:
    property_name: str
    state: IdentityCorroborationState   # never PROBABLE at this level
    observations: tuple[IdentityObservation, ...]

class CanonicalIdentity:
    subject: str
    state: IdentityCorroborationState   # rolled up from all properties
    properties: tuple[PropertyCorroboration, ...]

class RelationshipCorroborationState(StrEnum):
    WEAK = "weak"; CONFIRMED = "confirmed"; CONFLICTING = "conflicting"   # no PROBABLE

class CanonicalRelationship:
    subject: str
    category: str                        # e.g. "arp_neighbor", "connected_to", "bridge_fdb"
    state: RelationshipCorroborationState
    observations: tuple[RelationshipObservation, ...]   # related_subject lives here, not on CanonicalRelationship

class IdentityObservation:
    subject: str; property_name: str; value: str; provenance: ObservationProvenance

class RelationshipObservation:
    subject: str; related_subject: str; category: str; provenance: ObservationProvenance

class ObservationProvenance:
    provider: str; collection_method: str; observed_at: datetime; source_run: str
```

All of these are `@dataclass(frozen=True)`. Two structural facts drive everything downstream in this report:

- **Neither canonical type stores a single resolved value.** `PropertyCorroboration.observations` and `CanonicalRelationship.observations` retain every contributing observation; a "the value is X" claim must be derived by a presentation layer, not read off a field.
- **`RelationshipResolver` groups by `(subject, category)`, not `(subject, related_subject, category)`.** One `CanonicalRelationship` exists per subject per category, by design — "Grouping by the full triple would put every observation sharing that triple in the same group by construction, making conflicting evidence... structurally undetectable" (resolver docstring). A subject with a relationship to two different neighbors under the same category collapses into one `CONFLICTING` record, not two `CONFIRMED` ones.

`RelationshipResolver.resolve()` also excludes — but does not delete — any observation whose `subject` or `related_subject` doesn't resolve to a supplied `CanonicalIdentity`, or that is a self-loop:

```python
valid_subjects = frozenset(identity.subject for identity in identities)
preprocessed_observations = [
    o for o in relationship_observations
    if o.subject in valid_subjects and o.related_subject in valid_subjects and o.subject != o.related_subject
]
```

The excluded observation remains, untouched, wherever it already lived (typically `Project.observations`); it simply doesn't produce a `CanonicalRelationship` this run.

---

## 4. Presentation Boundary — Alternatives Considered

Three candidates were evaluated against the actual current code, not assumed:

**(a) Direct exporter traversal.** Each exporter reads `project.canonical_identities`/`canonical_relationships` and formats them inline, the same way each currently walks `network_graph.all_devices()` independently. **Rejected.** This is the exact pattern already producing duplicated logic in the codebase today — `MarkdownExporter._display_value`, `CsvExporter._stringify_value`, and `ClassificationWorkbench._display_value` are three independent implementations of the same "render `None` sensibly" rule, with no shared abstraction forcing convergence. Canonical identity/relationship rendering is materially more complex than that (nested observations, corroboration states, conflict display, provenance) — direct traversal offers no structural guarantee that `MarkdownExporter` and a future `CsvExporter` relationship output would label a `CONFLICTING` state identically, or agree on what counts as the "headline" value for a `WEAK` property.

**(b) Extend `ProjectSummary`.** Add identity/relationship fields to the existing summary dataclass. **Rejected.** `ProjectSummary` is an aggregate-statistics object (`total_devices`, `device_type_counts`, `vendor_counts`) consumed only by `MarkdownExporter`'s executive-summary section. Canonical identity/relationship presentation is inherently per-entity detail (each device's property table, each relationship's endpoints and state), not an aggregate count — forcing it in would make `ProjectSummary` stop being a summary. It also doesn't solve the multi-format problem: `CsvExporter` doesn't consume `ProjectSummary` today, so extending it wouldn't give CSV a path either; a genuinely separate mechanism would still be needed.

**(c) A new shared presentation/view-model layer**, structurally a sibling to `ProjectSummary` (same `reporting/` package, same "derive reusable data, then let exporters render it" pattern already documented in `docs/architecture/overview.md`'s Reporting Path section), but scoped to per-entity canonical detail rather than aggregate counts. **Recommended.** This mirrors the one piece of existing architecture that already works this way — `ProjectSummary` deriving data that `MarkdownExporter` renders — while correctly matching the shape of the new data (per-device, per-relationship, not aggregate). It gives both current exporters, and any exporter added later, one place to obtain a technician-legible representation (resolver-provided corroboration state, device-enriched references where a match exists, structured provenance) without re-deriving that logic per format.

This is not assumed as correct because it is the leading existing seam — (b) was evaluated on its own merits and rejected specifically because its shape doesn't match the data, independent of any preference for reusing what already exists.

---

## 5. Fresh-Run vs. Reloaded Project Behavior

Tracing the actual runtime sequence in `application.py` resolves this cleanly:

```
168-177  identities/relationships resolved, Project constructed (fully populated)
203-206  CsvExporter().export(project, ...)         ← fresh, fully-populated project
208-212  MarkdownExporter().export(project, ...)    ← fresh, fully-populated project
227      ProjectSerializer.save(project, ...)
229-231  loaded_project = ProjectSerializer.load(...)   ← round-trip verification only
233-237  device-count comparison printed; loaded_project is never exported
```

**Both exporters run before the save/load round-trip, against the same in-memory `Project` that resolution just populated.** `loaded_project` exists solely to verify device-count integrity after a round trip; it is never passed to `MarkdownExporter` or `CsvExporter`. There is currently no code path anywhere in the CLI that reloads a `.nmproj` file and then exports it.

Given `ProjectSerializer`'s save/load pair deliberately omits `observations`, `canonical_identities`, and `canonical_relationships` — for the traceability reason ARCH-019 names explicitly ("a reloaded `Project` carrying conclusions with no retained evidence behind them... directly contradict[s] ADR-011/ADR-012's traceability requirement") — a reloaded `Project` would present these fields as empty tuples if it were ever exported. But because no such export path exists today, **this is not a live architectural problem to solve, only a latent one to note.**

Two direct consequences for the recommended design:

- **No persistence change is required.** The presentation layer can assume it is always handed a freshly-resolved `Project`. Nothing about this recommendation should be read as license to add fields to `ProjectSerializer`'s save/load payload.
- **A genuinely reachable "empty" case still exists within fresh-run scope**, and must be handled: a technician who runs discovery without enabling any relationship-evidence flag (`--snmp-arp`, `--snmp-lldp`, `--snmp-bridge-fdb`) produces a fresh `Project` with a legitimately empty `canonical_relationships` tuple — not because of reload, but because no relationship provider ran. Presentation must degrade gracefully here (omit the section or state plainly that no relationship evidence was collected) regardless of *why* the tuple is empty; it does not need to, and should not try to, distinguish "empty because reload" from "empty because no evidence" from "empty because everything conflicted to nothing," since only the first of those is even reachable today and none of the three is currently distinguishable from the data alone. If a reload-then-export path is added later, this same empty-tuple handling continues to work identically. See Section 16 for the disambiguation question this defers.

**If persistence changes become necessary later** — e.g., to support a reload-then-export CLI feature, or the ProjectComparator historical-comparison use case (Section 11) — that is an explicit ADR trigger, not something this report's recommendation silently assumes or paves the way for. See Section 15.

---

## 6. Identity Presentation

`CanonicalIdentity` should not be dumped as-is. What's technician-useful, evaluated field by field:

- **`subject`** — currently a raw IP string, and the view-model's primary iteration axis is `Project.canonical_identities` itself, not `network_graph.all_devices()` (architectural requirement, corrected this pass): every `CanonicalIdentity` the resolver produced is a presentation candidate regardless of whether a `Device` exists for it. The view-model attempts to enrich each one with the corresponding `Device` (matching on IP) so identity information can appear alongside the hostname/vendor a technician already recognizes — but this is optional enrichment layered onto an already-complete iteration, not a prerequisite for the record to appear in output at all (Finding 4). Current providers make the match highly likely — `arp_neighbor_provider.py:97` and `lldp_neighbor_provider.py:130` both gate `IdentityObservation` emission on `discovered_ips` built from the live device list, and `nmap_provider.py`'s observations mirror a value the same call already wrote to `Device` — but this is an observed convention across current providers, not a type-level contract anything enforces. A `CanonicalIdentity` must never be dropped from presentation because its `subject` fails to match a `Device`: on a lookup miss, the view-model renders the raw `subject` string in place of a device reference, never raises, skips the record, or invents a device. A matched subject may be rendered in device-context presentation (e.g., alongside `MarkdownExporter`'s existing Identity/Evidence/Classification blocks); an unmatched subject must remain representable using its raw subject identifier through some device-independent treatment. Exact layout for both cases — whether matched and unmatched records share one rendering path or two, and what an unmatched entry looks like — is a PLAN-025 decision (Finding 8); this report establishes only that the capability is required, not its concrete form.
- **Resolved properties** — each `PropertyCorroboration` should render as one entry: property name, value(s), and the resolver's own `state`. For `WEAK`/`CONFIRMED`, one value, with the resolver's `state` label treated as authoritative. The presentation layer does not recompute an independent-source count to caption it (Finding 3): `IdentityResolver._resolve_property` (`identity/resolver.py:106-121`) computes and discards that count internally — neither `PropertyCorroboration` nor `CanonicalIdentity` stores it — and re-deriving it in the view-model would silently couple presentation to the resolver's independence algorithm with no shared, tested guarantee the two stay in agreement if that algorithm ever changes. A "confirmed by N sources" style label is not built here; if it's wanted later, it should come from a canonical-model change that stores the count explicitly, tracked as a live question (Section 16), not from view-model-side recomputation. For `CONFLICTING`, **all distinct values must be shown side by side**, not resolved to one — collapsing a conflict to a single displayed value would misrepresent data the resolver went out of its way to preserve, and would hide information a technician can actually use (e.g., stale SNMP `sysName` vs. current DNS hostname).
- **Corroboration state** — the resolver's per-property `state` shown alongside each property, plus the resolver's identity-level rollup `state` (`WEAK`/`PROBABLE`/`CONFIRMED`/`CONFLICTING`) as a quick-scan summary at the top of the device's identity block. Both are read directly from `CanonicalIdentity`/`PropertyCorroboration`, never re-derived.
- **Conflicting evidence** — must be surfaced, never suppressed, per the above. This is the one place presentation choice has real stakes: silently picking a value would be a presentation-layer judgment call the underlying architecture explicitly declined to make (no `CanonicalIdentity` field privileges one value), and making that call implicitly in an exporter would be a bigger decision than "how do we render this."
- **Provenance/evidence references** — the view-model exposes structured provenance per observation (`provider`, `collection_method`, `observed_at` where useful, e.g. to explain staleness), not a pre-formatted string (Finding 7); each renderer decides how to display it — a table column, an inline annotation, a footnote. This is what makes a `CONFIRMED` or `CONFLICTING` label explicable rather than a bare badge.

The presentation must be structured and technician-legible — property, value(s), corroboration state, and provenance per canonical identity, whether or not it is device-matched — not a transcription of `CanonicalIdentity`'s internal Python structure. The exact layout (table, list, subsection, or equivalent, for both matched and unmatched cases) is a PLAN-025 decision, not fixed here (Finding 8), consistent with how relationship layout is already deferred in Section 7.

---

## 7. Relationship Presentation

- **Primary iteration axis** — like identity presentation (Section 6), the view-model iterates `Project.canonical_relationships` directly, not `network_graph.all_devices()`; a `CanonicalRelationship` is a presentation candidate regardless of whether its `subject` or `related_subject` matches a `Device`, subject to the same no-suppression requirement.
- **Directional** — every `CanonicalRelationship` is `subject → related_subject`(s) by construction; presentation must show direction explicitly (e.g., an arrow or "from/to" framing), never imply symmetry the data doesn't claim.
- **Category** — known categories (`arp_neighbor`, `connected_to`, `bridge_fdb`) may receive friendly labels ("ARP Neighbor", "Connected To (LLDP)", "Bridge Forwarding Entry"), consistent with how `MarkdownExporter` already humanizes other internal names (`_display_title`). Since ADR-013 deliberately declines to freeze a category taxonomy, an unknown future category has no entry in that mapping by definition — it must fall back to a deterministic generic label derived from the raw category string (e.g., title-casing it), never omitted or left unhandled (Finding 5). This means a future category is renderable with zero presentation-layer code changes; adding a dedicated friendly-label mapping entry later is an optional wording improvement, not a prerequisite.
- **Source/related subject** — `related_subject` (read from `CanonicalRelationship.observations`, since there's no field for it directly on the canonical record) is enriched with a `Device` reference the same way `subject` is (Section 6), when a match exists; on a lookup miss the raw `related_subject` identifier is rendered instead, never suppressed.
- **Corroboration/confidence** — the resolver's own `WEAK`/`CONFIRMED`/`CONFLICTING` state, treated as authoritative and never recomputed, same visual treatment as identity (Section 6) for consistency across the report. `CONFLICTING` here means the group's observations disagree on `related_subject` — render all distinct claimed neighbors, not one.
- **Provenance** — which provider/collection method produced each observation, same treatment as identity.
- **Multiple relationships from one subject** — because cardinality is capped at one `CanonicalRelationship` per `(subject, category)` (Section 3), a subject with both an ARP-neighbor claim and an LLDP `connected_to` claim shows as two separate records grouped together under that subject — in device-context presentation when matched, under the raw subject identifier when not (Section 6) — one entry per category, not one entry per device.
- **Unresolved relationship observations vs. canonical relationships** — these are evidence that didn't resolve this run (unknown endpoint, or filtered self-loop), not evidence that's wrong. Recommendation: **do not surface these in the technician-facing Markdown/CSV report.** They serve a diagnostic purpose (why didn't a link show up?) better matched to existing console/diagnostics output than to the polished customer-facing report; including them risks conflating "here is what we know about your network" with "here is what our discovery process couldn't resolve," which are different audiences and different documents. This is a scoping judgment, not a technical constraint — flagged as revisable in Section 16.
- **The existing cardinality limitation** — a symmetric category like `connected_to`, reported independently from both ends of a link, produces two `WEAK` records (one per subject) rather than one `CONFIRMED` bidirectional one, because the two directions land in different `(subject, category)` groups. Per the instruction not to solve unrelated resolver limitations unless presentation cannot be correct without doing so: **presentation can be correct without fixing this.** Rendering "Device A → Device B (connected_to, single-source)" and, separately, "Device B → Device A (connected_to, single-source)" is an honest, faithful representation of the resolver's actual current output — not a presentation defect. It will look less tidy than a single confirmed bidirectional link would, which is worth flagging as a live question (Section 16) for a possible future `RelationshipResolver` enhancement, but is explicitly out of this investigation's scope to solve.
- **Projection into flat formats** — a single `CanonicalRelationship` may itself contain multiple distinct related subjects when `CONFLICTING` (Section 3). Any format that cannot represent a one-to-many field in one row (CSV, specifically) must expand such a record into multiple rows rather than collapsing them into a delimited value list (Section 8) — this is a rendering consequence of the data's actual shape, not a new relationship-presentation rule.

---

## 8. Multi-Format Semantics

**Shared across formats (belongs in the view-model layer):** grouping observations by property/category, reading the resolver's own corroboration `state` as authoritative — never recomputed (Finding 3) — resolving `subject`/`related_subject` strings to `Device` references where a match exists, with a raw-subject fallback otherwise (Finding 4), and exposing structured provenance data (`provider`, `collection_method`, `observed_at`) per observation. **Textual formatting is not shared** (Finding 7): the shared layer produces structured data, not a pre-formatted human-readable string; each renderer independently decides how to render a provider name, a timestamp, or a state label into text, including truncation and column layout. If `MarkdownExporter` and a future relationship-aware `CsvExporter` disagreed about which `state` a `CanonicalRelationship` carries, that would be a correctness bug — disagreeing about how that state's label is capitalized or punctuated would not be.

**Renderer-specific (does not belong in the shared layer):** layout, textual formatting, and — critically — how much of the shared structure a given format can represent at all. Markdown can afford full nested detail — every property, every contributing observation, indented per device. CSV's flat row/column shape cannot represent a variable-length nested list without an unreadable delimiter hack, so CSV necessarily renders a coarser projection (state labels, not the full observation list) of the same shared view-model output. This is not a shared-vs-renderer-specific split that treats CSV as broken or lesser — it's a legitimate case where different renderers consume different-depth projections of one correct underlying derivation.

**Does graph-shaped relationship data map cleanly to CSV? No — evaluated directly, not assumed.** The existing `CsvExporter` output is one row per device, a natural fit for identity (which is already one-per-device). Relationships are not one-per-device; they're edges between devices, and — because a `CONFLICTING` `CanonicalRelationship` carries more than one distinct `related_subject` (Section 3) — they are not even reliably one-per-`CanonicalRelationship`. Three options were considered:

- Force relationships into the existing device row (e.g., a delimited "Related Devices" column). **Rejected** — reintroduces the unreadable delimiter-hack problem, and silently truncates or garbles multi-relationship devices.
- A separate CSV artifact with **one row per distinct `(subject, category, related_subject)` claim** — not one row per `CanonicalRelationship` (corrected per Finding 1: a single `CanonicalRelationship` does not have one related subject to put in one row when it's `CONFLICTING`, so "one row per `CanonicalRelationship`" is not representationally valid for that case). For `WEAK`/`CONFIRMED` groups — exactly one distinct `related_subject` — this normally produces one row. For `CONFLICTING` groups it produces multiple rows, one per distinct claimed `related_subject`, sharing the same `subject`, `category`, and `state=CONFLICTING`. Each row's provenance reflects only the observations supporting *that row's* `related_subject`, not the whole group's observations undifferentiated. No related-subject value is ever collapsed into a delimited field. **Recommended**, as a distinct, secondary deliverable rather than bundled into the same change as identity presentation, since it is a structurally separate problem (a new output file, not new columns on an existing one) with its own, smaller design surface.
- Explicit deferral of relationship CSV output entirely, shipping only identity summary columns on the existing device row now. **Acceptable fallback** if PLAN-025 needs to trim scope, but not the default recommendation — the shape mismatch is well-understood enough (per the above) that deferral would be a sequencing choice, not a sign the problem is unsolved.

**Row ordering for the expanded projection** (Finding 9): because one `CanonicalRelationship` can now expand into multiple CSV rows, that expansion needs a deterministic secondary order beyond the resolver's own `(subject, category)` sort (`relationships/resolver.py:121-123`) — e.g., rows for one `CanonicalRelationship` ordered by `related_subject` — so rendered row order cannot depend on input observation order. This is presentation-layer ordering *of an already-resolved group*, not a redefinition of resolver ordering semantics, and must be covered by a dedicated test (Section 13).

Recommendation: identity corroboration state added to the existing device row as a deliberately coarse projection (Finding 6) — it must preserve the canonical identity/corroboration state, must never substitute a preferred conflicting value, and must never imply that an existing single-valued `Device` field (e.g. `Device.hostname`, which is populated independently of `CanonicalIdentity` and not linked to it anywhere in the codebase) resolves a canonical conflict. Detailed conflicting values and their provenance require a richer, per-property presentation than the existing flat, one-row-per-device CSV can provide — that detail belongs in Markdown, not because CSV formally depends on Markdown being generated (it doesn't; each exporter remains independently runnable), but because CSV's row shape cannot represent variable-length conflicting evidence without the delimiter-hack problem already rejected above. The exact CSV columns, and whether a compact conflict indicator or property-level summary is worth adding beyond the corroboration-state label, are PLAN-025 decisions, not fixed here. Relationships get a separate `(subject, category, related_subject)`-row CSV file, sequenced after the primary Markdown/identity work.

**Can unmatched canonical records be represented in CSV? It depends on which CSV — determined directly, not assumed.** The relationship CSV recommended above already satisfies the no-suppression invariant without further change: it is a separate artifact whose primary iteration axis is `canonical_relationships` itself, not `network_graph.all_devices()` (Section 7), so an unmatched `subject`/`related_subject` renders using its raw identifier exactly like a matched one, just without device enrichment. The identity summary columns on the *existing* device-row CSV are different, and here the answer is **no**: that CSV is structurally one row per `Device` (`CsvExporter.export()` iterates `network_graph.all_devices()`), so a canonical identity with no matching `Device` has no row to carry summary columns on. Inventing a placeholder device row to hold it would misrepresent the file's established semantics — every existing row means "a device was discovered here," and a synthetic row would corrupt anything downstream that counts rows as devices (device counts, per-vendor tallies). This is a genuine limitation of that specific format, not a suppression of the record: the no-suppression invariant is a property of the presentation architecture as a whole (at least one renderer must represent every canonical record), not a requirement that every individual renderer independently represent every record — Markdown, whose primary iteration axis is `canonical_identities` itself (Section 6), remains the representable surface for unmatched identities regardless of this CSV's limitation. Whether unmatched identities eventually warrant a CSV representation of their own — mirroring the relationship CSV's device-independent design — is deferred to PLAN-025, not resolved here (Section 16).

---

## 9. Read-Only Compliance

Re-checked ADR-005 against the recommended design, not assumed satisfied. ADR-005's text: *"Presentation logic should never modify project data... Exporters remain read-only consumers of project data."*

Every dataclass this design touches — `CanonicalIdentity`, `PropertyCorroboration`, `CanonicalRelationship`, `IdentityObservation`, `RelationshipObservation`, `ObservationProvenance` — is `@dataclass(frozen=True)`; Python raises on attempted mutation, so the constraint is structurally enforced, not merely a convention the new code has to remember to follow. The one new operation this design introduces — building a `subject`/IP → `Device` lookup dictionary from `network_graph.all_devices()` for enrichment, with a raw-subject fallback on a miss (Sections 6-7, Finding 4) — is a read: it constructs a new local dict, does not modify any `Device` instance, mirroring `ClassificationWorkbench`'s existing pattern of operating on throwaway copies (`replace(device)`) rather than stored state. No proposed change writes to `Project`, `Device`, `NetworkGraph`, or any observation/canonical object. The recommendation is fully compliant with ADR-005 as re-verified.

---

## 10. Reconciliation with Existing Architecture

- **ADR-005** — satisfied, per Section 9.
- **ADR-011** (bounded observation model) — the observation layer's scope was explicitly limited to identity resolution, relationship resolution, and future lifecycle/change-detection analysis, and explicitly does not replace `Device`. This design doesn't touch `Device` or observation semantics; it only adds a rendering path over resolver output. No expansion of ADR-011's bounds.
- **ADR-012** (identity resolution) — its own Future Work section names *"UI or reporting presentation of identity"* as explicitly deferred, unauthorized-but-anticipated work. ARCH-025 is that deferred investigation being taken up, not a revision of ADR-012's decisions.
- **ADR-013** (relationship resolution) — same pattern: *"UI presentation of relationships or topology"* is named future work. ADR-013's Relationship-with-Topology principle — *"Topology renders interpreted relationships; it is not responsible for relationship truth, and it must not shortcut relationship interpretation by reasoning from provider output directly"* — directly constrains this design: the presentation layer must derive its output from `canonical_relationships` (the resolver's conclusions), never by re-deriving relationships from raw `RelationshipObservation`s independently of the resolver. Raw observations may still be read *underneath* an already-resolved category, to show supporting evidence for a conclusion the resolver already reached (Section 7's provenance display) — that is showing evidence behind a conclusion, not re-deciding it.
- **ARCH-014** — set the precedent this design follows directly: relationship presentation should have *"the same read-only, presentation-layer relationship exporters already have to `Project`"* that topology was always intended to have. This design extends that existing exporter-to-`Project` relationship rather than inventing a new one.
- **`docs/architecture/overview.md`** — confirmed to currently omit observations, identity, and relationship subsystems entirely (it predates ADR-011/012/013). This document is scoped to *implemented* architecture only, per its own convention, so it is correctly silent until this design ships — but implementation of PLAN-025 should include an update to its Exporters/Reporting Path sections. That update is a follow-on task at implementation time, not part of this investigation.

No conflict with any existing ADR or ARCH was found. No new ADR is triggered by the recommended architecture itself (see Section 15 for the conditions under which one would be).

---

## 11. `ProjectComparator` — Evaluated Separately

`ProjectComparator.compare()` (`networkmapper/comparison/project_comparator.py`) returns a plain `ComparisonResult` dataclass — added/removed/hostname-changed/ip-changed device lists plus summary counts — built entirely from `network_graph.all_devices()` on both sides. It renders nothing: no formatted strings, no Markdown, no file output. **Structurally this is a computation concern, analogous to `ProjectSummary`, not a presentation concern** — something that would consume it (an exporter, a report section) is the actual presentation layer, and no such consumer currently exists (it's referenced only by its own module and its own test).

The instruction was not to assume it's a presentation consumer merely because it reads `Project` — evaluated directly, it isn't one, and identity/relationship-aware diffing would be a natural extension of its existing computation-only pattern (new `ComparisonResult` fields, same shape) rather than a dependency on the presentation layer this report recommends.

**Wiring it for identity/relationship-aware comparison is blocked for its intended use case, but the claim must be scoped precisely** (Finding 2). `ProjectComparator.compare()` takes two `Project` instances, and its natural use case (per ROADMAP Phase 9's "historical comparison") is comparing a past run against a current one — meaning the historical side is necessarily loaded via `ProjectSerializer.load()`. Since `canonical_identities`/`canonical_relationships`/`observations` are not persisted (Section 5), a loaded `Project`'s canonical fields are always empty tuples, so diffing against a *reloaded* historical project has nothing on the historical side to compare — that specific, intended path is genuinely blocked by non-persistence, not merely deferred.

This is narrower than saying the capability is unachievable in general. Two fully populated, same-session `Project` instances (neither one reloaded) would diff correctly today with no persistence change at all — nothing in `ProjectComparator` or the resolvers prevents that; the resolvers' output is ordinary immutable data any caller can hand to `compare()`. No code path calls `ProjectComparator` that way currently, so the practical scope exclusion still holds — but for the more precise reason that nothing invokes same-session comparison today, and the one use case that *is* anticipated (cross-session historical comparison) is the one blocked by non-persistence, not because identity/relationship comparison is structurally impossible.

---

## 12. Architectural Impact and File-Level Expectations

No code is proposed for change by this report; the following describes expected impact for the PLAN/FEAT stage, at a level appropriate to an investigation.

**New:**
- A view-model module in `networkmapper/reporting/` (sibling to `project_summary.py`) responsible for projecting `Project.canonical_identities`/`canonical_relationships` into technician-legible records, plus a subject→`Device` enrichment lookup built from `network_graph.all_devices()`, with a raw-subject fallback on a miss (Finding 4). Exact naming and dataclass shape are implementation-stage decisions, not fixed here.
- A separate CSV output path emitting one row per distinct `(subject, category, related_subject)` claim, not one row per `CanonicalRelationship` (Section 8), sequenced as a follow-on to the primary work.

**Modified:**
- `networkmapper/exporters/markdown_exporter.py` — new rendering content sourced from the view-model layer, which iterates `canonical_identities`/`canonical_relationships` directly (not `network_graph.all_devices()`) as its primary axis (corrected this pass — see Section 6). A canonical record whose subject matches a `Device` is rendered in that device's existing context (alongside the Identity/Evidence/Classification blocks); an unmatched record remains representable via its raw subject identifier through some device-independent treatment. Exact placement for both cases is a PLAN-025 layout decision, not fixed here.
- `networkmapper/exporters/csv_exporter.py` — additional identity-corroboration summary columns on the existing device row, for matched subjects only. This CSV remains structurally one row per `Device`; an unmatched canonical identity has no row to attach columns to, and a placeholder device row is rejected as a way to force one (Section 8) — a genuine format limitation, not a suppression, since Markdown remains representable for the unmatched case.
- `networkmapper/reporting/__init__.py` — export the new view-model type(s) alongside `ProjectSummary`.
- `docs/architecture/overview.md` — Exporters/Reporting Path sections updated to document the identity/relationship reporting path, at implementation time.

**Not modified:** `Project`, `Device`, `CanonicalIdentity`, `CanonicalRelationship`, `IdentityObservation`, `RelationshipObservation`, `IdentityResolver`, `RelationshipResolver`, `ProjectSerializer`, `ProjectComparator`. This design is additive and read-only throughout — every existing consumer of `Project` continues to function unchanged.

---

## 13. Testing Strategy

All of the following are achievable without discovery execution or network access, following the pattern already established in `test_identity_resolver.py` and `test_markdown_exporter.py`, since every type involved is a plain, directly-constructable frozen dataclass:

- **View-model derivation, unit-tested directly**: construct synthetic `CanonicalIdentity`/`CanonicalRelationship`/`Device` values covering `WEAK`/`PROBABLE`/`CONFIRMED`/`CONFLICTING` (identity) and `WEAK`/`CONFIRMED`/`CONFLICTING` (relationship) states, and assert the derived view records faithfully carry the resolver's own `state` and values — never a recomputed corroboration signal (Finding 3) — plus correct device enrichment when a match exists and a graceful raw-subject fallback when it doesn't (Finding 4).
- **Exporter rendering, unit-tested directly**: construct a synthetic `Project` (not via `Application.run()`) with populated `canonical_identities`/`canonical_relationships`, and assert expected Markdown section text / CSV row content, mirroring the existing exporter test files' structure.
- **Unknown-category fallback, unit-tested directly** (Finding 5): a `CanonicalRelationship` with a category absent from the friendly-label mapping renders using the deterministic generic fallback, without error and without requiring a presentation-layer code change.
- **Deterministic ordering, unit-tested directly** (Finding 9): assert that permuting the input `observations`/`identities` sequence before calling the resolvers does not change the view-model's or exporter's rendered output. The resolvers already guarantee this at their own level (`identity/resolver.py:71` sorts identities by subject, properties by name, observations by `(provider, method, value)`; `relationships/resolver.py:121-123` sorts relationships by `(subject, category)`, observations by `(provider, method, related_subject)`) — this test confirms the presentation layer preserves that guarantee rather than accidentally reordering it (e.g. via an incidental dict rebuild), not that presentation independently redefines ordering semantics. For the relationship-CSV expansion specifically (Section 8), separately assert the secondary per-`related_subject` row order is itself deterministic and independent of input order.
- **Empty-tuple handling (the reachable case, per Section 5)**: a `Project` with legitimately empty `canonical_relationships` (no relationship-evidence flags enabled) must render without error and without a misleading "confirmed no relationships exist" message — this is a first-class, currently-reachable test case, not a hypothetical.
- **Reload regression (documentation, not a live requirement)**: a test confirming a `Project` built via `ProjectSerializer.load()` continues to produce empty `observations`/`canonical_identities`/`canonical_relationships` tuples — useful to pin current, deliberate behavior explicitly, even though no exporter is invoked against a reloaded project today.
- **Symmetric-category double-`WEAK` case**: a targeted test asserting the exporter renders two independent single-source relationship records faithfully (Section 7), documenting the known resolver limitation is inherited into output on purpose, not accidentally.

No fresh-vs-reloaded exporter-level distinction needs testing beyond the above, since (Section 5) no reload-then-export code path exists to test today.

---

## 14. Scope Boundaries

All eight exclusions named at the outset were checked against the findings above; none proved load-bearing for the recommended architecture:

- **Topology visualization** — not touched; ARCH-014's precedent (presentation mirrors the existing exporter relationship to `Project`) is followed without needing to design for a topology renderer.
- **Web UI/API** — doesn't exist, not required by anything in this design.
- **New evidence providers** — this design renders whatever evidence already exists; it needs no new provider.
- **Q-BRIDGE-MIB/CDP** — irrelevant to how the existing `arp_neighbor`/`connected_to`/`bridge_fdb` categories render; category labels are already free-text (ADR-013 declines to freeze a taxonomy), and the deterministic generic fallback (Finding 5, Section 7) means a future category requires no presentation-layer *redesign* and remains renderable with zero code changes — an optional friendly-label mapping entry later is a wording improvement, not a prerequisite.
- **`ProjectComparator` wiring** — excluded because no CLI path invokes it today; its one anticipated use case, cross-session historical comparison, is specifically blocked by non-persistence (Section 11), though same-session comparison is not structurally impossible (Finding 2).
- **Run-to-run comparison** — same finding as above.
- **Persistence redesign** — confirmed not required (Section 5); explicitly not recommended as a side effect of this design.
- **`RelationshipResolver` redesign** — confirmed not required for correct presentation (Section 7); the known cardinality limitation is rendered faithfully, not fixed.

---

## 15. ADR-Trigger Check

Walking through every decision this report makes:

1. Introducing a new view-model layer in `reporting/` — an addition within an already-established pattern (`ProjectSummary`'s own role), not a new architectural category. No ADR trigger.
2. Extending `MarkdownExporter`/`CsvExporter` to read `canonical_identities`/`canonical_relationships` — explicitly anticipated and merely deferred by ARCH-019, not forbidden; ADR-012/013 name this exact presentation work as expected future work. No ADR trigger.
3. Choosing not to persist canonical data, and not adding a reload-then-export path — this preserves ADR-011/012's traceability requirement as-is. No ADR trigger; a trigger would arise only if this decision were later reversed.
4. Rendering the resolver's known cardinality limitation as-is rather than fixing `RelationshipResolver` — no behavioral change to the resolver, no ADR implication.
5. A separate CSV artifact emitting one row per distinct `(subject, category, related_subject)` claim — a new exporter output, not a new architectural boundary; consistent with `docs/architecture/overview.md`'s existing statement that the exporter subsystem "supports multiple output formats from the same source data."
6. Deriving presentation primarily from `canonical_identities`/`canonical_relationships`, with `Device` matching as optional enrichment rather than a prerequisite — this changes only presentation traversal semantics (which collection the view-model iterates, and how it handles an enrichment-lookup miss). It does not alter persistence, evidence collection, the canonical models (`CanonicalIdentity`/`CanonicalRelationship`), resolver behavior, or `Project` state. No ADR trigger.

**Conclusion: no ADR is required for the recommended architecture.** Two conditions would trigger one in the future, named explicitly per the instruction not to let them be silently absorbed: (a) if a reload-then-export CLI pathway is added, requiring a decision about whether/how to persist enough of `observations`/canonical data to keep presentation meaningful after reload; (b) if `ProjectComparator` is wired for identity/relationship-aware *cross-session historical* diffing (its one anticipated use case), which requires the same persistence decision — same-session comparison would not require it (Finding 2), but nothing wires that today either. Neither is proposed by this report.

---

## 16. Unresolved / Live Questions

- **Symmetric-relationship cardinality** (Section 7): whether `RelationshipResolver` should eventually recognize a bidirectionally-reported `connected_to` pair as one `CONFIRMED` relationship rather than two `WEAK` ones is a live question for a future resolver investigation — explicitly not solved here, and not required to be solved for presentation to be correct.
- **Unresolved relationship observations**: whether these ever deserve a technician-facing surface (vs. remaining diagnostics-only) is a scoping judgment (Section 7), not a technical constraint, and is revisable if user feedback on the shipped report indicates a need.
- **Fresh-vs-reloaded disambiguation**: if a reload-then-export pathway is ever added, an empty `canonical_relationships` tuple will become ambiguous between "no evidence collected," "evidence collected but nothing corroborated," and "reloaded, data not retained." This report deliberately does not design a disambiguation mechanism now (Section 5), since doing so today would mean adding metadata against a scenario that cannot currently occur.
- **`ProjectSummary.discovered_networks`**: observed to be an always-empty, unpopulated field, unrelated to this investigation's scope — noted for awareness, not addressed.
- **Independent-source-count exposure** (Finding 3): whether `PropertyCorroboration`/`CanonicalRelationship` should eventually expose the independent-source count the resolver already computes and discards internally (`identity/resolver.py:114`, `relationships/resolver.py:143`) as a stored field, so presentation could show a "confirmed by N sources" style label without recomputing it, is a live question for a future canonical-model change — not decided or built here. Until such a change exists, presentation shows the resolver's `state` alone, without a source count.
- **Exact view-model shape and naming**: deliberately left open for PLAN-025, per the instruction not to propose implementation here.
- **CSV representation of unmatched canonical identities**: the existing device-row CSV cannot carry a canonical identity with no matching `Device` without inventing a placeholder row that would misrepresent the file's device-counting semantics (Section 8). Markdown remains representable regardless. Whether unmatched identities warrant a CSV representation of their own — mirroring the relationship CSV's device-independent design — is a live question for PLAN-025, not resolved here.
- **Exact layout for matched-vs-unmatched canonical records**: whether a given renderer uses one unified rendering path (with device enrichment as an optional field) or two visibly distinct paths for matched and unmatched records is a PLAN-025 decision; this report establishes only that both must be representable (Section 6, Section 7).

---

## 17. Final Recommendation

Build a new, purpose-built presentation/view-model layer in `networkmapper/reporting/`, structurally a sibling to `ProjectSummary` rather than an extension of it, that projects — never recomputes — the resolvers' canonical output into technician-legible identity and relationship records, enriching subjects with `Device` references where a match exists and falling back to the raw subject otherwise. Extend `MarkdownExporter` to render every canonical identity and every canonical relationship — value, resolver-provided corroboration state, structured provenance, conflicts always shown and never collapsed; directional and category-labeled with a deterministic fallback for unmapped categories, corroboration-stated. A matching `Device` supplies optional enrichment context; an unmatched subject falls back to its raw subject identifier and remains fully representable either way. Exact renderer layout — for matched records, unmatched records, or both — is a PLAN-025 decision. Extend `CsvExporter` with identity-corroboration summary columns on the existing device row as a deliberately coarse projection, and add a separate, sequenced-later CSV artifact emitting one row per distinct `(subject, category, related_subject)` claim — not one row per `CanonicalRelationship` — rather than forcing graph-shaped data into the device-row format or collapsing conflicting related subjects into a delimited field. No changes to `Project`, the resolvers, `PropertyCorroboration`, `CanonicalRelationship`, `ProjectSerializer`, or `ProjectComparator` are required or recommended. No new ADR is triggered.

Recommended next sprint: **PLAN-025**, translating this architecture into a concrete file-level change inventory, sequenced as (1) the shared view-model layer, (2) `MarkdownExporter` identity and relationship rendering, (3) `CsvExporter` identity summary columns, with the separate relationship-CSV artifact as a distinct follow-on FEAT rather than bundled into the same PLAN.
