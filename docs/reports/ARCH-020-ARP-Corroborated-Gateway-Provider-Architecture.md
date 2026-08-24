# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — this investigation closes exactly the two questions
ADR-013/ARCH-018 explicitly left open for "the Stage 3 provider
implementation sprint itself" (ARCH-018 Section 5's ARP paragraph, Section
15): which evidence source to use, and ARP evidence's canonical category
name and symmetric/directional classification. Both fall inside ADR-013's
already-authorized "provider-specific mapping of relationship evidence to
canonical categories" future work, the same category of implementation
detail ARCH-017/ARCH-018 filled in without a new ADR.

Recommended Next Sprint:
FEAT-010A — SNMP ARP-Neighbor Enrichment Provider (Stage 3), a new
`EnrichmentProvider` mirroring `SnmpEnrichmentProvider`'s proven shape,
plus one new `SnmpClient` method to walk `ipNetToMediaTable`/
`ipNetToPhysAddress`. Offered as a recommendation, not a decision — per
scope, engineering review selects the next sprint.

---

## 1. Executive Summary

ARCH-018 named ARP-corroborated-gateway evidence "the cleanest first
candidate" for a relationship-evidence provider, and named it twice more
without designing it: once in Section 5 ("This investigation does not
assign ARP evidence a canonical category name or a symmetric/directional
classification... intentionally left to the Stage 3 provider
implementation sprint itself"), and once in Section 15 ("this stage is
also where the provider chooses ARP evidence's canonical category name and
symmetric/directional classification — intentionally not decided by this
investigation"). This investigation is that sprint. It answers both
deferred questions, evaluates the two evidence-collection mechanisms ARP
evidence could come from, and finds one clearly superior — not a coin
flip ARCH-018 left open, but a decision ARCH-018 deliberately declined to
make before the provider's own requirements were worked through.

**Evidence source.** Two mechanisms exist in principle: querying a
network device's own SNMP `ipNetToMediaTable` (its ARP cache, as the
device itself sees it), or reading the *scanning host's* local OS ARP
cache (`arp -a`/`ip neigh`). This investigation finds these are not two
flavors of the same evidence — they answer different questions. A
router's own ARP table says "this gateway has resolved these hosts,"
which is exactly the "ARP-corroborated-gateway" relationship ARCH-014
motivated. The scanning host's local ARP cache says only "the scanner
itself recently talked to these hosts on its own subnet" — no gateway
relationship, no evidence about any other device, and mostly redundant
with what `NmapProvider` already captures as `Device.mac_address` identity
evidence (Section 4). SNMP `ipNetToMediaTable` is the only one of the two
that produces the relationship ARCH-018 named. Section 6 works through
this in detail and rejects the local-ARP-cache alternative explicitly,
closing an ambiguity ARCH-018 left open rather than picking arbitrarily.

**The one real architectural gap.** `SnmpClient` today performs exactly
one fixed six-OID `GetRequest` (the MIB-2 system group) and has no
table-walking capability at all (Section 3). `ipNetToMediaTable` is a
table — an unknown number of rows, requiring `GetNext`/`GetBulk`
semantics — not a value `GetRequest` can retrieve. This is new client-layer
capability, not new provider-layer complexity: one new `SnmpClient` method
alongside `get_system_group()`, not a new architectural pattern. Section 5.

