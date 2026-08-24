# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No new ADR from this investigation's own recommendation
(see Section 8) — but this investigation confirms, more concretely than
ARCH-014/ARCH-018 did, that two of its five candidates would each trigger
one of ADR-013's own already-named future-ADR conditions if pursued as
literally scoped. Neither is recommended for pursuit as scoped, so neither
ADR is triggered by this report itself.

Recommended Next Sprint:
ARCH-022 — MAC-to-Canonical-Identity Resolution (a prerequisite
architecture investigation, not a provider). Three of this report's five
candidates — LLDP, CDP, and Bridge/MAC forwarding tables — are all blocked
on the identical missing mechanism, confirmed here as still absent
(ARCH-018 Section 12's own finding, reconfirmed against current code).
Building that one mechanism, not picking a "winning" provider outright, is
this investigation's actual recommendation — no candidate clears "promote
now." Offered as a recommendation, not a decision — per scope, engineering
review selects the next sprint.

---

## 1. Executive Summary

None of the five candidates this sprint was chartered to evaluate clears
"promote now." That is the central, non-obvious finding this investigation
exists to surface rather than talk around: it would be easy to pick the
most novel-sounding candidate (LLDP, the classic "real topology" evidence)
and start building, but every one of these five is blocked on a concrete,
identifiable, currently-missing prerequisite — not a vague sense that
"more work is needed," but a specific mechanism this investigation names
for each candidate.

**Three candidates share one blocker.** LLDP, CDP, and Bridge/MAC
forwarding tables all key their neighbor evidence on a MAC address or
chassis ID, never an IP address — and this codebase has no mechanism to
resolve a MAC address to the subject reference `IdentityObservation`/
`RelationshipObservation` already use for that same device (an IP
address, today). ARCH-018 Section 12 named this gap once, for Bridge MIB
specifically; this investigation confirms it applies identically to LLDP
and CDP, and reconfirms the gap still exists against current code — no
MAC index exists anywhere in `IdentityResolver`, `Project`, or any
provider. This is the single highest-leverage prerequisite among
everything this report evaluates: building it once unblocks three
candidates, not one.

**Two candidates are each blocked on something narrower and not worth
building for their own sake.** Router interface ownership hits the
non-`Device` relationship-endpoint problem ADR-013 already named as a
candidate future-ADR trigger (Section 6) — a large architectural cost for
evidence that isn't even clearly a first-class relationship claim (Section
6 also finds a cheaper, non-relationship reframing that this report
recommends preserving instead). Default gateway corroboration has the
cleanest evidence shape of all five — directional, already IP-to-IP, no
translation problem, structurally identical to ARP's own appeal — but its
acquisition cost is the worst of the five: it requires an entirely new
execution boundary (WMI or SSH) this codebase has never touched, for a
single candidate's payoff, unlike the SNMP table-walk infrastructure
FEAT-010A just proved out and that LLDP/CDP/Bridge-MIB would all reuse
directly.

**Recommendation.** Investigate the MAC-to-canonical-identity resolution
mechanism next (a prerequisite ARCH investigation, not a provider sprint),
then build LLDP first among the three it unblocks — the highest evidence
quality and broadest multi-vendor coverage of the three, with Bridge-MIB
and CDP as natural, cheap follow-ons once the shared plumbing exists.
Router interface ownership and default-gateway corroboration are not
rejected outright — both are preserved as legitimate future ideas, gated
on their own distinct, larger prerequisites this investigation names
explicitly (Section 7).

---

## 2. Method

Every candidate is evaluated against the eight criteria the charter
specifies, applied uniformly rather than selectively, so no candidate gets
a more forgiving pass than another: operational value, evidence quality,
compatibility with the current architecture, acquisition complexity,
coverage, corroboration value, architectural cost, and testing/real-network
verification. Scope risk is called out per candidate where a tempting but
premature extension exists. Findings are grounded against current code
(re-verified in this investigation, not assumed from ARCH-014/ARCH-018)
and against ARCH-014/ARCH-018's own prior per-source assessments where
they already did real work this investigation would otherwise repeat —
cited directly rather than re-derived.

---

## 3. LLDP

