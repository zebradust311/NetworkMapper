# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — this investigation determines how ADR-013 (Canonical
Relationship Resolution, Status: Accepted) and, through it, ADR-011/ADR-012
should be translated into a concrete `RelationshipResolver`, mirroring
exactly the role ARCH-017 played for `IdentityResolver` after ADR-012. Every
design choice below is either already authorized by ADR-013's Decision
section or falls inside ADR-013's own Future Work ("Relationship resolver
algorithms," "Provider-specific mapping of relationship evidence to
canonical categories") — implementation detail ADR-013 explicitly left for
this kind of investigation, not a new policy question. Section 14
("Suggested ADR Changes") records this finding in full, including one
candidate future ADR trigger that this investigation finds is not yet
reached.

Recommended Next Sprint:
FEAT-009A — Canonical Relationship Resolver (Stage 1), scoped identically
to how FEAT-008A scoped `IdentityResolver`: a pure, inert
`resolve(observations, identities) -> tuple[CanonicalRelationship, ...]`
function, unwired from `DiscoveryEngine`/`Application`, with unit tests and
a permanent architectural integration test. **Revised after review against
ARCH-017/FEAT-008A (see Section 6's Directionality subsection and Section
15): Stage 1 groups `subject`/`related_subject` exactly as reported, for
every category, with no symmetric-category canonicalization.** The
allowlist mechanism originally proposed as part of Stage 1 is deferred —
it is new algorithmic surface `IdentityResolver` never needed, with no
real evidence to validate it against: no provider emits any relationship
observation today, and the recommended first provider (Section 5/15
recommend ARP-corroborated-gateway) does not resolve this either way,
since its own canonical category and symmetric/directional classification
are themselves left to its own implementation sprint, not decided here —
so no confirmed symmetric-category evidence exists to build the mechanism
against, even prospectively.
Offered as a recommendation, not a decision — per scope, engineering
review selects the next sprint.

---

## 1. Executive Summary

ADR-013 (Canonical Relationship Resolution) is Accepted and already answers
every policy-level question this sprint's charter poses at the "what" level:
what a canonical relationship is (a deterministic interpretation of
retained relationship observations), what its endpoints are (canonical
identities, never raw provider references), how corroboration and conflict
should be treated (retained and surfaced, never silently arbitrated), and
where it sits relative to topology (upstream, producing what topology
renders). What ADR-013 explicitly does not do — by design, per its own
Future Work — is specify a resolver algorithm, a concrete type shape, which
observation sources actually participate, or how relationship *evidence*
gets grouped into relationship *interpretations*. That gap is this
investigation's scope, exactly as ARCH-017 filled the equivalent gap for
identity after ADR-012. Section 2 answers this sprint's ten charter
questions directly and concisely; the sections after it show the work
behind each answer.

The central finding is that `RelationshipResolver` can reuse
`IdentityResolver`'s proven algorithm shape almost directly — but only
after correcting one structural mismatch that is not obvious from ADR-013
alone: `IdentityObservation` carries a `value` field that two observations
can *disagree* about (two sources reporting different hostnames), which is
exactly what makes `IdentityResolver._resolve_property()`'s
grouping-and-comparing algorithm work. `RelationshipObservation` has no
such field — `subject`, `related_subject`, and `category` together *are*
the claim, not a value under a claim. Grouping relationship observations
the naive way (by the full `(subject, related_subject, category)` triple,
the closest literal analog of grouping identity observations by
`(subject, property_name)`) makes every observation within a group agree
by construction and makes conflict structurally undetectable — the two
independent-source counting rules `IdentityResolver` relies on would never
see a disagreement to count. Section 6 works through the fix: group by
`(subject, category)` instead, and treat `related_subject` as the value
being corroborated or contested — which restores an exact structural parity
with `IdentityResolver` (`category` plays `property_name`'s role;
`related_subject` plays `value`'s role) and makes conflicting evidence (LLDP
says port 3 connects to switch B; CDP says the same port connects to switch
C) detectable the same way a conflicting hostname is today.

