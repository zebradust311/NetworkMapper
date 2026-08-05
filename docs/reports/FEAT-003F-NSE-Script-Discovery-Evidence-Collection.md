# Status

Implementation Complete

Production Code Modified: Yes

ADR Required: No

Recommended Next Sprint:
FEAT-003G – SMB OS Discovery, per the roadmap FEAT-003E's Architecture
Review approved. Isolated into its own sprint because SMB probing has a
different operational profile (IDS/SOC visibility) than the three purely
passive candidates implemented here.

---

## Summary

Implemented the four Tier 1 candidates FEAT-003E recommended and the
Architecture Review scoped into FEAT-003F: HTTP title collection, TLS
certificate subject, TLS certificate issuer, and VMware version evidence.
All four reuse ports already in `CLASSIFICATION_PORTS` and data already
exchanged during the existing `-sV` probe or TLS handshake — no new scan
target, no `-sU`, no privilege escalation, no scan-profile change beyond
adding `--script http-title,ssl-cert,vmware-version` to the existing
STANDARD enrichment call.

`ServiceEvidence` gained three new optional fields (`http_title`,
`tls_subject`, `tls_issuer`); `version` gained a new producer
(`vmware-version`'s script output, preferred over `-sV`'s own guess when
both are present, since `vmware-version` queries the ESXi/vCenter API
directly). Three classification rules were extended with the new
evidence, following the reasoning FEAT-003E's Comparison Matrix and
candidate evaluations already established for each; two were deliberately
left unchanged, with the reasoning recorded below.

Full validation (`python -m devtools validate --all`) shows zero
regressions attributable to this sprint; the one error present is the
pre-existing, unrelated CSV exporter defect documented since TEST-001.
All three benchmark datasets remain at 100% accuracy — no fixture was
updated, because no existing fixture device's classification outcome
changed.

---

## Implementation

### Evidence Model

`ServiceEvidence` (`networkmapper/core/models.py`) gained three
`Optional[str]` fields: `http_title`, `tls_subject`, `tls_issuer` — the
same incremental, explicitly-named-field pattern every prior addition to
`Device`/`ServiceEvidence` has used (ADR-009's own recorded precedent).
No new ADR was needed, matching FEAT-003E's finding that this scope of
work "fits ADR-009's existing per-service evidence model... exactly as
ADR-009's Future Work anticipated."

### Discovery

`NmapProvider._standard_enrichment_arguments()` now adds
`--script http-title,ssl-cert,vmware-version` to the existing STANDARD
enrichment call. Nmap's own per-script `portrule` decides whether a given
script actually runs against a given port (e.g. `vmware-version` only
fires on ports `-sV` already identifies as VMware-related); no per-host
gating logic was needed on NetworkMapper's side.

`_extract_services()` now reads each port's `script` output dict (as
`python-nmap` parses it from Nmap's XML) and populates the new fields via
three small, focused parsing methods:

- `_clean_script_output()` — collapses multi-line NSE output into one
  string (used for `http-title` directly, and for `vmware-version`'s
  multi-line `"VMware ESXi\n6.7.0\nBuild 17167734"`-style output).
- `_extract_cert_field()` — a simple `"Label:"`-prefix line scanner
  against `ssl-cert`'s output, used for both `Subject:` and `Issuer:`.
- `_extract_version()` — prefers `vmware-version`'s script output over
  `-sV`'s own `version` guess when both are present, since
  `vmware-version` queries the ESXi/vCenter API directly rather than
  inferring version from a generic banner.

### Classification Rules — Where Extended, and Why

A new shared helper, `first_matching_identifier()`
(`evidence_helpers.py`), searches service product, HTTP title, TLS
certificate subject, and TLS certificate issuer, in that order, for the
first value containing a candidate keyword, returning a `(label, value)`
pair so reason text can name which evidence type actually matched instead
of assuming it came from one specific field. `first_matching_product()`
was refactored to delegate to a new, more general `first_containing()`
substring matcher it now shares with `first_matching_identifier()` —
functionally identical to its FEAT-003D behavior, confirmed by its
existing (unit-tested) call sites in `CiscoSwitchRule` continuing to pass
unchanged.

- **`SonicWallFirewallRule`** — new independent match tier (inserted
  between the vendor check and the existing hostname-plus-port/service
  fallback), matching `"sonicwall"` against product, HTTP title, TLS
  subject, or TLS issuer. Unlike the corroboration-only treatment given
  to Hypervisor/Cisco in FEAT-003D, this is a standalone trigger: a
  device's own served content naming its vendor (a login page titled
  "SonicWALL - Network Security Appliance," a self-signed certificate
  subject of "commonName=SonicWALL") is at least as strong an identifier
  as the MAC-OUI-derived vendor field, and does not depend on the
  hostname pattern the fallback branch requires. This mirrors the
  precedent FEAT-003D already established for `PrinterVendorRule`'s
  product-tier match.
