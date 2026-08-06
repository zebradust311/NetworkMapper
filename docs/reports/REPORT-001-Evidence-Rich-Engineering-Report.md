# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — this sprint redesigns how already-collected evidence
is *rendered*. No field, model, discovery mechanism, or classification
rule changed.

Recommended Next Sprint:
No single sprint is pre-selected. TEST-003's remaining recommendations
not addressed by this sprint or STAB-001 — benchmark fixture coverage
for the five unbenchmarked classification-active fields, CSV field
expansion (this sprint deliberately touched Markdown only, per its own
"presentation" framing and the absence of any CSV-specific instruction),
`ClassificationWorkbench` mismatch-evidence coverage, and `NetworkGraph`
merge semantics — remain open.

---

## DESIGN-001 Reference Note

This sprint's objective is to "implement the engineering report redesign
described in DESIGN-001." No `DESIGN-001` report, commit, or design
document exists anywhere in this repository — verified by file search
and full git history search. Rather than block on a missing prerequisite,
this sprint's own "Design Principles" and "Report Structure" sections
are detailed and concrete enough to serve as the specification directly,
so implementation proceeded from them. Flagging this transparently
rather than silently assuming DESIGN-001 was implicit; if a separate
DESIGN-001 document exists outside this repository, this implementation
should be checked against it.

---

## Summary

Redesigned `MarkdownExporter` — the only report NetworkMapper generates
with room for hierarchical, per-device evidence (`CsvExporter`'s flat
row-per-device format was not touched; nothing in this sprint's
objective named CSV) — from a four-field device listing into an
evidence-rich engineering report answering, per device: what is this,
why was it classified this way, and what evidence supports that.

**Executive Summary** is unchanged in content and structure, per this
sprint's explicit "retain the existing summary section" instruction —
only extracted into its own render method for readability.

**Classification Overview** is new: total UNKNOWN device count, UNKNOWN
percentage of the project, UNKNOWN devices grouped by vendor, and
UNKNOWN devices grouped by observed `operating_system` (labeled "where
known" rather than claiming to "infer" anything not directly observed —
see Known Limitations for why). All four are arithmetic over data
already on `Device`; nothing is invented or newly discovered.

**Per-device Identity** now shows `Device Type`, `IP Address`,
`Hostname`, `Vendor`, `MAC Address`, and `Discovery Sources` always
(using the existing "Unknown" placeholder convention when absent), and
`Computer Name`/`Operating System`/`Domain` only when present — per the
"(if present)" qualifier attached to exactly those three fields in this
sprint's own field list, and to avoid three near-always-empty lines on
every non-Windows device.

**Per-device Evidence** groups all `ServiceEvidence` fields under each
service's own entry (`port/protocol/service (product version)`, with
`HTTP Title`/`TLS Subject`/`TLS Issuer`/`HTTP Authentication Realm` as
indented sub-bullets when present on that specific service), plus
device-level `SMB Signing` separately. This follows ADR-009's own
correlation model — these fields are properties of a specific port, not
the device as a whole, so grouping them by service (rather than as flat
top-level bullets) is both the more accurate representation and avoids
fragmenting one port's evidence across the section. A device with
neither services nor `smb_signing` shows "No additional evidence
collected." rather than an empty heading.

**Per-device Classification** shows `Final Device Type` always, then
branches: a classified (non-`UNKNOWN`) device shows only the single
rule that matched (`Matching Rule` + `Reason`) — `DeviceClassifier` is
first-match-wins, so there is exactly one such rule, and per this
sprint's "do not list every skipped rule" instruction, the rules
evaluated before it aren't shown. An `UNKNOWN` device shows every
evaluated rule's `reason` under "No rule matched. Evaluated rules:" —
since no rule matched, "why no rule matched" *is* that full breakdown,
per this sprint's "Unknown Devices" instruction to use existing
`RuleResult` information. Rule evidence is obtained by re-running
`DeviceClassifier` against a `replace()`d copy of the device — the same
pattern `ClassificationWorkbench` already uses, since `RuleResult`s
aren't persisted on `Device` and must be recomputed to be displayed.

