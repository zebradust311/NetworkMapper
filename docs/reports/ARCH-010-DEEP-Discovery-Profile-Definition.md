# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No for the recommended v1 scope (every included capability
fits `ServiceEvidence`/`Device`'s existing incremental-field pattern, per
ADR-009). OS fingerprinting is deferred out of DEEP v1 entirely per
architecture review — it belongs to a dedicated future architecture
effort on heuristic, confidence-scored evidence generally, which should
determine for itself whether a new ADR is required (a value+confidence
pair has no precedent on `Device` today). Not required to define or
implement DEEP v1 itself.

Recommended Next Sprint:
FEAT-00X — Implement DEEP Profile Per This Architecture (v1 scope only
— see Recommended DEEP Profile Composition. OS fingerprinting is out of
scope for this sprint; see Recommendations).

---

## Executive Summary

DEEP currently behaves identically to FAST (DISC-001 Finding 2) — it has
never been given an identity distinct from either FAST or STANDARD. This
investigation defines that identity.

**DEEP is not "STANDARD with everything else turned on."** It is a
deliberately narrower thing: an opt-in, higher-cost, higher-visibility
profile a technician chooses for a *specific, bounded scope* — a
problem subnet, a rack, a pre-handoff verification pass — not a
replacement for STANDARD as the default broad-sweep profile across an
entire enterprise network. Every capability evaluated below is judged
against that use case, not against "would this be nice to have
somewhere."

The recommended DEEP composition is a strict superset of STANDARD: same
two-phase structure (ADR-001, unchanged), same enrichment script set,
extended along five axes — wider TCP port coverage, higher version
-detection intensity, a curated UDP reachability fix, expanded VMware
port coverage, and modest timing/retry patience. Three categories
evaluated and explicitly **excluded** from DEEP v1: LLDP/CDP (requires a
new `DiscoveryProvider` and a topology model DEEP's scope can't fix),
OS fingerprinting (a heuristic, confidence-scored evidence category
deferred to its own future architecture effort per architecture review
— see Recommendations), and any form of authenticated discovery (a
categorically different capability tier — DEEP stays unauthenticated by
design, same as every profile today).

No code changes accompany this report. This is an architecture
definition only, per this sprint's explicit scope.

---

## Framing: What DEEP Is For

### Intended Use Cases

- A technician has run STANDARD across a site and found a subnet, rack,
  or device cluster where evidence is thin (DISC-001's own finding: this
  is usually profile scope, not a defect) and wants to spend more time
  and traffic on that specific scope to close the gap before writing up
  documentation.
- A pre-handoff or audit-quality documentation pass on a bounded
  environment, where completeness matters more than speed and the
  technician can justify additional network visibility to the customer.
- An unfamiliar or heavily embedded/appliance-dense environment where
  STANDARD's curated 16-port set is suspected to be missing management
  interfaces on nonstandard ports (a common pattern for embedded web
  UIs — port 8000, 8888, 10000, etc.).

### Operator Expectations

