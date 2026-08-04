# Status

Investigation Complete

Production Code Modified: No

ADR Required:
No — every candidate in this investigation's recommended near-term
roadmap (TLS certificate subject/issuer, HTTP title, SMB OS discovery,
VMware version) fits ADR-009's existing per-service evidence model or
`Device`'s pre-existing pattern of incremental named fields, exactly as
ADR-009's Future Work anticipated ("the exact field set and types of the
per-service record" was explicitly left open, not fixed). Two candidates
evaluated here — SNMP interface/ifTable metadata and LLDP/CDP neighbor
data — **would** require a new ADR if pursued, because both are
relationship/topology data with no analog in `Device`, `ServiceEvidence`,
or `NetworkGraph` today. Neither is recommended as the next sprint; see
Stop Condition Review.

Recommended Next Sprint:
FEAT-003F – NSE-Script Discovery Evidence Collection (HTTP title, TLS
certificate subject, TLS certificate issuer, VMware version), followed by
FEAT-003G – SMB OS Discovery as a separate, isolated implementation
sprint. Per Architecture Review, SMB OS Discovery is deliberately split
out of the first sprint despite fitting the same Tier 1 cost/value
profile, because SMB probing has a distinct operational profile (it can
trigger IDS/SOC monitoring, unlike the passive HTTP/TLS evidence in
FEAT-003F) that warrants its own documentation, validation, benchmarking,
and future configuration decisions. Note the FEAT-003F/G naming
supersedes the single "FEAT-003E" placeholder name FEAT-003D used for
this scope of work — this investigation itself claimed the FEAT-003E ID,
so the corresponding implementation work is FEAT-003F and FEAT-003G. No
inconsistency: FEAT-003D's own text described this as a *recommendation*,
and an investigation sprint (this one) was warranted first, consistent
with this project's Investigation → Architecture Review → Implementation
lifecycle.

---

## Executive Summary

FEAT-003C established a correlated per-service discovery evidence model
(`ServiceEvidence`: port, protocol, service, product, version) and
FEAT-003D taught three classification rules to consume `product`. This
investigation asks what discovery evidence should be collected next.

The answer splits cleanly into two tiers, separated by a hard technical
and architectural line:

- **Tier 1 — reuses evidence already being retrieved on ports already
  being scanned.** TLS certificates are already exchanged during the
  `-sV` handshake on 443/8443; HTTP responses are already received on
  80/443/8080/8443; SMB negotiation already touches port 445. Extracting
  more from data already in flight costs one Nmap Scripting Engine (NSE)
  script per port, not a new scan, new port, or new provider. All four
  Tier 1 candidates (TLS subject/issuer, HTTP title, SMB OS discovery,
  VMware version) fit `ServiceEvidence` or `Device`'s existing field-by-
  field evolution pattern without any architectural change.
- **Tier 2/3 — requires new scanning behavior, a new provider, or a new
  data model.** SNMP evidence requires first fixing a known-but-unverified
  gap (STANDARD enrichment never adds `-sU`, so UDP/161 may not actually
  be reached today). SNMP interface metadata and LLDP/CDP neighbor data
  are not per-device facts at all — they are relationships between two
  devices, which nothing in `Device`, `ServiceEvidence`, or `NetworkGraph`
  can represent today. These are real, valuable, and explicitly not
  recommended next.

The prioritized roadmap recommends the four Tier 1 candidates across two
implementation sprints rather than one: FEAT-003F (HTTP title, TLS
certificate subject, TLS certificate issuer, VMware version — all passive,
no scan-argument changes, no meaningful operational risk) and FEAT-003G
(SMB OS Discovery, isolated on its own because it carries a distinct
operational profile — see Architecture Review Note below). SNMP
device-level evidence (sysDescr/sysObjectID) remains a distinct follow-on
sprint once the `-sU` gap is confirmed and fixed, and SNMP interface
metadata and LLDP/CDP remain deferred until a topology/relationship model
exists — which is a foundational architecture question, not a
discovery-evidence question, and out of this investigation's scope to
resolve.

