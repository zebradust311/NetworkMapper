# Status

Investigation Complete

Production Code Modified: No

ADR Required:
No — every candidate this investigation recommends for the near-term
roadmap fits ADR-009's per-service model or `Device`'s existing pattern
of incremental named fields. Two categories already identified in
FEAT-003E (SNMP interface/ifTable metadata, LLDP/CDP neighbor data) would
require a new ADR if pursued; this investigation reconfirms that finding
and adds no new ADR-triggering candidate.

Recommended Next Sprint:
FEAT-003G – SMB OS Discovery (already scoped by FEAT-003E/F's Architecture
Review), expanded by this investigation to also include SMB Security Mode
and the SMB2 dialect field (`smb2-time`) as free additions from the same
script family. RDP NTLM Info is
recommended as a distinct, lower-risk follow-on sprint (tentatively
FEAT-003H) rather than bundled into FEAT-003G — see Prioritized
Implementation Roadmap.

---

## Report Naming Correction

This investigation's objective titled it "ARCH-002," but that sprint
number is already in use: `ARCH-002A-Per-Service-Discovery-Evidence-
Architecture-Review.md` and `ARCH-002B-Per-Service-Discovery-Evidence-
ADR.md` both already exist, covering a different topic (the ADR-009
decision itself). Reusing "ARCH-002" here would collide with that
existing pair. Consistent with how this project's report series has
handled identical situations previously (`FEAT-003E`/`FEAT-003F`'s own
naming lineage), this report is filed as **ARCH-003** instead — the next
free number in the `ARCH-` series (`ARCH-001A`, `ARCH-002A`, `ARCH-002B`
already exist). This is a naming correction only; it does not change the
investigation's scope or content.

---

## Addendum (2026-08-05)

A follow-up prompt resubmitted this investigation's scope nearly
verbatim, with one addition not evaluated in the original pass: **SMB2
Time** (`smb2-time`). Rather than duplicate the entire report under a
new ID, this addendum adds `smb2-time` to Section 2.1 (SMB) and updates
the Architecture Fit, Operational Assessment, and Roadmap sections
accordingly. No other finding in this report changes.

---

## Executive Summary

This investigation inventories every piece of evidence NetworkMapper
currently extracts from Nmap, confirms which of it is actually consumed
by classification, and evaluates a broad set of additional Nmap/NSE
capabilities against ADR-009's evidence model.

Three findings anchor the roadmap:

1. **Three already-collected fields are consumed by nothing.**
   `ServiceEvidence.version`, `ServiceEvidence.protocol`, and
   `Device.operating_system` are populated by discovery (the first two by
   `NmapProvider` since FEAT-003C/F; `operating_system` by nothing at
   all, a gap FEAT-003A first flagged and no sprint since has closed) but
   read by zero classification rules — confirmed directly against every
   rule file, not inferred. This matters more than any new NSE script:
   before adding more evidence, NetworkMapper already has fields sitting
   unused.
2. **RDP NTLM Info (`rdp-ntlm-info`) is a materially better near-term
   candidate for `operating_system` than this investigation initially
   expected**, and was not evaluated in FEAT-003E. It targets port 3389
   (already in `CLASSIFICATION_PORTS`), returns a structured, protocol-
   level OS/computer-name/domain answer exactly like `smb-os-discovery`,
   but with a distinctly lower operational profile — RDP connection
   attempts are common, expected network traffic, unlike SMB session
   negotiation's lateral-movement-adjacent reputation. It should **not**
   be bundled into FEAT-003G's SMB-specific sprint on the assumption that
   "both populate `operating_system`" makes them operationally
   equivalent — they aren't.
3. **HTTP Authentication Realm (`http-auth`) is a new, high-confidence
   candidate this investigation surfaces that neither FEAT-003A nor
   FEAT-003E evaluated.** Many embedded/consumer devices (routers,
   printers, some IoT gear) gate their web UI behind HTTP Basic/Digest
   auth and present a realm string naming the exact model
   (`WWW-Authenticate: Basic realm="NETGEAR R7000"`). It requires zero
   authentication to observe, reuses ports already scanned, and fits
   `ServiceEvidence` exactly like `http_title`.

