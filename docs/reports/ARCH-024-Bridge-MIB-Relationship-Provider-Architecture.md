# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No, for the Stage 1 scope this investigation recommends —
every decision below is a direct, individually-checked application of
already-accepted policy (ADR-010/011/012/013) or an already-established
implementation precedent from this lineage (ARCH-020/022/023,
FEAT-010A/011A/012A), never a new rule. Section 10 checks this explicitly
against every decision this investigation makes. One genuine candidate
future ADR trigger is identified and deliberately **not reached** by this
investigation's own recommended scope — Section 10, item 7 — named rather
than silently resolved, per this sprint's own charter.

Recommended Next Sprint:
FEAT-013A — SNMP Bridge-MIB Forwarding-Table Relationship Provider, scoped
exactly by Section 9's architectural-impact list and Section 4's Stage 1
VLAN-scoping boundary. Offered as a recommendation, not a decision — per
scope, engineering review selects the next sprint.

---

## 1. Executive Summary

ARCH-021 ranked Bridge/MAC forwarding tables second among five
relationship-evidence candidates, finding genuinely complementary
access-layer coverage — MACs learned from end hosts that never speak
LLDP/CDP at all — blocked on the same MAC-to-Subject Reverse Index
ARCH-022 then built and FEAT-011A shipped. This investigation goes as deep
into Bridge-MIB's actual table structure as ARCH-023 went into LLDP's, and
finds a genuinely new result of its own: **the forwarding database this
evidence source depends on is not a single, unambiguous table on any real
VLAN-segmented switch** — a materially different, and materially harder,
problem than anything LLDP or ARP presented.

**Bridge-MIB's forwarding data is inherently per-VLAN (or per shared
forwarding-database instance) on any switch that actually segments
traffic, and the classic table (`dot1dTpFdbTable`, RFC 4188) has no VLAN
dimension in its index at all.** A plain SNMPv2c walk of this table
against a real, VLAN-segmented enterprise switch — the realistic MSP
target this project is built around — returns at most one VLAN's worth of
forwarding knowledge, commonly the device's default/management VLAN, and
is silent about every other VLAN's learned MACs. This is not a per-row
failure mode any existing failure-semantics pattern in this codebase
already handles; it is a **coverage ceiling on the table itself**, present
before a single row is even parsed. Q-BRIDGE-MIB's `dot1qTpFdbTable` (RFC
4363) is the standards-based fix, and a vendor-specific SNMPv2c
community-string-indexing (CSI) convention is a non-standard workaround —
both evaluated in depth (Section 4), neither adopted for Stage 1.

**Every other question this investigation was chartered to answer resolves
by direct, largely mechanical reuse of precedent this lineage already
established, and none required a new decision.** The MAC-resolution path
reuses `build_mac_index()`/`receive_observations()` completely unmodified
(ARCH-022). The directional, non-symmetric relationship shape reuses ARP's
own established reasoning (ARCH-020 Section 6) unmodified. `RelationshipObservation`
and `RelationshipResolver` need no change, the third confirmation of this
same finding after ARP and LLDP. One genuinely new implementation-shape
finding, distinct from the VLAN question: Bridge-MIB's forwarding-database
table carries **no** identity-bearing field about the resolved neighbor at
all (no hostname, no management address, nothing beyond a MAC and a port)
— this evidence source can only ever produce `RelationshipObservation`s
about a resolved neighbor, never `IdentityObservation`s about one
(`self`(4) rows are a distinct, separately deferred case — Section 12),
and is therefore **entirely** dependent on another source having already
populated the reverse index. There is no
partial-resolution fallback path the way LLDP has one (management address,
`networkAddress` chassis ID) — a MAC not already in the index simply never
resolves, by construction, not by a gate this investigation had to design.

**One genuine candidate future ADR trigger is identified, and deliberately
not reached.** Pursuing full VLAN coverage — via Q-BRIDGE-MIB's multi-FDB
walk or the vendor-specific CSI workaround — would require extending
`SnmpCredentials` (or introducing a parallel per-target VLAN/context
dimension) beyond ARCH-012's own established version-plus-community
credential model. This investigation's own Stage 1 recommendation scopes
VLAN-awareness out entirely, so this trigger is not reached — named here,
per this sprint's charter, so a future VLAN-aware sprint starts from a
recorded finding rather than rediscovering it.

No production code is proposed for change by this report.

---

## 2. Direct Answers

**1. Which Bridge-MIB tables carry relationship evidence?**
`dot1dTpFdbTable` (classic BRIDGE-MIB, RFC 4188) — one row per learned
MAC, keyed by the MAC itself. `dot1qTpFdbTable`/`dot1qVlanCurrentTable`
(Q-BRIDGE-MIB, RFC 4363) — the VLAN-aware successor, not targeted by
Stage 1. `dot1dBasePortTable` maps a bridge port number to its `ifIndex` —
identity-adjacent context, not relationship evidence itself. Section 3.

**2. What is the central new finding this investigation surfaces?**
Classic `dot1dTpFdbTable` has no VLAN index at all, and on any real
VLAN-segmented switch reflects only one VLAN's (or one shared
forwarding-database's) forwarding knowledge per plain SNMPv2c access —
never previously evaluated at this depth in this lineage. Section 4.

