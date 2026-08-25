# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No — every decision in this investigation applies an
already-accepted ADR-010/011/012/013 principle to a new case rather than
establishing a new one. Section 12 checks this explicitly, including
against the two questions this investigation came closest to treating as
policy decisions (a new `EnrichmentProvider` input method; whether
provider ordering should become a guaranteed dependency), and confirms
neither crosses into ADR territory.

**Revised after adversarial review**, in two rounds, before being
finalized here — recorded because both rounds changed real conclusions,
not just wording:

- **Round 1** corrected four issues: (1) a genuine architectural bug — the
  originally-proposed design would have let ARP evidence manufacture
  canonical identities for hosts NetworkMapper never independently
  discovered, letting the same evidence resolve its own relationship
  endpoint (Section 4); (2) an underspecified return type that silently
  collapsed "no evidence" and "conflicting evidence" into the same
  representation (Section 5); (3) a vague, scope-inviting API name and an
  unaddressed mutability gap (Section 8); (4) a design that would have
  forced an untranslatable LLDP chassis-ID subtype into a field contract
  it cannot validly occupy (Section 6).
- **Round 2** corrected the investigation's own title and terminology —
  the mechanism designed here never produces or consumes a
  `CanonicalIdentity`, and the original working title ("MAC-to-Canonical-
  Identity Resolution") claimed otherwise — and formalized enrichment-
  provider ordering as explicitly non-guaranteed, rejecting a dependency-
  graph mechanism that this investigation found no correctness reason to
  build (Section 7).

Recommended Next Sprint:
FEAT-011A (per ARCH-021's own sequencing) remains the natural next
implementation sprint, now scoped by this investigation's concrete
design: the MAC-to-subject reverse index, the `receive_observations()`
enrichment-provider hook, and the gated `SnmpArpNeighborProvider`
extension (Section 9). Offered as a recommendation, not a decision — per
scope, engineering review selects the next sprint.

---

## 1. Executive Summary

ARCH-021 found three of its five relationship-evidence candidates — LLDP,
CDP, Bridge/MAC forwarding tables — blocked on one shared, missing
mechanism: nothing in this codebase can answer "which discovered device
has MAC address X." This investigation designs that mechanism, and the
design that survives adversarial review is smaller and more carefully
bounded than the charter's own working title implied.

**It is not identity resolution.** The mechanism runs during
`DiscoveryEngine.discover()`, before `IdentityResolver.resolve()` has
produced anything — a hard sequencing fact, not a design preference — and
returns discovery-time `subject` references (today, IP addresses), never
`CanonicalIdentity` objects. Calling it "MAC-to-Canonical-Identity
Resolution," this investigation's own original working title, overclaims
in exactly the way this codebase has otherwise been careful not to. It is
renamed here to what it actually is: a **MAC-to-Subject Reverse Index** —
a small, pure, stateless lookup structure over already-retained
`IdentityObservation`s, architecturally adjacent to but categorically
distinct from `IdentityResolver`.

**The design's most important property is what it refuses to do.** A
first-pass design — `SnmpArpNeighborProvider` emitting a `mac_address`
`IdentityObservation` for every ARP-table row, unconditionally — was
found, on adversarial review, to let ARP evidence manufacture a canonical
identity for a host NetworkMapper never independently discovered, which
would then let that same ARP evidence resolve its own relationship
endpoint: a direct violation of the reason ADR-012 makes identity
resolution a prerequisite for relationship resolution in the first place
(an endpoint's identity must be established independently of the
relationship claiming it). The corrected design (Section 4) gates that
emission on the row's IP already belonging to the independently-discovered
device set — drawing the line at *existence* (established by a
`DiscoveryProvider`), not at *prior identity-property evidence*, which
would have been unnecessarily conservative.

**The design adds one new optional method, no dependency graph, and
touches no resolver.** `IdentityResolver` and `RelationshipResolver` are
confirmed unmodified throughout. The one new piece of shared orchestration
— an optional `EnrichmentProvider.receive_observations()` hook, mirroring
`collect_observations()`'s own established shape — was itself corrected
twice: renamed away from a vague "context" framing that invited scope
creep, and specified to pass an immutable snapshot rather than a live,
mutable reference, structurally (not just conventionally) preserving
read-only evidence ownership. Provider registration order is explicitly
**not** promoted to a guaranteed dependency mechanism — this investigation
found no correctness reason requiring one, and the burden of proof for
adding one was not met.

No production code is proposed for change by this report.

---

## 2. Direct Answers

**1. What should this mechanism be called, and why does it matter?**
A MAC-to-Subject Reverse Index, not "MAC-to-Canonical-Identity
Resolution" — it runs before canonical identities exist and never
produces or consumes one. Section 3.

**2. How do MAC addresses enter the system today, and why is there no
lookup?** Exactly one path — `NmapProvider`'s local-subnet ARP-based host
discovery — plus a second, currently-discarded path already latent in
`SnmpArpNeighborProvider`'s own ARP-table walk. No lookup exists because
`IdentityResolver` groups strictly by `subject`, never indexing by
`value`. Section 3.

**3. Should ARP-table MAC↔IP evidence become retained identity evidence,
stay provider-local, or be discarded?** Become retained
`IdentityObservation` evidence — but only when the row's IP already
belongs to the independently-discovered device set, the correction that
prevents endpoint self-bootstrapping. Section 4.

**4. What should the index return for an ambiguous MAC?** Not a plain
`dict[str, str]` — `dict[str, frozenset[str]]`, so "no evidence,"
"exactly one subject," and "conflicting subjects" remain three distinct,
never-collapsed states, per ADR-011/012/013's own repeated
never-silently-arbitrate principle. Section 5.

**5. Can an untranslatable LLDP chassis-ID subtype go into
`RelationshipObservation.related_subject`?** No — forcing it there would
misrepresent a permanent representational gap as a temporary,
"not yet discovered" one, contradicting ARCH-018's own already-stated
position on endpoint-namespace translation. A future LLDP provider must
simply not emit a `RelationshipObservation` for such an entry. Section 6.

**6. How should a provider receive observations it needs mid-`enrich()`?**
A new, optional, no-op-by-default `EnrichmentProvider.receive_observations(observations: tuple[...])`
method, called by `DiscoveryEngine` with a fresh, immutable snapshot
immediately before each provider's `enrich()` — not a generic "context"
parameter, and not a live, mutable reference. Section 8.

**7. Should provider registration order become a guaranteed dependency
mechanism?** No. Correctness does not require it — absence of prior
evidence reduces coverage, never correctness, the same tolerance-for-
absence principle ADR-010 already established for the output side. No
dependency graph or priority metadata is introduced. Section 7.

**8. Does anything here require a new ADR?** No — confirmed explicitly,
including against the two closest candidates. Section 12.

---

## 3. Current State, and Why "Resolution" Is the Wrong Word

**Where `mac_address` `IdentityObservation`s are emitted today.** Exactly
one place: `NmapProvider._build_device()` (`nmap_provider.py:412-427`),
via `_extract_mac_address()` (`nmap_provider.py:510-513`, reading nmap's
own ARP-based host-discovery output) and `_emit_identity_observation()`
(`nmap_provider.py:157-187`), which only appends an observation when a
value was actually found. No other provider emits this today — confirmed
directly: `SnmpEnrichmentProvider._IDENTITY_FIELD_TO_PROPERTY`
(`snmp_provider.py:54-56`) maps only `sysName → hostname`;
`SnmpArpNeighborProvider.collect_observations()` emits only
`RelationshipObservation`s (`arp_neighbor_provider.py:139-142`).

**A real coverage limit.** nmap's MAC capture only resolves a target on
the *same local subnet* as the scanning host — ARP does not cross
routers. For any other target, no `mac_address` observation exists at
all. This bounds how much a MAC-keyed index built from nmap's own source
alone could ever answer.

**A second, currently-discarded source already sits in the code.**
`SnmpArpNeighborProvider`'s own ARP-table walk resolves
`(interface_index, ip_address, mac_address, entry_type)` per row
(`SnmpArpTableEntry`, `snmp_client.py`) for every entry in a queried
gateway's ARP cache — network-wide, not limited to the scanner's own
subnet. `_collect_relationship_observations()`
(`arp_neighbor_provider.py:154-171`) reads only `entry.ip_address`;
`entry.mac_address` is computed and discarded. Section 4 evaluates
whether that should change.

**Where observations are stored.** No distinct storage — `mac_address`
observations flow through the identical pipeline every observation does,
into `Project.observations` (`application.py:135-144`, post-FEAT-009B),
indistinguishable in kind from any other `IdentityObservation`.

**Why no lookup exists.** `IdentityResolver.resolve()`
(`identity/resolver.py:49-71`) groups strictly by `observation.subject`
(line 62-64) — an IP address today. A `mac_address` observation's
`subject` is the IP of the device the MAC belongs to; its `value` is the
MAC itself. Nothing anywhere treats `value` as a key to look anything up
by — not `IdentityResolver`, not `CanonicalIdentity`
(`identity/models.py`), not `Project`. This is the confirmed gap ARCH-018
Section 12 named for Bridge MIB and ARCH-021 found applies identically to
LLDP/CDP.

**Naming, resolved.** The mechanism this investigation designs to close
that gap operates entirely on this raw, pre-canonical layer — it must
(Section 7's sequencing constraint), and it returns `subject` values, the
exact term `IdentityObservation` already uses for "a raw, discovery-time
reference... not a resolved canonical identity"
(`observations/models.py`'s own docstring language). Naming it
"resolution" would borrow a word this codebase reserves for the
corroboration-producing concept ADR-012/013 define (`IdentityResolver`,
`RelationshipResolver` — both literally titled "Canonical ... Resolution"
in their governing ADRs); naming it "canonical identity" would claim a
concept it never touches. This report and the mechanism it designs are
named **MAC-to-Subject Reverse Index** throughout, correcting this
investigation's own original working title.

---

## 4. Disposition of ARP-Table MAC↔IP Evidence

Three options, genuinely evaluated, not assumed.

**Should it become retained `IdentityObservation` evidence?** The
evidentiary case is strong: nmap's own MAC capture is not the target
self-reporting — it's the scanning host observing the target's MAC via
ARP resolution, structurally the identical kind of evidence a router's
`ipNetToPhysicalTable` entry is, just from a different vantage point.
Treating them as the same kind of evidence, from two independent sources,
means `IdentityResolver._resolve_property()`'s existing independent-
source corroboration (`identity/resolver.py:96-121`) already handles
"nmap says MAC A, SNMP ARP-table says MAC B for the same subject" with
zero new code — the identical mechanism already correctly used for
`hostname` from SMB vs. RDP (`nmap_provider.py:356-367`). The two
rejected alternatives — keeping it provider-local input to the index only
(never a retained observation), or leaving it discarded — were both
evaluated and found weaker: provider-local input would require the index
to accept two different kinds of input (the general observation stream,
plus a bespoke per-provider side-channel) for a narrower result than
simply treating it as one more `IdentityObservation`; discarding
already-validated evidence that fits ADR-011's retention model
contradicts that model for no offsetting benefit.

**The bug this investigation's first draft contained, and the fix.**
Emitting this observation *unconditionally* — for every ARP row,
regardless of whether the row's IP was ever independently discovered —
was found, on review, to be a genuine architectural defect, not a minor
gap. Traced concretely: a gateway G's ARP cache commonly contains IPs
`DiscoveryEngine` never discovered at all (outside the scanned range,
non-responsive to nmap's own sweep, stale cache entries). Today, such an
H correctly never resolves to a `CanonicalIdentity` — nothing emits an
`IdentityObservation` with `subject=H` unless H was independently
discovered — so `RelationshipResolver` correctly leaves the `arp_neighbor`
observation for G→H unresolved, ADR-013's unresolved-endpoint semantics
working exactly as designed. Emitting `mac_address` unconditionally would
break this: `IdentityResolver.resolve()` groups by `subject` with no
check that `subject` corresponds to an actually-discovered `Device`
(`identity/resolver.py:62-64`), so it would produce a `CanonicalIdentity`
for H from nothing but the ARP entry — and then `RelationshipResolver`
would resolve the G→H relationship using an identity that same evidence
manufactured, with zero independent corroboration that H is real,
reachable, or still at that address. This directly defeats the reason
ADR-012 makes identity resolution a prerequisite for relationship
resolution: an endpoint's identity must be established independently of
the relationship claiming it, not by it.

**The corrected design.** `SnmpArpNeighborProvider.enrich(devices)`
computes `{device.ip_address for device in devices}` once per call and
gates the new `mac_address` emission on `entry.ip_address` being in that
set. The existing `RelationshipObservation` emission stays
**unconditional**, exactly as it is today — ADR-013's unresolved-endpoint
handling already correctly covers the case where it isn't, and was never
the broken part. The principled line this draws is *existence*
(independently confirmed by a `DiscoveryProvider` — the target itself
responded to a probe) versus *prior identity-property evidence* (which
would be unnecessarily conservative: a host in `devices` with zero prior
`IdentityObservation`s can validly receive its first `mac_address`
observation from ARP, because its existence, independent of this
evidence, is already established).

---

## 5. The Reverse Index Itself

**Shape.** `build_mac_index(observations: Sequence[IdentityObservation | RelationshipObservation]) -> dict[str, frozenset[str]]`
— every observed MAC mapped to the complete set of distinct `subject`
values that claimed it, filtered to `property_name == "mac_address"`.

**Ambiguous MAC semantics — corrected from an underspecified first
draft.** A plain `dict[str, str]` cannot distinguish "this MAC was never
observed" from "this MAC was observed but for conflicting subjects" — an
absent key would mean both, silently collapsing a genuine, meaningful
conflict into ordinary absence. That's a real violation of ADR-011/012/013's
repeated principle — conflicting evidence must be retained and surfaced,
never silently arbitrated — introduced by omission rather than by a
deliberate tradeoff, which is worse. The `frozenset[str]` return value
fixes this by construction: key absent → no evidence; `len == 1` →
resolved; `len > 1` → conflicting, explicitly visible to the caller. This
mirrors `CanonicalRelationship`'s own already-established pattern exactly
— "a consumer reads the value(s) from the retained observations, never
from a field that would have to silently pick one during a conflict"
(`relationships/models.py`'s own docstring) — applied to a reverse index
instead of a forward one. What a caller *does* with a conflicting set
(this investigation recommends: skip the row, mirroring exactly how
`_parse_ipv4_arp_row` already skips a row it can't confidently parse,
`snmp_client.py`) is the caller's decision, not baked into the index.

**Placement.** A new, small, stateless module,
`networkmapper/identity/mac_index.py`, alongside `identity/resolver.py`
and `identity/models.py` — this resolves the same subject-identity
concept `IdentityResolver` already establishes, not a relationships-layer
concern, even though its primary consumers will be relationship-evidence
providers. This follows the same precedent `RelationshipResolver` itself
set: cross-cutting derived data is computed by one small, pure component
and passed as an explicit input, never re-derived ad hoc by each
consumer.

---

## 6. Chassis-ID Subtype Gating and the `RelationshipObservation` Boundary

**LLDP.** `lldpRemChassisIdSubtype` (LLDP-MIB) has several IEEE-defined
values; only `macAddress`(4) is directly usable by the reverse index.
`networkAddress`(5) is already IP-shaped and should resolve the same
direct way ARP does, bypassing the index entirely. The remaining
subtypes — `chassisComponent`, `interfaceAlias`, `portComponent`,
`interfaceName`, `local` — are locally-significant strings with no
cross-device meaning this or any future mechanism can resolve.

**Can an untranslatable identifier validly occupy `related_subject`
anyway, just to retain the evidence?** No — this investigation's first
draft got this wrong and is corrected here. `RelationshipObservation`'s
own docstring names "an LLDP neighbor not yet independently discovered"
as the canonical *legitimate* unresolved-endpoint case, but that example
assumes the value *is* correctly IP-shaped and simply hasn't been
corroborated yet. ARCH-018 Section 11 already, separately, names the
failure mode of a *wrongly-namespaced* endpoint value as a defect
("Endpoint-namespace translation is an easy defect to introduce
silently... simply never resolve to a canonical relationship — a silent,
hard-to-diagnose gap"), not a valid way to retain evidence. A
`portComponent`/`interfaceAlias`/`local`-subtype chassis ID is not "not
yet discovered" — it is categorically the wrong kind of reference, and no
future discovery ever resolves it. Forcing it into `related_subject`
anyway would make a permanent representational impossibility
indistinguishable from a temporary, legitimately-pending one, exactly the
silent misrepresentation ARCH-018 already warned against.

**What a future LLDP provider should do instead.** State the limitation,
don't work around it: for chassis-ID subtypes other than `macAddress` and
`networkAddress`, do not emit a `RelationshipObservation` for that
neighbor entry at all. This is a genuine, permanent ceiling of the
current model — `RelationshipObservation` can only represent
relationships between identity-namespace-shaped endpoints, and several
LLDP subtypes fall outside that by definition — the same class of
accepted, disclosed ceiling ARCH-014/018 already named for local-port
granularity ("no `Interface`/port model"). Whether some future, broader
observation model could ever capture a locally-scoped, non-subject-shaped
fact is a real question this investigation does not resolve — named as
open future work (Section 14), not solved here, and not an ADR trigger on
its own, since no new representation is being proposed, only a correct
refusal to misuse the existing one.

**CDP `cdpCacheAddress` — kept explicitly provisional, strengthened, not
softened.** CISCO-CDP-MIB's `cdpCacheAddress` column is documented to
carry the neighbor's own network-layer address directly in common Cisco
implementations, which would let much CDP evidence resolve the same
direct way ARP does, without the index at all. This is based on
documented MIB semantics, **not verified against any live Cisco device by
this or any prior investigation in this lineage** — the same
disclosed-uncertainty posture FEAT-010A already used for its own OID
parsing. If `cdpCacheAddress` proves unreliable or frequently empty in
real deployments, CDP falls back to needing the identical chassis-ID-style
translation and subtype-gating LLDP needs. Provider-level, live-network
verification is required before this is treated as settled.

---

## 7. Lifecycle and Ordering Semantics

**Lifecycle.** The index is a pure function over whatever observations
exist at the moment it's called — no state, no persistence, no `Project`
field. Confirmed by tracing its full scope: built and consumed entirely
inside `DiscoveryEngine.discover()`, never referenced by `Application.run()`,
never part of `Project(...)`'s construction (`application.py:135-144`) —
a narrower lifetime than `canonical_identities`/`canonical_relationships`
(FEAT-009B), which do need a `Project` field since they outlive
`discover()`. The index needs none. It must be **rebuilt fresh
immediately before each consuming provider's call**, not cached and
reused across providers — `self.observations` grows monotonically within
one `discover()` call as each provider's `collect_observations()` is
appended, so a stale, once-built index would miss evidence an
earlier-running provider just contributed.

**Should provider registration order become a guaranteed dependency
mechanism?** No — evaluated directly, not assumed. If a future LLDP
provider runs before `SnmpArpNeighborProvider`, or ARP enrichment isn't
enabled at all, the index simply has fewer entries at that point; LLDP
skips that neighbor entry — no `RelationshipObservation` is emitted, the
same non-emission outcome as an untranslatable chassis-ID subtype
(Section 6) — reduced coverage, never an incorrect result, never a
crash. This is the identical
tolerance-for-absence principle ADR-010 already established for the
*output* side ("optional by construction... simply absent... when its
prerequisites are not supplied"), extended unmodified to the *input*
side. Since correctness does not depend on ordering, a dependency graph
or provider-priority metadata is not justified — new mechanism bears the
burden of proof, and nothing in this investigation found a correctness
gap only such a mechanism could close.

**The rule, to be stated in `EnrichmentProvider.receive_observations()`'s
own docstring** (prose contract, not runtime-enforced machinery — the
same way `enrich()`'s "never raise for an expected per-device failure"
contract is communicated today, not mechanically enforced):

1. Each provider receives an immutable snapshot of all evidence available
   at the moment it runs.
2. Providers may opportunistically use earlier evidence.
3. No provider may require another optional provider to have run first
   for correctness.
4. Absence of prior evidence reduces resolution coverage, never
   correctness.

**Documented consequence for future LLDP, explicitly.** Remote-MAC
resolution may improve when ARP-derived MAC observations are already
available in the same run — but an LLDP provider must not assume ARP
enrichment is enabled, and must skip that neighbor entry — emitting no
`RelationshipObservation` — whenever the index has no entry, the same
non-emission outcome Section 6 already establishes for untranslatable
subtypes, regardless of what else happens to be configured.

---

## 8. Enrichment-Provider Input Hook

**Naming, corrected.** The first-draft name, `receive_context()`, is
rejected here, not merely renamed for style. "Context" is a grab-bag name
that invites exactly the scope creep a precise interface should prevent —
today it would carry observations; a vague name makes it easy to later
fold in scan profile, run metadata, or anything else "contextual,"
eroding the same discipline `collect_observations()`'s precise naming
already established. The corrected name,
`receive_observations(observations: tuple[IdentityObservation | RelationshipObservation, ...]) -> None`,
is scoped to exactly the one concrete need identified, symmetric with
`collect_observations()`, and typed for exactly what it carries.

**Mutability, addressed — a gap in the first draft, not just a detail.**
`DiscoveryEngine` must pass an immutable snapshot — `tuple(self.observations)`,
freshly built immediately before each provider's `enrich()` — never the
live, mutable list. `IdentityResolver`/`RelationshipResolver` both
structurally guarantee "never mutates its inputs," but that guarantee
currently rests on being small, centrally-reviewed components.
`EnrichmentProvider` is a broader, less centrally-controlled extension
point — future, potentially third-party providers — so the same guarantee
should be enforced by the type itself (a `tuple` has no mutating methods)
rather than by convention alone. This directly preserves read-only
evidence ownership structurally, not just by documentation.

**Optional, default no-op** — identical shape to `collect_observations()`'s
own existing default (`enrichment_provider.py:31-38`). Neither existing
provider (`SnmpEnrichmentProvider`, `SnmpArpNeighborProvider`) needs to
override it unless a future need arises.

---

## 9. Architectural Impact

- **New:** `networkmapper/identity/mac_index.py` — `build_mac_index()`,
  per Section 5.
- **Modified (new optional method, additive):** `EnrichmentProvider`
  (`enrichment_provider.py`) gains `receive_observations()`, default
  no-op, per Section 8.
- **Modified:** `DiscoveryEngine.discover()` — calls
  `receive_observations(tuple(self.observations))` on each enrichment
  provider immediately before `enrich()`. An ordering addition to
  existing orchestration, the same class of change ARCH-017 already
  precedented ("an ordering change to shared orchestration code, not a
  behavior change for the existing case"). **No dependency-graph or
  priority mechanism is added** (Section 7).
- **Modified:** `SnmpArpNeighborProvider` — emits `mac_address`
  `IdentityObservation`s alongside its existing `RelationshipObservation`s,
  gated on the row's IP already belonging to the discovered device set
  (Section 4). Its docstring's "never touches any `Device` field" claim
  stays true (this is observation emission, not a `Device` write) but
  should stop implying it emits no identity evidence at all.
- **Confirmed unchanged:** `IdentityResolver`, `RelationshipResolver`,
  `Project`, `NmapProvider`, `SnmpEnrichmentProvider`, every exporter,
  `ProjectSerializer`.

---

## 10. Testing Strategy

**The index** (`build_mac_index()`): unambiguous single MAC→subject;
a MAC corroborated by two independent sources for the same subject
(still resolves, `frozenset` of size 1); a MAC claimed by two different
subjects (`frozenset` of size 2+, never arbitrarily collapsed); empty
input; a subject with no MAC observation (simply absent). Pure-function,
no live network needed.

**`SnmpArpNeighborProvider`'s new emission:** a row whose IP is in the
discovered device set produces both the existing `RelationshipObservation`
and the new `IdentityObservation`; a row whose IP is *not* in the device
set produces only the `RelationshipObservation`, confirming the
endpoint-bootstrapping fix (Section 4) holds — this is the single most
important new test this investigation's own review process identified.

**`receive_observations()` orchestration:** a fake provider recording
what it received and when, mirroring `test_identity_pipeline.py`'s
existing fake-provider pattern; a test confirming a provider still
produces correct (if reduced-coverage) output when run *before* a
MAC-emitting provider or when no MAC-emitting provider is present at all
— directly exercising Section 7's ordering-tolerance rule, not just
documenting it in prose.

**Live-network verification remaining:** whatever a future LLDP/CDP/
Bridge-MIB provider actually walks against a real MIB table — the
already-disclosed class of risk FEAT-010A named for its own OID parsing.
The reverse index itself needs none.

---

## 11. Future Consumers

LLDP, Bridge/MAC forwarding tables, and CDP chassis IDs that fall back to
the MAC subtype (ARCH-021's three candidates), now with a concrete,
correctness-checked mechanism to consume. **Explicitly not solved by this
mechanism:** VMware relationship evidence's own translation problem
(ARCH-018 Section 5) — a VM's vCenter-reported identity versus its
independently-discovered IP identity — is a different, harder case this
index does not address.

---

## 12. ADR-Trigger Check

Re-checked after both review rounds, not merely restated. Six decisions
in total across this investigation:

1. Retaining gated ARP-table MAC evidence (Section 4) — applies ADR-011's
   already-general "providers may emit observations additively" policy
   (ARCH-017 Section 5) to a new provider; no new policy.
2. The `frozenset` conflict representation (Section 5) — applies
   ADR-011/012/013's existing never-silently-arbitrate principle to a new
   data structure; no new policy.
3. Declining to force untranslatable chassis IDs into
   `RelationshipObservation` (Section 6) — a correct refusal to misuse an
   existing representation, not a new one being proposed.
4. `receive_observations()`'s existence and immutability (Section 8) —
   re-checked directly against ADR-010's full Decision text
   (`ADR.md:536-566`): the ADR characterizes `EnrichmentProvider` by its
   effect on `Device` (fallback-only merge, never introduces/removes a
   device, never raises); nothing in its Decision, Rationale, or
   Consequences concerns what a provider may *read*. A new, optional,
   read-only, no-op-by-default input channel doesn't touch the
   "prevent silent merge conflicts" concern the ADR exists to solve — the
   exact symmetric case ARCH-017 already resolved at ARCH-level for the
   output side, under identical reasoning.
5. Rejecting a dependency-graph/priority mechanism (Section 7) — removes
   proposed mechanism rather than adding it; if adding it wouldn't
   require an ADR, declining to add it certainly doesn't either.
6. The report's own renamed terminology (Section 3) — not an
   architectural decision at all.

**No new ADR is triggered by this investigation.**

---

## 13. Recommended Sequence

Unchanged in substance from ARCH-021's own recommendation, now concretely
scoped: **FEAT-011A** — implement `build_mac_index()`,
`EnrichmentProvider.receive_observations()`, `DiscoveryEngine`'s new
orchestration call, and `SnmpArpNeighborProvider`'s gated `mac_address`
emission, per Sections 4/5/7/8/9 — then **FEAT-011B** (LLDP provider,
ARCH-021's Rank 1), consuming this mechanism directly, subject to Section
6's subtype-gating limitation. Not authorized here; offered as a
recommendation for engineering review.

---

## 14. Future Work

Explicitly deferred:

- The `mac_index.py` implementation itself, and the four other code
  changes in Section 9 — designed here, not written.
- Whether some future, broader observation model could represent a
  locally-scoped, non-subject-shaped fact (Section 6's named gap for
  non-`macAddress`/`networkAddress` LLDP chassis-ID subtypes) — a real
  open question, not resolved or scoped further here.
- Live-network verification of CDP's `cdpCacheAddress` encoding (Section
  6) — required before CDP's acquisition-complexity ranking (ARCH-021)
  can be revised with confidence.
- The LLDP/CDP/Bridge-MIB providers themselves (Section 13) — a separate,
  future implementation sprint.
- VMware relationship evidence's own translation problem (Section 11) —
  explicitly out of this investigation's scope.