- **`HypervisorHostnameRule`** — the existing `HYPERVISOR_PRODUCT_KEYWORDS`
  ("vmware") corroboration check was extended from product-only to also
  search HTTP title and TLS certificate subject, via
  `first_matching_identifier`. Kept as corroboration-only (appended to
  the reason text, never an independent trigger), unchanged from
  FEAT-003D's conservative treatment of this rule — the hostname-keyword
  gate remains the sole match condition.
- **`PrinterVendorRule`** — the existing product-tier match (FEAT-003D)
  was extended to also search HTTP title, reusing the same
  `SUPPORTED_PRINTER_VENDOR_KEYWORDS` list. Printer web management UIs
  commonly display the exact make/model in their page title, the same
  well-documented behavior that motivated the original product-string
  check.

**Deliberately left unchanged**, each for a specific reason recorded
directly in the affected rule or here:

- **`CiscoSwitchRule`** — not extended to HTTP title/TLS evidence.
  Unlike SonicWall or hypervisor management interfaces, a web-manageable
  interface is not a universal feature of Cisco switches (many are
  managed exclusively via SSH/CLI), so there is less confidence a
  reliably Cisco-branded title/certificate exists to match against.
  Left at its FEAT-003D scope (SSH banner product corroboration only).
- **`UbiquitiAccessPointRule`** — not extended. FEAT-003D already
  declined to add product-based evidence for this rule; this sprint
  reconfirms that decision for HTTP title/TLS evidence specifically,
  because Ubiquiti access points' web management behavior varies
  significantly once adopted into a UniFi controller (a common MSP
  deployment pattern per `docs/field-notes.md`'s own observations about
  these devices), making any assumed title/certificate content
  unverified and inconsistent with this sprint's "do not invent
  unsupported fingerprints" standard.
- **`ServerHostnameRule`, `DellWorkstationRule`, `VoiceVendorRule`** —
  unchanged from FEAT-003D's reasoning, which remains applicable: no
  natural product/vendor concept for generic hostname-only server
  matching, no realistic branded web service for general-purpose
  workstations, and no reliable phone vendor/model signal in default SIP
  service detection.

### Persistence and Benchmark Loading

`ProjectSerializer` and `BenchmarkRunner.load_inventory()` were both
updated to read/write the three new fields, following the exact pattern
established for `product`/`version` in FEAT-003C/FEAT-003D. No benchmark
fixture (`enterprise`, `homelab`, `small_office`) was modified — none of
the 17 existing benchmark devices populate the new fields, so no existing
classification outcome changes, and updating fixtures was explicitly
conditional on "behavior intentionally changes."

### Classification Workbench

`_format_service()` now appends `| title: '...'`, `| tls subject: '...'`,
and `| tls issuer: '...'` segments when present, so developer-facing
evidence output for UNKNOWN devices reflects the full evidence set a
device carries, not just port/service/product/version.

---

## Files Changed

**Production code**

- `networkmapper/core/models.py` — three new `ServiceEvidence` fields.
- `networkmapper/discovery/nmap_provider.py` — `--script` argument;
  `_extract_version`, `_clean_script_output`, `_extract_cert_field`.
- `networkmapper/classification/evidence_helpers.py` — new
  `first_containing()`, `service_http_titles()`, `service_tls_subjects()`,
  `service_tls_issuers()`, `first_matching_identifier()`;
  `first_matching_product()` refactored to share `first_containing()`
  (behavior unchanged).
- `networkmapper/classification/rules/sonicwall_firewall_rule.py` — new
  independent identifier match tier.
- `networkmapper/classification/rules/hypervisor_hostname_rule.py` —
  corroboration check extended to HTTP title/TLS subject.
- `networkmapper/classification/rules/printer_vendor_rule.py` —
  product-tier match extended to HTTP title.
- `networkmapper/project/serializer.py` — serialize/deserialize the three
  new fields.
- `networkmapper/developer/benchmark_runner.py` — load the three new
  fields from benchmark JSON.
- `networkmapper/developer/classification_workbench.py` — display the
  three new fields.

**Tests**

- `tests/test_nmap_provider_scan_profile.py` — updated the hardcoded
  STANDARD enrichment argument string (4 call sites) to include the new
  `--script` clause; 4 new tests covering HTTP title extraction, TLS
  subject/issuer extraction, `vmware-version` preferred over `-sV`'s
  guess, and fallback to `-sV`'s version when `vmware-version` is absent.
- `tests/test_classifier.py` — 10 new direct unit tests for
  `first_containing`, `first_matching_product` (now covered directly, not
  just indirectly via rule tests), and `first_matching_identifier`
  (product/HTTP-title/TLS-subject/TLS-issuer precedence, and the
  no-match case).
