# VER-028 — Relationship Cardinality Resolver Support Verification

This report verifies FEAT-RELATIONSHIP-CARDINALITY, commit `7668763af5fb76857d6e43409c35414bd14a699d`, against ADR-013 Amendment 1 (`a8eab2c`) and PLAN-028 (`bc15552`). It is an independent verification sprint: no production code or test was modified.

---

## 1. Verification Summary

FEAT-RELATIONSHIP-CARDINALITY makes four changes:
- adds a resolver-owned category cardinality policy (`networkmapper/relationships/categories.py`);
- changes `RelationshipResolver` to emit one `CanonicalRelationship` per `(subject, category, related_subject)` edge while still evaluating by `(subject, category)`;
- restricts `CONFLICTING` to single-valued categories;
- updates the canonical presentation layer and both relationship renderers to carry per-edge state.

Nothing was relied on from the implementation session. Every check was re-run against the commit:

- **Scope.** The commit was inspected with `git show` and diffed against its parent `bc15552` to confirm exactly which files changed and that protected areas did not.
- **Source.** All 7 production files were re-read from the commit (`git show 7668763:<path>`), not from the working tree.
- **Independent battery.** A new 22-check script (`independent_battery.py`) was written for this verification. It ran against a clean `git archive` export of the commit. Its core check compares the resolver with a **reference model written from the ADR-013 Amendment 1 / PLAN-028 text**, not from the resolver source, over 3,000 random observation sets under two cardinality policies.
- **Mutation check.** 12 single-defect mutants of the commit were each run against the committed test suite, to show the tests detect the regressions PLAN-028 cares about.
- **Official gate.** `python -m pytest tests/ -q` and `python -m devtools validate --all` were run on the working tree. Its code is byte-identical to the commit: `git diff --quiet HEAD -- networkmapper tests devtools` succeeded, and `HEAD` is `7668763`.

No defects were found. Section 8 lists residual risks and follow-up items, all previously documented in ARCH-027 and PLAN-028; none is a defect in this commit.

---

## 2. PASS / FAIL Determination

**PASS**

---

## 3. Commit Verified

| Item | Value |
|---|---|
| Commit | `7668763af5fb76857d6e43409c35414bd14a699d` |
| Parent | `bc155525ccbf80e694c98b11a7e55ff635f5dfd5` (PLAN-028) |
| Subject | `Implement relationship cardinality resolver support` |
| Files | 15: 13 modified, 2 added |
| `review.diff`, `diff.md` | Not in the commit |

**Files in the commit** (`git show --name-status`). All match the approved PLAN-028 list:

```
M networkmapper/exporters/markdown_exporter.py
M networkmapper/exporters/relationship_csv_exporter.py
M networkmapper/relationships/__init__.py
A networkmapper/relationships/categories.py
M networkmapper/relationships/models.py
M networkmapper/relationships/resolver.py
M networkmapper/reporting/canonical_presentation.py
M tests/test_canonical_presentation.py
M tests/test_identity_pipeline.py
M tests/test_markdown_exporter.py
M tests/test_project.py
M tests/test_project_serializer.py
A tests/test_relationship_cardinality_pipeline.py
M tests/test_relationship_csv_exporter.py
M tests/test_relationship_resolver.py
```

**Protected areas.** `git diff --name-only 7668763~1 7668763` over each of the following returned no files: `networkmapper/discovery` (providers), `networkmapper/observations`, `networkmapper/identity`, `networkmapper/core`, `networkmapper/project`, `networkmapper/application.py`, `devtools/` and `docs/`.

---

## 4. Files Inspected

**Production, read from the commit:** `relationships/categories.py`, `relationships/models.py`, `relationships/resolver.py`, `relationships/__init__.py`, `reporting/canonical_presentation.py`, `exporters/markdown_exporter.py`, `exporters/relationship_csv_exporter.py`.

**Production, read from the parent for comparison:** `exporters/relationship_csv_exporter.py` (CSV header).