**Architecture Review Note (post-investigation):** the Architecture
Review that approved this investigation's findings directed that SMB OS
Discovery be split into its own implementation sprint (FEAT-003G) rather
than bundled with the other three Tier 1 candidates (FEAT-003F), even
though SMB OS Discovery's cost/value profile places it in Tier 1
alongside them. The reason is operational, not technical: SMB probing's
distinct IDS/SOC visibility (documented in the SMB candidate evaluation
below) warrants its own documentation, validation, benchmarking, and
future configuration decisions, separate from the three purely passive
candidates. This does not change any candidate's technical evaluation —
only how the roadmap sequences implementation work.

---

## Current State (Evidence Baseline)

Confirmed directly from the current repository, not from prior reports'
summaries of it:

- `NmapProvider._standard_enrichment_arguments()` returns
  `-Pn -sV --version-light -p <16 ports>` — no `--script`, no `-sU`, no
  `-O`. The 16 ports are `CLASSIFICATION_PORTS`:
  22, 53, 80, 161, 443, 445, 515, 631, 9100, 3389, 5060, 5061, 8080, 8443,
  902, 903.
- `ServiceEvidence` (`networkmapper/core/models.py`) has exactly five
  fields: `port`, `protocol`, `service`, `product`, `version`.
- `Device` has `operating_system: Optional[str]`, populated by nothing
  (confirmed unchanged since FEAT-003A/FEAT-003B; FEAT-003D did not touch
  discovery or the `Device` model).
- `NetworkGraph` stores `dict[str, Device]` — no relationship, edge, or
  interface concept exists anywhere in the codebase (confirmed by
  `docs/architecture/overview.md`'s own description of `NetworkGraph` as
  "a lightweight inventory model rather than a rich topology engine").
- Classification rules that consume product evidence as of FEAT-003D:
  `HypervisorHostnameRule` (`"vmware"`), `CiscoSwitchRule`
  (`"cisco"`), `PrinterVendorRule` (reuses
  `SUPPORTED_PRINTER_VENDOR_KEYWORDS`). `SonicWallFirewallRule` and
  `UbiquitiAccessPointRule` were explicitly left unchanged in FEAT-003D
  for lack of a reliable `-sV`-only product signal — this is the direct
  motivation for evaluating NSE-script evidence here.

`python -m devtools validate`: 83 tests run, 0 failures, 0 errors, PASS —
identical to the post-FEAT-003D baseline, confirming this sprint made no
code changes.

---

## Candidate Evaluation

Each candidate is evaluated against: information collected, device types
improved, classification value, deterministic or heuristic, expected scan
cost, additional network traffic, security considerations, required scan
profile, ADR-009 compatibility, and whether a new ADR would be required.

### HTTP

#### `http-title`

| Criterion | Assessment |
|---|---|
| Information collected | The HTML `<title>` of the default page on an HTTP/HTTPS port. |
| Device types improved | `FIREWALL` (SonicWall), `ACCESS_POINT` (Ubiquiti), `HYPERVISOR` (VMware) — exactly the rules FEAT-003D could not extend with `-sV`-only evidence. Many embedded management UIs put the product name directly in the page title (e.g. "SonicWALL - Network Security Appliance", "VMware ESXi", vendor-branded UniFi/printer UI titles). |
| Classification value | High for the specific gap it closes; the title text itself is a single deterministic string, but *matching* it to a vendor requires keyword substring matching — the same heuristic-but-deterministic pattern already used for `vendor`/`product`/`service` matching throughout the classifier (not a new kind of risk). |
| Deterministic or heuristic | Collection: deterministic (one HTTP GET, one string). Classification use: keyword matching, same category as existing `product`/`vendor` substring checks. |
| Expected scan cost | Low — one additional lightweight NSE script per already-scanned web port (80, 443, 8080, 8443). |
| Additional network traffic | One extra HTTP GET per web port already being probed by `-sV`. Passive from the target's perspective — indistinguishable from a browser loading the page. |
| Security considerations | Minimal. Standard, unauthenticated HTTP GET; the same request class any web browser or monitoring tool makes routinely. |
| Required scan profile | STANDARD (extends the existing phase-2 enrichment call; no new phase). |
| ADR-009 model support | Yes — one new `Optional[str]` field on `ServiceEvidence` (e.g. `http_title`), same pattern as `product`/`version`. |
| New ADR required | No. |