The second finding is that relationship *categories* are not uniformly
shaped the way identity properties are: a **symmetric** category like
"connected to" can be legitimately reported from either endpoint's
perspective (device A's LLDP frame received by B, versus B's own SNMP
bridge-MIB table), while a **directional** category like "hosts service" or
"routes through" cannot be flipped without changing its meaning. Section 6
describes a symmetric-category canonicalization mechanism that would be
needed to fully corroborate such categories — but a post-draft scope review
against ARCH-017/FEAT-008A (this document's own precedent) found that
mechanism is new algorithmic surface with no real evidence to validate it
against yet: no provider emits any relationship observation today (Section
3), and even the recommended first provider does not settle the question,
since its own canonical category and symmetric/directional classification
are themselves left to its implementation sprint rather than decided here
(Section 5/15) — so no confirmed symmetric-category evidence exists to
validate the mechanism against, prospectively or otherwise. This is
exactly the kind of deferrable sophistication `IdentityResolver`'s own
Stage 1 already set precedent for deferring (cross-subject correlation).
**This investigation now recommends Stage 1 omit the canonicalization
mechanism**, grouping every category — including symmetric ones — exactly
as reported, and revisiting corroboration accuracy for symmetric
categories once a provider that actually produces one is being designed.
Section 6 and Section 15 detail this revision.

The third finding is a concrete integration constraint this investigation
surfaces for the first time, not previously written down: a future
relationship-evidence provider must emit `RelationshipObservation.subject`/
`related_subject` values in the **same reference namespace**
`IdentityObservation.subject` already uses for that device (today, an IP
address), not in whatever identifier its own protocol natively reports
(a MAC address, for bridge-MIB; a chassis ID, for LLDP/CDP). If it does
not, the observation's endpoint will never match any `CanonicalIdentity`
and can never resolve to a canonical relationship — silently, since Section
6's Preprocessing stage and Section 8's invariants both treat an
unresolved endpoint as ordinary retained evidence, not an error. Section 5
evaluates every named protocol against this constraint specifically.

The fourth finding, carried forward rather than newly discovered, is that
`RelationshipResolver`'s endpoints — canonical identities from
`IdentityResolver` — are today a **single-run, subject-scoped**
interpretation (FEAT-008A's Stage 1: observations are grouped by `subject`,
which in practice is the discovery-time IP address, within one run's
observation set). ADR-012's own "Relationship with Future ADRs" section
named canonical identity a prerequisite for relationship resolution
*because* a relationship can't be recognized as the same relationship
across scans unless its endpoints can first be recognized as the same
devices across scans — and Stage 1 identity resolution does not yet
provide that. `docs/LAB.md`'s "Stable Device & Identity Correlation" entry
already tracks this as open research, not yet scheduled work. This
investigation finds `RelationshipResolver` can still be built and validated
usefully *within* that limitation — corroborating relationship evidence
gathered within one observation set, exactly as `IdentityResolver` already
corroborates identity evidence within one observation set — but that its
highest-value use case (ARCH-014's own worked example: LLDP plus a routing
table plus ARP corroborating one relationship *across scans*) remains
blocked on the same unresolved cross-run identity problem ARCH-014 Section
7 already named. This is not a reason to defer Stage 1; it is a reason to
scope Stage 1 honestly, the same way `IdentityResolver`'s own docstring
already scopes itself honestly.

No production code is proposed for change by this report.

---

## 2. Direct Answers to the Ten Questions

Concise answers first; the section cited after each is where the reasoning
and evidence live.

**1. What constitutes a canonical relationship?** A deterministic
interpretation derived from one or more retained `RelationshipObservation`s
whose two endpoints both resolve to canonical identities (ADR-012) within
the same observation set — never a provider's direct output. Section 4.

**2. Which observations should participate — LLDP, CDP, STP, ARP, routing,
others?** None do yet (no provider emits `RelationshipObservation` today).
Ranked by near-term readiness once a provider exists: ARP-corroborated-
gateway is the cleanest first candidate (both endpoints already
`Device`-shaped, no new endpoint type). LLDP/CDP are the strongest evidence
for the "connected to" category but need per-port (`Interface`) granularity
this investigation's proposed key does not yet carry. STP (evaluated here
for the first time; ARCH-014 did not assess it) contributes topology-role
information, not direct neighbor identity, and is a weaker fit than
LLDP/CDP for the same category. Routing evidence's far endpoint is often a
subnet, not a device — out of this investigation's endpoint model. Every
candidate source must translate its own native identifier (MAC, chassis ID)
into the same subject reference `IdentityObservation` already uses for that
device, or its evidence can never resolve (Section 1's third finding).
Section 5.

**3. How should corroboration work?** Group by `(subject, category)`,
treat `related_subject` as the value under evaluation, count independent
`(provider, collection_method)` sources exactly as `IdentityResolver`
already does for identity properties. Stage 1 groups `subject`/
`related_subject` exactly as reported for every category — a deliberate,
reviewed scope reduction (Section 6) that leaves symmetric categories
(e.g. "connected to" reported from either end) under-corroborated as two
separate `WEAK` relationships rather than one `CONFIRMED` one, until a
later stage revisits it against real evidence. Section 6.

**4. What conflicts can occur?** More than one distinct `related_subject`
value observed for the same `(subject, category)` — most commonly two
independent sources disagreeing (e.g., LLDP and CDP naming different
neighbors for the same local claim), but not exclusively: mirroring
`IdentityResolver` field-for-field means a single source's own internally
inconsistent reports are sufficient too, exactly as they already are for
identity properties. Section 6.

**5. What evidence must never be discarded?** The original
`RelationshipObservation` objects (never mutated or dropped, including
conflicting ones and ones whose endpoints never resolve); every distinct
side of a genuine conflict (no "losing" observation is ever removed);
provenance on every retained observation. Section 7.

**6. Should relationships have confidence states analogous to
`IdentityResolver`?** Yes for `WEAK`/`CONFIRMED`/`CONFLICTING` — direct
reuse. No analog to `PROBABLE` is recommended; that state is specific to
identity's multi-property rollup and has no relationship equivalent
(Section 6 explains why introducing one would conflate unrelated claims).

**7. What should `RelationshipResolver`'s API look like?**
`resolve(observations: Sequence[IdentityObservation | RelationshipObservation], identities: Sequence[CanonicalIdentity]) -> tuple[CanonicalRelationship, ...]`
— a pure function, mirroring `IdentityResolver.resolve()`'s shape exactly.
Section 8.

**8. Where should it execute in the runtime pipeline?** Immediately after
Identity Resolution, in the same decoupled, additive interpretation path
ARCH-017 established — never inside `DiscoveryEngine.discover()`, never
wired into `Application` for Stage 1. Section 9.

**9. How should canonical identities and canonical relationships interact?**
Relationships are consumers of identities, never the reverse.
`RelationshipResolver` takes `IdentityResolver`'s output as an explicit
input parameter and resolves each observation's raw `subject`/
`related_subject` against it; an observation whose endpoint isn't in that
set contributes no canonical relationship this run, without erroring.
Sections 4 and 8.

**10. Which architectural decisions require a new ADR, and which belong
only in ARCH-018?** None of this investigation's own recommendations
require a new ADR — all fall inside ADR-013's already-authorized Future
Work. One candidate future trigger (non-`Device` endpoints, e.g. a subnet
for Routing evidence, or Redfish-style containment) is named but not yet
reached, since no evidence source reaching that case exists in the
codebase. Section 14.

---

## 3. Current Architecture Assessment

**What already exists.** `RelationshipObservation`
(`networkmapper/observations/models.py:67-104`) is a real, tested type:
`subject`, `related_subject`, `category`, `provenance`
(`ObservationProvenance`: `provider`, `collection_method`, `observed_at`,
`source_run`). It flows through the same plumbing `IdentityObservation`
already uses — `DiscoveryProvider.collect_observations()`
(`networkmapper/discovery/provider.py:21-31`), `DiscoveryEngine.observations`
(`networkmapper/discovery/discovery_engine.py:49,70,75,95`),
`Project.observations` (`networkmapper/project/models.py:31`) — all
additive, all already exercised by the permanent
`tests/test_identity_pipeline.py` architectural integration test.

**What does not exist.** No provider constructs a `RelationshipObservation`
today. `NmapProvider` and `SnmpEnrichmentProvider`'s `collect_observations()`
implementations emit only `IdentityObservation`s (hostname, mac_address,
computer_name, domain, sysName — confirmed directly against
`networkmapper/discovery/nmap_provider.py` and
`networkmapper/discovery/snmp_provider.py`). This is a materially different
starting condition from identity resolution at the point FEAT-008A was
built: `IdentityResolver` had real observations flowing through the
pipeline the day it was implemented; `RelationshipResolver` would not.
Sections 5 and 11 return to this.

**`IdentityResolver` as direct precedent.**
`networkmapper/identity/resolver.py` and `networkmapper/identity/models.py`
are the closest thing to a template this investigation has, and are read
in detail below (Section 6) rather than merely cited: `IdentityResolver`
groups by `subject`, then by `property_name`; computes independence via
`(provider, collection_method)` pairs; assigns `WEAK`/`CONFIRMED`/
`CONFLICTING` per property and rolls up to an identity-level state
including `PROBABLE`; sorts every output collection so results never
depend on input order; and is deliberately not wired into
`DiscoveryEngine`, `Application`, classification, reporting, or
persistence. Every one of these properties has a direct, evaluated analog
below for `RelationshipResolver`.

**`NetworkGraph` has no relationship concept.**
`networkmapper/core/network_graph.py` remains exactly the IP-keyed
`dict[str, Device]` ARCH-014 Section 9 already found, unchanged by
FEAT-007A/007B/008A. `RelationshipResolver`, like `IdentityResolver`, would
be a pure function over `Project.observations` plus `IdentityResolver`
output — it would not read from or write to `NetworkGraph`.

---

## 4. Relationship Model

**What constitutes a canonical relationship?** Per ADR-013, a canonical
relationship is a deterministic interpretation derived from one or more
retained `RelationshipObservation`s whose endpoints both resolve to
canonical identities (ADR-012) under the same observation set. It is never
a provider's direct output copied through — the same "interpretation, not
a field" posture ADR-012 establishes for identity (`identity/resolver.py`'s
own docstring: "not a claim that `subject`... *is* canonical identity").