**Operational value.** LLDP is the strongest available evidence for
"what's physically connected to what" — the topology-diagram question a
technician documenting a new customer's environment is most often trying
to answer, and one NetworkMapper cannot currently infer at all (its
IP-based discovery has no concept of physical adjacency, only "these two
devices exist"). This is real, high-value, un-derivable-any-other-way
evidence, confirmed by ARCH-014's own original motivation for this entire
relationship-evidence line of work.

**Evidence quality.** Reports a neighbor's chassis ID and (per-port)
local port ID — a direct claim, from the reporting device's own
link-layer table, that a specific neighbor is attached to a specific
local port. Strong evidence, the strongest of the five, for exactly the
reason ARCH-018 Section 5 already found. **Directional as reported** (one
device's own LLDP-remote table), describing a fact that is physically
symmetric — the same link, from either side. Category: `connected_to`
(ADR-013's own already-named Physical category — LLDP is precisely the
evidence that category was written for).

**Compatibility with the current architecture.** `RelationshipObservation`
needs no change — `subject`/`related_subject`/`category`/`provenance` is
already exactly the right shape. `RelationshipResolver` needs no change
either, confirmed directly: it consumes whatever
`RelationshipObservation`s any provider emits, with zero knowledge of
MAC addresses, chassis IDs, or any protocol specifics (FEAT-010A already
demonstrated this genericity in practice, not just in the pipeline
diagram). The blocker is entirely upstream of both: a provider cannot
construct a valid `RelationshipObservation` at all until it can translate
a reported chassis ID into the same IP-based subject reference the
neighbor's own `IdentityObservation`s already use — the MAC-to-identity
resolution mechanism this report's Section 6 addresses directly.

**Acquisition complexity.** SNMP LLDP-MIB (`lldpRemTable`,
`1.0.8802.1.1.2.1.4.1`) — a table walk, using the identical
`SnmpClient.walk_cmd`-based mechanism FEAT-010A just built and proved for
`ipNetToPhysicalTable`. This is the cheapest possible acquisition path
available to any of the three MAC-dependent candidates: no new client
capability, no new execution boundary, no new credential model — the same
`SnmpCredentials`/opt-in-flag pattern already established twice. Expected
failure modes are identical to the ARP provider's own (unsupported OID
subtree, timeout, empty table) — already-solved problems, not new ones.

**Coverage.** Broad and multi-vendor by design — LLDP is an open IEEE
802.1AB standard most managed switches, routers, many access points, and
an increasing number of servers/NICs support, unlike CDP's Cisco-specific
scope (Section 4). Real-world caveat, not a blocker: LLDP is frequently
disabled by default or restricted to trusted VLANs on security-conscious
networks — coverage is broad in principle, inconsistent in practice,
exactly the kind of "not every device, not every network" limitation this
report expects and does not treat as disqualifying (ARP evidence has the
identical characteristic — not every device exposes a useful ARP table
either).

**Corroboration value.** A genuinely new relationship class, not a
strengthening of existing ARP evidence — ARP evidence answers "does this
gateway know this IP," LLDP answers "is this port physically wired to
that device," a categorically different claim (Section 7's `arp_neighbor`
vs. `connected_to` distinction already established this exact principle).
Two devices' LLDP reports of the *same* physical link (A's remote-table
entry for B, and B's remote-table entry for A) are the textbook case
ARCH-018 Section 6 already designed for — currently landing as two
independent `WEAK` relationships under Stage 1's accepted
under-corroboration limitation, not one `CONFIRMED` one, until the
already-named, already-deferred symmetric-category canonicalization
mechanism (ARCH-018 Section 6/15's Stage 3.5) is built. This is a real,
disclosed limitation, not a blocker to shipping LLDP evidence at all —
Stage 1's own precedent (and FEAT-010A's own `arp_neighbor` evidence)
already ships useful, if under-corroborated, `WEAK` relationships this
same way.

