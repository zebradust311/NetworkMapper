# Status

Approved — Architect-Reviewed

Approval: Architect-approved on 2026-10-13 for implementation as FEAT-OBSERVATION-JSON-EXPORT, including decisions D1–D10 (Section 2) and architect rulings 1–4 (Section 2.1).

Revision: architect rulings 1–4 applied (Section 2.1). No open questions remain.

Authority: [ADR-011 Amendment 1 — Replay Observation Export](../ADR.md) (committed `84153e0`), which authorizes exactly one implementation sprint, FEAT-OBSERVATION-JSON-EXPORT, and requires this plan to be approved before any code is written. Design source: [ARCH-028](../reports/ARCH-028-Observation-JSON-Export-Authorization.md) Sections 4, 6, 7 and 9. Consumer: [OPS-001](OPS-001-SNMP-Enabled-Production-Evidence-Collection.md), currently blocked on this FEAT.

Baseline: `HEAD` `84153e0`. All file and line references below are as of that commit. The suite collects 784 tests at this baseline.

Implements: the "FEAT-OBSERVATION-JSON-EXPORT" sprint authorized by ADR-011 Amendment 1, §Authorization.

Production Code Modified: No. This is a planning document only.

New ADR Required: No. ADR-011 Amendment 1 is the governing decision. This plan implements it and introduces no new policy.

**OPS-001 remains blocked.** It stays blocked until this FEAT **and** its VER report are both committed (Section 13).

---

## 1. Sprint Name and Scope

**FEAT-OBSERVATION-JSON-EXPORT — Per-Run Replay Observation Artifact.**

The sprint makes five changes:
- Every run writes a deterministic, versioned `observations.json` into its run output directory. It is written once per application run.
- A read-only exporter writes it (ADR-005).
- `ReportRunPaths` gains one artifact path.
- A loader reconstructs the observation objects, for replay verification only.
- A read-only command, `python -m devtools replay-observations <run_dir>`, replays a run's artifact through the committed resolvers and compares the result with that run's `relationships.csv`.

**Scope exclusions** are listed in full in Section 11.

---

## 2. Decisions (D1–D10)

| # | Decision | Rationale |
|---|---|---|
| **D1** | **Module layout.** The format (constants, serializer, loader, error type) lives in one new module, `networkmapper/observations/replay_format.py`. The exporter is a thin class in `networkmapper/exporters/`. The replay function and the comparison live in `devtools/`, **not** in `networkmapper/`. | Keeping writer and reader in one module keeps the format in one place. Putting replay in `devtools/` means no production path references or invokes the loader, and `networkmapper/observations/` gains no dependency on `identity/` or `relationships/`, which already depend on it. This departs from ARCH-028 §9 item 5, which suggested `networkmapper/observations/replay.py`. **Approved (ruling 2).** |
| **D2** | **An architectural guard test keeps the loader replay-only.** It asserts that no module under `networkmapper/`, other than the format module and the exporter module, imports or uses replay loading (`load_observations`, `parse_observations`) (Section 9.4). | Turns the "replay is the only consumer" boundary into a failing test, not a convention. The claim is precise: no production path references or invokes the loader. The loader is still importable, like any module. **Guard test retained (ruling 2).** |
| **D3** | **Envelope:** `{"format": "networkmapper.retained-observations", "format_version": 1, "observations": [...]}`. No other top-level key. | ARCH-028 §4 item 4. No wall-clock, host, operator or run-metadata field, as Amendment 1 Decision 4 requires. |
| **D4** | **The loader is strict.** It rejects unknown or missing keys at every level, wrong value types, and non-canonical timestamps, in addition to the three rejections the amendment names. | Amendment 1 Decision 5: content must never be silently skipped or dropped. An unknown key is content. |
| **D5** | **Serialization form:** `json.dumps(..., sort_keys=True, indent=2, ensure_ascii=True)`, plus one trailing `\n`, written as UTF-8 **bytes** with `\n` line endings. | Byte-identical output on every platform. Text-mode writing on Windows would emit `\r\n`. `ensure_ascii=True` keeps the file pure ASCII, so there is no encoding or normalization ambiguity, and it still round-trips any string exactly, including lone surrogates that UTF-8 cannot encode. |
| **D6** | **The serializer never coerces.** A field that is not a `str` (or `observed_at` that is not a `datetime`), or an object that is neither observation type, raises `TypeError`. | Coercing `None` or an `int` would break the lossless guarantee without anyone noticing. All five providers emit `str` fields today (checked at `84153e0`), so this cannot fire on current code. |
| **D7** | **Timestamps are written with `datetime.isoformat()` and never normalized** (Section 6). | Amendment 1 Decision 3; ARCH-028 §7 guarantee 2. |
| **D8** | **The exporter runs first in the report-generation block**, before `CsvExporter`. | The raw evidence is the one artifact that cannot be regenerated. If a later exporter fails, the observations are already on disk. The existing exporters' behavior and relative order are unchanged. **Approved (ruling 3).** |
| **D9** | **The file is written once per application run, with plain overwrite.** It is opened in mode `"wb"`, matching the existing report artifacts' `"w"`. Exclusive-create semantics (`"xb"`) are **not** required. | Plain overwrite is how `report.md`, `devices.csv` and `relationships.csv` already behave, and `build_report_run_paths` already uses `exist_ok=True`. An exclusive-create failure would abort report generation at the end of a long scan. **Ruling 4.** |
| **D10** | **The devtools command compares replayed relationships against `relationships.csv` and reports identity counts only** (Section 7.3). | A run directory holds no machine-readable canonical identity artifact, and adding one would persist an interpretation, which is excluded. The command therefore does not prove exact production identity equality by comparison; exact identity replay is proven by tests. **Accepted with that stated limitation (ruling 1).** |