**Tests, read from the commit:** `test_relationship_resolver.py` (38 tests), `test_relationship_cardinality_pipeline.py` (6), `test_canonical_presentation.py` (16), `test_relationship_csv_exporter.py` (15), `test_markdown_exporter.py` (26), `test_project.py`, `test_project_serializer.py`, `test_identity_pipeline.py`.

**Authority:** `docs/ADR.md` (ADR-013 Amendment 1), `docs/plans/PLAN-028-Relationship-Cardinality-Resolver-Support.md`, `docs/reports/ARCH-026-Gateway-Relationship-Evidence-Readiness.md`, `docs/reports/ARCH-027-Relationship-Cardinality-and-Corroboration-Semantics.md`.

---

## 5. Requirement Checklist (ADR-013 Amendment 1 / PLAN-028)

| # | Requirement | Evidence | Result |
|---|---|---|---|
| 1 | Cardinality policy owned by the resolver layer, not providers or observations | `CATEGORY_CARDINALITY` lives in `relationships/categories.py`. There is no cardinality field on `RelationshipObservation`, and `observations/` and `discovery/` are unchanged in the commit. | ✅ |
| 2 | `arp_neighbor`, `bridge_fdb` and `connected_to` registered as MULTIPLE | `categories.py:40-42`. The independent battery confirms the policy has exactly these 3 entries, all MULTIPLE. | ✅ |
| 3 | `default_gateway` not registered | Absent from the policy (battery check). The only production occurrence is the docstring saying it is deliberately absent (`categories.py:14`). | ✅ |
| 4 | Unknown categories default to MULTIPLE | `DEFAULT_CARDINALITY = RelationshipCardinality.MULTIPLE`, and `cardinality_for` returns `policy.get(category, DEFAULT_CARDINALITY)` (`categories.py:48,57`). | ✅ |
| 5 | Policy is immutable; optional injected policy for tests (D1) | `MappingProxyType` (battery: assigning to it raises `TypeError`). `RelationshipResolver.__init__(cardinality_policy=None)` defaults to the module policy (`resolver.py:97-112`). `Application` is unchanged, so production never injects a policy. | ✅ |
| 6 | Evaluation key remains `(subject, category)` | `group_key = (observation.subject, observation.category)` (`resolver.py:148`). The endpoint gate and self-loop exclusion still run before grouping (`resolver.py:136-144`). | ✅ |
| 7 | Output identity is `(subject, category, related_subject)` | One record per distinct `related_subject` within a group (`resolver.py:181-213`). Output is sorted by the triple (`resolver.py:158-166`). The battery found no duplicate or out-of-order keys over 6,000 resolutions. | ✅ |
| 8 | CONFLICTING possible only for SINGLE | `group_conflicts = cardinality == SINGLE and len(observations_by_edge) > 1` (`resolver.py:185-187`). The model rejects MULTIPLE + CONFLICTING (`models.py:111-119`). The battery found 0 CONFLICTING non-SINGLE edges across 14,886 edges. | ✅ |
| 9 | SINGLE categories keep today's corroboration semantics, not today's output shape | When a SINGLE group conflicts, every edge is CONFLICTING, including an edge two sources support. Otherwise one source gives WEAK and two give CONFIRMED. The battery's reference model agreed with the resolver on all 6,000 resolutions. | ✅ |
| 10 | Independence counted per edge | Sources are distinct `(provider, collection_method)` pairs within one edge's own observations (`resolver.py:191-194`). Mutant M6 (group-wide counting) is caught by the tests. | ✅ |
| 11 | D3 invariants | `__post_init__` rejects MULTIPLE + CONFLICTING, empty observations, and any observation whose subject, category or related subject differs from the record's. The battery confirmed all 5 rejections and that SINGLE + CONFLICTING is accepted. | ✅ |
| 12 | D6 sort key `(provider, collection_method, related_subject, source_run, observed_at_sort_value)`, using a total timestamp form, documented in the resolver docstring | `_edge_observation_sort_key` uses `observed_at.isoformat()` (`resolver.py:217-231`), and the class docstring documents it. The battery confirmed the exact order on a 5-observation edge, and that results stay identical under shuffling with mixed naive and timezone-aware timestamps. | ✅ |
| 13 | No object-identity ordering (architect note 2) | The sort key uses values only; no `id()` or object-identity ordering appears. | ✅ |
| 14 | Providers remain observation-only | `networkmapper/discovery/` is unchanged in the commit. No `EnrichmentProvider` or `DiscoveryProvider` was added (scan of added lines). | ✅ |
| 15 | Presentation groups edges and keeps per-edge state (D4) | `RelationshipPresentation` has `cardinality` and no `state`. `RelatedSubjectPresentation.state` is copied from its edge. Edges sharing `(subject, category)` with different cardinalities raise `ValueError`. Confirmed by the battery. | ✅ |
| 16 | Relationship CSV schema unchanged; state written per edge (D5) | The header is identical at the parent and the commit. The state cell is `related.state.value` (`relationship_csv_exporter.py:47`). The battery confirmed one row per edge, each with that edge's state and that edge's full provenance. | ✅ |
| 17 | Markdown renders cardinality and per-edge state | A `- Cardinality: Multi-valued` line, plus a `- Corroboration State:` line under each related subject. No "Conflicting" appears for multi-valued fan-out (battery). | ✅ |
| 18 | No gateway inference, topology provider or rendering added | The only new production definitions are `RelationshipCardinality`, `cardinality_for`, `_edge_observation_sort_key`, `_present_relationships` and `_present_relationship_group`. A scan of added production lines for gateway, topology, provider or layout terms matched only the `default_gateway` docstring. | ✅ |
| 19 | Policy-completeness test checks only the three named provider constants (architect note 3) | `test_every_relationship_provider_category_is_registered` imports exactly `ARP_NEIGHBOR_CATEGORY`, `BRIDGE_FDB_CATEGORY` and `LLDP_NEIGHBOR_CATEGORY`. It does not walk `networkmapper.discovery` or match constants by naming convention. | ✅ |