#### HTTP Server header / generic response headers

Largely redundant: Nmap's `-sV` HTTP probe already parses the `Server:`
header into `product`/`version` in most cases — this is not new
evidence, it is evidence already flowing through the existing pipeline.
Capturing *other* headers (e.g. `WWW-Authenticate` realm strings) is
lower-value, more heuristic, and was not found to close any specific gap
FEAT-003D left open. **Not recommended as a distinct initiative.**

#### Favicon hashing

Requires a maintained hash-to-vendor lookup database NetworkMapper does
not have and would need to build and keep current itself — unlike NSE
signatures, which Nmap's own project maintains. This is fundamentally a
fuzzy-matching technique against externally-sourced data, in tension with
`docs/ADR.md`'s and `ENGINEERING.md`'s emphasis on deterministic,
explainable classification (ADR-002, ADR-003). **Rejected** — not a
scan-cost or complexity problem so much as a philosophy mismatch; pursuing
it would mean maintaining a second, unrelated data-curation project
alongside NetworkMapper itself.

### TLS

#### `ssl-cert` — subject and issuer

| Criterion | Assessment |
|---|---|
| Information collected | Certificate subject (CN, O, OU) and issuer, from the TLS handshake `-sV` already performs on 443/8443. |
| Device types improved | `FIREWALL`, `HYPERVISOR`, `ACCESS_POINT` — embedded management interfaces frequently self-sign certificates whose subject names the product ("SonicWALL", "VMware", vendor-specific UniFi OS naming). |
| Classification value | High, and structurally more reliable than free-text page titles: X.509 subject fields have defined semantics (CN/O/OU) even though vendors still populate them with arbitrary text — a middle ground between `product` (semi-structured, Nmap-parsed) and `http_title` (fully free-text). |
| Deterministic or heuristic | Collection: fully deterministic — the certificate is already retrieved as part of the existing handshake; nothing new is transmitted. Classification use: keyword/substring matching, same category as existing evidence. |
| Expected scan cost | **Effectively zero additional cost.** The TLS handshake already happens for `-sV` on HTTPS ports; this only changes what's parsed from data already received. |
| Additional network traffic | None beyond the handshake `-sV` already performs. |
| Security considerations | None beyond the existing HTTPS connection attempt already made by STANDARD enrichment. |
| Required scan profile | STANDARD. |
| ADR-009 model support | Yes — two new `Optional[str]` fields on `ServiceEvidence` (e.g. `tls_subject`, `tls_issuer`). |
| New ADR required | No. |

This is the single cheapest candidate evaluated in this investigation:
it adds no network traffic at all beyond what STANDARD enrichment already
generates.

#### `ssl-cert` — Subject Alternative Names (SANs)

Typically alternate hostnames for the same service; rarely reveals device
identity beyond what subject/issuer already provide. **Low priority** —
worth capturing opportunistically if the `ssl-cert` script is added for
subject/issuer anyway (same script, same data structure), but not a
reason to prioritize this work on its own.

#### `ssl-cert` — expiration

Not a classification signal — an expired or soon-to-expire certificate
says nothing about device type. This is a security/compliance signal for
a different NetworkMapper capability (a future risk/health report), not
this investigation's classification-quality question. **Out of scope**
for this evaluation, noted only so it isn't mistaken for an oversight.

### SMB

#### `smb-os-discovery`

