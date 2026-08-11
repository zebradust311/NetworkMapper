# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — this is a measurement and analysis sprint. No
discovery, classification, or reporting behavior was changed; nothing
here constitutes an architectural decision by itself. Section 7
(Potential Optimization Opportunities) identifies candidates for future
architecture review, but does not decide any of them.

Recommended Next Sprint:
No single sprint is pre-selected. Two candidates surfaced with roughly
equal weight: (1) an authenticated/credentialed discovery path targeted
specifically at DEEP's escalation use case (see Section 7), since this
benchmark shows DEEP's current unauthenticated port-sweep approach has
a poor cost/benefit ratio; (2) a small, targeted classification-rule
addition for generic HTTP-manageable NAS/appliance devices (see Section
6), since this benchmark caught a concrete, reproducible case of that
gap. Neither was implemented here, per this sprint's explicit
constraints.

---

## Summary

This benchmark measured the operational cost and evidence/classification
yield of NetworkMapper's three discovery profiles — FAST, STANDARD, and
DEEP — using OBS-002's runtime telemetry, against two complementary
benchmark environments (see Methodology for why two, and what each one
can and cannot honestly measure).

Headline findings:

1. **STANDARD is the correct default.** It costs roughly 13–16× FAST's
   runtime (single-host, real-nmap measurement) but resolves a device
   type FAST structurally cannot (a switch identified only by open
   management ports), and drops the synthetic benchmark environment's
   UNKNOWN rate from 33.3% to 25.0%.
2. **DEEP shows genuine diminishing returns relative to STANDARD.** It
   costs roughly 4.9× STANDARD's Service Enrichment time (real,
   single-host measurement: 44.4s vs. 9.0s) for, in the synthetic
   12-device environment, one additional host with any evidence at all,
   one additional HTTP title — and **zero** additional resolved
   classifications. Every device STANDARD left UNKNOWN, DEEP also left
   UNKNOWN.
3. **Two concrete evidence types were directly observed being collected
   at real cost and then contributing nothing to classification**: HTTP
   Authentication Realm evidence for a non-printer/non-firewall
   appliance, and DEEP's expanded-port-coverage HTTP title for a generic
   internal web app. Both are documented in Section 6 with the exact
   device and reason.
4. **RDP-sourced OS evidence is collected correctly but, by an existing,
   deliberate design decision (FEAT-003I), never independently
   corroborates a SERVER classification** — its bare NTLM build number
   (e.g. `"10.0.14393"`) doesn't contain the `"server"` keyword text
   `ServerHostnameRule`'s corroboration check requires. This benchmark
   reproduced that behavior directly rather than just citing the code
   comment.

---

## Benchmark Methodology

**Two complementary benchmark environments were used, because neither
alone can honestly answer everything this sprint asks for.** No live,
diverse, multi-device network is available in this environment to scan
(this sandbox has no authorization or ability to reach an arbitrary
subnet), so a single approach would have forced a choice between real
timing data with no device diversity, or device diversity with no real
timing data. Using both, and being explicit about which section each
one feeds, avoids that tradeoff without fabricating either.

### Track A — Real single-host timing (localhost)

A real `nmap` binary (version 7.99, confirmed present in this
environment) was invoked through the actual, unmodified
`NmapProvider`/`DiscoveryEngine` pipeline against `127.0.0.1` — a safe,
self-owned, authorized target — for all three profiles, with no mocking
of any kind. `NmapProvider.run_diagnostics.phases[*].elapsed_seconds` is
Nmap's own self-reported elapsed time per phase, exactly as already
defined by `ScanPhase`'s existing docstring, not a value computed or
estimated by this benchmark.

A minimal local HTTP server was started on port 8080 (in STANDARD's
curated port set) immediately before the STANDARD/DEEP runs, serving a
page titled "Benchmark Test Device", so at least one real `http-title`
extraction could be observed end-to-end rather than relying entirely on
whatever happened to already be listening on the test machine.

This track is genuinely real measurement — real Nmap process execution,
real TCP handshakes, real NSE script execution — but scoped to **one
host**. It answers "how does each profile's actual argument set cost
scale against each other," not "how long would a real customer subnet
take." Absolute times will scale with host count and real network
latency/jitter that a loopback interface doesn't have; the *relative*
cost ratios between profiles are the load-bearing numbers here, not the
absolute seconds.

### Track B — Controlled synthetic multi-device fixture