### 2.1 Architect rulings

1. **Identity comparison (D10).** Accepted: the devtools command compares replayed relationships against `relationships.csv` and reports identity counts. The limitation is explicit (Section 7.3): because the run directory has no machine-readable canonical identity artifact, the command does not prove exact production identity equality by comparison. Exact identity replay must be proven by tests (Section 9.3). OPS-001 needs a later wording update, after the FEAT and VER-029 (Section 13).
2. **Replay location (D1, D2).** Approved: `devtools/` holds replay and comparison; `networkmapper/observations/replay_format.py` holds the format constants, serializer, loader and error type. The plan's claim is the precise one: no production path references or invokes the loader. The architectural guard test stays (Section 9.4).
3. **Exporter order (D8).** Approved: the observation exporter runs before the existing exporters.
4. **Written once per application run (D9).** The artifact is written once per application run. Plain overwrite is acceptable and matches existing report artifact behavior. Exclusive-create semantics are not required. This plan uses "written once per application run" throughout, in place of the shorter label used in ADR-011 Amendment 1 and ARCH-028.

---

## 3. Files to Change

**Production (7 files: 4 new, 3 modified):**

| # | File | Change |
|---|---|---|
| 1 | `networkmapper/observations/replay_format.py` | **New.** `FORMAT_IDENTIFIER`, `FORMAT_VERSION`, `ObservationReplayFormatError`, `serialize_observations`, `parse_observations`, `load_observations`. |
| 2 | `networkmapper/exporters/observation_json_exporter.py` | **New.** `ObservationJsonExporter.export(project, output_path)`. Reads `project.observations` only; writes the bytes from file 1. |
| 3 | `networkmapper/reporting/report_run.py` | `ReportRunPaths` gains `observations_json_path`; `build_report_run_paths` sets it to `<run>/observations.json`. Docstrings updated. |
| 4 | `networkmapper/application.py` | Wiring only: import the exporter, call it first in the report block (D8), print `✓ Observations exported to <path>`. |
| 5 | `devtools/replay_observations.py` | **New.** `replay_observations`, `compare_with_relationships_csv`, `run_replay_command`, `format_replay_report`, and the result dataclasses. |
| 6 | `devtools/__main__.py` | Dispatch `replay-observations <run_dir>`; add one usage line. |
| 7 | `README.md` or `ENGINEERING.md` | Only if either lists the devtools commands or run artifacts; add one line each. Confirm at implementation time. |

**Tests (5 files: 3 new, 2 modified):**