---

## 6. Test Coverage Inspection

Each required coverage area maps to named tests in the commit:

| Coverage area | Committed tests |
|---|---|
| MULTIPLE fan-out without false conflict | `test_gateway_style_fan_out_produces_one_weak_edge_per_host`, `test_one_source_reporting_two_neighbors_is_not_a_conflict`, `test_two_sources_naming_different_neighbors_are_two_weak_edges` |
| SINGLE conflict, using an injected test policy | `RelationshipResolverSingleValuedConflictTest` (5 tests, using `_SINGLE_POLICY` on the test-only category `test_single_valued`) |
| Unknown category defaults to MULTIPLE | `test_unknown_category_defaults_to_multiple`, `test_unregistered_category_defaults_to_multiple_and_never_conflicts` |
| Per-edge observation retention | `test_each_edge_carries_only_its_own_observations`; SINGLE tests assert the union of retained observations equals the input |
| Deterministic sorting, including D6 timestamps | `test_output_is_sorted_by_subject_category_and_related_subject_regardless_of_input_order`, `test_edge_observations_are_sorted_deterministically_with_ties` (200 shuffles), `test_mixed_naive_and_aware_timestamps_sort_without_error`, `test_resolve_is_order_independent_across_many_random_permutations` |
| Policy completeness for the three provider constants | `test_every_relationship_provider_category_is_registered`, `test_existing_relationship_categories_are_registered_as_multiple`, `test_default_gateway_is_not_registered` |
| Policy immutability and injection | `test_module_policy_cannot_be_mutated`, `test_custom_policy_does_not_mutate_the_module_policy` |
| Model invariants | `CanonicalRelationshipInvariantTest` (4 tests, one with 3 subtests) |
| Presentation per-edge state and cardinality consistency | `test_multi_valued_edges_group_under_one_entry_with_their_own_states`, `test_single_valued_conflict_preserves_every_competing_related_subject`, `test_mixed_cardinality_for_one_subject_and_category_is_rejected`, `test_same_category_for_different_subjects_may_be_presented_independently` |
| CSV per-edge state | `test_multi_valued_fan_out_rows_carry_each_edge_state`, `test_single_valued_conflict_exports_one_conflicting_row_per_competing_edge`, `test_header_row` |
| Markdown per-edge state | `test_canonical_relationships_section_shows_multi_valued_fan_out_without_conflict`, `test_canonical_relationships_section_shows_all_conflicting_related_subjects`, `test_canonical_relationships_section_renders_direction_category_and_device_enrichment` |
| End-to-end: provider → resolver → exporters | `test_relationship_cardinality_pipeline.py`: ARP, bridge-FDB and LLDP fan-out (stub SNMP client → real provider → real `IdentityResolver` and `RelationshipResolver`); combined evidence through `RelationshipCsvExporter` and `MarkdownExporter`; 50-shuffle determinism |