Only one capability evaluated in this investigation — LLDP/CDP — is
unambiguously **new-provider territory**, unreachable by any extension of
`NmapProvider`. Everything else evaluated, including SNMP, can be
achieved by extending the existing Nmap-based path. This directly answers
this investigation's central question: nearly the entire roadmap below
should be completed before a second `DiscoveryProvider` is ever
introduced.

---

## 1. Current Discovery Coverage

### Every field NetworkMapper collects today

| Field | Model | Source | Consumed by classification? |
|---|---|---|---|
| `ip_address` | `Device` | Nmap host discovery (`-sn`) | Identity only, not a classification input |
| `hostname` | `Device` | Nmap reverse-DNS/NetBIOS resolution | **Yes** — 6 of 8 rules |
| `mac_address` | `Device` | Nmap ARP resolution (local subnet only) | Indirectly (source of `vendor`); not read directly by any rule |
| `vendor` | `Device` | MAC OUI lookup | **Yes** — 6 of 8 rules |
| `operating_system` | `Device` | **Nothing populates this** | No — zero producers, zero consumers |
| `discovery_sources` | `Device` | Hardcoded `["nmap"]` | No — not a classification input (FEAT-003A) |
| `services[].port` | `ServiceEvidence` | `-sV` STANDARD enrichment | **Yes** — 6 of 8 rules |
| `services[].protocol` | `ServiceEvidence` | `-sV` result key (`tcp`/`udp`) | **No** — confirmed zero references in `networkmapper/classification/` |
| `services[].service` | `ServiceEvidence` | `-sV` service-name detection | **Yes** — 6 of 8 rules |
| `services[].product` | `ServiceEvidence` | `-sV` product detection | **Yes** — `CiscoSwitchRule` directly; `HypervisorHostnameRule`, `PrinterVendorRule`, `SonicWallFirewallRule` via `first_matching_identifier` |
| `services[].version` | `ServiceEvidence` | `-sV`, or `vmware-version` NSE when present (FEAT-003F) | **No** — confirmed zero references in `networkmapper/classification/` |
| `services[].http_title` | `ServiceEvidence` | `http-title` NSE (FEAT-003F) | **Yes** — `HypervisorHostnameRule`, `PrinterVendorRule`, `SonicWallFirewallRule` |
| `services[].tls_subject` | `ServiceEvidence` | `ssl-cert` NSE (FEAT-003F) | **Yes** — same three rules |
| `services[].tls_issuer` | `ServiceEvidence` | `ssl-cert` NSE (FEAT-003F) | **Yes** — same three rules |

This table was built by direct inspection, not by trusting prior reports'
summaries of it: every rule file under
`networkmapper/classification/rules/` was grepped for
`device.vendor`, `device.hostname`, `device.mac_address`,
`device.operating_system`, and every `evidence_helpers` accessor. The
result is exact, not estimated.

### Evidence collected but not consumed

Three fields are worth calling out specifically, because "identify
evidence already available but not currently consumed" is this
investigation's own mandate and each has a different story:

- **`operating_system`** — the long-standing dormant field (FEAT-003A,
  FEAT-003B). Still true after FEAT-003C–F: no discovery provider has
  ever populated it, and consequently no rule has ever needed to read
  it. This investigation's SMB/RDP findings (Section 2) are the first
  concrete producers proposed for it.
- **`ServiceEvidence.version`** — has had a real producer since
  FEAT-003F (`vmware-version`, and `-sV` more generally), but is read by
  no rule. This is a smaller-scale echo of the same "producer without
  consumer" pattern `operating_system` represents, flagged as a Known
  Issue in FEAT-003F and reconfirmed, not newly discovered, here.
- **`ServiceEvidence.protocol`** — different in kind from the two above.
  It was added in FEAT-003C specifically to make a *pre-existing scanning
  gap* visible (the unverified inference that UDP port 161/SNMP may not
  actually be reached because STANDARD enrichment omits `-sU`), not as a
  classification input. Its non-consumption is by design, not an
  oversight — it exists as diagnostic evidence about the scan itself,
  not evidence about the device.

---

## 2. Candidate Evidence Assessment

Each candidate below documents: information collected, classification
value, deterministic or heuristic, scan cost/traffic, security
considerations, and implementation complexity, per this investigation's
required format.

### 2.1 SMB

#### `smb-os-discovery`

