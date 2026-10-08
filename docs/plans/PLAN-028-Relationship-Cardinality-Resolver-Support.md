# Status

Approved — Architect-Reviewed

Approval: Approved for implementation as FEAT-RELATIONSHIP-CARDINALITY, including decisions D1–D6 (Section 2), the corrected SINGLE-category wording (Section 2.1), and the architect notes on D6 sorting and the policy-completeness test (Section 2.2).

Authority: [ADR-013 Amendment 1 — Relationship Cardinality](../ADR.md) (committed `a8eab2c`), which authorizes exactly one resolver-cardinality implementation sprint. Design source: [ARCH-027](../reports/ARCH-027-Relationship-Cardinality-and-Corroboration-Semantics.md) Section 11 (Recommended Architecture). Evidence context: [ARCH-026](../reports/ARCH-026-Gateway-Relationship-Evidence-Readiness.md).

Baseline: `HEAD` `a8eab2c`. All file and line references below are as of that commit.

Implements: The "resolver cardinality support" sprint authorized by ADR-013 Amendment 1, §Authorization.

Production Code Modified: No. This is a planning document only.

New ADR Required: No. ADR-013 Amendment 1 is the governing decision. This plan implements it and introduces no new policy.

---

## 1. Sprint Name and Scope

**FEAT-RELATIONSHIP-CARDINALITY — Resolver Relationship Cardinality Support.**

The sprint makes four changes:
- `RelationshipResolver` applies resolver-owned category cardinality (`SINGLE` or `MULTIPLE`).
- It emits one canonical relationship per `(subject, category, related_subject)` edge.
- It produces `CONFLICTING` only for single-valued categories.
- The presentation layer and the Markdown and relationship CSV renderers are updated to match, and still never recompute state.

**Scope exclusions:** no new providers, no gateway inference, no topology rendering, no persistence, no speculative heuristics.

---

## 2. Decisions (D1–D6)

| # | Decision | Rationale |
|---|---|---|
| **D1** | `RelationshipResolver.__init__` accepts an optional `cardinality_policy: Mapping[str, RelationshipCardinality] \| None = None`, defaulting to the module policy. The `resolve(observations, identities)` signature is unchanged. | No production category is single-valued yet, and Amendment 1 forbids registering `default_gateway` before its provider exists. Tests need a way to exercise `SINGLE` semantics. `Application` keeps calling `RelationshipResolver()` with no arguments, so production semantics come only from the module policy. |
| **D2** | The policy is keyed by **string literals** inside `networkmapper/relationships/`. Provider category constants are **not** relocated. A policy-completeness test cross-checks the two (Section 7.2). | Importing provider constants into `relationships/` would make the interpretation layer depend on the discovery layer. Leaving the constants in place also means zero provider diff. |
| **D3** | `CanonicalRelationship.__post_init__` validates three invariants: it rejects `CONFLICTING` with `MULTIPLE`; it rejects empty `observations`; and it rejects any observation whose `subject`, `category` or `related_subject` differs from the record's. | Makes Amendment 1's "CONFLICTING only for single-valued" a property of the type rather than a convention. Every construction must be a valid state. |
| **D4** | The presentation **keeps the grouped layout**. `RelationshipPresentation` stays one per `(subject, category)`, loses its group-level `state` and gains `cardinality`. Each `RelatedSubjectPresentation` gains `state`. | Smallest change to the report layout. Both exporters already loop per related subject. |
| **D5** | The relationship CSV **keeps its columns unchanged**. Only the values change: the `Corroboration State` column becomes per edge. No `Cardinality` column is added. | Schema stability. ARCH-027 Open Question 5 (a cardinality column) stays open. |
| **D6** | Within each edge, observations are sorted by a key equivalent to `(provider, collection_method, related_subject, source_run, observed_at_sort_value)`, where `observed_at_sort_value` is a total, deterministic timestamp representation (for example `observed_at.isoformat()`). The ordering is documented in the resolver docstring (Section 2.2, note 1). | Closes a latent determinism gap (Risk R3). Today's key ends at `related_subject`, which is constant within an edge, so ties would otherwise fall back to input order. |

