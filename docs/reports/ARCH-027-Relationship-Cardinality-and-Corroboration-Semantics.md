# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: **Yes — an additive amendment to ADR-013, not a replacement** (Section 10). ADR-013's principles all still hold. What it lacks is a definition of conflict that depends on cardinality, a decision about which unit a canonical relationship is, and permission for the interpretation layer to hold category semantics. ADR-013 left all three open; this report settles them.

Recommended Next Sprint:
**ADR-013 Amendment 1: Relationship Cardinality** (documentation only). It must be accepted before any resolver change, because the change redefines what CONFLICTING means to every consumer. Offered as a recommendation, not a decision; engineering review selects the next sprint.

Source of truth: committed `HEAD` `fbbc820`. ARCH-026 (`docs/reports/ARCH-026-Gateway-Relationship-Evidence-Readiness.md`, uncommitted at time of writing) is used as context only.

---

## 1. Executive Summary

**Today's resolver treats every relationship category as single-valued.** `RelationshipResolver` groups observations by `(subject, category)` and marks a group CONFLICTING as soon as it holds more than one distinct `related_subject`. That rule is correct only when a subject can have at most one related subject in that category. **All three categories that are actually produced are naturally multi-valued** when reported from the infrastructure side:
- `arp_neighbor`: a gateway's ARP table lists many hosts.
- `bridge_fdb`: a switch's forwarding table lists many hosts.
- `connected_to`: a switch has many LLDP neighbors.

So the resolver labels the normal operation of every gateway and switch as a conflict. A scratch experiment against the real resolver confirms this (Section 2.4).

**This is a defect introduced in design, not one inherited from ADR-013.** ADR-013 never defines cardinality and explicitly defers "relationship resolver algorithms". The single-valued assumption came in through ARCH-018, which chose the `(subject, category)` key by direct analogy with identity's `(subject, property_name)`. ARCH-018's own motivating conflict example was per **local port**: "LLDP says port 3 connects to switch B; CDP says the same port connects to switch C". At port granularity that claim really is single-valued. The port component was then dropped because there is no Interface model (ARCH-018 §4), and the claim silently became per **device**, where many neighbors are normal. That is the root cause.

**There is a second, smaller false-conflict source.** `SnmpLldpNeighborProvider` emits one observation per management address of a *single* LLDP neighbor (`lldp_neighbor_provider.py:265-268`). A neighbor that advertises two management IPs is therefore already CONFLICTING today, even with no fan-out at all.