### 6.1 Mutation check

Each mutant injects one defect into a fresh copy of a full `git archive 7668763` export, then runs the committed `tests/` suite against that copy. The unmutated export passed first: **784 passed, 36 subtests passed**.

| Mutant | Result | Failing tests (count; example) |
|---|---|---|
| M1 MULTIPLE can conflict (pre-amendment semantics) | Killed | 16; `test_gateway_arp_table_fan_out_produces_one_weak_edge_per_host` |
| M2 SINGLE never conflicts | Killed | 4; `test_a_second_source_agreeing_with_one_value_does_not_soften_the_conflict` |
| M3 Unknown category defaults to SINGLE | Killed | 2; `test_unregistered_category_defaults_to_multiple_and_never_conflicts` |
| M4 `default_gateway` registered | Killed | 1; `test_default_gateway_is_not_registered` |
| M5 D6 tie-breakers dropped | Killed | 1; `test_edge_observations_are_sorted_deterministically_with_ties` |
| M6 Independence counted group-wide | Killed | 2; `test_mixed_weak_and_confirmed_edges_within_one_subject_and_category` |
| M7 Self-loop exclusion removed | Killed | 2; `test_a_self_loop_observation_produces_no_relationship` |
| M8 MULTIPLE + CONFLICTING invariant removed | Killed | 1; `test_conflicting_is_rejected_for_a_multiple_category` |
| M9 Presentation skips the cardinality check | Killed | 1; `test_mixed_cardinality_for_one_subject_and_category_is_rejected` |
| M10 CSV writes the group's first edge state on every row | Killed | 1; `test_multi_valued_fan_out_rows_carry_each_edge_state` |
| M11 Output sorted by `(subject, category)` only | Killed | 3; `test_mixed_evidence_resolves_identically_across_shuffles` |
| M12 Injected policy ignored | Killed | 4; `test_a_second_source_agreeing_with_one_value_does_not_soften_the_conflict` |

**12 of 12 killed.**

**Method note.** The first mutation run used an export of only `networkmapper/` and `tests/`. Every mutant then "failed" on the same collection error, because `tests/test_devtools_validate.py` imports `devtools`. That run was discarded as invalid. The table above comes from a full-repository export, after first confirming its unmutated baseline passes.

---

## 7. Test Execution Summary

Run on the working tree, whose code is identical to `7668763`:

**`python -m pytest tests/ -q`** (exit 0):

```
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 27%]
........................................................................ [ 36%]
................................................................... [ 45%]
........................................................................ [ 54%]
........................................................................ [ 63%]
......................................................... [ 70%]
.................................................................. [ 79%]
........................................................................ [ 88%]
.............................................................. [ 96%]
............................                                             [100%]
784 passed, 36 subtests passed in 8.28s
```

