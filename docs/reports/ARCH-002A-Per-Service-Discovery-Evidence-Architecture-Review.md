# Status

Architecture Review Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: Yes

Recommended Next Sprint:
ARCH-002B – Per-Service Discovery Evidence ADR

---

# Executive Summary

This review evaluates three candidate representations for per-service
discovery evidence, as required by
[FEAT-003B](FEAT-003B-Discovery-Evidence-Model-Investigation.md)'s finding
that `Device`'s two parallel lists (`open_ports`, `detected_services`)
cannot correlate a specific port to the service, product, or version
observed on it.

**Recommendation: Option 2 — a correlated per-service record, represented
as a list of small, explicitly-typed dataclass entries on `Device`.**
Each entry names its fields directly (port, protocol, service name,
product, version); there is no generic metadata catch-all.

This is not a novel pattern for the codebase: `Project` already contains
`NetworkGraph` as a nested dataclass field
([project/models.py:23](../../networkmapper/project/models.py#L23)), and
`NetworkGraph` already contains a keyed collection of `Device` objects
([network_graph.py:13](../../networkmapper/core/network_graph.py#L13)).
Adding one more level of typed composition — `Device` containing a list of
small per-service records — extends an already-used compositional style
rather than introducing one. `ENGINEERING.md` itself names `Device`,
`Interface`, and `Link` together as the intended family of small data
models (`## 5. Models contain data`), even though only `Device` is
currently implemented — a documentation/implementation gap independent of
this review, but supporting evidence that the codebase's stated
architecture already anticipates more than one model shape, not just an
ever-growing flat `Device`.

Option 1 (retain parallel lists) is rejected: it is structurally unable to
express the evidence FEAT-003A recommended collecting. Option 3, evaluated
here as a generic per-port metadata dictionary — the shape implied by the
`metadata` field in this sprint's own example schema — is also rejected:
no such generic, untyped model exists anywhere in the current codebase,
and it works against the explainability and determinism properties the
classification subsystem depends on. No repository evidence justifies it.

No existing ADR is altered by this recommendation. A new ADR
(ARCH-002B) is still required to formally record it, per FEAT-003B.

---

# Scope

This review evaluates only the representation of per-service discovery
evidence on `Device` — the specific architectural question FEAT-003B
surfaced. It does not evaluate exporter changes, persistence-gap fixes
(the missing `open_ports`/`detected_services` serialization noted in
FEAT-003B), OS fingerprinting, or any other FEAT-003A opportunity. Those
remain out of scope, as they were in the two preceding reports.

---

# Option 1 — Retain the Parallel-List Model

```
Device
    open_ports: list[int]
    detected_services: list[str]
```

This is the current implementation
([core/models.py:42-43](../../networkmapper/core/models.py#L42-L43)),
populated by two independent extraction loops in `NmapProvider`
([nmap_provider.py:162-187](../../networkmapper/discovery/nmap_provider.py#L162-L187))
that build and sort each list separately — `open_ports` numerically,
`detected_services` alphabetically. No code anywhere in the repository
correlates a specific entry in one list to a specific entry in the other
(confirmed by repository-wide search for positional access or `zip()`
usage across both fields — none exists).

**Can it reasonably support richer discovery evidence?** No. Product,
version, HTTP title, and TLS certificate evidence are all *per-port*
facts. Adding them as additional parallel lists (e.g.
`service_versions: list[str]`) would not merely fail to solve the
correlation problem FEAT-003B identified — it would compound it, since a
device with product/version data on some but not all open ports has no
way to express which entry in a fourth list corresponds to which port at
all, let alone reconstruct the association from sort order.

| Criterion | Assessment |
|---|---|
| Simplicity | Simple today, but only because current consumers never need port-service correlation. |
| Extensibility | Poor — each new per-port attribute requires another uncorrelated list. |
| ADR-008 compatibility | Compatible as far as it goes (still an immutable discovery fact), but does not resolve the modeling gap ADR-008's "Future Work" explicitly deferred. |
| Classification implications | Rules remain limited to independent presence checks (`first_matching_port`, `first_matching_service`); cannot express "port X is running product Y." |
| Serialization implications | Neither field is currently even persisted by `ProjectSerializer` (FEAT-003B finding) — unaffected either way by this option. |
| Benchmark implications | `BenchmarkRunner.load_inventory()` already loads both as flat lists from JSON; no change needed to keep this option. |
| Export implications | Neither exporter reads either field today; unaffected. |
| Engineering complexity | None — this is the status quo. |
| Future discovery support | Poor — SNMP, LLDP/CDP, and any future per-interface or per-service evidence would repeat the same unsolved correlation problem. |
| Migration cost | Zero (no migration), which is also its only real advantage. |

**Verdict: Rejected.** Zero migration cost does not offset an inability to
represent the evidence this line of work exists to collect.

---

# Option 2 — Correlated Per-Service Record (Recommended)

```
Device
    services: list[ServiceEvidence]

ServiceEvidence (example only — exact fields are a FEAT-003C decision)
    port: int
    protocol: str        # "tcp" | "udp"
    service: str | None
    product: str | None
    version: str | None
```

**Canonical representation of a discovered network service (Question 1):**
one record per observed open port, naming the port, the protocol it was
reached on, and whatever service/product/version evidence Nmap returned
for that port — exactly the granularity needed to answer "what did
discovery actually find running here," which is the concrete gap Option 1
cannot close.

Including `protocol` is directly justified by repository evidence, not
invented: `_extract_open_ports()` and `_extract_detected_services()`
already iterate over `("tcp", "udp")` as a recognized dimension
([nmap_provider.py:166](../../networkmapper/discovery/nmap_provider.py#L166),
[nmap_provider.py:178](../../networkmapper/discovery/nmap_provider.py#L178))
and then discard which protocol a given result came from. FEAT-003A also
flagged an unverified but plausible defect where UDP-only services (SNMP
on port 161) may never be reached because `-sU` is absent from the
STANDARD enrichment arguments — recording protocol per record would make
that kind of defect visible in collected evidence going forward, instead
of silently unrecoverable as it is today.

| Criterion | Assessment |
|---|---|
| Simplicity | One new, small, explicitly-typed dataclass; each field self-explanatory. Not simpler than Option 1's two lists in isolation, but simpler than what Option 1 would require to express the same evidence correctly. |
| Extensibility | Good — a new per-service attribute is one new named field on `ServiceEvidence`, added the same way every `Device` field has always been added (see FEAT-003B's history of `operating_system`, `open_ports`, `detected_services`). |
| ADR-008 compatibility | Compatible without modification. The record remains part of the immutable discovery observation (ADR-008); `device_type` and all interpretation remain untouched and structurally separate. This only changes the internal shape of the *discovery* half of the model, which is exactly the category of future work ADR-008 named and deferred. |
| Classification implications | No change to `ClassificationRule`, `RuleResult`, `DeviceClassifier`, or first-match-wins ordering (ADR-002/003/004 all unaffected). Rules gain the option to use a new correlated-lookup helper alongside the existing `first_matching_port`/`first_matching_service` in `evidence_helpers.py` — additive, not a rewrite of the rule contract. |
| Serialization implications | `ProjectSerializer` would need to serialize/deserialize a list of small records instead of a list of ints/strings — mechanically straightforward (a list of dicts in JSON), and is the natural point to also close the pre-existing persistence gap FEAT-003B found (not part of this recommendation, but the same code path). |
| Benchmark implications | `BenchmarkRunner.load_inventory()` would build `ServiceEvidence` entries from JSON the same way it already builds `Device` from JSON today — same pattern, one more level of nesting. Existing benchmark datasets (all of which currently omit per-port version/product evidence entirely) continue to work unchanged if the field defaults to an empty list. |
| Export implications | None required. Exporters ignore `open_ports`/`detected_services` today and can continue to ignore `services` — this option does not obligate exporter changes (FEAT-003B, Question 5). |
| Engineering complexity | Moderate: one new dataclass, updated `NmapProvider` extraction logic, updated serializer/benchmark loader, and a decision (left to FEAT-003C) on whether `open_ports`/`detected_services` are removed, kept as derived convenience views, or deprecated gradually. |
| Future discovery support | Good — SNMP, LLDP/CDP, and other per-interface/per-service providers can populate the same structure (or a sibling record following the same pattern) without re-litigating the correlation question this review settles. |
| Migration cost | Real but bounded: all 8 classification rules currently call `first_matching_port`/`first_matching_service` against the flat lists. Whether those helpers are kept (backed by `services` internally) or rules are migrated to a correlated lookup is a FEAT-003C implementation decision, not an architectural one — this review does not resolve it, only confirms the underlying data shape it would operate on. |

**Verdict: Recommended.** It is the only option that can correctly
represent the evidence FEAT-003A identified, and it extends existing,
already-used patterns (`Project`/`NetworkGraph` composition; incremental
named-field growth on `Device`) rather than introducing new ones.

---

# Option 3 — Alternative Representations Considered

## 3a. Generic Per-Port Metadata Dictionary

```
Device
    services: list[dict]   # e.g. {"port": 443, "metadata": {...arbitrary...}}
```

This is the shape implied by the `metadata` field in this sprint's own
example schema. It is evaluated and rejected explicitly rather than
silently folded into Option 2, because it is a materially different
design choice: an open-ended, untyped bag versus explicitly named fields.

No precedent for this pattern exists anywhere in the current codebase — a
repository-wide search for any existing generic `metadata`-style
dictionary field on a model returned no results. Every model in the
project, including every field ever added to `Device`, is explicitly
named and typed. A generic metadata dictionary would be the first
instance of that pattern in the codebase, not an extension of one.

It also works against properties the classification subsystem is
explicitly built around. `docs/architecture/classification.md` describes
explainability as "a defining characteristic of the implemented
classification subsystem," achieved through `RuleResult.reason` strings
that describe *named* evidence. A rule reading from an untyped dict would
either need to know magic string keys in advance (no better than a named
field, but without type safety or discoverability) or iterate the dict
generically (undermining the deterministic, explainable evaluation model
ADR-002/003 establish). `ENGINEERING.md`'s coding standards also
explicitly prefer dataclasses and explicit names over generic containers.

**Is a generic metadata model justified (Question 4)? No.** Nothing in
the repository's evidence — not FEAT-003A's discovery findings, not the
existing model style, not the classification subsystem's design goals —
supports it. Explicitly named fields, extended the same way `Device` has
always been extended, are simpler, more explainable, and equally
extensible without sacrificing type clarity. This review recommends
Option 2 use named fields, not a metadata dictionary, for exactly this
reason.

## 3b. A Correlation Index Instead of a Record List

Briefly considered and rejected without extended analysis: keeping
`open_ports`/`detected_services` as-is and adding a separate
`dict[int, str]`-style index (e.g. `port_to_service: dict[int, str]`) to
correlate them. This does not meaningfully differ from Option 2 — it is
the same underlying idea (correlate port to evidence) implemented with a
less extensible, untyped container. It would need a second, third, and
fourth such dict for product, version, and protocol, recreating the exact
parallel-structure problem Option 1 has today, one level down. Not
evaluated further; it is dominated by Option 2 on every criterion.

## 3c. An Independent Service Entity

Briefly considered and rejected: modeling discovered services as a
first-class entity independent of `Device` (e.g., a separate
service-keyed collection alongside `NetworkGraph`, referenced by device
IP). No repository evidence supports this — `NetworkGraph` has exactly
one collection today, keyed by device IP
([network_graph.py:13](../../networkmapper/core/network_graph.py#L13)),
and nothing about per-service evidence requires it to be queryable or
addressable independently of the device it was observed on. This would
introduce a second top-level collection and a cross-referencing scheme
for no identified benefit — a clear case of the "unnecessary abstraction"
this review's constraints warn against. Per Question 2, service evidence
should remain owned by `Device`, not modeled as an independent entity.

---

# Required Questions — Answered

1. **What is the canonical representation of a discovered network
   service?** A record correlating the port it was found on, the
   protocol used to reach it, and whatever service/product/version
   evidence discovery obtained for that port — see Option 2.

2. **Should service evidence be modeled independently from device-level
   evidence?** Structurally distinct (its own small, named record type),
   but not independently owned — it remains a field on `Device`, owned
   and persisted as part of that device's discovery record, consistent
   with `NetworkGraph`'s existing single-collection-keyed-by-device
   design and with ADR-008 treating the device's discovery record as one
   immutable whole.

3. **Does this require changing `Device`, or merely changing one portion
   of `Device`?** One portion only. `ip_address`, `hostname`,
   `mac_address`, `vendor`, `operating_system`, `device_type`, and
   `discovery_sources` are unaffected. Only the two fields currently
   representing per-port evidence (`open_ports`, `detected_services`)
   are in scope for restructuring.

4. **Is a generic metadata model justified?** No — see Option 3a. Use
   explicitly named fields, extended incrementally, matching the
   project's existing model style.

5. **Does this alter any existing ADR?** No. ADR-001 (two-phase
   discovery) is unaffected — this changes what phase 2 writes into, not
   the phasing itself. ADR-008 (discovery is immutable, interpretation is
   adjustable) is unaffected in principle and is the ADR this
   recommendation extends into the specific area it deferred. ADR-002,
   ADR-003, and ADR-004 (RuleResult, first-match-wins, read-only evidence
   API) are unaffected — no change to the classification contract is
   required. A **new** ADR (ARCH-002B) records this as an additional,
   accepted decision; nothing existing is revised.

---

# Recommendation

**Adopt Option 2: a correlated per-service record, represented as a list
of explicitly-typed, named-field entries on `Device`, replacing the
current parallel `open_ports`/`detected_services` lists as the
representation for per-port discovery evidence.**

Competing approaches are rejected for concrete, evidence-based reasons,
not preference:

- **Option 1** (status quo) cannot represent the evidence this entire
  line of investigation (FEAT-003A → FEAT-003B → this review) exists to
  collect. Its only advantage, zero migration cost, does not offset that.
- **Option 3a** (generic metadata dictionary) has no precedent anywhere
  in the codebase and directly conflicts with the explainability and
  explicit-naming principles the classification subsystem is built on.
- **Option 3b** (correlation index) is a weaker, untyped variant of
  Option 2 that would recreate Option 1's flaw one level down.
- **Option 3c** (independent service entity) is an unjustified
  abstraction with no supporting need identified anywhere in this
  review or its predecessors.

This review's own Stop Condition — halt if multiple architectures remain
equally valid — was not triggered. Option 2 is not one of several
comparably-good choices; it is the only option able to satisfy the
concrete requirement (per-port evidence correlation) that motivated this
entire review, evaluated against the other candidates on every criterion
in scope.

Exact field names, whether `open_ports`/`detected_services` are removed
outright or retained as derived convenience views during a transition,
and how existing classification rules migrate are implementation
decisions reserved for FEAT-003C, consistent with this review's
constraint against schema drafting.

---

# Risks

- **Migration sequencing risk in FEAT-003C.** All 8 classification rules
  and their tests currently depend on the flat-list shape. FEAT-003C's
  own investigation phase should decide the transition approach (dual
  representation during migration vs. a single coordinated cutover); this
  review does not prescribe one.
- **Scope creep risk.** The persistence gap and the `operating_system`
  dormancy pattern identified in FEAT-003B are real and adjacent, but
  neither is resolved by this recommendation and neither should be
  silently folded into ARCH-002B or FEAT-003C without being named as its
  own decision.

---

# Conclusion

Three representations were evaluated against repository evidence: the
current parallel-list model, a correlated per-service record, and a
generic metadata dictionary implied by this sprint's own example schema.
Only the correlated record can express the per-port evidence FEAT-003A
recommended collecting, and it does so using patterns — dataclass
composition, incrementally named fields — already present elsewhere in
the codebase rather than new ones. This review recommends it as the
architectural principle to formalize in ARCH-002B, the ADR sprint FEAT-003B
already identified as necessary before FEAT-003C's implementation begins.