Already fully evaluated in FEAT-003E and scoped as FEAT-003G by
Architecture Review. Not re-derived here. Summary: OS version/build,
computer name, and domain/workgroup via SMB negotiation on port 445
(already scanned); fully deterministic (structured protocol response);
low scan cost; the one candidate across the whole investigation series
with a distinct, real security consideration (SMB probing can read as
lateral-movement-adjacent to IDS/SOC tooling). Status: recommended,
sequenced as FEAT-003G, not yet implemented.

#### `smb-security-mode` (new to this investigation)

| Criterion | Assessment |
|---|---|
| Information collected | SMB signing policy (required/enabled/disabled), supported dialects (SMBv1/v2/v3), authentication level. |
| Classification value | **Low, and indirect.** This is a security-posture indicator, not a device-identity indicator. SMBv1-only support weakly correlates with legacy Windows or older NAS firmware, but that's a vintage hint, not a device-type signal any current rule could act on. |
| Deterministic or heuristic | Deterministic collection (structured protocol response). |
| Scan cost / traffic | Effectively free if `smb-os-discovery` is already being run — same initial SMB negotiate exchange, same port, same connection. |
| Security considerations | Identical to `smb-os-discovery`, because it is the same protocol interaction. No incremental risk beyond what FEAT-003G already accepts. |
| Implementation complexity | Trivial once `smb-os-discovery`'s SMB collection path exists — parsing one more field from output already being retrieved. |

**Recommendation:** bundle into FEAT-003G as a free addition, not a
separate sprint. Its classification value doesn't justify a dedicated
sprint on its own, but implementing it *outside* the sprint that's
already paying SMB's operational-review cost would be wasteful. Flagged
as security/compliance-relevant evidence for a *future* capability
(a device health/risk report), consistent with how FEAT-003E treated TLS
certificate expiration — out of scope for classification value, not
rejected outright.

#### `smb2-time` (new to this investigation)

| Criterion | Assessment |
|---|---|
| Information collected | The negotiated SMB2/SMB3 dialect (`2.02`, `2.10`, `3.0`, `3.02`, `3.11`) and the target's reported current system date/time (with timezone offset). |
| Classification value | **Low, on two different axes.** The negotiated dialect is a weak, indirect OS-vintage hint — dialect ceilings loosely correlate with OS generation (e.g. a `2.02`-only ceiling suggests an older stack; `3.1.1` support implies a materially newer one) but multiple OS/NAS generations overlap on supported dialects, so it is not a reliable device-type signal any rule could act on with confidence. The reported system time carries **no classification value at all** — it says nothing about device identity, only about clock state, and its only plausible use is a completely different future capability (clock-skew/drift diagnostics), not classification. |
| Deterministic or heuristic | Deterministic collection (structured SMB2 negotiation response); the dialect's *interpretation* as an OS hint would be heuristic if ever used, which is why it is not recommended for that purpose. |
| Scan cost / traffic | Effectively free if `smb-os-discovery`/`smb-security-mode` are already being collected — same SMB negotiate exchange, same port (445), same connection, one more field read from output already being retrieved. |
| Security considerations | Identical to `smb-os-discovery`/`smb-security-mode` — same protocol interaction, no incremental risk beyond what FEAT-003G already accepts. |
| Implementation complexity | Trivial once FEAT-003G's SMB collection path exists, for the dialect field. The time/timezone field is trivial to collect but has no current consumer or planned use. |

**Recommendation:** bundle the **dialect** field into FEAT-003G as a
third free addition alongside `smb-security-mode`, on the same "same
exchange, same sprint, don't pay the operational-review cost twice"
reasoning already applied to that field — but do **not** wire it into
classification; record it for the same possible future
vintage/health-context use as `smb-security-mode`. **Do not collect the
system time/timezone field** — unlike `smb-security-mode`, it has no
identified present or future consumer (not a security-posture indicator,
not a classification signal), so collecting it would be speculative data
collection with no stated purpose, which this project's evidence
standard (FEAT-003D/E/F: don't invent unsupported or purposeless
fingerprints) counsels against.

### 2.2 RDP

#### `rdp-ntlm-info` (new to this investigation)