**Architectural cost.** The MAC-to-canonical-identity resolution
mechanism (Section 6) is the one real cost, shared with CDP and Bridge-MIB
— not LLDP-specific. Local-port granularity has nowhere to go in
`RelationshipResolver`'s `(subject, category)` key (ARCH-014 Section 7's
own already-named ceiling, reconfirmed unchanged) — an accepted,
not-solved-here limitation, not a blocker. No ADR is triggered by LLDP
itself; the mechanism it depends on (Section 6) is implementation detail
inside ADR-012's own already-accepted identity-resolution scope, not a new
policy question.

**Testing and real-network verification.** Unit-testable in full,
mirroring `test_arp_neighbor_provider.py`'s exact pattern (a stub
`SnmpClient`, no live network needed) — FEAT-010A already proved this
testing shape works for a table-walk provider. The one thing that
genuinely needs live-network verification, not unit tests, is the same
class of risk FEAT-010A already disclosed for its own OID-index parsing:
whether a real LLDP-MIB agent's chassis-ID subtype and encoding match
what this report's design assumes (chassis IDs come in several IEEE-defined
subtypes — MAC address, interface name, locally-assigned string — and
only the MAC-address subtype is directly usable by the resolution
mechanism Section 6 proposes; other subtypes would need to be excluded,
not guessed at).

**Scope risk.** Building full `Interface`/port modeling to preserve
per-port granularity is tempting once LLDP data is flowing and visibly
richer than a flattened `(subject, category)` key can express — this
report recommends deferring it exactly as ARCH-014/ARCH-018 already did,
until real LLDP evidence exists to design that model against, not before.

**Verdict: Defer — promising, prerequisite missing.**

---

## 4. CDP

Structurally identical to LLDP in every respect except vendor scope and
acquisition detail — evaluated relative to LLDP rather than repeating the
full analysis.

**Operational value / evidence quality.** Identical in kind to LLDP — a
direct neighbor-chassis-and-port claim, `connected_to`, directional as
reported, describing a symmetric physical fact. CISCO-CDP-MIB
occasionally carries a little more Cisco-specific detail (native VLAN,
some capability flags) than baseline LLDP, but nothing this investigation
finds changes the relationship-evidence shape or value.

**Compatibility, architectural cost.** Identical to LLDP — same
`RelationshipObservation` shape, same zero change needed to
`RelationshipResolver`, same MAC-to-identity-resolution blocker (Section
6), same deferred symmetric-canonicalization refinement.

**Acquisition complexity.** Identical mechanism to LLDP — CISCO-CDP-MIB's
`cdpCacheTable` (`1.3.6.1.4.1.9.9.23.1.2.1`) is a table walk over the same
`SnmpClient.walk_cmd` infrastructure, no new capability needed beyond what
LLDP already requires.

**Coverage — the one real differentiator.** Cisco-proprietary. Useful
only where both the queried device and its neighbor are Cisco or
CDP-compatible (a handful of other vendors implement CDP for
interoperability, notably some VoIP phones) — meaningfully narrower than
LLDP's open-standard, broad-multi-vendor reach, and this matters
specifically for LAB.md's own MSP framing: a heterogeneous customer
environment (the realistic case) gets more value from LLDP than from CDP
alone.

**Corroboration value.** Where both LLDP and CDP are available on the
same Cisco link, this is a genuine, independent-source corroboration
opportunity — two different `(provider, collection_method)` pairs
observing the same physical fact, exactly the kind of case Stage 1's
independent-source counting already handles correctly once both providers
exist.

**Verdict: Defer — promising, prerequisite missing.** Same blocker as
LLDP; lower priority on its own because of narrower coverage, but cheap to
add once LLDP's shared prerequisite and acquisition pattern exist —
recommended as a near-immediate follow-on to LLDP, not a separately
justified sprint.

---

## 5. Bridge/MAC Forwarding Tables

**Operational value.** Answers a related but genuinely different question
than LLDP/CDP: not "what's directly wired to what" but "which switch port
is this MAC address reachable through" — coverage that includes end
hosts (workstations, printers, IoT devices) that never speak LLDP/CDP
themselves, and switches whose LLDP/CDP happens to be disabled. This is
real, complementary operational value a technician mapping a customer's
access layer would want and that neither LLDP/CDP nor ARP fully provides
(ARP only tells you what a *router* has resolved, not which access switch
a given host hangs off of).