**`python -m devtools validate --all`** (exit 0):

```
JSON report: C:\Users\mylesm\AppData\Local\Temp\tmpz4v4y5xg\nested\reports\benchmarks\dataset_output_dir.json
========================================
NetworkMapper Full Validation
========================================

Unit Tests

PASS

Tests Run: 784
Failures: 0
Errors: 0
Skipped: 0

Benchmarks

Dataset: enterprise
Devices: 9
Accuracy: 100.0%
PASS

Dataset: homelab
Devices: 5
Accuracy: 100.0%
PASS

Dataset: small_office
Devices: 5
Accuracy: 100.0%
PASS

----------------------------------------

Overall Status

PASS

========================================

=========================
FULL VALIDATION SUMMARY
=========================

Tests

- Total executed: 784
- Passed: 784
- Failed: 0
- Errors: 0
- Runtime: 7.52s

Benchmarks

- Enterprise: PASS
- Homelab: PASS
- Small Office: PASS

Overall Result

PASS
```

**Independent battery** (`git archive 7668763` export): **22/22 checks passed.** The reference model agreed on 3,000 random cases × 2 policies (14,886 edges, 0 mismatches), with 0 CONFLICTING non-SINGLE edges, 0 ordering violations and 0 differences under shuffling.

---

## 8. Residual Risks and Follow-Up Items

None of these is a defect in this commit, and none blocks it.

1. **OPS-001 is still pending, and no production relationship replay exists.** ARCH-026 found **zero relationship observations** in the current 244-device production dataset (`output/Test Network.nmproj`: no SNMP data, `nmap` as the only discovery source, and observations not persisted). This verification therefore proves the semantics on synthetic and stubbed-provider evidence only. Real fan-out sizes, SNMP reachability and output volume remain unmeasured until OPS-001 (an SNMP-enabled production capture) is run.
2. **One LLDP neighbor with several management addresses becomes several edges** (PLAN-028 R6; ARCH-027 Open Question 2). These may be one device under two subjects. They now show as WEAK edges rather than a false CONFLICTING, but they are not merged. `test_one_neighbor_with_two_management_addresses_produces_two_weak_edges` records this current behavior.
3. **Per-edge CONFIRMED can come from a single SNMP walk** (PLAN-028 R7; ARCH-027 Open Question 6). LLDP rows resolved through different `collection_method` labels count as independent sources. This belongs to ADR-013's deferred independence taxonomy, and no test asserts it as correct.
4. **The injected policy is not validated** (D1 is a test seam). `RelationshipResolver(cardinality_policy=...)` accepts any mapping, so non-enum values are not rejected. `Application` never injects a policy, so production is unaffected. Consider type validation only if the seam is ever used outside tests.
5. **Output values change for multi-valued categories.** Rows that would have read `conflicting` now read `weak` or `confirmed` per edge. No production run has emitted relationships yet (item 1), so nobody has seen the old values.
6. **The policy-completeness list must be maintained.** Any future relationship-provider sprint must add its category constant to the explicit list in `test_every_relationship_provider_category_is_registered` (PLAN-028 §2.2, note 3).
7. **Still deferred:** symmetric-category canonicalization (a bidirectional LLDP link is two WEAK edges), a per-port or interface model, cross-category corroboration, negative evidence, cross-run corroboration and persistence.

---

## 9. Required Fixes

None.

---

## 10. Recommendation

**Accept FEAT-RELATIONSHIP-CARDINALITY (`7668763`) as verified.** It implements ADR-013 Amendment 1 and PLAN-028 as specified, including decisions D1–D6 and the architect notes. It introduces no gateway inference, topology or provider changes, and leaves the relationship CSV schema unchanged.

The resolver's semantic blocker for topology, identified in ARCH-026 §8.4, is now closed. The **evidence** blocker is not: OPS-001 remains the next prerequisite before any relationship provider or topology consumer can be evaluated against real data.
