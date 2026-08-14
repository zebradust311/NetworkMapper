# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — this sprint adds no new field, evidence source, or
report section shape. It surfaces four fields that already exist on
`Device` (populated by FEAT-005, already persisted in `.nmproj` per
`project/serializer.py`) using the same per-device Evidence-block
pattern `MarkdownExporter` already uses for SMB Signing, and appends
four columns to `CsvExporter`'s existing flat-row shape. Same shape of
change as REPORT-001/REPORT-002 (neither required an ADR).

Recommended Next Sprint:
No single sprint is pre-selected. Section 7 names two candidates: an
Appendices-level "SNMP Evidence Coverage" summary line (parallel to the
existing per-field coverage counts, deliberately not added here — see
Scope), and a `.nmproj`-round-trip regression test tying the
`ProjectSerializer` fields BENCH-003 confirmed are already persisted to
the exporter fields this sprint added, closing the loop BENCH-003
started end-to-end.

Wait for engineering review before committing.

---

## Summary

BENCH-003 found, by direct source inspection, that SNMP evidence
(`sysDescr`, `sysObjectID`, `sysUpTime`, `sysContact`, `sysLocation`) is
collected (FEAT-005), consumed by classification for `sysDescr`
specifically (RULE-004), and persisted in the `.nmproj` project file —
but referenced by zero lines in either `MarkdownExporter` or
`CsvExporter`. A technician handing a customer the Markdown report, or
opening the CSV in a spreadsheet, got none of it.

This sprint closes that gap for the four fields with direct technician/
customer value — `sysDescr`, `sysLocation`, `sysContact`, `sysUpTime` —
using user-facing labels ("SNMP Description", "SNMP Location", "SNMP
Contact", "SNMP Uptime") rather than the underlying field/OID names.
`sysObjectID` is deliberately excluded from both exporters, per this
sprint's explicit scope: it is canonical evidence intended for future
knowledge interpretation (KNOW-003's Observation → Knowledge → Rule
lifecycle, not yet reached for `sysObjectID` per BENCH-003's own Section
6), not customer presentation — a numeric OID string has no meaning to
a report reader without an interpretation layer that doesn't exist yet.

Both changes are additive and minimal: `CsvExporter` gains four columns
appended after the existing five (never inserted between them, so
column-position-dependent tooling is unaffected); `MarkdownExporter`
gains four conditionally-rendered lines inside the per-device Evidence
block it already renders, alongside SMB Signing — no new section, no
layout redesign, exactly where BENCH-003's own framing said this
evidence belongs ("alongside the device it describes").

---

## Files Changed

Production code:

- `networkmapper/exporters/csv_exporter.py` — four columns appended to
  the header row and every device row: `SNMP Description`, `SNMP
  Location`, `SNMP Contact`, `SNMP Uptime`, each blank (`""`) when the
  corresponding `Device` field is `None` — the same blank-when-missing
  convention `Hostname`/`Vendor` already use in this exporter.
- `networkmapper/exporters/markdown_exporter.py` — `_render_evidence`
  gained a call to a new helper, `_format_snmp_evidence`, which renders
  one line per populated SNMP field (`SNMP Description:`, `SNMP
  Location:`, `SNMP Contact:`, `SNMP Uptime:`), inserted after the
  existing `SMB Signing:` line and folded into the same `has_content`
  check that decides whether to print "No additional evidence
  collected." No new top-level section, no new subsection heading — the
  lines sit directly inside the existing `**Evidence**` block, the same
  device-level-fact placement `SMB Signing` already established.

Tests:

- `tests/test_csv_exporter.py` — the existing header/row assertions
  updated for the four new columns; two new tests: SNMP evidence
  present (asserts exact column values and that `sysObjectID` never
  appears anywhere in the output), and SNMP evidence partially present
  (asserts the three unset SNMP columns render as `""`, not `None` or
  an error).
- `tests/test_markdown_exporter.py` — three new tests: SNMP evidence
  present (asserts all four labeled lines render, `sysObjectID`'s raw
  value and field name never appear in the device's section), SNMP
  evidence partially present (only the populated field's line renders;
  the other three are absent, not blank), and a device with no SNMP
  evidence at all (its section is byte-identical in shape to before this
  sprint — still "No additional evidence collected.", no stray "SNMP"
  text anywhere in its section).

No change to `Device`, `ServiceEvidence`, discovery, enrichment,
classification, telemetry, the knowledge repository, or
`devtools/validate.py`'s `STANDARD_REGRESSION_TESTS` list (neither
exporter test module is in that fast-validation subset today, and this
sprint didn't add either to it — an existing, pre-dating-this-sprint
gap, not introduced here).

---

## Evidence Surfaced

| Device field | CSV column | Markdown label | Rendered when |
|---|---|---|---|
| `snmp_sys_descr` | SNMP Description | SNMP Description | Non-empty |
| `snmp_sys_location` | SNMP Location | SNMP Location | Non-empty |
| `snmp_sys_contact` | SNMP Contact | SNMP Contact | Non-empty |
| `snmp_sys_uptime` | SNMP Uptime | SNMP Uptime | Non-empty |
| `snmp_sys_object_id` | *(not exposed)* | *(not exposed)* | Never — explicit scope exclusion |

All four surfaced fields were already being collected and persisted
before this sprint; no discovery, enrichment, or classification code was
touched to produce them. This is a pure interpretation-to-presentation
change, the same category REPORT-001 established for the rest of the
Markdown report's Evidence block.

---

## Exporter Changes

**CSV — append, never interleave.** The four new columns were added
after `Discovery Sources`, not inserted between existing columns. This
was a deliberate choice, not an accident of implementation order: CSV
has no column names for a downstream consumer to key off unless it
parses the header row itself, and many simple CSV consumers (a fixed
`awk`/`cut` column-index script, a spreadsheet macro written against
column letters) key by position. Appending preserves every existing
column's index; inserting would silently shift every consumer keyed on
`Device Type`'s or `Discovery Sources`' position. Every row gets the
same four columns regardless of whether that device has any SNMP
evidence — blank cells, not omitted columns — because CSV is a
fixed-width tabular format; per this sprint's own instruction, empty
columns are acceptable here specifically because they're "required by
the existing exporter design" (every existing column already follows
this blank-when-missing convention; a variable-width row would break
every downstream CSV parser).

