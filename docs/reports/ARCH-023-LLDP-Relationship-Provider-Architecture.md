# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — every decision below is a direct, individually-checked
application of already-accepted policy (ADR-010/011/012/013) or an
already-established implementation precedent from this lineage
(ARCH-018/020/021/022, FEAT-010A/FEAT-011A), never a new rule. Section 10
checks this explicitly against every decision this investigation makes,
including the two genuinely new findings it surfaces (Section 3's
`lldpRemManAddrTable` finding, Section 4's extension of ARCH-022's
endpoint-bootstrapping gate to `lldpRemSysName`).

Recommended Next Sprint:
FEAT-012A — SNMP LLDP Neighbor Relationship Provider, scoped exactly by
Section 9's architectural-impact list. Offered as a recommendation, not a
decision — per scope, engineering review selects the next sprint.

---

## 1. Executive Summary

ARCH-021 ranked LLDP first among five relationship-evidence candidates;
ARCH-022 built the shared prerequisite (the MAC-to-Subject Reverse Index)
those candidates needed and, in its own Section 6, already worked through
LLDP's chassis-ID subtype problem in real depth. This investigation goes
further: it inspects the full LLDP-MIB table structure, not just the
chassis-ID field ARCH-022 focused on, and finds a genuinely new result
that changes the practical shape of the recommended provider.

**LLDP-MIB has a second, cheaper resolution path ARCH-018/021/022 never
evaluated.** `lldpRemManAddrTable` — the remote management-address
table — carries a neighbor's own management IP address directly, when the
neighbor advertises one (common on managed switches and routers). Where
present, this resolves a neighbor exactly the way ARP already does —
`related_subject` is already IP-shaped, no MAC-index lookup needed at
all — for the same reason ARCH-022 Section 6 found CDP's `cdpCacheAddress`
column potentially sidesteps LLDP's own chassis-ID translation problem.
No prior report in this lineage evaluated this table; it was not an
oversight this investigation is correcting so much as a genuinely new
angle a full LLDP-MIB read surfaces that a chassis-ID-only view does not.
Held to the same disclosure standard as every other protocol-specific
claim in this lineage: this is documented LLDP-MIB structure, not
verified against a live device.

**Every pipeline component FEAT-011A built is reused unmodified.** Tracing
LLDP against the current, just-implemented `EnrichmentProvider`,
`DiscoveryEngine`, `build_mac_index()`, and `receive_observations()`
confirms the investment ARCH-022 argued for is paying off exactly as
predicted: zero changes to any of them are needed for this, the first
real consumer. `IdentityResolver` and `RelationshipResolver` remain
untouched for the same reason FEAT-011A itself needed no resolver change.

**The endpoint-bootstrapping gate generalizes, and this investigation
applies it rather than re-deriving it.** LLDP's remote table also reports
a neighbor's advertised `lldpRemSysName` — third-party identity evidence
about a device NetworkMapper may not have independently discovered, the
same shape of question ARCH-022 Section 4 already resolved for
ARP-derived MAC evidence. Section 4 below applies that same principle
directly rather than treating it as a new question.

**Chassis-ID subtype gating, individually verified for all seven
IEEE-802.1AB-defined values, confirms ARCH-022's finding rather than
merely restating it:** two of seven (`macAddress`, `networkAddress`) are
resolvable; the remaining five are permanent, not temporary, gaps in the
current `RelationshipObservation` model, exactly as ARCH-022 Section 6
already established for the general case.

No production code is proposed for change by this report.

---

## 2. Direct Answers

**1. Which LLDP-MIB tables carry relationship evidence?**
`lldpRemTable` (chassis ID, port ID, system name/description,
capabilities — one row per neighbor) and `lldpRemManAddrTable` (neighbor
management addresses). `lldpLocalSystemData`/`lldpLocPortTable` describe
the *queried* device itself, not a neighbor — identity-adjacent, not
relationship evidence. Section 3.

**2. Which LLDP data becomes which observation type?** `lldpRemManAddrTable`
addresses and `macAddress`/`networkAddress`-subtype chassis IDs →
`RelationshipObservation`, category `connected_to`. `lldpRemSysName` →
potentially `IdentityObservation` for the neighbor, gated exactly like
ARCH-022 Section 4's ARP case. `lldpRemPortId`/`lldpRemPortDesc`,
`lldpRemSysDesc`, `lldpRemSysCap*`, and the five non-resolvable chassis-ID
subtypes → neither, named as future work. Section 4.

**3. What happens with each of the seven chassis-ID subtypes?**
`macAddress`(4) resolves via `build_mac_index()`; `networkAddress`(5)
resolves directly when IPv4; `chassisComponent`(1), `interfaceAlias`(2),
`portComponent`(3), `interfaceName`(6), and `local`(7) are permanently
unresolvable under the current model — not "not yet discovered," per
ARCH-022 Section 6's own already-established distinction. Section 5.

