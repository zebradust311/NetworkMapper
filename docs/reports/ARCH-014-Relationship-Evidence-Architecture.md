# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: Yes — Section 8 recommends that a future sprint record one or
more ADRs formalizing a relationship-evidence model, following the same
Investigation → Architecture Review → ADR sequence ADR-009
(ARCH-002A/ARCH-002B) and ADR-010 (ARCH-012) already used. Per this
sprint's explicit scope ("Do not create ADRs. Wait for engineering
review."), no ADR is recorded here.

Recommended Next Sprint:
A dedicated architecture investigation into stable device identity across
rescans (Section 7 names this a prerequisite, not a nice-to-have — at
least two of the highest-value relationship categories evaluated here
produce evidence endpoints that don't yet resolve reliably to a `Device`).
This is offered as a candidate, not a decision — per this sprint's scope,
selecting the next sprint is an engineering-review decision.

---

## 1. Executive Summary

This investigation was chartered directly by ARCH-013's closing finding:
"Phase 3's single most consequential open question is not which
enrichment provider to build next — it is whether `NetworkGraph` gains a
relationship/topology model before or after the first Phase 3 provider
that would benefit from one." Three independent prior investigations
(FEAT-003E, ARCH-003, ARCH-012) each hit the same wall — relationship
evidence has nowhere in the canonical model to go — without being asked
to solve it. This investigation is that dedicated look.

The central finding is that NetworkMapper already has a proven,
repeatedly-validated architectural pattern for exactly this class of
problem, and the work here is to extend it rather than invent something
new: ADR-008 separates discovery (immutable, observed) from
interpretation (adjustable, derived); ADR-002 separates a rule's evidence
from its conclusion; ADR-010 requires corroboration rather than
overwrite when two sources describe the same fact. Relationship evidence
fits the same shape one level up — a **relationship observation** is
discovery, immutable and provider-attributed; a **corroborated
relationship** is interpretation, derived from one or more observations
and adjustable as more evidence arrives; **topology** (out of scope here)
is presentation, the same role Markdown/CSV exporters already play for
device evidence.

The second finding is structural, not philosophical, and it is the
reason this can't be solved by simply adding fields to `Device`: every
relationship category evaluated in Section 3 requires **two** endpoints,
and — unlike every `EnrichmentProvider` built so far, which by
construction (ADR-010) only ever writes into a `Device` NetworkMapper has
already discovered — a relationship's evidence can arrive with one
endpoint identified and the other not yet a `Device` at all (an LLDP
neighbor chassis ID for a switch NetworkMapper hasn't scanned; a VM
reported by a hypervisor's API that may or may not be independently
network-visible). No existing NetworkMapper abstraction handles a
partially-resolved fact, and this is a genuinely new architectural
question, not a rediscovery of one already answered.

The third finding is that relationship *identity* cannot be solved
independently of *device* identity. `NetworkGraph.add_device`
(`networkmapper/core/network_graph.py:15-19`) keys devices by IP address
alone, with no concept of "the same device, rescanned" versus "a new
device." ADR-008 already named this gap in its own Future Work
("a mechanism for recording, storing, and reconciling manual overrides
with subsequent rescans") and left it unresolved. A relationship between
two devices cannot be recognized as *the same relationship* across two
scans if the devices at its endpoints cannot themselves be recognized as
the same devices across two scans. This makes stable device identity a
blocking prerequisite for relationship lifecycle, not an independent,
parallel gap.

No production code, data model, or provider is proposed for change by
this report.

---

## 2. Relationship Philosophy

NetworkMapper's classification subsystem already draws a hard line
between observation and conclusion, and does so at two different layers
independently: `RuleResult` separates a single rule's evidence from its
suggested `device_type` (ADR-002), and ADR-008 separates recorded
discovery from adjustable interpretation across a device's lifetime,
explicitly generalizing the same principle "to the relationship between
discovery and interpretation across the device's lifetime."

Relationship evidence should extend that same line, not draw a new one:

- **Relationship Observation** — a single provider's report that two
  identified endpoints appear related in some way, at some point in
  time. Immutable once recorded, exactly as ADR-008 requires for device
  discovery: "A recorded observation is immutable. A subsequent scan
  creates a new observation."
- **Corroborated Relationship** — the interpretation derived from one or
  more Relationship Observations describing the same endpoints and
  category. Adjustable: as more observations arrive (or stop arriving),
  the corroborated relationship's confidence and validation status
  change, but the underlying observations that produced it are never
  edited or deleted, mirroring how re-classification never edits a
  device's discovery fields.
- **Topology** — a rendering or interpretation of the corroborated
  relationship set, explicitly out of this investigation's scope
  (charter: "This investigation does not design topology rendering").
  Its relationship to Corroborated Relationships should be the same
  read-only, presentation-layer relationship exporters already have to
  `Project` (`docs/architecture/overview.md`, "Exporters" section) —
  topology consumes corroborated relationships; it does not decide what
  counts as one.

This is not a new philosophy. It is ADR-008's own stated generalization,
applied to the one category ADR-008 explicitly left for "future schema...
work": relationships were never in scope for ADR-008, ADR-009, or
ADR-010, each of which scoped itself narrowly and deliberately (ADR-009's
Context: "per-service portion of the discovery record... does not
undertake the full discovery/interpretation schema separation ADR-008
left open"). Framing relationships as Observation → Interpretation is the
natural next narrow scope in that same lineage, not a departure from it.

The charter's own framing — "Relationships are observations. Relationships
are not assumptions. Topology is an interpretation of corroborated
relationship evidence." — is this section's conclusion restated as a
premise, and this investigation finds nothing in the current architecture
that argues against it. Every existing corroboration mechanism in the
codebase (ADR-010's fallback-only merge, RULE-004's SNMP-checked-last
evidence-hierarchy) already treats "observed by two independent sources"
as stronger than "observed by one," never as a reason to discard the
weaker single-source case — the same posture a relationship evidence
model needs.

---

## 3. Relationship Categories

Each candidate category is assessed against evidence NetworkMapper
already collects or has already investigated collecting (ARCH-003,
ARCH-012, FEAT-003E, ARCH-013 Section 8), not against a hypothetical
future provider. "Naturally emerges" means a concrete, already-identified
evidence source produces it; "does not naturally emerge" means no
evidence source evaluated in this project's history produces it, and
speculative design of one is out of scope.

**Service — device hosts service.** NetworkMapper already models this
relationship category today, without having named it as one.
`ServiceEvidence` (`networkmapper/core/models.py:22-54`) correlates a
port with the service/product observed on it — that is a
device-hosts-service fact, one-ended in the current representation
(the "service" side has no independent identity; it exists only as an
attribute of the device). This is the strongest existing precedent for
what a relationship record's evidence shape should look like (a
correlated, named-field record per ADR-009), even though today it is not
framed as a relationship. Worth naming explicitly because it means
NetworkMapper's evidence pipeline has already validated one relationship
category end-to-end (collection → representation → classification
consumption) without a dedicated relationship model — a data point in
favor of extending the existing per-device evidence pattern for
one-ended relationships rather than assuming every category needs a
two-ended edge model.

**Physical — device connected to device.** Requires LLDP/CDP or SNMP
bridge-MIB (`dot1dTpFdbTable`) evidence, neither of which NetworkMapper
collects today. FEAT-003E found this "fundamentally relationship data
between two devices, not a fact about either one in isolation" and that
"there is nowhere in `NetworkGraph` to record 'device A's port 3
connects to device B's port 7'" (FEAT-003E, LLDP/CDP section). Does not
naturally emerge from current providers; would require a new provider
(FEAT-003E already confirmed `DiscoveryProvider` architecturally
anticipates this) and the relationship model this investigation is
scoped to inform.

**Logical — device belongs to VLAN.** Requires SNMP Q-BRIDGE-MIB
(VLAN-tagged interface membership), not collected today. Structurally
this is closer to a device-to-entity relationship (device → VLAN) than
device-to-device, meaning VLAN itself would need to be a modeled entity,
not just a second `Device`. No current evidence source produces it; does
not naturally emerge yet.

**Routing — subnet routed through gateway.** Requires SNMP
`ipCidrRouteTable` or an equivalent local routing-table query, not
collected today. This is the clearest case where a relationship endpoint
is not a `Device` at all — a subnet is closer to `ENGINEERING.md`'s
long-unbuilt "Network" model (Core Principle 5: "Models contain data.
Examples: Device, Interface, Link, Network") than to anything currently
implemented. Does not naturally emerge from current providers, and
uniquely among the categories evaluated here, its second endpoint isn't
even device-shaped.

**ARP — device's MAC observed via gateway/local host.** Partially
already collected in a different form: `NmapProvider._extract_mac_address()`
(`networkmapper/discovery/nmap_provider.py:428-431`) already populates
`Device.mac_address` from Nmap's own ARP-based local-subnet discovery.
Today this is stored as a plain device attribute, not framed as a
relationship — "this device's own MAC" is not the same claim as "this
device's MAC was observed via ARP through this specific gateway," which
is what the charter's own worked example (LLDP + Routing Table + ARP →
Corroborated Relationship) requires. The identity-level fact (a device
has a MAC) already exists; the relationship-level fact (which gateway
observed it, corroborating a device→gateway relationship) does not.
Closest category to already being partially instrumented, but the
relationship framing itself does not yet exist.

**Administrative — managed by.** No evidence source identified anywhere
in this project's discovery history produces this. Every relationship
category above is *discovered* — observed as a side effect of scanning
or querying a device. "Managed by" is fundamentally different in kind:
it is asserted by a human or imported from an external system (a CMDB,
a ticketing system), not observed on the wire. This investigation finds
that administrative relationships likely belong to a different evidence
category altogether — human-asserted or imported fact, not discovery
evidence — and recommends that any future relationship model explicitly
distinguish "observed by a provider" from "asserted by a person," rather
than forcing both through the same corroboration pipeline. This
distinction is new; it does not exist for device evidence today because
every current `Device` field is provider-observed, never human-asserted
(ADR-008's discovery/interpretation split does not currently have a
third "human assertion" category either — device *interpretation*, like
a manual device-type override, is explicitly named as future work in
ADR-008, not yet built).

**Service — service depends on service.** No evidence source identified.
This is application-layer dependency tracing (which NetworkMapper does
not do and has no discovery mechanism for — nothing resembling APM or
distributed tracing exists in any provider evaluated across Phase 1-3).
Does not naturally emerge and no near-term evidence source changes that;
flagged as out of realistic scope rather than deferred pending a
specific provider.

**Virtualization — VM hosted by hypervisor.** Partial precedent exists:
`HYPERVISOR` is an established `DeviceType` (`networkmapper/core/models.py:18`),
and the `vmware-version` NSE script (FEAT-003E, "VMware — existing and
additional NSE scripts" section) already populates
`ServiceEvidence.version` for ESXi/vCenter hosts. But no VM entity model
exists, and ARCH-013 Section 8 already flagged VMware as one of the two
Phase 3 candidates "most likely to immediately re-encounter Section 6's
leading debt item" because "a VMware API exposes host-to-VM
relationships" with "no field to receive" them. This category also
raises a distinct identity question this investigation surfaces in
Section 7: a VM reported by a hypervisor's API may *also* be a `Device`
NetworkMapper already discovered independently at its own IP — resolving
"is this the same entity" is a corroboration/identity problem, not a
collection problem.

**Geographic — device located at site.** Closest existing precedent of
any category not already covered by Service: `snmp_sys_location`
(`networkmapper/core/models.py:90-91`, populated by FEAT-005) is
administrator-entered free text describing physical location, collected
today as a plain `Device` string field, not a relationship to a modeled
Site entity. Naturally emerges as raw text today; does not naturally
emerge as a *relationship* (device → Site) because no Site entity exists
to be the other endpoint, and unlike a switch or gateway, a "site" would
need to be an entity NetworkMapper invents from evidence rather than one
it discovers directly (nothing on the wire announces "you are at Site
X" the way a device announces its own hostname).

**Summary:** exactly one category (Service — device hosts service)
already has a working, validated evidence-to-model-to-classification
path today, just not named as a relationship. Two categories (Physical,
ARP-corroborated-gateway) have partial precedent in already-collected
device-level facts but no relationship framing. Four categories
(Logical/VLAN, Routing, Virtualization, Geographic) require either a new
non-device entity type or a new provider with no current evidence
source. Two categories (Administrative, Service-depends-on-service) do
not naturally emerge from anything NetworkMapper's discovery model does
today, and Administrative specifically appears to need a structurally
different evidence category (human-asserted, not provider-observed).

---

## 4. Evidence Sources

Per the charter, this section evaluates architectural implications only
— no provider is designed.

**LLDP / CDP.** Link-layer multicast protocols; FEAT-003E already found
`NmapProvider`'s IP-based TCP/UDP scanning cannot observe them, requiring
either passive L2 capture or SNMP LLDP-MIB/CDP-MIB queries. The
architectural implication beyond FEAT-003E's own finding: LLDP/CDP
neighbor data names a *local port* on the reporting device (typically an
SNMP `ifIndex`) as one side of the relationship. A `Device`-to-`Device`
relationship record alone would discard which physical interface was
involved — the same interface-granularity problem `ENGINEERING.md`'s
named-but-unbuilt `Interface` model already anticipates. LLDP/CDP is
also the clearest case of the "unresolved endpoint" problem from Section
1: a neighbor's reported chassis ID may not correspond to any `Device`
NetworkMapper has scanned.

**SNMP interface MIBs (`ifTable`/`ifXTable`).** Per-interface facts about
the interface itself (description, speed, admin/oper status) — not,
by themselves, relationship evidence. Architectural implication: this is
the evidence that would populate an `Interface` model if one existed,
and it is a *prerequisite* for LLDP/CDP evidence to be fully expressed
(LLDP's local-port field references an `ifIndex` this MIB would resolve
to a human-meaningful interface). Collecting `ifTable` without
`Interface` existing would face the same "nowhere to put it" finding
FEAT-003E already recorded for the SNMP interface metadata it evaluated.

**Bridge MIB (`dot1dTpFdbTable` / Q-BRIDGE-MIB).** Produces a
MAC-address-to-switch-port forwarding table — the mechanism that would
back Physical and Logical/VLAN relationship evidence without LLDP.
Architectural implication distinct from LLDP: its evidence unit is a MAC
address, not a `Device`. `Device.mac_address` exists as a plain field
today with no index or lookup structure — resolving a bridge-MIB MAC
entry to a specific `Device` would require a MAC→Device resolution
capability NetworkMapper does not currently have anywhere (not in
`NetworkGraph`, which is IP-keyed only, and not in any classification or
evidence helper).

**Routing tables (SNMP `ipCidrRouteTable`, or a local `ip route`/WMI
query).** As noted in Section 3, the far endpoint of a routing
relationship is a subnet or a next-hop IP, not necessarily a discovered
`Device`. Architectural implication: this is the strongest case among
all evaluated sources for needing a non-`Device` endpoint type (a
Network/subnet entity) rather than only solving the "endpoint not yet
discovered" problem LLDP/CDP and VMware raise — here the endpoint may
never be a `Device` at all, by definition.

**ARP (SNMP `ipNetToMediaTable`, or a local `arp -a`/equivalent).**
Produces IP-to-MAC bindings, observed from the perspective of whichever
host or device answered the query. Architectural implication: this is
corroborating evidence for an *existing* device-level fact
(`Device.mac_address`, already populated by Nmap's own ARP behavior per
Section 3) combined with a *new* relational claim (which gateway or host
observed the binding). This is the cleanest fit among all sources
evaluated for a corroboration example, because it doesn't introduce a
new endpoint type — both the device and the observing gateway are
already `Device`-shaped.

**WMI.** ARCH-013 Section 8 already established that most WMI evidence
(OS, computer name, domain, installed software/hardware inventory)
is architecturally identical to what SNMP/SMB/RDP already proved — a
device-level fact reached via a credentialed query. Some WMI classes are
inherently relational, though: `Win32_NetworkAdapterConfiguration`
reports a default-gateway IP and DNS server IPs per host, and
`Win32_LogonSession`/domain-controller queries report user- and
domain-membership relationships. Architectural implication: WMI is not
uniformly one shape — it produces both plain `Device` facts (already
proven safe to extend, per ARCH-013) and relationship-shaped facts (which
hit this investigation's findings) from the same credentialed connection,
meaning a future WMI `EnrichmentProvider` would need to route its own
results into two different downstream representations depending on
which WMI class answered.

**VMware (vCenter/ESXi API).** As discussed in Section 3, the richest
relationship-shaped evidence among near-term candidates (host-to-VM), and
the clearest case of the identity-resolution question in Section 7: a
reported VM may already exist in `NetworkGraph` as an independently
discovered `Device`, and nothing in the current architecture can
recognize that.

**Redfish.** Chassis/power/drive/network-interface component
relationships. Architectural implication distinct from every other
source evaluated: Redfish relationships are largely *containment*
("this NIC is part of this chassis"), not *peering* ("this device
connects to that device"). A relationship model built only around
symmetric device-to-device edges (the shape every other category in
Section 3 assumes) would not naturally represent containment without
either a third relationship shape or treating "part of" as a directional
category within the same model — a design question a future Redfish
investigation should expect to face, not one this investigation resolves.

**SSH.** Confirmed, consistent with ARCH-013 Section 8, to carry no
relationship category of its own — SSH is a channel; whatever runs over
it (`ip route`, `arp -a`, `lldpctl`) determines which category above
applies. Its architectural implications are inherited entirely from the
command executed, not from SSH itself.

---

## 5. Corroboration Strategy

NetworkMapper already has two independently-arrived-at corroboration
mechanisms, and Section 5 of ARCH-013 names both explicitly: at the
merge layer, `EnrichmentProvider`'s fallback-only rule (ADR-010) means a
later source can fill a gap but never overwrite an earlier source's
fact; at the classification layer, `first_matching_identifier`'s
SNMP-checked-last ordering (RULE-004,
`networkmapper/classification/evidence_helpers.py:67-104`) means a
weaker source is only consulted after every stronger one has already
been checked. Both converge on the same directional bias — earlier or
stronger evidence is preferred, never silently replaced.

Relationship corroboration should follow this same bias, but it cannot
reuse the *mechanism* unmodified, because the two existing mechanisms
solve a structurally different problem:

- `EnrichmentProvider`'s fallback-only merge collapses multiple sources
  into **one** field value per device (first writer wins; the fact that
  three sources originally agreed is not retained anywhere after the
  merge — only the final value is).
- Relationship corroboration, per the charter's own worked example
  (LLDP + Routing Table + ARP → Corroborated Relationship), depends on
  being able to say *how many independent sources* agree, which requires
  retaining each contributing observation rather than collapsing them
  into a single merged value. Collapsing away the individual
  observations the way `EnrichmentProvider._merge()` does would destroy
  the exact information corroboration needs to work.

This means relationship corroboration is closer in shape to
`RuleResult`'s evidence-collection model (every evaluated rule's result
is retained via `get_last_rule_results()`, not just the winning one —
ADR-004) than to `EnrichmentProvider`'s field-merge model. A
**Corroborated Relationship** should be understood as a value derived
from a retained collection of **Relationship Observations**, not as a
single record progressively overwritten by each new source.

On confidence: `RuleResult.confidence_contribution` has existed, unused,
in every classification result since ADR-002 — Phase 2's own retrospective
(ARCH-013 Section 7) names this restraint as a deliberate, validated
principle: "Prefer deterministic, explainable reasoning over confidence
scoring or heuristics that can't be traced to specific evidence." This
investigation finds no reason relationship confidence should diverge from
that principle. A numeric confidence score for a relationship would face
the same objection ARCH-013 raises for classification: it cannot
currently be traced to specific evidence in a way a technician could
verify. A discrete, explainable label — "single-source," "corroborated
(N independent sources)," "conflicting" — is consistent with how
first-match-wins classification is already explained (a category derived
from countable, named evidence) and should be preferred over any
score-based design until a specific, evidence-driven reason to depart
from that pattern emerges (mirroring KNOWLEDGE-LIFECYCLE.md's own bar:
a pattern earns promotion only once corroborated across independent
cases, not on a single observation).

On conflicting observations (two sources disagree about the same
relationship, e.g. LLDP and CDP each reporting a different neighbor for
the same local port): the dominant precedent across the codebase is
"corroborate rather than override," never "arbitrate and discard." ADR-008
requires that "a recorded observation is immutable" and that
disagreement is resolved by keeping both observations, not erasing one.
This investigation recommends the same posture for relationships:
conflicting Relationship Observations should both be retained with their
provenance, and presenting or resolving the conflict is topology's
concern (out of scope), not the evidence layer's. This avoids the evidence
layer making a silent, unexplainable choice — the same failure mode
ADR-009 rejected a generic metadata dictionary specifically to avoid at
the device-evidence layer.

---

## 6. Provenance Strategy

The charter asks whether existing provenance concepts should be extended
or generalized. Two existing shapes are candidates, and they answer the
question differently, which is itself the finding worth recording.

`Device.discovery_sources: list[str]` (`networkmapper/core/models.py:113`,
also used directly by `SnmpEnrichmentProvider.enrich()`,
`networkmapper/discovery/snmp_provider.py:96-98`) is the current
device-level provenance mechanism. It answers only "which provider(s)
contributed to this device," as a flat list of names — it carries no
timestamp, no per-field attribution (which source populated *which*
field), and no run/scan identity. It is sufficient for `Device` today
because `EnrichmentProvider`'s fallback-only merge already guarantees at
most one source ever populates a given field, so "which sources touched
this device at all" is enough information to reconstruct provenance
after the fact.

`Observation` (`networkmapper/knowledge/models.py:120-138`) is a richer,
already-solved shape: `captured_at`, `ObservationScan` (`profile`,
`networkmapper_version`, mirroring `RunMetadata`'s `scan_profile`/
`version` fields per its own docstring), and a structured
`review_history` of who acted on the observation and when. Critically,
`Observation` already models *one capture event*, not a mutable running
record — exactly the shape Section 5 concluded relationship evidence
needs (a retained collection of individual observations, not one
collapsed value).

This investigation finds that relationship-evidence provenance should
generalize the `Observation` shape, not extend `Device.discovery_sources`.
The reasoning: `discovery_sources`'s flat-list-of-names shape is
sufficient specifically *because* device evidence is merged down to one
value per field (Section 5's fallback-only merge). Relationship evidence
is explicitly not merged down that way — Section 5 requires retaining
each contributing observation — so its provenance needs the same
per-observation granularity `Observation` already has: which provider,
which run, at what time, contributed *this specific* claim. Extending
`discovery_sources` (a per-device, cumulative list) to relationships
would silently reintroduce the single-value-collapse problem Section 5
just ruled out.

Concretely, the four provenance elements the charter names — originating
provider, observation source, observation date, supporting observations
— map directly onto fields `Observation` already has (`ObservationScan`,
implicitly the provider through the evidence shape, `captured_at`) plus
one new one specific to relationships: "supporting observations" is a
list of sibling Relationship Observations, which has no analog in
`Observation` today because a single `Observation` is presently a
complete, self-contained record with no notion of corroborating with
another `Observation`. This is new territory `Observation` itself does
not yet cover, not a solved problem being rediscovered.

"Validation status," the charter's fifth named provenance element, maps
naturally onto `ObservationStatus`
(`networkmapper/knowledge/models.py:8-21`) — already a human-controlled
lifecycle enum (`NEW`/`UNDER_REVIEW`/`VALIDATED`/`IMPLEMENTED`/`ARCHIVED`)
with the explicit, load-bearing property that "state transitions never
occur automatically." Whether a Corroborated Relationship's validation
status should reuse this exact enum or a relationship-specific variant is
future design work, but the *pattern* — human-gated status transitions
that never influence runtime behavior on their own — is already proven
and should carry over.

---

## 7. Stable Identity Assessment

**Endpoint identity is the blocking constraint, not relationship
identity itself.** `NetworkGraph.add_device`
(`networkmapper/core/network_graph.py:15-19`) is a first-write-wins dict
keyed by IP address, with no concept of the same physical device
persisting across a changed IP, a rescan, or a re-registration under DHCP.
ADR-008 named this exact gap in its own Future Work section ("a mechanism
for recording, storing, and reconciling manual overrides with subsequent
rescans... How that is preserved is future work; this ADR establishes
only the principle") and it remains unresolved as of this investigation.
A relationship cannot be recognized as "the same relationship, seen
again" unless both of its endpoints can first be recognized as "the same
device, seen again." This investigation did not find any relationship
category in Section 3 that could sidestep this dependency — even the
most self-contained category (Service — device hosts service, already
partially proven) implicitly relies on `Device` identity being stable
enough that re-observing the same service on a rescan is meaningful.

**Relationship identity, once endpoint identity is solved, is a
composite key problem, not a hard one.** A natural candidate shape is
(endpoint A identity, endpoint A interface, endpoint B identity, endpoint
B interface, category) — analogous to how `ServiceEvidence` already
correlates port + protocol + service into one addressable record
(ADR-009) rather than independent lists. The interface component of that
key is only meaningful once an `Interface` concept exists (Section 4);
until then, relationship identity would need to degrade to
(endpoint A identity, endpoint B identity, category), which is
sufficient for Service, ARP-corroborated-gateway, and Virtualization, but
loses the per-port granularity Physical (LLDP/CDP) evidence naturally
carries.

**Endpoints may not resolve to an identity at all.** Section 3 (LLDP/CDP,
Virtualization) and Section 4 (LLDP/CDP, Routing) both surface the same
finding independently: a relationship observation's second endpoint may
be (a) a `Device` NetworkMapper has already discovered, (b) a `Device`
NetworkMapper has not yet discovered but could recognize once it does
(e.g. a switch chassis ID that would match a device scanned in a later
run), or (c) never a `Device` at all (a subnet, in the Routing case). No
current NetworkMapper abstraction distinguishes these three cases — every
existing evidence type assumes its subject is already a resolved
`Device` (this is, structurally, exactly what ADR-010 requires of an
`EnrichmentProvider`: "never introduces a `Device` for an IP not already
present"). A relationship evidence model must be able to represent case
(b) and (c) without that representation becoming, itself, an unauthorized
way to introduce new devices into `NetworkGraph` — a real tension between
"preserve what was observed" (ADR-008) and "don't let evidence-of-a-thing
silently become the thing" (ADR-010's own boundary).

**Lifecycle and staleness are a new category, not a relationship-specific
one.** Neither a `Device` nor its evidence fields currently express "not
observed on the most recent run" versus "observed and unchanged" —
`Device` has no timestamp of any kind on any field, and a rescan's
current, undesigned behavior (per ADR-008's own Future Work) is not
resolved even for devices. Relationships will need this same concept
(a link that was corroborated last month but not re-observed this run is
meaningfully different from one just discovered), and this investigation
recommends it be designed once, generally, rather than invented
separately for relationships and then retrofitted onto `Device` later.

**Conflicting observations** are addressed in Section 5 (Corroboration
Strategy) as an evidence-retention question, not an identity question;
they are only relevant to identity insofar as two conflicting
observations about the same endpoint pair must still be recognized as
describing the *same* relationship identity (in conflict) rather than two
different relationships — which again depends on the composite-key
resolution above already working.

---

## 8. Architectural Recommendations

These are findings offered for engineering review, not implemented or
authorized decisions. Consistent with `ENGINEERING.md`'s AI Execution
Policy, architecture changes require explicit sprint approval; nothing
below should be treated as approved.

1. **Extend ADR-008's discovery/interpretation split with a third,
   named layer specifically for relationships** — Relationship
   Observation (discovery, immutable) → Corroborated Relationship
   (interpretation, adjustable) → Topology (presentation, out of scope) —
   as Section 2 describes, before any relationship-evidence provider is
   built. This should be recorded as its own ADR, following the same
   Investigation → Architecture Review → ADR sequence ADR-009 and ADR-010
   both used, once engineering review selects a next sprint.

2. **Represent relationship evidence as an explicit, named record — never
   a generic edge or metadata dictionary** — consistent with ADR-009's
   explicit rejection of a generic per-port metadata dictionary and the
   same reasoning: `RuleResult.reason` and every rule's explainability
   already depend on evidence living in named fields, not open-ended
   containers. A relationship record's minimum shape, per Sections 3-7,
   needs: two endpoint references (each capable of representing a
   resolved `Device`, an unresolved-but-named entity, or a non-`Device`
   entity like a subnet), a category, and provenance per Section 6 — the
   exact field list is deferred to the future ADR, per this
   investigation's charter.

3. **NetworkGraph needs a second, distinct collection for relationship
   evidence — not a new field on `Device`.** A relationship is not a
   property of one device any more than a `RuleResult` is a property of
   one rule in isolation; it inherently spans two. This is consistent
   with `ENGINEERING.md`'s own long-named-but-unbuilt `Interface`/`Link`
   models (Core Principle 5) — this investigation's findings are, in
   effect, the first concrete evidence-architecture justification for why
   those models were named at the outset and never built: nothing before
   Phase 3 needed them.

4. **Stable device identity across rescans should be investigated as its
   own prerequisite, not folded into the relationship-evidence ADR.**
   Section 7 found this blocks relationship identity structurally, but it
   is also a pre-existing gap independent of relationships (ADR-008's own
   deferred Future Work). Solving it once, generally, avoids solving it
   twice — once informally for relationships, once later when ADR-008's
   original deferred rescan-reconciliation problem is finally addressed.

5. **Relationship corroboration should follow the existing
   "corroborate, never silently override" posture** already proven
   independently at two layers (ADR-010's merge, RULE-004's evidence
   hierarchy) — a third convergent instance of the same principle, per
   Section 5, not a new one requiring separate justification.

6. **Relationship confidence should remain a discrete, explainable label,
   not a numeric score**, consistent with `RuleResult.confidence_contribution`'s
   deliberate, still-unused restraint and ARCH-013's own recorded
   principle (Section 5) valuing determinism and explainability over
   confidence scoring.

7. **Relationship provenance should generalize `Observation`'s
   per-capture-event shape, not `Device.discovery_sources`'s flat list**,
   per Section 6's finding that relationship evidence is retained as a
   collection of discrete observations rather than merged down to one
   value.

8. **Administrative relationships ("managed by") likely need a distinct
   evidence category — human-asserted, not provider-observed** — and
   should not be forced through the same corroboration pipeline Sections
   5-6 describe for discovered evidence, per Section 3's finding.

---

## 9. Technical Debt

Debt identified or reconfirmed during this investigation, scoped per
`docs/reports/README.md` to items affecting maintainability, correctness,
or extensibility today — not feature requests.

**1. No relationship/topology model exists anywhere in the canonical
data model — reconfirmed, not newly discovered.** This is ARCH-013
Section 6's leading debt item; this investigation was chartered to
address it and reconfirms it independently through a fourth angle
(relationship-evidence architecture specifically, rather than any single
provider's collection needs). `NetworkGraph`
(`networkmapper/core/network_graph.py:13`) remains an IP-keyed
`dict[str, Device]` with no edges.

**2. `Device.discovery_sources` has no per-source timestamp or
per-field attribution.** Sufficient for device evidence today only
because `EnrichmentProvider`'s fallback-only merge guarantees at most one
source per field (Section 6). This is a real, if currently invisible,
limitation that would surface immediately if `Device`-level provenance
were ever asked the same question relationship provenance needs answered
("which source said this, and when") — worth naming now because Section
6 explicitly declined to extend this mechanism to relationships for
exactly this reason.

**3. No stable device identity across rescans — ADR-008's own deferred
Future Work, still unresolved, and now confirmed to block a second
subsystem.** Previously scoped only as a device-rescan-reconciliation
gap; Section 7 finds it also blocks relationship identity, which raises
its priority without this investigation itself proposing to resolve it
(explicitly deferred to Section 10).

**4. `NetworkGraph`/`Device` have no "not observed this run" concept.**
Surfaced in Section 7 as a lifecycle gap relationships will need;
confirmed to not exist for devices either, meaning it is pre-existing
debt this investigation's relationship-lifecycle question exposed rather
than created.

---

## 10. Future Work

Explicitly deferred, and not authorized by this investigation:

- The ADR(s) formalizing a relationship-evidence data model (Section 8,
  item 1) — requires its own sprint, following the ADR-009/ADR-010
  precedent.
- Concrete design of an `Interface`, `Link`, or `Network` model
  (`ENGINEERING.md` Core Principle 5) — this investigation establishes
  that relationships need a second collection distinct from `Device`, not
  its field list or type structure.
- A dedicated investigation into stable device identity across rescans —
  recommended as this investigation's own suggested next sprint (Status
  block), prerequisite to reliable relationship identity per Section 7.
- Any concrete relationship-evidence provider design — LLDP/CDP, SNMP
  bridge/routing/ARP, WMI, VMware, Redfish, or SSH-based collection.
  Section 4 evaluates architectural implications only, per the charter.
- A topology rendering or interpretation layer — explicitly out of this
  investigation's scope from the outset.
- A confidence-label taxonomy for corroborated relationships (Section 5
  names the direction — discrete labels like "single-source"/
  "corroborated"/"conflicting" — but does not define the full set or its
  semantics).
- A resolution mechanism for relationship endpoints that are not yet
  `Device` objects (Section 7's cases (b) and (c)) — named as an open
  tension between ADR-008 and ADR-010, not resolved here.
- Whether and how `ObservationStatus`'s human-gated lifecycle pattern
  should be reused, generalized, or reimplemented for relationship
  validation status (Section 6).