| Criterion | Assessment |
|---|---|
| Information collected | Target NetBIOS computer name, NetBIOS domain name, DNS computer name, DNS domain name, and OS build number — revealed during RDP's CredSSP/NLA negotiation, before any authentication occurs. |
| Classification value | **High**, and structurally identical in kind to `smb-os-discovery`: a protocol-level, deterministic OS/identity answer, not a heuristic guess. Targets port 3389, already in `CLASSIFICATION_PORTS`. Complements SMB rather than duplicating it — some hosts have RDP open with SMB firewalled (or vice versa), so this catches devices `smb-os-discovery` alone would miss. |
| Deterministic or heuristic | Fully deterministic — structured protocol negotiation fields, not free text. |
| Scan cost / traffic | Low — one NSE script against a port already scanned; the negotiation this script performs is a small fraction of a full RDP connection attempt. |
| Security considerations | **Materially lower than SMB.** No authentication is attempted (the script reads information disclosed during the pre-auth negotiation phase only) and RDP connection attempts are common, unremarkable network traffic on any network with RDP enabled — unlike SMB session/enumeration-style interaction, which carries a specific lateral-movement association in security tooling. This is the clearest operational-risk differentiator this investigation found between two evidence sources that produce the same *category* of information. |
| Implementation complexity | Low — same integration shape as `vmware-version`: one more `--script` entry, one more parsing method, feeding the same (currently unpopulated) `Device.operating_system` field `smb-os-discovery` targets. |

**Architectural note:** because both `smb-os-discovery` and
`rdp-ntlm-info` can produce `operating_system` (and a computer-name/
domain pair), implementing both eventually raises a precedence question
— which source wins when both are present, or are they merged? This is
not a new architectural category (ADR-009 already established the
precedent in FEAT-003F: `vmware-version`'s script output is preferred
over `-sV`'s own guess for the same field, decided as a routine
implementation choice, not an ADR). The same applies here: whichever
sprint implements the second of the two sources should decide precedence
deliberately, as an implementation decision, not an architectural one.

**Recommendation:** distinct sprint from FEAT-003G, not bundled with it,
specifically *because* its risk profile differs enough to warrant its
own lighter-weight review rather than inheriting SMB's operational
caveats by association. See Prioritized Implementation Roadmap.

### 2.3 SSH

#### `ssh-hostkey` (new to this investigation)

| Criterion | Assessment |
|---|---|
| Information collected | SSH host public key(s) and their type(s) (RSA/ECDSA/ED25519), and key fingerprints. |
| Classification value | **Low for device-type classification.** Key type/algorithm doesn't reliably indicate vendor or device type — modern OpenSSH and most vendor SSH stacks support the same common key types. The SSH *banner* (already captured via `-sV`'s existing `product` detection, e.g. `"Cisco SSH"`, consumed by `CiscoSwitchRule` since FEAT-003D) is the far stronger classification signal already in use; host keys add nothing beyond it for this purpose. |
| Deterministic or heuristic | Deterministic collection (unauthenticated key exchange, no login attempted). |
| Scan cost / traffic | Low — one NSE script on an already-scanned port (22). |
| Security considerations | **Lowest-risk NSE script evaluated across this entire investigation series.** Retrieving a host's own public SSH key requires no authentication and is precisely what standard tools like `ssh-keyscan` do routinely; it is not associated with any enumeration or lateral-movement pattern. |
| Implementation complexity | Low, but see recommendation — the complexity is in what to *do* with the value, not in collecting it. |