**4. How does LLDP consume the reverse index?** Exactly as built: one
`build_mac_index()` call per `enrich()` invocation (not per row, mirroring
`SnmpArpNeighborProvider`'s own `discovered_ips` computation), fed by
`receive_observations()`'s already-existing snapshot — no change to
either. Section 6.

**5. What are LLDP's failure semantics?** Timeout and unreachable-host
handling are unchanged from ARP's already-solved case. A genuinely new
question this investigation resolves by applying, not inventing, existing
precedent: LLDP's richer table needs a load-bearing/best-effort column
split, which `SnmpArpNeighborProvider`'s own Type-column precedent already
established the pattern for. Section 7.

**6. Where does this provider belong?** Squarely inside the existing
`EnrichmentProvider` architecture, as its own new class — every reason
ARCH-020 Section 8 gave for keeping ARP separate from
`SnmpEnrichmentProvider` applies at least as strongly here. Section 8.

**7. What changes, and what doesn't?** A new provider, a new `SnmpClient`
method, new diagnostics, and `application.py` wiring — the identical shape
FEAT-010A already took. `DiscoveryEngine`, `EnrichmentProvider`,
`build_mac_index()`, `receive_observations()`, `IdentityResolver`,
`RelationshipResolver`, `Project`, and every existing provider are
confirmed unchanged. Section 9.

**8. What testing is needed?** Unit tests for the client and provider
layers mirror FEAT-010A's own template directly. One new kind of test
this sprint specifically enables: a real two-provider orchestration test
(ARP + LLDP together) exercising FEAT-011A's "later providers may see
earlier evidence" guarantee against a genuine second consumer for the
first time, not a synthetic fixture. Live-network verification is
required for the same reasons, and to the same extent, FEAT-010A already
disclosed for its own OID parsing. Section 11.

**9. What should stay out of FEAT-012A?** An `Interface`/port model,
local system-data corroboration, device-capability data feeding
classification, a diagnostics-type consolidation refactor, and both
remaining ARCH-021 candidates (CDP, Bridge-MIB). Section 12.

**10. Is a new ADR required?** No — checked individually against every
decision this investigation makes, including the two new findings.
Section 10.

---

## 3. LLDP-MIB Structure

IEEE 802.1AB / LLDP-MIB, OID root `1.0.8802.1.1.2`. Structure and
semantics recalled from the standard's documented design, not verified
against a live device or the authoritative MIB module text in this
environment — the same disclosure this lineage already applies to every
other protocol-specific claim (FEAT-010A's OID parsing, ARCH-022's CDP
finding). Exact numeric OID suffixes below should be confirmed against
the actual MIB module at implementation time; the table *structure* is
standard IEEE 802.1AB design this investigation has high confidence in.

**`lldpRemTable`** — the primary relationship-evidence table. One row per
`(local port, neighbor)` pair, indexed by `(lldpRemTimeMark,
lldpRemLocalPortNum, lldpRemIndex)`. Adversarial review corrected an
overstatement here: this is not simply "three plain integer components."
`lldpRemTimeMark` uses the `TimeFilter` textual convention (RFC 2021) —
a polling-generation marker with its own query semantics (the normal
pattern is querying with `TimeMark=0` for the current view), not an
ordinary per-row key. Whether a straightforward lexicographic walk
behaves as expected against this convention is a separate, structural
unknown from the numeric OID suffixes discussed in Section 13 — named
here explicitly rather than folded into "numeric-suffix confidence is
not [high]," which understated it. `lldpRemLocalPortNum`/`lldpRemIndex`
remain ordinary integer index components with no comparable caveat.
Relevant columns: `lldpRemChassisIdSubtype`, `lldpRemChassisId`,
`lldpRemPortIdSubtype`, `lldpRemPortId`, `lldpRemPortDesc`,
`lldpRemSysName`, `lldpRemSysDesc`, `lldpRemSysCapSupported`,
`lldpRemSysCapEnabled`.

**`lldpRemManAddrTable`** — the neighbor's advertised management
address(es). This investigation's central new finding: where populated
(common for managed switches/routers, not universal), a management
address is already IP-shaped and resolves a neighbor exactly the way ARP
does, sidestepping the chassis-ID translation problem for that row
entirely.

Adversarial review found the original description of this table
understated its acquisition complexity, treating it as if reading a
simple per-row field. It is not. `lldpRemManAddrTable` is a **separate
table from `lldpRemTable`**, requiring its own walk — indexed by the
same `(lldpRemTimeMark, lldpRemLocalPortNum, lldpRemIndex)` prefix
`lldpRemTable` uses, *plus* the management-address subtype and value as
additional index components, because IEEE 802.1AB permits a neighbor to
advertise more than one management address. Consuming this table
correctly requires an index-prefix correlation back to `lldpRemTable`'s
rows — the same kind of correlation `SnmpArpNeighborProvider` already
performs between its `PhysAddress` and `Type` column walks (FEAT-010A),
but across two tables rather than two columns of one.

**Multiple management addresses are a real, not hypothetical, case**, and
this investigation resolves it by applying ADR-011's own evidence-
retention principle directly rather than inventing new behavior: emit one
`RelationshipObservation` per advertised management address, never pick
one arbitrarily. This is not a new pattern — it is the identical
one-fact-per-observation shape `SnmpArpNeighborProvider` already uses for
multiple ARP-table rows describing the same queried device's multiple
neighbors, applied here to one neighbor's multiple addresses.
`SnmpLldpNeighborEntry` (Section 9) should therefore carry
`management_addresses: list[str]`, not a single optional field.

**`lldpLocalSystemData` / `lldpLocPortTable`** — the *queried* device's
own advertised chassis ID, system name/description, capabilities, and
local port identifiers. Not relationship evidence — this describes the
device being queried, not a neighbor. Potentially identity-adjacent
(Section 12).

**`lldpStatistics` / `lldpConfiguration`** — operational/administrative
tables, no identity or relationship evidence. Out of scope, not evaluated
further.

---

## 4. Observation-Type Mapping

**`lldpRemManAddrTable` addresses and `networkAddress`/`macAddress`-subtype
chassis IDs → `RelationshipObservation`, one category.** This
investigation recommends one category, `connected_to` — ADR-013's own
already-named Physical category, and the category ARCH-018 already
designated LLDP as the primary evidence source for — regardless of which
column resolved a given row. Adversarial review found the original
justification for this overstated: the three resolution paths were
described as supporting "the identical underlying claim." They do not,
quite. A chassis ID is IEEE 802.1AB's designated *identity* claim for a
neighbor; a management address is a separate TLV whose defined purpose is
management *reachability*, not identity. Using it as a practical stand-in
for the neighbor's identity is a reasonable engineering approximation —
in practice the two coincide for the same physical device — not a claim
that the two fields are semantically identical. The recommendation is
unchanged (one category still correctly reflects that all three paths
corroborate the same physical fact, an LLDP link to this neighbor), but
the justification should name the approximation rather than assert
equivalence. This is distinct from `arp_neighbor`'s own separate category
(ARCH-020 Section 7): ARP and LLDP remain different *kinds* of claims (L3
cache knowledge vs. direct L2 protocol adjacency) and must not share a
category for the reason ARCH-020 already established; three different
*resolution mechanisms* for the same LLDP claim is not that same problem
and does not need three categories.

**`lldpRemPortId`/`lldpRemPortDesc` → neither, future work.** Per-port
detail with nowhere to go in `RelationshipObservation`'s `(subject,
category)` shape — the exact, already-accepted ceiling ARCH-014/018
named for local-port granularity. Recommend retaining it in whatever
intermediate row structure the provider builds internally (mirroring
`SnmpArpTableEntry.entry_type`'s own "retained even without a current
consumer" precedent, ARCH-022 Section 6) without designing where it goes
beyond that. This deferral explicitly includes `lldpRemPortIdSubtype ==
networkAddress` — a port identified by a network address is, in
principle, as directly resolvable as a `networkAddress`-subtype chassis
ID, but port-level evidence has no home in the current model regardless
of how well-resolved its identifier is (Section 5). Named here so it is
not silently absorbed into FEAT-012A rather than left unaddressed by
omission.

**`lldpRemSysDesc` → neither.** Mirrors SNMP's own `sysDescr`, which
ARCH-015/ADR-012 already found is not identity-bearing (`snmp_provider.py`'s
`_IDENTITY_FIELD_TO_PROPERTY` maps only `sysName`, never `sysDescr`).
Applying that already-settled finding here rather than re-litigating it:
`lldpRemSysDesc` should not become identity evidence either.

**`lldpRemSysCapSupported`/`lldpRemSysCapEnabled` → neither, future
work.** Device-capability bits (bridge, router, WLAN access point,
telephone, …) are classification-adjacent, but classification remains a
`Device`-state consumer per ADR-011, untouched by this or any report in
this lineage. Not designed further here.

**`lldpRemSysName` → a genuinely new application of ARCH-022's own gate,
not a new question.** This is third-party evidence — the local device
reporting what it heard the *neighbor* advertise about itself — the same
shape of claim ARCH-022 Section 4 already worked through for
ARP-derived `mac_address` evidence. The identical reasoning applies
directly: if a neighbor's `related_subject` resolves (via management
address, `networkAddress`, or the reverse index) to an IP already in the
independently-discovered device set, emitting
`IdentityObservation(subject=related_subject, property_name="hostname",
value=lldpRemSysName, ...)` is safe, for the same reason ARCH-022 Section
4 found gated ARP-MAC emission safe — the endpoint's *existence* is
independently established, only this specific *property* is being
corroborated. If the neighbor is not independently discovered, the same
emission would recreate the exact endpoint-bootstrapping defect ARCH-022's
own review process found and fixed. **This investigation recommends the
identical gate** — emit only when `related_subject` is already in the
discovered device set — applying ARCH-022 Section 4 rather than deciding
a new question.

Adversarial review found the original justification for this gate
incomplete, though its conclusion was correct. Tracing it through: given
today's exactly two `mac_address`-emitting sources (`NmapProvider`,
already self-scoped to devices it discovers; `SnmpArpNeighborProvider`,
gated per ARCH-022 Section 4), the reverse index can in fact only ever
contain subjects that are already independently discovered — meaning
this LLDP-side check would be redundant *against today's sources*. That
is not a reason to remove it. This gate is deliberately **defense in
depth**, not a restatement of an already-guaranteed invariant: relying
solely on every current *and future* `mac_address`-emitting provider
(a hypothetical Bridge-MIB provider, per ARCH-021's Rank 2, among others)
to correctly self-gate is fragile — it depends on every future
implementer re-discovering and re-applying ARCH-022 Section 4 correctly,
with no single enforcement point if one of them doesn't. Checking at the
point of `RelationshipObservation`/`IdentityObservation` emission, as
this gate does, is the one place that protects the invariant regardless
of whether every upstream producer got its own gating right. The gate
stays in the design specifically because it does not assume that.

**`lldpLocChassisId`/`lldpLocSysName` (the queried device's own local
data) → out of this investigation's core scope, named as a separable,
low-risk option.** This is direct self-report about an already-discovered
device (the one being queried), with no bootstrapping risk at all,
architecturally identical to SNMP's own `sysName → hostname` corroboration.
Legitimate, cheap, but not the relationship-provider deliverable this
sprint is chartered around — Section 12 recommends deferring it as a
separable decision for engineering review, not folding it into FEAT-012A
by default.

---

## 5. Chassis-ID Subtypes, Individually

All seven IEEE-802.1AB-defined `lldpRemChassisIdSubtype` values, each
evaluated on its own rather than lumped together:

1. **`chassisComponent`(1)** — an `entPhysicalAlias` reference
   (Entity-MIB). Locally significant to the reporting device's own
   physical inventory; no cross-device meaning. **Not resolvable.**
2. **`interfaceAlias`(2)** — an `ifAlias` value (an admin-assigned
   interface description string). No guaranteed uniqueness or cross-device
   meaning. **Not resolvable.**
3. **`portComponent`(3)** — an `entPhysicalAlias` reference for a port.
   Same limitation as `chassisComponent`, port-scoped. **Not resolvable.**
4. **`macAddress`(4)** — a 6-octet MAC address. **The primary resolvable
   case**, via `build_mac_index()`.
5. **`networkAddress`(5)** — an address-family-prefixed network address
   (the leading octet identifies IPv4/IPv6/other per the standard address-
   family numbering). **Resolvable directly when IPv4**, mirroring ARP's
   own "already IP-shaped" appeal — no index lookup needed. IPv6 and other
   families skipped for Stage 1, consistent with `SnmpArpNeighborProvider`'s
   own established IPv4-only scope (FEAT-010A).
6. **`interfaceName`(6)** — an `ifName` value (e.g. "GigabitEthernet0/1").
   Locally significant, no cross-device meaning. **Not resolvable.**
7. **`local`(7)** — a vendor-defined, arbitrary string with no standardized
   cross-device semantics at all. **Not resolvable.**

Two of seven are resolvable. This is a reconfirmation of ARCH-022 Section
6's finding, individually verified for all seven rather than restated in
aggregate, per this sprint's own charter. Per Section 4's per-entry
mapping (already established by ARCH-022, applied here without
modification): a row with any of the five non-resolvable subtypes
produces no `RelationshipObservation` at all — never a forced, wrongly-
namespaced value, never treated as a legitimate unresolved-endpoint case
(ARCH-022 Section 6/7's own already-corrected distinction).

`lldpRemPortIdSubtype` is a separate, analogous enumeration
(`interfaceAlias`, `portComponent`, `macAddress`, `networkAddress`,
`interfaceName`, `agentCircuitId`, `local`) governing the *port*
identifier, not the chassis. This investigation does not evaluate it
further — per-port evidence has no home in the current model regardless
of its own subtype (Section 4's port-detail finding already covers this),
so the port subtype's resolvability is moot until an `Interface` model
exists to consume it.

---

## 6. Consuming the Reverse Index

No change to `build_mac_index()` or `receive_observations()` — both
consumed exactly as FEAT-011A built them. Concretely, inside
`enrich(devices)`:

```
received = self._received_observations  # set via receive_observations()
mac_index = build_mac_index(received)
discovered_ips = {device.ip_address for device in devices}

