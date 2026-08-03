# Status

Implementation Complete

Production Code Modified: Yes

ADR Required: No

Recommended Next Sprint:
FEAT-003D – Classification Consumption of Service Product/Version Evidence

---

## Summary

Implemented ADR-009: `Device`'s two independent parallel lists,
`open_ports: list[int]` and `detected_services: list[str]`, are replaced
by a single correlated field, `services: list[ServiceEvidence]`, where
each `ServiceEvidence` entry names the port, protocol (`"tcp"`/`"udp"`),
and, when known, the service name, product, and version observed on that
specific port ([networkmapper/core/models.py](../../networkmapper/core/models.py)).
The old fields were removed outright rather than retained alongside the
new structure, per this sprint's instruction to avoid duplicate
representations.

`NmapProvider`'s two separate extraction methods
(`_extract_open_ports`, `_extract_detected_services`) were replaced with
one, `_extract_services()`, which builds one `ServiceEvidence` per open
port and — since STANDARD enrichment already runs `-sV` — also captures
the `product`/`version` strings Nmap already returns, which were
previously parsed and discarded (the specific gap FEAT-003A identified as
the cheapest available discovery win). No new Nmap arguments, ports, or
NSE scripts were added; this sprint changed representation and parsing
depth of an existing scan, not scan behavior. DEEP remains unchanged
(still equivalent to FAST) — redefining it was explicitly out of scope
for both FEAT-003A and ADR-009.

The five classification rules that read port/service evidence
(`CiscoSwitchRule`, `HypervisorHostnameRule`, `PrinterVendorRule`,
`SonicWallFirewallRule`, `VoiceVendorRule`) were migrated to the new
structure. Rather than changing the generic, independently-tested
`first_matching_port`/`first_matching_service` helpers to know about
`ServiceEvidence` — which would have coupled a reusable sequence-matching
utility to one specific model shape — two small extraction helpers,
`service_ports()` and `service_names()`, were added to
`evidence_helpers.py`. Each rule now does
`first_matching_port(service_ports(device.services), ...)` instead of
`first_matching_port(device.open_ports, ...)`. This kept the generic
helpers, and their existing direct unit tests in
`test_classifier.py::EvidenceHelpersTest`, completely unchanged.

`ProjectSerializer`, `BenchmarkRunner.load_inventory()`, and
`ClassificationWorkbench` were updated to read/write the new structure.
Serializing `services` also closes the persistence gap FEAT-003B
identified (`open_ports`/`detected_services` were never saved by
`ProjectSerializer` at all) — this fell naturally out of implementing
serialization for the field that replaced them, not a separate scope
addition. The two benchmark fixtures that used the old fields
(`enterprise`, `homelab`) were migrated to the `services` schema;
`small_office` was already unaffected.

## Files Changed

**Production code**

- `networkmapper/core/models.py` — added `ServiceEvidence`; replaced
  `Device.open_ports`/`Device.detected_services` with `Device.services`.
- `networkmapper/discovery/nmap_provider.py` — replaced
  `_extract_open_ports`/`_extract_detected_services` with
  `_extract_services()`; now also captures `product`/`version` from the
  existing `-sV` STANDARD enrichment scan.
- `networkmapper/classification/evidence_helpers.py` — added
  `service_ports()` and `service_names()`; `first_matching_port`/
  `first_matching_service` unchanged.
- `networkmapper/classification/rules/cisco_switch_rule.py`,
  `hypervisor_hostname_rule.py`, `printer_vendor_rule.py`,
  `sonicwall_firewall_rule.py`, `voice_vendor_rule.py` — migrated call
  sites to `service_ports(device.services)`/`service_names(device.services)`.
- `networkmapper/project/serializer.py` — `services` now serialized and
  deserialized (previously `open_ports`/`detected_services` were not
  persisted at all).
- `networkmapper/developer/benchmark_runner.py` —
  `load_inventory()` builds `ServiceEvidence` entries from the `services`
  key in benchmark JSON.
- `networkmapper/developer/classification_workbench.py` — replaced the
  separate "Open Ports:"/"Detected Services:" sections with one
  "Services:" section rendering each correlated entry
  (`port/protocol service (product version)`); removed the now-unused
  `_display_list()` helper.

**Fixtures**

- `benchmarks/enterprise/inventory.json`,
  `benchmarks/homelab/inventory.json` — migrated the three devices that
  used `open_ports`/`detected_services` to the `services` schema.
  `benchmarks/small_office/inventory.json` required no change (no
  port/service evidence).

**Tests**

- `tests/test_nmap_provider_scan_profile.py` — rewritten assertions
  against `device.services`; added a new test covering product/version
  capture from the existing `-sV` scan.
- `tests/test_cisco_switch_rule.py`, `test_hypervisor_hostname_rule.py`,
  `test_printer_vendor_rule.py`, `test_sonicwall_firewall_rule.py`,
  `test_voice_vendor_rule.py` — device fixtures migrated to
  `services=[ServiceEvidence(...)]`.