**Markdown — integrated, not standalone.** No new heading was added
anywhere in the document. The four fields render as plain lines inside
the per-device `**Evidence**` block that already exists for every
device, positioned after `SMB Signing:` (the closest existing precedent
— another device-level, protocol-sourced fact rendered as a flat
labeled line rather than a nested structure). A device with zero SNMP
evidence renders zero SNMP lines — confirmed directly, not assumed (see
Regression Tests) — so the change is invisible in every report that
predates SNMP enrichment or ran without `--snmp`.

**Label choice.** "SNMP Description"/"SNMP Location"/"SNMP Contact"/
"SNMP Uptime" were used verbatim as specified in this sprint's own
example ("SNMP Description" instead of `snmp_sys_descr`) — user-facing
labels, not field or OID names, consistent with every other label
`MarkdownExporter` already uses (`SMB Signing`, `HTTP Authentication
Realm`, `TLS Subject`) rather than their underlying source field names.

**`sysObjectID` exclusion, enforced not just omitted.** Both new test
suites include an explicit negative assertion that the raw OID value
never appears anywhere in either exporter's output for a device that
has it set — this is a regression guard against a future accidental
`assertIn`-style addition, not just an absence of code that would add
it today.

---

## Regression Tests

`python -m unittest discover -s tests -p "test_*.py"`: **384 passed, 0
failed** (379 before this sprint + 5 new: 2 in `test_csv_exporter.py`, 3
in `test_markdown_exporter.py`).

`devtools.validate.run_full_validation()`: **PASS** — 384/384 unit
tests, and all three benchmark datasets **unchanged at 100.0% accuracy**
(enterprise: 9/9, homelab: 5/5, small_office: 5/5) — none of their
fixture devices carry SNMP evidence, so the new columns/lines are blank/
absent for every benchmarked device, and classification/accuracy is
untouched (this sprint changed no code any benchmark accuracy check
reads).

Manual visual verification (not part of the automated suite, but
performed directly against real exporter output rather than assumed):
a two-device sample project (one switch with `sysDescr`/`sysObjectID`/
`sysUptime`/`sysLocation` populated and `sysContact` absent, one
workstation with no SNMP evidence at all) was exported through both
`CsvExporter` and `MarkdownExporter`. Confirmed directly:

- The switch's CSV row shows the three populated SNMP columns with
  correct values and a blank `SNMP Contact` cell; `sysObjectID`'s value
  appears nowhere in the file.
- The switch's Markdown section shows exactly three SNMP lines (no
  `SNMP Contact:` line at all — not a blank one), positioned
  immediately after its `Services:` list, inside the same `**Evidence**`
  block that already existed.
- The workstation's Markdown section is unchanged from its pre-sprint
  shape: `No additional evidence collected.`, no `SNMP` text anywhere.
- Report Generation itself and every other section (Customer, Executive
  Summary, Classification Overview, Appendices) are visually unaffected.

Every regression case the sprint's Testing section asked for has direct
coverage: existing reports remain readable (confirmed by the full
existing suite passing unmodified plus manual visual check), devices
without SNMP evidence are unchanged (dedicated tests in both exporter
suites), devices with SNMP evidence display only populated fields
(dedicated tests in both), CSV/Markdown exports contain the expected
values (dedicated tests in both), and the complete test suite passes.

---

## Backward Compatibility

**CSV**: existing columns (`IP Address`, `Hostname`, `Vendor`, `Device
Type`, `Discovery Sources`) are unchanged in name, order, and index.
Any consumer reading this CSV by column position for those five fields
continues to work unmodified. A consumer that reads by column *count*
(e.g., asserting exactly 5 columns) would need updating — this is the
one unavoidable compatibility cost of adding columns to a fixed-width
format at all, and is exactly the "where practical" qualifier in this
sprint's own instruction: full byte-for-byte row compatibility isn't
achievable while also adding requested columns, but positional
compatibility for every pre-existing column is, and was preserved.

**Markdown**: the Evidence block's existing content (Services, SMB
Signing) is unchanged in wording, order, or formatting for every device
that predates this sprint's fields. New lines are additive-only,
appearing only when the underlying `Device` field is populated — a
report generated from a project with no SNMP evidence (i.e., every
project generated before FEAT-005, or any run without `--snmp`) is
byte-for-byte identical to what `MarkdownExporter` would have produced
before this sprint. Confirmed directly by the "device without SNMP
evidence is unaffected" test rather than assumed from the conditional
logic alone.

**`.nmproj` / `ProjectSerializer`**: untouched. This sprint is exporter-
only; the canonical persisted-project format BENCH-003 confirmed already
carries this evidence is unaffected in either direction.

---

## Future Opportunities

Deliberately not implemented here, consistent with "do not redesign the
report layout beyond what is required":

1. **An Appendices-level SNMP evidence coverage summary**, parallel to
   the existing `Discovery Evidence Coverage` section's per-field counts
   (`Operating System: N/total devices`, etc.). This sprint's explicit
   scope was per-device presentation ("Surface existing SNMP evidence
   already stored on Device... Evidence should appear alongside the
   device it describes"), not an aggregate rollup — adding one here
   would be exactly the "large standalone SNMP section" this sprint was
   told to avoid, even at the smaller scale of one appendix subsection.
   A low-risk, evidence-backed follow-on once a real multi-device SNMP
   run exists to size it against.
2. **A `.nmproj`-round-trip regression test** connecting
   `ProjectSerializer`'s already-confirmed persistence of these five
   fields (BENCH-003, `project/serializer.py:32-36`) directly to this
   sprint's exporter output, in one end-to-end test — today the two are
   verified by separate test suites (`test_project_serializer.py` and
   this sprint's new exporter tests) that both pass independently but
   don't exercise the save → load → export path in one place. Not added
   here because this sprint's scope was the exporters themselves, not a
   new integration-test category.
3. **`sysObjectID` presentation remains an open, deliberately deferred
   question**, not a decision made here. This sprint excludes it from
   both exporters because it has no interpretation layer yet (BENCH-003
   Section 6, RULE-004's own scope boundary) — a numeric OID string
   alone has no reader-facing meaning. If a future, evidence-gated rule
   ever interprets `sysObjectID` into something reader-facing (e.g. a
   resolved vendor/product name), that interpreted *result* — not the
   raw OID — would be the natural candidate for report surfacing, not
   a reason to revisit this sprint's exclusion of the raw value.