| Criterion | Assessment |
|---|---|
| Information collected | Precise OS version/build, computer name, and domain/workgroup, via SMB protocol negotiation on port 445 (already in `CLASSIFICATION_PORTS`). |
| Device types improved | `SERVER`, `WORKSTATION` — currently classified by hostname keyword alone (`ServerHostnameRule`, `DellWorkstationRule`); an authoritative OS string and domain-joined status would be strictly stronger evidence than hostname pattern-matching for these two rules specifically, though wiring that consumption is separate implementation work beyond this investigation. |
| Classification value | High, and uniquely **not heuristic** — SMB protocol negotiation returns a structured, protocol-level answer, not a probabilistic guess. This is the most deterministic evidence-collection mechanism evaluated in this investigation. |
| Deterministic or heuristic | Fully deterministic collection (structured protocol response, not free text). |
| Expected scan cost | Low — one NSE script on an already-scanned port. |
| Additional network traffic | A small number of SMB negotiate/session-setup packets against port 445, already being probed by `-sV`. |
| Security considerations | **The one candidate in this investigation with a real, distinct operational caveat.** SMB negotiation is a more "active" protocol interaction than an HTTP GET or a TLS handshake, and some security tooling (IDS/IPS, SOC monitoring) treats unsolicited SMB enumeration as a lateral-movement indicator, independent of whether it's actually malicious. A technician running this against a client network could trigger a security alert that an HTTP or TLS-based script would not. This does not disqualify the candidate — `smb-os-discovery` is one of Nmap's own default (`-sC`) scripts and is extremely common in legitimate network-discovery tooling — but it is worth surfacing explicitly to whoever scopes the implementing sprint, unlike every other Tier 1 candidate. |
| Required scan profile | STANDARD. |
| ADR-009 model support | This is **not** per-service evidence — OS, computer name, and domain are device-wide facts, not tied to a specific port. It fits `Device`'s pre-existing pattern of individual named fields (the same pattern `operating_system` itself already used) rather than `ServiceEvidence`. `operating_system` already exists and needs no new field at all; `computer_name`/`domain` would be one or two new `Device` fields, following the exact same incremental pattern. |
| New ADR required | No — this doesn't even touch ADR-009's per-service model; it's the same kind of `Device`-level field addition the project has always done. |

Notably, `smb-os-discovery` would be the first real *producer* for the
`operating_system` field FEAT-003A and FEAT-003B both flagged as fully
wired but permanently empty since the very first commit that created the
`Device` model. Closing that gap was explicitly named as future work in
neither FEAT-003A nor FEAT-003B, but this investigation identifies it as
essentially free once `smb-os-discovery` is added for classification
purposes on Windows hosts.

### SNMP

#### sysDescr / sysObjectID (device-level fields)

| Criterion | Assessment |
|---|---|
| Information collected | `sysDescr` (free-text device description) and `sysObjectID` (a vendor-assigned, IANA-enterprise-number-based OID identifying the exact product line) via SNMP GET on port 161. |
| Device types improved | Network infrastructure broadly — `SWITCH`, `FIREWALL`, `PRINTER`, and potentially a future `ROUTER` rule (no rule currently produces `ROUTER` at all, a gap FEAT-003A already noted independently of this investigation). |
| Classification value | **Potentially the highest ceiling of any candidate evaluated.** `sysObjectID` is a formally standardized, vendor-registered identifier — more rigorously structured than a TLS certificate subject or an HTTP title, which are free text a vendor chose to write. |
| Deterministic or heuristic | Collection: deterministic (structured SNMP response). Classification use of `sysObjectID` could be close to a direct lookup (vendor OID prefixes are public and stable) rather than substring heuristics; `sysDescr` remains free text requiring keyword matching, similar to `product`. |
| Expected scan cost | **Meaningfully higher than the Tier 1 candidates above**, for a specific, concrete reason (next row). |
| Additional network traffic | Requires actual UDP traffic to port 161 with an SNMP community string (commonly `"public"` as a default guess). This is new traffic, not extraction from an existing handshake. |
| Security considerations | Sending SNMP community-string probes is a more active, more visible action than the passive/opportunistic Tier 1 candidates, though it is standard, well-established discovery-tooling practice (not credential brute-forcing) and low risk in context. Some environments disable SNMPv1/v2c entirely or use non-default community strings, meaning yield will vary significantly by environment (higher in homelab/small-office, lower in hardened enterprise). |
| Required scan profile | **This candidate cannot work with today's scan arguments as they stand.** `_standard_enrichment_arguments()` has no `-sU`; FEAT-003A flagged, as an unverified inference, that port 161 (already in `CLASSIFICATION_PORTS`) may therefore never actually be reached as UDP. Implementing SNMP evidence collection requires first adding `-sU` — a genuine scan-argument change, not merely an added script layered onto the existing TCP flow like every Tier 1 candidate. This is the clearest cost differentiator between SNMP and the four Tier 1 candidates above. |
| ADR-009 model support | Yes for the fields themselves — `sysDescr`/`sysObjectID` are device-level facts, fitting the same `Device` named-field pattern as `operating_system`. |
| New ADR required | No, for the evidence model itself. (The `-sU` argument change is routine scan-configuration work, not an architectural decision requiring an ADR — but it is real, additional scope beyond "add an NSE script.") |