### 2.1 Corrected wording: SINGLE categories

**SINGLE categories preserve today's corroboration semantics, but not today's output shape.**

- **Semantics preserved.** A subject whose observations name more than one distinct related subject is `CONFLICTING`. A single source naming two values is enough. A second, agreeing source does not soften the conflict. Repeated observations from the same `(provider, collection_method)` count once. Two independent sources agreeing give `CONFIRMED`; otherwise the state is `WEAK`.
- **Shape changed.** Today one `CanonicalRelationship` per `(subject, category)` holds every competing related subject. After this sprint, each competing related subject is its own edge record, and every such sibling carries `CONFLICTING`. The conflict is explained by the set of records sharing `(subject, category)`, which output ordering keeps adjacent.

### 2.2 Architect notes on D6 sorting and on the policy-completeness test

**1. D6 sorting.**
- **Deterministic and documented.** Observations within each edge are sorted deterministically, and the ordering is documented in the `RelationshipResolver` docstring.
- **Key.** The sort key is equivalent to `(provider, collection_method, related_subject, source_run, observed_at_sort_value)`.
- **Why `related_subject` stays in the key.** It is constant within an edge that has already been partitioned. Keeping it makes the sort self-documenting, and keeps it safe if the sort helper is reused elsewhere.
- **Timestamp form.** `observed_at` holds naive datetimes today. Providers stamp it with `datetime.now()` (`arp_neighbor_provider.py:99`, `bridge_fdb_provider.py:126`), and the relationship tests use naive datetimes too. Comparing naive and aware datetimes directly raises `TypeError`. The implementation therefore sorts on a total, deterministic representation rather than comparing `datetime` objects; a string form such as `observed_at.isoformat()` is acceptable.
- **Not in scope.** This sprint is not required to normalize timestamp semantics across the project.

**2. Fully identical observations.** Two observations identical in every sorted field cannot be told apart by value equality, so their relative order does not matter. No object-id or other identity-based ordering is added. The resolver's output is deterministic **by value**; it does not promise to preserve the identity order of equal observations. `test_original_observation_objects_are_preserved_unmodified` keeps its single-observation `is` check, which this contract does not affect.

**3. Policy-completeness test.**
- **What it checks.** Only the actual relationship category constants from the known relationship provider modules:
  - `networkmapper.discovery.arp_neighbor_provider.ARP_NEIGHBOR_CATEGORY`
  - `networkmapper.discovery.bridge_fdb_provider.BRIDGE_FDB_CATEGORY`
  - `networkmapper.discovery.lldp_neighbor_provider.LLDP_NEIGHBOR_CATEGORY`
- **What it does not do.** It does not walk every module in `networkmapper.discovery`, and it does not collect every constant whose name ends in `_CATEGORY`.
- **Future providers.** A sprint that adds a relationship provider must add that provider's category constant to this explicit list.

---

## 3. Files to Change

**Production (7 files: 6 modified, 1 new):**

| # | File | Change |
|---|---|---|
| 1 | `networkmapper/relationships/categories.py` | **New.** Cardinality enum, policy table, default, lookup helper. |
| 2 | `networkmapper/relationships/models.py` | `CanonicalRelationship` edge shape plus D3 invariants; docstrings. |
| 3 | `networkmapper/relationships/resolver.py` | Cardinality-aware evaluation, per-edge output, D1 policy injection, D6 sort. |
| 4 | `networkmapper/relationships/__init__.py` | Export the new names; remove the stale "Inert and unwired" docstring line (the resolver is runtime-wired since FEAT-009B). |
| 5 | `networkmapper/reporting/canonical_presentation.py` | D4 presentation shape. |
| 6 | `networkmapper/exporters/markdown_exporter.py` | Per-related-subject state; group-level cardinality line. |
| 7 | `networkmapper/exporters/relationship_csv_exporter.py` | Per-row state from the edge; docstring. |

