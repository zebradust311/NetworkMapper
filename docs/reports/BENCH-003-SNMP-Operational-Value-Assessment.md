# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — this is a measurement and analysis sprint. No
discovery, enrichment, classification, reporting, or telemetry behavior
was changed. Section 8 (Future Work) identifies candidates for future
architecture/engineering review — most notably, a real gap this
benchmark discovered in report surfacing (Section 8, item 1) — but does
not decide any of them.

Recommended Next Sprint:
No single sprint is pre-selected. Section 8 names the strongest
candidate with supporting evidence: closing the gap this benchmark
found between "SNMP evidence is collected and persisted" and "SNMP
evidence is visible in the Markdown/CSV report a technician hands to a
customer" — currently zero, confirmed by direct code inspection, not
inference. This was an open question ARCH-012 itself flagged and left
unresolved (Open Question 5); this benchmark is the first sprint to
confirm, empirically, that it went unresolved through FEAT-005 and
RULE-004 both.

Wait for engineering review before implementing anything here.

---

## Summary

This benchmark measured FEAT-005 (SNMP collection) and RULE-004 (SNMP
classification consumption) end-to-end, using the same two-track
methodology BENCH-002 established (no live, diverse, multi-device
network is available in this environment to scan — see Methodology),
extended with a real, working SNMPv2c agent for this sprint specifically
so the "responds" case could be measured directly rather than estimated.

Headline findings:

1. **SNMP's runtime cost is overwhelmingly dominated by hosts that don't
   respond, not hosts that do** — confirmed with real wire-protocol
   measurements of both cases for the first time. A responding host costs
   **~0.15–0.27s**; a non-responding host costs **~3.3–3.4s** (default
   `timeout=1.5s, retries=1`) — a **~13–20×** cost multiplier for exactly
   the scenario ARCH-003/ARCH-012 already flagged as the common case
   ("many modern enterprise networks disable public SNMP entirely").
2. **In this benchmark's realistic 12-device fixture, SNMP evidence
   changed zero classifications.** All five SNMP-responding devices in
   that fixture already had stronger, higher-precedence evidence (vendor,
   product string, or HTTP authentication realm) that resolved their
   classification before RULE-004's SNMP corroboration was ever reached
   — confirmed directly from unchanged `RuleResult.reason` text, not
   inferred. This is the "corroborates, does not override" design
   working exactly as intended, but it means SNMP's classification
   payoff in an already-STANDARD-enriched environment is narrower than
   RULE-004's "five rules consume it" framing might suggest.
3. **A separately-constructed device demonstrates the mechanism does
   work when its designed-for scenario actually occurs**: an unbranded
   device with no Nmap-derived vendor, hostname, or service evidence at
   all correctly resolved from `UNKNOWN` to `SWITCH` using SNMP `sysDescr`
   evidence alone, with a fully traceable reason string. This is real,
   demonstrated value — just conditional on a specific evidence gap, not
   a broad classification-rate improvement.
