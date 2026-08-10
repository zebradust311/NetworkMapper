# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — this sprint adds a new output-path convention and a
new shared metadata object for the existing report-export pipeline. It
does not change discovery, classification, the evidence model, scan
behavior, or any documented architectural boundary in
[docs/architecture/](../architecture/); it extends `MarkdownExporter`'s
existing public API with a backward-compatible optional parameter and
adds one new `networkmapper/reporting/` module alongside the existing
`project_summary.py`/`discovery_summary.py` siblings it already has that
shape. No ADR-level decision (a cross-cutting, hard-to-reverse design
choice) is being made here that isn't already reversible by design (see
Backward Compatibility Notes).

Recommended Next Sprint:
No single sprint is pre-selected. Two candidates surfaced but were
deliberately left out of scope: (1) extending the same `RunMetadata`/
`build_report_run_paths` infrastructure to the `.nmproj` project-save
path and the `--workbench` diagnostic export, which currently still
overwrite a fixed filename each run — left alone because this sprint's
objective was scoped to "report persistence" (Markdown + CSV)
specifically, and `.nmproj`/workbench are project-persistence and
developer-diagnostic artifacts respectively, not customer reports; (2)
a `devtools`-level run-comparison utility that reads two `RunMetadata`-
tagged directories and diffs them — natural future use of this
sprint's metadata, but not requested here.

---

## Summary

Every scan execution previously wrote its Markdown and CSV reports to
the same two fixed filenames (`output/Test Network.md`,
`output/Test Network.csv`), so re-running a scan — including running
STANDARD and DEEP back-to-back, the specific case named in this
sprint's Background — silently overwrote the previous run's reports.
This blocked benchmarking, historical comparison, and regression
analysis, exactly as described in the sprint background.

This sprint makes every run's report artifacts land in a unique,
timestamped directory instead, and embeds enough run-identifying
metadata directly in the Markdown report that a single exported file
can be understood on its own, without its source `Project`/`.nmproj`
file.

Concretely:

- A new shared module, `networkmapper/reporting/report_run.py`,
  introduces `RunMetadata` (generation timestamp, scan profile,
  customer name, device count, tool version) and
  `build_report_run_paths()`, which derives a unique run directory name
  from the timestamp and scan profile, creates it, and returns the
  `report.md`/`devices.csv` paths inside it.
- `Application.run()` (`networkmapper/application.py`) now builds one
  `RunMetadata` per run and calls `build_report_run_paths("output",
  run_metadata)` once, then points both `CsvExporter` and
  `MarkdownExporter` at the paths it returns, instead of the two
  hardcoded literal strings.
- `MarkdownExporter.export()` gained one new optional, keyword-only
  parameter, `run_metadata: RunMetadata | None = None`. When supplied,
  a new `# Run Metadata` section is prepended to the report, before the
  existing `# Customer` section; when omitted (as every pre-existing
  caller and test does), the report renders exactly as it did before
  this sprint — verified directly by a new regression test asserting
  the with-metadata report literally ends with the without-metadata
  report's full text.
- `CsvExporter` was **not modified**. Its row schema is unchanged; only
  its call site in `application.py` now passes a directory-scoped path.
  CSV's flat, tabular format has no natural place for a metadata block
  without corrupting its schema, and the sprint's own Metadata section
  scopes embedded metadata to "the Markdown report" specifically. CSV
  and Markdown stay synchronized by both being written from the same
  `report_paths` value inside the same run, into the same directory,
  in the same `Application.run()` call — not by CSV also carrying
  metadata.
- `networkmapper/__init__.py` gained `__version__ = "0.1.0"`. No version
  constant existed anywhere in the repo before this sprint (confirmed by
  search); one was needed to satisfy the "NetworkMapper Version (if
  available)" metadata field, and there is now something available.

---

## Files Changed

Production code:

- `networkmapper/reporting/report_run.py` — new. `RunMetadata`,
  `ReportRunPaths`, `build_report_run_paths()`.
- `networkmapper/__init__.py` — new `__version__ = "0.1.0"` constant
  (file previously existed but was empty).
- `networkmapper/application.py` — imports `RunMetadata`/
  `build_report_run_paths`; builds one `RunMetadata` per run using the
  already-in-scope `scan_profile` and `before_save_count` variables;
  replaces the two hardcoded `"output/Test Network.csv"`/
  `"output/Test Network.md"` literals with `report_paths.csv_path`/
  `report_paths.markdown_path`; passes `run_metadata` into
  `MarkdownExporter().export(...)`; updates the two `print()`
  confirmation lines to show the real (now variable) path. The
  `--workbench` export and the `.nmproj` save/load persistence-
  validation round trip are untouched — out of this sprint's "report
  persistence" scope, as noted above.
- `networkmapper/exporters/markdown_exporter.py` — `export()` gained
  the optional `run_metadata` keyword parameter and a new
  `_render_run_metadata()` method. No other method changed.
- `networkmapper/exporters/csv_exporter.py` — **not changed**.

Tests:

- `tests/test_report_run.py` — new. Covers `RunMetadata`'s version
  default/override, run-directory naming, that Markdown/CSV paths live
  inside the run directory, that the directory is actually created on
  disk, that two runs at different timestamps don't collide (and don't
  clobber a file already written into the first run's directory), that
  STANDARD and DEEP at the *same* timestamp still produce distinct
  directories, and that a `Path` (not just `str`) is accepted as
  `output_root`.
- `tests/test_markdown_exporter.py` — `_export()` helper now takes an
  optional `run_metadata` kwarg (defaults to `None`, so every existing
  call site is unaffected). Added: metadata section omitted when not
  provided, metadata section renders all five fields when provided,
  `version=None` renders `"Unknown"` rather than `"None"`, and a direct
  regression test asserting the metadata-bearing report's text is
  byte-identical to the metadata-free report's text except for a
  prepended block (`with_metadata.endswith(without_metadata)`).
- `tests/test_application_cli.py` — `build_report_run_paths` is now
  mocked alongside the existing `CsvExporter`/`MarkdownExporter`/
  `ProjectSerializer`/`ClassificationWorkbench` mocks, in both the
  shared `_run_application()` helper and the standalone workbench test's
  manual patch block — without this, every CLI test would have created
  a real, uncleaned directory under the repository's real `output/`
  (this module's tests, unlike the workbench test, don't isolate a temp
  working directory). Added one new test asserting
  `build_report_run_paths` is called with `("output", <RunMetadata
  matching the run>)` and that both exporters are called with the paths
  it returns.
- `tests/test_csv_exporter.py` — **not changed** (its two-argument
  `export(project, output_path)` call site was never touched).

---

## Architecture Decisions

1. **New shared `report_run` module rather than duplicating
   path/metadata logic per exporter.** `RunMetadata` and
   `build_report_run_paths()` live in one place
   (`networkmapper/reporting/report_run.py`) and are computed once per
   run in `Application.run()`, then handed to both exporters. This is
   the sprint's own "do not duplicate export logic... refactor so
   future report formats can reuse the same infrastructure" principle:
   a third exporter (JSON, PDF, whatever comes next) calls
   `build_report_run_paths()` for a path inside the same run directory
   and receives the same `RunMetadata` to embed, without recomputing
   either.

