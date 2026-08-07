# Status

Implementation Complete

Production Code Modified: Yes

ADR Required: No — every change extends `NmapProvider`'s existing
two-phase shape (ADR-001) and incremental-field pattern (ADR-009);
matches ARCH-010's own "no new ADR required for v1 scope" conclusion.

Recommended Next Sprint:
No single sprint is pre-selected. ARCH-010's excluded-from-v1 items
remain open in their existing sequencing: a dedicated future
architecture effort on heuristic/confidence-scored evidence (OS
fingerprinting's eventual home), SNMP evidence collection as a
dependent follow-on once UDP reachability is separately addressed, and
LLDP/CDP's own architecture investigation. None are prerequisites for
this sprint's DEEP implementation.

---

## Summary

Implements DEEP per ARCH-010's approved architecture, as refined by its
architecture review (OS fingerprinting deferred out of DEEP entirely).
DEEP no longer behaves identically to FAST — it now performs the same
two-phase discovery STANDARD does (ADR-001, unchanged), with enrichment
extended along the axes ARCH-010 approved for v1: top-1000 TCP port
coverage, maximum version-detection intensity, one additional
`safe`-category NSE script (`sip-methods`, ARCH-010's approved pilot),
and increased retry/host-timeout patience.

**No parallel implementation was created.** `NmapProvider`'s two prior
enrichment paths — `_discover_with_standard_enrichment()` for STANDARD
and a single-pass `-sn`-only path for FAST/DEEP — are now one shared
method, `_discover_with_enrichment()`, used by both STANDARD and DEEP,
differing only in which argument string `_enrichment_arguments()`
dispatches to. All service/identity extraction, SMB/RDP merge logic, and
per-host diagnostics are the exact same code for both profiles; DEEP was
verified against STANDARD's own SMB-identity fixture to confirm
byte-for-byte identical extraction behavior (see Testing).

**Port coverage was verified, not assumed.** ARCH-010 recommended
nmap's own `--top-ports 1000` ranking specifically so DEEP wouldn't
require a bespoke port list. Before wiring it in, this sprint checked
directly against the Nmap installation's own `nmap-services` frequency
data whether STANDARD's full curated 16-port set — including the two
ports (902/903) FEAT-002B added specifically for their non-obvious
VMware relevance — falls inside Nmap's actual top 1000. It does, and so
do ARCH-010 Candidate 6's VMware CIM/WBEM ports (5988/5989), which
`--top-ports 1000` therefore already includes for free with no separate
port-list addition required. DEEP's port coverage is confirmed, not
assumed, to be a strict superset of STANDARD's.

**UDP/SNMP was not implemented**, consistent with this sprint's explicit
exclusion list and its own affirmative requirements list, which never
mentions UDP. ARCH-010 evaluated `-sU` solely as a prerequisite for a
future SNMP evidence sprint; implementing it here with no consumer and
no SNMP data collection would have repeated the exact "no identified
consumer" pattern this project has already rejected once (`smb2-time`,
FEAT-003H).

Observability (OBS-001) was extended with a new `RunDiagnostics.
expanded_capabilities: list[str]` field, populated only for DEEP, and a
new "Additional Capabilities Enabled" console section — giving each of
this sprint's four extension axes its own labeled, human-readable line
rather than leaving them only discoverable inside the raw argument
string.

## Files Changed

**Discovery**
- [networkmapper/discovery/nmap_provider.py](networkmapper/discovery/nmap_provider.py)
  — added `DEEP_ADDITIONAL_ENRICHMENT_SCRIPTS`, `DEEP_TOP_PORTS`,
  `DEEP_MAX_RETRIES`, `DEEP_HOST_TIMEOUT` constants; renamed
  `_discover_with_standard_enrichment()` → `_discover_with_enrichment()`
  and routed both STANDARD and DEEP through it (`discover()`'s dispatch
  condition now checks for either profile); added `_enrichment_arguments()`
  (profile dispatch), `_deep_enrichment_arguments()`, and
  `_expanded_capabilities()`; simplified `_discover_single_pass()` and
  removed the now-dead `_scan_arguments()`/`profile_arguments` dict
  (FAST is the only remaining single-pass profile, so the dispatch table
  it existed for no longer has more than one entry).
- [networkmapper/discovery/run_diagnostics.py](networkmapper/discovery/run_diagnostics.py)
  — added `RunDiagnostics.expanded_capabilities: list[str]`; rewrote
  `PROFILE_MESSAGES[ScanProfile.DEEP]` to describe DEEP's real behavior
  in place of the retired "currently identical to FAST" text.

**Application**
- [networkmapper/application.py](networkmapper/application.py) — added
  an "Additional Capabilities Enabled" section to
  `_print_discovery_diagnostics()`, printed only when
  `run_diagnostics.expanded_capabilities` is non-empty.

**Tests (new)**
- `tests/test_nmap_provider_deep_profile.py` — DEEP's two-phase shape,
  exact argument-string composition (script list, `--top-ports`,
  `--version-all`, `--max-retries`, `--host-timeout`), the zero-host
  skip case, `expanded_capabilities` population, and a direct
  side-by-side proof that DEEP's SMB-identity extraction matches
  STANDARD's own fixture exactly (no duplicated/diverged logic).

**Tests (extended)**
- `tests/test_nmap_provider_run_diagnostics.py` — replaced the now-false
  "DEEP records enrichment disabled, same as FAST" test with one
  asserting DEEP's real two-phase, enrichment-enabled behavior; added
  `expanded_capabilities == []` regression checks to the existing
  FAST/STANDARD tests.
- `tests/test_run_diagnostics.py` — replaced the "DEEP message states
  identical to FAST" test with one checking DEEP's new message content.
- `tests/test_application_cli.py` — replaced the equivalent CLI-level
  message test with one exercising a full DEEP `RunDiagnostics` fixture
  (two phases, populated `expanded_capabilities`) and asserting the new
  console section renders; added a FAST-side test confirming the
  "Additional Capabilities Enabled" section is correctly absent when
  there's nothing to report.

**Not changed**
- `networkmapper/core/models.py`, `networkmapper/classification/*`,
  `networkmapper/project/serializer.py`, exporters,
  `CLASSIFICATION_PORTS`, `STANDARD_ENRICHMENT_SCRIPTS`,
  `_standard_enrichment_arguments()` — STANDARD's own argument string,
  script list, and evidence model are byte-for-byte unchanged, per this
  sprint's "do not duplicate/do not modify STANDARD" constraint.

## Representative DEEP Command

Phase 2 (Service Enrichment), as actually issued to `nmap.PortScanner.scan()`:

```
-Pn -sV --version-all --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode,sip-methods --top-ports 1000 --max-retries 6 --host-timeout 15m
```

Phase 1 (Host Discovery) is unchanged from STANDARD: `-sn`.

Compared to STANDARD's phase 2
(`-Pn -sV --version-light --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode -p 22,53,80,161,443,445,515,631,9100,3389,5060,5061,8080,8443,902,903`),
DEEP: replaces `--version-light` with `--version-all`; replaces the
curated `-p` list with `--top-ports 1000`; appends `sip-methods` to the
script list; and adds `--max-retries 6 --host-timeout 15m`, which
STANDARD does not specify at all (relying on Nmap's built-in defaults).

## Example Console Output

DEEP profile, two hosts discovered, one with an HTTP service on a
non-curated port (8000) that only DEEP's expanded coverage reaches, one
fully dark:

```
Discovery Diagnostics
----------------------------------------
Scan Profile: DEEP
Hosts Discovered: 2
Enrichment Enabled: Yes
Enrichment Arguments: -Pn -sV --version-all --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode,sip-methods --top-ports 1000 --max-retries 6 --host-timeout 15m

Additional Capabilities Enabled:
- Expanded TCP port coverage: top 1000 ports (STANDARD scans a curated 16-port set).
- Version detection intensity: --version-all, maximum (STANDARD uses --version-light).
- Additional enrichment script: sip-methods (STANDARD's script set plus this).
- Retry/timeout patience: --max-retries 6 --host-timeout 15m (STANDARD uses Nmap's built-in defaults).

Phases Executed:
- Host Discovery (-sn) — 3.05s
- Service Enrichment (-Pn -sV --version-all --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode,sip-methods --top-ports 1000 --max-retries 6 --host-timeout 15m) — 48.63s

DEEP profile:
Host discovery, then expanded service enrichment: top 1000 TCP ports, maximum version-detection intensity, one additional safe NSE script (sip-methods), and increased retry/timeout patience.
Higher runtime and network visibility than STANDARD. Still unauthenticated — per ARCH-010, intended for a focused scope (a subnet, a device cluster), not a full enterprise sweep.

Discovery Summary
----------------------------------------
Hosts Discovered            : 2
Hosts Enriched              : 1
Hosts with Service Evidence : 1
Hosts with SMB Identity     : 0
Hosts with RDP Identity     : 0
Hosts with HTTP Titles      : 1
Hosts with TLS Certificates : 0
Hosts with HTTP Auth Realms : 0

Per-Host Diagnostics (no enrichment evidence collected)
----------------------------------------
172.16.100.11:
  - No curated ports open.
  - SMB unreachable (port 445 not open).
  - RDP unreachable (port 3389 not open).
  - HTTP service not present.
```

(Manually exercised end-to-end via `Application.run()` with a mocked
`nmap.PortScanner.scan`, not fabricated — this is the actual rendered
output.)

## Validation Results

`python -m devtools validate --all`:

- Unit tests: **240 run, 0 failures, 0 errors** (up from a 234-test
  baseline — 6 net new tests: 5 in the new DEEP-specific test file, plus
  1 verifying the "Additional Capabilities Enabled" section is absent
  for FAST; several existing tests were also rewritten in place to match
  DEEP's new real behavior rather than added alongside stale ones).
- Benchmarks: enterprise, homelab, small_office all 100.0% accuracy,
  unchanged — no classification rule or evidence field was touched.

Verified explicitly, per this sprint's Testing requirements:
- **FAST unchanged:** `_discover_single_pass()` still issues `-sn` only;
  all pre-existing FAST tests pass unmodified.
- **STANDARD unchanged:** `_standard_enrichment_arguments()` was not
  touched; every pre-existing test pinning STANDARD's exact argument
  string still passes unmodified.
- **DEEP inherits STANDARD correctly:** proven two ways — structurally,
  by both profiles now sharing one `_discover_with_enrichment()` method
  instead of DEEP having its own copy; and behaviorally, by feeding DEEP
  STANDARD's own SMB-identity test fixture and confirming an identical
  result (`test_deep_profile_merges_smb_identity_same_as_standard`).

## Known Limitations

- **Retry/timeout values are engineering judgment, not benchmarked.**
  `--max-retries 6` and `--host-timeout 15m` were chosen as reasonable,
  clearly-labeled explicit values — consistent with ARCH-010's own
  "qualitative, not measured" framing for timing tradeoffs — not derived
  from a specific benchmark against real network conditions. They are
  isolated constants (`DEEP_MAX_RETRIES`, `DEEP_HOST_TIMEOUT`) and easy
  to retune later without any architectural impact.
- **`sip-methods` remains an unverified pilot**, exactly as ARCH-010
  scoped it. This sprint wires it into DEEP's script list; it does not
  add any `VoiceVendorRule` matching logic against its output, since
  ARCH-010 explicitly recommended observing real response content first.
- **DEEP's actual runtime was not measured against a live network** —
  no live target was scanned as part of this sprint (only mocked
  `nmap.PortScanner.scan()` calls, per the existing test/demo
  convention). ARCH-010's own runtime-impact discussion was already
  qualitative for the same reason; this sprint doesn't change that.
- **UDP/SNMP, OS fingerprinting, LLDP/CDP, `ssh-hostkey`, and any
  intrusive/vuln-category script remain unimplemented**, exactly as this
  sprint's exclusion list specifies. This is a deliberate scope boundary,
  not an oversight — see ARCH-010 for the reasoning behind each.
- **`--top-ports 1000` vs. the curated list is a strict superset today**,
  verified directly against this environment's installed
  `nmap-services` file. This is Nmap's own frequency-ranked data and
  could, in principle, be revised in a future Nmap release; it isn't
  pinned or re-verified automatically by any test in this codebase.

## Recommended Next Sprint

No single sprint is pre-selected. ARCH-010's remaining items — a
dedicated future architecture effort on heuristic/confidence-scored
evidence (OS fingerprinting), SNMP evidence collection once UDP
reachability is separately addressed, and LLDP/CDP's own architecture
investigation — remain open in their existing sequencing, none blocking
or blocked by this sprint.