**Recommended model: cardinality is a property of the category, declared in a resolver-owned policy table, with one canonical record per edge.**
- **Cardinality** has two values: `SINGLE` (at most one related subject per subject, for example `default_gateway`) and `MULTIPLE` (many is normal, for example `arp_neighbor`, `bridge_fdb` and `connected_to`). The table lives in `networkmapper/relationships/`, not in providers. A category missing from the table defaults to `MULTIPLE`, so an unregistered category can never manufacture a conflict.
- **Corroboration.** Every edge `(subject, category, related_subject)` gets its own state: WEAK with one independent source, CONFIRMED with two or more. For `SINGLE` categories only, a subject with more than one distinct related subject makes **all** of that subject's edges in the category CONFLICTING. That is exactly today's behavior for single-valued claims.
- **Canonical output.** One `CanonicalRelationship` per edge, with `related_subject` as an explicit field. Evaluation still groups by `(subject, category)` so that conflicts in `SINGLE` categories can be detected. The **evaluation key** and the **output identity key** are deliberately separate, which resolves ARCH-018's objection to triple-keyed grouping without losing what it was protecting.
- **No many-to-many mode.** Every `MULTIPLE` category is already many-to-many across the whole graph (a host appears in many switches' forwarding tables), and per-edge records represent that natively.
- **What `MULTIPLE` categories give up.** They lose CONFLICTING altogether. The observation model holds only positive claims, so there is no evidence that could contradict an edge in a multi-valued category. Inventing one is out of scope (Section 5.3).

**Providers are unchanged.** They emit the same observations as before and never declare cardinality. ADR-013's rule that "providers never create canonical relationships" holds as written.

**Blast radius.** The change is contained to the interpretation and presentation layers:
- **Production code:** the resolver, the canonical relationship model and `__init__`, the presentation view-model, the Markdown exporter and the relationship CSV exporter (6 files).
- **Tests:** 6 test files. `CanonicalRelationship(` is constructed 22 times across 5 of them, and 3 resolver tests that today assert CONFLICTING for `connected_to` fan-out will invert.
- **Not affected:** the observation layer, all providers, `IdentityResolver`, the MAC index, `Application` wiring, serialization (canonical records are never persisted) and the `devtools` regression suite (no relationship module is in `STANDARD_REGRESSION_TESTS`).
- **Output schemas:** the relationship CSV's columns can stay the same, but its **values change**: fan-out rows that read `conflicting` today would read `weak` or `confirmed`.

**ADR decision.** ADR-013 needs an **additive amendment** (Amendment 1), not a replacement. All of its principles survive. The amendment settles three things ADR-013 left open or deferred: (1) conflict is defined relative to category cardinality, (2) the canonical relationship unit is the edge, which settles its deferred "Relationship identifiers" item, and (3) the interpretation layer may hold a minimal category-semantics table, which relaxes ADR-013's refusal to freeze any category taxonomy only as far as cardinality.

**Recommended next sprint:** draft and accept that amendment (docs only), then implement it in a FEAT sprint.

---

## 2. Current Resolver Semantics

Audited at `HEAD` `fbbc820`: `relationships/resolver.py`, `relationships/models.py`, `observations/models.py`, the three providers and `tests/test_relationship_resolver.py`.

### 2.1 Pipeline

1. **Filter:** keep only `RelationshipObservation`s (`resolver.py:90-92`).
2. **Endpoint gate** (`resolver.py:101-108`): keep an observation only if `subject` **and** `related_subject` are both canonical-identity subjects and are different from each other. Dropped observations still exist as observations (ADR-013 Relationship Endpoints); they just never reach a canonical record.
3. **Grouping key:** `(subject, category)` (`resolver.py:110-113`). `related_subject` is **not** part of the key; it is treated as the *value* under evaluation, the analog of identity's `value` (ARCH-018 §1/§4).
4. **Independent sources:** distinct `(provenance.provider, provenance.collection_method)` pairs within the group (`resolver.py:133-136`). Repeated observations from the same pair count once, whatever their `source_run` or `observed_at`. Cross-run repetition therefore never upgrades a state.
5. **State derivation** (`resolver.py:138-148`):

   | Condition (evaluated in this order) | State |
   |---|---|
   | More than one distinct `related_subject` in the group | `CONFLICTING` |
   | Two or more independent sources (all agreeing on one `related_subject`) | `CONFIRMED` |
   | Otherwise | `WEAK` |

   Conflict ignores source independence. A single source reporting two values is enough (test `test_a_single_source_reporting_two_values_conflicts_on_its_own`), and agreement from a second source does not soften it (`test_a_second_source_agreeing_with_one_value_does_not_soften_the_conflict`).
6. **Output:** one `CanonicalRelationship(subject, category, state, observations)` per group, sorted by `(subject, category)`. Its observations are sorted by `(provider, collection_method, related_subject)`. There is **no** `related_subject` field: consumers read the related subjects back out of `observations` (`models.py`, ARCH-025 §3).

### 2.2 Assumptions that are implicitly single-valued

- **The grouping key copies identity's.** An identity property (one hostname per device) is single-valued by nature. Relationships were given the same key with no record of whether each category is single-valued.
- **"More than one distinct related subject" is defined as a conflict.** That holds only for single-valued categories.
- **The output shape is one record per `(subject, category)`.** That presumes one answer per subject and category; ARCH-025 had to compensate by expanding CONFLICTING records into several rows in the CSV.
- **Tests encode it.** Three resolver tests (lines 108, 129 and 152) assert CONFLICTING for a subject with two `connected_to` neighbors. Two of them have a *single* LLDP source reporting two neighbors, which is exactly how a normal switch looks.

### 2.3 Categories wrongly treated as mutually exclusive

| Category | Produced by | Treated as | Should be |
|---|---|---|---|
| `arp_neighbor` | `SnmpArpNeighborProvider` | mutually exclusive | multi-valued |
| `bridge_fdb` | `SnmpBridgeFdbProvider` | mutually exclusive | multi-valued |
| `connected_to` | `SnmpLldpNeighborProvider` | mutually exclusive | multi-valued per device (single-valued only per local port, which cannot be represented) |

All three categories produced today are affected. No category produced today is genuinely single-valued.

### 2.4 Experimental confirmation

A scratch experiment fed synthetic observations with identity-resolved endpoints through the real `IdentityResolver` and `RelationshipResolver` at `HEAD`:

| Input | Current output |
|---|---|
| Gateway ARP table lists 3 hosts (one source) | 1 record, **CONFLICTING** |
| Switch forwarding table lists 2 hosts | 1 record, **CONFLICTING** |
| One LLDP neighbor advertising 2 management IPs | 1 record, **CONFLICTING** |
| Unregistered category with 2 related subjects | 1 record, **CONFLICTING** |
| `default_gateway`: route table and DHCP agree | 1 record, CONFIRMED (correct) |
| `default_gateway`: route table and DHCP disagree | 1 record, CONFLICTING (correct) |

---

## 3. Relationship Category Inventory

Categories produced in code (`HEAD`) or explicitly planned:

| | `arp_neighbor` | `bridge_fdb` | `connected_to` | `default_gateway` (planned, ARCH-026 §9) |
|---|---|---|---|---|
| Producer | `SnmpArpNeighborProvider` (`ipNetToPhysicalTable`) | `SnmpBridgeFdbProvider` (`dot1dTpFdbTable`) | `SnmpLldpNeighborProvider` (`lldpRemTable`, 3 resolution methods) | none yet (host-side route table or DHCP option 3) |
| Claim | Subject (an L3 device) has resolved the related subject's IP on one of its interfaces | The related subject's MAC is learned on one of the subject switch's ports | The subject receives LLDP from the related subject | The subject (a host) uses the related subject as its default gateway |
| Natural direction | Directional: L3 device → host (ARCH-020 §7) | Directional: switch → host (ARCH-024 §5) | Symmetric in reality; reported directionally (each end separately) | Directional: host → gateway |
| Cardinality, subject → related | **Many** | **Many** | **Many** per device (one per local port, but ports aren't modelled) | **One** |
| Multiple related subjects valid? | Yes, normal | Yes, normal | Yes, normal for any switch | No |
| Multiple related subjects mutually exclusive? | No | No | No (at device granularity) | **Yes** |
| Corroboration | The same edge from a second independent source, for example the same host in the switch's forwarding table **under its own category** (cross-category, see below) | The same edge from another independent source | The same edge from a second independent source, for example CDP in future, or the reverse direction once symmetric canonicalization exists (deferred, ARCH-018) | Two independent host-side sources agree, for example the route table and the DHCP lease |
| Contradiction | None expressible: no negative observations exist (Section 5.3) | None expressible | None expressible at device granularity. Per-port contradiction (ARCH-018's example) needs an Interface model | Independent sources (or one source) name different gateways |

**Named elsewhere but not produced or planned:** `hosts_service` and `routes_through` appear only as docstring examples (`observations/models.py`). ADR-013's broader categories (VLAN membership, Administrative, Virtualization, Geographic, Dependency) have no producer. The model below needs none of them. A future category only has to declare its cardinality (Section 4.3).

**Cross-category corroboration** (for example, `bridge_fdb` S→H supporting `connected_to` S→H) is not defined by ADR-013's independence rules, and this report does not introduce it. Each category is corroborated only within itself (Open Question 3).

---

## 4. Cardinality Model

### 4.1 Options evaluated

| Option | Description | Assessment |
|---|---|---|
| **A. Cardinality metadata on each observation or provider** | Providers declare cardinality, or carry it on `RelationshipObservation` | **Rejected.** Cardinality would become provider-owned truth, against ADR-013's "Providers never create canonical relationships": the provider would decide how the resolver interprets its claims. Two providers of the same category could also declare different cardinalities, which makes the outcome provider-dependent. It also changes an immutable, frozen observation type. |
| **B. A relationship-type enum carrying cardinality** | Replace the free-text `category: str` with an enum whose members carry semantics | **Rejected.** It freezes a closed taxonomy, against ADR-013's "does not freeze an implementation taxonomy" and the free-text design of `RelationshipObservation.category`. It forces an observation-model change and turns an unknown category into a construction error instead of a deterministic default. Heavier than needed. |
| **C. A resolver-owned policy table keyed by category** | `dict[str, RelationshipCardinality]` in `networkmapper/relationships/`, with a fixed default for unknown categories | **Recommended.** Observations stay immutable and free-text. Cardinality is interpretation, so it sits in the interpretation layer. There are no provider-specific branches (the resolver looks up a category, never a provider). A new category is a one-line table entry. |
| **D. Infer cardinality from the data** | For example, treat "a single source reporting many values" as multi-valued | **Rejected.** It is non-deterministic in the ADR-013 sense: the same category would be interpreted differently depending on which evidence happened to arrive. It cannot be explained by reference to a fixed rule, and a single-valued category with one buggy source would silently stop detecting conflicts. |

### 4.2 Recommended definition

```python
class RelationshipCardinality(StrEnum):
    SINGLE = "single"      # at most one related subject per (subject, category)
    MULTIPLE = "multiple"  # any number of related subjects per (subject, category)

CATEGORY_CARDINALITY: Mapping[str, RelationshipCardinality] = {
    "arp_neighbor": MULTIPLE,
    "bridge_fdb": MULTIPLE,
    "connected_to": MULTIPLE,
    # "default_gateway": SINGLE  -- registered by the sprint that introduces its provider
}
DEFAULT_CARDINALITY = RelationshipCardinality.MULTIPLE
```

**Naming.** The charter's "one-to-one" for `default_gateway` is, across the whole graph, many-to-one (many hosts share one gateway). The property the resolver needs is **per subject**: can this subject have more than one related subject in this category? `SINGLE` and `MULTIPLE` state exactly that and avoid suggesting a global constraint the resolver never checks.

**Default for unknown categories: `MULTIPLE`.** An unregistered category then produces only WEAK or CONFIRMED edges and never a conflict that wasn't asserted. The opposite default (`SINGLE`, today's behavior) is what produces the false conflicts this report is fixing. The cost is that a genuinely single-valued category that someone forgets to register would silently lose conflict detection. That is covered by a **registry-completeness test**: every `*_CATEGORY` constant a provider emits must appear in `CATEGORY_CARDINALITY` (Section 9).

**Many-to-many is not a separate mode.** Every `MULTIPLE` category is globally many-to-many (a host appears in several switches' forwarding tables and several L3 devices' ARP tables). Per-edge records represent that with no extra resolver logic, so a third enum value would add complexity with nothing to evaluate.

### 4.3 Extensibility

A new category needs exactly one decision, `SINGLE` or `MULTIPLE`, recorded in the table by the sprint that introduces its provider. Nothing else in the resolver changes. A future category with semantics outside these two (containment or a subnet endpoint, which ADR-013 §Relationship Evidence anticipates) would need its own design; neither has a producer today.

---

## 5. Corroboration Semantics

The **edge** is `(subject, category, related_subject)`. Its **independent sources** are the distinct `(provider, collection_method)` pairs among the observations that support exactly that edge. This is the same independence rule as today, now applied per edge.

### 5.1 `SINGLE` (example: host → `default_gateway`)

| Question | Answer |
|---|---|
| Two independent sources name the same related subject? | **CONFIRMED.** |
| Independent sources name different related subjects? | **CONFLICTING**, on every edge of that `(subject, category)`. |
| One source names two different related subjects? | **CONFLICTING.** A single-valued claim contradicted by its own source is still a contradiction, as today. |
| Repeated observations from the same `(provider, collection_method)`, including across runs? | They count once, so the edge stays **WEAK**. |
| One edge is confirmed by two sources while a competitor exists? | All edges are **CONFLICTING**. Conflict dominates, as today (`test_a_second_source_agreeing_with_one_value_does_not_soften_the_conflict`). |

These are exactly today's semantics. For `SINGLE`, the only change is the output shape (Section 6).

### 5.2 `MULTIPLE` (examples: gateway → `arp_neighbor`, switch → `bridge_fdb`, device → `connected_to`)

| Question | Answer |
|---|---|
| Is each related subject corroborated independently? | **Yes.** Each edge has its own state. |
| Can one subject and category have some WEAK and some CONFIRMED edges? | **Yes.** For example, a gateway's ARP edge to H1 confirmed by two sources while its edge to H2 is weak. |
| Do several related subjects affect each other's state? | **No.** Many related subjects is the normal condition, not evidence about any one of them. |
| Repeated observations from the same source? | They count once. |
| Single group, or one claim per related subject? | **One claim per related subject** (Section 6). |

### 5.3 What CONFLICTING means for `MULTIPLE`: nothing expressible today

A contradiction of a multi-valued edge would have to be **negative evidence**: "S authoritatively enumerated its full ARP table and H was absent". The retained observation model (ADR-011) holds positive claims only, and absence of an observation is not an observation. So for `MULTIPLE` categories:

- `CONFLICTING` is **never produced**;
- the state space is effectively `{WEAK, CONFIRMED}`;
- edges that go stale or disappear are a **lifecycle** concern (ADR-013 §Relationship Lifecycle: retirement, replacement), not a conflict. They stay deferred, needing persistence and cross-run evidence.

**Trade-off made explicit.** ARCH-018's per-port conflict ("port 3 → B according to LLDP, → C according to CDP") becomes undetectable under `MULTIPLE`. It was never detected *correctly* at device granularity, though: today it is indistinguishable from a switch with two neighbors. Detecting it properly needs an Interface or local-port model, which would make per-port `connected_to` a `SINGLE` claim. That remains future work (Open Question 1).

### 5.4 Prototype results (scratch, not production)

The proposed rules were prototyped against the real resolvers' inputs and checked for order-independence (200 random permutations × 8 cases, all identical):

| Case | Current | Proposed |
|---|---|---|
| Gateway ARP fan-out, 3 hosts | 1 × CONFLICTING | 3 edges, each WEAK |
| ARP fan-out; one host also seen in a second run (same method) | 1 × CONFLICTING | 2 edges, each WEAK (a second run isn't an independent source) |
| Switch forwarding table, 2 hosts, plus one LLDP edge | `bridge_fdb` CONFLICTING, `connected_to` WEAK | 3 edges, each WEAK |
| One LLDP neighbor with 2 management IPs | 1 × CONFLICTING | 2 edges, each WEAK (see Open Question 2) |
| `default_gateway`, two sources agree | CONFIRMED | 1 edge, CONFIRMED |
| `default_gateway`, two sources disagree | CONFLICTING | 2 edges, each CONFLICTING |
| `default_gateway`, same source repeated | WEAK | 1 edge, WEAK |
| Unregistered category, 2 related subjects | CONFLICTING | 2 edges, each WEAK (default `MULTIPLE`) |

---

## 6. Canonical Output Shape Analysis

### 6.1 Options

**Option 1: one record per `(subject, category)`, with per-related-subject states.**
`CanonicalRelationship(subject, category, cardinality, related: tuple[RelatedSubjectCorroboration(related_subject, state, observations)])`

**Option 2: one record per edge.**
`CanonicalRelationship(subject, category, related_subject, cardinality, state, observations)`. Here `observations` holds only that edge's supporting observations. For a `SINGLE` category, the competing edges are sibling records sharing `(subject, category)`, each with `state=CONFLICTING`.

**Option 3: two shapes**, a group record for `SINGLE` and edge records for `MULTIPLE`. **Rejected:** two canonical types for one concept double every consumer's branching, which is the kind of provider- or category-specific branching the charter asks to avoid.

### 6.2 Comparison

| Consequence | Option 1 (group + per-related state) | Option 2 (edge) |
|---|---|---|
| **ADR-013** | The group-level `state` has no meaning for `MULTIPLE` (there's nothing to roll up; ARCH-025/FEAT-009A already rejected rollups across independent claims). It would need to be removed or made optional. | Matches ADR-013's wording directly: "canonical relationships exist between canonical identities" describes an edge with two endpoints. Settles the deferred "Relationship identifiers" item as `(subject, category, related_subject)`. |
| **Explainability of `SINGLE` conflicts** | The competing values sit inside one record. | The competing values are sibling records. "Why CONFLICTING?" is answered by the set of records sharing `(subject, category)`, which output ordering keeps adjacent. ADR-013 explainability is met at the record-set level, the same way the relationship CSV already expands conflicts today. |
| **`CanonicalPresentation`** | Small change: `RelatedSubjectPresentation` gains a `state`. | Moderate: `_present_relationship` regroups edges by `(subject, category)` to keep today's grouped layout. Each `RelatedSubjectPresentation` gains a `state` taken from its edge. The group `state` is removed or limited to `SINGLE`. |
| **Markdown exporter** | Renders a state per related subject. | The same, after presentation regrouping. |
| **Relationship CSV exporter** | Rows already come one per related subject; the state column moves to per row. | **Simplest:** one row is exactly one canonical record. The per-row provenance workaround (`_provenance_cell` docstring: "never the complete evidence behind the group's state") becomes unnecessary. |
| **Determinism** | Sort by `(subject, category)`, then `related_subject`. | Sort by `(subject, category, related_subject)`. Both are trivially deterministic. |
| **Future topology consumer** | Has to flatten groups into edges. | **Native:** an edge list with state and cardinality. |
| **Persistence and serialization** | None today. Canonical records aren't persisted (`project/serializer.py` contains no canonical fields). | None today. If persistence comes later, an edge with a stable natural key is the easier thing to diff across runs (ADR-013 Lifecycle). |
| **Existing tests** | All `CanonicalRelationship(` constructions change (new required field). | All `CanonicalRelationship(` constructions change (new required field `related_subject`). The blast radius is roughly the same either way. |

### 6.3 Recommendation: Option 2 (one record per edge)

```python
@dataclass(frozen=True)
class CanonicalRelationship:
    subject: str
    category: str
    related_subject: str
    cardinality: RelationshipCardinality
    state: RelationshipCorroborationState   # CONFLICTING only possible when cardinality is SINGLE
    observations: tuple[RelationshipObservation, ...]  # only this edge's supporting observations
```

**Two keys, deliberately separate.** This answers ARCH-018's objection to triple-keyed grouping. ARCH-018 was right that **evaluating** conflict by the triple makes conflict undetectable. The proposed resolver still **evaluates** `SINGLE` conflict per `(subject, category)` group. Only the **output identity** is the triple. ARCH-018 merged these two keys; separating them is the core of the fix.

`cardinality` is carried on every record so consumers never have to consult the policy table to tell "WEAK in a multi-valued category" from "WEAK in a single-valued category". Records stay self-describing, and the presentation layer keeps its "read state, never recompute" contract (ARCH-025).

---

## 7. Provider Contract

**Do providers need to declare cardinality? No.** Providers emit `RelationshipObservation(subject, related_subject, category, provenance)`, unchanged. Cardinality belongs to the category's interpretation, which the resolver owns (Section 4.1, Option A rejected).

**Does ADR-013's "providers never directly own canonical relationship truth" still hold? Yes, unchanged, and more strictly than before.** Today a provider's choice of *what to emit* effectively decides the canonical state: an LLDP row with two management addresses produces CONFLICTING. Under the proposal, the canonical state comes from category policy plus independent evidence only.

**Recommended (optional) hygiene.** Move the three `*_CATEGORY` constants into a shared module, for example `networkmapper/relationships/categories.py`, beside the policy table. Providers would import them from there, so emitted names and registered names cannot drift apart. Provider behavior and output are unchanged. The registry-completeness test (Section 9) protects the same invariant if the constants stay where they are.

**Unchanged:** the observation types, `EnrichmentProvider`, the providers' emission logic, the MAC index's ambiguity gating, `DiscoveryEngine` and `Application` wiring, and the `RelationshipResolver.resolve(observations, identities)` signature.

---

## 8. Topology Readiness

| Category | False conflicts under the proposal? | Canonical edge(s) topology would consume | Ambiguity that remains | Evidence still missing |
|---|---|---|---|---|
| **`default_gateway`** | None. `SINGLE`: CONFLICTING only on a real disagreement. | Host → gateway, one per host, with state | Several valid gateways (HA virtual IP against the physical peers; ECMP or several default routes) would show as CONFLICTING. That is technically honest, but the HA case needs a modelling decision (Open Question 4). | Everything: no provider exists, and host-side collection is needed (ARCH-026). |
| **`arp_neighbor`** | None. `MULTIPLE`: per-edge WEAK or CONFIRMED. | L3 device → each resolved host | It proves layer-3 adjacency, **not** gateway use (ARCH-026 §5). Several L3 devices legitimately have edges to the same host. | Production SNMP data (ARCH-026: 0 observations). |
| **`bridge_fdb`** | None. | Switch → each host learned on any port | Without port granularity, "learned on an uplink" (transit) and "learned on an access port" (direct) look the same, so these edges over-state adjacency. Hosts appear on every switch in the path. | Port and Interface model; production SNMP data. |
| **`connected_to` (LLDP)** | None at device level. | Device → each LLDP neighbor, one edge per direction (two independent WEAK edges for a bidirectional link: symmetric canonicalization is still deferred, ARCH-018/ARCH-025) | Neighbors with several management addresses produce one edge per address, which can be the same device under two subjects (Open Question 2). Per-port conflicts can't be detected (Section 5.3). | Symmetric canonicalization; cross-subject identity correlation (LAB.md); port model; production SNMP data. |

**Bottom line.** The proposal removes the **semantic** blocker: no category would produce false conflicts. It does not supply **evidence**. ARCH-026's findings stand: 0 production relationship observations, and gateway identity needs host-side evidence. Topology also still needs a port model before `bridge_fdb` and `connected_to` can tell direct adjacency from transit.

---

## 9. Migration and Compatibility Impact

Files the eventual FEAT sprint is likely to touch (counts at `HEAD`):

| File | Change | Size |
|---|---|---|
| `networkmapper/relationships/models.py` | Add `RelationshipCardinality`; add `related_subject` and `cardinality` to `CanonicalRelationship`; update docstrings (the "no separate field holding the resolved related_subject" rationale is reversed) | Medium |
| `networkmapper/relationships/categories.py` (new) | `CATEGORY_CARDINALITY`, `DEFAULT_CARDINALITY`, and optionally the shared category constants | Small |
| `networkmapper/relationships/resolver.py` | Policy lookup; evaluate per `(subject, category)` group; emit per edge; sort by the triple | Medium (1 construction site) |
| `networkmapper/relationships/__init__.py` | Export the new names | Trivial |
| `networkmapper/reporting/canonical_presentation.py` | Regroup edges by `(subject, category)`; add a per-related-subject `state`; group-level `state` removed or limited to `SINGLE`; `cardinality` exposed | Medium (2 construction sites) |
| `networkmapper/exporters/markdown_exporter.py` | Per-related-subject state line; group state shown only for `SINGLE` | Small |
| `networkmapper/exporters/relationship_csv_exporter.py` | One row per record; provenance cell covers the full edge evidence | Small |
| Providers (3), optional | Import category constants from `relationships/categories.py` | Trivial, no behavior change |
| `tests/test_relationship_resolver.py` (18 tests) | 3 conflict tests change category to a `SINGLE` one, or invert to per-edge WEAK; the grouping and sorting tests (lines 277 and 290) move to edge keys; new tests for the cardinality table, the default, mixed WEAK/CONFIRMED within one subject, and the registry-completeness invariant | Large |
| `tests/test_canonical_presentation.py` (6 constructions) | Update constructions; assert per-related state | Medium |
| `tests/test_relationship_csv_exporter.py` (11 constructions) | Update constructions; conflict-expansion tests become single-valued-only | Medium |
| `tests/test_markdown_exporter.py` (3 constructions) | Update constructions and expected text | Small |
| `tests/test_project.py`, `tests/test_project_serializer.py` (1 construction each) | Update constructions | Trivial |
| `tests/test_identity_pipeline.py` | Re-check the end-to-end assertion against the new shape | Trivial |
| **New end-to-end test** | A multi-entry ARP, FDB or LLDP table sent provider → resolver, asserting no CONFLICTING. This closes ARCH-026 §8.4's coverage gap. | Small |
| `docs/ADR.md` | ADR-013 Amendment 1 (Section 10) | Docs |

**Unaffected (verified):** `observations/` (both types), all three providers' emission logic, `identity/` (including `mac_index.py`, which only references `CanonicalRelationship` in a docstring), `project/serializer.py` (canonical records never persisted), `project/models.py` (it holds a tuple; the type change is transparent), `comparison/project_comparator.py` (no relationship handling), `application.py` (resolver signature unchanged), and `devtools/validate.py` (no relationship test module is in `STANDARD_REGRESSION_TESTS`, so the test-count check does not move). No file under `docs/architecture/` mentions canonical relationships or `RelationshipResolver`, so none needs changing.

**Output schemas:**
- **Relationship CSV:** the column set can stay the same (`Subject, Subject Hostname, Category, Related Subject, Related Subject Hostname, Corroboration State, Provenance`). **Values change:** rows in multi-valued categories that read `conflicting` today would read `weak` or `confirmed`. Whether to add a `Cardinality` column is Open Question 5.
- **Markdown report:** the `# Canonical Relationships` section gains a state per related subject.
- **In practice nothing visible changes yet.** No production run has emitted relationship observations (ARCH-026), so no customer-facing report shows relationships today.

---

## 10. ADR-013 Assessment

**Is ADR-013 correct as written? Yes; nothing in it is wrong.** Its principles hold unchanged under the proposal: evidence-driven, deterministic, order-independent, explainable, providers never owning truth, endpoints as canonical identities, conflicts retained and never arbitrated, and topology as a consumer. The single-valued defect came from ARCH-018 and FEAT-009A's algorithm, which ADR-013 deliberately left to them ("Relationship resolver algorithms" is listed under Future Work).

**Does it need an amendment? Yes.** The fix makes three **policy** decisions ADR-013 either deferred or explicitly declined, and implementation sprints shouldn't make those silently:

1. **Conflict is relative to cardinality.** ADR-013 §Corroboration says conflicting observations "must be retained and surfaced" but never says what makes observations conflict. The amendment defines it: a conflict exists only where the category is single-valued and different related subjects are claimed. For multi-valued categories, several related subjects are not a conflict, and no conflict state is derivable from positive-only observations.
2. **The canonical relationship unit is the edge.** This settles ADR-013's deferred "Relationship identifiers and how they are assigned" as `(subject, category, related_subject)`, and separates the evaluation key from the identity key.
3. **The interpretation layer may hold minimal category semantics.** ADR-013 §Relationship Categories "does not freeze an implementation taxonomy". A cardinality table is a narrow exception to that: it attaches exactly one property (cardinality) to categories that already exist, adds no taxonomy, and has a deterministic default for categories it doesn't list.

**Amendment, not replacement.** Context, Decision, every principle, the Alternatives and the Consequences all remain valid. The change adds a section and moves one Future Work item ("Relationship identifiers") into decided scope. Following the repository's pattern of never silently rewriting accepted ADRs, the recommendation is:

- keep ADR-013's existing text unchanged;
- change its status to **"Accepted (amended by Amendment 1, ARCH-027)"**;
- append an **"Amendment 1 — Relationship Cardinality"** subsection after Future Work, with the date and source (ARCH-027), covering items 1–3 above plus the default-`MULTIPLE` rule;
- in the amendment, strike only "Relationship identifiers" from Future Work, by reference rather than by editing the original list.

---

## 11. Recommended Architecture

1. **Cardinality** is a property of the relationship **category**: `SINGLE` or `MULTIPLE`. It is declared in a resolver-owned policy table in `networkmapper/relationships/`, never by providers or observations. Unregistered categories default to `MULTIPLE`, and a test enforces that every emitted category is registered.
2. **Evaluation:** the endpoint gate is unchanged. Observations are then grouped by `(subject, category)`, and edges are formed by `related_subject`. Independence is distinct `(provider, collection_method)` per edge, as today.
3. **States:**
   - every edge is WEAK with one independent source, CONFIRMED with two or more;
   - `SINGLE` only: if the group holds more than one distinct related subject, **every** edge in the group is CONFLICTING;
   - `MULTIPLE` never produces CONFLICTING.
4. **Output:** one `CanonicalRelationship` per edge, carrying `related_subject`, `cardinality`, `state` and only that edge's observations, sorted by `(subject, category, related_subject)`.
5. **Providers, observations, identity resolution, wiring and persistence are unchanged.**
6. **Presentation** regroups edges for display and never recomputes states (ARCH-025 contract kept).
7. **Out of scope:** symmetric canonicalization, port or Interface modelling, cross-category corroboration, negative evidence and lifecycle, cross-run independence, and a many-to-many mode.

---

## 12. Recommended Next Sprint

**ADR-013 Amendment 1: Relationship Cardinality** (documentation only).

Dependency order:
1. **Amendment first.** The FEAT sprint changes what CONFLICTING means to every consumer and settles an item ADR-013 deferred. Implementing that before the policy is accepted would be exactly the "silently rewrite history" pattern to avoid.
2. **Then FEAT-RELATIONSHIP-CARDINALITY**, which implements Section 11, with the new end-to-end fan-out tests in the same sprint. Splitting the end-to-end tests into a separate earlier sprint would mean writing tests that assert today's known-wrong CONFLICTING behavior, only to invert them.
3. **OPS-001** (the SNMP production capture ARCH-026 recommends) **does not depend on this track**: it collects observations, which are unaffected. It can run whenever production access allows. It does not block the amendment, because the cardinality assignments come from protocol semantics, not from measured data.

---

## 13. Open Questions

1. **Per-port `connected_to`.** Once an Interface or local-port model exists, should per-port adjacency become a separate `SINGLE` category, restoring ARCH-018's port-3 conflict detection?
2. **One LLDP neighbor, several management addresses.** These produce several edges that may be one device under two subjects. Should the provider emit one observation per neighbor row (choosing an address deterministically), or is this a job for cross-subject identity correlation (LAB.md)? This is a provider-level question, independent of the cardinality model.
3. **Cross-category corroboration.** Should a `bridge_fdb` edge S→H count toward a `connected_to` edge S→H? ADR-013's independence rules don't cover it.
4. **Valid plural gateways.** HA virtual gateway IPs, ECMP and several default routes would make a `SINGLE` `default_gateway` show CONFLICTING. Is that the intended honest outcome, or does the `default_gateway` provider need to emit only the active or virtual gateway? This should be decided when that provider is designed.
5. **Should the relationship CSV gain a `Cardinality` column?** Without one, a reader can't tell from the CSV alone why `conflicting` is impossible in some categories.
6. **Independence within one SNMP walk.** LLDP's three `collection_method` labels all come from one `lldpRemTable` walk. Under per-edge corroboration, two LLDP rows for the same neighbor (for example two LAG member links) resolved by different methods would count as two independent sources and give CONFIRMED from a single walk. That conflicts with ADR-013 §Relationship Independence ("two fields surfaced from one SNMP walk must not automatically count as two independent confirmations"). The issue exists today but becomes easier to hit once fan-out stops masking it as CONFLICTING. The fix belongs to ADR-013's deferred independence taxonomy, possibly an independence key based on provider and walk.
7. **Cross-run repetition.** Same-method observations from different runs never upgrade a state (Section 2.1). Once observation persistence exists (ARCH-017), should repetition across runs count toward corroboration, or only toward lifecycle (staleness)?

---

## 14. git status

At the time of writing (no files staged; nothing committed or pushed by this sprint):

```
 M review.diff                                                         (pre-existing, unrelated)
?? diff.md                                                             (pre-existing, unrelated)
?? docs/reports/ARCH-026-Gateway-Relationship-Evidence-Readiness.md   (previous sprint, uncommitted)
?? docs/reports/ARCH-027-Relationship-Cardinality-and-Corroboration-Semantics.md   (this report)
```

No production code or test file was modified. The scratch prototype used for Section 5.4 lives only in the session scratchpad, outside the repository.