- `tests/test_benchmark_runner.py` — one test migrated to the `services`
  JSON schema.
- `tests/test_classification_workbench.py` — the two open-ports/detected-
  services rendering tests were replaced with three tests covering the
  new "Services:" section (empty, port-only, and name/product/version
  display).
- `tests/test_project_serializer.py` — **new file**. No serializer test
  existed before this sprint (a gap FEAT-003B flagged); added two tests
  covering save/load round-tripping of `services`, including
  product/version, since this sprint added the first real serialization
  logic for this evidence category.

**Documentation**

- `docs/architecture/overview.md`, `docs/architecture/classification.md`
  — updated the prose descriptions of discovery evidence fields from
  "open ports"/"detected services" to the correlated per-service model,
  citing ADR-009.
- `docs/ADR.md` — not modified, per this sprint's constraints.

## Validation Performed

`python -m devtools validate --all`:

```
Unit Tests: 143 run, 0 failures, 1 error
Benchmarks: enterprise PASS (100.0%), homelab PASS (100.0%), small_office PASS (100.0%)
Overall Status: FAIL
Runtime: 0.81s
```

The single error is
`tests.test_csv_exporter.CsvExporterTest.test_export_writes_expected_csv_rows`
(`AttributeError: 'str' object has no attribute 'name'` in
`csv_exporter.py`). This is **pre-existing and unrelated to this sprint**:
confirmed by stashing all of this sprint's changes and re-running the
same test in isolation against the unmodified `main` branch, which
produces the identical traceback. It is the same defect TEST-001
documented ("a genuine, currently-failing bug in `csv_exporter.py` ...
invisible to `validate`"); `csv_exporter.py` was not touched by this
sprint, and this test does not reference `open_ports`, `detected_services`,
or `services` in any form.

All other 142 tests pass, including the 20 new/migrated tests this sprint
added or changed and the pre-existing suite. All three benchmark datasets
classify at 100% accuracy, unchanged from before this sprint — the
representation change did not alter classification outcomes for any
curated benchmark case.

## Known Issues

- **`ServiceEvidence.product`/`.version` are captured but not yet
  consumed by any classification rule.** This sprint populates them from
  data `-sV` already returns (no new scan cost), but no rule reads them
  yet — only `.port` and `.service` are consumed today, via
  `service_ports()`/`service_names()`. This is a smaller-scale instance of
  exactly the pattern FEAT-003B warned against with `operating_system`
  (a field with a producer but no consumer), though it differs in one
  respect: `operating_system` has neither producer nor consumer, while
  `product`/`version` have a producer (this sprint) but not yet a
  consumer. Left as-is rather than addressed here, because writing
  classification-rule logic was outside this sprint's scope
  ("Implement ADR-009... do not revisit architectural decisions"), and
  because pre-existing evidence and FEAT-003A already reasoned about
  which existing rules a `product`/`version` corroboration would
  naturally strengthen. See Recommended Next Sprint.
- **`ServiceEvidence.protocol` will, in practice, almost always be
  `"tcp"` today.** FEAT-003A flagged, as an unverified inference, that
  STANDARD enrichment's arguments (`-Pn -sV --version-light -p <ports>`)
  omit `-sU`, so UDP-only services (e.g. SNMP on port 161) may not
  actually be reachable despite port 161 being in the scanned port list.
  This sprint's representation change does not fix or investigate that;
  it now makes the gap visible in collected evidence (a device's SNMP
  entry, if ever captured, would show `protocol: "tcp"`, which is a
  signal worth checking later) rather than resolving it.
- The pre-existing, unrelated `test_csv_exporter.py` failure documented
  above remains open; fixing it was not in scope for this sprint.

## Next Recommended Sprint

**FEAT-003D — Classification Consumption of Service Product/Version
Evidence.** This sprint captured `product`/`version` evidence at no
additional scan cost, but per the Known Issues above, it is not yet used
by any rule — exactly the dormant-field risk this whole investigation
chain (FEAT-003B, ARCH-002A, ADR-009) was built around avoiding. FEAT-003A
already identified which existing rules this would strengthen:
`SonicWallFirewallRule`, `HypervisorHostnameRule`, and `CiscoSwitchRule`
currently corroborate hostname matches with bare port/service presence;
product/version strings (e.g. a `vmware-hostd` product string
corroborating a hypervisor hostname match) would be strictly stronger
evidence for the same rules, without changing rule ordering,
`RuleResult`'s contract, or first-match-wins behavior (ADR-002/003
unaffected).

A secondary, independent option is the NSE-script evidence collection
(`http-title`, `ssl-cert`, `smb-os-discovery`) FEAT-003A originally
proposed and ADR-009 explicitly deferred as future work. It is not
blocked by anything in this sprint and could proceed before or alongside
FEAT-003D, but closing the loop on evidence already being collected
(product/version) is the more direct continuation of this sprint's own
work and carries no new scanning cost or risk to evaluate first.