#### SNMP interface / ifTable metadata

Interface-level data (`ifDescr`, `ifTable` walks) is not a fact about
*one* device — an interface entry only means something in relation to
what it connects to, and NetworkMapper has no interface or link concept
in its data model today (`docs/architecture/overview.md` explicitly
scopes `NetworkGraph` as inventory, not topology). Collecting it would
require multiple SNMP GETNEXT/walk operations per device (heavier traffic
than a handful of GETs) and, more importantly, **somewhere to put the
result that doesn't exist yet.** **This requires a new ADR if pursued** —
it is genuinely new data-model territory, not an extension of ADR-009's
per-service principle or `Device`'s field-by-field pattern.

### LLDP / CDP

Neighbor identity, platform, and chassis information are fundamentally
**relationship** data between two devices, not a fact about either one in
isolation — the same structural category as SNMP interface metadata, one
level further from anything the current model supports. Two additional
findings specific to LLDP/CDP:

- **Collection technique mismatch.** LLDP/CDP are link-layer multicast
  protocols; nothing about `NmapProvider`'s IP-based TCP/UDP port-scan
  model can observe them. This would require either passive L2 packet
  capture (a fundamentally different technique from anything
  `NmapProvider` does) or SNMP LLDP-MIB/CDP-MIB queries (itself dependent
  on the SNMP prerequisites above). This is unambiguously **new-provider**
  territory — which the `DiscoveryProvider` abstraction already
  anticipates architecturally (confirmed compatible in ARCH-002A), so the
  provider mechanism itself is not the blocker.
- **Data-model mismatch is the actual blocker.** Even with a working
  collection mechanism, there is nowhere in `NetworkGraph` to record "device
  A's port 3 connects to device B's port 7." This is the same "new ADR
  required" territory as SNMP interface metadata, one step further removed
  from the current architecture, and was already flagged as premature
  relative to product readiness in FEAT-003A. This investigation reconfirms
  that conclusion with the added, more specific finding that neither
  ADR-008 nor ADR-009 — nor any other existing ADR — provides a
  representation for inter-device relationships at all.

**LLDP/CDP is the strongest "requires fundamental architecture change"
finding in this investigation.** See Stop Condition Review.

### VMware — existing and additional NSE scripts

Nmap's `vmware-version` NSE script queries the ESXi/vCenter SOAP API
(already reachable on port 443, already in `CLASSIFICATION_PORTS`) for
exact build/version information.

| Criterion | Assessment |
|---|---|
| Information collected | Exact ESXi/vCenter product and build version. |
| Device types improved | `HYPERVISOR` only — narrow, but this is already NetworkMapper's most heavily corroborated device type (FEAT-002B port additions, FEAT-003D product-string matching). |
| Classification value | High precision for a single device type; complements, rather than duplicates, the `"vmware"` product-substring check FEAT-003D already added. |
| Deterministic or heuristic | Deterministic — structured API response, not text scraping. |
| Expected scan cost | Very low — one more `--script` argument on an already-scanned port. |
| Additional network traffic | One additional lightweight API query on port 443, already probed. |
| Security considerations | Minimal — a standard, read-only API query. |
| Required scan profile | STANDARD. |
| ADR-009 model support | **Full — populates the existing `ServiceEvidence.version` field. No new field required at all.** |
| New ADR required | No. This is the lowest-friction candidate in the entire investigation: it needs no model change of any kind. |

### Other Nmap capabilities