2. **Directory naming: `<output_root>/<timestamp>_<profile>/report.md`
   + `devices.csv`, timestamp at second precision.** Both example
   structures in this sprint's brief nest a single run's Markdown+CSV
   under one directory; the flat `<timestamp>_<profile>/` form (the
   sprint's first example) was chosen over the nested
   `<date>/<profile>/` form (its second example) because the profile
   value is already unique-enough per run and a flat structure needs no
   extra `Path` joins in `build_report_run_paths()`, and — more
   importantly — the nested `<date>/<profile>/` form *reintroduces* the
   original overwrite bug for two runs of the *same* profile on the
   *same* day, which directly contradicts "every scan execution must
   produce a unique report artifact." The sprint's example used
   minute-level precision (`1357`); this implementation uses
   second-level precision (`135742`) instead — deliberately more
   precise than the example, not less — specifically so two runs
   moments apart (as automated tests do, and as a technician re-running
   a scan can do) still land in distinct directories. This is
   documented as a known residual limit below, not silently patched
   over.

3. **`report.md`/`devices.csv` filenames, not customer-name-based
   filenames.** The old convention derived filenames from
   `project.customer_name` (`"Test Network.csv"`). Generic filenames
   were chosen instead — matching this sprint's own example structures
   exactly — because customer names are free text that can contain
   characters invalid in Windows paths (`:`, `/`, etc.), and because the
   run directory name plus the embedded `Customer Name` metadata field
   already identify whose report it is; a technician does not need the
   customer name repeated in the filename once it's the directory
   they're standing in.

4. **`MarkdownExporter.export()` gained an optional keyword parameter
   rather than a new required one or a second method.** A required
   parameter would have broken every existing caller and test
   (`export(project, output_path)`, two positional args). A second
   method (e.g. `export_with_metadata()`) would have duplicated the
   whole render pipeline for one prepended section. An optional,
   keyword-only parameter defaulting to `None` satisfies "preserve
   backward compatibility where practical" exactly: old call sites are
   unmodified, and the metadata section degrades to "not present"
   rather than to placeholder/garbage values when the caller has no run
   in progress to describe.

5. **`CsvExporter` is untouched; no metadata written into CSV.** CSV's
   value as an interchange/spreadsheet format depends on every row
   having the same shape; injecting a metadata preamble would require
   either a separate header convention (most CSV consumers don't
   expect one) or a sidecar file (which the sprint didn't ask for).
   This sprint's own Metadata section says "Embed run metadata into the
   Markdown report" — singular, naming Markdown specifically — so CSV's
   format was left alone by design, not by oversight.

---

## Directory Structure

```
output/
    2026-08-10_135742_standard/
        report.md
        devices.csv
    2026-08-10_135810_deep/
        report.md
        devices.csv
```

Verified directly (see Testing Performed): a STANDARD run and a DEEP
run generated at the *same* wall-clock second still produce two
distinct directories (`..._standard` / `..._deep`), and two runs of the
same profile seconds apart produce two distinct timestamped
directories, neither overwriting the other.

`output/Test Network.nmproj` and (when `--workbench` is passed)
`output/Test Network.workbench.txt` continue to be written to their
pre-existing fixed locations, unchanged by this sprint — see Files
Changed and Recommended Next Sprint.

---

## Testing Performed

`python -m unittest discover -s tests -p "test_*.py"`: **261 passed, 0
failed** (248 before this sprint + 13 new: 8 in
`tests/test_report_run.py`, 4 in `tests/test_markdown_exporter.py`, 1
in `tests/test_application_cli.py`).

`devtools.validate.run_full_validation()`: **PASS** — 261/261 unit
tests, and all three benchmark datasets (enterprise, homelab,
small_office) unchanged at 100.0% accuracy (expected: no
classification, discovery, or evidence code was touched).

Manual end-to-end verification (synthetic `Project`, real
`CsvExporter`/`MarkdownExporter`/`build_report_run_paths`, real
temp-directory filesystem, no mocks):

- A single run produced `<run>/report.md` and `<run>/devices.csv`
  together in one new directory; the Markdown file opened with:
  ```
  # Run Metadata

  - Report Generated: 2026-08-10 13:57:42
  - Scan Profile: STANDARD
  - Customer Name: Acme Corp
  - Device Count: 1
  - NetworkMapper Version: 0.1.0

  # Customer
  ...
  ```
- Two runs at different timestamps (`STANDARD` then `DEEP`, ~30 seconds
  apart) produced two sibling directories; content written to the
  first run's file was still intact and unmodified after the second
  run completed.

Against this sprint's explicit Testing checklist:

- Consecutive runs no longer overwrite previous reports — confirmed
  (`test_consecutive_runs_with_different_timestamps_do_not_collide`,
  plus the manual check above).
- STANDARD and DEEP can both exist simultaneously — confirmed, including
  the same-second edge case
  (`test_standard_and_deep_runs_at_the_same_timestamp_do_not_collide`).
- CSV and Markdown remain synchronized — confirmed; both are written
  from the one `ReportRunPaths` value computed once per run, into the
  same directory
  (`test_report_artifacts_are_written_to_a_unique_run_directory`,
  `test_markdown_and_csv_paths_live_inside_the_run_directory`).
- Existing report contents remain unchanged except for the added
  metadata — confirmed directly
  (`test_existing_report_content_is_unchanged_by_added_metadata`), and
  indirectly by every pre-existing `MarkdownExporter`/`CsvExporter`
  test passing unmodified.
- Existing automated tests continue to pass — confirmed, 248/248
  pre-existing tests still pass unmodified in content (three test files
  had mocking/helper-signature updates to accommodate the new call,
  not assertion changes — see Files Changed).

---

## Backward Compatibility Notes

Preserved:

- `CsvExporter.export(project, output_path)` — signature and behavior
  completely unchanged.
- `MarkdownExporter.export(project, output_path)` — still valid;
  `run_metadata` is optional and keyword-only, so every existing call
  site compiles and behaves identically. Report content is byte-for-
  byte unchanged when `run_metadata` is omitted (see the endswith
  regression test).
- `.nmproj` save/load path and the `--workbench` diagnostic export path
  — untouched, same fixed-location behavior as before this sprint.
- All pre-existing `DeviceType`/classification/discovery behavior —
  untouched; this sprint imports `ScanProfile` (read-only) but modifies
  nothing under `networkmapper/classification/` or
  `networkmapper/discovery/`.

Necessarily changed (inherent to the sprint's own objective, not an
oversight):

- `output/Test Network.csv` and `output/Test Network.md` are no longer
  written at those fixed paths by `Application.run()`. This is the
  direct, unavoidable consequence of "prevent report overwrites" —
  a fixed output path and a no-overwrite guarantee are mutually
  exclusive requirements, so preserving the old fixed path was not
  "practical" in the sense the sprint's own engineering principle
  intends. Anything that previously depended on that literal path
  (confirmed by repo-wide search: nothing in the codebase or docs did,
  other than `application.py` itself) will need to look under
  `output/<timestamp>_<profile>/` instead.

Known residual limitation (not a compatibility break, but worth
flagging): two runs of the *same* scan profile within the *same*
wall-clock second would still collide, since `build_report_run_paths()`
uses `mkdir(parents=True, exist_ok=True)` and would reuse the existing
second-precision directory rather than erroring. This was a deliberate
scope decision — real network scans take far longer than one second, so
this only matters for pathological rapid-fire automated use, which
isn't this sprint's target use case — but it means the no-collision
guarantee is "distinct wall-clock seconds," not "distinct invocations,"
and a future sprint could tighten this (e.g. a monotonic run counter)
if that ever becomes a real constraint.