4. **SNMP evidence is not visible anywhere in the exported Markdown or
   CSV report.** Confirmed by direct source inspection of both
   exporters: zero references to any `snmp_sys_*` `Device` field in
   either. The evidence is correctly collected and correctly persisted
   in the `.nmproj` project file, but a technician handing a customer
   the Markdown report today gets none of it — undermining half of
   ARCH-012's own stated value case for collecting `sysUpTime`/
   `sysContact`/`sysLocation` at all ("direct value to the Customer/
   Account Manager personas"). This was an open question ARCH-012
   flagged and left unresolved (Open Question 5); it is still
   unresolved.

---

## Methodology

**Two complementary tracks, for the same reason BENCH-002 used them**:
no live, diverse, multi-device network is available in this environment
to scan, so a single approach would force a choice between real timing
data with no device diversity, or device diversity with no real timing
data.

### Track A — Real timing (localhost)

Real, unmodified `NmapProvider`/`SnmpEnrichmentProvider`/`PysnmpClient`
were invoked against `127.0.0.1` (a safe, self-owned, authorized target
— the same boundary BENCH-002 established and this benchmark did not
widen), wired to the real OBS-002 `RuntimeEventBus`/
`RuntimeTelemetryRecorder` so phase durations are read from the same
telemetry production code uses, not hand-timed.

**New for this sprint**: BENCH-002 had no way to measure a real SNMP
"responds" case (no SNMP agent was available). This benchmark stood up a
minimal, throwaway SNMPv2c agent using `pysnmp`'s own command-responder
API (`pysnmp.entity.rfc3413.cmdrsp`), bound to `127.0.0.1:161`,
returning the six real MIB-2 system-group scalars. This is test
infrastructure only — not part of the product, not committed, discarded
after measurement — built specifically because ARCH-012's own Testing
Strategy named a real/simulated SNMP responder as "valuable future
integration-test infrastructure...explicitly not added" in FEAT-005;
this benchmark needed it to answer "how much does SNMP cost when it
works," which no prior sprint had measured.

### Track B — Controlled synthetic multi-device fixture

BENCH-002's own fixture-generating script was not committed to the
repository (`Production Code Modified: No` — it was ad hoc, like this
one), so this benchmark reconstructed a fixture modeled on BENCH-002's
own described 12-device roster (a domain controller, a core switch, a
printer, a VoIP phone, a SonicWall firewall, an ESXi host, a Ubiquiti
access point, a Dell workstation, an RDP-reachable app server, a
vendor-ambiguous "mystery box," a NAS appliance, and a generic internal
web app) — not a byte-for-byte reuse, stated plainly rather than implied
as identical.

**One deliberate methodology difference from BENCH-002's own Track B**:
BENCH-002 mocked `nmap.PortScanner.scan()` and let `NmapProvider`'s own
extraction code build `Device` objects. This benchmark instead starts
from already-built `Device` objects representing STANDARD's typical
output directly. This is a scoping decision, not a shortcut: Nmap's
extraction logic is unaffected by SNMP and is already covered by
FEAT-003's/`NmapProvider`'s own test suite; this benchmark's actual
target is SNMP's incremental contribution on top of an
already-STANDARD-enriched device set, and re-deriving Nmap's raw
scan-result dict format would add risk (a subtly wrong hand-authored
fixture) without adding information relevant to this sprint's question.
Everything downstream of that starting point is real: the real
`DiscoveryEngine` orchestration, the real `SnmpEnrichmentProvider.enrich()`
(with only `SnmpClient` — FEAT-005's own purpose-built dependency-
injection seam for exactly this — mocked with fixed per-host responses,
identical in spirit to BENCH-002's "mock only the wire call" approach),
and the real `DeviceClassifier`.

**One device added beyond the 12-device roster, clearly separated in
every table below**: `172.16.100.99`, constructed specifically to test
the scenario RULE-004 was built for — a device with no Nmap-derived
vendor, hostname, or service evidence at all, reachable only via SNMP.
BENCH-002's own 12-device mix does not happen to contain such a device
(every device in it has at least a vendor or a diagnostic hostname), so
without this addition, this benchmark could not honestly answer "does
the mechanism work when it's supposed to" — only "does it happen to fire
in this particular mix" (Finding 2's honest, real answer: no).

**SNMP response modeling**: of the 12-roster devices, the five
"infrastructure-shaped" ones (switch, printer, firewall, hypervisor
host, NAS) were modeled as SNMP-responsive, with `sysDescr` text
mirroring ARCH-012's own cited examples; the other seven (domain
controller, phone, access point, workstation, RDP app server, mystery
box, generic web app) were modeled as non-responsive. This deliberately
mirrors RULE-004's own scope of consumption (the same five device
categories) — **it is a benchmark construction choice to exercise the
capability being measured, not a claim about real-world SNMP adoption
rates**, which this benchmark has no field data to support. This is
stated as a limitation, not smoothed over — see Section 8.

`sysName` was deliberately omitted from every Track B mocked response.
Track A's real-agent run already directly verified the `sysName` →
`hostname` fallback mechanism working correctly end-to-end against real
wire traffic (see Runtime Comparison); repeating it in Track B's
already-hostname-populated fixture would exercise the same code path a
second time without adding information.

---

## Runtime Comparison

### Track A — real, localhost

| Measurement | Result |
|---|---:|
| STANDARD, Host Discovery (1 host) | 0.26s |
| STANDARD, Service Enrichment (1 host) | 9.12s |
| STANDARD total (1 host) | 9.38s |
| SNMP, 1 non-responding host (default timeout/retries) | 3.44s |
| SNMP, 3 non-responding hosts, serial | 9.77s (≈3.26s/host) |
| SNMP, 1 responding host, single query (avg of 5 real queries) | 0.169s |
| SNMP, 5 responding hosts via full provider | 1.35s (≈0.27s/host) |