| # | File | Change |
|---|---|---|
| 1 | `tests/test_observation_replay_format.py` | **New.** Round trip, duplicates, unresolved endpoints, timestamp and `source_run` fidelity, determinism, all rejections, the loader guard test (D2). |
| 2 | `tests/test_observation_json_exporter.py` | **New.** Exporter writes the expected bytes, is read-only, and never contains credentials; `ProjectSerializer` output unaffected. |
| 3 | `tests/test_devtools_replay_observations.py` | **New.** Exact replay, comparison outcomes, command exit codes and messages, read-only behavior. |
| 4 | `tests/test_report_run.py` | Assert the new path; assert `observations.json` sits inside the run directory. |
| 5 | `tests/test_application_cli.py` | Add `observations_json_path` to `_fake_report_run_paths()`; patch `networkmapper.application.ObservationJsonExporter` in `_run_application` (without the patch the real exporter would write to `output/fake-run/`); assert the call, the path and the printed line. |

**Explicitly unchanged:**
- `networkmapper/observations/models.py`, `provenance.py` and `__init__.py`. The new module is imported by its full path and is not re-exported.
- All of `networkmapper/discovery/`, `identity/`, `relationships/`, `classification/`, `comparison/`, `developer/`, `knowledge/`.
- `networkmapper/project/models.py` and `project/serializer.py`.
- `networkmapper/reporting/canonical_presentation.py` and the three existing exporters.
- `devtools/validate.py`, including `STANDARD_REGRESSION_TESTS`; `devtools/benchmark.py`, `compare.py`, `diagnostics.py`.
- `docs/ADR.md` (Amendment 1 is already committed) and `.gitignore` (`output/` is already ignored).

---

## 4. JSON Schema

```json
{
  "format": "networkmapper.retained-observations",
  "format_version": 1,
  "observations": [
    {
      "type": "identity",
      "subject": "192.0.2.10",
      "property_name": "hostname",
      "value": "host-a.example",
      "provenance": {
        "provider": "nmap",
        "collection_method": "reverse-dns",
        "observed_at": "2026-10-13T09:15:02.123456",
        "source_run": "0f8e6c1d2b3a49e5a7c6d5e4f3a2b1c0"
      }
    },
    {
      "type": "relationship",
      "subject": "192.0.2.1",
      "related_subject": "192.0.2.10",
      "category": "arp_neighbor",
      "provenance": { "...": "same four keys" }
    }
  ]
}
```

| Element | Rule |
|---|---|
| `format` | The string `networkmapper.retained-observations`, exactly. |
| `format_version` | The integer `1`. A JSON `true`, `1.0` or `"1"` is rejected: the loader requires `type(value) is int`, because `True == 1` in Python. |
| `observations` | An array, possibly empty. An empty array is a valid artifact (a run with no observations). |
| `type` | `"identity"` or `"relationship"`. Maps to `IdentityObservation` or `RelationshipObservation`. |
| Identity record keys | Exactly `type`, `subject`, `property_name`, `value`, `provenance`. |
| Relationship record keys | Exactly `type`, `subject`, `related_subject`, `category`, `provenance`. |
| `provenance` keys | Exactly `provider`, `collection_method`, `observed_at`, `source_run`. |
| Value types | Every leaf is a JSON string. No nulls, numbers or booleans. |
| Not present | Observation identifiers, canonical identities or relationships, device data, run metadata, scan targets, host or operator names, timestamps of the export itself, credentials. |

One record per retained observation. Duplicates produce duplicate records. Relationship observations are written whether or not their endpoints resolve: the exporter never consults the resolvers.

---

## 5. Deterministic Ordering

1. **Record order.** Records are sorted by one total key of eight strings:

   | Position | Identity | Relationship |
   |---|---|---|
   | 1 | `"identity"` | `"relationship"` |
   | 2 | `subject` | `subject` |
   | 3 | `property_name` | `related_subject` |
   | 4 | `value` | `category` |
   | 5 | `provenance.provider` | same |
   | 6 | `provenance.collection_method` | same |
   | 7 | `provenance.source_run` | same |
   | 8 | `provenance.observed_at.isoformat()` | same |