**Appendices** are new: Vendor Counts (reuses `ProjectSummary.vendor_counts`,
already computed), Service Counts (aggregate `service` value counts
across all devices' `ServiceEvidence`), and Discovery Evidence Coverage
(a live, per-project version of TEST-003's static coverage matrix —
"N/total devices" or "N/total services" for each of the ten fields
added since FEAT-003D). All three are the specific examples this
sprint's own "Appendices" instruction named.

No discovery, evidence model, classification logic, benchmark inventory,
or ADR was touched. No confidence scores were introduced. No evidence
field beyond what already exists on `Device`/`ServiceEvidence`/
`RuleResult` appears anywhere in the new report.

## Files Changed

**Exporters**
- `networkmapper/exporters/markdown_exporter.py` — full redesign.
  Public API unchanged (`MarkdownExporter().export(project, output_path)`),
  so `networkmapper/application.py` required no changes. Retained
  helpers: `_group_devices_by_type`, `_render_section_manufacturers`,
  `_display_value`, `_display_title`, `_plural_title` (all unchanged).
  New: `_render_classification_overview`, `_render_device_section`,
  `_render_identity`, `_render_evidence`, `_format_service_summary`,
  `_format_service_detail`, `_render_classification`, `_evaluate_rules`,
  `_matching_rule`, `_render_appendices`.

**Not changed**
- `networkmapper/exporters/csv_exporter.py` — out of scope; this
  sprint's structure and examples are entirely Markdown-shaped
  (per-device evidence blocks, rule reasoning) and nothing in the
  objective named CSV.
- `networkmapper/reporting/project_summary.py` — Classification
  Overview and Appendix statistics are computed directly in
  `MarkdownExporter` rather than added to `ProjectSummary`, keeping the
  existing "Retain the existing summary section" data model untouched
  and the new computation scoped to where it's used.
- `networkmapper/classification/` — not touched. `MarkdownExporter`
  calls `DeviceClassifier.classify()`/`get_last_rule_results()`, both
  pre-existing public methods; no rule, ordering, or decision logic
  changed.
- `networkmapper/developer/classification_workbench.py` — not touched;
  this sprint's report and the workbench remain two separate tools with
  overlapping but not identical purposes (workbench: `UNKNOWN`-only,
  interactive developer debugging; this report: full-project, all
  devices, customer/engineer-facing document).
- Benchmark inventories, ADRs — untouched, per explicit constraint.

**Tests**
- `tests/test_markdown_exporter.py` — rewritten. Retains the original
  structural test (updated to also assert the two new top-level
  headings exist), adds: Classification Overview with and without
  UNKNOWN devices, Identity's conditional-field omission/inclusion,
  Evidence with full per-service detail and the empty-evidence case,
  Classification for both the classified-device and UNKNOWN-device
  branches, and both populated and empty Appendices. 10 tests total (up
  from 1).

## Example Report Sections

Generated from a synthetic four-device project (one SonicWall-pattern
firewall, one Hyper-V host, one Windows Server host, one fully-unknown
device) to demonstrate every new section in one place:

```
# Classification Overview

- Total UNKNOWN Devices: 1
- UNKNOWN Devices as % of Total: 25.0%

## UNKNOWN Devices by Vendor

- Generic Manufacturing Co: 1

## UNKNOWN Devices by Operating System (where known)

- Not Determined: 1
```

```
### tz-370

**Identity**

- Device Type: Firewall
- IP Address: 10.20.0.20
- Hostname: tz-370
- Vendor: Unknown
- MAC Address: Unknown
- Discovery Sources: Unknown

**Evidence**

Services:
- 443/tcp https
  - HTTP Title: SonicWALL - Network Security Appliance
  - TLS Subject: commonName=SonicWALL

**Classification**

Final Device Type: Firewall

Matching Rule: SonicWallFirewallRule
Reason: Detected HTTP title 'SonicWALL - Network Security Appliance' matched known firewall vendor identifier.
```

```
### mystery-box-01

**Identity**

- Device Type: Unknown
- IP Address: 10.20.0.99
- Hostname: mystery-box-01
- Vendor: Generic Manufacturing Co
- MAC Address: Unknown
- Discovery Sources: Unknown

**Evidence**

Services:
- 8080/tcp http

**Classification**

Final Device Type: Unknown

No rule matched. Evaluated rules:
- ServerHostnameRule: Hostname 'mystery-box-01' did not match known server naming patterns.
- HypervisorHostnameRule: Hostname 'mystery-box-01' did not match known hypervisor naming conventions.
- UbiquitiAccessPointRule: Vendor 'Generic Manufacturing Co' and hostname 'mystery-box-01' did not match known wireless infrastructure vendor patterns.
- SonicWallFirewallRule: Vendor 'Generic Manufacturing Co' is not a known firewall vendor.
- PrinterVendorRule: Vendor 'Generic Manufacturing Co' is not a known printer vendor and no printer networking protocols were detected.
- VoiceVendorRule: Vendor 'Generic Manufacturing Co' is not a known voice device vendor.
- CiscoSwitchRule: Vendor 'Generic Manufacturing Co' is not a known switch vendor.
- DellWorkstationRule: Vendor 'Generic Manufacturing Co' and hostname 'mystery-box-01' did not match known workstation indicators.
```

```
# Appendices

## Vendor Counts

- Generic Manufacturing Co: 1
- Unknown: 3

## Service Counts

- http: 1
- https: 1

## Discovery Evidence Coverage

- Operating System: 2/4 devices
- Computer Name: 2/4 devices
- Domain: 2/4 devices
- SMB Signing: 0/4 devices
- MAC Address: 0/4 devices
- Product: 0/2 services
- Version: 0/2 services
- HTTP Title: 1/2 services
- TLS Subject: 1/2 services
- TLS Issuer: 0/2 services
- HTTP Authentication Realm: 0/2 services
```

## Validation Performed

`python -m devtools validate --all`:

- Unit tests: **206 run, 0 failures, 0 errors** — clean, continuing
  from STAB-001's first fully clean run.
- Benchmarks: enterprise, homelab, small_office all 100.0% accuracy —
  unchanged, as expected (no classification or discovery logic changed).
- Fast-path test count pin required no update — `test_markdown_exporter`
  is not a member of `STANDARD_REGRESSION_TESTS`.

## Known Limitations

- **"UNKNOWN devices by inferred platform" is implemented as grouping
  by observed `operating_system`, not a genuinely inferred category.**
  This sprint's own constraints ("do not invent recommendations,"
  "summarize observable facts only," "do not invent new evidence")
  rule out fuzzy platform inference from hostname patterns or similar
  heuristics — `operating_system` is the only directly-observed,
  non-invented fact that plausibly maps to "platform." The section is
  labeled "by Operating System (where known)" rather than "by inferred
  platform" so the report doesn't overstate what it's actually showing.