**Which fields define relationship identity?** Section 1 already found the
naive triple-based key destroys conflict detectability. The corrected
composite key, and this investigation's concrete proposal, is
**`(subject, category)`**, with `related_subject` treated as the value
under evaluation — the direct structural analog of identity's
`(subject, property_name)` key with `value` as the field under evaluation.
This is a deliberate, evaluated departure from ARCH-014 Section 7's own
illustrative shape ("(endpoint A identity, endpoint A interface, endpoint B
identity, endpoint B interface, category)"), which that section itself
flagged as provisional pending an `Interface` model that does not yet
exist; the flattened two-endpoint composite key is what remains once the
interface component degrades away, exactly as ARCH-014 Section 7 already
anticipated ("relationship identity would need to degrade to (endpoint A
identity, endpoint B identity, category)").

**How are endpoints represented?** As `CanonicalIdentity.subject` string
values — today, in practice, the same discovery-time reference
(`IdentityObservation.subject`, an IP address) `IdentityResolver` already
groups by, per its own docstring's explicit disclaimer that this is "a
practical grouping key, not a claim about canonical identity semantics."
`RelationshipResolver` inherits that same disclaimer rather than
introducing a new, stronger claim about endpoint stability that
`IdentityResolver` itself does not make. A `RelationshipObservation` whose
`subject` or `related_subject` does not appear among the supplied
`CanonicalIdentity` set is real, retained evidence (ADR-011) that simply
does not resolve to a canonical relationship this run — mirroring exactly
how `IdentityResolver` already treats a `RelationshipObservation` it is
handed (ignored, not erased, not an error). This exclusion is applied
during Section 6's Preprocessing stage, before grouping — never after —
per Section 6's own explicit statement of why that order is required.

**Self-loops.** No relationship category ADR-013/ARCH-014 evaluated models
a device's relationship to itself. This investigation recommends
`RelationshipResolver` treat `subject == related_subject` (after endpoint
resolution) as excluded from canonical resolution — the same
"retained-but-not-promoted" treatment as an unresolved endpoint, not a
raised error, since a self-referential observation is still real evidence
of *something* (most plausibly a collection artifact) that should not be
silently discarded from `Project.observations`, only withheld from
canonical interpretation. Like the unresolved-endpoint exclusion above,
this is applied during Section 6's Preprocessing stage, before grouping.

**Non-`Device`-shaped and containment endpoints.** ADR-013's Relationship
Categories and Relationship Evidence sections already record that Routing's
far endpoint may be a subnet and Redfish evidence is containment
("part of"), not peering, and explicitly declines to design either. This
investigation does not design them either — `RelationshipResolver`'s
Stage 1 scope (Section 15) is limited to `RelationshipObservation`s whose
both endpoints are canonical-identity-shaped, consistent with the only
category evidence currently reachable in the codebase (Section 3: none
yet, but the nearest candidates per Section 5 — ARP-corroborated-gateway,
Physical/LLDP — are both device-to-device). Extending the model to
non-`Device` endpoints is named explicitly as Future Work (Section 16), not
silently assumed away.

---

## 5. Observation Sources by Protocol

Per this sprint's charter, evaluated against evidence NetworkMapper already
collects or has already investigated collecting (ARCH-003, ARCH-012,
FEAT-003E, ARCH-014), not against a hypothetical future provider. The
governing constraint from Section 1's third finding applies to every source
below: **whatever native identifier a protocol reports must be translated
into the same subject reference `IdentityObservation` already uses for that
device** before a `RelationshipObservation` is emitted, or the endpoint can
never resolve. This is new analysis this investigation adds to ARCH-014's
own per-source assessment, not a restatement of it.

**LLDP / CDP.** Link-layer neighbor-discovery protocols; `NmapProvider`'s
IP-based scanning cannot observe them (FEAT-003E). Reports a neighbor's
chassis ID and local port as one side of a "connected to" relationship —
the strongest near-term evidence for the `connected_to` category, and the
category this investigation's Section 6 symmetric-category allowlist is
built around. Translation requirement: a chassis ID is not an IP address:
a future LLDP/CDP provider must resolve the reported chassis ID to whatever
subject reference the neighbor device's own `IdentityObservation`s use
(today, its IP) before emitting a `RelationshipObservation`, which requires
the neighbor to already be independently discovered — the "unresolved
endpoint" case Section 4 already accommodates architecturally, but which a
real LLDP/CDP provider will hit often in practice (a neighbor switch not
yet scanned). Local-port granularity is lost under this investigation's
`(subject, category)` key (Section 4); this is a known, named ceiling
(Section 12), not solved here.

**STP (Spanning Tree Protocol).** Not evaluated by ARCH-014; assessed here
for the first time per this sprint's explicit charter. SNMP STP-MIB
(`dot1dStp`, `dot1dStpPortTable`) exposes each bridge's root-bridge ID and,
per port, its STP role (root/designated/blocking) and the designated bridge
for that port. This is topology-*role* information — which links are
currently active versus blocked by the spanning-tree algorithm — not a
direct "device A connects to device B" claim the way LLDP/CDP are. Its
evidence unit (a bridge ID) faces the same MAC/bridge-identifier-to-subject
translation requirement as Bridge MIB, below, and this investigation finds
it a weaker, not stronger, corroboration source for `connected_to` than
LLDP/CDP specifically because it tells you a port's *role* in the tree, not
which specific neighbor sits on it — a designated-bridge field can
corroborate that *some* link exists on a port without independently
confirming *which* device is on the other end the way a chassis ID does.
Does not naturally emerge from any current provider.

**SNMP interface MIBs (`ifTable`/`ifXTable`).** Per-interface facts about
the interface itself (description, speed, admin/oper status) — not
relationship evidence by themselves (ARCH-014 Section 4, reconfirmed). This
is the evidence that would populate an `Interface` model if one existed
(Section 12), and a prerequisite for LLDP/CDP's local-port field to be
human-meaningful, not a participating relationship source on its own.

**Bridge MIB (`dot1dTpFdbTable` / Q-BRIDGE-MIB).** MAC-to-switch-port
forwarding table — could back `connected_to` evidence without LLDP/CDP.
Its evidence unit is a MAC address, not an IP or any other subject
reference `IdentityObservation` currently uses. This investigation finds
this is not merely ARCH-014's already-named "no MAC→Device resolution
capability" gap restated — it is now, concretely, the exact translation
requirement Section 1's third finding names: a Bridge MIB provider cannot
emit a valid `RelationshipObservation` at all until something resolves a
MAC address to the same subject value that device's own
`IdentityObservation`s use, and no such resolution mechanism exists
anywhere in the codebase today (not in `NetworkGraph`, IP-keyed only; not
in `IdentityResolver`, subject-keyed only, with no MAC index).