for each lldpRemTable row (walked and correlated by its own row index):
    management_addresses = lldpRemManAddrTable rows sharing this row's
                            (TimeMark, LocalPortNum, RemIndex) prefix
                            (Section 3) — best-effort: a failed or empty
                            management-address walk does not fail the row,
                            it just yields no addresses here

    related_subjects = []
    for addr in management_addresses:
        related_subjects.append((addr, "lldp-management-address"))

    if not related_subjects and chassis_id_subtype == networkAddress:
        related_subjects.append((chassis_address, "lldp-chassis-network-address"))
    elif not related_subjects and chassis_id_subtype == macAddress:
        subjects = mac_index.get(chassis_mac, frozenset())
        if len(subjects) == 1:
            related_subjects.append((the one subject, "lldp-chassis-mac"))
        # len == 0 or > 1: no valid related_subject — row contributes
        # nothing further (absent or ambiguous — Section 5, ARCH-022 Section 5)
    elif not related_subjects:
        pass  # unresolvable chassis-ID subtype — Section 5, no RelationshipObservation

    for related_subject, collection_method in related_subjects:
        # one RelationshipObservation per address/resolution — ADR-011's
        # evidence-retention principle, never arbitrarily picking one
        # when a neighbor advertises multiple management addresses
        emit RelationshipObservation(subject=queried_ip, related_subject=related_subject,
                                      category="connected_to", collection_method=collection_method)

        if related_subject in discovered_ips:
            emit IdentityObservation(subject=related_subject, property_name="hostname",
                                      value=lldpRemSysName, collection_method=collection_method)
            # gated per Section 4's application of ARCH-022 Section 4