- **`-O` general OS fingerprinting.** Already extensively evaluated in
  FEAT-003A: probabilistic (confidence-percentage) TCP/IP stack
  fingerprinting, slower, and sometimes requires elevated privileges. For
  the specific goal of populating `operating_system`, `smb-os-discovery`
  (above) is a strictly better mechanism for Windows hosts — a
  deterministic protocol answer instead of a heuristic guess, at lower
  cost. **`-O` is not recommended as a priority**; it would only add value
  for non-Windows devices where SMB doesn't apply, which is a narrower
  and lower-value case than this investigation's other findings.
- **Generic banner-grabbing (`banner` NSE).** Substantially redundant
  with what `-sV` already extracts into `product`/`version` for most
  services. **Not recommended** as a distinct initiative.
- **Vulnerability-assessment or aggressive-intrusion NSE script
  categories.** Explicitly evaluated and **rejected on product-philosophy
  grounds**, independent of technical feasibility. NetworkMapper is
  positioned throughout `README.md` and `ENGINEERING.md` as a discovery
  and documentation platform for technicians and MSPs, not a security
  scanner; running vulnerability-probing scripts against a customer
  network without a specifically scoped security engagement is a category
  mismatch with every persona `ENGINEERING.md` defines (Technician,
  Account Manager, Customer), not merely a cost/complexity tradeoff.

---

## Comparison Matrix

| Candidate | Classification value | Deterministic? | Scan cost | New traffic | Security consideration | Scan profile | ADR-009 model fit | New ADR? |
|---|---|---|---|---|---|---|---|---|
| TLS cert subject/issuer | High | Yes (collection) | Minimal | **None** (reuses existing handshake) | None | STANDARD | Yes (new `ServiceEvidence` fields) | No |
| VMware version (`vmware-version`) | High (narrow) | Yes | Very low | Minimal | None | STANDARD | Yes (existing `version` field) | No |
| HTTP title (`http-title`) | High | Yes (collection) / heuristic (use) | Low | Low (1 extra GET) | None | STANDARD | Yes (new `ServiceEvidence` field) | No |
| SMB OS discovery | High | **Yes (protocol-level)** | Low | Low | **Real — SMB probing can trigger SOC/IDS alerts** | STANDARD | Yes (new/existing `Device` fields) | No |
| TLS SANs | Low-Medium | Yes | Minimal (same script) | None | None | STANDARD | Yes | No |
| SNMP sysDescr/sysObjectID | **Highest ceiling** | Yes (collection) | **Medium** (needs `-sU` fix first) | Medium (new UDP traffic) | Community-string probing, variable yield | STANDARD (after `-sU` fix) | Yes (new `Device` fields) | No |
| `-O` OS fingerprinting | Medium (redundant w/ SMB for Windows) | No (probabilistic) | Medium-High | Medium | Privilege requirements | N/A | Yes (existing field) | No |
| TLS expiration | N/A (not a classification signal) | Yes | Minimal | None | None | — | — | — |
| HTTP generic headers | Low | Heuristic | Low | Low | None | — | — | — |
| Favicon hashing | Low-Medium (needs new DB) | **No (fuzzy match)** | Medium | Low | None | — | — | — |
| SNMP interface/ifTable | High (topology) | Yes (collection) | High | Medium-High | Same as SNMP above | N/A | **No** | **Yes** |
| LLDP/CDP | High (topology) | Yes (collection) | High (new provider) | New (L2 or SNMP-MIB) | Passive capture or SNMP-dependent | N/A (new provider) | **No** | **Yes** |
| Vulnerability/aggressive NSE | N/A | N/A | N/A | High | **Rejected on product-philosophy grounds** | — | — | — |

---

## Prioritized Implementation Roadmap

**Sprint 1 (recommended next — FEAT-003F):** HTTP title, TLS certificate
subject, TLS certificate issuer, VMware version. All four reuse ports
already in `CLASSIFICATION_PORTS`, add NSE scripts only (no scan-argument
changes beyond `--script`), fit the existing model without any new ADR,
introduce no meaningful operational risk (no security consideration
beyond "None" or "Minimal" in the Comparison Matrix), and directly close
specific gaps FEAT-003D identified (`SonicWallFirewallRule`,
`UbiquitiAccessPointRule` lacking product-level evidence).