The STANDARD numbers reproduce BENCH-002's own measurement closely
(0.21s/9.00s/9.4s then vs. 0.26s/9.12s/9.38s now) — expected, since
`NmapProvider` was not touched by FEAT-005 or RULE-004, and confirms
this benchmark's methodology is directly comparable to BENCH-002's.

**SNMP's real cost is asymmetric by roughly an order of magnitude**,
confirmed with real traffic on both sides for the first time: a
responding host (~0.15–0.27s: one UDP round trip, exactly as ARCH-012's
"single `GetRequest` PDU" design predicted) costs **~13–20× less** than
a non-responding host (~3.3–3.4s: full timeout × (1 initial + 1 retry)
under the default `DEFAULT_TIMEOUT_SECONDS=1.5`/`DEFAULT_RETRIES=1`).
Serial execution was confirmed directly, not assumed: 3 non-responding
hosts took 9.77s (≈3× the single-host cost), matching
`SnmpEnrichmentProvider`'s documented serial-per-host design exactly.

On this Windows environment specifically, a closed/non-listening
UDP/161 did **not** produce a fast ICMP-based rejection — every attempt
consumed the full configured timeout, which is the "silently firewalled"
behavior ARCH-012's Performance Considerations anticipated as the
realistic case, not the exception. This is a real, environment-specific
finding worth stating plainly: technicians should not expect a
fast-fail when SNMP is unreachable.

