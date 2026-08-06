# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — every change is a bug fix, a test addition, or a
docstring clarification within existing structure. No field, model, or
architectural boundary changed.

Recommended Next Sprint:
No single sprint is pre-selected. TEST-003's remaining recommendations
(CSV/Markdown field expansion, benchmark coverage for the five
unbenchmarked classification-active fields, workbench mismatch-evidence
coverage, `NetworkGraph` merge semantics) remain open, unordered by
priority beyond TEST-003's own Recommended Implementation Order.

---

## Summary

Implements the three low-risk items TEST-003 identified as safe to fix
immediately, ahead of REPORT-001 and further discovery work.

**1. CSV export — both bugs fixed.** TEST-003 found the long-standing
`test_csv_exporter` failure was two stacked defects, not one:
`tests/test_csv_exporter.py` constructed `Device(device_type="server")`
as a raw string (crashing `CsvExporter` on `.name`), and even if fixed,
the test's expected lowercase value (`"server"`) would still have
disagreed with what `.name` actually produces (`"SERVER"`). Fixed both:
the test now constructs proper `DeviceType.SERVER`/`DeviceType.UNKNOWN`
enum members, and `CsvExporter` now reads `.value` instead of `.name`
— matching `MarkdownExporter`'s existing `DeviceType` display
convention (`_display_title`, which is also `.value`-derived), so the
two exporters are now internally consistent with each other, not just
each individually self-consistent.

**2. Serializer coverage — `mac_address` round-trip added.** TEST-003
found `mac_address` is fully wired in both `ProjectSerializer` and
`BenchmarkRunner.load_inventory()` but had zero dedicated test coverage
in either `test_project_serializer.py` or `test_benchmark_runner.py` —
a real gap, since a future refactor could silently break the round-trip
with no test catching it. Added an assertion to one existing test in
each file rather than new test classes, keeping the change minimal.

**3. Evidence documentation — `ServiceEvidence.version` rationale
recorded.** TEST-003 noted `version`'s classification dormancy had been
flagged three times (FEAT-003F, ARCH-003, TEST-003 itself) without ever
being explicitly justified, unlike `smb_signing`'s docstring, which
states its future purpose. Added a docstring note explaining the
likely reason `version` was never consumed: unlike `product` (free
text, frequently containing vendor/model names), `version` is
typically a bare version number with no identifying signal — closer in
kind to `protocol` (already-documented diagnostic evidence) than to
`product`. No classification code was touched; this is a documentation-
only change, per this sprint's explicit "prefer documentation over
implementation" instruction.

No new evidence fields, no new classification rules, no discovery
changes, no report redesign, and no benchmark inventory changes — all
explicitly out of scope and untouched.

## Files Changed

**Exporters**
- `networkmapper/exporters/csv_exporter.py` — `device.device_type.name`
  → `device.device_type.value`, with a one-line comment recording why
  (matches `MarkdownExporter`'s convention).

**Model**
- `networkmapper/core/models.py` — `ServiceEvidence.version` docstring
  extended with the diagnostic-vs-classification rationale. No field,
  type, or default changed.

**Tests**
- `tests/test_csv_exporter.py` — `device_type="server"`/`"unknown"`
  (raw strings) → `DeviceType.SERVER`/`DeviceType.UNKNOWN` (proper enum
  members). Test assertions unchanged (still expect lowercase values,
  now correctly produced by `.value`).
- `tests/test_project_serializer.py` — added `mac_address` to the
  existing `test_save_and_load_round_trips_smb_identity_evidence`
  device construction, plus a round-trip assertion.
- `tests/test_benchmark_runner.py` — added `mac_address` to the
  existing `test_dataset_loading_populates_device_fields` fixture
  payload, plus a load assertion.

**Not changed**
- No benchmark inventory files (`benchmarks/*/inventory.json`) —
  constraint honored; the two test additions above use inline JSON
  fixtures constructed within the test files themselves, not the
  checked-in benchmark datasets.
- No classification rule files.
- No new `Device`/`ServiceEvidence` fields.
- `networkmapper/exporters/markdown_exporter.py` — not touched; TEST-003
  found no defect in it, only a field-coverage gap already tracked as a
  separate, larger recommendation (not in this sprint's scope).
- The orphaned `_stringify_value()` helper in `csv_exporter.py` (defined
  but never called) — noted during TEST-003's research but not named as
  one of the two defects in TEST-003's own findings section, so left
  untouched to keep this sprint's diff minimal and traceable strictly to
  what TEST-003 documented as a defect.

## Validation Performed

`python -m devtools validate --all`:

- Unit tests: **197 run, 0 failures, 0 errors** — first fully clean run
  this session. The previously pre-existing `test_csv_exporter` failure
  (flagged as unrelated in every FEAT-003F/G/H/I validation run) is
  resolved.
- Benchmarks: enterprise, homelab, small_office all 100.0% accuracy —
  unchanged, as expected (no benchmark inventory or classification
  logic changed).
- Fast-path test count pin (`tests/test_devtools_validate.py`) required
  no update — no new test functions were added, only assertions added
  to existing ones, and none of the touched files are members of
  `STANDARD_REGRESSION_TESTS`.

## Remaining Technical Debt

Everything TEST-003 identified beyond this sprint's three scoped items
remains open, unchanged by this sprint:

- CSV/Markdown reports still expose none of the ten evidence fields
  added since FEAT-003D (`operating_system` through `http_auth_realm`,
  plus per-service evidence generally).
- `product`, `http_title`, `tls_subject`, `tls_issuer`, and
  `http_auth_realm` remain classification-active but unexercised by any
  benchmark fixture.
- `ClassificationWorkbench` still only covers `UNKNOWN` devices, not
  misclassified-but-not-`UNKNOWN` ones.
- `NetworkGraph.add_device()` still silently drops duplicate-IP devices
  — dormant until a second `DiscoveryProvider` exists.
- The orphaned `_stringify_value()` helper in `csv_exporter.py` remains
  unused (see Files Changed — deliberately out of this sprint's scope).
- `computer_name`/`domain`'s classification-consumer question (raised
  in TEST-003's Classification Gaps as a plausible future feature, not
  a defect) remains open and unimplemented, per this sprint's "do not
  add new classification rules" constraint.

## Recommended Next Sprint

TEST-003's Recommended Implementation Order lists, in priority order
after this sprint's three items: benchmark fixture coverage for the
five unbenchmarked classification-active fields (recommendation 3),
then CSV/Markdown field expansion (recommendation 2), then
`ClassificationWorkbench` mismatch-evidence coverage (recommendation
4), then `NetworkGraph` merge semantics (recommendation 6, correctly
sequenced last). No specific choice among these is made here; the next
sprint's scope should be set explicitly, not inferred from this list.