**3. What happens to each `dot1dTpFdbStatus` value?** `learned`(3) is the
only status Stage 1 uses. `self`(4) (the bridge's own MAC) and `mgmt`(5)
(a statically configured entry, not traffic-observed) are excluded by
recommendation; `other`(1)/`invalid`(2) are excluded as non-current facts;
a row whose status could not be determined at all (a best-effort walk
failure, Section 7) is excluded the same way. Section 6.

**4. How does this provider consume the reverse index?** Identically to
LLDP's `macAddress`-subtype path (ARCH-023 Section 6) — `build_mac_index()`
called once per `enrich()` call, fed by `receive_observations()`, no new
resolution logic. Unlike LLDP, there is no non-index fallback path at all:
every row's resolution depends entirely on the index. Section 6.

**5. What are this provider's failure semantics?** Timeout/unreachable
handling is unchanged from ARP/LLDP's already-solved case.
`dot1dTpFdbAddress`/`dot1dTpFdbPort` are load-bearing; `dot1dTpFdbStatus`
remains best-effort at the client layer, mirroring the established
ARP/LLDP shape — a failed status walk never fails the host. The safety
requirement Stage 1's filtering policy (Section 6) needs is enforced at
the provider layer instead: a `RelationshipObservation` is emitted only
when status is explicitly `learned`(3); missing, malformed, or unresolved
status excludes that row from emission, not the whole host from
responding. Scale is a materially larger, real operational concern than
ARP or LLDP ever presented. Section 7.

**6. Where does this provider belong?** Squarely inside the existing
`EnrichmentProvider` architecture, as its own new class — every reason
ARCH-020/023 gave for keeping each table-walk provider separate applies at
least as strongly a third time. Section 8.

**7. What changes, and what doesn't?** A new provider, a new `SnmpClient`
method, new diagnostics, `application.py` wiring — the identical shape
FEAT-010A/FEAT-012A already took. `DiscoveryEngine`, `EnrichmentProvider`,
`build_mac_index()`, `receive_observations()`, `IdentityResolver`,
`RelationshipResolver`, `Project`, and every existing provider are
confirmed unchanged. Section 9.

**8. Is a new ADR required?** No, for Stage 1's recommended scope. One
candidate trigger (VLAN-scoped SNMP access) is named and explicitly not
reached. Section 10.

**9. What should stay out of this sprint?** Q-BRIDGE-MIB/VLAN-aware
coverage, the CSI workaround, `dot1dBasePortTable`-derived port/`Interface`
modeling, `self`(4)-as-self-identity-corroboration, spanning-tree state,
any port-fan-out-based directness heuristic, CDP, and topology rendering.
Section 12.

---

## 3. Bridge-MIB / Q-BRIDGE-MIB Structure

IEEE 802.1D bridging, MIB-2 branch `dot1dBridge`, OID root
`1.3.6.1.2.1.17`. Structure and semantics recalled from the standards'
documented design, not verified against a live device or the authoritative
MIB module text in this environment — the same disclosure this lineage
already applies to every other protocol-specific claim (FEAT-010A's ARP
OID parsing, ARCH-023's LLDP-MIB structure). Exact numeric OID suffixes are not given below and should be confirmed
against the actual MIB modules at implementation time; the table
*structure* below is long-standing, stable, widely documented standard
design this investigation has high confidence in. Unlike ARCH-023's
LLDP-MIB investigation, this report deliberately withholds specific
numeric leaf OID suffixes for the Bridge-MIB/Q-BRIDGE-MIB columns named
below, rather than fabricating them merely to match ARCH-023's level of
numeric detail.

**`dot1dBasePortTable`** (`dot1dBase` branch) — maps a bridge's internal
port numbering (`dot1dBasePort`) to the standard `ifIndex`
(`dot1dBasePortIfIndex`) MIB-2 interfaces use elsewhere. Identity-adjacent
context for a learned MAC's port, not itself relationship evidence.

**`dot1dTpFdbTable`** (`dot1dTp` branch) — the classic transparent-bridging
forwarding database, and this investigation's primary Stage 1 target. One
row per learned MAC address. Structurally simpler than either
`ipNetToPhysicalTable` or `lldpRemTable`: the row **INDEX is the 6-byte
MAC address itself** (`dot1dTpFdbAddress`) — no composite index, no
row-correlation join needed the way `ipNetToPhysicalTable`'s
`(ifIndex, addressType, addressLength, address)` or `lldpRemTable`'s
`(TimeMark, LocalPortNum, RemIndex)` require. Two value columns:
`dot1dTpFdbPort` (which `dot1dBasePort` learned this MAC — 0 if the
bridge itself doesn't know, per RFC 4188) and `dot1dTpFdbStatus`
(`other`(1) | `invalid`(2) | `learned`(3) | `self`(4) | `mgmt`(5)).
**No VLAN component exists anywhere in this table's index or columns.**
This table represents exactly one forwarding database — on a
non-VLAN-aware or single-VLAN bridge that is unambiguous; on a
VLAN-segmented switch, *which* database (if any coherent one) this table
reflects is not specified by RFC 4188 and is vendor-defined (Section 4).

**`dot1qTpFdbTable`** (Q-BRIDGE-MIB, `dot1qBridge` branch, IEEE 802.1Q) —
the VLAN-aware successor. INDEX is `(dot1qFdbId, dot1qTpFdbAddress)` —
`dot1qFdbId` is a **filtering database identifier**, not a VLAN ID
directly. `dot1qVlanCurrentTable` separately maps
`(dot1qVlanTimeMark, dot1qVlanIndex)` → `dot1qVlanFdbId`, recording which
filtering database a given VLAN currently uses. This two-table indirection
exists because IEEE 802.1Q permits either Independent VLAN Learning (IVL —
each VLAN gets its own FDB) or Shared VLAN Learning (SVL — several VLANs
share one FDB), a vendor/configuration-dependent choice the standard
itself does not fix. Notably, `dot1qVlanCurrentTable`'s own index uses a
`dot1qVlanTimeMark` component with the same `TimeFilter` (RFC 2021) query
semantics ARCH-023 Section 3 already flagged as an unresolved walk-behavior
question for `lldpRemTimeMark` — the identical uncertainty recurring in a
second, unrelated MIB, worth naming rather than re-deriving as if new.

**Community-string indexing (CSI)** — a vendor convention (documented for
Cisco IOS/Catalyst; implemented by some other vendors for
interoperability), not part of RFC 4188 or RFC 4363's own text at all: an
operator appends `@<vlan-id>` to the SNMPv2c community string (e.g.
`"public@100"`) to scope a classic `dot1dTpFdbTable` walk to one specific
VLAN. This achieves per-VLAN coverage on devices whose Q-BRIDGE-MIB
implementation is absent or incomplete, at the cost of being entirely
outside any standard, and of needing a distinct credential value per VLAN
per device (Section 4/10).

**`dot1dStpPortTable`** (spanning-tree state) — operational data, no
relationship evidence. Out of scope, not evaluated further (Section 12).

---

## 4. The VLAN-Scoping Problem

This section is this investigation's central finding, and the reason
Bridge-MIB is a materially harder evidence source than LLDP or ARP were,
independent of the already-solved MAC-resolution question.

**On a genuinely non-VLAN-aware or single-VLAN bridge** — a small
unmanaged-but-SNMP-capable switch, an older device, a Linux bridge, a lab
environment with no VLAN segmentation — `dot1dTpFdbTable` directly and
completely represents that bridge's forwarding knowledge. No scoping
problem exists; the table *is* the bridge's one and only forwarding
database.

**On any real VLAN-segmented switch — the realistic target of an MSP
engagement this project is built around (per `docs/LAB.md`'s own framing)
— the forwarding database is inherently per-VLAN (or per shared-FDB, under
SVL), and classic `dot1dTpFdbTable` was never designed to expose more than
one of them at a time.** A plain SNMPv2c walk with an unscoped community
string returns, per RFC 4188, whichever single forwarding database the
device chooses to expose this way — commonly its default or
management-VLAN database — and is entirely silent about every other
VLAN's learned MACs. This is not a per-row parsing failure any existing
failure-semantics pattern already handles (Section 7); it is a **coverage
ceiling on the table itself**, present before a single row is walked.
Concretely: an access switch trunking a dozen VLANs, with hundreds of end
hosts spread across them, could return a `dot1dTpFdbTable` walk containing
only the handful of MACs on its management VLAN — a small, potentially
misleadingly sparse fraction of what the switch actually knows.

**Q-BRIDGE-MIB's `dot1qTpFdbTable` is the standards-based fix.** Because
its own INDEX carries `dot1qFdbId` directly (Section 3), a single walk —
no per-VLAN credential switching — can in principle return entries across
every filtering database the device maintains, joined back to specific
VLANs via `dot1qVlanCurrentTable`. This is **not verified against any real
device by this investigation** — flagged explicitly as an
implementation-time uncertainty, at the identical disclosure standard
ARCH-023 applied to `lldpRemManAddrTable`'s real-world population rate:
whether a given real switch actually implements `dot1qTpFdbTable`
completely and correctly, across every VLAN, in one accessible context, is
a live-network question this investigation cannot answer from the MIB text
alone.

**The CSI workaround is real and reliably documented for Cisco IOS/Catalyst
devices specifically**, but carries three costs worth stating plainly: (a)
it is vendor-specific, not a general SNMP mechanism, so it cannot be relied
on across a heterogeneous MSP customer fleet; (b) it requires already
knowing the target device's VLAN list — from VLAN-MIB's
`dot1qVlanStaticTable` or a vendor-specific MIB such as CISCO-VTP-MIB,
neither implemented anywhere in this codebase today, meaning CSI would
itself need its own prerequisite discovery step; (c) it requires
constructing and using a **different community string per VLAN per
device** — a materially different shape of credential than
`SnmpCredentials`' current single `community: str` field was ever designed
to hold (Section 10, item 7).

**This investigation's Stage 1 recommendation, applying ARCH-021's own
scope call directly rather than re-deciding it:** ARCH-021 Section 5
already recommended "starting with whichever table shape is simpler to
walk correctly and treating VLAN-scoped forwarding as a deliberate, later
refinement, not a Stage 1 requirement." Classic `dot1dTpFdbTable` is
unambiguously the simpler table — a single-column MAC-keyed index, no
cross-table join, no filtering-database indirection. This investigation
applies that scope call directly: **Stage 1 targets `dot1dTpFdbTable`
only**, with the VLAN-scoping limitation disclosed explicitly and in
advance as a known, accepted Stage 1 characteristic — reduced, possibly
substantially reduced, real-world coverage on VLAN-segmented
infrastructure — not a defect to silently work around or a surprise to be
discovered only after building it. `dot1qTpFdbTable`'s full VLAN coverage
is named as the natural, higher-value follow-on refinement, **not
authorized by this investigation**, mirroring ARCH-021's own "later
refinement" framing exactly. The CSI workaround is not recommended at any
stage evaluated by this report (Section 12).

**Recommended pre-implementation check, mirroring ARCH-023 Section 13's
identical pattern for LLDP's own open coverage question:** before deep
implementation investment, verify against a small, representative sample
of real target-market devices (a mix of vendors/models an MSP might
realistically encounter) whether `dot1dTpFdbTable` returns useful data at
all in practice, or whether it is VLAN-starved severely enough that
`dot1qTpFdbTable` should be prioritized from the start instead. This is
offered as the single highest-value piece of information this
investigation could not itself gather — not a blocking gate, the identical
posture ARCH-023 already established for its own analogous question.

---

## 5. Observation-Type Mapping and Category Naming

**`dot1dTpFdbTable` rows with `status = learned`(3) and a resolvable MAC →
`RelationshipObservation`.** `subject` = the queried bridge's own IP;
`related_subject` = the subject resolved for the learned MAC via
`build_mac_index()`. **Category: a new value, not `connected_to` and not
`arp_neighbor`.** ARCH-021 Section 5 already recommended this, for exactly
the reason ARCH-020 Section 7 gave `arp_neighbor` its own category rather
than reusing `connected_to`: a forwarding-table entry proves L2
reachability through a port, not that the far end is a single,
directly-attached device — an unmanaged switch or hub (or, for that
matter, several more managed switches) between the queried bridge and the
learned MAC is entirely invisible to this evidence. Mixing this weaker,
indirect-reachability claim into `connected_to`'s corroboration group
would let `RelationshipResolver`'s `(subject, category)` grouping produce
a spurious `CONFIRMED` or `CONFLICTING` result between two evidence types
that were never claiming the same thing. This investigation, having gone
deeper into the actual table semantics than ARCH-021's comparative-level
treatment, recommends the specific name **`bridge_fdb`** — short, and
naming the exact evidence source (the Forwarding DataBase) the way
`arp_neighbor` names ARP rather than describing an interpretation of it.
Not a final decision — the same implementation-time-adjacent naming
latitude ARCH-020 left for `arp_neighbor`'s own exact name.

**Directional, not symmetric — reaffirming ARCH-021 Section 5's own
finding, unmodified.** A bridge's FDB entry for a MAC is that bridge's
own, one-sided, learned knowledge; the MAC's own device has no reciprocal
claim in this evidence at all. Structurally identical to ARP's own
directionality (ARCH-020 Section 6), applied here without modification.

**No new `IdentityObservation` type — a genuine, if quieter, finding of
its own.** `dot1dTpFdbTable` carries exactly three pieces of information
per row: the MAC, the learning port, and the status. Unlike ARP (which
independently corroborates MAC↔IP for the device it queries) or LLDP
(whose `lldpRemSysName` carries third-party hostname evidence about the
*neighbor*), Bridge-MIB's forwarding table says nothing about the resolved
neighbor beyond its MAC and the local port it was learned on — no
hostname, no management address, no identity-bearing field of any kind.
**This evidence source can therefore only ever produce
`RelationshipObservation`s about a resolved neighbor, never
`IdentityObservation`s about one** — `self`(4) rows are a distinct case,
excluded from this evidence source's relationship-evidence role entirely
(Section 6) and evaluated only as a separately deferred, not-included
possibility for the *queried bridge's own* self-identity (Section 12), not
a neighbor's. A direct consequence: this provider is **entirely** dependent on another source
(ARP or Nmap) already having populated the reverse index for a given MAC —
there is no partial, non-index resolution path the way LLDP has one
(management address, `networkAddress` chassis ID). A MAC absent from
`build_mac_index()`'s output simply never resolves here, by construction —
not a gate this investigation had to design, since there is no identity
claim of Bridge-MIB's own to gate in the first place (Section 6).

**`dot1dTpFdbPort` (and its `dot1dBasePortTable`-mapped `ifIndex`) →
retained, unconsumed context**, mirroring `lldpRemPortId`'s established
precedent (ARCH-023 Section 4/12) directly — no `Interface`/port model
exists yet; this is an application of an already-accepted deferral, not
new ground.

---

## 6. FDB Entry Resolution via the Reverse Index

**`dot1dTpFdbStatus` filtering — a genuinely new judgment call, resolved
by direct analogy to already-established precedent, not invented fresh.**

- **`learned`(3)** — the only status representing a live-traffic-derived
  observation. The qualifying status for Stage 1.
- **`self`(4)** — the bridge's own MAC address(es), on its own interfaces.
  **Recommended for exclusion from relationship-evidence emission
  entirely** — if the bridge's own MAC happens to already be resolvable
  via `build_mac_index()` back to the bridge's own subject (plausible but
  not guaranteed: many bridges' own MACs are never independently reported
  by ARP or Nmap), emitting it *could* produce a self-referential claim
  (`subject == related_subject`); when the MAC isn't already in the index,
  the row would simply fail to resolve regardless. The exclusion is
  precautionary against that conditional risk, not a response to a
  certainty. Two lines of defense are recommended, mirroring ARCH-023
  Section 4's "defense in depth" framing for the endpoint-bootstrapping
  gate directly: (1) the provider itself should not
  emit for `self`(4) rows at all — proactive exclusion at the point of
  evidence construction, not reliance on a downstream safety net; (2)
  `RelationshipResolver`'s own already-existing self-loop exclusion
  (`relationships/resolver.py`'s preprocessing,
  `observation.subject != observation.related_subject`) independently
  catches this even if it weren't — confirmed present in current code, not
  a new dependency this investigation introduces, worth naming as an
  existing second line of defense for a mistake the recommended design
  already avoids by construction.
- **`mgmt`(5)** — a statically/administratively configured entry, not
  learned from observed traffic. **Recommended exclusion from Stage 1**,
  not a settled certainty: ADR-011's observation semantics describe a
  retained observation as "one direct claim produced by an evidence
  source" from what was actually observed; a static configuration entry
  reads more like a config fact than a traffic-derived observation, and
  since `dot1dTpFdbStatus` cleanly distinguishes it, there is no forcing
  reason to blur the two together. A future implementer could reasonably
  choose to include `mgmt`(5) with its own distinct `collection_method`
  value for provenance clarity instead — this investigation's own
  recommendation is exclusion, matching `connected_to`/`arp_neighbor`'s
  own established precedent of representing live, wire-observed facts,
  not configuration.
- **`other`(1), `invalid`(2)** — excluded; neither represents a usable,
  current MAC-to-port fact under RFC 4188's own definitions.

**Missing or unresolved status is excluded the same way, not treated as a
host-level failure.** `dot1dTpFdbStatus` is walked as a best-effort column
at the client layer (Section 7) — a row whose status could not be
determined (a failed or partial status walk, not a malformed index) is
still constructed with its MAC and port intact, but is excluded from
`RelationshipObservation` emission at the provider layer exactly as
`other`/`invalid` already are, since Stage 1 has no principled default for
treating an unresolved status as `learned`. This preserves the filtering
policy's safety property (never emit for anything but a confirmed
`learned` row) without discarding a host's otherwise-successful MAC/port
data over one column's failure (Section 7).

**Reverse-index consumption — identical mechanism to LLDP's
`macAddress`-subtype path (ARCH-023 Section 6), reused without
modification.** `build_mac_index(self._received_observations)` computed
once per `enrich()` call, not per row (the same once-per-call precedent
`SnmpArpNeighborProvider`/`SnmpLldpNeighborProvider` already establish).
Per `learned`-status row: `mac_index.get(mac, frozenset())`; `len == 1` →
resolves to that one subject; `len == 0` (absent) or `len > 1`
(ambiguous) → the row contributes nothing, never an error, mirroring
ARCH-022 Section 5's own caller-decision recommendation directly. No new
resolution logic beyond what LLDP already established; this investigation
confirms it transfers unmodified to a third consumer.

**A consequence worth stating plainly, as expectation-setting rather than
a defect discovered after the fact:** because Bridge-MIB has no
non-MAC-index resolution path at all (Section 5), its practical yield is
**entirely** bounded by how many of a switch's learned MACs belong to
devices ARP or Nmap have already independently discovered and reported a
`mac_address` for. On a switch with many end hosts NetworkMapper never
separately discovered (common — not every host responds to an Nmap sweep,
and ARP-corroborated-gateway evidence only sees hosts a queried gateway's
own cache happens to contain), most `learned`-status rows will resolve to
nothing. This mirrors the same "reduced coverage, never incorrect" principle
ARCH-022 Section 7 already established for provider-ordering tolerance,
applied here to source coverage instead — genuinely expected, not a
defect, but worth disclosing before implementation rather than only after.

---

## 7. Failure Semantics and Scale

**Timeout, unreachable host, incorrect community string.** Unchanged from
ARP/LLDP's already-solved case — SNMPv2c's identical indistinguishability
applies identically here.

**Load-bearing vs. best-effort — reaffirms, rather than departs from, the
established ARP/LLDP shape, corrected from this investigation's own first
draft.** `dot1dTpFdbAddress` (the row index itself) and `dot1dTpFdbPort`
are load-bearing: without a MAC and a learning port, no usable row exists
at all — a failed walk of either fails the whole host, the same treatment
`get_arp_table`/`get_lldp_neighbors` already give their own load-bearing
columns. `dot1dTpFdbStatus` is **best-effort at the client layer**,
matching `lldpRemSysName`'s established shape directly: a failed or
partial status walk never fails the host, and the client retains a row
whose MAC/port data was successfully collected even when its status could
not be determined. This investigation's own first draft recommended
treating status as load-bearing instead, reasoning that Stage 1 has no
safe default for an unknown-status row — correct as far as it goes, but
that reasoning supports excluding the *row* from emission, not discarding
the *host's* otherwise-successful MAC/port data over one column's
transient failure, and was corrected on review. The safety property is
preserved at the provider layer instead (Section 6): a
`RelationshipObservation` is emitted only when status is explicitly
`learned`(3); missing, malformed, or unresolved status excludes that row
from emission, never the host from responding.

**Empty table (responded, zero rows).** Legitimate, mirroring the
established ARP/LLDP precedent directly — a bridge with an empty
forwarding database, or queried too soon after a reset, is a real,
non-error outcome.

**Missing Bridge-MIB support entirely** (a device with no bridging
function — a router-only device, certain end-host SNMP agents). Also
legitimate, the same `noSuchObject`/`endOfMibView` handling already proven
twice.

**Malformed entries.** A row whose parsed index does not yield exactly the
6 octets RFC 4188 defines for `dot1dTpFdbAddress` is malformed — skipped,
not erroring, mirroring `_parse_ipv4_arp_row`'s established
non-conforming-row treatment.

**Scale — a genuinely new, more severe concern than ARP or LLDP presented,
named explicitly rather than assumed away.** ARCH-012's own already-named
risk ("a table walk against a core router is materially larger than the
fixed six-OID system-group GET") motivated `ARP_TABLE_MAX_ROWS`/
`LLDP_TABLE_MAX_ROWS`'s shared 10,000-row bound. This investigation finds
Bridge-MIB forwarding tables can be materially larger again: a core or
aggregation switch's FDB commonly holds thousands of entries, bounded
roughly by the switch's own forwarding-hardware capacity — informally, on
the order of 8,000–32,000+ entries for real managed switches. **This range
is an illustrative operational estimate drawn from general industry
familiarity with switch forwarding-table capacity, not an authoritative or
verified bound** — this investigation has not measured or cited a specific
vendor specification for it, the same care the rest of this document takes
to distinguish verified fact from disclosed estimate. Even taken only as
illustrative, it is plausibly an order of magnitude beyond the ARP/LLDP
precedent's shared bound in a realistic worst case, and routinely large
even on ordinary access switches with a full complement of connected
hosts. This
investigation does not fix the exact bound here — the same
implementation-time tuning question `ARP_TABLE_MAX_ROWS`/
`LLDP_TABLE_MAX_ROWS` themselves were, neither requiring its own ADR — but
the architectural conclusion holds regardless of the estimate's own
precision: reusing 10,000 unexamined would be a silent assumption, not a
considered one, and this provider should define its own constant,
consciously chosen and reconsidered at implementation time against real
device data, rather than copied from a table plausibly an order of
magnitude smaller in the realistic case.

---

## 8. Provider Placement

Confirmed against ADR-010's Decision text directly: this provider fits the
same "receives the already-discovered device set and adds evidence to it
in place" contract every prior `EnrichmentProvider` in this lineage
already satisfies — a learned MAC never becomes a new `Device` regardless
of whether it resolves.

**A new provider class, not an extension of `SnmpArpNeighborProvider`,
`SnmpLldpNeighborProvider`, or `SnmpEnrichmentProvider`.** Every reason
ARCH-020 Section 8 gave for keeping ARP separate, and ARCH-023 Section 8
reaffirmed for LLDP as a second table-walk provider, applies at least as
strongly a third time: a narrowly-scoped class contract, independent
opt-in, one concern per provider class. ARCH-023 Section 8 already
considered and rejected generalizing the provider shape itself once, with
two similar providers on the table; a third similar provider does not, on
its own, meet the burden of proof that consideration already applied —
reaffirmed, not re-litigated. Recommend `SnmpBridgeFdbProvider` (name
illustrative, not finalized), in a new
`networkmapper/discovery/bridge_fdb_provider.py`, mirroring
`arp_neighbor_provider.py`/`lldp_neighbor_provider.py`'s own shape
directly.

**A new `SnmpClient` method, following the proven walk pattern.**
`get_bridge_fdb(host, credentials, timeout, retries) ->
SnmpBridgeFdbResult`, using the same `walk_cmd`-based, `lookupMib=False`,
bounded-`maxRows` mechanism `get_arp_table()`/`get_lldp_neighbors()`
already proved out twice — with its own row-index parsing helper, since
`dot1dTpFdbTable`'s single-6-octet-MAC index (Section 3) is a materially
simpler shape than either prior table's composite index, not a reuse of
either existing helper.

**New diagnostics types, mirroring `snmp_arp_diagnostics.py`/
`snmp_lldp_diagnostics.py`'s established shape.** ARCH-023 Section 12
already noted that generalizing the ARP and LLDP diagnostics types into
one shared table-walk diagnostics type was a worthwhile, non-blocking
refinement once a second near-identical case existed; a third
near-identical type strengthens that same already-made observation
without changing it — still not attempted here, still a nice-to-have
implementation-time refinement, not a requirement of this investigation.

---

## 9. Architectural Impact

**New:**
- `networkmapper/discovery/bridge_fdb_provider.py` —
  `SnmpBridgeFdbProvider`.
- `SnmpClient.get_bridge_fdb()` plus `SnmpBridgeFdbEntry`/
  `SnmpBridgeFdbResult` dataclasses in `snmp_client.py`, mirroring
  `SnmpArpTableEntry`/`SnmpLldpNeighborEntry`'s established shape.
- A new diagnostics type (mirroring `snmp_arp_diagnostics.py`/
  `snmp_lldp_diagnostics.py`'s shape) — Section 8 flags, again, whether
  this should instead be generalized to a shared table-walk diagnostics
  type now that a third near-identical case exists, as a worthwhile but
  non-blocking refinement, not a requirement.

**Modified:**
- `networkmapper/application.py` — a new `--snmp-bridge-fdb` flag, shared
  credential resolution extended to a fourth flag (mirroring FEAT-010A's
  own `--snmp-arp` addition and FEAT-012A's own `--snmp-lldp` addition to
  the same pattern exactly), new diagnostics printing.

**Confirmed unchanged, and why, traced against current code rather than
assumed:**
- `DiscoveryEngine.discover()` — already generic over any number of
  `EnrichmentProvider`s and already calls `receive_observations()`
  immediately before each one's `enrich()` (FEAT-011A); a fourth provider
  needs no change here.
- `EnrichmentProvider` — `receive_observations()`/`collect_observations()`
  already accept exactly the shapes this provider needs.
- `build_mac_index()` — already generic over any `IdentityObservation`
  stream; consumes whatever `mac_address` observations exist regardless
  of source.
- `IdentityResolver`/`RelationshipResolver` — both already generic over
  any observation a provider emits, the same property FEAT-011A's design
  confirmed and FEAT-012A reconfirmed against a real second consumer; this
  investigation finds nothing about a third, `RelationshipObservation`-only
  consumer that would change that.
- `Project`, `NmapProvider`, `SnmpEnrichmentProvider`,
  `SnmpArpNeighborProvider`, `SnmpLldpNeighborProvider` — untouched; the
  new provider is a sibling, not a modification of any existing one.
- Exporters, `ProjectSerializer` — unaffected; no new `Project` field, no
  new report content, consistent with every prior sprint in this lineage.

---

## 10. ADR-Trigger Check

Checked individually against every decision this investigation makes:

1. `SnmpBridgeFdbProvider` fitting `EnrichmentProvider`'s existing contract
   (Section 8) — direct application of ADR-010's already-accepted
   Decision text; no new policy.
2. A new `bridge_fdb` relationship category (Section 5) — direct
   application of ADR-013's already-declined-to-freeze-taxonomy stance,
   the same non-trigger status `arp_neighbor` and `connected_to` already
   have; no new policy.
3. Directional, non-symmetric relationship shape (Section 5) — direct,
   unmodified reuse of ARP's already-established directionality reasoning
   (ARCH-020 Section 6); no new policy.
4. `dot1dTpFdbStatus` filtering — `learned`-only, excluding
   `self`/`mgmt`/`invalid`/`other`/unresolved (Section 6), with status
   walked best-effort at the client layer and the exclusion enforced at
   the provider layer (Section 7) — an implementation-level
   evidence-quality judgment, analogous to LLDP's load-bearing/best-effort
   column split and chassis-ID-subtype gating; no new policy, though
   flagged as a recommendation a future implementer could reasonably
   revisit for `mgmt`(5) specifically (Section 6).
5. Reverse-index consumption via `build_mac_index()`/
   `receive_observations()` (Section 6) — zero-modification reuse of
   ARCH-022's already-designed mechanism; no new policy.
6. A provider-specific FDB scale/max-rows bound distinct from
   `ARP_TABLE_MAX_ROWS`/`LLDP_TABLE_MAX_ROWS` (Section 7) — the same kind
   of implementation-level tuning constant those two already are, neither
   of which required an ADR; no new policy.
7. **VLAN-scoped SNMP access — a genuine candidate future ADR trigger,
   identified and deliberately not reached (Section 4).** If a future
   sprint pursues Q-BRIDGE-MIB's `dot1qTpFdbTable` for full multi-FDB
   coverage, or the vendor-specific community-string-indexing workaround
   to achieve full VLAN coverage on devices whose Q-BRIDGE-MIB support is
   absent or incomplete, either would require extending `SnmpCredentials`
   (or introducing a parallel per-target VLAN/context dimension) beyond
   ARCH-012's own established version-plus-community credential model — a
   materially new credential-model capability, not a natural extension of
   already-accepted policy; confirmed by re-reading ARCH-012's own
   Credential Strategy section directly, which anticipated SNMPv3's
   username/auth/priv fields but never a per-target VLAN or context
   dimension. This investigation's own Stage 1 recommendation (Section 4)
   scopes VLAN-awareness out entirely, so this trigger is **not reached**
   by anything this investigation recommends — named here explicitly, per
   this sprint's own charter, mirroring the same "name it, don't resolve
   it early" pattern ARCH-014/ARCH-018/ARCH-021 already established for
   the structurally analogous non-`Device`-relationship-endpoint trigger,
   so a future VLAN-aware Bridge-MIB sprint starts from a recorded finding
   rather than rediscovering this from scratch.

**No new ADR is triggered by this investigation's own recommended scope.**
One candidate trigger (item 7) is named and deliberately not reached.

---

## 11. Testing Strategy

**Unit — `SnmpClient.get_bridge_fdb()`.** Mirrors
`test_snmp_client.py`'s ARP/LLDP test templates directly: each
`dot1dTpFdbStatus` value individually (`learned`, `self`, `mgmt`,
`invalid`, `other`); a malformed row whose index does not yield exactly 6
octets; a load-bearing address/port-walk failure (whole host lost,
mirroring `get_arp_table`/`get_lldp_neighbors`'s established treatment); a
best-effort status-walk failure (row retained with MAC/port intact, status
unresolved — Section 7); empty table; timeout; missing Bridge-MIB support.

**Unit/provider — `SnmpBridgeFdbProvider`.** Mirrors
`test_arp_neighbor_provider.py`/`test_lldp_neighbor_provider.py`'s
template: a `learned`-status row resolves via a fed `build_mac_index()`
snapshot (supplied through `receive_observations()`); an ambiguous MAC
lookup (`frozenset` of size > 1) skips the row; an absent MAC lookup skips
the row; a `self`-status row produces **no** observation at all — a
direct, full-exclusion test (a `self`-status row must never emit any
`RelationshipObservation`), distinct in shape from ARP's own
`test_an_undiscovered_row_produces_relationship_evidence_only` (which
tests *partial* gating — a relationship emitted, an identity withheld):
this test instead proves Section 6's defense-in-depth exclusion produces
no observation of either kind; a `mgmt`-status row produces no observation
under the recommended exclusion; a row with unresolved/missing status
(Section 7's best-effort status walk) produces no observation, the same
full-exclusion shape as the `self`/`mgmt` cases; `Device` fields are never
mutated; diagnostics and telemetry-phase tests mirroring the established
pattern.

**Integration — a genuinely new case FEAT-012A's own design enables for
the first time.** `SnmpArpNeighborProvider`, `SnmpLldpNeighborProvider`,
and this new provider registered together in `DiscoveryEngine`'s
`enrichment_providers` list, across representative orderings — extending
FEAT-012A Section 11's own two-provider precedent to a third real
consumer, confirming `receive_observations()` correctly aggregates
whatever combination of prior evidence exists, and that this provider
degrades to reduced-but-correct coverage regardless of which, if any,
other MAC-emitting provider ran first or at all.

**Live-network verification, explicitly separated.** The exact numeric
OID suffixes for every `dot1dTpFdbTable`/`dot1dBasePortTable` column, at
the same disclosed-uncertainty class as every prior SNMP table-walk in
this lineage; the real-world VLAN-scoping behavior of `dot1dTpFdbTable`
across representative vendors — this investigation's own central,
recommended early check (Section 4); realistic FDB table sizes on
representative access/aggregation switches, informing the scale bound
named in Section 7.

---

## 12. Scope Boundaries

Explicitly out of a resulting FEAT-013A sprint, named so they are not
silently absorbed into it:

- **Q-BRIDGE-MIB / `dot1qTpFdbTable` VLAN-aware coverage** (Section 4) —
  named as valuable, likely necessary-for-real-value follow-on work, not
  a Stage 1 requirement.
- **Community-string-indexing (CSI) VLAN workaround** (Section 3/4) —
  vendor-specific, and would require the ADR-trigger-candidate credential
  extension named in Section 10 item 7; not pursued at any stage evaluated
  by this report.
- **`dot1dBasePortTable`-derived port/`Interface` modeling** — retained,
  unconsumed context only (Section 5), mirroring LLDP's identical,
  already-accepted deferral.
- **`self`(4) rows as self-identity corroboration for the queried
  bridge's own MAC** — this investigation excludes `self`(4) from
  relationship evidence (Section 6), but does not evaluate using it as
  identity-layer evidence instead (an `IdentityObservation` corroborating
  the queried device's own `mac_address`, analogous to `NmapProvider`'s
  own self-reported MAC). Legitimate and low-risk in principle — direct
  self-report about an already-discovered device, with no bootstrapping
  risk at all — structurally identical to ARCH-023 Section 4/12's own
  deferral of LLDP's local system data (`lldpLocChassisId`/
  `lldpLocSysName`). Not the relationship-provider deliverable this
  investigation is chartered around; preserved here as a separable,
  explicitly deferred future idea for engineering review, not folded into
  FEAT-013A by default.
- **Spanning-tree state** (`dot1dStpPortTable`) — operational data, not
  relationship evidence; not evaluated further.
- **Any heuristic inferring "directly attached end host" versus "uplink
  toward more switches" from a port's learned-MAC count** — a
  topology-adjacent interpretation question explicitly out of the
  observation-retention layer's scope (ADR-011); named here so it is not
  silently absorbed rather than left unaddressed by omission.
- **CDP** (ARCH-021's Rank 3) — its own, separate, not-yet-chartered
  future sprint, sharing this same reverse-index prerequisite but not
  folded into this one merely because of that.
- **Topology rendering of any kind** — still explicitly out of scope per
  every report in this lineage back to ADR-013's own boundary.

---

## 13. Final Recommendation

**Recommended architecture:** exactly Section 9's file list — one new
provider (`SnmpBridgeFdbProvider`, `learned`-status rows only, classic
`dot1dTpFdbTable` only), one new client method, new diagnostics,
`application.py` wiring — reusing `build_mac_index()`,
`receive_observations()`, `IdentityResolver`, and `RelationshipResolver`
entirely unmodified. VLAN-aware coverage (`dot1qTpFdbTable`) explicitly
deferred, not designed here.

**Implementation order**, mirroring FEAT-010A/FEAT-012A's own successful
sequencing: (1) `SnmpClient.get_bridge_fdb()` plus its unit tests —
isolable, no dependency on the provider; OID-suffix confirmation happens
here, before anything else; (2) `SnmpBridgeFdbProvider` plus its unit
tests — depends on (1) and the already-shipped `build_mac_index()`/
`receive_observations()`; (3) `application.py` wiring — depends on (2);
(4) the three-provider integration test (Section 11) — depends on (2) and
the already-shipped ARP/LLDP providers; (5) full-suite validation.

**Remaining unknowns, named rather than guessed past:** exact numeric OIDs
need confirmation against the authoritative BRIDGE-MIB module before
coding begins, the same class of disclosed risk every prior SNMP
table-walk sprint in this lineage has carried. Two further, larger
unknowns are specific to this investigation and recommended as
pre-implementation checks, not blocking gates: `dot1dTpFdbTable`'s
real-world VLAN-scoping yield across representative vendors (Section 4 —
this investigation's single highest-value open question), and realistic
FDB table sizes on representative switches, informing the scale bound
named in Section 7.

**ADR requirement:** none for this investigation's own recommended Stage 1
scope (Section 10). One candidate trigger — extending the SNMP credential
model for VLAN-scoped access — is named and deliberately not reached.