To generate a realistic mix of device types and evidence — which one
localhost interface cannot provide — a fixed, hand-authored 12-device
scan-result fixture (modeled on a small-business network: a domain
controller, a core switch, a printer, a VoIP phone, a SonicWall
firewall, an ESXi host, a Ubiquiti access point, a Dell workstation, an
RDP-only application server, a vendor-ambiguous "mystery box," a NAS
appliance, and a generic internal web app) was fed through the real
`NmapProvider`/`DiscoveryEngine`/`DeviceClassifier`/OBS-002 telemetry
pipeline, with only `nmap.PortScanner.scan()` mocked to return that
fixed data — identical host-discovery data for all three profiles, and
identical enrichment data for STANDARD and DEEP **except** one
deliberate difference: DEEP's result additionally includes a service on
port 8090, which is outside STANDARD's curated 16-port list but within
DEEP's `--top-ports 1000`, modeling DEEP's actual, real port-coverage
advantage rather than inventing an arbitrary difference.

Everything downstream of that one mocked call is real: real
`_extract_services`/`_extract_smb_identity`/`_extract_rdp_identity`/
`diagnose_host` parsing, real `DeviceClassifier` rule evaluation, real
`DiscoverySummary`/`RuntimeTelemetryRecorder` aggregation. This track
answers "given the same set of hosts and services, what does each
profile actually see and classify" — it does **not** produce meaningful
wall-clock timing (the mocked call returns in microseconds), so its
`phase_durations` are reported only to show real, if tiny, CPU cost for
Classification (which scales with device count, not profile), not as a
network-cost comparison.

`Application Startup` and `Report Generation` were measured once (not
per profile) by running the full `Application.run()` pipeline against
the STANDARD synthetic fixture: **0.02s** and **~0.00s** respectively.
Both are pure CPU/local-disk work — argument parsing and writing two
small files — with no dependency on which discovery profile ran or how
many hosts were enriched beyond the trivial cost of writing more report
rows. They are not repeated per-profile because there is no reason to
expect, and this benchmark found no reason to expect, that they vary by
profile.

**A note on rigor**: an earlier draft of the Track B fixture used a
`json.dumps`/`json.loads` round-trip to derive DEEP's scan result from
STANDARD's. That silently rewrote an integer dictionary key (port
`3389`) to the string `"3389"`, which broke `_extract_rdp_identity`'s
int-keyed lookup and made DEEP appear to lose RDP evidence STANDARD had.
This was caught by inspecting the intermediate data rather than trusting
the first result, and fixed with `copy.deepcopy`. Flagging this
explicitly because it's exactly the kind of tooling artifact that could
otherwise be mistaken for a real product finding.

---

## Runtime Comparison

### Track A — real, single host (localhost), by phase

| Profile | Host Discovery | Service Enrichment | Total (wall) |
|---|---:|---:|---:|
| FAST | 0.57s | — (not run) | ~0.72s |
| STANDARD | 0.21s | 9.00s | ~9.4s |
| DEEP | 0.21s | 44.40s | ~44.8s |

Relative cost (real, single-host):

- STANDARD's Service Enrichment alone costs **~16×** FAST's entire
  runtime.
- DEEP costs **~4.9×** STANDARD's Service Enrichment time, and **~4.8×**
  STANDARD's total wall time.
- DEEP costs **~62×** FAST's total wall time.