**Evidence quality.** A MAC-to-port learning-table entry — weaker
evidence than LLDP/CDP for a *direct physical link* claim, since a
forwarding-table entry only proves L2 reachability through that port, not
that the far end is a single directly-attached device (an unmanaged
switch or hub between them is invisible to this evidence, exactly as
ARCH-014 already found). **Directional, not symmetric** — a switch's own
forwarding table entry for a MAC is a one-sided observation from that
switch's perspective, structurally identical in this respect to ARP
(Section 6 of ARCH-020 already established this exact reasoning for why
ARP is directional; the same reasoning applies here without modification).
Because the claim is weaker than LLDP/CDP's, this investigation recommends
it get its **own** category — not `connected_to` — for the identical
reason ARCH-020 gave `arp_neighbor` its own category rather than reusing
`connected_to`: mixing a weaker, indirect-reachability claim into the same
corroboration group as LLDP's strong direct-adjacency claim would let
`RelationshipResolver`'s `(subject, category)` grouping produce a spurious
`CONFIRMED` or `CONFLICTING` result between two evidence types that were
never claiming the identical thing. A category name in the spirit of
`bridge_forwarding` or `l2_reachable_via` is recommended; not decided
finally here, consistent with how ARCH-020 itself left `arp_neighbor`'s
exact name as this kind of implementation-time-adjacent naming call.

**Compatibility with the current architecture.** Same as LLDP/CDP:
`RelationshipObservation`/`RelationshipResolver` need no change. The
blocker is identical and shared: the forwarding table's evidence unit is
a MAC address, requiring the same MAC-to-canonical-identity resolution
mechanism (Section 6) LLDP/CDP also need.

**Acquisition complexity.** SNMP Bridge MIB (`dot1dTpFdbTable`) or its
Q-BRIDGE-MIB successor (`dot1qTpFdbTable`, VLAN-aware) — again a table
walk over the same `SnmpClient.walk_cmd` mechanism. Genuinely broad device
coverage on the acquisition side: virtually any managed switch that
speaks SNMP exposes this, including older/cheaper equipment that may not
implement LLDP/CDP at all — the broadest acquisition coverage of the
three MAC-dependent candidates, even though the *data itself* is weaker
per-entry than LLDP/CDP's.

**Coverage.** Broadest access-layer reach of the three — captures every
learned MAC on a managed switch, not only LLDP/CDP-speaking neighbors.
This is Bridge-MIB's real differentiator from LLDP/CDP, not a lesser
version of the same idea.

**Corroboration value.** A genuinely new relationship class (edge/access
attachment), not a strengthening of ARP or a duplicate of LLDP/CDP's
direct-link claim. Where a Bridge-MIB entry and an LLDP entry both exist
for the same switch/port, this report does not recommend treating them as
corroborating the same category (Section 5 above already explains why —
they are structurally different claims), but they remain independently
valuable evidence about the same physical area of the network.

**Architectural cost.** Identical to LLDP/CDP — the shared
MAC-to-canonical-identity resolution mechanism (Section 6) is the whole
cost. No ADR triggered, for the same reason.

**Testing and real-network verification.** Unit-testable using the exact
same pattern FEAT-010A already proved (stub `SnmpClient`, no live
network). Real-network verification is needed for the same class of risk
FEAT-010A already disclosed for its own table-walk OID parsing —
untested against a real Bridge-MIB agent's actual row-index encoding.

**Scope risk.** VLAN-awareness (`dot1qTpFdbTable` vs. the older,
VLAN-unaware `dot1dTpFdbTable`) is tempting to build fully from day one;
this report recommends starting with whichever table shape is simpler to
walk correctly and treating VLAN-scoped forwarding as a deliberate,
later refinement, not a Stage 1 requirement.

**Verdict: Defer — promising, prerequisite missing.** Same blocker as
LLDP/CDP; recommended as the natural second addition after LLDP, ahead of
CDP, because its access-layer coverage is genuinely complementary rather
than narrower-scope-of-the-same-thing.

---

## 6. The Shared Blocker: MAC-to-Canonical-Identity Resolution