**Category and directionality — closing ARCH-018's deferred decision.**
This investigation recommends a new category, `arp_neighbor`, distinct
from `connected_to` (reserved for LLDP/CDP's stronger, direct physical-
adjacency claim per ADR-013's Physical category) — and finds ARP evidence
is **directional**, not symmetric, on structural grounds stronger than
LLDP's own symmetric classification: a router's ARP table containing host
H is not the same claim as H's own ARP table (if queried) containing the
router — the two entries can independently exist, expire, or diverge, so
there is no single physical fact two endpoints' reports describe from
different sides the way an LLDP link is. Section 7.

**Provider architecture.** A new `EnrichmentProvider` — not an extension
of `SnmpEnrichmentProvider` — sharing `SnmpCredentials`/`SnmpClient`
infrastructure but kept independently opt-in and independently testable,
consistent with how `NmapProvider` and `SnmpEnrichmentProvider` are
already kept separate rather than merged. Section 8.

**No further runtime-integration work is needed.** This is this
investigation's clearest finding, and worth stating plainly: FEAT-009B
already wired `IdentityResolver`/`RelationshipResolver` to consume
whatever `Project.observations` contains, and `DiscoveryEngine.discover()`
already collects `collect_observations()` from every enrichment provider
generically (Section 3). A new provider that emits `RelationshipObservation`s
needs to do nothing more than exist and be added to
`Application.run()`'s `enrichment_providers` list — the additive,
decoupled pipeline ARCH-017 designed and FEAT-009B shipped already
generalizes to this without modification. This validates ARCH-017's
original design goal directly, not merely by argument.

No production code is proposed for change by this report.

---

## 2. Direct Answers

**1. Which evidence-collection mechanism should Stage 3 use?** SNMP
`ipNetToMediaTable`/`ipNetToPhysAddress`, queried against already-discovered
devices — not the scanning host's local ARP cache. Section 6.

**2. What new client-layer capability does this require?** One new
`SnmpClient` method performing a table walk, alongside the existing
single-`GetRequest` `get_system_group()`. This is the one genuine
architectural gap this investigation found. Section 5.

**3. What is `RelationshipObservation`'s field mapping for ARP evidence?**
`subject` = the queried device's own IP (the potential gateway); each ARP
table row contributes one `related_subject` = the IP address found in that
row. Both are already in `IdentityObservation`'s subject namespace — ARP
is the source ARCH-018 Section 1 already confirmed needs no translation
step, reconfirmed here against the concrete table shape. Section 6.

**4. What canonical category name and symmetric/directional classification
apply?** A new category, `arp_neighbor`; directional, not symmetric.
Section 7.

**5. How does the provider fit the existing architecture?** A new
`EnrichmentProvider` implementation, structurally parallel to
`SnmpEnrichmentProvider`, sharing `SnmpCredentials`/`SnmpClient` but kept
as a separate, independently opt-in class. Section 8.

**6. What runtime-integration work does this require, beyond FEAT-009B?**
None. The provider only needs to exist and be added to
`Application.run()`'s `enrichment_providers` list; `DiscoveryEngine`,
`IdentityResolver`, and `RelationshipResolver` already consume whatever
`RelationshipObservation`s any enrichment provider emits, unmodified since
FEAT-009B. Section 3, Section 9.

**7. What is explicitly out of scope?** LLDP/CDP, Bridge MIB, STP,
routing-table evidence, any `Interface`/port model, cross-run
corroboration, topology rendering, and any change to `IdentityResolver`/
`RelationshipResolver` themselves. Section 11.

---

## 3. Current Architecture Assessment

**`EnrichmentProvider` is the exact shape this provider needs.**
`networkmapper/discovery/enrichment_provider.py` defines the contract:
`enrich(devices)` adds evidence to an already-discovered device set in
place, never introduces or removes a `Device`; `collect_observations()`
defaults to `[]` and is additive/optional (`enrichment_provider.py:10-38`).
`SnmpEnrichmentProvider` (`discovery/snmp_provider.py`) is the closest,
and only, real precedent: constructed with `SnmpCredentials`, an injectable
`SnmpClient`, and an `event_bus`; iterates every device, queries it, never
raises per-host (per-device failures are caught and recorded as
diagnostics — `snmp_provider.py:154-167`), and separately tracks
`_observations` for `collect_observations()` to return
(`snmp_provider.py:181-183`). A Stage 3 ARP provider fits this template
directly — same credentials type, same injectable-client pattern for
testability, same never-raise-per-device posture, same
`collect_observations()` contract.

**The pipeline already generalizes to a new provider without change.**
`DiscoveryEngine.discover()` (`discovery_engine.py:82-97`) already loops
over every `enrichment_provider` in `self._enrichment_providers`, calls
`enrich(devices)`, then `collect_observations()`, and extends
`self.observations` — generically, not specific to `SnmpEnrichmentProvider`.
`Application.run()` (`application.py:135-136`, post-FEAT-009B) already
calls `IdentityResolver().resolve(engine.observations)` then
`RelationshipResolver().resolve(engine.observations, identities)` over
whatever `engine.observations` contains, regardless of which providers
produced it. A new `RelationshipObservation`-emitting provider therefore
requires zero changes to `DiscoveryEngine`, `IdentityResolver`,
`RelationshipResolver`, or the resolver-wiring block in `Application.run()`
— only construction of the new provider and its addition to the
`enrichment_providers` list passed to `DiscoveryEngine(...)`
(`application.py:90-94`), the same one-line addition `SnmpEnrichmentProvider`
itself already demonstrates (`snmp_provider` appended when `args.snmp` is
set).

**`SnmpClient` cannot walk a table today.** `networkmapper/discovery/
snmp_client.py` defines exactly one operation:
`get_system_group(host, credentials, timeout, retries) -> SnmpHostResult`,
implemented as a single `get_cmd` PDU carrying the six fixed system-group
OIDs (`snmp_client.py:100-145`, using `pysnmp.hlapi.v3arch.asyncio.get_cmd`).
There is no `GetNext`/`GetBulk`/walk operation anywhere in the codebase.
`ipNetToMediaTable` (IP-MIB, `1.3.6.1.2.1.4.22`) — or its RFC 4293
replacement `ipNetToPhysicalTable`, `1.3.6.1.2.1.4.35` — is a table with an
a priori unknown number of rows (one per ARP cache entry), which SNMP can
only retrieve by walking, not by a single `GetRequest`. This is a real,
confirmed gap, not a restated one: ARCH-018 Section 12's technical-debt
item 5 ("no MAC-address-to-canonical-identity resolution mechanism")
concerned Bridge MIB/STP specifically and does not apply here — ARP's
`related_subject` is already an IP address in each table row, not a MAC
requiring translation (Section 6 reconfirms this). The gap this
investigation identifies is narrower and different: a missing *query
mechanism*, not a missing *identity-resolution* mechanism.

**`Device.mac_address` is unrelated, pre-existing identity evidence.**
`NmapProvider._extract_mac_address()` (`nmap_provider.py:510`) already
populates `Device.mac_address` and emits a `mac_address`
`IdentityObservation` (`nmap_provider.py:415-418`) from nmap's own
ARP-based local-subnet host discovery. This is evidence about one device's
own identity (its MAC address), not a relationship between two devices —
structurally unrelated to what this investigation designs, confirmed here
so it is not mistaken for a precedent or a competing mechanism.

---

## 4. Why the Scanning Host's Local ARP Cache Is Rejected

ARCH-018 Section 5 named both "SNMP `ipNetToMediaTable`, or a local
`arp -a`/equivalent" without choosing between them. This investigation
evaluates both explicitly rather than picking by convention.

**What the scanning host's local ARP cache actually contains.** Only
entries the scanning machine itself has populated by ARPing another host
directly — which, on a typical Layer-3-segmented network, is limited to
devices on the scanner's own local subnet that the scanner has recently
communicated with. This is not "the gateway's knowledge of its
downstream hosts" (ARCH-018's own "ARP-corroborated-gateway" framing) — it
is "what the scanner itself has already talked to," which is largely
redundant with the very host-discovery process (`NmapProvider.discover()`)
that already ran to produce the device set an enrichment provider receives.
Reading it would produce, at best, an `arp_neighbor` observation whose
`subject` is the scanning host itself — a single vantage point contributing
no relationship a NetworkMapper user doesn't already get for free from the
device list itself, and none of the actual gateway-corroboration value
ARCH-014/ARCH-018 motivated this work with.

**A router's SNMP `ipNetToMediaTable`, by contrast**, reflects that
specific device's own ARP cache — built from real traffic that device has
handled as a Layer-3 hop for its attached subnet(s). Querying several
routers/switches (not just the scanning host) surfaces genuinely
independent claims about which hosts each gateway has resolved, which is
exactly the corroborating-evidence shape ARCH-014's own worked example
described (multiple sources independently reporting the same relationship).

**Secondary considerations, weaker but reinforcing the same conclusion.**
Local ARP-cache reading would require a new, unprecedented execution
boundary — spawning a subprocess (`arp -a` on Windows, `ip neigh`/`arp -n`
on Linux) with platform-dependent output parsing, a materially different
trust and testing boundary than the existing `SnmpClient` abstraction
(ARCH-012's own "credential/boundary" precedent). SNMP `ipNetToMediaTable`
requires no new execution boundary at all — it extends the same
`SnmpClient`/`SnmpCredentials` boundary `SnmpEnrichmentProvider` already
uses today.

**Conclusion.** SNMP `ipNetToMediaTable`/`ipNetToPhysAddress`, queried
against already-discovered devices, is the only mechanism of the two that
produces "ARP-corroborated-gateway" evidence at all. The local-ARP-cache
alternative is not merely a weaker variant of the same idea; it answers a
different, lower-value question. This investigation recommends it be
dropped from consideration for Stage 3, not deferred.

---

## 5. New Client Capability

**What's needed.** A new `SnmpClient` method, e.g.
`get_arp_table(host, credentials, timeout, retries) -> SnmpArpTableResult`,
performing a walk (`GetBulk`, or repeated `GetNext`, over pysnmp's
asyncio hlapi) of the `ipNetToMediaTable`/`ipNetToPhysicalTable` subtree,
returning a list of `(interface_index, ip_address, mac_address)` rows
(mirroring `ipNetToMediaTable`'s four-column shape: `ifIndex`, `NetAddress`,
`PhysAddress`, `Type` — `Type` distinguishes `dynamic`/`static`/`invalid`
entries, worth retaining as diagnostic evidence even though this
investigation does not design a use for it yet). This investigation
does not design the walk's exact pysnmp call shape, retry/pagination
behavior, or the `ipNetToMediaTable`-vs-`ipNetToPhysicalTable` OID choice
(the latter is IPv6-capable and RFC 4293's modern replacement for the
former's RFC 1213 origin; a real implementation should prefer it with a
fallback, but that is implementation detail for FEAT-010A, not an
architectural decision this investigation needs to make) — consistent with
how ARCH-018 designed `RelationshipResolver`'s algorithm without writing
its code.

**Why this is the right layer for the addition.** `SnmpClient` is already
`SnmpEnrichmentProvider`'s injected boundary specifically so provider
tests can mock the contract without touching pysnmp internals
(`snmp_client.py:62-68`'s own stated purpose). A table-walk method belongs
on the same boundary, for the same reason — a future
`SnmpArpNeighborProvider` should be testable the same way
`SnmpEnrichmentProviderTest` already is, against a stub `SnmpClient`, not
against real UDP traffic or pysnmp mocking internals.

**Failure semantics carry over unchanged.** ARCH-012's Failure Model —
timeout, unreachable UDP/161, and an incorrect community string are all
indistinguishable at this layer under SNMPv2c (`snmp_client.py:119-124`'s
existing comment) — applies identically to a table walk. `get_arp_table()`
must never raise (mirroring `get_system_group()`'s contract,
`snmp_client.py:77`), returning an empty/failed result on any error
instead. A device that does not support or expose
`ipNetToMediaTable`/`ipNetToPhysicalTable` at all (many workstations,
printers, and some switches restrict SNMP MIB visibility) is not a
different failure mode from a timeout — both must degrade to "no evidence
from this device," never abort the enrichment pass, exactly as
`SnmpEnrichmentProvider.enrich()` already treats a per-host failure
(`snmp_provider.py:154-167`).

---

## 6. Relationship Observation Mapping

**Field assignment.** For a device `G` (the one queried) whose
`ipNetToMediaTable` contains a row mapping IP `H` to a MAC address:

```python
RelationshipObservation(
    subject=G.ip_address,
    related_subject=H,
    category="arp_neighbor",
    provenance=ObservationProvenance(
        provider="snmp",
        collection_method="ipNetToMediaTable",
        observed_at=...,
        source_run=...,
    ),
)
```

One `RelationshipObservation` per table row. `subject` is always the
queried device's own already-known `ip_address` (never derived from the
table itself); `related_subject` is each row's `NetAddress` column value —
already an IP address string, in the identical subject namespace
`IdentityObservation.subject` uses for that device, satisfying ARCH-018
Section 1's translation requirement with no additional step, exactly as
Section 5's ARP paragraph there predicted before any table shape had been
examined. This investigation confirms that prediction against the real
table structure rather than merely repeating it.

**Endpoint resolution is not this provider's concern.** Per ADR-013's
Relationship Endpoints section and `RelationshipResolver`'s own
preprocessing (`relationships/resolver.py:103-109`), whether `H` resolves
to a `CanonicalIdentity` this run depends on whether `H` was independently
discovered — the provider's job is only to emit the observation
faithfully; an `H` NetworkMapper never separately scanned produces a
retained-but-unresolved observation, not an error, not a gap this provider
needs to detect or handle. This is not a new case for `RelationshipResolver`
to learn — it is the exact "unresolved endpoint" case ADR-013/ARCH-018
already designed for, now exercised by a real evidence source for the
first time.

**Self-loops are already handled, need no new logic.** A device's own
`ipNetToMediaTable` row for itself would be unusual (ARP resolves *other*
hosts' addresses, not the querying device's own) but not impossible
(loopback interfaces, misconfiguration). `RelationshipResolver`'s existing
`subject == related_subject` exclusion (`relationships/resolver.py:108`)
already covers this without any provider-side filtering.

**Row `Type` (dynamic/static/invalid) is retained but not mapped to
anything yet.** This investigation finds no current use for distinguishing
a dynamic (learned) from a static (administrator-configured) ARP entry —
both indicate the same relationship fact (G has resolved H) — but
recommends the provider retain it as part of `SnmpArpTableResult`
regardless (Section 5), since discarding collected evidence prematurely
would contradict ADR-011's retention principle even where this
investigation finds no immediate consumer for it.

---

## 7. Category and Directionality

**Why not `connected_to`.** ADR-013's Physical category (`connected_to`)
is ARCH-014/ARCH-018's name for LLDP/CDP's direct link-layer adjacency
claim — a neighbor's chassis ID and local port, the strongest available
evidence that two devices are physically wired together. ARP evidence
claims something weaker and different: that a device has, via IP protocol
operation, resolved another IP to a MAC address in its own cache — L3/ARP
knowledge, not confirmed physical adjacency (a router's ARP entry for a
host on the far side of an unmanaged switch is still valid ARP evidence,
with no physical-link claim implied). Grouping ARP observations into the
same `connected_to` category as future LLDP/CDP observations would let
`RelationshipResolver`'s `(subject, category)` grouping (ARCH-018 Section
4/6) mix two structurally different claims under one corroboration count —
an ARP entry and an LLDP report for the same subject could then produce a
spurious `CONFIRMED` or `CONFLICTING` result between two evidence types
that were never actually claiming the identical thing. This investigation
recommends a distinct category, `arp_neighbor` — a free-text category name,
per ADR-013's own deliberate refusal to freeze an enumerated taxonomy — so
`RelationshipResolver`'s existing grouping/corroboration algorithm (already
correct and unmodified, Section 9) only ever corroborates ARP evidence
against other ARP evidence, not against a structurally different evidence
type wearing the same category label.