**Recommendation:** **not** recommended for classification purposes.
Its genuine value lies elsewhere: a host key is a stable identifier that
persists across IP address changes, making it a strong candidate for a
completely different future capability — device identity/fingerprinting
for rescans and historical comparison (ROADMAP Phase 9, "Project
Intelligence," not Phase 3 "Intelligence"). This is out of ADR-009's
scope (which governs discovery evidence for *classification*) and not a
conflict with it — just a different problem, better addressed in a
future investigation focused on change tracking, if and when that
becomes a priority. Recorded here so it isn't rediscovered from
scratch later.

### 2.4 HTTP

#### `http-auth` (new to this investigation)

| Criterion | Assessment |
|---|---|
| Information collected | The authentication realm string presented in an HTTP `401 Unauthorized` challenge (`WWW-Authenticate: Basic realm="..."`). |
| Device types improved | `FIREWALL`, `PRINTER`, `ACCESS_POINT`, and any embedded-management-interface device type generally. Many consumer/embedded devices gate their entire web UI behind HTTP Basic/Digest auth rather than a styled login page, and commonly put the exact model in the realm string (a well-documented, long-standing convention for consumer routers, printers, and similar appliances). |
| Classification value | **High.** This is genuinely new evidence, not a restatement of something `http-title` or `product` already captures — a device using HTTP auth to gate access frequently has no meaningful page title to scrape (`http-title` would see only the generic auth-challenge page), making this a complementary signal to FEAT-003F's work, not a duplicate of it. |
| Deterministic or heuristic | Collection: fully deterministic (a single structured HTTP response header). Classification use: substring keyword matching, same category as every other free-text evidence field already in use. |
| Scan cost / traffic | Low — one more lightweight NSE script on ports already scanned (80, 443, 8080, 8443). No authentication is attempted; the realm is visible in the challenge itself. |
| Security considerations | Minimal — observing an auth challenge is not a login attempt. Same risk profile as `http-title`/`ssl-cert`. |
| Required scan profile | STANDARD (extends the existing enrichment call). |
| Implementation complexity | Low — identical shape to `http-title`: one new `ServiceEvidence` field (e.g. `http_auth_realm`), one more script in the existing `--script` list, one more parsing method. |
| ADR-009 model support | Yes — a new named field on `ServiceEvidence`, same incremental pattern as every prior addition. |
| New ADR required | No. |

**Recommendation:** the strongest single new finding in this
investigation. Recommended for the same near-term tier as the rest of
the passive HTTP/TLS work already implemented in FEAT-003F.

#### HTTP generic response headers (`http-headers`)

Reconfirms FEAT-003E's finding with one addition: beyond `Server:`
(already captured via `-sV`'s `product`/`version` parsing), other
headers (`X-Powered-By`, `Set-Cookie` naming patterns) occasionally leak
implementation details (e.g. `X-Powered-By: PHP/7.4.3`), but these
identify the *software stack*, not the *device vendor* — useful for
software inventory, not device-type classification, and heuristic with a
weaker signal-to-noise ratio than `http-auth` or `http-title`. **Not
recommended** as a dedicated initiative; no rule has a use for
stack-identification evidence today.

#### HTTP redirect information

Some embedded devices redirect their root path to a vendor-specific
management path (e.g. `/cgi-bin/luci` implying OpenWrt-based firmware).
This is a real but weak and speculative signal — path conventions are
far less consistently vendor-specific than an auth realm string or a
page title, and there is no single well-established NSE script dedicated
to capturing redirect targets independent of `http-title`'s own
(already-noted, per FEAT-003F's Known Issues) redirect-following
behavior. **Not recommended** as a dedicated initiative; at most an
opportunistic byproduct if `http-title`'s parsing is ever revisited.

### 2.5 TLS — additional certificate fields

FEAT-003E already evaluated and priced SANs (low priority, capturable
"for free" alongside subject/issuer if ever revisited) and expiration
(not a classification signal, security/compliance-relevant instead).
This investigation checked the remaining certificate sub-fields `ssl-cert`
exposes: public key algorithm/size, serial number, signature algorithm.
None carry classification value — they describe cryptographic
implementation choices, not device identity. Serial number has a
narrow, different potential use (a stable-ish identifier, similar in
spirit to an SSH host key, for future change-tracking) but is weaker for
that purpose than a host key (certificates are reissued far more often
than SSH host keys are rotated). **Not recommended** for classification;
noted and set aside for the same future change-tracking context as SSH
host keys, not rejected outright.

### 2.6 Banner Information

Reconfirms FEAT-003D/FEAT-003E's finding: generic banner-grabbing is
substantially redundant with what `-sV` already parses into
`product`/`version` for services on ports already scanned. **Not
recommended** as a distinct initiative; no new information found in this
investigation that changes that conclusion.

### 2.7 SNMP

Reconfirms FEAT-003E's full evaluation without modification:
`sysDescr`/`sysObjectID` as new `Device`-level fields remain the
highest-ceiling classification candidate evaluated across this entire
investigation series (a formally vendor-registered identifier), blocked
on a real prerequisite (confirming and fixing the `-sU` gap so UDP/161 is
actually reached), with a distinct operational profile (active
community-string probing, variable yield by environment). This
investigation additionally reviewed two more invasive SNMP NSE script
families while researching "other high-value NSE scripts":

- `snmp-interfaces` — the same interface/`ifTable` metadata FEAT-003E
  already found requires a topology/relationship model no part of the
  architecture has today. Reconfirmed, not re-derived.
- `snmp-win32-software`, `snmp-processes` — these enumerate installed
  software and running processes on a target. **Rejected outright, on
  the same product-philosophy grounds FEAT-003E used to reject
  vulnerability-assessment NSE scripts.** This is host-level software
  audit territory, not network discovery, and is a poor fit for every
  persona `ENGINEERING.md` defines.

### 2.8 SIP (new to this investigation)

Both FEAT-003D and FEAT-003F declined to extend `VoiceVendorRule` with
service-string evidence, citing insufficient confidence that Nmap's
default SIP probing reliably reveals phone vendor/model. This
investigation looked specifically for a dedicated SIP NSE script rather
than relying on `-sV`'s generic probe: `sip-methods` sends a SIP OPTIONS
request and, for many phones/PBX/ATA devices, receives a response whose
`Server:` or `User-Agent:`-equivalent header names the exact vendor or
model — a real, plausible signal, but one this investigation cannot
verify with the same confidence as `http-auth` or `rdp-ntlm-info`
without a live device to test against, consistent with every prior
sprint's honesty about this same limitation.

**Recommendation:** the one candidate in this investigation suited to a
small, explicit pilot rather than either full adoption or rejection —
add `sip-methods` to a future sprint's scan arguments and *observe*
actual response content across a few real environments before writing
any `VoiceVendorRule` matching logic against it, rather than committing
to a keyword list against an unverified assumption. This is a
process recommendation (validate before committing), not a roadmap tier
by itself.

### 2.9 LLDP/CDP

Reconfirms FEAT-003E's finding without modification: neighbor identity,
platform, and chassis information are relationship data between two
devices, not a fact about either one in isolation. `NetworkGraph` has no
representation for this today. Two points reconfirmed directly relevant
to this investigation's "before new discovery providers" framing:

- LLDP/CDP are link-layer multicast protocols; nothing about
  `NmapProvider`'s IP-based TCP/UDP scanning model can observe them.
  This is the **one and only candidate evaluated across FEAT-003E and
  this investigation that unambiguously requires a new
  `DiscoveryProvider`** — not an extension of the Nmap-based path, a
  structurally different collection technique (passive L2 capture, or an
  SNMP-MIB dependency with its own prerequisites).
- Even with a working collection mechanism, there is nowhere to record
  the result — a new ADR is required for the relationship/topology model
  itself, independent of the provider question.

### 2.10 Rejected Outright (not merely deferred)

Reconfirmed from FEAT-003E, no new information changes these
conclusions: favicon hashing (requires a self-maintained fingerprint
database, conflicts with deterministic-classification philosophy),
vulnerability-assessment/aggressive-intrusion NSE scripts (product-
philosophy mismatch), and — new to this investigation — invasive SNMP
software/process-enumeration scripts (same philosophy mismatch).

---

## 3. Architecture Fit Assessment

| Candidate | Extend `ServiceEvidence`? | Device-level? | New evidence model? | Conflicts with ADR-009? | Intentionally ignore? |
|---|---|---|---|---|---|
| `smb-os-discovery` (OS/computer/domain) | No | **Yes** | No | No | No — FEAT-003G |
| `smb-security-mode` | **Yes** (or device-level; weak either way) | Optional | No | No | Bundle into FEAT-003G, don't drive its own sprint |
| `smb2-time` (dialect field) | **Yes** (or device-level; weak either way) | Optional | No | No | Bundle into FEAT-003G, not wired into classification |
| `smb2-time` (system time field) | N/A — no identified consumer | N/A | No | No | **Yes** — do not collect, no stated purpose |
| `rdp-ntlm-info` (OS/computer/domain) | No | **Yes**, same fields as SMB (multi-producer) | No | No | No — recommended |
| `ssh-hostkey` | Would fit `ServiceEvidence` structurally | N/A | Arguably a *different* future model (device identity/fingerprint, not classification evidence) | No | **Yes**, for classification purposes |
| `http-auth` realm | **Yes** | No | No | No | No — recommended |
| `http-headers` (generic) | Would fit `ServiceEvidence` | No | No | No | Yes — no rule needs it |
| HTTP redirect target | Would fit `ServiceEvidence` | No | No | No | Yes — too speculative alone |
| TLS SANs | **Yes** (already established, FEAT-003E) | No | No | No | Opportunistic only |
| TLS expiration, serial, key algorithm | N/A — not classification evidence | No | No | No | Yes — different future capability |
| SNMP `sysDescr`/`sysObjectID` | No | **Yes** | No | No | No — reconfirmed from FEAT-003E |
| SNMP interface/`ifTable` | N/A | N/A | **Yes** | Requires new ADR | Deferred pending topology model |
| SNMP software/process enumeration | N/A | N/A | N/A | N/A | **Yes** — philosophy mismatch |
| `sip-methods` | Would fit `ServiceEvidence` | No | No | No | Pilot first, don't commit |
| LLDP/CDP | N/A | N/A | **Yes**, plus new provider | Requires new ADR | Deferred pending topology model + provider |
| Favicon hashing, vuln scripts | N/A | N/A | N/A | N/A | **Yes** — philosophy mismatch |

---

## 4. Operational Assessment

| Candidate | Scan duration impact | New traffic | Auth required? | Privilege required? | IDS/IPS consideration | STANDARD-suitable? |
|---|---|---|---|---|---|---|
| `smb-os-discovery` | Low | Low (SMB negotiate) | No | No | **Real** — SMB probing reads as enumeration-adjacent | Yes, with documentation (FEAT-003G) |
| `smb-security-mode` | Negligible (same exchange) | None beyond above | No | No | Same as above | Yes, bundled with FEAT-003G |
| `smb2-time` (dialect field) | Negligible (same exchange) | None beyond above | No | No | Same as above | Yes, bundled with FEAT-003G |
| `rdp-ntlm-info` | Low | Low (RDP negotiate) | **No** | No | **Low** — RDP connection attempts are common, unremarkable traffic | Yes |
| `ssh-hostkey` | Low | Low (key exchange) | No | No | **Lowest of all candidates** — identical to routine `ssh-keyscan` usage | Yes, if ever prioritized for identity tracking |
| `http-auth` | Low | Low (one more request per web port) | No | No | Minimal | Yes |
| `http-headers` | Low | Low | No | No | Minimal | Not prioritized (low value) |
| SNMP `sysDescr`/`sysObjectID` | Medium | Medium (new UDP traffic; requires `-sU` fix first) | Community string (not real auth) | No | Community-string probing, variable yield | Yes, after `-sU` fix |
| SNMP interface walk | High (multiple GETNEXT/walk ops) | Medium-High | Same as above | No | Same as above | Deferred (needs new model first) |
| `sip-methods` | Low | Low (one OPTIONS request) | No | No | Minimal, unverified | Pilot only |
| LLDP/CDP | N/A (different technique) | New (L2 capture or SNMP-MIB) | Depends on mechanism | Possibly (raw packet capture) | Passive capture or SNMP-dependent | N/A — new provider |

---

## 5. Prioritized Implementation Roadmap

**Tier 0 — close before adding anything new.** Wire `Device.operating_system`
and `ServiceEvidence.version` into classification once a producer exists
for the former (this tier is really "don't repeat the mistake" — see
Section 1). Not a scan-evidence sprint; a classification-consumption
sprint, same shape as FEAT-003D.

**Tier 1 (recommended immediately — extends FEAT-003F's already-approved
passive bundle):** HTTP Authentication Realm (`http-auth`). Same
operational profile as the four candidates FEAT-003F already implemented
— zero new risk, ports already scanned, no scan-argument change beyond
one more script name.

**Tier 2 (FEAT-003G, as already scoped, now expanded):** SMB OS
Discovery plus SMB Security Mode plus the SMB2 dialect field from
`smb2-time` (bundled — same script family, same port, same
already-accepted operational review). The `smb2-time` system time/
timezone field is explicitly excluded — no identified consumer.

**Tier 3 (new, distinct sprint — tentatively FEAT-003H):** RDP NTLM
Info. Kept separate from Tier 2 specifically because its risk profile is
lower than SMB's, despite targeting the same `Device`-level fields —
bundling it with FEAT-003G would import SMB's operational caveats onto a
candidate that doesn't carry them, understating how safe this evidence
source actually is. This sprint should also resolve the SMB/RDP
precedence question raised in Section 2.2 as a routine implementation
decision.

**Tier 4 (reconfirmed from FEAT-003E, unchanged):** SNMP
`sysDescr`/`sysObjectID`, blocked on confirming and fixing the `-sU` gap
first.

**Tier 5 (pilot, not a commitment):** `sip-methods` — observe real
response content before writing any matching logic against it.

**Deferred, prerequisite architecture work required (reconfirmed from
FEAT-003E):** SNMP interface/`ifTable` metadata and LLDP/CDP. Recommend a
dedicated architecture investigation (analogous to ARCH-002A) if and
when relationship/topology data becomes a priority.

**Intentionally set aside, not part of any classification roadmap:** SSH
host keys and TLS certificate serial numbers, both flagged as
better-suited to a future device-identity/change-tracking capability
(ROADMAP Phase 9) than to classification (ADR-009's actual domain).

**Rejected, not merely deferred:** favicon hashing, HTTP generic headers,
HTTP redirect-target capture, vulnerability/aggressive NSE scripts,
invasive SNMP software/process enumeration.

### What must precede introducing a new `DiscoveryProvider`

Precisely one capability evaluated across this investigation and
FEAT-003E requires a new provider: **LLDP/CDP.** Every other candidate —
including SNMP, which might intuitively feel like "provider-scale" work —
can be, and should be, achieved by extending the existing
`NmapProvider`/NSE path first. This investigation's Tiers 1 through 5
represent the practical ceiling of Nmap-extractable evidence identified
to date; completing them (or deliberately deferring specific ones with
documented reasoning, as this report does for SSH host keys and TLS
serial numbers) is what "maximize the value extracted from Nmap before
introducing additional discovery providers" concretely means for this
project. LLDP/CDP is correctly the trigger for that next architectural
step, not before.

---

## 6. ADR Recommendations

**No new ADR is required for this investigation's recommended roadmap**
(Tiers 0–5). Every field addition fits `ServiceEvidence` or `Device`'s
existing incremental-field pattern exactly as ADR-009 anticipated, and
the SMB/RDP precedence question (Section 2.2) is a routine implementation
decision with direct precedent (`vmware-version` vs. `-sV`, FEAT-003F),
not a new architectural boundary.

The two ADR-triggering findings are unchanged from FEAT-003E and are
restated, not newly discovered, here: SNMP interface/`ifTable` metadata
and LLDP/CDP both require a topology/relationship data model
`NetworkGraph` does not have. Should either be prioritized, it should
begin with its own architecture investigation (analogous to ARCH-002A),
not a discovery-evidence sprint.

---

## Stop Condition Review

This investigation's guidance frames it as preparatory to "introducing
additional discovery providers." No stop condition is triggered:
answering "what should be built next" does not require resolving any
architecture question first. Tier 1 (HTTP auth realm) is immediately
actionable with zero architectural prerequisite, exactly like FEAT-003F
before it. The one finding that does require new architecture (LLDP/CDP,
reconfirmed from FEAT-003E) is explicitly excluded from the recommended
roadmap rather than proposed for implementation.

---

## Conclusion

The highest-value next steps remain, as in FEAT-003E, extensions of the
existing Nmap-based discovery path rather than new infrastructure. This
investigation adds two genuinely new findings to that path — RDP NTLM
Info and HTTP Authentication Realm — both fitting ADR-009 exactly, both
low-risk, and reconfirms the rest of the previously-evaluated landscape
(SMB, SNMP, LLDP/CDP, and the philosophy-driven rejections) without
finding reason to revise any of it. The more consequential finding may
be structural rather than additive: `operating_system` and
`ServiceEvidence.version` are both already-collected evidence sitting
unused, a pattern this investigation series has now flagged three times
(FEAT-003A, FEAT-003B, this report) without a dedicated sprint closing
it. Before extending discovery further, wiring what's already collected
into classification is the cheapest and most overdue improvement
available. LLDP/CDP remains the one capability that genuinely requires a
new discovery provider, and is correctly the last item on this roadmap,
not the next.
