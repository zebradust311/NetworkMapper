# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — this sprint adds one more named field to
`ServiceEvidence`, the same incremental pattern ADR-009 established and
FEAT-003F already exercised for `http_title`, `tls_subject`, and
`tls_issuer`. No new evidence category or model is introduced.

Recommended Next Sprint:
FEAT-003H — SMB OS Discovery (+ SMB Security Mode, + the SMB2 dialect
field from `smb2-time`). See `ROADMAP.md` for the FEAT-003G/FEAT-003H
sprint-numbering note.

---

## Summary

Implements ARCH-003 Tier 1: HTTP Authentication Realm discovery. Adds a
new `http_auth_realm` field to `ServiceEvidence`, populated via a new
`http-auth` NSE script added to STANDARD-profile enrichment. The realm
string (e.g. `Basic realm=NETGEAR R7000`) is parsed from Nmap's
`http-auth` script output the same way `http-title`/`ssl-cert` were
parsed in FEAT-003F, and is wired into the shared `first_matching_identifier`
helper — the same multi-field identifier search already used by
`HypervisorHostnameRule`, `PrinterVendorRule`, and `SonicWallFirewallRule`
— so all three rules gained this evidence source with no rule-specific
code changes. `CiscoSwitchRule` and `UbiquitiAccessPointRule` were left
untouched, consistent with FEAT-003D/F's prior reasoning (a web UI with
Basic/Digest auth is not a universal signal for either device type, and
neither rule uses `first_matching_identifier`).

The change is purely additive: no existing scan target, port, or script
was removed or altered, and `http-auth`'s own portrule limits it to
ports already in `CLASSIFICATION_PORTS` that Nmap identifies as
HTTP/HTTPS, so no per-host gating logic was needed.

## Files Changed

**Model**
- `networkmapper/core/models.py` — added `ServiceEvidence.http_auth_realm`.

**Discovery**
- `networkmapper/discovery/nmap_provider.py` — added `http-auth` to
  `STANDARD_ENRICHMENT_SCRIPTS`; added `_extract_http_auth_realm()`
  (parses the `realm=` marker from raw script output, since http-auth's
  output isn't a fixed `Label: value` line like ssl-cert's); wired the
  new field into `_extract_services()`.

**Classification**
- `networkmapper/classification/evidence_helpers.py` — added
  `service_http_auth_realms()`; extended `first_matching_identifier()`
  to check HTTP auth realm as a fifth, lowest-priority evidence source
  (appended after TLS issuer, so no existing single-field match's
  reported label or precedence changes).
- No changes to any individual rule file — `HypervisorHostnameRule`,
  `PrinterVendorRule`, and `SonicWallFirewallRule` all call
  `first_matching_identifier()` already and picked up the new field
  automatically.

**Persistence**
- `networkmapper/project/serializer.py` — `http_auth_realm` added to
  both save and load paths.
- `networkmapper/developer/benchmark_runner.py` — `load_inventory()`
  reads `http_auth_realm` from fixture JSON.

**Developer tooling**
- `networkmapper/developer/classification_workbench.py` —
  `_format_service()` appends `| auth realm: '...'` when present.

**Documentation**
- `docs/architecture/overview.md`, `docs/architecture/classification.md`
  — updated the per-service evidence field list, which had gone stale
  after FEAT-003F (it still only mentioned port/protocol/service/product/
  version). Now reflects the full current field set including
  `http_auth_realm`.

**Tests**
- `tests/test_nmap_provider_scan_profile.py` — two new tests (realm
  extraction; quote-stripping for `Digest realm="..."` form); updated
  four existing tests' hardcoded `--script` argument string to include
  `http-auth`.
- `tests/test_sonicwall_firewall_rule.py`, `tests/test_printer_vendor_rule.py`,
  `tests/test_hypervisor_hostname_rule.py` — one new test each, covering
  the independent-match-tier case (SonicWall, Printer) and the
  corroboration case (Hypervisor).
- `tests/test_project_serializer.py` — round-trip test extended to
  include `http_auth_realm`.
- `tests/test_benchmark_runner.py` — new dedicated loader test.
- `tests/test_classification_workbench.py` — new display test.
- `tests/test_devtools_validate.py` — fast-path test count pin updated
  101 → 104 (three new tests added to files already in
  `STANDARD_REGRESSION_TESTS`: sonicwall, printer, hypervisor rule
  tests).

**Not changed**
- Benchmark fixtures (`benchmarks/*/inventory.json`) — no existing
  fixture device has HTTP auth realm evidence, so no accuracy behavior
  changed; per this sprint's own instruction, fixtures are only updated
  when behavior intentionally changes.
- `networkmapper/classification/rules/cisco_switch_rule.py`,
  `networkmapper/classification/rules/ubiquiti_access_point_rule.py` —
  deliberately not extended (see Summary).

## Validation Performed

`python -m devtools validate --all`:

- Unit tests: 182 run, 0 failures, 1 error.
- The 1 error is `tests.test_csv_exporter.CsvExporterTest.test_export_writes_expected_csv_rows`
  (`AttributeError: 'str' object has no attribute 'name'`) — confirmed
  pre-existing and unrelated by reproducing it against unmodified `HEAD`
  before this sprint's changes (same failure, same traceback). Not a
  regression introduced by this sprint.
- Benchmarks: enterprise, homelab, small_office all 100.0% accuracy —
  unchanged, as expected (no fixture changes).

## Known Issues

- The pre-existing `test_csv_exporter` failure (see above) remains
  unresolved and out of scope for this sprint, same as it was for
  FEAT-003F's cleanup commit.
- `first_matching_identifier()` now checks five fields; ARCH-003's
  Section 2 architectural note about this helper's growth as more
  evidence sources are added remains an open observation, not a
  blocker — no rule-level duplication has resulted from this addition.
- `smb2-time`'s dialect field (added to ARCH-003 as an addendum after
  this sprint's scope was fixed) is not part of this implementation;
  it belongs to the SMB-family sprint identified below.

## Next Recommended Sprint

FEAT-003H — SMB OS Discovery, SMB Security Mode, and the SMB2 dialect
field from `smb2-time` (ARCH-003 Tier 2, expanded by its SMB2 Time
addendum). See `ROADMAP.md` for the sprint-numbering note.