2. **The key is total.** It covers every serialized field. Two records that tie on all eight positions are byte-identical, so their relative order cannot affect the output.
3. **Comparison is by Python `str` ordering** (Unicode code point), which does not depend on locale or platform. `observed_at` is compared through its ISO string, never as a `datetime`, so mixed naive and aware values cannot raise `TypeError` (the same reasoning as PLAN-028 D6).
4. **Key order within objects** comes from `sort_keys=True`.
5. **Whitespace and encoding** are fixed by D5.
6. **Sorting does not affect replay.** Both resolvers are order-independent (ADR-012, ADR-013). `serialize_observations` sorts a copy and never mutates its input.

---

## 6. Timestamp Serialization

- **Write:** `observed_at.isoformat()` with default arguments. Microseconds appear when non-zero and are omitted when zero. A naive value has no offset suffix. An aware value carries its offset (`+00:00`, `-05:00`, and so on).
- **No normalization.** Never converted to UTC, never given a timezone, never truncated or rounded.
- **Read:** `datetime.fromisoformat(text)`, followed by a canonical-form check: `parsed.isoformat() == text`. A string that parses but is not in the form the writer produces (for example a `Z` suffix or a space separator) is rejected, so `serialize(load(file))` always reproduces the file byte for byte.
- **What "exact" means.** After a round trip:
  - the loaded value `==` the original;
  - `isoformat()` is identical;
  - `tzinfo is None` is preserved, in both directions;
  - `utcoffset()` is identical.
- **What is not preserved.** An aware value comes back with a fixed-offset `datetime.timezone`. A named zone object (`ZoneInfo("America/Chicago")`) and the `fold` attribute are not recorded. Neither is part of `isoformat()` or of `datetime` equality, and providers stamp naive `datetime.now()` today. This limit is stated in the module docstring.
- **`source_run`** is an opaque string, written and read verbatim. It is never parsed as a UUID, trimmed or case-folded.

---

## 7. Replay and Comparison (`python -m devtools replay-observations <run_dir>`)

### 7.1 Replay

`replay_observations(run_dir)`:
1. Reads `<run_dir>/observations.json` through `load_observations`.
2. Runs `IdentityResolver().resolve(observations)`.
3. Runs `RelationshipResolver().resolve(observations, identities)`. No cardinality policy is passed, so the module policy applies, exactly as in `Application.run()`.
4. Returns the observations, identities and relationships.

It never constructs a `Project`, never touches `ProjectSerializer`, and writes nothing.

### 7.2 Relationship comparison

The command reads `<run_dir>/relationships.csv` and compares it with rows derived from the replayed relationships.

| CSV column | Compared? | Replay value |
|---|---|---|
| Subject | Yes | `relationship.subject` |
| Category | Yes | `relationship.category` |
| Related Subject | Yes | `relationship.related_subject` |
| Corroboration State | Yes | `relationship.state.value` |
| Provenance | Yes | `provider/collection_method` tokens, deduplicated in the resolver's observation order, comma-joined |
| Subject Hostname, Related Subject Hostname | **No** | They come from `Device` data, which is not in the artifact. |

- **Order matters.** The comparison is over ordered rows. Both sides follow the resolver's `(subject, category, related_subject)` order.
- **Header check.** The CSV header must be the seven columns `RelationshipCsvExporter` writes today. A different header is an input error, not a mismatch.
- **Provenance tokens** are computed in `devtools/` by the same rule as `RelationshipCsvExporter._provenance_cell`. The exporter is not modified or imported privately. A parity test (Section 9.3) builds a synthetic project, runs the real exporter, and asserts the comparison reports MATCH, so the two cannot drift apart unnoticed.

### 7.3 Identities

The command prints the replayed identity count and its distribution by state, labeled **"not compared: a run directory holds no machine-readable identity artifact"**.

**Limitation (ruling 1).** Because the run directory has no machine-readable canonical identity artifact, the command does **not** prove exact production identity equality by comparison. A `MATCH` result is a statement about relationship rows only. Exact identity replay must be, and is, proven by tests (Section 9.3, tests 1–5). The command's docstring and the VER-029 report state this limitation.

What supports identity replay for a production run, short of comparison:
- tests prove `IdentityResolver().resolve(loaded) == project.canonical_identities` exactly, on synthetic sets covering every identity state (Section 9.3);
- the relationship resolver's endpoint gate depends on the identity subjects, so a missing or extra identity subject changes the compared relationship rows whenever it is an endpoint;
- the round-trip tests prove the loaded observations equal the run's observations, and the resolvers are deterministic functions of them.