- **Section ordering resolves an internal tension in this sprint's own
  spec.** The "Design Principles" list the four questions in the order
  identity → why-classified → evidence-supporting-that → next-steps,
  which would put Classification before Evidence. The "Report Structure"
  section explicitly lists per-device headings in the order Identity →
  Evidence → Classification. This implementation follows the literal,
  concrete Report Structure ordering (Evidence before Classification)
  rather than the more abstract Design Principles ordering, on the
  reasoning that a reader seeing the evidence first is better primed to
  understand the classification reasoning that follows it. If the
  reviewer intended the other order, swapping `_render_evidence` and
  `_render_classification`'s call order in `_render_device_section` is
  a one-line change.
- **The fourth Design Principle ("what should an engineer investigate
  next?") is answered only for `UNKNOWN` devices**, via their full
  rule-by-rule breakdown. Classified devices have no "next steps"
  section — there generally isn't a meaningful next step for a device
  the classifier is confident about, and inventing one would conflict
  with "do not invent recommendations."
- **Rule evidence requires re-running `DeviceClassifier` per device**
  at report-generation time (not cached anywhere on `Device`). For very
  large projects this is `O(devices × rules)` extra classification
  work beyond what discovery already did once. Not a concern at any
  scale this project currently targets, but worth noting if project
  sizes grow substantially — the same cost `ClassificationWorkbench`
  already pays per `UNKNOWN` device, now paid per device generally.
- CSV export was not extended — TEST-003's CSV field-expansion
  recommendation remains open and unaddressed by this sprint.

## Recommended Next Sprint

No single item is pre-selected. Open TEST-003/STAB-001 recommendations
not addressed here: CSV field expansion (if still wanted, now that
Markdown has a proven per-device evidence rendering pattern to mirror),
benchmark fixture coverage for `product`/`http_title`/`tls_subject`/
`tls_issuer`/`http_auth_realm`, `ClassificationWorkbench` coverage for
misclassified-but-not-`UNKNOWN` devices, and `NetworkGraph` merge
semantics (still correctly last — no observable effect until a second
`DiscoveryProvider` exists).
