# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — the recommended sprint extends `NmapProvider`'s existing
STANDARD/DEEP enrichment pass (parsing already-returned data, adding
narrowly-targeted NSE scripts on ports already scanned). It changes no
provider contract, no two-phase discovery model (ADR-001), and no
discovery/interpretation boundary (ADR-008).

Recommended Next Sprint:
FEAT-003B — Service Version & Metadata Enrichment

---

# Executive Summary

NetworkMapper's discovery subsystem has exactly one concrete provider
(`NmapProvider`) behind the `DiscoveryProvider` abstraction, and that
provider currently uses a narrow slice of what Nmap itself already returns.
The most valuable near-term opportunity is not a new discovery source — it
is capturing evidence Nmap is **already collecting today** and currently
discarding, plus a small number of low-cost NSE scripts on ports the
STANDARD profile already scans.

Three findings drove this conclusion:

1. **`_extract_detected_services()` discards product, version, and CPE data
   that `-sV` already returns.** ([nmap_provider.py:174-187](../../networkmapper/discovery/nmap_provider.py#L174-L187)) Only the bare service `name` (e.g. `"http"`) is kept. Version strings (`"Apache httpd 2.4.41"`) that would materially strengthen classification confidence are thrown away for free, with zero additional scan cost.
2. **The DEEP scan profile is not implemented.** `_scan_arguments()` maps `ScanProfile.DEEP` to the identical `"-sn"` argument as `ScanProfile.FAST` ([nmap_provider.py:121-128](../../networkmapper/discovery/nmap_provider.py#L121-L128)), and no test exercises DEEP behavior distinctly from FAST. A user selecting DEEP today receives no additional evidence over FAST. This is a latent gap, not a design decision — ROADMAP.md and ADR.md are both silent on what DEEP should contain.
3. **The `operating_system` field is fully wired end-to-end (model, serializer, benchmark loader, classification workbench display) but is populated by nothing and read by nothing.** No discovery provider ever sets it; none of the 8 classification rules ever read it. It is dead evidence infrastructure — a cautionary precedent for adding new evidence fields without a corresponding consumer.

The recommended next sprint, **FEAT-003B — Service Version & Metadata
Enrichment**, is scoped to recover the discarded `-sV` version/product data
and add 2–3 targeted NSE scripts (`http-title`, `ssl-cert`,
`smb-os-discovery`) to ports already inside `CLASSIFICATION_PORTS`. It adds
no new scan targets, no new provider, no new ADR, and directly strengthens
the evidence behind rules that already exist (SonicWall, Ubiquiti,
VMware/hypervisor, switch). Higher-cost, higher-risk options — SNMP
enrichment, OS fingerprinting, LLDP/CDP, a redefined DEEP profile — are
real and roadmap-aligned, but each has a dependency or open scope question
that FEAT-003B does not, and each is addressed in Implementation Options
below with the specific reason it should wait.

No ADR change, architecture rework, or roadmap reordering is indicated by
this investigation. None of the report's Stop Conditions were triggered
(see Scope Recommendation).

---

# Current State

## Discovery Pipeline

The discovery subsystem has two layers, exactly as described in
[docs/architecture/overview.md](../architecture/overview.md):

- `DiscoveryProvider` ([provider.py](../../networkmapper/discovery/provider.py)) — a one-method abstract contract (`discover() -> list[Device]`).
- `DiscoveryEngine` ([discovery_engine.py](../../networkmapper/discovery/discovery_engine.py)) — iterates `Iterable[DiscoveryProvider]`, classifies each returned `Device` inline via `DeviceClassifier`, and inserts it into `NetworkGraph`.

Only one concrete provider exists: `NmapProvider`
([nmap_provider.py](../../networkmapper/discovery/nmap_provider.py)), wrapping
`python-nmap` (confirmed as the sole scanning dependency in
[docs/DEPENDENCIES.md](../DEPENDENCIES.md)). `DiscoveryEngine` already accepts
multiple providers by construction (`Iterable[DiscoveryProvider]`), so the
abstraction does not need to change to support future providers — it has
simply never been exercised with more than one.

## Scan Profiles

`ScanProfile` defines three values: `FAST`, `STANDARD`, `DEEP`
([scan_profile.py](../../networkmapper/discovery/scan_profile.py)). Their
actual behavior in `NmapProvider`:

| Profile | Arguments | Behavior |
|---|---|---|
| FAST | `-sn` | Single-pass host discovery only (ping sweep, ARP/PTR/MAC-vendor lookup). No ports, no services. |
| STANDARD | Phase 1: `-sn`; Phase 2: `-Pn -sV --version-light -p <16 ports>` | Two-phase, per ADR-001: host discovery establishes the authoritative device list, then a curated 16-port service-detection pass merges `open_ports`/`detected_services` onto existing devices by IP. |
| DEEP | `-sn` | **Identical to FAST.** No differentiated behavior exists. |

The STANDARD-profile port list, `CLASSIFICATION_PORTS`
([nmap_provider.py:17-34](../../networkmapper/discovery/nmap_provider.py#L17-L34)),
is intentionally curated to serve classification rules, not general
inventory — the code comment documents that ports 5988/5989 were evaluated
during FEAT-002B and deliberately excluded for insufficient classification
value relative to added scan surface. This is the same tradeoff logic this
report applies to new candidate evidence.

`_discover_with_standard_enrichment()`
([nmap_provider.py:73-107](../../networkmapper/discovery/nmap_provider.py#L73-L107))
implements ADR-001's two-phase model directly: phase-1 hosts are the
authoritative set; phase-2 results only ever enrich `open_ports` and
`detected_services` on IPs already present from phase 1, never add or
remove devices. This is confirmed by test coverage
([tests/test_nmap_provider_scan_profile.py](../../tests/test_nmap_provider_scan_profile.py)),
which explicitly asserts host counts are preserved when enrichment returns
partial data.

## Evidence Collected Today

Per-device fields a discovered `Device` can currently carry, and their
actual source:

| Field | Populated by | Notes |
|---|---|---|
| `ip_address` | All profiles | Always present. |
| `hostname` | All profiles (`-sn` reverse-DNS/NetBIOS via Nmap's own resolution) | First name in `hostnames[]`; no validation of source. |
| `mac_address` | All profiles, local subnet only | Nmap's own ARP resolution; only works for directly-attached L2 segments. |
| `vendor` | All profiles, local subnet only | MAC OUI lookup, same ARP dependency as above. |
| `open_ports` | STANDARD only | Limited to the 16-port `CLASSIFICATION_PORTS` list. |
| `detected_services` | STANDARD only | **Names only** — see Evidence Assessment. |
| `discovery_sources` | All profiles | Hardcoded to `["nmap"]`; the field exists to support multiple providers but currently only ever holds one value. |
| `operating_system` | **None** | Field exists on `Device` ([core/models.py:41](../../networkmapper/core/models.py#L41)) and is fully wired through serialization, benchmark loading, and the classification workbench display, but no provider ever sets it. |

## Classification's Dependence on Discovery

All 8 classification rules were read directly
([networkmapper/classification/rules/](../../networkmapper/classification/rules/)).
Every rule operates exclusively on `vendor`, `hostname`, `open_ports`, and
`detected_services`. None reads `operating_system`. None reads any
service-version or product string, because none currently exists on the
model. This is a direct, verified architectural fact, not an inference: the
classifier cannot use evidence the discovery layer never produces, and it
currently makes no use of the one enrichment field (`operating_system`)
that the model already reserves for it.

---

# Evidence Assessment

## Evidence Discarded Today

- **Service product/version/extrainfo/CPE strings.** `-sV` is already
  invoked in the STANDARD enrichment pass
  ([nmap_provider.py:130-133](../../networkmapper/discovery/nmap_provider.py#L130-L133)),
  and `python-nmap`'s per-port service dictionaries include `product`,
  `version`, `extrainfo`, and `cpe` alongside `name`. `_extract_detected_services()`
  reads only `name`
  ([nmap_provider.py:174-187](../../networkmapper/discovery/nmap_provider.py#L174-L187)).
  Everything else nmap returns from a scan NetworkMapper is *already
  running* is thrown away. This is the cheapest possible evidence gain in
  the entire assessment — it requires no additional scan, only additional
  parsing and a place on `Device` to keep it.
- **OS fingerprint.** The `operating_system` field is reserved but unused
  end-to-end, as detailed above.
- **Anything outside the 16-port `CLASSIFICATION_PORTS` list.** A device
  listening only on a port outside that list (e.g. a database on 3306, an
  application server on 8000) is invisible to STANDARD enrichment
  entirely — FAST-equivalent host presence only.

## Evidence Never Attempted

No discovery code anywhere references NSE scripts, `-O` (OS detection),
SNMP, LLDP/CDP, mDNS, SSDP, DNS zone enrichment, TLS certificate parsing,
or HTTP response metadata (confirmed via repository-wide search — the only
Nmap-related import is `import nmap` in `nmap_provider.py`, and the only
scanning dependency listed in `docs/DEPENDENCIES.md` is `python-nmap`).
IPv6 is not referenced anywhere in the codebase or documentation.

## An Inference Worth Flagging: SNMP Port 161 May Never Actually Be Reached

`CLASSIFICATION_PORTS` includes port 161 (SNMP), and
`_extract_open_ports()`/`_extract_detected_services()` both iterate over
`("tcp", "udp")` result keys, implying the code anticipates a UDP result.
But the STANDARD enrichment argument string
(`-Pn -sV --version-light -p <ports>`) never includes `-sU`. Per standard
Nmap argument semantics, a bare `-p <port>` without `-sU` is scanned as
**TCP only** — SNMP's actual UDP/161 service would not be probed, and the
`udp` branch of the extraction code would never populate in a real scan
against a typical SNMP agent (which does not also listen on TCP/161).

**This is an engineering inference, not a confirmed defect** — this
investigation did not execute a live scan against a real SNMP agent to
verify. It is flagged here because it directly bears on any future SNMP
enrichment work: the existing port list already signals SNMP intent, but
the current argument string cannot realize it. This is the kind of thing
FEAT-003B or a follow-on SNMP-enrichment sprint should confirm empirically
before relying on it.

## What Exporters Actually Surface

Neither exporter reads `open_ports`, `detected_services`, or
`operating_system` today:

- `CsvExporter` ([csv_exporter.py](../../networkmapper/exporters/csv_exporter.py)) writes IP, hostname, vendor, device type, discovery sources.
- `MarkdownExporter` ([markdown_exporter.py](../../networkmapper/exporters/markdown_exporter.py)) writes the same fields plus manufacturer-distribution summaries; no per-device ports/services/OS section exists.

This matters for prioritization: today, evidence collected by STANDARD
enrichment is consumed **only** by classification. It has no direct,
customer-visible documentation value yet. Any discovery enrichment work
increases classification confidence now; making it customer-visible would
require separate exporter work, which is out of this investigation's scope
(discovery only) and would be its own sprint.

## Benchmark Evidence

All three curated benchmark datasets pass at 100% accuracy on the evidence
discovery already collects:

| Dataset | Devices | Accuracy |
|---|---|---|
| homelab | 5 | 100.0% |
| enterprise | 7 | 100.0% |
| small_office | 5 | 100.0% |

Inspecting `benchmarks/enterprise/inventory.json` directly confirms none of
the 17 total benchmark devices across all three datasets use
`operating_system` — every one classifies correctly using only
vendor/hostname/ports/service-name evidence.

**This is an important, honest limitation on this report's own claims.**
There is currently no empirical (benchmark-driven) evidence that missing
discovery data is causing real misclassifications, because the benchmark
corpus's ground truth was authored to match what discovery already
collects. The case for richer discovery evidence in this report is an
**architectural inference** — evidence exists that Nmap already returns and
NetworkMapper discards, and evidence exists that a reserved model field has
no producer or consumer — not a measured accuracy problem. Where a claim
below is inference rather than observed fact, it is labeled as such.

---

# Gap Analysis

## Classification Bottlenecks Caused by Missing Discovery

- **No rule ever corroborates a match with a service version string**, because none exists. A hostname-based match (e.g. `HypervisorHostnameRule` matching `"esx"` in a hostname) currently has no way to be strengthened by, for example, an HTTP title of "VMware ESXi" or a TLS certificate CN — evidence Nmap could cheaply surface today.
- **`operating_system` is architecturally present but functionally inert.** Adding a discovery source for it without a consuming rule would repeat the same "collect it and let it sit idle" pattern already observed. Any future OS-fingerprinting discovery work should be paired with, or immediately followed by, a classification-consumption sprint — not shipped in isolation.
- **`DeviceType.ROUTER` has zero rule coverage.** All 8 rules were read directly; between them they produce SWITCH, WORKSTATION, HYPERVISOR, PRINTER, SERVER, FIREWALL, ACCESS_POINT, and PHONE — never ROUTER. This is a rule-authoring gap, not a discovery-evidence gap (the existing port/vendor evidence would likely support a router rule already), and is out of this investigation's discovery-only scope. Noted here because it is adjacent and easily mistaken for a discovery gap.

## Discovery Bottlenecks

- **STANDARD enrichment only reaches the curated 16-port list.** Anything outside it is invisible beyond bare host presence.
- **DEEP provides no capability beyond FAST.** Whatever a technician expects "deep" scanning to mean (broader port range, OS detection, script scanning) does not happen today.
- **Single source of discovery evidence.** `discovery_sources` always resolves to `["nmap"]`; the field's plural framing anticipates providers that do not yet exist.
- **No IPv6 path.** Not a currently-scoped product gap per README/ENGINEERING positioning (on-prem MSP subnet discovery), but worth naming as a known blind spot. Pursuing it would touch `NetworkGraph`'s device-identity model (devices are keyed by IP address; a dual-stack host would need reconciliation logic that does not exist today) — an architecture-level question, not a routine discovery addition.

---

# Opportunity Assessment

Each roadmap-listed and required-evaluation area, scored on Classification
improvement, Discovery improvement, Engineering complexity, Performance
cost, User-visible value (today, given exporters as they exist), and
Architectural impact.

| Opportunity | Classification Value | Discovery Value | Eng. Complexity | Performance Cost | User-Visible Value (today) | Architectural Impact |
|---|---|---|---|---|---|---|
| Recover `-sV` product/version/CPE (already scanned) | High | High | Low | None (no new scan) | Low (exporters don't show it yet) | None |
| Targeted NSE (`http-title`, `ssl-cert`, `smb-os-discovery`) on already-scanned ports | High | Medium-High | Low-Medium | Low (same ports, one script each) | Low (same reason) | None |
| Define & differentiate DEEP profile | Unknown until scoped | High | Medium | High (undefined until scoped) | Medium | Low, but scope is currently undefined |
| SNMP enrichment (sysDescr/sysObjectID) | High | High | Medium-High | High (UDP scanning; needs `-sU` fix noted above) | Low today | Possible new provider |
| OS fingerprinting (`-O`) | Medium (no consumer yet) | Medium | Medium | High | None until paired with a rule | None (field exists) |
| NetBIOS/SMB enrichment (beyond `smb-os-discovery`) | Medium | Medium | Medium | Low-Medium | Low | Possible new provider |
| LLDP/CDP discovery | High (topology) | High | High | Medium | None — no topology/edge model exists in NetworkGraph to consume it | New provider; premature relative to Phase 7 |
| mDNS/SSDP discovery | Low-Medium | Medium | Medium | Low | Low | New provider; weak fit for MSP/enterprise persona |
| DNS enrichment | Low-Medium | Medium | Medium-High | Low | Low | Authorization/scope concerns (zone access) |
| ARP enrichment beyond local subnet | Low | Low | Medium-High | Low | Low | Marginal — local-subnet ARP already works |
| Cloud-host detection | Low | Low | Medium | Low | Low | Weak fit — product model is on-prem subnet scanning |
| IPv6 | Low (no current demand signal) | Medium | High | Medium | Low | Touches `NetworkGraph` device-identity/dedup model |

---

# Implementation Options

## Option A — Service Version & Metadata Enrichment (Recommended)

Scope: parse the `product`/`version`/`extrainfo`/`cpe` fields Nmap's `-sV`
already returns during STANDARD/DEEP enrichment instead of discarding them;
add `http-title`, `ssl-cert`, and `smb-os-discovery` NSE scripts to the
existing enrichment argument string, targeting ports already inside
`CLASSIFICATION_PORTS` (80/443/8080/8443 for HTTP/TLS, 445 for SMB).

- No new scan targets, no new provider, no new ADR.
- Fits ADR-001 (stays inside the existing phase-2 enrichment pass) and
  ADR-008 (adds discovery facts; does not touch interpretation) without
  modification.
- Directly strengthens existing rules' evidentiary basis (SonicWall,
  Ubiquiti, VMware/hypervisor, switch rules currently rely on
  hostname/port heuristics that version/title/cert evidence would
  corroborate).
- Requires a Device-model decision (where richer per-service evidence
  lives) that the next sprint's own investigation phase should resolve,
  not this report — consistent with the constraint against introducing
  implementation details here.

## Option B — Define and Implement a Differentiated DEEP Profile

Real gap (DEEP currently no-ops as FAST), but its scope is genuinely
undefined: full port range? OS detection? NSE vulnerability scripts? None
of ROADMAP.md, ADR.md, or ENGINEERING.md specify what "deep" is supposed to
mean, and its performance cost is unbounded until that's decided. This
should be the investigation topic of a focused follow-on sprint, not
folded into Option A.

## Option C — SNMP Enrichment Provider

High classification value (sysObjectID can yield exact vendor/model for
network infrastructure) but meaningfully larger scope: likely a new
provider, UDP scanning (`-sU`, slower and lossier than TCP), community
string handling, and the port-161 TCP-vs-UDP scanning defect noted above
needs to be resolved as a prerequisite, not discovered mid-sprint. Roadmap-
aligned (Phase 6) but not the cheapest next step.

## Option D — OS Fingerprinting (`-O`)

Real evidence value in principle, but no classification rule reads
`operating_system` today. Shipping OS discovery without a paired
classification-consumption plan would recreate the exact "wired but
inert" problem already documented in this report. Also carries real
performance cost and can require elevated privileges depending on
platform/permissions — a dependency this report did not verify in this
environment.

## Option E — LLDP/CDP Discovery

Highest strategic value for a "network relationship mapping platform"
(per README.md's stated vision), but premature: `NetworkGraph` is
presently a flat, IP-keyed inventory with no topology/edge model
(confirmed in [docs/architecture/overview.md](../architecture/overview.md),
"Role of NetworkGraph"). Building adjacency discovery ahead of a consumer
for adjacency data provides no product value yet, and Phase 7
(Visualization/topology) has not started per ROADMAP.md.

---

# Recommended Direction

**FEAT-003B — Service Version & Metadata Enrichment** (Implementation
Option A).

**Why it should be next:** It is the only option in this assessment with
near-zero performance cost, no new provider, no ADR impact, and no
undefined scope — every other option has at least one open dependency
(DEEP's undefined scope, SNMP's UDP-scanning defect, OS detection's missing
consumer, LLDP/CDP's missing topology consumer). It also directly recovers
evidence Nmap is already returning during a scan NetworkMapper already
runs, which is the cheapest possible improvement available anywhere in this
assessment.

**Why competing options should wait:** Each has a real, named blocker
(above) that itself requires investigation or a product decision before
implementation — starting any of them now would violate ENGINEERING.md's
"stop and report when architectural uncertainty is discovered" principle
mid-sprint rather than during investigation, where it belongs.

**Expected customer value:** Indirect in the near term (exporters don't
surface ports/services/OS yet), but it raises classification confidence for
device types already covered by existing rules and lays groundwork for a
DEEP profile whose "deep" content is script/version-driven rather than
speculative.

**Expected engineering cost:** Low. Extends one existing method's argument
string and one existing parsing method; no new provider, no new test
architecture pattern (the existing `test_nmap_provider_scan_profile.py`
mocking approach applies directly).

**Risks:**
- NSE script output parsing (especially `ssl-cert` XML/text structure) adds
  real parsing surface area that the current `_extract_*` helpers don't
  have a precedent for.
- Deciding where product/version evidence lives on `Device` is a small
  model decision the next sprint's investigation phase must make
  explicitly — this report intentionally does not prescribe it.

**Dependencies:** None on other unimplemented work. Does not depend on
Option B, C, D, or E.

---

# Risks

- **Evidence collected without a consumer repeats a known failure mode.**
  `operating_system` is the concrete precedent in this codebase for
  shipping a discovery field with no classification rule to use it. Any
  future discovery sprint (this one included) should verify a consumption
  path exists or is planned before investing in new evidence collection
  beyond Option A's low-cost, already-scanned-port scope.
- **The SNMP/UDP scanning gap identified in this report is unverified
  against a live scan.** If a future SNMP sprint is scoped, its
  investigation phase should confirm this empirically before design work
  proceeds.
- **Exporters currently discard everything discovery already collects
  beyond classification inputs.** Prioritizing more discovery evidence
  without ever planning exporter work caps the practical ceiling on
  customer-visible value from this entire investigation area.

---

# Scope Recommendation

Proceed with FEAT-003B (Option A) as the next implementation sprint,
scoped narrowly to: (1) parsing already-returned `-sV` product/version/CPE
data, and (2) adding `http-title`, `ssl-cert`, and `smb-os-discovery` NSE
scripts to the existing STANDARD/DEEP enrichment pass on ports already in
`CLASSIFICATION_PORTS`. Do not bundle DEEP-profile redefinition, SNMP,
OS fingerprinting, or LLDP/CDP into the same sprint — each has its own open
question and belongs in its own investigation, consistent with
ENGINEERING.md's one-objective-per-sprint discipline.

**Stop Conditions evaluated and not triggered:**

- *ADR must change* — no. FEAT-003B fits inside ADR-001 and ADR-008
  without modification.
- *Discovery architecture is fundamentally insufficient* — no. The
  provider abstraction already supports future providers without rework;
  the gaps found are missing capability, not structural insufficiency.
- *Recommendation requires multiple independent implementation sprints* —
  no. FEAT-003B is a single, narrowly-scoped sprint. (Options B–E are
  legitimate future sprints, not part of this recommendation.)
- *Roadmap priorities should be reordered* — no. ROADMAP.md Phase 6
  ("Discovery Expansion") already anticipates this work and currently has
  no designated next sprint ("Current Priority" section), which this
  report's recommendation fills directly.

---

# Conclusion

NetworkMapper's discovery architecture — the `DiscoveryProvider`
abstraction, `DiscoveryEngine` coordination, and ADR-001's two-phase
STANDARD model — is sound and does not need to change to capture
substantially more evidence than it does today. The highest-value next
step is not a new discovery source; it is finishing the enrichment pass
NetworkMapper already runs, recovering data Nmap already returns and
currently throws away, and adding a small number of low-cost NSE scripts
on ports already being scanned. Higher-cost opportunities (SNMP, OS
fingerprinting, LLDP/CDP, a real DEEP profile) are legitimate and
roadmap-aligned, but each carries an open dependency this investigation
surfaced and none should be started until that dependency is resolved in
its own investigation.