### 7.4 Output and exit codes

```
========================================
NetworkMapper Observation Replay
========================================
Run directory          : <run_dir>
Format                 : networkmapper.retained-observations v1
Observations           : <n> (<i> identity, <r> relationship)
Canonical identities   : <n> (not compared: no machine-readable identity artifact)
  weak <a> / probable <b> / confirmed <c> / conflicting <d>
Canonical relationships: <n> replayed, <m> in relationships.csv
  weak <a> / confirmed <b> / conflicting <c>
Result                 : MATCH
========================================
```

On a mismatch, `Result` reads `MISMATCH`, followed by counts of rows missing from the replay, rows not in the CSV, and rows that differ, then at most the first 10 differing rows.

| Exit code | Meaning |
|---|---|
| 0 | Replay ran and the relationship rows match exactly. |
| 1 | Replay ran and the rows differ. Also the existing devtools usage error (wrong argument count). |
| 2 | The replay could not run: bad run directory, missing file, or a rejected artifact (Section 8). |

**Sanitization.** Mismatch rows print raw subjects. The output is local console output and falls under OPS-001 D4: it must not be pasted into committed material. The command's docstring and the VER report both say so.

**Read-only.** The command opens both files for reading only and creates, modifies and deletes nothing.

---

## 8. Failure Behavior and Error Messages

All loader failures raise `ObservationReplayFormatError`, a `ValueError` subclass. Nothing is ever skipped: the first invalid element fails the whole load and no partial list is returned. `<path>` is the file's path; `<i>` is the record's zero-based index in the file.

| Condition | Message |
|---|---|
| Not valid JSON | `<path>: not valid JSON: <decoder message>` |
| Top level is not an object | `<path>: expected a JSON object at the top level, found <type>` |
| `format` missing | `<path>: missing required key 'format'` |
| **Unknown format identifier** | `<path>: unknown format identifier '<value>'; expected 'networkmapper.retained-observations'` |
| `format_version` missing | `<path>: missing required key 'format_version'` |
| **Unsupported format version** | `<path>: unsupported format version <value>; this build reads version 1 only` |
| `observations` missing or not an array | `<path>: 'observations' must be a JSON array` |
| Unknown top-level key | `<path>: unknown top-level key '<key>'` |
| Record is not an object | `<path>: observation <i>: expected a JSON object, found <type>` |
| **Unknown observation type** | `<path>: observation <i>: unknown observation type '<value>'; expected 'identity' or 'relationship'` |
| Record `type` missing | `<path>: observation <i>: missing required key 'type'` |
| Record key missing | `<path>: observation <i>: missing required key '<key>'` |
| Record key unknown | `<path>: observation <i>: unknown key '<key>'` |
| Value is not a string | `<path>: observation <i>: '<key>' must be a string, found <type>` |
| Timestamp unparseable or non-canonical | `<path>: observation <i>: 'observed_at' is not a canonical ISO-8601 timestamp: '<value>'` |

**Check order:** `format`, then `format_version`, then top-level keys, then records in file order. A file from a different format is therefore reported as an unknown format, not as a pile of key errors.

**Messages name keys and positions, never observation values**, with two exceptions that are format metadata, not evidence: the offending format identifier, version or type string, and the offending timestamp string.

**Command-level failures** (exit code 2, printed as `Error: <message>`):

| Condition | Message |
|---|---|
| `<run_dir>` is not a directory | `run directory not found: <run_dir>` |
| `observations.json` absent | `no observations.json in <run_dir>; the run predates FEAT-OBSERVATION-JSON-EXPORT or the export failed` |
| `relationships.csv` absent | `no relationships.csv in <run_dir>; cannot compare replayed relationships` |
| `relationships.csv` header differs | `relationships.csv has an unexpected header; cannot compare` |
| Any `ObservationReplayFormatError` | The loader's message, unchanged. |

**Writer-side failure.** `serialize_observations` raises `TypeError` for a non-observation object or a non-string field (D6). In `Application.run()` this propagates like any other exporter error. No `try/except` is added around it: a run that cannot preserve its evidence must fail visibly.