Host Discovery itself is cheap and nearly identical across profiles
(0.21–0.57s) — it's a single `-sn` sweep regardless of profile; all of
the cost difference between profiles is in Service Enrichment, driven
directly by DEEP's `--top-ports 1000` (vs. STANDARD's curated 16 ports),
`--version-all` (vs. `--version-light`), one extra NSE script, and
`--max-retries 6 --host-timeout 15m` (vs. Nmap's defaults) — all
verified directly from `NmapProvider._deep_enrichment_arguments()`, not
inferred.

These ratios are for **one host on a zero-latency loopback interface**.
Real subnets add per-host network round-trip time and Nmap's own
internal parallelism/timeout behavior across many hosts, so absolute
numbers will differ on a real network — but the *relative* driver (port
count × version-intensity × script count × retry patience) is a fixed
property of each profile's argument set and will scale with host count
regardless of network conditions.

### Track B — synthetic 12-device fixture (CPU-only phases)

| Profile | Classification (12 devices) |
|---|---:|
| FAST | 0.22ms |
| STANDARD | 0.22ms |
| DEEP | 0.30ms |

Classification cost is negligible and scales with device count, not
scan profile — 12 devices classify in under a third of a millisecond
regardless of how much evidence each device carries. This confirms
Classification and Report Generation are not meaningful cost centers in
any profile; Service Enrichment is the only phase whose cost varies
significantly by profile choice.

---

## Evidence Comparison

Synthetic 12-device environment, identical input host set across all
three profiles:

| Metric | FAST | STANDARD | DEEP |
|---|---:|---:|---:|
| Hosts Discovered | 12 | 12 | 12 |
| Hosts Enriched | 0 | 8 (66.7%) | 9 (75.0%) |
| Hosts with HTTP Titles | 0 | 1 | 2 |
| Hosts with TLS Certificates | 0 | 1 | 1 |
| Hosts with SMB Identity | 0 | 1 | 1 |
| Hosts with RDP Identity | 0 | 1 | 1 |
| Hosts with HTTP Auth Realm | 0 | 1 | 1 |

FAST collects **zero** enrichment evidence by design (confirmed directly
by `PROFILE_MESSAGES[ScanProfile.FAST]`: "Service enrichment disabled by
design") — it only ever has hostname/vendor/MAC from the host-discovery
sweep itself, which is enough for vendor- and hostname-tier
classification rules but nothing evidence-tier.

DEEP's only evidence delta over STANDARD in this environment is **one**
additional enriched host and **one** additional HTTP title — both from
the single port-8090 service STANDARD's curated port list structurally
cannot see. Every other evidence category (TLS, SMB, RDP, HTTP auth) is
identical between STANDARD and DEEP, because every host that carries
that evidence in this environment exposes it on a port already in
STANDARD's curated set.

Track A (real localhost) independently confirms this port-coverage
story: DEEP found a real service on port 16992 (Intel AMT, with a real
extracted HTTP title) and port 135 (msrpc) that STANDARD's scan
structurally could not see, because neither port is in STANDARD's
curated list — that's DEEP's real, demonstrated value, not a synthetic
artifact.

---

## Classification Comparison

Synthetic 12-device environment:

| Device Type | FAST | STANDARD | DEEP |
|---|---:|---:|---:|
| SERVER | 2 | 2 | 2 |
| SWITCH | 0 | 1 | 1 |
| PRINTER | 1 | 1 | 1 |
| PHONE | 1 | 1 | 1 |
| FIREWALL | 1 | 1 | 1 |
| HYPERVISOR | 1 | 1 | 1 |
| ACCESS_POINT | 1 | 1 | 1 |
| WORKSTATION | 1 | 1 | 1 |
| **UNKNOWN** | **4 (33.3%)** | **3 (25.0%)** | **3 (25.0%)** |

**FAST → STANDARD: one device is reclassified** (`sw-core-01`, UNKNOWN →
SWITCH). This is a structural result, not a coincidence of the fixture:
`SwitchVendorRule`'s hostname-plus-management-port path (the only path
available for a switch with an unbranded/unknown vendor string) requires
open-port evidence that simply does not exist without Service
Enrichment — under FAST, `device.services` is always empty, so that
rule's port check can never match. Any device whose classification
depends on port/service evidence rather than vendor or hostname alone
will show the same FAST-blind-spot pattern.

**STANDARD → DEEP: zero devices are reclassified.** The three UNKNOWN
devices under STANDARD (`mystery-box-01`, `netgear-nas-01`,
`web-app-01`) are the *same* three UNKNOWN devices under DEEP, despite
DEEP collecting strictly more evidence for one of them
(`web-app-01`, via the port-8090 discovery). See Section 6 for exactly
why that extra evidence doesn't resolve the classification, and Section
7 for what would.

Track A (real localhost) reproduces the same "evidence collected but
UNKNOWN nonetheless" pattern for its one real host: SMB identity and an
HTTP title were both genuinely collected, but the host's hostname
(`"localhost"`) and vendor (unavailable — no ARP MAC-vendor lookup
across a loopback interface) never matched any rule, and the SMB OS
caption (Windows, no explicit "Server" edition) didn't independently
trigger `ServerHostnameRule`'s OS-corroboration path either (it's
corroboration-only, requiring a hostname match first — see
`ServerHostnameRule`'s own documented design in RULE-002). Real
evidence, real classifier code, still UNKNOWN — the same shape of result
the synthetic environment shows at a larger scale.

---

## Operational Recommendations

**Default technician profile: STANDARD.** It is the only profile that
resolves port/service-dependent device types (switches, in this
benchmark) without a wildly disproportionate cost — its real,
single-host Service Enrichment cost (~9s) is high relative to FAST but
low relative to DEEP (~4.9× less), and it captures every evidence
category this benchmark exercised (SMB, RDP, HTTP title, TLS, HTTP
auth) at that cost. This matches STANDARD's existing design intent
(ARCH-010's curated, production-scoped port/script set) — this
benchmark provides the first direct measurement confirming that intent
holds up in practice.

**Rapid inventory profile: FAST.** Real single-host measurement shows
it costs roughly 1/16th of STANDARD's enrichment time, with zero
enrichment evidence but full hostname/vendor-derived classification for
every device type whose classification rule doesn't depend on
port/service evidence — which, in this benchmark's realistic device mix,
was **7 of 8** non-UNKNOWN device types. Recommended specifically for
large-scale host census / "what's alive on this network right now"
sweeps where a technician needs a live-host count and rough inventory
fast, with the understanding that switches and similar port-identified
device types will show as UNKNOWN until a STANDARD pass follows.

**Escalation profile: DEEP.** Not a default-scale profile — this
benchmark's clearest finding is that DEEP's cost (~4.9× STANDARD) is not
matched by a proportional classification benefit (0 additional resolved
devices in the synthetic environment; 1 additional enriched host and 1
additional HTTP title, neither of which changed a classification
outcome). Recommended narrowly, exactly as `PROFILE_MESSAGES[ScanProfile.DEEP]`
already states in the product's own operator-facing text ("intended for
a focused scope — a subnet, a device cluster — not a full enterprise
sweep"): run it selectively against hosts a STANDARD pass left UNKNOWN
or under-evidenced, not as a blanket replacement for STANDARD.

**Profile showing diminishing returns: DEEP, relative to STANDARD**, as
detailed above and in Section 6. This is not a claim that DEEP has no
value — Track A's real port-16992/Intel-AMT discovery is genuine,
demonstrated value STANDARD structurally cannot provide — only that its
cost/benefit ratio is poor as a *default*, and good as a *targeted*
tool.

---

## Potential Optimization Opportunities

Identified, not implemented, per this sprint's explicit constraints.

1. **HTTP Authentication Realm evidence is collected but has no
   classification consumer today outside `PrinterVendorRule`/
   `SonicWallFirewallRule`'s identifier tiers.** This benchmark's
   `netgear-nas-01` device collected a real, well-formed HTTP auth realm
   ("NETGEAR ReadyNAS") at the same marginal cost as every other
   STANDARD-tier evidence field (it rides the same `http-auth` script
   already running against an already-scanned port — no separate
   cost), and it correctly identifies the device's vendor/product in the
   evidence itself, but no rule reads it for anything outside printer
   and firewall classification. A narrowly-scoped future rule (or an
   identifier-tier keyword expansion, following exactly the pattern
   RULE-002 established for `SwitchVendorRule`) recognizing common
   NAS/network-appliance vendor strings in HTTP auth realms and HTTP
   titles could plausibly resolve this specific, reproducible UNKNOWN
   pattern without any new evidence collection — a pure classification
   sprint, same shape as RULE-002.
2. **DEEP's cost driver is almost entirely `--top-ports 1000` combined
   with `--version-all` and the retry/timeout settings, not the extra
   NSE script.** This benchmark cannot isolate which of those three
   contributes the most to DEEP's ~4.9× cost multiplier over STANDARD
   without a controlled experiment varying them independently (out of
   this sprint's scope — see "Do not optimize code" and "Do not modify
   discovery behavior"). A future investigation could determine whether
   a narrower "DEEP-lite" (e.g., expanded ports at `--version-light`
   instead of `--version-all`) captures most of DEEP's real evidence
   advantage (this benchmark's Track A found real value specifically
   from *port coverage*, port 16992, not from version-detection
   intensity) at meaningfully lower cost — a genuine, evidence-backed
   optimization candidate, not a guess.
3. **An authenticated discovery path, scoped specifically to DEEP's
   escalation use case**, was already flagged as a future direction in
   DISC-001 and remains unimplemented. This benchmark adds a concrete
   data point for why it matters: DEEP's current unauthenticated
   approach pays a real, measured cost (~44s/host in Service Enrichment)
   for marginal evidence gain once a host has already been through
   STANDARD — an authenticated pass targeted at STANDARD's UNKNOWN
   residue could plausibly yield more classification value per second
   than DEEP's current blanket port/version expansion, though this
   benchmark did not (and could not, per its constraints) measure that
   directly.