**Tests (8 files: 7 modified, 1 new):** `tests/test_relationship_resolver.py`, `tests/test_canonical_presentation.py`, `tests/test_markdown_exporter.py`, `tests/test_relationship_csv_exporter.py`, `tests/test_project.py`, `tests/test_project_serializer.py`, `tests/test_identity_pipeline.py`, and the new `tests/test_relationship_cardinality_pipeline.py`.

**Explicitly unchanged:**
- **Providers:** all three (`arp_neighbor_provider.py`, `bridge_fdb_provider.py`, `lldp_neighbor_provider.py`), including their category constants (D2).
- **Other packages and modules:** `networkmapper/observations/`; `networkmapper/identity/` (including `mac_index.py`); `project/models.py`; `project/serializer.py` (canonical records are not persisted); `application.py`; `comparison/`; `reporting/__init__.py` (it exports the same names); `devtools/validate.py`.
- **Docs:** `docs/ADR.md` (Amendment 1 is already committed).

---

## 4. Model and API Changes

### 4.1 `networkmapper/relationships/categories.py` (new)

```python
class RelationshipCardinality(StrEnum):
    SINGLE = "single"      # at most one related subject per (subject, category)
    MULTIPLE = "multiple"  # any number of related subjects per (subject, category)

CATEGORY_CARDINALITY: Mapping[str, RelationshipCardinality] = MappingProxyType({
    "arp_neighbor": RelationshipCardinality.MULTIPLE,
    "bridge_fdb": RelationshipCardinality.MULTIPLE,
    "connected_to": RelationshipCardinality.MULTIPLE,
})
DEFAULT_CARDINALITY = RelationshipCardinality.MULTIPLE

def cardinality_for(
    category: str,
    policy: Mapping[str, RelationshipCardinality] = CATEGORY_CARDINALITY,
) -> RelationshipCardinality: ...
```

- `MappingProxyType` prevents runtime mutation of the module policy.
- `default_gateway` is **not** registered (Amendment 1 §Explicit Limits).
- An unregistered category resolves to `DEFAULT_CARDINALITY` (`MULTIPLE`), so it can never manufacture a conflict.

### 4.2 `networkmapper/relationships/models.py`

- `CanonicalRelationship` becomes `(subject, category, related_subject, cardinality, state, observations)`. `related_subject` and `cardinality` are required and have no defaults, so every construction site must be explicit.
- `__post_init__` enforces the D3 invariants.
- `RelationshipCorroborationState` keeps its three members (`WEAK`, `CONFIRMED`, `CONFLICTING`). Its docstring narrows `CONFLICTING` to single-valued categories.
- The class docstring reverses the previous "no separate field holding the resolved `related_subject`" rationale and cites ADR-013 Amendment 1 §Decision 3.

### 4.3 `networkmapper/relationships/__init__.py`

Additionally exports `RelationshipCardinality`, `CATEGORY_CARDINALITY`, `DEFAULT_CARDINALITY` and `cardinality_for`.

---

## 5. Resolver Algorithm (`networkmapper/relationships/resolver.py`)

```
1. Filter RelationshipObservations                          (unchanged)
2. Endpoint gate + self-loop exclusion, before grouping     (unchanged; still required,
                                                             because SINGLE groups still
                                                             detect conflict)
3. Group by evaluation key (subject, category)              (unchanged key)
4. cardinality = cardinality_for(category, self._policy)    (new; D1)
5. Within the group, partition by related_subject → edges   (new)
6. Per edge: independent sources = distinct (provider, collection_method)
   among THAT EDGE's observations only                      (was: across the whole group)
7. State:
     SINGLE and the group has >1 distinct related_subject → every edge CONFLICTING
     otherwise, sources ≥ 2 → CONFIRMED
     otherwise             → WEAK
   (MULTIPLE can never reach CONFLICTING)
8. Emit one CanonicalRelationship per edge, carrying only that edge's
   observations, sorted per D6
9. Sort output by (subject, category, related_subject)      (was: (subject, category))
```