Confirmed directly against current code, not assumed from ARCH-018:
`IdentityResolver` groups `IdentityObservation`s by `subject` only
(`identity/resolver.py:62-64`) — there is no MAC-keyed index anywhere in
`identity/resolver.py`, `identity/models.py`, or `Project`. `NmapProvider`
already emits a `mac_address` `IdentityObservation` per device
(`nmap_provider.py:415-418`, confirmed this session) — meaning the *data*
a MAC-to-identity lookup would need already flows through
`Project.observations` today; only the *index/lookup mechanism itself*
is missing. This is a meaningfully smaller prerequisite than it might
first appear: not a new observation type, not a new provider, not a new
ADR — a lookup structure over evidence already being collected.

This investigation recommends a dedicated ARCH investigation (ARCH-022,
Section 1) to design it properly rather than inventing it inline here,
for the same reason ARCH-017/ARCH-018 each got their own investigation
before implementation: whether the lookup should live on `IdentityResolver`
itself, as a new small resolver, or as a helper a provider calls directly;
how to handle a MAC observed by multiple independent sources with
conflicting associated IPs; and how a chassis ID's *subtype* (MAC address
vs. interface name vs. locally-assigned string, per LLDP/CDP's own
encoding) should gate whether resolution is even attempted are all real
design questions this report does not resolve, consistent with its own
"do not implement anything" charter.

---

## 7. Router Interface Ownership

**Operational value.** Tells you which router is the Layer-3 gateway for
a given subnet, and what that router's own interface addressing looks
like — genuinely useful context a technician documenting network
architecture wants, and not something NetworkMapper can currently infer
(it has no subnet or routing concept at all today).

**Evidence quality.** SNMP `ipAddrTable`/`ipAddressTable` reports a
router's *own* interface IP/netmask/ifIndex — a direct, high-confidence
fact about the router's own configuration. But it is not, on its own, a
claim about a *relationship between two discovered devices* the way every
other candidate in this report is — it is a fact about one device.