---

## 9. Test Plan

All fixtures are synthetic: documentation address ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), invented MACs and placeholder hostnames (ARCH-028 §8). No golden file derived from a real run is committed.

### 9.1 `tests/test_observation_replay_format.py` (new)

**Round trip**
1. Mixed identity and relationship observations: `parse(serialize(obs))` equals `obs` as a multiset (`collections.Counter`).
2. Empty input produces a valid envelope and loads as an empty list.
3. **Duplicates preserved:** three identical observations in, three records out, three objects loaded.
4. **Unresolved endpoints preserved:** a relationship observation whose `related_subject` has no identity observation is in the file and in the loaded list.
5. Non-ASCII and awkward strings (`"sw-été"`, a string containing `"`, `\`, a newline, and an empty string) round-trip exactly.

**`observed_at`**
6. Naive with microseconds (`.123456`).
7. Naive with zero microseconds: no fractional part is written, and the loaded value is equal.
8. Aware UTC; aware with a negative offset; aware with a non-whole-hour offset (`+05:30`).
9. Naive stays naive and aware stays aware: assert `tzinfo is None` and `utcoffset()` on each.
10. A naive and an aware value with the same wall-clock time stay distinct after the round trip.

**`source_run`**
11. A `uuid4().hex` value, an empty string, and a value with surrounding whitespace and mixed case each round-trip exactly.

**Determinism**
12. 200 random shuffles of one mixed set, including duplicates and mixed naive and aware timestamps, all produce identical bytes.
13. `serialize(parse(serialize(obs)))` equals `serialize(obs)`.
14. The bytes end in exactly one `\n`, contain no `\r`, and are pure ASCII.
15. `serialize_observations` does not mutate or reorder its input list.

**Rejection** (each asserts `ObservationReplayFormatError` and the Section 8 message)
16. Unknown format identifier.
17. Missing `format`.
18. Unknown format version (`2`), and `0`.
19. Non-integer versions: `"1"`, `1.0`, `true`.
20. Unknown observation type, with valid records before and after it: the whole load fails.
21. Missing key, unknown key, non-string value, at record and provenance level.
22. Unknown top-level key.
23. Non-canonical timestamp (`Z` suffix) and unparseable timestamp.
24. Invalid JSON; top-level array.

**Writer strictness (D6)**
25. A non-observation object, a `None` field and an `int` field each raise `TypeError`.

**Import independence**
26. Importing `networkmapper.observations.replay_format` does not import `networkmapper.identity`, `networkmapper.relationships` or `networkmapper.project`.

### 9.2 `tests/test_observation_json_exporter.py` (new)

1. The exporter writes exactly `serialize_observations(project.observations)` to the given path.
2. Read-only: `project.observations`, `canonical_identities`, `canonical_relationships` and the device list are equal before and after, and the observation list holds the same objects in the same order.
3. The file contains no `canonical`, `devices` or `customer_name` key, and nothing from `RunMetadata`.
4. **Credentials never appear.** Using the stub-client pattern from `tests/test_relationship_cardinality_pipeline.py`: build `SnmpCredentials` with a distinctive sentinel community; drive `SnmpEnrichmentProvider`, `SnmpArpNeighborProvider`, `SnmpLldpNeighborProvider` and `SnmpBridgeFdbProvider` through `collect_observations()`; resolve; export. Assert the sentinel is absent from the file's bytes, and that the file contains none of the strings `community` or `***`.
5. **`ProjectSerializer` unaffected:** saving a `Project` that carries observations produces a file byte-identical to saving the same project without them (complements the existing `test_observations_do_not_survive_a_save_and_load_round_trip`).

### 9.3 `tests/test_devtools_replay_observations.py` (new)

Each test builds a run directory in a `TemporaryDirectory` using the real `ObservationJsonExporter` and `RelationshipCsvExporter`.

**Exact replay**
1. Identity-only set: replayed identities `==` `project.canonical_identities`.
2. Mixed set covering WEAK and CONFIRMED edges, fan-out, a self-loop, an unresolved endpoint and duplicates: replayed identities and relationships `==` the run's tuples exactly.
3. Identity states WEAK, PROBABLE, CONFIRMED and CONFLICTING all reproduce.
4. The observations were shuffled before export: replay is still exact.
5. End to end from providers: stub SNMP clients → providers → resolvers → export → replay → equal.

**Comparison**
6. An untouched run directory reports MATCH, exit code 0. This is the parity test for provenance tokens (Section 7.2).
7. A CSV with one state changed, one row removed, one row added, and rows reordered each report MISMATCH, exit code 1, with the right counts.
8. Changed hostname columns still report MATCH.
9. A run with no relationships (header-only CSV) reports MATCH.

**Command**
10. `main(["replay-observations", run_dir])` returns 0 and prints the Section 7.4 report.
11. Missing directory, missing `observations.json`, missing `relationships.csv`, bad CSV header: exit code 2 and the Section 8 message.
12. Unknown format, version and type in the artifact: exit code 2 and the loader's message.
13. `main(["replay-observations"])` and a call with two paths print usage and return 1.
14. Read-only: every file's bytes and the directory listing are identical before and after the command, for both a MATCH and a MISMATCH run.

### 9.4 Architectural guard test (D2)

In `tests/test_observation_replay_format.py`: walk every `.py` file under `networkmapper/`, excluding the format module (`observations/replay_format.py`) and the exporter module (`exporters/observation_json_exporter.py`), and assert none imports or uses replay loading (`load_observations`, `parse_observations`). The exporter is exempt because it is the format module's one sanctioned production client; it needs only `serialize_observations`.

The test proves that no production path references or invokes the loader. It does not, and cannot, prove the loader is unreachable: it remains an importable function. The test's docstring cites Amendment 1's Boundaries and states that a failure means a normal workflow has started reading the artifact.

### 9.5 Updates to existing tests

| File | Change |
|---|---|
| `tests/test_report_run.py` | `test_markdown_and_csv_paths_live_inside_the_run_directory` also asserts `observations_json_path == run_directory / "observations.json"`. |
| `tests/test_application_cli.py` | `_fake_report_run_paths()` gains the new field. `_run_application` patches `ObservationJsonExporter` and returns the mock. `test_report_artifacts_are_written_to_a_unique_run_directory` asserts one `export(ANY, str(fake_paths.observations_json_path))` call and the `✓ Observations exported to` line. One new test asserts the observation exporter is called before `CsvExporter` (D8). |

`STANDARD_REGRESSION_TESTS` is not changed.

---

## 10. Validation Gate

1. `python -m pytest tests/ -q`: all 784 existing tests plus the new ones pass.
2. `python -m pytest tests/test_observation_replay_format.py tests/test_observation_json_exporter.py tests/test_devtools_replay_observations.py -q`: pass.
3. `python -m devtools validate --all`: PASS, all benchmarks at 100%. Benchmarks do not touch observations (ARCH-017); this confirms classification is unaffected.
4. `git diff --stat 84153e0 -- networkmapper/project networkmapper/discovery networkmapper/identity networkmapper/relationships networkmapper/classification networkmapper/observations/models.py networkmapper/observations/provenance.py`: empty.
5. `git status --short` shows nothing under `output/` staged or tracked, and no `observations.json` anywhere in the tree outside `output/`.
6. **Synthetic smoke test of the command.** A throwaway script builds a run directory in a temp folder from synthetic observations, then `python -m devtools replay-observations <that dir>` prints MATCH and exits 0. No live scan is part of this gate.
7. **VER report.** `docs/reports/VER-029-Observation-JSON-Export.md` is written as an independent verification, mapping each ARCH-028 §7 guarantee and each Amendment 1 decision to the test that proves it.

---

## 11. Risks and Non-Goals

### 11.1 Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **File size.** Large ARP and forwarding tables produce many records, and `indent=2` is verbose (about 12 lines per record). | The file is local and gitignored. Readability and diff-ability are worth more than size for a verification artifact. Measuring the real size is an OPS-001 reporting item. A compact form would be a new format version. |
| R2 | **The format becomes a contract.** | `format_version`, strict rejection (D4), and a single module owning both directions (D1). |
| R3 | **Scope creep toward persistence.** | The architectural guard test (D2), the `ProjectSerializer` byte-identity test, and replay living in `devtools/`. |
| R4 | **The new exporter can now fail a run.** A write error or a D6 `TypeError` aborts report generation. | Deliberate: a run that cannot preserve its evidence must not look successful. Providers emit only strings today. Running first (D8) means a failure costs no partially written reports. |
| R5 | **The command does not prove exact production identity equality by comparison**, because a run directory has no machine-readable canonical identity artifact. | Accepted (ruling 1). Stated in the command's output, its docstring, Section 7.3 and VER-029. Exact identity replay is proven by tests. |
| R6 | **Provenance-token logic exists in two places** (the CSV exporter and devtools). | The parity test (Section 9.3, test 6) fails if they diverge. |
| R7 | **Timezone object identity is not preserved** (named zone → fixed offset; `fold`). | Documented (Section 6). Equality, offset and ISO form are preserved, and that is everything the resolvers read. |
| R8 | **Mismatch output prints raw subjects.** | Local console only; D4 applies; documented in the command and the VER report. |
| R9 | **A stricter loader rejects a hand-edited file.** | Intended. The artifact is machine-written and is not meant to be edited. |
| R10 | **`tests/test_application_cli.py` writes to the real `output/` if the new exporter is not patched.** | Called out in Section 3 and done in the same step as the wiring (Section 12, step 4). |

### 11.2 Non-goals

- **No `.nmproj` schema change and no `ProjectSerializer` change.**
- **No loading observations into normal workflows:** not into `Project`, `Application.run()`, reports, `ProjectComparator`, the workbench or benchmarks.
- **No cross-run storage, merging or corroboration.**
- **No observation identifiers and no retention policy.**
- **No long-term evidence database or event store.**
- **No persisted canonical interpretations.** Identities and relationships are reproduced by replay, never written.
- **No behavior change** to providers, the observation model, either resolver, the cardinality policy, classification, `devices.csv`, `relationships.csv` or `report.md`.
- **No gateway inference and no topology behavior.**
- **No new scan CLI flag.** The artifact is written on every run.
- **No committed raw production artifact.** No real `observations.json`, and no fixture derived from one.
- **No migration or multi-version reader.** Version 1 is the only version.
- **No timestamp normalization** anywhere in the project.
- **No change to OPS-001's text** in this sprint (Section 13).

---

## 12. Implementation Order

The sprint lands as a **single commit**. Within it:

1. `networkmapper/observations/replay_format.py` with `tests/test_observation_replay_format.py` (Sections 4, 5, 6, 8, 9.1, 9.4).
2. `networkmapper/exporters/observation_json_exporter.py` with `tests/test_observation_json_exporter.py` (Section 9.2).
3. `ReportRunPaths.observations_json_path` with the `tests/test_report_run.py` update.
4. `application.py` wiring with the `tests/test_application_cli.py` update. Steps 3 and 4 go together: the new required field breaks `_fake_report_run_paths()` until the test is updated.
5. `devtools/replay_observations.py` and the `devtools/__main__.py` dispatch, with `tests/test_devtools_replay_observations.py` (Sections 7, 9.3).
6. The one-line documentation updates, if applicable (Section 3, file 7).
7. The full validation gate (Section 10).
8. In a **separate** commit, the VER-029 report.

**Open questions:** none. The three questions raised in the first draft (identity comparison, replay location, exporter order) are settled by the architect rulings in Section 2.1.

---

## 13. OPS-001

**OPS-001 remains blocked.** It may be unblocked only after both of the following are committed:
- FEAT-OBSERVATION-JSON-EXPORT, implemented to this plan once approved;
- its VER-029 verification report.

Afterwards, and as a separate change that is **not** part of this sprint, OPS-001 is revised and resubmitted for approval to run:
- Section 6, step 5: no export flag exists; the artifact is `output\<run>\observations.json`.
- Section 6, step 9: the replay command is `python -m devtools replay-observations "$($run.FullName)"`, expected to print `Result : MATCH` and exit 0.
- Section 7: the observation export's file name.
- Section 6, step 9, and Section 8, criterion 5 (ruling 1): reworded so they no longer require the command to reproduce canonical identities by comparison. The command confirms `relationships.csv` exactly and reports identity counts; exact identity replay is proven by the FEAT's tests, as recorded in VER-029.
- Section 13, item 1: marked resolved by ADR-011 Amendment 1.