**ARP (SNMP `ipNetToMediaTable`, or a local `arp -a`/equivalent).**
Produces IP-to-MAC bindings observed from the perspective of whichever host
or device answered the query. Both the observing device and the observed
IP are already `Device`-shaped and already use IP as their subject
reference — the one source among all evaluated here that satisfies Section
1's third finding with no additional translation step, confirming
ARCH-014 Section 4's own finding that ARP is "the cleanest fit among all
sources evaluated for a corroboration example." This investigation's own
recommendation (Section 15) makes this NetworkMapper's most realistic first
relationship-evidence provider. This investigation does not assign ARP
evidence a canonical category name or a symmetric/directional
classification — per ADR-013's own deferral of provider-specific category
mapping, and consistent with this document's general position (Section 1)
that provider-specific mapping is implementation detail, that mapping is
intentionally left to the Stage 3 provider implementation sprint itself
(Section 15), not decided here. A Stage 3 implementer must choose it
deliberately rather than assume, by analogy to Physical/LLDP evidence, that
ARP evidence belongs on Section 6's symmetric-category allowlist — an ARP
binding observed from one side (the querying device) is not obviously the
same claim as one observed from the other, and nothing in this
investigation resolves that either way.

**Routing tables (SNMP `ipCidrRouteTable`, or a local `ip route`/WMI
query).** The far endpoint is frequently a subnet or next-hop IP, not a
discovered `Device` — the clearest case in ARCH-014 Section 4 needing a
non-`Device` endpoint type this investigation explicitly does not design
(Section 4). Where the next hop happens to be a device NetworkMapper has
already discovered by IP, the translation requirement is trivially
satisfied (it's already an IP); where the endpoint is a bare subnet, it is
out of this investigation's endpoint model entirely, not merely
unresolved.

**WMI (`Win32_NetworkAdapterConfiguration` default gateway/DNS,
`Win32_LogonSession`/domain-controller queries).** Reports a gateway or DNS
server by IP — satisfies the translation requirement the same way ARP does,
since the endpoint is already IP-shaped. Directional by nature (a host's
default gateway is not symmetric), so these categories would not belong on
Section 6's symmetric-category allowlist.

**VMware (vCenter/ESXi API).** Host-to-VM relationship-shaped evidence.
Translation requirement is the hardest among near-term candidates: a
reported VM may already be a `Device` NetworkMapper discovered
independently at its own IP, and nothing in the current architecture
recognizes that as the same entity (ARCH-014 Section 3/7) — a
corroboration/identity problem this investigation does not solve, layered
on top of Section 1's translation requirement.

**Redfish.** Chassis/component containment ("part of"), not peering —
out of this investigation's endpoint/relationship-shape model (Section 4),
consistent with ADR-013's own deferral.

**SSH.** Confirmed by ARCH-014 Section 4 to carry no relationship category
of its own; whatever runs over it (`ip route`, `arp -a`) determines which
category above applies, and inherits that category's translation
requirement unchanged.

---

## 6. Corroboration Strategy

**Resolver pipeline.** Grouping and endpoint/self-loop exclusion were
previously specified without stating their relative order — two orderings
are possible, and they are not equivalent (worked through below, under
"Preprocessing must precede grouping"). This section states the
authoritative order explicitly; it is the single source of truth for
`RelationshipResolver`'s internal pipeline, and Sections 4 and 8
cross-reference it rather than restating it:

```
RelationshipObservation
        ↓
Preprocessing
    - resolve each observation's subject/related_subject against
      the supplied CanonicalIdentity set
    - exclude observations with an unresolved endpoint
    - exclude self-loops (subject == related_subject, post-resolution)
        ↓
Grouping — by (subject, category), Section 4
        ↓
Corroboration — independent-source counting, below
        ↓
CanonicalRelationship (Section 8)
```

Preprocessing operates on individual observations, before any grouping
occurs. A `RelationshipObservation` excluded during preprocessing never
enters any `(subject, category)` group and never contributes a
`related_subject` value for that group's corroboration/conflict
computation — it is invisible to Grouping and Corroboration entirely, not
merely excluded from the final output. This mirrors, and extends to
content-based filtering, the same precede-grouping filter pattern
`IdentityResolver.resolve()` already uses for its own type-based filter
(`identity_observations = [o for o in observations if isinstance(o,
IdentityObservation)]`, `identity/resolver.py:58-59`, executed before any
grouping in that resolver too).

**Preprocessing must precede grouping.** This ordering is required, not
stylistic. If grouping ran first — i.e., if exclusion were applied only to
the finished `CanonicalRelationship` output rather than to observations
beforehand — a self-loop artifact (e.g., a misconfigured switch reporting
itself as its own LLDP neighbor) or an observation whose target is not yet
independently discovered would still occupy the same `(subject, category)`
group as any genuine, valid observation for that same subject and
category, since the grouping key does not include `related_subject`
(below). A real `A → B` observation sharing a group with a noisy or
premature `A → A` or `A → (unresolved)` observation would then present
more than one distinct value under Corroboration's counting rule —
incorrectly producing `CONFLICTING` for a relationship that has only one
genuine, single-source claim behind it. Preprocessing-first avoids this
by construction: excluded observations are removed before Grouping ever
runs, so they cannot contaminate a group they were never part of.

**The structural correction, worked through.** `IdentityResolver` computes
`PropertyCorroboration` by grouping a subject's observations by
`property_name`, then within each group collecting values by independent
`(provider, collection_method)` source: more than one distinct value among
independent sources is `CONFLICTING`; two or more independent sources
agreeing on one value is `CONFIRMED`; otherwise `WEAK`
(`identity/resolver.py:96-121`). Applying this unmodified to
`RelationshipObservation` by grouping on the full
`(subject, related_subject, category)` triple would put every observation
sharing that triple in the same group by definition — there is no
`related_subject` disagreement possible *within* a group already keyed by
`related_subject`. Two observations claiming different neighbors for the
same local relationship (LLDP: port 3 → switch B; CDP: port 3 → switch C)
would land in two *separate*, individually-unconflicted groups
`(A, connected_to) → B` and `(A, connected_to) → C` rather than being
recognized as competing claims about the same thing — silently losing
exactly the conflict ADR-013 requires be surfaced, not hidden. Grouping
instead by `(subject, category)` and treating `related_subject` as the
value (on already-preprocessed observations, above) restores the
identical mechanism `IdentityResolver` already uses, field-for-field:
`category` in the role of `property_name`, `related_subject` in the role
of `value`.

**Confidence states — direct reuse, one deliberate omission.** This
investigation recommends the identical three-state vocabulary
`IdentityResolver` uses at the property level: `WEAK` (one independent
source), `CONFIRMED` (two or more independent sources agreeing),
`CONFLICTING` (more than one distinct value present among the group's
retained observations, never silently arbitrated). This is a direct,
literal reuse of `IdentityResolver._resolve_property()`'s own definition,
not merely its vocabulary: that method has no independent-source-count
gate on its `CONFLICTING` branch — `len(distinct_values) > 1` alone
triggers it, regardless of how many independent sources contributed those
values. `CONFLICTING` therefore does not require the disagreement to
originate from two *different* independent sources; a single source's own
internally inconsistent reports are already sufficient, exactly as they
already are for identity properties. (An earlier draft of this section
described `CONFLICTING` as "independent sources disagree," which read in
isolation could be misunderstood as requiring source plurality — this
revision aligns the prose with the algorithm it has always specified,
per the field-for-field mirroring this section requires, rather than
changing the algorithm to match the earlier, imprecise prose.)
`IdentityCorroborationState.PROBABLE` — the identity-level rollup across
*multiple properties* of one subject — has no direct analog and this
investigation recommends **not** introducing one. `PROBABLE` exists at
identity's subject level because a subject's several distinct properties
(hostname, domain, computer_name) can each be individually weak yet
jointly increase confidence *in the same subject's identity*. A
relationship has no equivalent breadth dimension: `connected_to` and
`hosts_service` are unrelated claims about a subject, and one being weakly
observed says nothing about the other's truth — inventing a rollup here
would conflate independent claims the way ADR-013's Relationship
Explainability section explicitly warns against ("never by reference to a
provider-specific heuristic that bypassed retained evidence"). This is why
Section 4's model has no identity-level wrapper analogous to
`CanonicalIdentity` wrapping several `PropertyCorroboration`s — one
`CanonicalRelationship` per `(subject, category)` is the complete output;
nothing rolls up above it.

**Independence.** Identical definition to ADR-012/`IdentityResolver`:
two observations sharing both `provenance.provider` and
`provenance.collection_method` are the same underlying collection
operation and must not count as two independent confirmations — ADR-013's
Relationship Independence section names this explicitly as "the same
requirement ADR-012 established for identity evidence, applied to
relationship evidence." This requirement governs what counts as a
*confirmation*; it does not gate what counts as a *conflict*. A single
source's own internally differing reports are not two independent
confirmations of anything, but per Confidence states above, they are
still more than one distinct value — sufficient for `CONFLICTING` on
their own, identical to how `IdentityResolver` already treats identity
properties.

**Directionality — a real mechanism, deliberately deferred out of Stage 1.**
Some categories are symmetric (peering): "connected to," observed from
either end, describes one physical fact regardless of which endpoint's
provider reported it. Some are directional: "hosts service," "routes
through," "managed by" mean something different — or nothing at all — if
`subject`/`related_subject` are swapped. Grouping strictly by literal
`subject` (Section 4's key) puts device A's own LLDP-reported observation
and device B's own SNMP-bridge-MIB-reported observation of the *same
physical link* into two different groups (`(A, connected_to) → B` and
`(B, connected_to) → A`), which never corroborate each other under Stage
1's grouping — undercounting corroboration for exactly the categories
ARCH-014's worked example (LLDP + routing table + ARP corroborating one
relationship) depends on.

A mechanism to fix this exists — canonicalize an observation's
`(subject, related_subject)` pair (e.g., sort it) before grouping, for
categories on a small, explicit, extensible symmetric-category allowlist
(starting with `connected_to`, the only category with any near-term
evidence path per Section 5) — but this investigation's own scope review
against ARCH-017/FEAT-008A (Section 1, Section 15) found it does not belong
in a first implementation: it is new algorithmic surface `IdentityResolver`
never needed, and it has no real evidence to validate it against — not
merely because zero providers exist today (Section 3), but because even
the recommended first provider does not resolve the question, since
Section 5/15 leave its own canonical category and symmetric/directional
classification to its own implementation sprint rather than deciding it
here. Building the canonicalization mechanism now would mean building it
against a category taxonomy that does not yet exist, not merely against
evidence that has not yet arrived. It also mirrors exactly the kind of
harder, adjacent problem `IdentityResolver`'s own Stage 1 already set
precedent for deferring (cross-subject correlation) rather than solving
upfront.

**This investigation now recommends Stage 1 group `subject` and
`related_subject` exactly as reported, for every category, with no
canonicalization.** This is a known, accepted limitation, not a defect:
Stage 1 will represent a symmetric category's evidence as two independent,
non-corroborating `WEAK` relationships (one per reporting direction) rather
than one `CONFIRMED` one, until a later stage — sequenced against an actual
symmetric-category provider, per Section 15 — revisits it. No category
observed in Stage 1 is silently merged incorrectly either way; the
limitation is under-corroboration, never mis-corroboration.

---

## 7. Conflict Handling

**How are conflicting observations retained?** Identically to
`PropertyCorroboration.observations` (`identity/models.py:60-62`): every
retained observation contributing to a `(subject, category)` group is kept
in full on `CanonicalRelationship.observations`, sorted deterministically
(this investigation recommends the same field order `IdentityResolver`
already uses: provider, collection method, then the relationship-specific
field — `related_subject` in place of `value`) — never collapsed to one
"winning" `related_subject`, exactly mirroring ADR-013's "conflicting
observations... must be retained and surfaced, never silently arbitrated."

**How is provenance preserved?** Unchanged from ADR-011/ADR-013 —
`RelationshipObservation.provenance` already carries provider, collection
method, timestamp, and source/run identity (`observations/provenance.py`),
and `RelationshipResolver` never mutates or strips it, the same guarantee
`IdentityResolver` already proves by test
(`test_identity_resolver.py::IdentityResolverProvenanceRetentionTest`,
asserting `assertIs(retained, observation)` — the retained object is the
original, not a copy).

**What should never be discarded?** Three things, all already established
by ADR-011/ADR-012/ADR-013 and simply restated here at the relationship
layer for completeness: (1) the original `RelationshipObservation` objects
— never mutated, never dropped, even when conflicting or when their
endpoints never resolve to a canonical identity; (2) a genuine conflict's
losing side — there is no "losing side"; `CONFLICTING` retains every
distinct `related_subject` value's supporting observations, not just the
plurality; (3) an unresolved-endpoint observation's presence in
`Project.observations` — `RelationshipResolver` choosing not to promote it
to a `CanonicalRelationship` (Section 4) does not remove it from
`Project.observations`, where it remains available to a future resolver
run once its endpoint's identity does resolve.

---

## 8. Resolver Interface

Proposed shape, deliberately mirroring `IdentityResolver`'s proven public
surface:

```python
class RelationshipResolver:
    def resolve(
        self,
        observations: Sequence[IdentityObservation | RelationshipObservation],
        identities: Sequence[CanonicalIdentity],
    ) -> tuple[CanonicalRelationship, ...]:
        ...
```

**`CanonicalRelationship`'s proposed type shape.** Referenced throughout
this document but not previously given as a concrete definition; added
here to close that gap:

```python
class RelationshipCorroborationState(StrEnum):
    """Mirrors IdentityCorroborationState (identity/models.py), minus
    PROBABLE — Section 6 explains why no relationship-level analog to
    PROBABLE is recommended."""

    WEAK = "weak"
    CONFIRMED = "confirmed"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class CanonicalRelationship:
    """One resolved interpretation of one subject's relationships in one
    category — Section 4's (subject, category) key, the complete output
    unit (Section 6: nothing rolls up above it, unlike CanonicalIdentity).

    Deliberately has no separate field holding "the" resolved
    related_subject value. When state is WEAK or CONFIRMED, exactly one
    distinct related_subject value is present across `observations` and is
    recoverable from there; when CONFLICTING, more than one is present and
    none is privileged. This mirrors PropertyCorroboration's identical
    absence of a collapsed value field (identity/models.py) — a consumer
    reads the value(s) from the retained observations, never from a field
    that would have to silently pick one during a conflict.
    """

    subject: str
    category: str
    state: RelationshipCorroborationState
    observations: tuple[RelationshipObservation, ...]
```

**Inputs.** `observations` is the same mixed collection
`IdentityResolver.resolve()` already accepts — in practice,
`Project.observations` — from which `RelationshipResolver` extracts only
`RelationshipObservation`s, ignoring `IdentityObservation`s exactly as
`IdentityResolver` already ignores `RelationshipObservation`s
(`identity/resolver.py:58-59`, mirrored). `identities` is
`IdentityResolver.resolve()`'s own output — this is the concrete
implementation of ADR-012's "Relationship with Future ADRs" dependency:
`RelationshipResolver` cannot run before `IdentityResolver` has, and takes
its output as a direct, explicit parameter rather than re-deriving
identities itself.

**Outputs.** `tuple[CanonicalRelationship, ...]`, sorted deterministically
(by `subject`, then `category`, mirroring `IdentityResolver.resolve()`'s
own sort-by-subject and `_resolve_subject()`'s sort-by-property-name).

**Invariants.** Four of the six below are a direct, evaluated carry-forward
of an invariant `IdentityResolver` already upholds; the two endpoint/
self-loop exclusion invariants are not — `IdentityResolver` has no
analogous content-based filter (only a type-based one), so those two are
genuinely new mechanics, specified fully by Section 6's Preprocessing
stage rather than by precedent:

- Never mutates `observations` or `identities`. (Carried forward.)
- Never touches `Device`, `NetworkGraph`, classification, reporting, or
  persistence — a pure function over its two inputs, exactly like
  `IdentityResolver.resolve()`. (Carried forward.)
- Deterministic and order-independent: the same `(observations, identities)`
  pair, processed in any order, produces byte-identical output — the
  identical determinism requirement ADR-013's Relationship Principles
  restates from ADR-012, and the identical mechanism satisfies it
  (grouping into dicts/sets, then explicitly sorting every output
  collection, never relying on input iteration order). (Carried forward.)
- A `RelationshipObservation` whose subject or related_subject does not
  resolve to a supplied `CanonicalIdentity` is excluded during Section 6's
  Preprocessing stage, before grouping, and so contributes no
  `CanonicalRelationship` — silently excluded, not an error, not a
  partial/pending result (ARCH-017's "no partially interpreted identity or
  relationship is ever exposed to a consumer" principle, applied here
  directly). (New; see Section 6.)
- A self-loop (`subject == related_subject` after endpoint resolution) is
  likewise excluded during Preprocessing, before grouping, per Section 4/6,
  and so contributes no `CanonicalRelationship`. (New; see Section 6.)
- Every `RelationshipObservation` supplied and retained by a
  `CanonicalRelationship` is preserved by identity (`is`, not merely `==`),
  matching `IdentityResolver`'s own proven provenance-retention guarantee.
  (Carried forward.)

---

## 9. Pipeline Integration

**Where does this fit?** Exactly where ARCH-017's corrected pipeline
diagram already places it — the stage directly after Identity Resolution,
in the same decoupled, additive interpretation path that runs alongside,
never inside, the existing Discovery → Enrichment → Classification →
Reporting pipeline:

```
Discovery Provider ──► Enrichment Provider ──► Device (unchanged) ──► Classification ──► Reporting
        │                       │
        └────────────┬──────────┘
                      ▼
          Observation Emission (additive)
                      ▼
           Observation Retention (Project.observations)
                      ▼
              Identity Resolution (IdentityResolver)
                      ▼
            Relationship Resolution (RelationshipResolver)
                      ▼
                  (future) Topology
```

**What should it consume?** `Project.observations` (for
`RelationshipObservation`s) and `IdentityResolver.resolve()`'s output (for
endpoint resolution) — never `Device`, `NetworkGraph`, or raw provider
output directly. This is not a new design choice; it is ADR-013's
Relationship Endpoints section and Relationship-with-Future-Topology
section applied literally: relationships exist between canonical
identities, and nothing about `Device` or `NetworkGraph` changes as a
result of this work, the identical non-goal FEAT-008A already delivered on
for `IdentityResolver`.

**Should it be wired into `DiscoveryEngine`/`Application`?** No, for
Stage 1 (Section 15) — identical posture to `IdentityResolver`'s own
explicit, docstring-recorded scope ("not wired into `DiscoveryEngine`,
`Application`, classification, reporting, or persistence — nothing in the
existing pipeline calls it"). `RelationshipResolver` should launch equally
inert, callable directly by tests and by whatever future consumer
(topology, a report, a CLI diagnostic) engineering review authorizes to
call it, not by `DiscoveryEngine.discover()` itself. Wiring resolvers into
the live pipeline changes runtime behavior and is explicitly out of this
sprint's scope regardless.

**How does it interact with the future topology engine?** As a producer,
never a peer. ADR-013's Relationship-with-Future-Topology section already
settles this: "Topology renders interpreted relationships; it is not
responsible for relationship truth, and it must not shortcut relationship
interpretation by reasoning from provider output directly." This
investigation designs `RelationshipResolver` as the thing that makes that
possible — a `CanonicalRelationship` is exactly the interpreted,
provenance-preserving unit a future topology consumer would read — without
designing topology itself, which remains out of scope here exactly as it
was out of scope for ARCH-014.

---

## 10. Testing Strategy

**Unit tests** (a new `tests/test_relationship_resolver.py`, structurally
parallel to `tests/test_identity_resolver.py`, which this investigation
finds is the right template to clone rather than invent independently):

- Empty input produces no relationships.
- A single observation with both endpoints resolved produces one `WEAK`
  `CanonicalRelationship`.
- Two independent sources agreeing on the same `related_subject` for the
  same `(subject, category)` produce `CONFIRMED`.
- Two observations from the same `(provider, collection_method)` do not
  confirm (independence, mirroring
  `IdentityResolverCorroborationTest::test_duplicate_observations_from_the_same_source_do_not_confirm`).
- Two independent sources reporting different `related_subject` values for
  the same `(subject, category)` produce `CONFLICTING`, with both retained
  (Section 7) — the test this investigation's Section 6 correction exists
  specifically to make possible.
- A single independent source reporting two different `related_subject`
  values for the same `(subject, category)` also produces `CONFLICTING`,
  with both retained — `CONFLICTING` does not require the disagreement to
  originate from two different independent sources (Section 6), mirroring
  `IdentityResolver._resolve_property()`'s identical, ungated behavior for
  identity properties.
- An observation whose `subject` or `related_subject` is absent from the
  supplied identities produces no `CanonicalRelationship` and raises no
  error (Section 8).
- A self-loop observation produces no `CanonicalRelationship` (Section 4).
- A symmetric-category observation (e.g. `connected_to`) reported from each
  endpoint's perspective produces two independent, non-corroborating `WEAK`
  relationships in Stage 1, not one `CONFIRMED` one — the explicit,
  positive test proving Stage 1's deferred-directionality limitation
  (Section 6) behaves as documented, not as an accidental gap. The
  canonicalization mechanism itself, and the test proving either
  direction's report corroborates the same relationship, is deferred to
  the later stage that introduces it (Section 15).
- `IdentityObservation`s present in the input are ignored, not errors
  (mirroring
  `IdentityResolverGroupingTest::test_relationship_observations_are_ignored_not_erroring`,
  inverted).
- Order-independence across many random permutations of both `observations`
  and `identities` (mirroring `IdentityResolverDeterminismTest`, with
  `random.Random` seeded for reproducibility exactly as the existing test
  does).
- Original observation objects are preserved by identity, not copied
  (mirroring `IdentityResolverProvenanceRetentionTest`).

**Architectural integration test.** This investigation recommends
extending `tests/test_identity_pipeline.py` (or adding a sibling test
alongside it, engineering review's call at implementation time) to cover
the full contract this sprint's own precedent, FEAT-008A, established:

```
Application → DiscoveryEngine → Project.observations → IdentityResolver → RelationshipResolver
```

using the same pattern already proven — a real (unmocked) `DiscoveryEngine`
fed a fake, in-process `DiscoveryProvider` that emits both
`IdentityObservation`s and `RelationshipObservation`s without touching the
network, verifying `RelationshipResolver.resolve()` runs without exception
against real `Project.observations` and real `IdentityResolver` output, and
produces `CanonicalRelationship` objects when resolvable evidence exists.
This is the direct relationship-layer analog of the identity pipeline test
FEAT-008A's validation sprint produced and engineering review already
promoted to permanent regression coverage — the same category of test,
extended one stage further.

**Validation sprint requirements.** Identical workflow to FEAT-008A's:
`python -m devtools validate --all` (comprehensive — required because this
work touches something outside the classification layer, per
`docs/process/validation-workflow.md`), full existing benchmark suite
unchanged (near-zero risk, by the same structural isolation ARCH-017
Section 7 already demonstrated for `BenchmarkRunner` — a resolver that
never touches `Device` cannot affect classification accuracy), and a
temporary or permanent integration validation confirming the full chain
completes without exception, consistent with the process this sprint's own
predecessor (FEAT-008A) established and this document explicitly names as
the pattern to repeat.

---

## 11. Risk Assessment

**No real evidence source exists yet.** Section 3's finding: zero
providers emit `RelationshipObservation`s today. `RelationshipResolver`
Stage 1 (Section 15) would be exercisable only via unit tests and the
architectural integration test's synthetic fake provider — real,
demonstrated correctness against synthetic evidence, but no real-world
validation until a future relationship-evidence provider exists (Section
5's nearest candidate: ARP-corroborated-gateway). This is a real gap
between "resolver exists and is correct" and "resolver has ever resolved
anything observed from a real network," named explicitly rather than
obscured.

**Symmetric categories under-corroborate in Stage 1 (accepted, by design).**
Section 6's scope reduction means a symmetric category like `connected_to`
reported from both endpoints produces two independent `WEAK` relationships
in Stage 1, not one `CONFIRMED` one, until a later stage introduces
canonicalization. This is a known limitation, not a silent defect — Section
10's explicit positive test documents the current behavior — but a future
consumer (e.g. an early topology prototype) reading Stage 1 output directly
must not mistake "two `WEAK` relationships between the same pair" for two
different physical facts. Mitigated by naming the limitation here and in
Section 6/15 rather than only in code comments a future reader might miss.

**Endpoint stability is still Stage-1-scoped.** Section 1's fourth finding,
restated as a risk: `RelationshipResolver`'s endpoints are only as stable
as `IdentityResolver`'s current subject-scoped grouping, which is
single-run. Cross-run relationship corroboration — ARCH-014's own
motivating worked example — is not yet meaningful until the cross-subject
identity correlation problem `docs/LAB.md` already tracks is addressed.
This does not block Stage 1 (Section 15 scopes around it, the same way
`IdentityResolver` Stage 1 already did), but it does mean Stage 1's
practical value is bounded to within-one-observation-set corroboration,
not the cross-scan case that motivated ARCH-014 in the first place.

**Endpoint-namespace translation is an easy defect to introduce silently.**
Section 5's cross-cutting finding, restated as a risk: a future provider
that emits a `RelationshipObservation` using its protocol's native
identifier (a MAC, a chassis ID) instead of the subject reference the
device's own `IdentityObservation`s use will produce observations that
*look* valid, pass no validation anywhere in the pipeline (nothing in
`DiscoveryProvider`, `DiscoveryEngine`, or `RelationshipResolver` checks
this), and simply never resolve to a canonical relationship — a silent,
hard-to-diagnose gap rather than a loud failure. Mitigated by naming the
requirement explicitly here so a future provider implementation cannot
discover it only after shipping; not mitigated by any mechanism this
investigation designs (no validation is proposed, consistent with not
implementing production code).

**No `Interface`/port model.** Carried forward from ARCH-014 Section 4/7,
unchanged: LLDP/CDP evidence's local-port granularity has nowhere to go in
the `(subject, category)` key this investigation proposes (Section 4),
exactly as ARCH-014 Section 7 already anticipated the key would need to
"degrade" without an `Interface` model. Not a Stage 1 blocker — Stage 1 has
no LLDP/CDP provider to lose that granularity from yet — but a known
ceiling on what Stage 1's shape can express once such a provider exists.

**Benchmark/classification regression risk.** Near-zero, by the same
structural argument ARCH-017 Section 7 already made for identity
resolution and repeated here for completeness: `RelationshipResolver`
reads `Project.observations` and `IdentityResolver` output only, writes
nothing to `Device` or `NetworkGraph`, and is not wired into
`DiscoveryEngine.discover()` — `BenchmarkRunner.load_inventory()` does not
invoke any of this code path, so it cannot regress benchmark accuracy by
construction.

---

## 12. Technical Debt

Confirmed against current repository state; not created by this
investigation.

**1. `NetworkGraph` still has no relationship/topology collection** —
ARCH-014 Section 9's leading debt item, reconfirmed unchanged. This
investigation's `RelationshipResolver` does not resolve it — it produces
`CanonicalRelationship` values with nowhere in `NetworkGraph` to live,
consistent with the same "additive interpretation layer, not a `Device`/
`NetworkGraph` change" posture ARCH-017 already established for identity.

**2. No `Interface`/port model** — ARCH-014 Section 4/7/9, reconfirmed.
Section 11 above names the concrete ceiling this creates for Stage 1's
proposed key shape.

**3. Cross-run/cross-subject identity correlation remains unsolved** —
tracked in `docs/LAB.md`, reconfirmed here as now also a concrete
`RelationshipResolver` limitation (Section 11), not only an
`IdentityResolver` one.

**4. Zero relationship-evidence providers exist** — a new observation
specific to this investigation (Section 3/5), not carried forward from
ARCH-014, since ARCH-014 predates FEAT-007B's provider-emission work and
could not have confirmed this against running code the way this
investigation could.

**5. No MAC-address-to-canonical-identity resolution mechanism exists** —
a new observation specific to this investigation (Section 5's Bridge MIB
assessment), concretely blocking any future Bridge-MIB or STP provider
from emitting a resolvable `RelationshipObservation` until it exists.

---

## 13. Open Questions

Genuinely unresolved by this investigation, not merely deferred as
out-of-scope implementation detail (contrast with Section 16, Future Work,
which lists work this investigation deliberately did not attempt):

- **Should `RelationshipResolver` accept a confidence/validation floor for
  which categories it evaluates at all**, given only one category
  (`connected_to`) has any near-term evidence path (Section 5)? This
  investigation's proposed API (Section 8) accepts any category
  unconditionally; whether Stage 1 should artificially restrict itself to
  categories with real evidence sources, or accept the full open taxonomy
  ADR-013 already declines to freeze, is a scope call this investigation
  surfaces without resolving.
- **How should a future consumer (e.g. topology) distinguish "no evidence
  observed" from "evidence observed but excluded" (unresolved endpoint or
  self-loop)** — both currently produce simply no `CanonicalRelationship`
  in the output, with the distinguishing reason recoverable only by
  manually re-inspecting `Project.observations`. Whether this asymmetry of
  information matters enough to warrant a diagnostic mechanism is not
  resolved here (Section 8 explicitly declines to design one).
- **Should the symmetric-category allowlist (Section 6, deferred to Stage
  3.5 per Section 15) live as a constant on `RelationshipResolver` itself,
  or as a field on a future relationship taxonomy/registry** — this
  investigation sketches the mechanism but not its concrete placement,
  since no such taxonomy/registry exists yet, inventing one is out of this
  investigation's scope, and the question is no longer immediate now that
  the mechanism itself is deferred out of Stage 1.
- **What should happen when the same physical evidence source (e.g. one
  SNMP walk) yields both an `IdentityObservation` and a
  `RelationshipObservation` in the same call** — independence today is
  computed separately within each resolver; whether cross-resolver
  independence interactions matter is not evaluated here, because no
  provider produces both from one collection operation today (Section 3).

---

## 14. Suggested ADR Changes

**No changes to ADR-013 are proposed.** This investigation's own
recommendations — the `(subject, category)` grouping key (Section 4), the
three-state (not four-state) corroboration vocabulary (Section 6), the
symmetric-category allowlist mechanism (Section 6), the
`resolve(observations, identities)` interface shape (Section 8) — all fall
inside ADR-013's own Future Work ("Relationship resolver algorithms,"
"Provider-specific mapping of relationship evidence to canonical
categories"), the same category of already-authorized implementation
detail ARCH-017 filled in for identity without a new ADR or amendment. This
investigation finds no reason to depart from that precedent, and no
statement in ADR-013's Decision, Alternatives Considered, or Consequences
sections that this investigation's recommendations contradict.

**No new ADR is proposed.** ADR-013 already is the relationship-resolution
ADR this sprint's charter frames as a future deliverable ("Research →
Architecture → ADR"). ADR-013 predates this investigation and this
investigation builds on it rather than producing it.

**One candidate future ADR trigger, not yet reached.** If a future sprint
needs to represent a genuinely non-`Device` relationship endpoint (a
subnet, for Routing evidence) or genuine containment rather than peering
(Redfish's "part of"), that would extend `CanonicalRelationship`'s
endpoint representation (Section 4) beyond what this investigation designs
— at that point, engineering review should evaluate whether the extension
is implementation detail (another ARCH-style investigation, no ADR) or a
big enough departure from ADR-013's "canonical identities" endpoint framing
to warrant its own ADR or an amendment to ADR-013. This investigation does
not resolve that question now because no evidence source reaching that case
exists yet (Section 3), consistent with ADR-013's own deferral of the
identical question.

---

## 15. Suggested Implementation Roadmap

Mirroring FEAT-008A's own staging, which this investigation finds
transfers directly:

**Stage 1 — `RelationshipResolver` introduced, inert, directional-only.**
`CanonicalRelationship` and `RelationshipCorroborationState` types and the
resolver itself (Section 8), grouping `subject`/`related_subject` exactly
as reported for every category (Section 6 —
**revised after review against ARCH-017/FEAT-008A**: the symmetric-category
canonicalization mechanism originally scoped into Stage 1 is deferred to
Stage 3.5, below), unit tests (Section 10) — not wired into
`DiscoveryEngine` or `Application`, identical scope discipline to
FEAT-008A's own Stage 1.

**Stage 2 — Permanent architectural integration test.** Extends
`tests/test_identity_pipeline.py` or adds a sibling test (Section 10),
following the exact validation-sprint-then-engineering-review process this
document's own predecessor sprint (FEAT-008A) just established and
engineering review just approved as the pattern to repeat.

**Stage 3 (separate future sprint, not authorized here) — first
relationship-evidence provider.** Section 5's own finding that
ARP-corroborated-gateway evidence is the cleanest near-term candidate (no
new endpoint type, both ends already `Device`-shaped, no translation
requirement to solve first) makes it the natural first real evidence
source to validate `RelationshipResolver` against actual discovery, rather
than only synthetic test fixtures. Per Section 5's ARP paragraph, this
stage is also where the provider chooses ARP evidence's canonical category
name and symmetric/directional classification — intentionally not decided
by this investigation.

**Stage 3.5 (deferred from Stage 1 by this review) — symmetric-category
canonicalization.** The directionality mechanism Section 6 describes but
recommends withholding from Stage 1: sequenced here, against an actual
symmetric-category provider (LLDP/CDP, most plausibly, per Section 5),
rather than upfront against no evidence. Not designed further here beyond
the mechanism Section 6 already sketches.

**Stage 4 (further out) — `Interface` model, MAC-to-identity resolution,
non-`Device` endpoints, topology.** Named for sequencing only, per
ARCH-014's own scope exclusion and this investigation's Section 11/12
findings; none of it designed here. A Bridge-MIB or STP provider (Section
5) is blocked on the MAC-to-identity resolution component of this stage
specifically.

---

## 16. Future Work

Explicitly deferred, and not authorized by this investigation:

- The Stage 1 implementation sprint itself (Section 15) —
  `CanonicalRelationship`, `RelationshipCorroborationState`, and
  `RelationshipResolver`'s concrete code.
- The permanent architectural integration test extension (Section 10,
  Stage 2).
- Any relationship-evidence provider (ARP-corroborated-gateway, LLDP/CDP,
  Bridge MIB, STP, or otherwise) — Stage 3, a separate future sprint.
- The symmetric-category canonicalization mechanism (Section 6, Stage 3.5)
  — deliberately scoped out of Stage 1 by this document's own review
  against ARCH-017/FEAT-008A; Stage 1 ships with the accepted
  under-corroboration limitation Section 6/11 document instead.
- The `Interface`/port model and any relationship-identity key extension
  that would depend on it (Section 11's ceiling finding).
- A MAC-address-to-canonical-identity resolution mechanism (Section 12,
  item 5) — required before any Bridge-MIB or STP provider can participate.
- Non-`Device` relationship endpoints (subnets) and containment-shaped
  relationships (Redfish) — Section 4, Section 14's candidate ADR trigger.
- Cross-run/cross-subject identity correlation — `docs/LAB.md`'s own
  tracked research item, reconfirmed as a prerequisite for
  `RelationshipResolver`'s highest-value use case (Section 1, Section 11),
  not resolved or scheduled by this investigation.
- Topology rendering or interpretation of any kind — out of scope here,
  exactly as it was out of scope for ARCH-014.
- Wiring `RelationshipResolver` into `DiscoveryEngine`, `Application`, or
  any report — Section 9 names the integration point; nothing here
  authorizes actually connecting it.
- Resolution of the Open Questions in Section 13 — named as genuinely
  unresolved, not merely undesigned.