**Compatibility with the current architecture — the real problem.**
Forcing this into a `RelationshipObservation` requires a relationship
endpoint that is a *subnet*, not a `Device` — exactly the non-`Device`
endpoint case ADR-013's Relationship Endpoints section and ARCH-014
Section 4/9 already named and explicitly declined to design, and which
ADR-013 Section 14 already flags as a **candidate future ADR trigger**
("if a future sprint needs to represent a genuinely non-`Device`
relationship endpoint... engineering review should evaluate whether the
extension is implementation detail... or a big enough departure... to
warrant its own ADR or an amendment to ADR-013"). This investigation
confirms that trigger condition is reached by this candidate specifically,
if pursued as a relationship. Neither `RelationshipObservation` nor
`RelationshipResolver`'s `(subject, category)` model has anywhere for a
subnet to go today.

**A cheaper reframing worth preserving.** This investigation finds router
interface ownership does not need to be modeled as a relationship at all
to deliver most of its value: it could instead be collected as
*identity-layer* evidence about the router itself (new
`IdentityObservation` `property_name`s, e.g. `interface_ip`/`interface_subnet`,
or new `Device` fields) — sidestepping the endpoint-modeling problem
entirely, at real cost only to the "relationship" framing this sprint's
charter specifically asked about. This reframing is preserved here as a
distinct, smaller future idea, not evaluated further as a relationship
candidate, per the charter's own instruction to preserve rather than
discard.

**Acquisition complexity.** Cheap, reusing the exact
`SnmpClient.walk_cmd` mechanism already proved twice.

**Coverage.** Universal among SNMP-speaking IP devices in principle, but
the *use case* is specifically routers/L3 switches — narrow value even
where technical coverage is broad.

**Corroboration value.** Could, in principle, help a future consumer
distinguish "this ARP entry represents a real gateway relationship" from
"this ARP entry is incidental L2 adjacency" — but that would require new
resolver-level mechanism (cross-category reasoning `RelationshipResolver`
does not have and this investigation does not design), not merely new
evidence.

**Architectural cost.** The largest of any candidate in this report if
pursued as a relationship — a genuine ADR-triggering endpoint-model
extension, for a use case this investigation itself finds is better served
by a cheaper, non-relationship reframing.

**Testing and real-network verification.** Unit-testable via the same
established pattern; real-network verification needed for the same
row-index-parsing class of risk as every SNMP table-walk candidate.

**Scope risk.** The tempting adjacent work here — building a general
non-`Device` relationship-endpoint model — should be deferred until a
concrete, justified need for it exists (Routing evidence, ARCH-014's own
prior candidate, would need the identical model), not built speculatively
for this candidate alone.

**Verdict: Reject for now**, as a relationship-evidence candidate
specifically — the architectural cost (Section 6's endpoint-model
extension) is disproportionate to a use case this investigation itself
finds is better served outside the relationship model entirely. The
cheaper identity-layer reframing is preserved as a distinct future idea,
not rejected.

---

## 8. Default Gateway Corroboration

**Operational value.** Confirms, from the host's own perspective, which
device it believes is its gateway — genuinely useful and, importantly,
directionally complementary to ARP-corroborated-gateway evidence (which
tells you the gateway's perspective, not the host's). A technician
validating "is this really the customer's gateway, or did someone
misconfigure a host" gets real value from having both sides.

**Evidence quality.** Directional (a host's default gateway is not
symmetric), already IP-to-IP — `subject` = the host, `related_subject` =
its configured gateway IP — satisfying the translation requirement with
no additional step, structurally identical to ARP's own appeal
(ARCH-018 Section 5 already named this explicitly for WMI-sourced default-
gateway evidence). Category: closest fit among ADR-013's already-named
categories is **Routing** ("routes through") — a host's default gateway
is literally the first hop packets from that host route through — a
better fit than router interface ownership found for any existing
category.

**Compatibility with the current architecture.** No `RelationshipObservation`/
`RelationshipResolver` change needed, identical to every other candidate
in this report — the cost lives entirely in acquisition, not in the
resolver or observation model.

**Acquisition complexity — the real problem.** This is where this
candidate's story changes sharply from its evidence-quality promise.
Confirmed directly against current code: this codebase's only
evidence-collection mechanisms are nmap NSE scripts and SNMP
(`nmap_provider.py`'s `STANDARD_ENRICHMENT_SCRIPTS`/
`STANDARD_HOST_ENRICHMENT_SCRIPTS`, and `SnmpClient`) — no WMI client, no
SSH client, no local-subprocess execution boundary exists anywhere. A
host's own default gateway is not a fact any existing SMB/RDP NSE script
or SNMP MIB reliably exposes for a typical end-user workstation (SNMP
agents are rarely running on workstations in real MSP environments,
confirmed by this investigation's own reasoning, not merely assumed).
Acquiring it for real requires either a WMI query
(`Win32_NetworkAdapterConfiguration.DefaultIPGateway`, Windows-only,
needing a DCOM/RPC-capable client this codebase has no precedent for —
Python has no cross-platform stdlib WMI client; a library such as
`impacket` would be a new, heavier, more failure-prone dependency than
`pysnmp`) or SSH plus remote command execution (`ip route`/`route print`,
again a wholly new execution boundary). Either path is a materially larger
new capability than anything LLDP/CDP/Bridge-MIB require, all three of
which reuse infrastructure this codebase already has proven twice.

**Coverage.** The underlying fact (every IP host has a default gateway)
is universal, but real-world *acquisition* coverage is the worst of the
five candidates in this report: it needs admin-level Windows credentials
(WMI) or valid SSH credentials (Unix), a materially higher bar than SNMP's
simple community string or nmap's typically-credential-free scripts — in
a credential-constrained MSP engagement (the realistic case this report
weighs throughout), this is a real, not theoretical, coverage limiter.

**Corroboration value.** Genuinely valuable if it existed — the
opposite-direction complement to `arp_neighbor` evidence Section 1
already named. This is the strongest argument *for* eventually building
it, not against it; the finding here is about cost and sequencing, not
about the evidence being unwanted.

**Architectural cost.** Not a `RelationshipObservation`/`RelationshipResolver`
cost at all — the entire cost is a new execution/credential boundary this
investigation finds is disproportionate to build for this one candidate
alone, compared to the leverage the shared MAC-to-identity mechanism
provides across three other candidates simultaneously.

**Testing and real-network verification.** Unit-testable for whatever
parsing logic sits on top of a WMI/SSH response, but the acquisition layer
itself would need real Windows/Unix hosts to validate against — a larger,
more environment-dependent verification burden than any SNMP-based
candidate in this report, none of which need more than a stub client to
unit test and a single real device to smoke-test.

**Scope risk.** Building a general-purpose WMI or SSH execution boundary
"while we're at it" for other future evidence sources is exactly the kind
of adjacent work this report recommends deferring — that boundary's own
design (credential model, platform support, failure semantics) deserves
its own investigation if and when it's actually justified, not as a
byproduct of one relationship-evidence candidate.

**Verdict: Reject for now.** Best evidence shape of any candidate in this
report, but the acquisition cost is disproportionate relative to the
three candidates already unlockable by one shared, smaller mechanism.
Preserved explicitly as a strong future candidate once a WMI or SSH
execution boundary is independently justified.

---

## 9. Ranking

Ranked by justified engineering value — not novelty, not implementation
convenience, per the charter's own instruction — reflecting how well each
candidate is worth eventually pursuing and in what order, given that none
clears "promote now" today:

1. **LLDP** — highest evidence quality, broadest multi-vendor coverage,
   cheapest acquisition path (reuses proven `SnmpClient.walk_cmd`
   infrastructure) among the three sharing the MAC-to-identity blocker.
   First priority once that prerequisite exists.
2. **Bridge/MAC forwarding tables** — genuinely complementary
   access-layer coverage, not a lesser LLDP; broadest acquisition-side
   device coverage of the three. Natural second addition.
3. **CDP** — identical blocker and mechanism to LLDP, narrower
   vendor-specific coverage. Cheap, low-priority follow-on once LLDP's
   shared plumbing exists; not independently justified on its own.
4. **Default gateway corroboration** — best individual evidence shape of
   any candidate, but isolated payoff relative to its acquisition cost
   (a wholly new WMI/SSH execution boundary). Worth building once that
   boundary is independently justified, not before.
5. **Router interface ownership** — largest architectural cost (an
   ADR-triggering non-`Device` endpoint extension) for a use case this
   investigation itself finds is better served by a cheaper,
   non-relationship reframing. Lowest priority as a relationship
   candidate specifically.

---

## 10. Recommended Sequence

Not a roadmap commitment — offered per this report's own scope, for
engineering review to accept, modify, or decline:

**ARCH-022 — MAC-to-Canonical-Identity Resolution** (prerequisite
investigation, Section 6). Design questions this report explicitly leaves
open: where the lookup lives, how conflicting MAC-to-IP associations are
handled, and how chassis-ID subtype gates resolution attempts.

**FEAT-011A (contingent on ARCH-022's outcome, not authorized here) —
LLDP-neighbor relationship provider**, the first consumer of ARCH-022's
mechanism, mirroring FEAT-010A's own provider shape closely (same
`SnmpClient.walk_cmd` pattern, same `EnrichmentProvider` template).

**FEAT-011B/C (separate future sprints, not authorized here) — Bridge/MAC
forwarding-table provider, then CDP provider**, each a comparatively small
addition once ARCH-022's mechanism and FEAT-011A's provider pattern exist.

**Not recommended for near-term pursuit, explicitly preserved rather than
discarded:** default gateway corroboration (Section 8, gated on an
independently-justified WMI/SSH execution boundary) and router interface
ownership as a relationship candidate (Section 7, gated on an
independently-justified non-`Device` endpoint model) — its cheaper
identity-layer reframing (Section 7) is also preserved as a smaller,
separate idea worth a future look on its own merits.

---

## 11. Scope Confirmation

Per the charter's own instruction: no roadmap item is added by this
report; no ADR is filed by this report (Section 1); no code is proposed;
`RelationshipResolver`/`IdentityResolver`'s own algorithms are not touched
or redesigned by any recommendation here. This investigation's only
concrete recommendation is which prerequisite investigation to charter
next (Section 10), not which provider to build.