**Docstring rewrite.** The class docstring's paragraph justifying `(subject, category)` grouping becomes an explanation of the **evaluation key versus the output identity** (ADR-013 Amendment 1 §Decision 3). The symmetric-category limitation paragraph stays: each direction is still a separate edge, so a bidirectional link is still two independent WEAK records.

---

## 6. Presentation and Exporter Changes

### 6.1 `networkmapper/reporting/canonical_presentation.py` (D4)

- `RelatedSubjectPresentation` gains `state: RelationshipCorroborationState`, copied from the edge and never recomputed.
- `RelationshipPresentation` loses `state` and gains `cardinality: RelationshipCardinality`.
- `RelationshipPresentation` records are built by grouping consecutive edges with the same `(subject, category)`. The resolver's sort order makes this grouping deterministic and keeps the module's existing "preserve resolver order" contract.
- `_group_related_subjects` is replaced by a per-edge mapping: one `RelatedSubjectPresentation` per edge, with observations in the order the resolver gave them.

### 6.2 `networkmapper/exporters/markdown_exporter.py` (`_render_canonical_relationships`)

- The group-level `- Corroboration State:` line becomes `- Cardinality: Single-valued` or `- Cardinality: Multi-valued`.
- Each `  - A → B` line is followed by `    - Corroboration State: <state>`, then the provenance lines as today.
- The empty-section text and the `## <subject> — <Category Label>` heading format are unchanged.

### 6.3 `networkmapper/exporters/relationship_csv_exporter.py` (D5)

- The `Corroboration State` cell is taken from `related.state` instead of `relationship.state`.
- Header row is unchanged. There is still one row per related subject, which is now exactly one row per canonical record.
- The `_provenance_cell` docstring is updated: a row's provenance is the complete evidence for that edge, and the competitors in a SINGLE conflict appear as sibling rows.

---

## 7. Test Plan

### 7.1 Updates to existing tests

| File | Required change |
|---|---|
| `tests/test_relationship_resolver.py` (18 tests) | **Rewrite** the three conflict tests (`test_two_independent_sources_disagreeing_conflict`, `test_a_single_source_reporting_two_values_conflicts_on_its_own`, `test_a_second_source_agreeing_with_one_value_does_not_soften_the_conflict`), which currently assert `CONFLICTING` for `connected_to`, so they run against an injected `SINGLE` test category (D1). **Add inverted twins**: the same inputs under `connected_to` give per-edge `WEAK` or `CONFIRMED` records, never `CONFLICTING`. **Update** edge-shape assertions (`related_subject`, `cardinality`) in the single-observation, confirmation, duplicate-source, endpoint-gate, self-loop, contamination and identity-observation tests. **Update** `test_output_is_sorted_by_subject_then_category_regardless_of_input_order` to the `(subject, category, related_subject)` key. **Keep**, with updated assertions only: `test_a_symmetric_category_reported_from_both_endpoints_does_not_corroborate_in_stage_1` (two WEAK records) and `test_observations_are_grouped_by_subject_and_category_into_separate_relationships` (`hosts_service` is unregistered, so MULTIPLE, still two records). **Keep and extend** `test_resolve_is_order_independent_across_many_random_permutations` (Section 7.2). |
| `tests/test_canonical_presentation.py` (6 constructions) | Update all constructions. Change `test_conflicting_relationship_preserves_every_distinct_related_subject` (which builds `CONFLICTING` on `arp_neighbor`, now invalid under D3) to **two `SINGLE` edges, both `CONFLICTING`**. Assert per-related `state` and group `cardinality`. `test_presentation_is_independent_of_input_observation_order` is unchanged. |
| `tests/test_markdown_exporter.py` (3 constructions) | `test_canonical_relationships_section_renders_direction_category_and_device_enrichment`: `- Corroboration State: Weak` moves under the related-subject line, and `- Cardinality: Multi-valued` is asserted. `test_canonical_relationships_section_shows_all_conflicting_related_subjects`: change to `SINGLE` edges, with both related subjects shown as Conflicting. `test_unknown_relationship_category_falls_back_to_generic_label`: construction only. |
| `tests/test_relationship_csv_exporter.py` (11 constructions) | Update all constructions to edge form. `test_conflicting_relationship_expands_to_one_row_per_distinct_related_subject` becomes two `SINGLE` edge records, with every row reading `conflicting`. All other tests: construction change only; expected rows unchanged. |
| `tests/test_project.py`, `tests/test_project_serializer.py` | One construction each. |
| `tests/test_identity_pipeline.py` | Add assertions `related_subject == "172.16.100.11"` and `cardinality == MULTIPLE` next to the existing `WEAK` assertion. Runtime wiring is unchanged. |