**Directional, not symmetric — a stronger case than LLDP's own.** ARCH-018
Section 6 classified `connected_to` as symmetric because an LLDP frame
received by either endpoint describes *one* physical fact regardless of
which side reports it. ARP evidence has no such single-fact backing: `G`'s
ARP cache containing `H` and `H`'s ARP cache (if queried) containing `G`
are two independently-maintained, independently-expiring cache entries
that can diverge (one present, one stale or absent) without either being
wrong — there is no single ground truth two reports are describing from
opposite sides. This investigation therefore classifies `arp_neighbor` as
directional. The practical consequence is favorable, not merely academic:
directional categories are excluded from Stage 1's deferred
symmetric-category canonicalization mechanism (ARCH-018 Section 6/15's
Stage 3.5) by construction, so this decision requires no new mechanism —
`arp_neighbor` observations are grouped and corroborated exactly as Stage
1 already groups every category, with no special-casing needed.

**Corroboration in practice.** Two independent gateways both reporting the
same `(subject=G, related_subject=H, category=arp_neighbor)` triple would
require the *same* device `G` to be queried twice by independent
`(provider, collection_method)` sources — unlikely within a single run
with one SNMP provider instance, so most `arp_neighbor` observations will
resolve to `WEAK` canonical relationships in practice, not `CONFIRMED`.
This is not a defect in the category design; it is the same honestly-scoped
limitation ARCH-018 Section 1 already named for relationship resolution
generally — corroboration *within* one observation set is what Stage 1
provides, and cross-run corroboration remains blocked on the same
cross-subject identity correlation problem `docs/LAB.md` already tracks.

