# Status

Implementation Complete

Production Code Modified: Yes

ADR Required: No — this sprint adds observability data derived entirely
from information already produced during discovery (scan arguments,
Nmap's own reported elapsed time, and evidence already stored on
`Device`/`ServiceEvidence`). No discovery behavior, Nmap argument,
classification rule, or evidence field changed.

Recommended Next Sprint:
No single sprint is pre-selected. DISC-001's remaining recommendations
not addressed here — a differentiated DEEP profile, UDP/protocol-surface
expansion, and an authenticated-discovery profile — remain open, each
requiring its own architecture review per DISC-001's Recommendations.

---

## Summary

OBS-001 implements DISC-001's top follow-on recommendation: run-level
diagnostics and evidence-coverage summaries so an engineer can see *why*
a scan produced the evidence it did without reading `NmapProvider`
source. Per DISC-001's own framing, missing evidence is overwhelmingly
operational (profile selection, port scope, target behavior) rather than
a parser/storage defect — this sprint makes those operational conditions
visible instead of changing them.

Three additions:

1. **Run diagnostics** (`RunDiagnostics`/`ScanPhase`, in the new
   `networkmapper/discovery/run_diagnostics.py`) — `NmapProvider` now
   records which Nmap phases it ran, their exact argument strings, and
   their elapsed time (read from Nmap's own `scanstats.elapsed`, no new
   timing code). Populated as `NmapProvider.run_diagnostics` after
   `discover()` returns; the `DiscoveryProvider`/`DiscoveryEngine`
   interfaces are unchanged.
2. **Per-host diagnostics** (`HostDiagnostics`, `diagnose_host()`) —
   computed inside `NmapProvider._discover_with_standard_enrichment()`
   while the SMB/RDP identity dicts still exist *before* their
   documented merge (ADR-established: SMB wins per field). This is what
   makes "hosts with SMB identity" vs. "hosts with RDP identity" possible
   to report at all — after the merge, RDP's contribution is
   indistinguishable from SMB's on `Device` alone. Reasons reported
   (`"SMB unreachable (port 445 not open)"`, `"No curated ports open"`,
   etc.) are limited to conditions directly observable in that host's own
   scan results — no inference about *why* a port was closed (firewall
   vs. absent service) is made, matching this sprint's "do not
   speculate" instruction.
3. **Discovery summary** (`DiscoverySummary`, in the new
   `networkmapper/reporting/discovery_summary.py`) — aggregates
   `HostDiagnostics` into the eight counters this sprint's Scope
   requested (hosts discovered/enriched, and per-evidence-type coverage).
   Built the same way `ProjectSummary` already summarizes classification
   data: a pure aggregation function, no estimation.

`Application.run()` prints all three via a new
`_print_discovery_diagnostics()` method, plus a profile-specific message
(`PROFILE_MESSAGES` in `run_diagnostics.py`) stating plainly what each
profile does — including DEEP's message stating it currently behaves
identically to FAST, rather than implying differentiated behavior that
doesn't exist yet (DISC-001 Finding 2).

Per-host diagnostics are printed only for hosts where enrichment
produced *no* evidence at all (`HostDiagnostics.enriched is False`), not
for every host — printing all six reasons for every host regardless of
device type (e.g. "SMB unreachable" on a printer) was judged too noisy
to be useful; the full reason set is still computed and available on
`RunDiagnostics.host_diagnostics` for any host, exercised directly in
tests.

## Files Changed

**New**
- `networkmapper/discovery/run_diagnostics.py` — `ScanPhase`,
  `HostDiagnostics`, `RunDiagnostics` dataclasses; `diagnose_host()`;
  `PROFILE_MESSAGES`/`profile_message()`.
- `networkmapper/reporting/discovery_summary.py` — `DiscoverySummary`
  dataclass and `from_run_diagnostics()`.

**Discovery**
- `networkmapper/discovery/nmap_provider.py` — `NmapProvider` gained a
  public `run_diagnostics: RunDiagnostics | None` attribute, populated
  by both `_discover_single_pass()` (FAST/DEEP) and
  `_discover_with_standard_enrichment()` (STANDARD). Added
  `_extract_elapsed_seconds()` reading `scan_result["nmap"]["scanstats"]["elapsed"]`.
  The STANDARD enrichment loop now iterates `devices_by_ip` directly
  (instead of `enriched_hosts`) so a `HostDiagnostics` entry exists for
  every discovered host, including ones absent from the enrichment scan
  result — behaviorally identical to before (a host missing from
  `enriched_hosts` still resolves to empty service/identity evidence via
  `host_data = {}`), verified by the unchanged existing tests. No Nmap
  argument string changed.

**Application**
- `networkmapper/application.py` — added `_print_discovery_diagnostics()`,
  called right after `engine.discover()`, before the existing
  classification summary output.

**Tests**
- `tests/test_run_diagnostics.py` — new: `profile_message()` coverage
  for all three profiles; `diagnose_host()` coverage for each reason
  (no curated ports, unnamed services, SMB/RDP unreachable, HTTP absent,
  TLS cert absent/present, plain-HTTP not flagged for TLS, SMB/RDP
  identity flags evaluated pre-merge).
- `tests/test_discovery_summary.py` — new: all-zero summary when
  enrichment never ran; counts correctly aggregated across multiple
  hosts.
- `tests/test_nmap_provider_run_diagnostics.py` — new: FAST/DEEP
  single-phase diagnostics, missing-scanstats fallback, STANDARD
  zero-host case (enrichment phase never invoked), STANDARD two-phase
  case with per-host diagnostics for both an enriched and a fully dark
  host.