### 7.2 New tests

**Resolver unit tests (in `tests/test_relationship_resolver.py`):**
1. The policy registers `arp_neighbor`, `bridge_fdb` and `connected_to` as `MULTIPLE`, and `default_gateway` is **not** registered.
2. An unknown category defaults to `MULTIPLE`: two related subjects give two `WEAK` records.
3. Fan-out in a `MULTIPLE` category (one source, three related subjects) gives three `WEAK` records and no `CONFLICTING`.
4. Mixed states within one subject and category: edge A is `CONFIRMED` (two independent sources) while edge B is `WEAK`.
5. `SINGLE`, two sources disagreeing: **every** edge is `CONFLICTING`, including an edge confirmed by two sources.
6. `SINGLE`, the same source repeated across runs: `WEAK`.
7. Each edge's observations contain only observations for that edge.
8. **Determinism with ties (D6):** within one edge, observations from the same provider and method but different `source_run` and `observed_at` values keep the same order across 200 random shuffles. The expected order follows the Section 2.2 note 1 key, with `observed_at` compared through its total string form.
9. Supplying a custom policy (D1) does not mutate `CATEGORY_CARDINALITY`.
10. **Invariants (D3):** `MULTIPLE` with `CONFLICTING`, a mismatched `related_subject`, and empty `observations` each raise an error.

**Policy-completeness test.** The test imports the three known relationship category constants explicitly and asserts that each one is registered in `CATEGORY_CARDINALITY` (Section 2.2, note 3):
- `ARP_NEIGHBOR_CATEGORY` from `networkmapper.discovery.arp_neighbor_provider`
- `BRIDGE_FDB_CATEGORY` from `networkmapper.discovery.bridge_fdb_provider`
- `LLDP_NEIGHBOR_CATEGORY` from `networkmapper.discovery.lldp_neighbor_provider`

It does not walk `networkmapper.discovery` or collect constants by naming convention. The test's docstring states that any future relationship-provider sprint must add its category constant to this explicit list, so a new category cannot quietly fall back to the default cardinality.

**New end-to-end module: `tests/test_relationship_cardinality_pipeline.py`.** Each test runs: stub SNMP client → real provider → `collect_observations()` (plus identity observations for the endpoints) → `IdentityResolver` → `RelationshipResolver`. The stub clients follow the pattern the provider test modules already use.

1. **ARP fan-out:** one L3 device's table lists 3 discovered hosts, giving 3 `WEAK` `arp_neighbor` records and no `CONFLICTING`.
2. **Bridge FDB fan-out:** the switch's forwarding table has 2 learned MACs, resolved through `receive_observations` and the MAC index, giving 2 `WEAK` `bridge_fdb` records.
3. **LLDP:** a switch with 2 neighbors gives 2 `WEAK` `connected_to` records. One neighbor advertising 2 management addresses gives 2 `WEAK` edges. That locks in today's documented behavior (ARCH-027 Open Question 2) without fixing it.
4. **Exporters:** combined ARP + FDB + LLDP evidence passed through `CanonicalPresentation`, `RelationshipCsvExporter` and `MarkdownExporter`. No CSV row reads `conflicting`, and the Markdown contains no "Conflicting".
5. **Mixed run:** ARP, FDB and LLDP observations in one input, shuffled 50 ways, give identical output.