---

## 8. Provider Architecture

**A new class, not an extension of `SnmpEnrichmentProvider`.** This
investigation considered folding ARP-table walking into
`SnmpEnrichmentProvider.enrich()` (same credentials, same device loop,
same client) and recommends against it, for three reasons: (1)
`SnmpEnrichmentProvider`'s own docstring scopes it explicitly to "MIB-2
system-group SNMP evidence" (`snmp_provider.py:60`) — broadening that
scope silently would make the class's contract narrower than its actual
behavior; (2) a table walk is a materially heavier SNMP operation than a
fixed six-OID `GetRequest`, particularly against a core router with a
large ARP table — bundling it into the same opt-in flag as system-group
enrichment removes a customer's ability to enable one without the other;
(3) the codebase's own precedent already keeps single-concern discovery
concerns in separate classes (`NmapProvider`'s host discovery and
`SnmpEnrichmentProvider`'s system-group enrichment are not merged despite
both running in the same pipeline stage grouping) — a new
`SnmpArpNeighborProvider` (name illustrative, not decided here) continues
that precedent rather than breaking it.

**Shared infrastructure, independent opt-in.** The new provider reuses
`SnmpCredentials` (same environment-variable-sourced community string,
ARCH-012's Credential Strategy — no new credential mechanism needed) and
the extended `SnmpClient` (Section 5), constructed and injected the same
way `SnmpEnrichmentProvider` already is (`snmp_provider.py:67-94`). Its own
`enrich(devices)` loops every device, calls the new `get_arp_table()`
client method per device, and for each returned row emits a
`RelationshipObservation` (Section 6) via `collect_observations()` — never
mutating any `Device` field, since ARP-table evidence has no natural
`Device` attribute to merge into (unlike system-group evidence's
`_merge()` fallback pattern) and this investigation finds no reason to
invent one.

**Wiring.** `Application.run()` gains, at most, one more `if`-gated
provider construction mirroring `args.snmp`'s existing pattern
(`application.py:82-88`) and one more entry in the `enrichment_providers`
list (`application.py:90-94`) — whether this shares the existing `--snmp`
flag or introduces a new one is implementation detail for FEAT-010A, not
an architectural question this investigation needs to resolve, since
either choice requires the identical one-line wiring change and neither
touches `DiscoveryEngine`, `IdentityResolver`, or `RelationshipResolver`
(Section 3).

---

## 9. Confirmation: FEAT-009B's Pipeline Requires No Changes

Traced directly against the current, post-FEAT-009B `discovery_engine.py`
and `application.py`, not assumed from ARCH-019's own prior design intent:

```
NmapProvider ──► SnmpEnrichmentProvider ──► (new) SnmpArpNeighborProvider
        │                  │                            │
        └──────────────────┴──────────┬─────────────────┘
                                       ▼
                     Observation Emission (additive, per-provider)
                                       ▼
                  Project.observations (DiscoveryEngine.observations)
                                       ▼
                       IdentityResolver.resolve(...)
                                       ▼
              RelationshipResolver.resolve(..., identities)
                                       ▼
        Project.canonical_identities / canonical_relationships
```

Every arrow in this diagram already exists and is already generic over
"however many providers happen to be configured" — none of it is specific
to `NmapProvider` or `SnmpEnrichmentProvider` by name. Adding a third
provider that emits `RelationshipObservation`s changes nothing about this
diagram's shape; it only adds a third arrow into the same existing
funnel. This is the direct, concrete payoff of ARCH-017's original
"decoupled additive layer" design goal and FEAT-009B's implementation of
it — this investigation's clearest finding is that this payoff is real,
not merely claimed.

---

## 10. Testing Strategy

**New `SnmpClient.get_arp_table()` unit tests** (extending
`tests/test_snmp_client.py`'s existing pattern, if one exists in that
shape, or `tests/test_snmp_provider.py`'s stub-client pattern otherwise):
empty table, multiple rows, a device that does not support the OID subtree
(degrades to empty/no-error, mirroring `SnmpHostResult`'s
`responded=False` shape), and the same timeout/unreachable/malformed-
response cases `get_system_group()` already covers.

**New provider unit tests** (a new `tests/test_arp_neighbor_provider.py`,
structurally parallel to `tests/test_snmp_provider.py`, which this
investigation finds is the correct template to clone, exactly as ARCH-018
found `test_identity_resolver.py` was the correct template for
`test_relationship_resolver.py`): one row produces one
`RelationshipObservation` with the expected `subject`/`related_subject`/
`category`; multiple rows produce multiple observations; a per-device
failure degrades without raising and without stopping the remaining
devices; `collect_observations()` resets between `enrich()` calls
(mirroring `SnmpEnrichmentProviderObservationTest`'s existing coverage of
the identical requirement for `SnmpEnrichmentProvider`).

**No changes needed to `RelationshipResolver`'s own tests.** Section 9's
finding means the resolver requires no new test coverage — it already
correctly processes any `RelationshipObservation` regardless of source,
proven by `tests/test_relationship_resolver.py`'s existing synthetic-
fixture coverage.

**Architectural integration test.** This investigation recommends
extending `tests/test_identity_pipeline.py` once more (or a sibling),
following the exact pattern FEAT-009B's own verification already
established: a fake, network-free provider standing in for the new SNMP
ARP provider, proving the full `Application.run()` chain — including a
*second* enrichment provider now — still produces correct
`canonical_relationships`. This is the first test that would exercise two
enrichment providers together, a case no existing test covers, though
`DiscoveryEngine.discover()`'s loop over `self._enrichment_providers`
(`discovery_engine.py:82-97`) already handles this generically today.

---

## 11. Scope Exclusions

Confirmed against the current codebase as things this investigation's
recommendation does not touch, add, or require:

- **LLDP/CDP, Bridge MIB, STP.** Not evaluated further here; ARCH-018
  Section 5's assessment of each stands unchanged. This investigation's
  `arp_neighbor` category is deliberately kept separate from whatever
  category a future LLDP/CDP provider would use (Section 7).
- **Routing-table evidence.** Still out of this investigation's endpoint
  model — a routing table's far endpoint is frequently a subnet, not a
  `Device` (ADR-013's own carried-forward finding), unaffected by ARP
  evidence's all-`Device`-shaped endpoints.
- **`Interface`/port model.** Not needed — `ipNetToMediaTable`'s `ifIndex`
  column is retained as diagnostic evidence (Section 6) but not mapped to
  anything, the same accepted ceiling ARCH-018 Section 11/12 already
  named for LLDP/CDP's local-port granularity.
- **Cross-run/cross-subject identity correlation.** Unaffected;
  `arp_neighbor` observations corroborate exactly as far as Stage 1
  `IdentityResolver`'s single-run scope already allows (Section 7).
- **`IdentityResolver`/`RelationshipResolver` changes.** None required or
  proposed (Section 9).
- **`DiscoveryEngine`, `Project`, exporter/reporting changes.** None
  required (Section 9); `canonical_relationships` becomes non-empty on a
  real scan as a consequence of this provider existing, with no further
  wiring, but this investigation does not propose any exporter/report
  consuming it — that remains explicitly future work, unchanged from
  ARCH-019 Section 13.

---

## 12. Risks

**Large ARP tables on core infrastructure.** A busy core router's ARP
table can hold hundreds to low thousands of entries. A table walk against
such a device is a materially larger and slower SNMP operation than the
fixed six-OID system-group `GetRequest` every other SNMP interaction in
this codebase performs today. This investigation does not design pagination,
row-count limits, or timeout scaling for this — recommended as
implementation-time detail for FEAT-010A to address explicitly, not
silently assumed away.

**Most `arp_neighbor` observations resolve to `WEAK`, not `CONFIRMED`, in
practice (Section 7).** Named directly so FEAT-010A's own validation
sprint does not mistake an all-`WEAK` result set for a defect — it is the
expected outcome of a single-provider, single-run evidence source, exactly
as ARCH-018 predicted relationship evidence generally would look before
multiple corroborating sources exist.

**A device exposing `ipNetToMediaTable` may still be a workstation, not a
gateway, for some rows.** `arp_neighbor` evidence does not itself prove
`subject` is a router or gateway — it proves only that `subject` has an
ARP entry for `related_subject`, which any Layer-2-adjacent device can
have, not only routers. The `arp_neighbor` category name and this report's
prose describe the common, motivating case (ARCH-014's "gateway"
framing) without asserting the evidence proves a gateway role — a
distinction worth stating explicitly so a future consumer does not conflate
"this device has ARP evidence" with "this device is classified as a
router" (`DeviceClassifier`'s own, entirely separate concern, untouched by
this work).

**No real evidence source exists yet, same structural risk ARCH-018
Section 11 already named for Stage 1 generally.** This investigation
closes the design gap; FEAT-010A closes the "has this code ever run
against a real network" gap. Both remain separate milestones.

---

## 13. Suggested Roadmap

**FEAT-010A (this investigation's subject, not authorized here) —
`SnmpClient.get_arp_table()` plus a new `EnrichmentProvider` emitting
`arp_neighbor` `RelationshipObservation`s**, unit-tested per Section 10,
wired into `Application.run()`'s existing opt-in pattern (Section 8).

**FEAT-010B (separate future sprint) — architectural integration test
extension** (Section 10), following FEAT-009B's own precedent for
validating a new evidence-emitting component through the real
`Application.run()` path.

**Future, not authorized here:** LLDP/CDP (needs its own category and its
own translation-requirement design, per ARCH-018 Section 5); pagination/
scale handling for large ARP tables (Section 12); any exporter/report
consumption of `canonical_relationships` (still ARCH-019 Section 13's
deferred item, unaffected by this investigation).

---

## 14. Open Questions

- **`ipNetToMediaTable` vs. `ipNetToPhysicalTable`, and whether to walk
  both with fallback** — implementation detail this investigation
  deliberately leaves to FEAT-010A (Section 5), since neither choice
  changes anything this report designs at the `RelationshipObservation`
  or category level.
- **Whether ARP-table walking shares `--snmp` or gets its own CLI flag**
  (Section 8) — left to FEAT-010A; both require identical architectural
  wiring.
- **Whether the ARP row's `Type` (dynamic/static/invalid) should ever gate
  which rows produce observations at all** — this investigation recommends
  retaining but not filtering on it (Section 6), without fully resolving
  whether a future refinement should exclude `invalid` entries specifically
  (arguably stale/negative evidence, not corroborating evidence) — noted
  as genuinely open, not merely deferred as out-of-scope implementation
  detail.