```

Management-address resolution is attempted first and is best-effort
relative to chassis-ID resolution: only when no management address
resolves does the row fall back to `networkAddress`- or `macAddress`-
subtype chassis-ID resolution (Section 3, Section 7). `collection_method`
takes one of three distinct values per Section 3's correlation — a direct
requirement of ADR-011's provenance requirement, which asks that
provenance be sufficient to determine collection method, and which the
three resolution paths here are methodologically different enough to
warrant distinguishing. This documents only the intended *values*;
`ObservationProvenance`'s own shape is unchanged.

`build_mac_index()` is called once per `enrich()` call, over the
`receive_observations()`-delivered snapshot — mirroring
`SnmpArpNeighborProvider._collect_relationship_observations()`'s own
once-per-call computation of `discovered_ips`, not rebuilt per row.

---

## 7. Failure Semantics

**Timeout, unreachable host, incorrect community string.** Unchanged from
ARP's already-solved case (FEAT-010A) — SNMPv2c's identical
indistinguishability applies identically here.

**Load-bearing vs. best-effort columns — a genuinely new question this
table raises, resolved by applying existing precedent rather than
inventing new policy.** `lldpRemTable` has materially more columns than
`ipNetToPhysicalTable`'s two, raising real odds that one column's walk
fails transiently while others succeed. `SnmpArpNeighborProvider`'s own
design already established the applicable precedent: the `PhysAddress`
walk is load-bearing (its failure fails the whole host), the `Type` walk
is best-effort (its failure only loses that one field, `snmp_client.py`'s
`_get_arp_table` implementation). Applying this directly: chassis-ID and
chassis-ID-subtype are load-bearing (without them no relationship
evidence can be built for that row at all); port ID/description, system
name/description, and capability columns are best-effort (their absence
degrades corroboration richness, never blocks the row).

**`lldpRemManAddrTable`'s own walk — omitted from the original failure-
semantics discussion, added here.** This is a separate table walk from
`lldpRemTable` (Section 3), and its failure semantics were not previously
named. It is best-effort relative to chassis-ID resolution: a failed or
empty management-address walk does not fail the row — it means Section
6's fallback path (`networkAddress`- or `macAddress`-subtype chassis-ID
resolution) is used instead, exactly as chassis-ID resolution already
falls back to no-`RelationshipObservation` when it, in turn, cannot
resolve.

**Malformed entries.** A subtype value outside the seven defined values,
or a chassis-ID length inconsistent with its claimed subtype (e.g.
`macAddress` with a non-6-byte value) — skipped, not erroring, mirroring
`SnmpArpNeighborProvider`'s own established treatment of a non-IPv4 ARP
row.

**Unsupported devices / missing LLDP-MIB.** A device that doesn't
implement LLDP-MIB returns an immediate `noSuchObject`/`endOfMibView`-style
response under SNMPv2c, not a timeout — already correctly distinguished
by the existing `_UNRESOLVED_VALUE_TYPES` handling FEAT-010A's
`_walk_column` implementation already has, reused unmodified. Zero rows
from a real, responding device is a legitimate result
(`responded=True, entries=[]`), not a failure — the identical semantic
distinction FEAT-010A already established and disclosed for
`get_arp_table()`'s own "empty ARP table is legitimate" finding, applied
here without modification.

---

## 8. Provider Placement

Confirmed against ADR-010's actual Decision text (re-read in full this
investigation, not assumed): "receives the already-discovered device set
and adds evidence to it in place... never introduces a `Device` for an IP
not already present." LLDP fits this exactly — it is queried per
already-discovered device; a neighbor mentioned in a row never becomes a
new `Device` regardless of whether it resolves. Notably, ARCH-022's own
endpoint-bootstrapping gate (Section 4) is really ADR-010's "never
introduces a `Device`" principle applied one layer up, at the
`IdentityObservation` level rather than the `Device` level — the same
boundary, restated at the evidence layer rather than reinvented for it.

**A new provider class, not an extension of `SnmpArpNeighborProvider` or
`SnmpEnrichmentProvider`.** Every reason ARCH-020 Section 8 gave for
keeping ARP separate applies at least as strongly here: a narrowly-scoped
class contract, independent opt-in (a table walk this size is a
meaningfully heavier SNMP operation than even ARP's two-column walk),
and this lineage's established precedent of one concern per provider
class. Recommend `SnmpLldpNeighborProvider`, in a new
`networkmapper/discovery/lldp_neighbor_provider.py`, mirroring
`arp_neighbor_provider.py`'s own shape directly.

**Provider-class generalization, explicitly considered and rejected.**
Adversarial review raised a question the original text didn't engage
with: with a second SNMP-table-walk relationship provider now on the
table (and Bridge-MIB, ARCH-021's Rank 2, a plausible third), should the
provider *shape itself* be generalized — one configurable table-walk
provider rather than a third hand-copied, largely-similar class? This
investigation considers that alternative and rejects it, by applying
ARCH-018's own already-established precedent directly rather than
deciding the question fresh: ARCH-018 deferred building the
symmetric-category canonicalization mechanism specifically because
building it before a real evidence source existed to validate it against
would mean designing against a taxonomy that didn't yet exist. The same
reasoning applies here — a generic table-walk framework designed against
two instances (ARP, LLDP) risks being shaped by whichever two happened to
exist first, not by the real variation a third, not-yet-chartered
instance (Bridge-MIB) would actually require. Two similar providers are
not sufficient justification for introducing a generic framework at this
stage; the smallest architectural change remains a third hand-written
class following the established pattern, with generalization revisited
only if and when a real third instance makes the shared shape concrete
rather than speculative.

**A new `SnmpClient` method, following the proven walk pattern.**
`get_lldp_neighbors(host, credentials, timeout, retries) -> SnmpLldpTableResult`,
using the same `walk_cmd`-based, `lookupMib=False`, bounded-`maxRows`
mechanism `get_arp_table()` already proved out (FEAT-010A). The OID-suffix
parsing logic cannot be reused as-is — `lldpRemTable`'s three-integer row
index has a different shape than `ipNetToPhysicalTable`'s variable-length
address encoding — but the *pattern* (parse each column's OID suffix,
correlate by shared row index across separate column walks) transfers
directly and should inform, not be copied verbatim by, a new parsing
helper.

---

## 9. Architectural Impact

**New:**
- `networkmapper/discovery/lldp_neighbor_provider.py` — `SnmpLldpNeighborProvider`.
- `SnmpClient.get_lldp_neighbors()` plus `SnmpLldpTableResult`/
  `SnmpLldpNeighborEntry` dataclasses in `snmp_client.py`, mirroring
  `SnmpArpTableResult`/`SnmpArpTableEntry`. `SnmpLldpNeighborEntry` must
  carry `management_addresses: list[str]`, not a single optional field —
  a neighbor may advertise more than one (Section 3).
- Diagnostics types for the new provider (mirroring
  `snmp_arp_diagnostics.py`'s shape) — Section 12 flags whether these
  should instead be generalized to a shared table-walk diagnostics type
  now that a second near-identical case exists, as a worthwhile but
  non-blocking refinement, not a requirement.

**Modified:**
- `networkmapper/application.py` — new `--snmp-lldp` flag, shared
  credential resolution extended to a third flag (mirroring FEAT-010A's
  own `--snmp-arp` addition to the existing `--snmp` pattern exactly),
  new diagnostics printing.

**Confirmed unchanged, and why, traced against current code rather than
assumed:**
- `DiscoveryEngine.discover()` — already generic over any number of
  `EnrichmentProvider`s and already calls `receive_observations()` before
  each one's `enrich()` (FEAT-011A); a third provider needs no change here.
- `EnrichmentProvider` — `receive_observations()`/`collect_observations()`
  already accept exactly the shapes this provider needs.
- `build_mac_index()` — already generic over any `IdentityObservation`
  stream; consumes whatever `mac_address` observations exist regardless
  of source.
- `IdentityResolver`/`RelationshipResolver` — both already generic over
  any observation a provider emits, the exact property FEAT-011A's own
  design confirmed and this investigation reconfirms against a real
  second consumer.
- `Project`, `NmapProvider`, `SnmpEnrichmentProvider`,
  `SnmpArpNeighborProvider` — untouched; the new provider is a sibling,
  not a modification of any existing one.
- Exporters, `ProjectSerializer` — unaffected; no new `Project` field, no
  new report content, consistent with every prior sprint in this lineage.

---

## 10. ADR-Trigger Check

Checked individually against every decision this investigation makes:

1. LLDP fitting `EnrichmentProvider`'s existing contract (Section 8) —
   direct application of ADR-010's already-accepted Decision text; no new
   policy.
2. Chassis-ID subtype resolvability, all seven individually (Section 5) —
   individually-verified extension of ARCH-022 Section 6's already-decided
   position; no new policy.
3. `lldpRemManAddrTable` as a direct-resolution relationship source
   (Section 3/4) — the same `RelationshipObservation` shape and
   translation-free resolution ARP already established; a new *evidence
   source*, not a new *representation* or *policy*.
4. One shared `connected_to` category regardless of resolution path
   (Section 4) — direct application of ADR-013's already-named Physical
   category and ARCH-018's own LLDP designation; not a new category or
   naming policy.
5. Extending ARCH-022 Section 4's endpoint-bootstrapping gate to
   `lldpRemSysName` (Section 4) — explicitly an application, stated as
   such, not a new question resolved independently.
6. The load-bearing/best-effort column split (Section 7) — direct
   application of `SnmpArpNeighborProvider`'s own already-shipped
   `PhysAddress`/`Type` precedent.
7. Empty-but-responded and malformed-entry handling (Section 7) — direct,
   unmodified reuse of FEAT-010A's own already-established semantics.
8. Management-address multiplicity — emit one `RelationshipObservation`
   per advertised address, never arbitrarily pick one (Section 3) —
   direct application of ADR-011's evidence-retention principle; no new
   policy.
9. Provider-class generalization, rejected (Section 8) — direct
   application of ARCH-018's already-established anti-premature-
   generalization precedent; removes proposed mechanism rather than
   adding it, the same non-trigger reasoning already applied to
   rejecting a dependency graph in ARCH-022 Section 7.
10. `collection_method` provenance values for the three resolution paths
    (Section 6) — direct application of ADR-011's existing provenance
    requirement to three new string values; no change to
    `ObservationProvenance` or any new provenance policy.

**No new ADR is triggered by this investigation.**

---

## 11. Testing Strategy

**Unit — `SnmpClient.get_lldp_neighbors()`.** Mirrors
`test_snmp_client.py`'s ARP-table test template directly: each chassis-ID
subtype individually (resolvable and non-resolvable), a management-address
row, a load-bearing column failure (whole row lost) vs. a best-effort
column failure (row survives, missing field), a malformed/out-of-range
subtype value, empty table, timeout.

**Unit — `SnmpLldpNeighborProvider`.** Mirrors
`test_arp_neighbor_provider.py`'s template: a `macAddress`-subtype row
resolves via a fed `build_mac_index()` snapshot; a `networkAddress`-subtype
row and a management-address row both resolve directly, no index needed;
a neighbor advertising multiple management addresses produces one
`RelationshipObservation` per address, never one arbitrarily chosen from
the set — the direct executable proof of Section 3's evidence-retention
correction; an unresolvable-subtype row produces no `RelationshipObservation`; an
ambiguous MAC (index returns `frozenset` of size >1) skips the row,
exactly mirroring ARCH-022 Section 5's own caller-decision recommendation;
`lldpRemSysName` identity emission is gated on device-set membership,
directly exercising Section 4's applied gate with its own dedicated
discovered/undiscovered test pair, the same shape as FEAT-011A's own
critical bootstrapping test; `Device` fields are never mutated.

**Integration — a genuinely new case FEAT-011A's own design enables for
the first time.** `SnmpArpNeighborProvider` and the new LLDP provider
registered together in `DiscoveryEngine`'s `enrichment_providers` list, in
both orders: confirms the LLDP provider's `receive_observations()` call
sees ARP-derived `mac_address` evidence when ARP runs first (richer
resolution), and confirms it still produces correct, if reduced-coverage,
output when ARP runs second or is absent entirely (Section 7 of ARCH-022,
directly exercised against a real second provider rather than a synthetic
stub for the first time).

**Live-network verification, explicitly separated.** The exact numeric
OID suffixes for every `lldpRemTable`/`lldpRemManAddrTable` column; the
real-world distribution of chassis-ID subtypes and management-address
availability across vendors (this investigation's own central open
question, Section 13); OID-suffix parsing against a real device's actual
row-index encoding — the identical class of disclosed, not-yet-verified
risk FEAT-010A already named for its own ARP implementation, carried
forward unmodified for LLDP's own, larger table.

---

## 12. Scope Boundaries

Explicitly out of FEAT-012A, named so they are not silently absorbed into
it:

- **`Interface`/port model** to capture `lldpRemPortId`/`lldpRemPortDesc`/
  `lldpRemLocalPortNum` — tempting, since LLDP surfaces far richer
  port-level detail than ARP ever could, but this is ARCH-014's own
  already-accepted, not-solved-here ceiling. Retain the data internally
  (Section 4) without designing where it goes.
- **Local system-data corroboration** (`lldpLocChassisId`/`lldpLocSysName`
  as identity evidence for the *queried* device itself) — legitimate and
  low-risk (Section 4), but a separable decision, not a default inclusion.
- **Device-capability data** (`lldpRemSysCapSupported`/`Enabled`) feeding
  future classification — classification remains untouched by this entire
  lineage; do not even sketch this.
- **Diagnostics-type consolidation** — generalizing
  `SnmpArpHostDiagnostics`/`SnmpArpRunDiagnostics` and the new LLDP
  equivalents into one shared table-walk diagnostics type is a reasonable
  simplification now that a second near-identical case exists, but a
  nice-to-have refactor, not a requirement — worth a look at
  implementation time, not a blocking design question here.
- **Symmetric-category canonicalization** (ARCH-018's own Stage 3.5) —
  `connected_to` remains symmetric; Stage 1's accepted under-corroboration
  limitation (two independent `WEAK` relationships rather than one
  `CONFIRMED` one when both LLDP peers report the same link) still stands,
  unchanged by this investigation.
- **CDP and Bridge/MAC forwarding tables** — ARCH-021's Ranks 3 and 2,
  each its own separate future sprint, not folded into this one merely
  because they share the reverse-index prerequisite.
- **Topology rendering of any kind** — still explicitly out of scope per
  every report in this lineage back to ADR-013's own boundary.

---

## 13. Final Recommendation

**Recommended architecture:** exactly Section 9's file list — one new
provider, one new client method, new diagnostics, `application.py`
wiring — reusing `build_mac_index()`, `receive_observations()`,
`IdentityResolver`, and `RelationshipResolver` entirely unmodified.

**Implementation order**, mirroring FEAT-010A's own successful sequencing:
(1) `SnmpClient.get_lldp_neighbors()` plus its unit tests — isolable, no
dependency on the provider; (2) `SnmpLldpNeighborProvider` plus its unit
tests — depends on (1); (3) `application.py` wiring — depends on (2);
(4) the two-provider integration test (Section 11) — depends on (2) and
the already-shipped `SnmpArpNeighborProvider`; (5) full-suite validation.

**Remaining unknowns, named rather than guessed past:** exact numeric
OIDs need confirmation against the authoritative LLDP-MIB module before
coding begins. This is separate from a second, distinct unknown
adversarial review surfaced (Section 3): `lldpRemTimeMark`'s `TimeFilter`
walk behavior is its own implementation-time validation item, not covered
by "numeric-suffix confidence is not [high]" — confirming a real device
walks correctly under this convention is a different check than
confirming the right column numbers. The real-world
population rate of `lldpRemManAddrTable` versus `macAddress`-subtype
chassis IDs across vendors is unverified and materially affects how much
of FEAT-012A's value depends on the reverse index at all versus resolving
directly — this investigation recommends an early, cheap live-network
check of this specific question before deep implementation investment,
not as a blocking gate but as the single highest-value piece of
information FEAT-012A could gather early.

**ADR requirement:** none (Section 10).