- `tests/test_application_cli.py` — extended: shared `_run_application()`
  helper now injects a real `RunDiagnostics` (previously an unconfigured
  mock would have broken on iteration once diagnostics printing was
  added); new tests for FAST/DEEP profile messaging, STANDARD phase and
  summary rendering, per-host diagnostics section presence/absence, and
  the "unknown" elapsed-time fallback.

**Not changed**
- `networkmapper/core/models.py`, `networkmapper/classification/*`,
  `networkmapper/project/serializer.py`, exporters — no field, rule, or
  persisted-schema change, per this sprint's constraints.

## Example Console Output

STANDARD profile, two hosts discovered, one fully enriched, one dark:

```
Discovery Diagnostics
----------------------------------------
Scan Profile: STANDARD
Hosts Discovered: 2
Enrichment Enabled: Yes
Enrichment Arguments: -Pn -sV --version-light --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode -p 22,53,80,161,443,445,515,631,9100,3389,5060,5061,8080,8443,902,903

Phases Executed:
- Host Discovery (-sn) — 2.31s
- Service Enrichment (-Pn -sV --version-light --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode -p 22,53,80,161,443,445,515,631,9100,3389,5060,5061,8080,8443,902,903) — 11.02s

STANDARD profile:
Host discovery, then service enrichment on a curated port set.
Enrichment scripts: http-title, ssl-cert, vmware-version, http-auth, rdp-ntlm-info, smb-os-discovery, smb-security-mode.

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

FAST profile (default CLI behavior — DISC-001 Finding 1):

```
Discovery Diagnostics
----------------------------------------
Scan Profile: FAST
Hosts Discovered: 1
Enrichment Enabled: No

Phases Executed:
- Host Discovery (-sn) — 1.50s

FAST profile:
Host discovery only.
Service enrichment disabled by design.

Discovery Summary
----------------------------------------
Hosts Discovered            : 1
Hosts Enriched              : 0
Hosts with Service Evidence : 0
Hosts with SMB Identity     : 0
Hosts with RDP Identity     : 0
Hosts with HTTP Titles      : 0
Hosts with TLS Certificates : 0
Hosts with HTTP Auth Realms : 0
```

(No Per-Host Diagnostics section prints here — FAST never populates
`host_diagnostics`, since enrichment doesn't run.)

DEEP profile message, reflecting DISC-001 Finding 2 rather than implying
undelivered capability:

```
DEEP profile:
Currently identical to FAST (no differentiated DEEP behavior is
implemented yet).
Host discovery only. Service enrichment disabled by design.
```

## Validation Results

`python -m devtools validate --all`:

- Unit tests: 234 run, 0 failures, 0 errors (up from 206 pre-sprint —
  28 new tests added across the four new/extended test files above).
- Benchmarks: enterprise, homelab, small_office all 100.0% accuracy,
  unchanged (no classification or evidence-model change was made).

Manually exercised the full `Application.run()` STANDARD path with a
mocked `nmap.PortScanner.scan` (one enriched host, one dark host) to
confirm the console output above renders as designed end-to-end,
including the per-host diagnostics gating.

## Known Limitations

- **RDP/SMB identity attribution depends on diagnosing before the merge.**
  `Device.operating_system`/`computer_name`/`domain` remain a single
  SMB-preferred merge per ADR-established precedence (FEAT-003I); this
  sprint did not and could not change that (out of scope). "Hosts with
  RDP identity" is only knowable because `diagnose_host()` runs inside
  `NmapProvider` while the pre-merge dicts still exist. If SMB/RDP
  extraction is ever refactored so those dicts no longer exist at a
  single call site, this diagnostic will need to move with them.
- **TLS/HTTP heuristics are name-based, not port-based.** "HTTP service
  not present" and "TLS certificate not presented" are decided from
  Nmap's detected `service` name (contains `"http"`/`"https"`/`"ssl"`),
  not from a fixed port list — chosen because `http-title`/`ssl-cert`'s
  own Nmap portrules are service-name-driven, not fixed-port. A port
  Nmap fails to name at all (e.g. weak/absent banner on an HTTPS port)
  will report "HTTP service not present" even though the port is open;
  this is the same "no supported services identified" condition
  surfacing under a different reason, not a defect, but it means the two
  reasons aren't perfectly mutually exclusive across ports on the same
  host.
- **Per-host diagnostics are gated on full darkness, not partial gaps.**
  A host with an open HTTP port but no TLS cert on a *different* open
  HTTPS port doesn't get a console line, because that host's `enriched`
  flag is `True`. `RunDiagnostics.host_diagnostics[ip].missing_evidence_reasons`
  still has the full detail; only the default console rendering is
  narrowed. A future sprint could add a `--verbose` flag or a
  per-device Markdown section if partial-gap visibility is wanted
  without reopening the noise trade-off this sprint made.
- **Elapsed time depends on Nmap emitting `scanstats`.** Confirmed
  present in `python-nmap`'s own parsed output structure; if Nmap ever
  omits it (already handled — falls back to `None`/"unknown" rather than
  raising), phase timing simply won't display for that phase.
- Console-only. Per this sprint's Scope, the Markdown/CSV exporters
  were not touched; diagnostics exist only in the CLI run currently
  invoked by `Application.run()`, not in the persisted `.nmproj`/export
  artifacts.

## Recommended Next Sprint

No single sprint is pre-selected; the remaining DISC-001 recommendations
this sprint didn't address are, in DISC-001's own suggested order:

1. ARCH-00X — DEEP Profile Definition and Scope.
2. FEAT-00X — Implement DEEP per approved architecture.
3. FEAT-00X — Optional protocol-surface expansion (profile-gated).
4. FEAT-00X — Optional authenticated discovery profile (separate
   controls).

Additionally, if partial-gap per-host visibility (see Known Limitations)
turns out to matter operationally, a small follow-on could expose it
via an opt-in verbosity flag rather than changing the default output
this sprint calibrated.