**Report Generation** (Track B's 13-device output, both scenarios):
STANDARD 0.0051s total (CSV + Markdown), STANDARD+SNMP 0.0025s total —
both negligible and within measurement noise of each other, confirming
Report Generation cost is unaffected by SNMP evidence at this scale,
consistent with BENCH-002's own ~0.00s finding and with RULE-004's
confirmation that no exporter code path was touched.

### Track B — synthetic fixture (CPU-only phases)

| Phase | STANDARD | STANDARD + SNMP |
|---|---:|---:|
| Classification (13 devices) | 0.0003s | 0.0002s |
| SNMP Enrichment (13 devices, mocked client) | — | 0.0001s |

As in BENCH-002, these numbers show real, if tiny, CPU cost only — the
mocked `SnmpClient` returns in microseconds, so this is **not** a
network-cost measurement. Track A's real numbers above are the load-
bearing runtime figures for this benchmark's Operational Assessment.

---

## Coverage Metrics

13-device Track B fixture (12-device roster + 1 addendum device,
reported combined; the 12-roster-only subset is called out where it
differs):

| Metric | Value |
|---|---:|
| Hosts discovered | 13 |
| Hosts eligible for SNMP | 13 (all — no separate eligibility filter exists; every discovered device is queried) |
| SNMP attempts | 13 |
| SNMP responses | 6 (5 of the 12-roster's infrastructure devices + the addendum device) |
| Timeouts | 7 (all from the 12-device roster) |
| Authentication failures | **Not separately measurable** — see below |
| Unreachable UDP/161 | **Not separately measurable** — see below |

**"Authentication failures" and "unreachable UDP/161" cannot be
distinguished from a timeout in this implementation, by design.**
Confirmed directly from `snmp_client.py`: an SNMPv2c `error_indication`
(covering a timeout, an unreachable host, and an incorrect community
string alike) is uniformly recorded as `failure_reason="timeout"`, with
a code comment stating why: "SNMPv2c has no authentication-failure
response." This is not a gap in this benchmark's measurement — it is a
real, correct property of the shipped implementation, exactly as
ARCH-012's Failure Model specified it should be, and this benchmark is
the first to confirm the three categories the sprint's own Test Matrix
asks for are, in fact, one category in production.

---

## Evidence Yield

Across the 6 SNMP-responding devices:

| Field | Hosts producing it | Notes |
|---|---:|---|
| `sysDescr` | 6 / 6 | Every responder |
| `sysObjectID` | 6 / 6 | Every responder |
| `sysUpTime` | 6 / 6 | Every responder |
| `sysContact` | 2 / 6 | Only where modeled as administrator-configured (fw-01, esxi-01) |
| `sysLocation` | 3 / 6 | sw-core-01, fw-01, esxi-01 |
| `sysName` | 0 / 6 (modeled) | Deliberately omitted from Track B — see Methodology; verified separately and directly in Track A (below) |

**Evidence added**: `snmp_sys_descr`/`snmp_sys_object_id`/`snmp_sys_uptime`
for all 6 responders (previously `None`, now populated); `snmp_sys_contact`
for 2; `snmp_sys_location` for 3.

**Evidence unchanged**: `hostname` for all 13 devices in Track B — every
responder already had a hostname from Nmap, so the fallback-only
`sysName` merge correctly never overwrote anything (consistent with
ADR-010's fallback-only merge rule). This mechanism was verified
working for real in Track A: querying the live test agent with a device
that had no prior hostname correctly set `device.hostname` to the
agent's `sysName` value (`"sw-core-01"`), confirmed by direct inspection
of the resulting `Device` object, not just by the existing unit test
suite.

**Evidence unavailable**: `sysContact` for 4 of 6 responders + all 7
non-responders (11 of 13 total); `sysLocation` for 3 of 6 responders +
all 7 non-responders (10 of 13 total); everything for the 7 timed-out
hosts. This mirrors ARCH-012's own framing of `sysContact`/`sysLocation`
as "administrator-entered free text" — genuinely often blank in the
field, not just in this fixture.

---

## Classification Improvements

**12-device roster (BENCH-002-modeled) — zero classification changes.**
`UNKNOWN` before: 2 (`mystery-box-01`, `web-app-01`, given RULE-003
already resolved `netgear-nas-01` independent of SNMP). `UNKNOWN` after:
**2 — unchanged**. Zero devices reclassified. Zero `RuleResult.reason`
strings changed, confirmed by direct text comparison, not inference —
every one of the 5 SNMP-responding devices already had a higher-
precedence match:

| Device | Pre-existing evidence that already resolved it | Where SNMP evidence was reached in the priority chain |
|---|---|---|
| sw-core-01 | Hostname + management port (a code path that never consults `snmp_sys_descr` at all) | Never — `SwitchVendorRule`'s identifier tier requires `"procurve"`/`"edgeswitch"`; its `sysDescr` ("Cisco IOS Software...") doesn't contain either |
| printer-01 | `vendor="HP"` (checked before the identifier tier even runs) | Never reached |
| fw-01 | `vendor="SonicWall"` (checked before the identifier tier even runs) | Never reached |
| esxi-01 | Service product string `"VMware ESXi Server httpd"` (checked earlier in `first_matching_identifier`'s priority chain than `snmp_sys_descr`) | Reached internally, but a stronger match already returned first |
| netgear-nas-01 | HTTP authentication realm `"NETGEAR ReadyNAS"` (checked earlier in the same priority chain) | Reached internally, but a stronger match already returned first |

This is **"SNMP evidence corroborates, it does not override" working
exactly as designed** — not a defect. But it is also the honest,
measured answer to "how many devices actually benefit," for this
particular, realistic device mix: none, at the classification layer.

**Addendum device — one clean, fully explainable reclassification.**
`172.16.100.99` (no vendor, no hostname, no service evidence at all)
went from `UNKNOWN` to `SWITCH`, with reason: *"Detected SNMP sysDescr
'HP ProCurve Switch 2530-24G, revision Y.12.03' matched known switch
identifier."* Every classification change in this benchmark is
explainable — there was exactly one, and its reason string names the
exact evidence value and the exact keyword that matched, satisfying the
sprint's "verify every classification change is explainable" requirement
directly.

**Combined 13-device total**: `UNKNOWN` before 3, after 2.

**"Strengthened classifications" (reason text enriched without a type
change): zero**, in this fixture — confirmed directly, not assumed.
Every one of the 5 responders' reason strings were byte-identical before
and after SNMP enrichment, for the precedence reasons in the table
above. This is a real, if slightly counterintuitive, finding: RULE-004's
corroboration mechanism only becomes *visible* in a report's reason text
when it is the **first-priority** matching evidence found, and in an
already-STANDARD-enriched environment, vendor/product/HTTP evidence is
very often already first in that priority chain.

---

## Knowledge Opportunities

Documented only — no rule is proposed or implied by any of these, per
this sprint's explicit instruction.

- **`sysObjectID` values observed in this fixture** (illustrative,
  synthetic — not field-corroborated): `1.3.6.1.4.1.9.1.516` (Cisco,
  enterprise 9), `1.3.6.1.4.1.11.2.3.9.1` (HP, enterprise 11 —
  printer), `1.3.6.1.4.1.11.2.3.7.11.108` (HP, enterprise 11 — switch),
  `1.3.6.1.4.1.8741.1` (SonicWALL), `1.3.6.1.4.1.6876.4.1` (VMware),
  `1.3.6.1.4.1.4526.100.2` (Netgear). **Worth noting concretely**: this
  fixture's two HP devices (a LaserJet printer and a ProCurve switch)
  share the same top-level enterprise number (11) but diverge at the
  next sub-OID level. This is a direct, concrete illustration of why
  ARCH-012/RULE-004's "no enterprise-number-only OID interpretation, no
  embedded vendor database" caution is correct, not merely cautious — a
  shallow enterprise-number lookup would conflate these two
  unrelated device types.
- **Recurring `sysDescr` shape**: every modeled responder's `sysDescr`
  followed a `"<Vendor/Product> <Model>, <Version/Firmware string>"`
  pattern, consistent with ARCH-012's own cited examples. Reconfirms
  (does not newly discover) the free-text-banner assumption RULE-004's
  keyword-matching approach depends on.
- **Cisco `sysDescr` text is collected but structurally unreachable by
  RULE-004's own design, and this fixture makes the consequence
  concrete.** `sw-core-01`'s `sysDescr` ("Cisco IOS Software, C2960...")
  is exactly the ARCH-012-cited example switch text, yet it has zero
  classification effect — not because the evidence is absent, but
  because RULE-004 deliberately excluded a bare `"cisco"` `sysDescr`
  trigger (collision risk with phones/APs/firewalls, documented in
  `switch_vendor_rule.py`). This means a real Cisco-manufactured switch
  reachable *only* via SNMP (no hostname hint, no open management port
  visible to the scanner) — the same shape of gap this benchmark's
  addendum device fills for HP ProCurve — would **not** be resolved by
  the current implementation, unlike the ProCurve case. Worth recording
  as a known, deliberate boundary rather than rediscovering it from
  scratch in a future sprint: closing it would require either a
  narrower Cisco-switch-specific keyword (e.g. a literal `"ios
  software"` or model-family string, not bare `"cisco"`) or a
  cross-rule precedence decision this sprint's scope does not cover.

---

## Operational Assessment

**How much additional runtime does SNMP introduce?** Dominated
overwhelmingly by non-responding hosts: **~3.3–3.4s per non-responding
host** (serial, default settings) vs. **~0.15–0.27s per responding
host** — a ~13–20× multiplier. For a subnet where SNMP is mostly
disabled (ARCH-003's own "common case" framing), the SNMP phase's cost
approaches `hosts_discovered × ~3.3s`, additive on top of STANDARD's own
Service Enrichment cost (~9s/host from Track A). For a 50-host subnet
with, say, 10 SNMP-responsive hosts, that's roughly `(40 × 3.3s) + (10 ×
0.2s) ≈ 134s` (~2.2 minutes) for the SNMP phase alone — a real, non-
trivial addition, though smaller in absolute terms than STANDARD's own
Service Enrichment phase at the same host count.

**How many devices actually benefit?** At the **classification** layer,
in this benchmark's realistic mix: zero of twelve. Real benefit was
demonstrated only for a device shape STANDARD's other evidence sources
structurally cannot identify (no vendor, no hostname, no reachable
management port) — a real, narrow case, not a broad one. At the
**evidence-collection** layer, 6 of 13 devices gained real, correctly-
merged data — but see Finding 4: that data does not currently reach the
Markdown or CSV report a technician would hand to a customer, only the
`.nmproj` project file and (transiently, at the terminal) the CLI's SNMP
Diagnostics block.

**Would an onsite technician enable `--snmp`?** Conditionally, not by
default. The cost is real and worst-case-dominated exactly as ARCH-003/
ARCH-012 predicted (now measured, not just anticipated); the
classification payoff is narrow and conditional; and the documentation
payoff — the case ARCH-012 itself leaned on to justify collecting
`sysUpTime`/`sysContact`/`sysLocation` at all — is not currently
realized in the deliverable report. None of this means SNMP has no
value (the addendum device shows it genuinely does, in its designed-for
case); it means the value is narrower and more conditional than "SNMP
support is complete" might suggest on its own.

**Under what circumstances?**
- A technician suspects unbranded/unidentifiable infrastructure devices
  are present (spoofed/randomized MACs defeating vendor lookup,
  management ports firewalled from the scanner) — this benchmark
  directly demonstrated real value here.
- SNMP is known or likely to be enabled on the target network (e.g., a
  recurring MSP engagement with prior environment knowledge), reducing
  the non-responding-host cost penalty that otherwise dominates.
- The technician is prepared to consult the `.nmproj` file directly for
  `sysContact`/`sysLocation`/`sysUptime` detail, since today's Markdown/
  CSV report won't show it.

**Would the recommendation change by environment size?**

| Environment | Assessment |
|---|---|
| Small office | Skip by default. Lowest expected SNMP response rate (BENCH-002's own homelab/small_office benchmark fixtures carry no SNMP evidence at all); cost is almost entirely the non-responding-host penalty with little payoff. |
| Medium business | Plausible targeted candidate — closer to this benchmark's own fixture assumption (some managed switches/firewalls). Recommend targeting hosts STANDARD alone leaves `UNKNOWN` or vendor-ambiguous, not a blanket default. |
| Enterprise | SNMP-managed infrastructure is more common, but subnet sizes are larger, and the serial, timeout-dominated cost model compounds across more silent hosts. Recommend the same "targeted escalation, not blanket sweep" framing BENCH-002 already established for DEEP — a specific subnet or device cluster, not a full enterprise sweep. |
| Datacenter | Plausibly the most favorable cost/benefit ratio (SNMP is commonly enabled on managed switches/PDUs/hypervisor hosts in this environment type) — but this benchmark has **no datacenter-shaped fixture or field data** to substantiate that directly. Flagged as a plausible, evidence-gated hypothesis for future validation, not a claim this benchmark can support. |

---

## Future Work

1. **Close the report-surfacing gap this benchmark found (Finding 4).**
   `MarkdownExporter`/`CsvExporter` reference zero `snmp_sys_*` fields
   today — confirmed by direct source inspection, not inference. This
   was ARCH-012's own Open Question 5 ("Should the Markdown/CSV report
   surface SNMP evidence?"), left unresolved through FEAT-005 and
   RULE-004 both. This is the single most concrete, evidence-backed
   candidate this benchmark surfaced: without it, the documentation/
   inventory value case ARCH-012 made for `sysUpTime`/`sysContact`/
   `sysLocation` is currently unrealized for any report a technician
   actually delivers. Squarely a reporting-design decision — out of this
   sprint's own scope ("Do not modify reporting") — but now backed by a
   direct measurement rather than a speculative open question.
2. **A narrower, evidence-gated Cisco-switch `sysDescr` keyword**,
   specifically scoped to avoid the phone/AP/firewall collision risk
   RULE-004 already identified (e.g. a literal `"ios software"` or
   model-family substring, not bare `"cisco"`) — motivated directly by
   this benchmark's Knowledge Opportunities finding that Cisco `sysDescr`
   text is currently the least-reachable of RULE-004's five categories,
   not a hypothetical.
3. **A real datacenter-shaped or enterprise-shaped benchmark fixture**,
   to test whether the "SNMP is more commonly enabled" hypothesis in the
   Operational Assessment actually holds — this benchmark's fixture
   construction (Methodology) was deliberately built to match RULE-004's
   own scope, not sampled from or validated against any real environment
   of that kind.
4. **A bounded-concurrency SNMP query phase**, motivated by this
   benchmark's own real measurement of the serial, timeout-dominated
   cost model (~3.3s × non-responding host count) — already flagged as
   a deferred, measurement-gated candidate in ARCH-012's Performance
   Considerations and Implementation Sequence item 5; this benchmark
   supplies the first real per-host timing data to size that decision
   against, but does not decide it (out of this sprint's own "Do not
   optimize code" scope).
5. **This benchmark's fixture SNMP response modeling (5 of 12
   "infrastructure-shaped" devices responsive) is a benchmark
   construction choice, not a field-observed SNMP adoption rate.** A
   future sprint with access to real network telemetry (the same caveat
   BENCH-002's own Future Opportunities flagged for its synthetic/
   localhost data) could replace this assumption with a measured one,
   strengthening the Operational Assessment's per-environment
   recommendations beyond the "plausible hypothesis" framing this
   benchmark had to use for enterprise/datacenter environments
   specifically.
