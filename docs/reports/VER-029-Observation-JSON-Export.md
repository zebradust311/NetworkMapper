# VER-029 — Observation JSON Export Verification

This report verifies FEAT-OBSERVATION-JSON-EXPORT against ADR-011 Amendment 1 (`84153e0`) and PLAN-029 (`7184256`).

It has two layers, kept separate throughout:
- **Verification of the committed baseline, `97b22e7`.** No production code or test was modified to produce it. Sections 3–6.1, 7.1 and 8 are this layer.
- **Validation of one pending, test-only addition.** It was made after that verification, at the architect's direction, to close the coverage gap found in Section 6.2. It adds two tests to `tests/test_observation_replay_format.py`, is not part of `97b22e7`, and changes no production code. Sections 6.3 and 7.2 are this layer.

**On the word "pending".** Throughout this report, "pending" describes the state at the time of verification: the two tests were in the working tree on top of `97b22e7` and had not been committed. They were committed afterwards, in the same commit as this report. All results for the pending tests were obtained in that pre-commit state.

---

## 1. Verdict

**PASS** for the committed baseline `97b22e7`. Verification found one test-coverage gap (Section 6.2). The pending test-only addition closes it (Section 6.3).

- **Scope.** Both commits contain exactly their approved files. No artifact was committed, and no excluded area changed.
- **Checklist.** Every ADR-011 Amendment 1 decision and every PLAN-029 implementation requirement is met (Section 4).
- **Independent battery.** 87 of 87 checks pass against a clean export of `97b22e7`. Against the feature commit alone (`e12b81a`), 9 checks fail, all of them identity-replay checks. This confirms that `97b22e7` is a necessary prerequisite for exact identity replay, and that it is sufficient.
- **Mutation check.** 29 of 30 deliberate defects are caught by the tests committed at `97b22e7`. The one survivor (M3, `source_run` removed from the artifact's sort key) is caught by the independent battery. It is a gap in the tests, not a defect in the implementation.
- **Gap closed, pending commit.** Two new tests fail under M3 and pass against the committed implementation. With them, 30 of 30 mutants are caught.
- **Gate at `97b22e7`.** `python -m pytest tests/ -q` gives 880 passed. `python -m devtools validate --all` gives PASS, with all three benchmarks at 100.0%.
- **Gate with the pending tests.** 882 passed, and `validate --all` gives PASS with all benchmarks at 100.0%.
- **Smoke test.** A synthetic run directory replays to MATCH with exit 0, and every file is byte-identical afterwards. A missing directory gives exit 2; no argument gives usage and exit 1.

---

## 2. Scope and Authority

**Baseline.** Verification baseline is HEAD at 97b22e7. The feature under verification is FEAT-OBSERVATION-JSON-EXPORT from e12b81a, plus the prerequisite identity resolver determinism fix in 97b22e7 required for ADR-011 Amendment 1 Decision 6. The fix corrects pre-existing identity observation ordering and does not change provider, classification, relationship, observation-format, exporter, serializer, or replay-command semantics.

| Item | Value |
|---|---|
| Feature commit | `e12b81a2895aae84577362854f09bc81fbbc966c`, *Implement observation JSON replay export* |
| Prerequisite fix | `97b22e7762012a84eac4e270e0251ed2ca956665`, *Make identity observation tie ordering deterministic* |
| Parent of the feature | `7184256` (PLAN-029 approved) |
| Authorization | ADR-011 Amendment 1, Replay Observation Export (`docs/ADR.md`) |
| Plan | `docs/plans/PLAN-029-Observation-JSON-Export.md` (architect rulings 1–4) |
| Design source | `docs/reports/ARCH-028-Observation-JSON-Export-Authorization.md` |
| Consumer | `docs/plans/OPS-001-SNMP-Enabled-Production-Evidence-Collection.md`, blocked on this report |

**Why the fix is in scope.** The first verification pass, run against `e12b81a` alone, found that replay did not reproduce canonical identities exactly. This happened in 12 of 400 randomized replays.

- **Cause.** `IdentityResolver._resolve_property` sorted a property's observations by `(provider, collection_method, value)` only. Observations that tied on those three fields but differed in `source_run` or `observed_at` kept their input order.
- **Effect.** The run resolves observations in collection order, but the replay resolves them in the artifact's sorted order. The two outputs therefore differed in the order of those tied observations, although they matched in state, values and membership.
- **Rules affected.** The resolver's dependence on input order contradicts ADR-012 ("identity must never depend on provider ordering"). The replay mismatch breaks Amendment 1 Decision 6.
- **Resolution.** The architect ruled that the fix land first, without qualifying the verdict. `97b22e7` extends the sort key to `(provider, collection_method, value, source_run, observed_at.isoformat())`, mirroring PLAN-028 D6 for relationships.

**Method.** Nothing was taken on trust from the implementation sessions.

- **Commit contents.** Inspected with `git show` and diffed against `7184256`.
- **Independent battery.** `independent_battery.py`, written for this report, ran against a clean `git archive 97b22e7` export. Its reference models were written from the text of ADR-011 Amendment 1, PLAN-029 Sections 4–7 and ADR-012/ADR-013. They do not import or copy the implementation's serializer, sort key, comparison or resolvers.
- **Mutation check.** Each mutant ran against its own throwaway copy of that export. The repository working tree was never mutated.
- **Official gate at `97b22e7`.** Run on the working tree before the pending test was added. Its code was identical to `97b22e7`: `git diff --quiet HEAD -- networkmapper tests devtools` succeeded, and `HEAD` was `97b22e7`.
- **Validation of the pending test.** Run on the working tree after the addition. Production and devtools code was still identical to `97b22e7` (`git diff --quiet HEAD -- networkmapper devtools` succeeded); the only code difference was `tests/test_observation_replay_format.py`.

**Disclosure.** The same agent session implemented the feature (`e12b81a`), implemented the fix (`97b22e7`), wrote the pending tests, and performed this verification.

The reference models, the battery, the mutants and the smoke fixtures are *independent methods*. They were written from the governing documents rather than from the implementation, and they check the implementation against those documents. They are not a second-party review: the same session wrote both sides. The architect should weigh this report as a self-verification backed by reproducible evidence.

---

## 3. Commit Scope Check

**`e12b81a`**: 13 files (7 modified, 6 added), 2,376 insertions and 8 deletions. Exactly the approved list:

```
M  ENGINEERING.md
M  devtools/__main__.py
A  devtools/replay_observations.py
M  networkmapper/application.py
A  networkmapper/exporters/observation_json_exporter.py
A  networkmapper/observations/replay_format.py
M  networkmapper/reporting/report_run.py
M  tests/test_application_cli.py
A  tests/test_devtools_replay_observations.py
M  tests/test_identity_pipeline.py
A  tests/test_observation_json_exporter.py
A  tests/test_observation_replay_format.py
M  tests/test_report_run.py
```

**`97b22e7`**: 4 files, 188 insertions and 14 deletions. Exactly the approved list:

```
M  networkmapper/identity/models.py
M  networkmapper/identity/resolver.py
M  tests/test_devtools_replay_observations.py
M  tests/test_identity_resolver.py
```

The `models.py` change is a docstring only: the documented observation order now lists the two added tie-breakers. In `resolver.py`, the only code change replaces the sort lambda with `_property_observation_sort_key` (`resolver.py:131`, `resolver.py:166-184`). Grouping, independence counting, property states and the identity roll-up are unchanged.

**Nothing extra was committed.** Neither commit contains `review.diff`, `diff.md`, a review bundle, a smoke artifact, an `observations.json`, a `.nmproj` file, any `output/` path, or any `docs/` path, including `docs/reports`. A name filter over both commits returned 0 matches. `git ls-tree -r 97b22e7` contains no `observations.json`, `.nmproj` or `output/` path.

**Excluded areas.** `git diff --name-only 7184256 97b22e7` over each of the following returned no files:

- `networkmapper/project` (`ProjectSerializer`, `.nmproj`)
- `networkmapper/discovery` (providers)
- `networkmapper/relationships`
- `networkmapper/classification`, `networkmapper/comparison`, `networkmapper/developer` (workbench), `networkmapper/knowledge`, `networkmapper/core`, `networkmapper/runtime`, `networkmapper/ui`, `networkmapper/config`
- `observations/models.py`, `observations/provenance.py`, `observations/__init__.py`
- the three existing exporters and `exporters/__init__.py`
- `reporting/canonical_presentation.py`, `reporting/discovery_summary.py`
- `devtools/validate.py`, `benchmark.py`, `compare.py`, `diagnostics.py`
- `docs/`, `benchmarks/`, `knowledge/`, `.gitignore`, `README.md`, `ROADMAP.md`, `main.py`, `requirements.txt`

Under `networkmapper/identity`, only the two files authorized for the fix changed. Across both commits, 16 files changed in total: 13 + 4, with `tests/test_devtools_replay_observations.py` changed by both.

---

## 4. Requirement Checklist

File references are to `HEAD` `97b22e7`. Test abbreviations:
- **RF** = `tests/test_observation_replay_format.py`
- **EX** = `tests/test_observation_json_exporter.py`
- **DT** = `tests/test_devtools_replay_observations.py`
- **IR** = `tests/test_identity_resolver.py`
- **CLI** = `tests/test_application_cli.py`
- **RR** = `tests/test_report_run.py`

**Battery** refers to the independent checks in Section 5.

### 4.1 ADR-011 Amendment 1

| # | Decision or boundary | Evidence | Result |
|---|---|---|---|
| D1 | `observations.json` is written on every run, once, into the run's report directory; sole purpose is replay | `application.py:232-235` calls the exporter unconditionally; no CLI flag was added (battery E4). Path is `report_run.py:35,74`. Tests: CLI `test_observations_are_exported_on_every_run_before_the_other_report_artifacts`; RR `test_markdown_and_csv_paths_live_inside_the_run_directory` | ✅ |
| D2 | A read-only exporter writes it (ADR-005) | `exporters/observation_json_exporter.py:27-30` reads only `project.observations`. Test: EX `test_export_is_read_only` | ✅ |
| D3 | Lossless: every observation, including **duplicates** and **unresolved-endpoint relationships**, every field verbatim | `replay_format.py:156-193` writes every field; nothing is filtered or de-duplicated. Tests: RF `test_duplicate_observations_are_preserved`, `test_relationship_observation_with_an_unresolved_endpoint_is_preserved`, `test_every_field_is_written_verbatim`. Battery A3, B3: 4,959 duplicates and 5,469 unresolved or self-loop relationship observations preserved | ✅ |
| D3 | **`observed_at` exact**, including sub-second precision and timezone presence or absence | Written with `isoformat()` (`replay_format.py:190`); read with `fromisoformat` plus a canonical-form check (`replay_format.py:300-315`). Tests: RF `ObservedAtFidelityTest` (8 tests). Battery A5, B5, B7 | ✅ |
| D3 | **`source_run` exact**, as an opaque value | Written and read verbatim (`replay_format.py:191`). Tests: RF `test_source_run_round_trips_exactly_as_an_opaque_string`, `test_observations_differing_only_in_source_run_stay_distinct`. Battery A5 | ✅ |
| D4 | **Deterministic bytes** whatever the collection order; explicit format identifier and version; no wall-clock, host, operator or credential data | Total 8-field sort (`replay_format.py:202-224`); `json.dumps(sort_keys=True, indent=2, ensure_ascii=True)` plus `\n`, encoded as ASCII (`replay_format.py:91-92`); written in binary (`exporter:29`). Envelope `replay_format.py:86-90`. Tests: RF `test_output_is_byte_identical_across_many_random_input_orders`, `test_bytes_are_ascii_with_lf_line_endings_and_one_trailing_newline`, `test_artifact_has_no_fields_beyond_the_format_and_the_observations`. Battery A1, A2 (6,000 shuffles), B1, B2. See also Section 6.2 | ✅ |
| D5 | **Unknown format, version or type rejected, never skipped** | Format check `replay_format.py:117-124`; version check `:126-134`, which uses `type(...) is int` so `true` and `1.0` are rejected; type check in `_from_record` (`:227-245`); unknown keys `:284-291`; duplicate JSON keys `:338-346`. No partial list is ever returned. Tests: RF `RejectionTest` (21 tests); DT loader-message tests (exit 2). Battery C1–C15 | ✅ |
| D6 | Replay is the only consumer; **replay reproduces canonical identities and relationships exactly** | Loader `replay_format.py:95-153`; replay in `devtools/replay_observations.py:133-146`. **Exact identity replay depends on `97b22e7`** (`identity/resolver.py:166-184`). Tests: DT `test_identity_only_run_replays_canonical_identities_exactly`, `test_mixed_run_replays_identities_and_relationships_exactly`, `test_every_identity_state_is_reproduced`, `test_replay_is_exact_whatever_order_the_run_collected_observations_in`, `test_replay_is_exact_end_to_end_from_real_providers`, `test_replay_is_exact_for_identity_observations_that_tie_on_source_and_value`; IR tie tests. Battery A7, A8, A9, H1, H2: 87 of 87 at `97b22e7`; A7, H1 and H2 fail at `e12b81a` | ✅ |
| D6 | Read-only `python -m devtools replay-observations <run_dir>`; never modifies the run directory | `devtools/__main__.py:71-74`. The module's only file calls are `is_dir`, `is_file`, `read_bytes` and `open(..., "r")` (`replay_observations.py:181,243-251`; `replay_format.py:153`). Test: DT `test_command_is_read_only`. Battery A11, E7, F2, F3, F7 | ✅ |
| D7 | **Credentials never appear**, tested directly | By construction: the exporter reads observations only, and the format and exporter modules never reference credentials (battery D4). By test: EX `test_credentials_never_appear_in_the_artifact` drives all four SNMP providers with a sentinel community. Battery D1–D3. Mutants M25 and M26 are caught | ✅ |
| B | No `.nmproj` or `ProjectSerializer` change | `networkmapper/project` unchanged (Section 3). Test: EX `test_project_serializer_output_is_unaffected_by_observations`. Battery G1 | ✅ |
| B | No loading into `Project` or into any normal run, report, comparison, workbench or benchmark workflow | **The loader is not referenced by any production path.** The format module is imported only by the exporter (`serialize_observations` only) and by `devtools/replay_observations.py` (battery E1, E2, using an AST scan of 84 production files). Tests: RF `test_no_production_path_references_or_invokes_replay_loading`, `test_exporter_module_uses_only_the_serializer`. Mutants M23 and M24 are caught | ✅ |
| B | No cross-run store, observation identifiers, retention policy, database or persisted interpretations | Top-level keys are exactly three. An `id` key is rejected (battery C6), as is a `canonical_identities` key (battery C8). Test: EX `test_export_contains_observations_only`. Battery G2 | ✅ |
| B | No provider, observation-type, resolver, classification or existing-report behavior change | Section 3. The only resolver change is the authorized `97b22e7` tie ordering. The existing exporters' calls and their order are unchanged (battery E3). Benchmarks are at 100.0% | ✅ |
| B | **No gateway or topology behavior** | No such term appears in any new module (battery G3). `relationships/` and `discovery/` are unchanged, so no category was registered and no provider was added | ✅ |
| B | No committed raw production artifact | Section 3. Fixtures use documentation address ranges only | ✅ |

### 4.2 PLAN-029

| # | Requirement | Evidence | Result |
|---|---|---|---|
| D1 | Format module at `networkmapper/observations/replay_format.py`; replay and comparison in `devtools/` | As stated. Battery E5: importing the format module loads no resolver, project or provider module | ✅ |
| D2 | Architectural guard test, with the format and exporter modules exempt | RF `test_no_production_path_references_or_invokes_replay_loading` (`test_observation_replay_format.py`, `ArchitectureTest`) | ✅ |
| D3 | Envelope `format`, `format_version`, `observations` and nothing else | `replay_format.py:86-90`. Battery B1 | ✅ |
| D4 | Strict loader | Section 4.1, D5 row | ✅ |
| D5 | Byte form | `replay_format.py:91-92`; `exporter:29` (`"wb"`). Battery B2. Mutant M18 (text-mode writing) is caught | ✅ |
| D6 | Writer never coerces | `replay_format.py:196-199`. Test: RF `WriterStrictnessTest`. Battery B9. Mutant M17 is caught | ✅ |
| D7 | Timestamps never normalized | `replay_format.py:190`. Battery B5. Mutants M5 and M6 are caught | ✅ |
| D8 | **Observation exporter runs before the existing exporters** | `application.py:232` comes before `CsvExporter` (`:237`), `RelationshipCsvExporter` (`:242`) and `MarkdownExporter` (`:247`). Test: CLI `test_observations_are_exported_on_every_run_before_the_other_report_artifacts`. Battery E3 (AST). Mutant M27 is caught | ✅ |
| D9 | Written once per application run, plain overwrite, no exclusive-create | `exporter:29`. Test: EX `test_export_overwrites_an_existing_file` | ✅ |
| D10 | **Command compares relationships with `relationships.csv`; reports identity counts with the stated limitation** | Comparison of Subject, Category, Related Subject, State and Provenance, in order (`replay_observations.py:149-235`). The label "(not compared: no machine-readable identity artifact)" is at `:297`, and the module docstring limitation is at `:9-12`. Tests: DT `ComparisonTest` (10 tests). Battery A10, F1, F3, F4. Mutants M19 and M20 are caught | ✅ |
| 7.4 | Exit codes: 0 match, 1 mismatch, 2 cannot replay; usage gives 1 | `replay_observations.py:61-63,238-264`. Tests: DT `CommandTest` (14 tests). Battery F1–F8. Mutant M21 is caught | ✅ |
| 8 | Error messages as specified | Tests: RF `RejectionTest` (exact strings); DT exit-2 tests. PLAN deviations 2 and 3 (an extra duplicate-key message and two extra messages) were reported at implementation and approved with the commit | ✅ |
| 9.2.5 | `ProjectSerializer` output unaffected | EX `test_project_serializer_output_is_unaffected_by_observations` | ✅ |
| Ruling 1 | Identity limitation stated explicitly; exact identity replay proven by tests | Command output and docstring. DT and IR tests listed in Section 4.1, D6 row | ✅ |
| Ruling 2 | No production path references or invokes the loader; guard test retained | Section 4.1, loader row | ✅ |
| Prerequisite | Identity tie ordering (`97b22e7`) | `identity/resolver.py:131,166-184`. Tests: IR `test_observations_differing_only_in_source_run_resolve_in_the_same_order`, `test_observations_differing_only_in_observed_at_resolve_in_the_same_order`, `test_source_run_orders_before_observed_at`, `test_tied_observations_with_mixed_naive_and_aware_timestamps_sort_without_error`, `test_resolve_is_order_independent_with_tied_observations_across_many_permutations`, `test_tie_ordering_does_not_change_corroboration_states`; DT `test_replay_is_exact_for_identity_observations_that_tie_on_source_and_value`. Mutants M28–M30 are caught | ✅ |

---

## 5. Independent Verification

**Harness.** `independent_battery.py` ran from the root of a clean `git archive 97b22e7` export. It defines two reference models from the governing text.

- **Artifact model** (PLAN-029 Sections 4, 5 and D5). It builds each record from an observation's fields, sorts records by the Section 5 table, and serializes with the specified JSON options. The implementation's bytes are compared with this model's bytes.
- **Canonical-output model** (ADR-012; ADR-013 and its Amendment 1). Identity follows these rules:
  - property state is CONFLICTING if more than one value is reported, otherwise CONFIRMED with two or more `(provider, method)` sources, otherwise WEAK;
  - identity state is CONFLICTING if any property conflicts, otherwise CONFIRMED if any property is confirmed, otherwise PROBABLE with two or more properties, otherwise WEAK.

  Relationships follow these rules:
  - edges are formed after the endpoint gate and self-loop exclusion;
  - every category is multi-valued, so an edge is CONFIRMED with two or more sources and WEAK otherwise;
  - provenance tokens follow the PLAN-027 5.1 rule, in PLAN-028 D6 order.

**Generator.** 2,000 random observation sets, seeded, totalling 34,532 observations. They contain:

- 4,959 exact duplicates;
- 5,469 relationship observations with an undiscovered endpoint (`198.51.100.77`, `203.0.113.5`) or a self-loop;
- awkward strings: accents, quotes, a backslash, CR and LF, a tab, an empty string, padding, CJK text and a lone surrogate;
- seven timestamps: naive with microseconds, naive whole-second, naive with a single microsecond, UTC, −05:00, +05:30 with 999,999 µs, and a 1999 date;
- five `source_run` values, including an empty string and a mixed-case padded string;
- six sources, and five categories including two unregistered ones.

**Results at `97b22e7`: 87 of 87 checks pass.**

| Group | Checks | What was verified |
|---|---|---|
| A. Randomized | 12 | Bytes equal the reference model for all 2,000 sets. Bytes are identical across 6,000 shuffles. The record multiset, read back with the standard library only, equals the input. The loader round-trips the multiset, `observed_at` (text, naive or aware, offset) and `source_run`. `serialize(load(file))` reproduces the file. In 400 full replays through the file system: identities and relationships equal the run's exactly; identities equal the ADR-012 model (1,482 identities); relationships equal the ADR-013 model (944 edges, 16 confirmed); the CSV's compared columns equal the model, including provenance; and the command reports MATCH with exit 0 and writes nothing. |
| B. Structure | 12 | Exact envelope and record keys. ASCII, LF only, one trailing newline. Duplicate and unresolved records are written. Timestamps are written verbatim. A named (non-`timezone`) zone round-trips equal, with the same ISO text and offset, as a fixed-offset `timezone` (the documented limit). Mixed naive and aware timestamps sort without error. The writer refuses four kinds of coercion. |
| C. Rejection | 26 | Unknown or missing format; eight bad versions (`2`, `0`, `-1`, `"1"`, `1.0`, `true`, `null`, `[1]`); unknown and wrong-case types; unknown record, provenance and top-level keys (including `id` and `canonical_identities`); missing `source_run`; a null value; five non-canonical timestamps; invalid JSON; a top-level array; a duplicate key; a non-array `observations`. |
| D. Credentials | 4 | All four real SNMP providers ran through a stub client with a sentinel community. The client received the sentinel at least 12 times, and the providers produced `arp_neighbor`, `bridge_fdb` and `connected_to` evidence. The sentinel is absent from the artifact in any letter case, as are `community` and `***`. It is absent from every in-memory observation field. The format and exporter modules contain no credential reference. |
| E. Architecture (AST) | 7 | No production module imports or names the loader, exporter included (84 files). The format module is imported by exactly two modules: the exporter (`serialize_observations` only) and devtools replay (`load_observations` plus constants). `Application.run()` export order is observations, csv, relationships, markdown. No new CLI flag. Importing the format module loads no resolver, project or provider module. The replay module imports no project, serializer, provider or exporter module, opens files only in `"r"` mode, and makes no write, delete or create call. |
| F. Command | 14 | MATCH with exit 0 and the identity limitation printed. Byte-identical files. Six CSV corruptions each give exit 1 and write nothing: a state change, a provenance change, a provenance token reorder, a removed row, an added row and a changed related subject. Changed hostname columns still match. A missing directory gives exit 2; no argument gives exit 1. Unknown format, version and type each give exit 2 and write nothing. An empty run gives exit 0. |
| G. Boundaries | 3 | `.nmproj` output is byte-identical with and without observations. The artifact holds no canonical state, device data or run metadata. No gateway or topology term appears in any new module. |
| H. Identity ties | 8 | Four tie families: `source_run` only, `observed_at` only, naive and aware, and mixed with duplicates. In each, across 100 input orders, the resolver's observation order equals the reference order (provider, method, value, `source_run`, ISO timestamp), and the replayed identities equal the run's exactly. |

**The same battery against the feature commit alone (`e12b81a`): 78 of 87.** The failing checks are A7 (12 of 400 replays differ, in identities only) and all eight H checks. Every other check passes. This isolates the defect to identity tie ordering and shows that `97b22e7` closes it without affecting anything else.

---

## 6. Mutation and Negative Checks

### 6.1 Results

Each mutant injects one defect into a fresh copy of the clean `97b22e7` export, then runs the committed `tests/` suite on that copy. The unmutated export passed first: **880 passed, 86 subtests passed.** Copies were deleted after each run, and the repository working tree was never modified.

| Mutant | Defect | Result | Failing tests (count; examples) |
|---|---|---|---|
| M1 | `source_run` omitted from the artifact | Killed | 103; `test_source_run_round_trips_exactly_as_an_opaque_string`, `test_every_field_is_written_verbatim` |
| M2 | `source_run` written as a constant | Killed | 23; `test_duplicate_observations_are_preserved`, `test_identity_only_run_replays_canonical_identities_exactly` |
| **M3** | **`source_run` ignored by the record sort key** | **Survived at `97b22e7`** | 0. See Section 6.2. Killed by the pending tests (Section 6.3) |
| M4 | `observed_at` omitted from the artifact | Killed | 102; `test_aware_timestamp_is_never_normalized_to_utc` |
| M5 | `observed_at` normalized: timezone stripped | Killed | 8; `test_aware_utc_timestamp`, `test_aware_timestamp_with_a_negative_offset` |
| M6 | `observed_at` normalized: sub-second precision dropped | Killed | 23; `test_every_field_is_written_verbatim`, `test_aware_utc_timestamp` |
| M7 | Unknown record and provenance keys accepted | Killed | 3; `test_unknown_keys_are_rejected_not_dropped` |
| M8 | Unknown top-level keys accepted | Killed | 1; `test_unknown_top_level_key_is_rejected` |
| M9 | Duplicate observations collapsed | Killed | 4; `test_duplicate_observations_are_preserved`, `test_mixed_run_replays_identities_and_relationships_exactly` |
| M10 | Unresolved relationship endpoints dropped from the artifact | Killed | 26; `test_export_writes_exactly_the_serialized_observations`, `test_load_observations_reads_a_file_written_from_the_serialized_bytes` |
| M11 | Unknown format identifier accepted | Killed | 4; `test_unknown_format_identifier_is_rejected`, `test_unknown_format_identifier_exits_two_with_the_loader_message` |
| M12 | Unsupported format version accepted | Killed | 4; `test_unknown_format_versions_are_rejected` (subtests), `test_unknown_format_version_exits_two_with_the_loader_message` |
| M13 | Version compared with `==` (`true` and `1.0` accepted) | Killed | 2 subtests of `test_non_integer_format_versions_are_rejected` (`version=True`, `version=1.0`) |
| M14 | Unknown observation type silently skipped | Killed | 3; `test_unknown_observation_type_fails_the_whole_load`, `test_unknown_observation_type_exits_two_with_the_loader_message` |
| M15 | Non-canonical timestamps accepted | Killed | 3 subtests of `test_non_canonical_and_unparseable_timestamps_are_rejected` |
| M16 | Records not sorted (output follows input order) | Killed | 2; `test_output_is_byte_identical_across_many_random_input_orders`, `test_records_are_sorted_by_type_then_fields` |
| M17 | Writer coerces non-string fields | Killed | 7 subtests of `test_non_string_fields_are_never_coerced` |
| M18 | Exporter writes in text mode (platform line endings) | Killed | 3; `test_export_writes_exactly_the_serialized_observations` |
| M19 | Replay comparison ignores provenance | Killed | 2; `test_changed_provenance_is_a_mismatch`, `test_untouched_run_matches` |
| M20 | Replay comparison ignores state | Killed | 4; `test_changed_state_is_a_mismatch` |
| M21 | Mismatch reported as exit 0 | Killed | 8; `test_mismatching_run_prints_counts_and_exits_one`, `test_changed_state_is_a_mismatch` |
| M22 | Replay command writes into the run directory | Killed | 1; `test_command_is_read_only` |
| M23 | Loader imported by `Application` (production path) | Killed | 1; `test_no_production_path_references_or_invokes_replay_loading` |
| M24 | Loader referenced through a module alias in `ProjectSerializer` | Killed | 1; `test_no_production_path_references_or_invokes_replay_loading` |
| M25 | Credentials in exported content (ARP provider uses the community as `source_run`) | Killed | 1; `test_credentials_never_appear_in_the_artifact` |
| M26 | Credentials in exported content (system-group provider writes the community into `sysName` evidence) | Killed | 4; `test_credentials_never_appear_in_the_artifact` |
| M27 | Observation exporter runs after the existing exporters | Killed | 1; `test_observations_are_exported_on_every_run_before_the_other_report_artifacts` |
| M28 | Identity tie-breakers removed (the pre-`97b22e7` key) | Killed | 6; `test_observations_differing_only_in_source_run_resolve_in_the_same_order`, `test_replay_is_exact_for_identity_observations_that_tie_on_source_and_value` |
| M29 | Identity `observed_at` tie-breaker removed | Killed | 4; `test_observations_differing_only_in_observed_at_resolve_in_the_same_order` |
| M30 | Identity `source_run` tie-breaker removed | Killed | 4; `test_source_run_orders_before_observed_at` |

**29 of 30 killed by the tests committed at `97b22e7`; 30 of 30 with the pending tests (Section 6.3).** Every category the task required is covered: `source_run` omitted or ignored (M1–M3), `observed_at` omitted or normalized (M4–M6), unknown keys accepted (M7, M8), duplicates collapsed (M9), unresolved endpoints dropped (M10), comparison ignoring provenance (M19), an unauthorized loader import (M23, M24), credentials in exported content (M25, M26), and identity tie-breakers removed (M28–M30).

### 6.2 Finding: M3 survives the committed tests

This is the finding as originally recorded against `97b22e7`. Section 6.3 records its closure.

**The gap.** Removing `source_run` from the artifact's record sort key (`replay_format.py:222`) leaves every test committed at `97b22e7` passing. With that key, two records that differ only in `source_run` keep their input order. The file's bytes would then depend on collection order, which violates Amendment 1 Decision 4.

**Why the tests miss it.** The committed determinism fixtures contain no pair of records that tie on every field except `source_run`. The closest pair in `test_output_is_byte_identical_across_many_random_input_orders` also differs in `observed_at`.

**Not an implementation defect.** The committed code includes `source_run` in the key, and the independent battery verifies the behavior directly. Run against an M3-mutated copy, the battery fails A1 (48 of 2,000 sets differ from the reference bytes) and A2 (12 shuffle differences). So the requirement is verified for `97b22e7`, but the committed suite would not catch a future regression of this field alone.

**Correction to the first draft of this section.** The first draft also said that removing `observed_at` from the key would leave the same kind of gap. That was not checked at the time, and it is wrong. Section 6.3, check 4, shows that the existing test `test_output_is_byte_identical_across_many_random_input_orders` already catches that mutation, because its fixtures include records that differ only in `observed_at`.

### 6.3 Closure: pending test-only addition

At the architect's direction, two tests were added to `DeterminismTest` in `tests/test_observation_replay_format.py`. Production code was not changed. The addition is **pending**: it is in the working tree, not in `97b22e7`.

- `test_identity_records_differing_only_in_source_run_are_ordered_by_source_run`
- `test_relationship_records_differing_only_in_source_run_are_ordered_by_source_run`

**Why two tests.** Identity and relationship records are built by separate branches of `_to_record`, and they take separate branches when `_record_sort_key` picks its third and fourth fields. Each test exercises one branch.

**What each test does.** It builds two synthetic observations, identical in every field except `source_run` (`"run-b"` and `"run-a"`). It serializes them in both input orders, then asserts:
- the two outputs are byte-identical;
- both records are present;
- the records are ordered `run-a` then `run-b`, following the approved PLAN-029 Section 5 order, where `source_run` sits at position 7, before `observed_at`;
- the loader returns both observations.

**Mutation evidence.** All runs used throwaway copies of a clean `git archive 97b22e7` export. The repository was not mutated.

| # | Copy | Command | Result |
|---|---|---|---|
| 1 | `97b22e7` + pending test file, unmutated | the two new tests | **2 passed**, exit 0 |
| 2 | `97b22e7` + pending test file, **M3 applied** | the two new tests | **2 failed**, exit 1. Both fail on the byte-equality assertion: the forward output lists `run-b` first and the backward output lists `run-a` first |
| 2 | same | `python -m pytest tests/ -q` | **2 failed, 880 passed**, exit 1. The two failures are exactly the new tests |
| 3 | `97b22e7` only (no pending tests), **M3 applied** | `python -m pytest tests/ -q` | **880 passed**, exit 0. This reproduces the original survival |
| 4 | `97b22e7` + pending test file, **`observed_at` removed from the key** | `python -m pytest tests/ -q` | **1 failed, 881 passed**, exit 1: `test_output_is_byte_identical_across_many_random_input_orders`. This sibling was already covered |

Failure output from check 2, abbreviated by pytest:

```
E   AssertionError: b'{\n[316 chars]"run-b"\n      },\n      "subject": "192.0.2.1[414 chars]n}\n' != b'{\n[316 chars]"run-a"\n      },\n      "subject": "192.0.2.1[414 chars]n}\n'
E   AssertionError: b'{\n[315 chars]"run-b"\n      },\n      "related_subject": "1[431 chars]n}\n' != b'{\n[315 chars]"run-a"\n      },\n      "related_subject": "1[431 chars]n}\n'
FAILED tests/test_observation_replay_format.py::DeterminismTest::test_identity_records_differing_only_in_source_run_are_ordered_by_source_run
FAILED tests/test_observation_replay_format.py::DeterminismTest::test_relationship_records_differing_only_in_source_run_are_ordered_by_source_run
2 failed in 0.15s
```

**Status.** The gap is closed once the pending tests are committed. Until then, `97b22e7` alone still has the gap described in Section 6.2.

---

## 7. Validation Output

### 7.1 Committed baseline `97b22e7`

Run on the working tree before the pending test was added, when its code was identical to `97b22e7`.

**`python -m pytest tests/ -q`** (exit 0):

```
........................................................................ [  8%]
........................................................................ [ 16%]
........................................................................ [ 24%]
...................................................................... [ 32%]
........................................................................ [ 40%]
................................................................... [ 48%]
.................................................................. [ 55%]
...................................................................................................... [ 67%]
......................................................... [ 73%]
.................................................................. [ 81%]
........................................................................ [ 89%]
............................................................................................                                           [100%]
880 passed, 86 subtests passed in 9.72s
```

**`python -m pytest tests/test_observation_replay_format.py tests/test_observation_json_exporter.py tests/test_devtools_replay_observations.py -q`** (exit 0):

```
........................................ [ 45%]
................................................       [100%]
88 passed, 50 subtests passed in 2.36s
```

**`python -m devtools validate --all`** (exit 0):

```
JSON report: C:\Users\mylesm\AppData\Local\Temp\tmp3mgzpurf\nested\reports\benchmarks\dataset_output_dir.json
========================================
NetworkMapper Full Validation
========================================

Unit Tests

PASS

Tests Run: 880
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

- Total executed: 880
- Passed: 880
- Failed: 0
- Errors: 0
- Runtime: 9.45s

Benchmarks

- Enterprise: PASS
- Homelab: PASS
- Small Office: PASS

Overall Result

PASS
```

**Independent battery** (`git archive 97b22e7` export): **87/87 checks passed.** The same battery against `e12b81a` gives 78/87; Section 5 explains the difference.

**Mutation check:** **29 of 30 killed**; Section 6.

### 7.2 Pending test-only addition

Run on the working tree after the two tests were added. Production and devtools code was identical to `97b22e7`; the only code difference was `tests/test_observation_replay_format.py`. The suite grows from 880 to 882, which is the two new tests.

**`python -m pytest tests/test_observation_replay_format.py -q`** (exit 0):

```
........................................ [ 78%]
...........                                              [100%]
51 passed, 48 subtests passed in 0.43s
```

**`python -m pytest tests/ -q`** (exit 0):

```
........................................................................ [  8%]
........................................................................ [ 16%]
........................................................................ [ 24%]
...................................................................... [ 32%]
........................................................................ [ 40%]
................................................................... [ 48%]
.................................................................. [ 55%]
........................................... [ 60%]
........................................................... [ 67%]
......................................................... [ 73%]
.................................................................. [ 81%]
........................................................................ [ 89%]
..............................................................................................                                         [100%]
882 passed, 86 subtests passed in 8.99s
```

**`python -m devtools validate --all`** (exit 0):

```
JSON report: C:\Users\mylesm\AppData\Local\Temp\tmpasz801z4\nested\reports\benchmarks\dataset_output_dir.json
========================================
NetworkMapper Full Validation
========================================

Unit Tests

PASS

Tests Run: 882
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

- Total executed: 882
- Passed: 882
- Failed: 0
- Errors: 0
- Runtime: 8.43s

Benchmarks

- Enterprise: PASS
- Homelab: PASS
- Small Office: PASS

Overall Result

PASS
```

---

## 8. Smoke Test Output

The synthetic run directory was built outside the repository, in the session scratch folder (shown as `<SCRATCH>`), with the real `ObservationJsonExporter` and `RelationshipCsvExporter`. Its contents:

- 12 observations, using documentation addresses only;
- an identity tie on `source_run`, and an identity tie on `observed_at` with a −05:00 value;
- an exact duplicate relationship observation;
- an unresolved endpoint (`198.51.100.77`);
- a non-ASCII hostname;
- a relationship confirmed by two sources.

```
$ python smoke_build.py <SCRATCH>/smoke/2026-10-14_091502_standard
wrote 12 observations, 3 identities, 3 relationships
[exit code: 0]

$ sha256sum *   (before)
58adf8f4112d5379206fe54ef1a1b41cdc09c9855836d260ce497233327e4c2f *observations.json
38b328ee5d48270cb9e52d55467e95fc73eac073bcb392972c41c547bc8a4611 *relationships.csv

$ python -m devtools replay-observations <SCRATCH>/smoke/2026-10-14_091502_standard
========================================
NetworkMapper Observation Replay
========================================
Run directory          : <SCRATCH>/smoke/2026-10-14_091502_standard
Format                 : networkmapper.retained-observations v1
Observations           : 12 (6 identity, 6 relationship)
Canonical identities   : 3 (not compared: no machine-readable identity artifact)
  weak 2 / probable 0 / confirmed 1 / conflicting 0
Canonical relationships: 3 replayed, 3 in relationships.csv
  weak 2 / confirmed 1 / conflicting 0
Result                 : MATCH
========================================
[exit code: 0]

$ sha256sum *   (after)
58adf8f4112d5379206fe54ef1a1b41cdc09c9855836d260ce497233327e4c2f *observations.json
38b328ee5d48270cb9e52d55467e95fc73eac073bcb392972c41c547bc8a4611 *relationships.csv
(2 files, unchanged)

$ python -m devtools replay-observations <SCRATCH>/smoke/does-not-exist
Error: run directory not found: <SCRATCH>/smoke/does-not-exist
[exit code: 2]

$ python -m devtools replay-observations
Usage: python -m devtools <command>
Commands:
  validate        Run the fast classifier regression suite
  validate --all  Run every test module and every benchmark dataset
  benchmark  Run canonical benchmark workflow
  compare    Compare two benchmark JSON reports
  diagnostics  Run canonical developer environment diagnostics
  replay-observations <run_dir>  Replay a run's observations.json (read-only)
[exit code: 1]
```

The `relationships.csv` that was replayed:

```
Subject,Subject Hostname,Category,Related Subject,Related Subject Hostname,Corroboration State,Provenance
192.0.2.1,,arp_neighbor,192.0.2.10,,weak,snmp/ipNetToPhysicalTable
192.0.2.1,,arp_neighbor,192.0.2.11,,weak,snmp/ipNetToPhysicalTable
192.0.2.1,,connected_to,192.0.2.10,,confirmed,"nmap/lldp-neighbor,snmp/lldpRemTable"
```

The `198.51.100.77` observation is present in `observations.json` and absent from `relationships.csv`, as it should be: it is retained as evidence, but it does not resolve to a canonical relationship.

---

## 9. Residual Risks

None of these is a defect in the verified commits, and none blocks them.

1. **No live production scan was run.** All evidence here is synthetic or from stubbed providers. Real artifact sizes (PLAN-029 R1), SNMP reachability and real observation volumes remain unmeasured until OPS-001 runs.
2. **The replay command does not prove exact production identity equality by comparison.** A run directory has no machine-readable canonical identity artifact, so the command compares relationships with `relationships.csv` and only *reports* identity counts. Its MATCH result is a statement about relationship rows only (architect ruling 1).
3. **Exact identity replay is proven by tests and by independent verification, not by parsing production output.** The committed DT and IR tests, battery checks A7, A8, H1 and H2, and mutants M28–M30 establish it. No production `report.md` was parsed, by design.
4. **The test-coverage gap from Section 6.2 is closed only once the pending tests are committed.** At `97b22e7` alone, the committed suite would not catch the loss of `source_run` from the artifact's record sort key. The two pending tests catch it (Section 6.3). The loss of `observed_at` from the key was already caught at `97b22e7`.
5. **Named timezones are recorded as fixed offsets**, and `fold` is not recorded (PLAN-029 Section 6; battery B7). Providers stamp naive `datetime.now()` today, so this has no effect on current data.
6. **Visible ordering change from `97b22e7`.** In `report.md`, provenance lines for identity observations that tie on source and value now appear in a stable `(source_run, timestamp)` order instead of collection order. No state, value or count changes.
7. **Same-session implementation and verification (Section 2).** The session that implemented the feature, the fix and the pending tests also performed this verification. The reference models are independent methods, not a second-party review.
8. **OPS-001 remains blocked until this VER-029 report is committed.** After that, OPS-001 needs the separate wording update PLAN-029 Section 13 describes:
   - step 5: no export flag; the artifact is `output\<run>\observations.json`;
   - step 9: `python -m devtools replay-observations <run_dir>`, expected MATCH with exit 0;
   - success criterion 5: no longer requires identity comparison by the command;
   - Section 7: the artifact's file name.

   OPS-001 must then be resubmitted for approval to run.

---

## 10. Final Approval Recommendation

**Accept FEAT-OBSERVATION-JSON-EXPORT (`e12b81a`), together with its prerequisite fix (`97b22e7`), as verified.**

At `97b22e7`, the implementation meets every ADR-011 Amendment 1 decision and boundary and every PLAN-029 requirement and architect ruling. In particular:

- the artifact is lossless, deterministic and strictly versioned;
- replay reproduces canonical identities and relationships exactly;
- no production path references or invokes the loader;
- credentials never appear in the artifact;
- the observation exporter runs first;
- the replay command is read-only, and its identity limitation is stated where it is printed.

No `.nmproj`, `ProjectSerializer`, provider, relationship, classification, existing-report, gateway or topology behavior changed.

**Required fixes to production code:** none.

**Test coverage:** the gap found in Section 6.2 is closed by the two pending tests in `tests/test_observation_replay_format.py` (Section 6.3). They pass against the committed implementation, fail under M3, and leave the full gate green (Section 7.2). They should be committed together with this report, or before it, so that the committed suite matches what this report describes.

**Next step:** commit the pending tests and this report. Then, as a separate change, update OPS-001 as described in Section 9, item 8, and resubmit it for approval to run.