**`STANDARD_REGRESSION_TESTS`:** not changed. No relationship test module is in it today, so the hardcoded count in `tests/test_devtools_validate.py` does not move.

---

## 8. Validation Gate

1. `python -m pytest tests/ -q`: about 753 existing plus about 20 new tests, all passing.
2. `python -m devtools validate --all`: PASS, all three benchmarks at 100%. Benchmarks don't exercise relationships (ARCH-017); this confirms classification is unaffected.
3. **Before/after comparison** on fixed synthetic observation sets:
   - `SINGLE` categories: today's corroboration outcomes are preserved; only the output shape differs (Section 2.1).
   - `MULTIPLE` categories: no `CONFLICTING` anywhere.
4. **No production replay is possible.** ARCH-026 found 0 relationship observations in the 244-device dataset.

---

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Visible output change: CSV and Markdown values for multi-valued categories go from `conflicting` to `weak` or `confirmed`. | No production run has emitted relationships (ARCH-026), so no one has seen these values. State the change in the commit message. |
| R2 | The presentation API change (`RelationshipPresentation.state` removed) breaks consumers. | The only consumers are the two exporters (verified with `git grep` at `a8eab2c`). `reporting/__init__.py` export names are unchanged. |
| R3 | **Latent determinism gap.** Today observations within a record are sorted by `(provider, collection_method, related_subject)`. With one record per edge, `related_subject` is constant, so ties (same source, different runs) fall back to input order, which breaks ADR-013 order-independence. | D6 key extended with `source_run` and a total timestamp form (Section 2.2, note 1), plus new test 8. Equal-by-value observations need no further ordering (note 2). |
| R4 | The `MULTIPLE` default hides a forgotten `SINGLE` registration. | The policy-completeness test checks the three known provider category constants explicitly (Section 2.2, note 3). Each future relationship-provider sprint must extend that list. A category no provider emits has no evidence to mishandle. |
| R5 | D3 invariants break ad-hoc `CanonicalRelationship` construction. | All 22 construction sites are tests rewritten in this sprint. Production constructs records only in the resolver. |
| R6 | An LLDP neighbor with several management addresses appears as several edges, possibly to the same device. | Not fixed here (ARCH-027 Open Question 2). End-to-end test 3 records the current behavior. |
| R7 | Per-edge `CONFIRMED` from a single SNMP walk: two LLDP rows resolved by different methods count as two independent sources. | Out of scope; it belongs to ADR-013's deferred independence taxonomy (ARCH-027 Open Question 6). Flagged, not asserted as correct by any test. |
| R8 | D1 policy injection is used to alter production semantics. | `Application` never passes a policy; only tests do. |

---

## 10. Non-Goals

- **No new providers or categories.** `default_gateway` is not registered.
- **No gateway inference** of any kind: `arp_neighbor` edges are not inverted, ranked or filtered.
- **No topology** rendering, layout or graph consumer.
- **No persistence:** canonical records remain run-scoped.
- **No changes to provider emission or provider constants** (D2).
- **No speculative heuristics**, including inferring cardinality from the evidence.
- **Deferred:** symmetric-category canonicalization, any per-port or interface model, cross-category corroboration, negative evidence, cross-run corroboration, and independence-taxonomy refinements.
- **No CSV schema change** (D5).
- **No `STANDARD_REGRESSION_TESTS` change.**

---

## 11. Suggested Execution Order

The sprint lands as a **single commit**. Within it:

1. `categories.py` and the `models.py` changes, with the invariant tests.
2. Resolver changes, with the updated and new resolver tests. Steps 1 and 2 go together, because the new required fields break all 22 construction sites until the resolver and tests are updated.
3. Presentation and both exporters, with their test updates.
4. The new end-to-end module, `tests/test_relationship_cardinality_pipeline.py`.
5. The full validation gate (Section 8).