**Sprint 2 (FEAT-003G — isolated from Sprint 1 per Architecture
Review):** SMB OS Discovery, on its own. Although SMB OS Discovery's
cost/value profile otherwise matches Sprint 1's candidates, and although
it would be the first real producer for the long-standing dormant
`operating_system` field (FEAT-003A, FEAT-003B), it is deliberately
sequenced into its own sprint rather than bundled with Sprint 1: SMB
negotiation has a materially different operational profile from HTTP/TLS
evidence (documented in the SMB candidate evaluation above) — it can
trigger IDS/SOC monitoring in ways a passive HTTP GET or TLS handshake
cannot — and isolating it allows FEAT-003G to give that tradeoff its own
documentation, validation, benchmarking, and future configuration
decisions (e.g. whether SMB OS Discovery should be opt-in) without
diluting the otherwise risk-free Sprint 1 scope.

**Sprint 3 (follow-on, not bundled with Sprints 1 or 2):** SNMP sysDescr/
sysObjectID as new `Device`-level fields. Sequenced separately because it
has a real prerequisite (confirming and fixing the `-sU` gap FEAT-003A
flagged) and a distinct security/operational profile (active UDP
community-string probing) that deserves its own focused investigation of
expected yield and risk in typical customer environments, rather than
being folded into either of the Tier 1 sprints above.

**Deferred, prerequisite work required (not scoped by this
investigation):** SNMP interface/ifTable metadata and LLDP/CDP neighbor
data. Both require a topology/relationship data model that does not exist
in `NetworkGraph` today, and LLDP/CDP additionally requires a new
discovery provider. Recommend a dedicated architecture investigation
(analogous to ARCH-002A) if and when relationship/topology data becomes a
priority — this is a foundational data-model question, not a discovery-
evidence question, and resolving it is out of this investigation's scope.

**Rejected, not merely deferred:** favicon hashing (determinism/
maintenance mismatch), vulnerability/aggressive NSE scripts (product-
philosophy mismatch), generic banner grabbing (redundant with existing
`-sV` output).

---

## Stop Condition Review

The stop condition triggers only if answering "what should be built next"
requires first resolving a fundamental architecture change. It does not:
Sprints 1 and 2 (FEAT-003F and FEAT-003G) together cover all four Tier 1
candidates and form a complete, well-justified, immediately actionable
recommendation that needs no architecture change of any kind — splitting
them across two sprints is a sequencing decision, not an architectural
one.

Two candidates evaluated *within* this investigation — SNMP interface
metadata and LLDP/CDP — were found to require a new ADR (a topology/
relationship model `NetworkGraph` does not have). This is reported as a
finding, not a reason to halt the investigation: both are explicitly
excluded from the recommended roadmap rather than proposed for
implementation, consistent with "do not propose implementation work" for
anything not actually ready. If either is prioritized in the future, it
should begin with its own architecture investigation, not a discovery-
evidence sprint.

---

## Validation

`python -m devtools validate`: 83 tests run, 0 failures, 0 errors, PASS —
identical to the result following FEAT-003D. This confirms the expected
outcome for a documentation-only investigation sprint; no production
code, test, or benchmark file was modified.

---

## Conclusion

The next engineering investment with the best ratio of classification
value to cost is not a new discovery provider or a new data model — it is
extracting more from scans NetworkMapper already runs. TLS certificates,
HTTP responses, and SMB negotiation on already-scanned ports all carry
usable evidence today that is simply not being parsed. All four Tier 1
candidates fit ADR-009's model exactly as its Future Work anticipated,
require no new ADR, and directly close gaps the two preceding sprints
(FEAT-003A/B and FEAT-003D) already identified by name. SNMP and
LLDP/CDP are real, valuable, and correctly out of scope for the
immediate next sprint — SNMP because of a concrete scan-argument
prerequisite and distinct security profile, LLDP/CDP because it requires
relationship data no part of the current architecture can represent.