- `tests/test_sonicwall_firewall_rule.py` — 4 new tests: HTTP-title
  match, TLS-subject match, identifier match taking precedence over (and
  not requiring) the hostname/port fallback, and an unrelated title
  correctly not matching.
- `tests/test_hypervisor_hostname_rule.py` — 2 new tests: HTTP-title and
  TLS-subject corroboration.
- `tests/test_printer_vendor_rule.py` — 1 new test: HTTP-title-based
  printer match.
- `tests/test_project_serializer.py` — extended the existing round-trip
  test to cover the three new fields.
- `tests/test_benchmark_runner.py` — 1 new test covering
  `load_inventory()`'s handling of the three new fields.
- `tests/test_classification_workbench.py` — 1 new test covering the
  extended `_format_service()` display; the two FEAT-003C-era tests
  covering plain port/service and product/version display are
  unaffected (verified passing unchanged).
- `tests/test_devtools_validate.py` — updated the fast-validation
  test-count pin (`83` → `101`) to reflect the 18 new tests added to
  files already inside `STANDARD_REGRESSION_TESTS`. Same expected,
  verified maintenance as FEAT-003D's identical pin update — confirmed
  by checking that every modified test file
  (`test_classifier`, `test_hypervisor_hostname_rule`,
  `test_printer_vendor_rule`, `test_sonicwall_firewall_rule`) is already
  a member of that list.

**Not changed:** `docs/architecture/overview.md` and
`docs/architecture/classification.md`. Both already describe discovery
evidence as "correlated per-service evidence... per ADR-009" in general
terms; that description remains accurate without enumerating every field.
Updating them was not part of this sprint's explicitly stated scope
(HTTP title, TLS subject, TLS issuer, VMware version, wiring, rules,
tests, and conditional benchmarks only), so they were deliberately left
untouched rather than expanding scope beyond what was requested.

---

## Validation Performed

`python -m devtools validate --all`:

```
Unit Tests: 175 run, 0 failures, 1 error
Benchmarks: enterprise PASS (100.0%), homelab PASS (100.0%), small_office PASS (100.0%)
Overall Status: FAIL
Runtime: 0.53s
```

The single error is the same pre-existing, unrelated
`tests.test_csv_exporter.CsvExporterTest.test_export_writes_expected_csv_rows`
defect documented since TEST-001 and reconfirmed in FEAT-003C and
FEAT-003D (`AttributeError: 'str' object has no attribute 'name'` in
`csv_exporter.py`, untouched by this sprint).

One expected, non-regression change surfaced during validation and was
fixed within this sprint: `test_devtools_validate.py`'s hardcoded fast-
validation test count needed updating from `83` to `101` after this
sprint added 18 tests to already-fast-listed files — the same situation
FEAT-003D encountered and resolved identically, confirmed legitimate by
checking `STANDARD_REGRESSION_TESTS` membership before changing the pin.

All three benchmark datasets remain at 100% accuracy, unchanged from
before this sprint. No existing benchmark fixture device populates
`http_title`, `tls_subject`, or `tls_issuer`, so none of this sprint's
new evidence paths fire against existing benchmark data — expected, and
not itself validation that the new rules work correctly; that is
established by the new unit tests, which construct `ServiceEvidence`
entries with the new fields set directly.

## Known Issues

- **No benchmark case exercises the new evidence paths**, for the same
  reason noted in FEAT-003D: adding one was not required by this
  sprint's validation instructions ("Benchmark updates only if behavior
  intentionally changes"), and no existing fixture's outcome changed.
- **The `"hp"` keyword risk noted in FEAT-003D** (a short, two-character
  substring in `SUPPORTED_PRINTER_VENDOR_KEYWORDS`) now also applies to
  HTTP title matching, in addition to product matching. No new risk was
  introduced — the same keyword list is reused, not expanded — but the
  surface area it's checked against has grown by one more free-text
  field.
- **`ssl-cert` output format parsing (`_extract_cert_field`) has not been
  verified against a live Nmap scan.** Parsing is based on Nmap's
  documented `ssl-cert` script output format (`Subject:`/`Issuer:`
  line-prefixed fields); this sprint's tests exercise the parsing logic
  against representative sample output but, consistent with every prior
  sprint in this series, no live scan was run in this environment.

## Next Recommended Sprint

**FEAT-003G — SMB OS Discovery**, isolated into its own sprint per
FEAT-003E's Architecture Review, for the reason already recorded there:
SMB negotiation has a materially different operational profile from the
passive HTTP/TLS evidence implemented here (it can trigger IDS/SOC
monitoring), warranting its own documentation, validation, benchmarking,
and future configuration decisions rather than being bundled with this
sprint's risk-free scope.