DEEP should be understood, and eventually documented to the operator
(the same way `PROFILE_MESSAGES` from OBS-001 already states FAST's and
STANDARD's behavior plainly), as: **slower, louder, and still
unauthenticated.** Not "more thorough but otherwise free" — every
capability evaluated below trades runtime and/or network visibility for
evidence. An operator choosing DEEP should expect a scan that takes
meaningfully longer than STANDARD and that is more likely to be visible
to network security tooling, and should choose it deliberately for a
bounded scope rather than defaulting to it for a full enterprise sweep.

### Runtime Tradeoffs and Network Impact

No benchmarking infrastructure exists to produce measured numbers for
this investigation (no code was written or run) — the estimates below
are qualitative, drawn from each capability's Nmap mechanics, and should
be treated as directional, not contractual. The dominant cost driver is
port-range expansion (Section 2.1): querying ~1,000 ports per host
instead of 16 is the single largest surface-area increase evaluated,
though because `-sV`/NSE cost is only paid on ports found open, actual
wall-clock impact scales with how many additional open ports a given
network actually has, not with the raw port count itself. Of the
capabilities evaluated, OS fingerprinting and UDP scanning were the two
most likely to change a Nmap profile's *visibility* to IDS/IPS tooling,
independent of raw runtime — see their respective tables. OS
fingerprinting is deferred out of v1 (see Recommendations), so UDP
scanning is the one visibility-affecting addition v1 actually ships.

### Evidence Gained

Beyond STANDARD's existing evidence set, the recommended v1 composition
adds: services discovered on non-curated ports (using evidence fields
that already exist — no model change), materially better product/version
accuracy on ambiguous or uncommon services, a fixed and verified path to
UDP/161 reachability (closing a gap ARCH-003 already flagged but never
confirmed fixed), and CIM/WBEM evidence on VMware hosts previously
excluded on cost grounds that DEEP's scope reverses. A confidence-scored
OS guess for non-Windows/non-SMB/RDP devices remains a real, identified
evidence gap this profile could eventually help close, but is not part
of v1 — see Recommendations.

### Overlap With STANDARD

DEEP does not fork discovery into a second, parallel implementation.
Every recommended capability is expressed as this sprint's future
implementation extending the same two-phase shape ADR-001 already
established and the same `STANDARD_ENRICHMENT_SCRIPTS`/
`STANDARD_HOST_ENRICHMENT_SCRIPTS` script set STANDARD already runs —
DEEP's script list is STANDARD's plus one pilot addition, run against a
wider port set with higher version intensity. An engineer reading
`NmapProvider` after DEEP is implemented should see one profile-driven
argument-construction path, not two independent scanning strategies.

### Overlap With Future Authenticated Discovery

None, by design. DISC-001 Finding 6 already established that current
discovery is unauthenticated by design with no credentialed path in
production code, and DISC-001's own Recommendation 5 scoped any future
authenticated capability as "a separate authenticated-discovery profile
as its own architecture-reviewed effort" — not a deeper tier of the
existing FAST/STANDARD/DEEP ladder. This investigation reaffirms that
boundary rather than revisiting it: nothing evaluated below uses
credentials, and nothing recommended for DEEP should be read as a step
toward them. If authenticated discovery is pursued later, it should be
its own mode alongside DEEP, not layered on top of it.

---

## Candidate Capability Assessment

Each candidate is evaluated against this sprint's required dimensions:
Benefits, Cost, Risk, Runtime, False Positive Potential, Evidence Value,
Interaction with STANDARD.

### 1. Expanded TCP Port Coverage

| Dimension | Assessment |
|---|---|
| Benefits | Surfaces services on ports outside the curated 16-port `CLASSIFICATION_PORTS` list — most valuably, management web UIs on nonstandard ports, which the existing `http-title`/`ssl-cert`/`http-auth` scripts already fire against by service-name portrule, not a fixed port list, so a wider `-p` range makes them reach targets they otherwise never see. |
| Cost | The single largest scan-surface increase evaluated. Nmap's well-known "top 1000" port list is the natural, industry-precedented boundary rather than a bespoke number or all 65,535 ports (which would multiply cost again for near-zero marginal yield in typical enterprise environments). |
| Risk | A scan touching ~1,000 ports per host has a materially stronger "port scan" signature to IDS/IPS/NDR tooling than STANDARD's curated 16 — this is DEEP's primary driver of the "louder" expectation set above. |
| Runtime | High relative to STANDARD's port-scan phase; actual enrichment-phase cost (which only runs `-sV`/NSE against *open* ports) scales with yield, not with the port count scanned. |
| False positive potential | None directly — an open port is a fact. Indirect: more open ports found means more chances for `-sV` to misidentify an unusual service, the same accuracy ceiling STANDARD already accepts. |
| Evidence value | High — this is the main value driver of DEEP; every other STANDARD-derived evidence field becomes reachable on any port found, not just the curated 16. |
| Interaction with STANDARD | Purely additive. No new evidence field, no new script — the existing script set simply runs against a wider `-p` argument. |

### 2. Expanded NSE Scripts

| Dimension | Assessment |
|---|---|
| Benefits | A home for ARCH-003's one still-open "pilot, not a commitment" candidate, `sip-methods` — DEEP is exactly the profile a technician opts into for exactly this kind of not-yet-fully-verified evidence. |
| Cost | Low — one additional script name, same integration shape as every prior NSE addition. |
| Risk | Governed by Nmap's own script categorization: this investigation recommends DEEP restrict itself to scripts Nmap tags `safe` (as `http-title`/`ssl-cert`/`http-auth`/`rdp-ntlm-info`/`smb-os-discovery`/`smb-security-mode`/`vmware-version` already are), explicitly excluding `intrusive`/`vuln`/`exploit` categories — consistent with `ENGINEERING.md`'s existing rejection of vulnerability-assessment and aggressive NSE scripts. This is a boundary DEEP should adopt explicitly, not just inherit by accident. |
| Runtime | Low per script; scales with the wider port set from Candidate 1, since `sip-methods` targets SIP ports already in `CLASSIFICATION_PORTS`. |
| False positive potential | Unverified — ARCH-003 explicitly could not confirm `sip-methods`' real-world response reliability without a live device. This is exactly why it's a pilot, not a commitment: observe actual content in DEEP runs before writing any `VoiceVendorRule` matching logic against it. |
| Evidence value | Speculative but plausible (ARCH-003's own characterization) — potentially high if verified, currently unknown. |
| Interaction with STANDARD | Additive only; does not touch any STANDARD script or field. `ssh-hostkey` was considered here and excluded — ARCH-003 already ruled it out of ADR-009's classification-evidence domain entirely (it's a future device-identity/fingerprinting candidate, not classification evidence), and DEEP shouldn't quietly reopen a decision already made. |

### 3. Version Intensity

| Dimension | Assessment |
|---|---|
| Benefits | STANDARD's `--version-light` trades detection depth for speed by trying fewer, more-common-first probes. Raising intensity (Nmap default intensity 7, or `--version-all` for maximum) improves identification of uncommon or ambiguous services `--version-light` misses or mis-guesses. |
| Cost | Low-to-moderate — extra probe attempts only against services `-sV` couldn't confidently identify at low intensity; well-identified common services (http, https, ssh, microsoft-ds) see no added cost. |
| Risk | Low — same probe *types* STANDARD already sends, just more of them; minimal incremental IDS signature beyond what `-sV` already presents. |
| Runtime | Low-to-moderate, concentrated on already-open, already-unusual ports — much cheaper than Candidate 1's blanket surface increase. |
| False positive potential | Lower than STANDARD, not higher — more probes generally *improves* Nmap's own confidence and accuracy for the same field. |
| Evidence value | Medium — sharpens `product`/`version` on the long tail of services STANDARD already tries to identify; doesn't add a new evidence category. |
| Interaction with STANDARD | Pure parameter change to the same `-sV` mechanism STANDARD already uses; no script or field change. |

### 4. OS Fingerprinting (`-O`)

| Dimension | Assessment |
|---|---|
| Benefits | The only candidate evaluated that could populate `Device.operating_system` for devices SMB/RDP identity can never reach — non-Windows hosts: Linux servers, network appliances, printers, embedded/IoT gear. This directly closes the identity gap FEAT-003H/I's SMB/RDP work structurally cannot. |
| Cost | Moderate — a handful of additional crafted probes per host (TCP SYN/ACK sequencing, ICMP echo/timestamp, a closed-UDP-port probe, TCP options ordering), not a large packet volume, but a qualitatively different *kind* of probe than anything STANDARD sends today. |
| Risk | The highest IDS/IPS signature risk evaluated in this report. Crafted, non-standard packet sequences for stack fingerprinting are a textbook reconnaissance signature, more likely to be flagged than either a wide port scan or extra version-detection probes. |
| Runtime | Low-to-moderate per host (a fixed, small probe set), but every host pays it, unlike Candidate 3's yield-concentrated cost. |
| False positive potential | **The highest of any candidate evaluated in this project's history**, structurally, not incidentally. Nmap's OS match is a confidence-scored guess against a fingerprint corpus (`nmap-os-db`), frequently returning multiple candidates or "no exact match." This is the same *epistemic category* the project has already rejected once: favicon hashing was rejected specifically for being a non-deterministic, corpus-matched guess ("conflicts with deterministic-classification philosophy"). The distinction that matters here — the fingerprint corpus is Nmap-maintained, not something NetworkMapper itself curates, unlike the rejected favicon-hash approach — doesn't remove the underlying problem: a confidence percentage is not a fact in the way a protocol-native SMB/RDP field is. |
| Evidence value | Potentially high, but only if treated honestly as heuristic evidence rather than fact. See Recommendation below — this is the report's central judgment call. |
| Interaction with STANDARD | Would require a new evidence shape, not just a new field: a value **and** a confidence score, which has no precedent on `Device` today (every existing field is a bare deterministic string). Fits ADR-009's *field-addition* pattern only if that pairing is treated as a single structured field, not two independent ones inviting drift. |

**Recommendation for `-O` specifically (revised per architecture
review):** defer entirely out of DEEP v1 — evidence-only inclusion
included, not just classification consumption. This investigation's
original position was to include `-O` in v1 as evidence-only (collected
and stored, e.g. a `Device.os_fingerprint_guess` / confidence pair, with
zero rule consuming it until a dedicated future decision), the same
disciplined "producer without consumer" pattern this project has already
used correctly twice (`operating_system`'s multi-sprint dormancy,
`ServiceEvidence.version` since FEAT-003F). Architecture review
determined that even evidence-only collection shouldn't ship inside
DEEP's implementation sprint: `-O` would be the first genuinely
confidence-scored, heuristic evidence category this codebase has ever
stored, and that question — what a confidence-scored value even *is* on
`Device`, and whether the deterministic-evidence principle that sank
favicon hashing extends to storage as well as consumption — deserves its
own dedicated architecture effort rather than being decided as a
sub-clause of DEEP's scope. This is a sequencing refinement, not a
reversal of the analysis above: `-O` remains the one candidate evaluated
with real potential to close the non-Windows identity gap nothing else
in this report reaches, and nothing about this deferral forecloses it —
see Recommendations for the follow-on effort this report now recommends.

### 5. UDP Scanning (`-sU`)

| Dimension | Assessment |
|---|---|
| Benefits | Fixes a gap ARCH-003 already flagged but never confirmed resolved: STANDARD's enrichment command has never included `-sU`, so port 161/UDP (SNMP) — despite being listed in `CLASSIFICATION_PORTS` — has likely never actually been reached by a UDP probe. `ServiceEvidence.protocol` exists specifically to make this gap *visible*, not to imply it's closed. This is the direct prerequisite for ARCH-003's Tier 4 SNMP roadmap item (rated "the highest-ceiling classification candidate evaluated" across the entire investigation series). |
| Cost | UDP scanning is inherently slower than TCP per port — Nmap must wait out a timeout or an ICMP port-unreachable response to infer state, with retransmission on top. |
| Risk | Low-to-moderate — UDP probing is a known, common network operations activity (monitoring tools do this routinely), lower-signature than OS fingerprinting's crafted TCP sequences. |
| Runtime | High per port scanned, but bounded in this recommendation to the one or two UDP ports actually relevant among `CLASSIFICATION_PORTS` (161 today) — not a blanket UDP sweep, mirroring the same curation discipline already applied to TCP. |
| False positive potential | Nmap's UDP scanning has a well-known "open\|filtered" ambiguity (no response can mean either state). `NmapProvider._extract_services()` already only accepts a literal `"open"` state, which structurally excludes this ambiguous case without any new code — a favorable existing safeguard, not a new one this sprint would need to add. |
| Evidence value | High, but only as a *prerequisite* — this candidate by itself only proves reachability; it does not add SNMP evidence (`sysDescr`/`sysObjectID`) itself. |
| Interaction with STANDARD | Additive scan-type change on an already-curated port; adds no new field. Actual SNMP evidence collection is deliberately **not** bundled into this recommendation — see Recommended Next Sprint. |

### 6. VMware (Expanded CIM/WBEM Coverage)

| Dimension | Assessment |
|---|---|
| Benefits | Ports 5988/5989 (CIM/WBEM hardware management) were evaluated and deliberately excluded from `CLASSIFICATION_PORTS` in FEAT-002B specifically because "their lower universality doesn't justify the added scan surface without a specific classification need" under STANDARD's cost discipline. DEEP's entire premise — accepting more scan surface for more evidence on a deliberately chosen scope — directly reverses that cost/benefit calculation. |
| Cost | Low — two additional ports, already-supported script family (`vmware-version`'s portrule already covers VMware-identified services generally). |
| Risk | Low — same operational profile as the already-accepted 902/903 VMware management ports. |
| Runtime | Negligible addition on top of Candidate 1's port expansion. |
| False positive potential | Low — CIM/WBEM presence is a structural fact (port open, service identifiable), not a heuristic guess. |
| Evidence value | Low-to-medium — legacy and increasingly disabled on modern ESXi per FEAT-002B's own original assessment, but free to include once DEEP's port budget already accepts a wider surface. |
| Interaction with STANDARD | Additive port-list-only change; no new field or script beyond what STANDARD already has for VMware identification. |

### 7. LLDP/CDP

| Dimension | Assessment |
|---|---|
| Benefits | Neighbor/topology/relationship data — genuinely valuable, but categorically different in kind from every other candidate here. |
| Cost | Cannot be achieved by tuning `NmapProvider`'s scan arguments at all. LLDP/CDP are link-layer multicast protocols; `NmapProvider`'s IP-based TCP/UDP scanning model has no path to observing them, confirmed unchanged from ARCH-003/FEAT-003E. |
| Risk | N/A for DEEP specifically — the mechanism required (passive L2 capture, or an SNMP-MIB-dependent path) is a different collection technique needing its own risk assessment, not a DEEP scan-argument decision. |
| Runtime | N/A |
| False positive potential | N/A |
| Evidence value | High in principle, but `NetworkGraph` has no representation for device-to-device relationship data today — even a working collection mechanism has nowhere to write its result. |
| Interaction with STANDARD | None possible under the current architecture. |

**Recommendation:** exclude from DEEP entirely. This reconfirms
ARCH-003/FEAT-003E's finding without new information: LLDP/CDP requires
a new `DiscoveryProvider` and a new topology/relationship ADR,
regardless of how "deep" a Nmap-based profile goes. DEEP cannot absorb
this by definition — it is a Nmap-profile question, and LLDP/CDP is not
one. The dedicated future architecture investigation ARCH-003 already
recommended for this remains the correct path, independent of DEEP.

### 8. SNMP (`sysDescr`/`sysObjectID` Collection)

| Dimension | Assessment |
|---|---|
| Benefits | ARCH-003's own top-rated candidate: `sysObjectID` is a formally vendor-registered identifier — the single most deterministic device-identity field evaluated across this project's entire investigation history, when reachable. |
| Cost | Blocked on Candidate 5 (`-sU`) actually landing first; on top of that, requires a community-string list (starting with the ubiquitous default, `"public"`) and the relevant SNMP NSE scripts. |
| Risk | Community-string probing — even read-only, even the well-known default string — reads as active reconnaissance to some monitoring tooling, distinct from (and arguably more visible than) plain UDP port-state detection alone. |
| Runtime | Medium — variable by environment; many modern enterprise networks disable public SNMP entirely, so yield (and therefore effective cost-per-result) varies widely, as ARCH-003 already noted. |
| False positive potential | Very low for `sysObjectID` specifically (a structured, vendor-registered numeric OID); `sysDescr` is free text requiring the same substring-matching approach already used for `http_title`/`product` — a familiar, already-accepted risk profile. |
| Evidence value | Very high — reconfirmed from ARCH-003 without new information changing that assessment. |
| Interaction with STANDARD | Would add new `Device`-level fields, fitting ADR-009's existing incremental pattern exactly (no new ADR needed for these two fields specifically, per ARCH-003 Section 6 — distinct from `snmp-interfaces`/`ifTable` metadata, which does require one and remains out of scope here as before). |

**Recommendation:** do not bundle into DEEP v1. This is a dependent,
not a peer, of Candidate 5 — implementing it in the same sprint as the
`-sU` fix would conflate "make UDP reachable" with "collect SNMP
identity evidence," two decisions worth reviewing independently. Land
DEEP's `-sU` capability first, verify it actually reaches 161/UDP in a
real environment, then scope SNMP evidence collection as its own
immediate follow-on sprint — exactly the sequencing ARCH-003 already
recommended (Tier 4), now with a concrete prerequisite (this sprint's
DEEP profile) instead of an open-ended one.

### 9. Timeout Tuning

| Dimension | Assessment |
|---|---|
| Benefits | Reduces false negatives (missed services/hosts) on slow, congested, or WAN-connected segments — directly useful for DEEP's "spend more time to get a complete answer" premise. |
| Cost | Runtime increase, potentially substantial in the worst case (unresponsive hosts each consuming their full extended timeout). |
| Risk | **Lower** than STANDARD's default timing in one specific sense: slower, more patient scanning is less likely to trip threshold/rate-based IDS alerts than a fast, bursty scan — the one candidate evaluated where a DEEP-specific change plausibly *reduces* detection risk rather than raising it, even though it costs more time. |
| Runtime | Directly proportional to how much patience is added; the report recommends a modest increase (e.g., extended `--host-timeout`), not an extreme one, to avoid DEEP runs stalling indefinitely on a handful of unresponsive hosts. |
| False positive potential | Reduces false negatives; does not introduce new false positives of its own. |
| Evidence value | Indirect — improves completeness/reliability of evidence STANDARD already collects, rather than adding a new evidence type. |
| Interaction with STANDARD | A tuning parameter only; no field, script, or model change. |

### 10. Retry Behavior

| Dimension | Assessment |
|---|---|
| Benefits | More probe retransmissions reduce false negatives from packet loss, complementary to Candidate 9. |
| Cost | Runtime increase proportional to retry count, concentrated on unresponsive or lossy probes. |
| Risk | Negligible incremental IDS signature beyond ordinary TCP retransmission behavior. |
| Runtime | Low-to-moderate, smaller in practice than Candidate 9's timeout extension. |
| False positive potential | Reduces false negatives; no new false positives. |
| Evidence value | Same indirect completeness/reliability role as Candidate 9. |
| Interaction with STANDARD | Tuning parameter only; tightly coupled to Candidate 9 and best decided together, not independently, when DEEP is implemented. |

---

## Recommended DEEP Profile Composition

DEEP is defined as STANDARD's two-phase structure (ADR-001, unchanged),
extended along the following axes. Nothing below requires forking
`NmapProvider`'s shape into a second code path — every item is a
parameter or list extension to the same enrichment-argument construction
STANDARD already uses.

**Include, v1:**

1. Expanded TCP port coverage — Nmap's standard "top 1000" ports,
   replacing the curated 16-port list for DEEP specifically (STANDARD's
   curated list is unaffected).
2. STANDARD's full existing script set, run unchanged against the wider
   port range from (1) — no new script required for this alone.
3. `sip-methods`, as DEEP's designated pilot lane for ARCH-003's
   already-recommended, not-yet-verified SIP vendor/model signal.
4. Higher `-sV` version intensity (Nmap default intensity, or
   `--version-all`) in place of STANDARD's `--version-light`.
5. `-sU` against the currently UDP-relevant curated port (161 today) —
   transport-layer fix only, no SNMP evidence collection bundled.
6. VMware CIM/WBEM ports (5988/5989) added to DEEP's port set.
7. Modest timeout/retry patience increase (Candidates 9–10), tuned
   together, not independently.

**Explicitly excluded from DEEP v1:**

- **OS fingerprinting (`-O`)** — deferred per architecture review, in
  full (evidence-only collection included, not just classification
  consumption). `-O` would be this codebase's first confidence-scored,
  heuristic evidence category, and that representational question
  deserves its own dedicated architecture effort rather than riding
  along inside DEEP's implementation sprint. See Candidate 4's
  Recommendation and Recommendations below for the follow-on effort.
- LLDP/CDP — requires a new `DiscoveryProvider` and topology ADR;
  categorically not a Nmap-profile question. Redirect to the dedicated
  future architecture investigation ARCH-003 already recommended.
- SNMP `sysDescr`/`sysObjectID` evidence collection — a dependent
  follow-on sprint once (5) is implemented and verified, not a DEEP-v1
  feature. Bundling it here would conflate two independent decisions.
- `ssh-hostkey` and any other classification-irrelevant identity/
  fingerprinting candidate ARCH-003 already routed to a future
  device-identity capability (ROADMAP Phase 9) — DEEP is not the place
  to reopen that routing decision.
- Any `intrusive`/`vuln`/`exploit`-category NSE script — DEEP inherits
  STANDARD's (and `ENGINEERING.md`'s) product-philosophy boundary
  against aggressive/vulnerability-assessment scanning; this boundary
  should be adopted explicitly, not left implicit.
- Any authenticated mechanism (credentialed WMI/SSH/WinRM/SNMPv3-real-
  community, etc.) — out of scope for DEEP entirely; a future
  authenticated profile is a separate, independently-reviewed effort.

This composition keeps DEEP v1 coherent and reviewable as a single
implementation sprint, gives operators a real, honestly-described reason
to choose it over STANDARD, and defers three things — OS fingerprinting,
SNMP data, and any authenticated mechanism — for reasons specific to
each, not as a blanket "everything else later."

---

## Findings

1. DEEP's identity gap (behaving identically to FAST) is a naming/scope
   gap, not a technical blocker — every capability recommended above is
   achievable by extending `NmapProvider`'s existing profile-driven
   argument construction, with zero new `DiscoveryProvider`.
2. OS fingerprinting is the one candidate that meaningfully closes
   NetworkMapper's non-Windows identity gap, and also the one candidate
   most in tension with the project's stated deterministic-classification
   philosophy — the first confidence-scored, heuristic evidence category
   this codebase would ever store. Per architecture review, that tension
   is resolved by deferring it out of DEEP entirely (not just out of
   classification) into its own dedicated future architecture effort,
   rather than folding a new evidence-representation question into a
   scan-profile sprint.
3. UDP scanning and SNMP evidence collection are two separate decisions,
   not one — ARCH-003 already identified SNMP as a Tier 4 candidate
   blocked on a `-sU` fix; this investigation confirms that dependency
   still holds and recommends sequencing them as two sprints, not one.
4. LLDP/CDP remains, as it has since FEAT-003E/ARCH-003, the one
   capability requiring genuinely new architecture (provider + topology
   model) rather than a deeper scan profile. No new information in this
   investigation changes that.
5. Nmap's own `safe`/`intrusive`/`vuln` script categorization is a
   ready-made, already-authoritative boundary for what DEEP may ever
   include — adopting it explicitly avoids relitigating
   `ENGINEERING.md`'s existing rejection of aggressive/vulnerability
   scanning on a per-script basis in every future sprint.

## Recommendations

1. Implement DEEP per the Recommended DEEP Profile Composition above
   (v1 scope, OS fingerprinting excluded), as its own sprint following
   architecture approval of this report.
2. Extend OBS-001's `PROFILE_MESSAGES`/diagnostics pattern to describe
   DEEP honestly once implemented — "broader coverage, higher runtime,
   still unauthenticated," not "more thorough" alone — so operator
   expectations (per this report's Framing section) are visible in the
   tool itself, not only in this document.
3. Sequence SNMP evidence collection as an immediate follow-on sprint
   after DEEP ships and its `-sU` capability is verified against a real
   environment — not bundled into DEEP's implementation sprint.
4. Scope a dedicated future architecture effort on heuristic,
   confidence-scored evidence generally, with OS fingerprinting (`-O`)
   as its first candidate — per architecture review, this should
   establish how (or whether) a value+confidence pair is represented on
   `Device` at all, independent of any specific scan profile, before
   `-O` is added to DEEP or anywhere else.
5. Keep LLDP/CDP and any authenticated-discovery capability off DEEP's
   roadmap entirely; both remain correctly scoped as separate,
   independently-reviewed future efforts.
6. Adopt Nmap's `safe` script category as an explicit, documented
   constraint on any future DEEP script addition, not just an implicit
   convention inherited from STANDARD's current choices.

## Risks

- **Operator misunderstanding risk:** without the messaging update in
  Recommendation 2, an operator could reach for DEEP as a faster path to
  "more evidence" without understanding the runtime/visibility tradeoff,
  defeating the bounded-scope use case this report designs DEEP around.
- **Evidence misuse risk:** if OS fingerprint data is ever added to any
  profile — DEEP or otherwise — without the dedicated future
  architecture effort Recommendation 4 requires, it would quietly
  reintroduce exactly the non-deterministic evidence problem favicon
  hashing was rejected to avoid, this time without even the evidence-
  only safeguard this investigation originally proposed.
- **IDS/IPS visibility risk:** DEEP v1's port-range expansion is a real,
  qualitatively higher-signature change versus STANDARD; running DEEP
  against a full enterprise network rather than a bounded scope could
  generate security-tooling alerts a technician isn't expecting.
- **Sequencing risk:** if a future sprint implements SNMP evidence
  collection without first verifying DEEP's `-sU` fix actually reaches
  161/UDP in a live environment, it would repeat the same
  "unverified inference" gap ARCH-003 already flagged once.

## Assumptions

- Nmap's own script category metadata (`safe`/`intrusive`/`vuln`) is
  accurate and can be relied upon as a filtering boundary without
  NetworkMapper needing to independently re-vet each script.
- "Top 1000" ports is an acceptable default breadth for DEEP; this
  investigation did not evaluate intermediate options (e.g., top 100,
  top 5000) in detail, since no benchmarking infrastructure exists to
  compare their yield/cost tradeoff empirically.
- Runtime and network-impact characterizations throughout this report
  are qualitative engineering judgment based on each capability's Nmap
  mechanics, not measured benchmarks — no code was written or executed
  for this investigation, per its explicit "do not implement" scope.

## ADR Considerations

No new ADR is required to define or implement DEEP's recommended v1
scope — every included capability is a scan-argument extension or an
incremental named field, both patterns ADR-009 already covers.

OS fingerprinting is deferred out of DEEP entirely, per architecture
review, precisely because it may trigger this question: whether a
confidence-scored value pair is a new representational pattern requiring
its own ADR-fit assessment, separate from the plain incremental-field
pattern every other `Device`/`ServiceEvidence` field has used to date.
That determination is left to the dedicated future architecture effort
Recommendation 4 scopes, not decided here and not a prerequisite for
implementing DEEP v1.

Previously identified future ADR triggers (SNMP interface/`ifTable`
metadata, LLDP/CDP's topology model) are unaffected and unchanged by
this investigation.
