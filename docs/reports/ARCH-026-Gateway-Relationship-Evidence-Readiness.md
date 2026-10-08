# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: Not by this report itself. Section 9 identifies a question that **would** need ADR-013 to be amended or extended if pursued: how the relationship resolver should treat categories that legitimately carry many related subjects. This report frames that question but does not decide it.

Recommended Next Sprint:
OPS-001: SNMP-enabled production evidence capture. This is a data-collection sprint, not a provider sprint. It means re-running the production scan with `--snmp --snmp-arp --snmp-lldp --snmp-bridge-fdb` and keeping the relationship observations, so that a replay like the one in Section 6 has real relationship evidence to work with. The evidence does **not** justify building a new topology provider yet (Section 10). This is offered as a recommendation, not a decision; engineering review selects the next sprint.

---

## 0. Why This Is ARCH-026 and Not ARCH-020

This sprint was chartered as "ARCH-020 Investigation: ARP-Corroborated Gateway Relationship Provider". ARCH-020 already exists. It was completed on 2026-08-24 (`49ce5ce`), and a full lineage was built on it:

| Sprint | Outcome |
|---|---|
| FEAT-010A | `SnmpArpNeighborProvider`, emitting the `arp_neighbor` category |
| ARCH-020 | ARP provider architecture: SNMP `ipNetToPhysicalTable`, directional, not the scanner's local ARP cache |
| ARCH-021 | Comparison of relationship evidence sources: MAC-to-subject resolution is the shared blocker |
| ARCH-022 / FEAT-011A | MAC-to-subject reverse index (`identity/mac_index.py`) |
| ARCH-023 / FEAT-012A | `SnmpLldpNeighborProvider`, emitting the `connected_to` category |
| ARCH-024 / FEAT-012B | `SnmpBridgeFdbProvider`, emitting the `bridge_fdb` category |
| ARCH-025 to FEAT-027 | Canonical identity and relationship presentation, plus the relationship CSV export |

The engineer chose to keep this sprint's deliverables but re-scope it as a **readiness assessment**: does the evidence NetworkMapper actually collects in production support deterministic gateway relationships today? That question is new. Every earlier sprint in this lineage was designed and tested against synthetic SNMP fixtures, and none was replayed against the 244-device production dataset. This report builds on ARCH-020 to ARCH-025 and does not re-litigate their decisions.

---

## 1. Executive Summary

**The production dataset supports zero deterministic gateway relationships.** None of the discovery fields NetworkMapper currently collects can establish that host H uses device G as its gateway. This is not a near miss. The fields that could carry such evidence either do not exist in the schema (there is no route, gateway, netmask or interface field anywhere) or were never populated: every SNMP field is empty on all 244 devices, and `nmap` is the only discovery source recorded on any device. All three existing relationship providers depend on SNMP table walks, so all three emit nothing for this dataset. Replaying the stored evidence through the real `IdentityResolver` and `RelationshipResolver` gives **244 canonical identities and 0 canonical relationships** (Section 6).

**Heuristics do not close the gap; they show how ambiguous it is.** The collected fields contain only indirect gateway hints, and those hints point in conflicting directions (Section 8):
- **Six competing candidates.** Six devices are currently classified as routers or firewalls (two SonicWalls, three EdgeOS routers and one pfSense box), and all six sit in 172.16.100.x.
- **No L3 device in the other ranges.** None of these devices is in 172.16.101.x or 172.16.102.x.
- **The ".1" convention fails everywhere.** 172.16.100.1 is a Cisco switch, 172.16.101.1 is an Intel-vendor host, and 172.16.102.1 was not discovered.
- **The DNS-service hint is spread across five devices.** Three of the six candidates run DNS, and so do two Windows DNS servers.

Picking a gateway from these signals would be a guess presented as a fact.

**The address layout is probably not three routed subnets.** Nmap reports a MAC address only for hosts on the scanner's own layer-2 segment. 243 of the 244 devices have a unique MAC address, spread across all three /24 ranges. The one device without a MAC is 172.16.102.52 (`SCTLT108`), which is most likely the scanner itself. The data is therefore most consistent with one flat layer-2 segment, probably a /22, rather than three routed /24s. If so, there are no inter-subnet gateway hops to discover within the scanned range; the gateway question becomes "which of six L3 devices is the default gateway for this segment". This is an inference: the run did not record its scan targets, and that is itself an evidence gap (Section 8.3).

**Even with SNMP evidence, the current resolver would label every real gateway as a conflict.** This is the report's main architectural finding, and it was confirmed by running the real resolver (Section 8.4). `RelationshipResolver` keeps one canonical record per `(subject, category)` and marks the group CONFLICTING whenever it holds more than one distinct `related_subject`. ARCH-025 §3 recorded this mechanically. Its consequence for topology has not been drawn before: a gateway's ARP table, a switch's forwarding table and a switch's LLDP neighbor table all *normally* list many related subjects. So under today's resolver, every useful gateway or switch comes out as one CONFLICTING record. The evidence would be retained, but the corroboration state would be wrong: it reports disagreement where there is only ordinary fan-out. This blocks gateway topology independently of evidence collection.

**ARP evidence is necessary but not sufficient for a gateway claim.** `arp_neighbor` (ARCH-020 §7) proves that the queried device has resolved a host on one of its interfaces. In a segment with six L3 devices, including two running dnsmasq for DNS, several devices will legitimately hold ARP entries for the same host. A *deterministic* gateway relationship needs host-side evidence: the host's own default route, or DHCP option 3. ARCH-021 assessed that as the cleanest evidence shape but the most expensive to acquire (WMI or SSH).

**Recommendation.** Do not build a new topology provider yet. In order:
1. Capture real SNMP relationship evidence from production (OPS-001).
2. Resolve the multi-valued category semantics in the resolver (an ADR-013 question, Section 9).
3. Only then decide whether a host-side `default_gateway` provider is worth its acquisition cost.

Section 9 specifies the provider interface that evidence would need, so that a later sprint can start from it.

---

## 2. Direct Answers

1. **Which currently collected discovery fields can establish deterministic gateway relationships?** None. Section 4 audits every field.
2. **Which collected fields carry any gateway-relevant signal at all?** Four, all indirect: `device_type` (derived, not discovered), `vendor`, port-53 `ServiceEvidence`, and `mac_address` (as a signal of layer-2 adjacency to the scanner). None identifies *which* device is a given host's gateway.
3. **How many edges does the production dataset produce today?** Zero relationship observations and zero canonical relationships, across all three providers. Section 6.
4. **How many edges would an SNMP-enabled run produce?** At most 6 canonical `arp_neighbor` records (one per responding L3 candidate), each CONFLICTING whenever its ARP table holds more than one entry. That is effectively always the case for a real gateway. Section 7.
5. **Is the main ambiguity in the data or in the model?** Both, independently. The data offers six candidate gateways with no discriminating evidence. The model labels ordinary gateway fan-out as a conflict.
6. **Should the first topology provider be built now?** No. Section 10.
7. **What interface should a gateway provider eventually implement?** The existing `EnrichmentProvider` contract with no changes. It should emit `RelationshipObservation`s with the **host** as `subject` and the gateway as `related_subject`, under a new `default_gateway` category. That shape is single-valued by nature, so CONFLICTING would then mean a real disagreement. Section 9.

---

## 3. What Already Exists (Verified Against Current Code)

- **Providers.** `SnmpArpNeighborProvider` (`arp_neighbor`), `SnmpLldpNeighborProvider` (`connected_to`) and `SnmpBridgeFdbProvider` (`bridge_fdb`) live in `networkmapper/discovery/`. Each is an `EnrichmentProvider` and each is opt-in: `Application.run()` adds it only when `--snmp-arp`, `--snmp-lldp` or `--snmp-bridge-fdb` is passed (`application.py:120-133`).
- **SNMP client.** `SnmpClient` can retrieve the system group, the ARP table, LLDP neighbors and the bridge forwarding table (`snmp_client.py:385/448/506/695`). The table-walk gap ARCH-020 §5 identified has been closed.
- **Resolvers.** Both resolvers are wired into the runtime (FEAT-009B). `RelationshipResolver.resolve(observations, identities)` keeps only observations where both endpoints are canonical identity subjects and are not the same subject. It groups by `(subject, category)`, and judges independence by distinct `(provider, collection_method)` pairs (`relationships/resolver.py:79-175`).
- **Persistence.** Observations and canonical records are kept for one run only and are **not persisted**. The `.nmproj` file contains only `customer_name`, `created_date`, `modified_date` and `devices`.
- **Presentation.** The Markdown report and the relationship CSV (FEAT-025 to FEAT-027) render canonical relationships when they exist. The production run (2026-09-04) predates FEAT-025 and FEAT-027 and contains no relationship output.

---

## 4. Discovery Field Audit

Every field NetworkMapper collects, audited for gateway-relationship value. The population figures come from `output/Test Network.nmproj` (244 devices, STANDARD profile, scanned 2026-09-04).

### 4.1 `Device` fields

| Field | Populated | Source | Gateway-relationship value |
|---|---:|---|---|
| `ip_address` | 244 | nmap | **Indirect.** It places a host in an address range but says nothing about routing. The /24 grouping is an assumption, not evidence (Section 8.3). |
| `mac_address` | 243 | nmap (ARP during host discovery) | **Indirect, about the scanner only.** A MAC can only be learned for a host on the scanner's layer-2 segment, so this is evidence about the scanner-to-host relationship, not host-to-gateway. ARCH-020 §4 rejected the scanner's ARP view as relationship evidence, and that still holds. |
| `hostname` | 91 | nmap reverse DNS | None. |
| `vendor` | 243 | nmap MAC OUI lookup | **Indirect.** It drives classification as router or firewall, which yields gateway *candidates*, not gateway *relationships*. |
| `operating_system` | 66 | SMB / RDP | None. |
| `computer_name`, `domain` | 65 / 66 | SMB / RDP | None. |
| `smb_signing` | 18 | SMB | None. |
| `snmp_sys_descr`, `snmp_sys_object_id`, `snmp_sys_uptime`, `snmp_sys_contact`, `snmp_sys_location` | **0** | SNMP system group | None directly, even when populated: the system group holds no route or adjacency data. Their absence confirms SNMP was not collected. |
| `services` | 491 records | nmap `-sV` + NSE | **Indirect.** Port 53 marks DNS servers, not gateways. No routing-protocol ports (BGP 179, RIP 520, HSRP 1985, OSPF, quagga 2601-2605, winbox 8291) were observed on any device. |
| `device_type` | 244 | classification (derived) | **Indirect, derived.** It is an interpretation, not discovery evidence, so using it as relationship evidence would turn a heuristic into a fact. |
| `discovery_sources` | 244 (`nmap` only) | runtime | None. It confirms that no SNMP provider ran. |

### 4.2 `ServiceEvidence` fields

| Field | Populated | Gateway-relationship value |
|---|---:|---|
| `port`, `protocol`, `service` | 491 | Indirect only (see `services` above) |
| `product`, `version` | 280 / 125 | None. Product strings identify a device (for example dnsmasq or Unbound), not the device's relationships. |
| `http_title`, `http_auth_realm`, `tls_subject`, `tls_issuer` | 234 / 4 / 146 / 144 | None |

### 4.3 Retained observations

| Observation | Emitted by | Gateway-relationship value |
|---|---|---|
| `IdentityObservation` (`mac_address`, `hostname`, `computer_name`, `domain`) | `NmapProvider` | None. These are identity, not relationships, but they let endpoints qualify (all 244 hosts resolve to canonical identities, Section 6). |
| `IdentityObservation` (`hostname` from `sysName`) | `SnmpEnrichmentProvider` | None. It was not emitted in production. |
| `RelationshipObservation` (`arp_neighbor`, `connected_to`, `bridge_fdb`) | The three SNMP providers | The only relationship evidence in the codebase. **Not emitted in production**, and not persisted when it is emitted. |

### 4.4 Fields that do not exist anywhere in the schema

There is no default gateway, route table, netmask or prefix length, interface or VLAN, DHCP lease (option 3), or traceroute hop field. Nmap is not run with `--traceroute`: the STANDARD and DEEP argument strings in `nmap_provider.py:441-475` omit it. **Every deterministic gateway evidence source would be new collection.**

---

## 5. Relationship Evidence Matrix

Each candidate source is rated on whether it establishes **H uses G as its gateway**, deterministically, as distinct from weaker adjacency claims.

| Evidence source | Status today | Claim it actually proves | Deterministic gateway? | Endpoint shape | Production yield (this dataset) | Blocker |
|---|---|---|---|---|---|---|
| Host default route (host route table, WMI/SSH) | Not collected | H's configured gateway is G | **Yes** | Host → G, single-valued | 0 | New execution boundary (ARCH-021: highest acquisition cost) |
| DHCP lease option 3 (host or DHCP server) | Not collected | G was *assigned* to H as its gateway | **Yes** for DHCP hosts (static hosts not covered) | Host → G, single-valued | 0 | New collection path (WMI on the host, or DHCP server access) |
| SNMP `ipRouteTable` / `ipCidrRouteTable` on an L3 device | Not collected | G's own next hops and connected networks | Yes for G's **own** upstream; tells nothing about which hosts use G | G → next hop or subnet (ADR-013 non-device endpoint) | 0 | New SNMP walk, plus non-device endpoints (ARCH-021 §6) |
| SNMP ARP table (`ipNetToPhysicalTable`) on an L3 device | **Implemented** (FEAT-010A) | G has an interface on H's segment and has resolved H | **No.** Necessary, not sufficient: every L3 device on the segment can hold entries for H | G → many hosts (fan-out) | 0 (SNMP not run) | Not collected in production; fan-out labelled CONFLICTING (Section 8.4) |
| SNMP LLDP (`lldpRemTable`) | **Implemented** (FEAT-012A) | Direct layer-2 link between two LLDP speakers | No. Physical adjacency, not routing | Switch → many neighbors | 0 (SNMP not run) | Same as above |
| SNMP bridge forwarding table (`dot1dTpFdbTable`) | **Implemented** (FEAT-012B) | H's MAC is reachable through a port of switch S | No. Layer-2 reachability, not routing | Switch → many hosts | 0 (SNMP not run) | Same as above |
| Nmap `--traceroute` | Not collected | Layer-3 hops from the scanner to H | Only for the **scanner's** path, and empty within a flat segment | Scanner → hop chain | 0 | Scanner-centric (the same objection ARCH-020 §4 raised to the local ARP cache) |
| Scanner's local ARP cache / nmap MAC | Collected (as `mac_address`) | The scanner and H share a layer-2 segment | No | Scanner → H | 243 hosts, scanner-centric | Rejected by ARCH-020 §4 |
| Classification + IP heuristics (router or firewall type, ".1", DNS) | Derivable today | Nothing. These are guesses. | **No** | n/a | 6 candidates, no discrimination (Section 8) | Non-deterministic by construction |

**Reading the matrix.** Only host-side sources (default route, DHCP option 3) establish a gateway relationship deterministically, and neither is collected. Every source NetworkMapper *has* implemented proves adjacency or reachability, not "is the gateway of". Each of them is useful topology evidence, but none of them is a gateway claim on its own.

---

## 6. Production Replay

### 6.1 Method

1. Load the 244 stored devices from `output/Test Network.nmproj`.
2. Rebuild the `IdentityObservation`s that `NmapProvider` emits (`mac_address`, `hostname`, `computer_name`, `domain`) from the stored fields. This gives 465 observations.
3. Add the `RelationshipObservation`s the stored evidence can support. There are none: all three relationship providers need SNMP table data, and none was collected or persisted.
4. Run the real `IdentityResolver().resolve()` and `RelationshipResolver().resolve()` from current `HEAD`.

### 6.2 Result

| Measure | Count |
|---|---:|
| Identity observations (rebuilt) | 465 |
| Canonical identities | **244** |
| `arp_neighbor` observations | 0 |
| `connected_to` observations | 0 |
| `bridge_fdb` observations | 0 |
| Canonical relationships | **0** |

**Interpretation.** Endpoint eligibility is not the blocker. Every discovered host resolves to a canonical identity, so any relationship observation between two discovered hosts would pass the resolver's endpoint gate. Evidence is the blocker: the run collected none.

### 6.3 Limits of this replay

- The replay cannot reconstruct what an SNMP-enabled run *would* have collected. SNMP reachability, the configured communities and the ARP cache contents are all unknown. Section 7 therefore gives bounds, not predictions.
- Because observations are not persisted, **no** saved project can be replayed for relationships. Measuring relationship yield requires a live run that keeps its observations (Section 10).

---

## 7. Expected Edge Counts

| Scenario | Relationship observations | Canonical relationships | States |
|---|---:|---:|---|
| **S0: current dataset, current code** (measured) | 0 | 0 | none |
| **S1: same network, `--snmp-arp`, all 6 L3 candidates answer SNMP** (bound) | ≤ 6 × 243 ≈ 1,458 | **≤ 6** (one per responding subject) | CONFLICTING for any device whose ARP table lists more than one discovered host, which is effectively all of them |
| **S2: plus `--snmp-bridge-fdb` / `--snmp-lldp` on the 10 current switches** (bound) | ≤ 10 × 243 ≈ 2,430 FDB observations, plus LLDP entries | ≤ 10 per category | Likewise CONFLICTING for any switch with more than one learned MAC or LLDP neighbor |
| **S3: hypothetical host-side `default_gateway` provider** (bound) | ≤ 1 per host that answers | **≤ 243** (one per host) | WEAK when one source reports one gateway; CONFIRMED when two independent sources agree (for example the route table and the DHCP lease); CONFLICTING only on a real disagreement |

The S1 and S2 bounds assume that ARP and forwarding entries exist only for discovered hosts. Entries for undiscovered addresses are kept as observations but dropped from canonical records by the resolver's endpoint gate (verified: an `arp_neighbor` observation pointing at an undiscovered address yields no canonical record). Real ARP caches age out, so actual counts would be lower.

**The key comparison is S1 against S3.** S1 produces at most six records, all of them CONFLICTING. That means it cannot answer "which gateway does H use?" even in principle, because the answer is spread across six fan-out records. S3 answers that question directly, one record per host. This is why the provider interface in Section 9 puts the host as the subject.

---

## 8. Ambiguity Analysis

### 8.1 Candidate gateways in the data

Six devices are classified (at `HEAD`) as able to route at layer 3. All six are in 172.16.100.0/24.

| IP | Type | Winning rule | Vendor | Notes |
|---|---|---|---|---|
| 172.16.100.2 | FIREWALL | SonicWallFirewallRule | SonicWall | |
| 172.16.100.6 | FIREWALL | SonicWallFirewallRule | SonicWall | hostname `sw2.wrf.scterm.com`: possibly an HA peer of .2, unconfirmed |
| 172.16.100.4 | ROUTER | EdgeRouterRule | Ubiquiti | dnsmasq on port 53 |
| 172.16.100.7 | ROUTER | EdgeRouterRule | Ubiquiti | dnsmasq on port 53 |
| 172.16.100.240 | ROUTER | EdgeRouterRule | Ubiquiti | port 53 tcpwrapped |
| 172.16.100.8 | FIREWALL | PfSenseFirewallRule | Silicom (pfSense) | Unbound on port 53 |

Nothing in the collected fields tells these six apart as "the gateway". The HA-pair possibility for .2 and .6 is itself unverifiable: there are no virtual or locally-administered MACs in the dataset.

### 8.2 Heuristic signals fail on this dataset

| Heuristic | Result |
|---|---|
| ".1 is the gateway" | 172.16.100.1 is a Cisco **switch**, 172.16.101.1 is an Intel-vendor **host** classified UNKNOWN, and 172.16.102.1 was **not discovered**. The heuristic fails in all three ranges. |
| ".254 is the gateway" | Not discovered in any range. |
| "Device classified as router or firewall" | Six candidates (Section 8.1), none in 172.16.101.x or 172.16.102.x. |
| "Runs DNS" | Five devices: three of the candidates plus two Dell Windows DNS servers (172.16.100.20 and .21). |
| "Runs a routing protocol" | No routing-protocol ports observed on any device. |

### 8.3 Is this one routed network or three?

The evidence points to **one flat layer-2 segment**. This is an inference, not a measurement.

- **MAC coverage.** Nmap reports MACs only for hosts it reaches over the local layer-2 segment, and 243 of 244 hosts have a unique MAC across all three /24 ranges. Behind a router, nmap would report no MAC for remote hosts. Proxy ARP is also unlikely: it would answer with the router's MAC, so many hosts would share one MAC, and none do.
- **The scanner.** The one host without a MAC, 172.16.102.52 (`SCTLT108`, a laptop-style name), is consistent with being the scanner. Nmap does not report the scanning host's own MAC.
- **No L3 device outside 172.16.100.x.** A routed design would normally need an interface in each subnet.

**Consequence.** If the segment is flat, "gateway relationships between /24s" do not exist, and the meaningful question is which of the six L3 devices is the segment's default gateway (and what lies beyond it). The /24 grouping used in this report and in common practice would then be a presentation artifact.

**Evidence gap.** The run did not record its scan targets: neither the `.nmproj` file nor the report keeps the `--subnet` values or the auto-detected subnet (`local_subnet.py`). Any future topology replay needs this run metadata to separate "outside the scanned range" from "not present".

### 8.4 The resolver labels gateway fan-out as a conflict

This was verified by running the real `IdentityResolver` and `RelationshipResolver` on synthetic `arp_neighbor` observations with identity-resolved endpoints:

| Case | Canonical result |
|---|---|
| One gateway's ARP table lists 3 discovered hosts | **1 record, `CONFLICTING`**, related = {3 hosts} |
| One gateway's ARP table lists 1 host | 1 record, `WEAK` |
| Two firewalls each list the same host | 2 records, each `WEAK` (subject = each firewall) |
| An ARP entry for an undiscovered address | No canonical record (the observation is kept) |

`CONFLICTING` is defined as "more than one distinct `related_subject`" for a `(subject, category)` group (`resolver.py:146-147`). That definition fits **single-valued** claims, where one subject should have one related subject, such as "H's default gateway". It does not fit **multi-valued** claims (a gateway's ARP neighbors, a switch's forwarding entries, a switch's LLDP neighbors), where many related subjects are the normal, correct state. All three implemented categories are multi-valued when reported from the infrastructure side.

ARCH-025 §3 recorded this cardinality mechanically ("a subject with a relationship to two different neighbors under the same category collapses into one CONFLICTING record") and chose to render it faithfully rather than fix it, which was correct for a presentation sprint. For topology, though, the label is wrong rather than merely untidy. A technician who sees the firewall "CONFLICTING" across 200 hosts would read it as an evidence problem when it is simply the firewall working normally.

Current tests do not cover this. The ARP, LLDP and FDB provider tests stop at observation emission, and no test sends a fan-out table through the resolver end to end.

---

## 9. Recommended Provider Interface

This section specifies the interface a gateway provider would need **when** the evidence justifies one. It does not recommend building it now (Section 10).

### 9.1 Contract: unchanged `EnrichmentProvider`

No new interface is needed. The provider:

- implements `enrich(devices)` and `collect_observations()`, exactly as the three SNMP providers do;
- never mutates `Device` (ARCH-017's additive-layer rule);
- emits `RelationshipObservation`s only (plus `IdentityObservation`s if it learns a gateway's MAC, following FEAT-010A's gated MAC-identity pattern);
- is opt-in, behind its own flag, added to `Application.run()`'s `enrichment_providers` list (ARCH-020 §9: no further runtime integration needed).

### 9.2 Observation shape: the host as subject

```
RelationshipObservation(
    subject          = <host IP>,          # the host whose gateway is claimed
    related_subject  = <gateway IP>,       # the claimed gateway
    category         = "default_gateway",  # new, single-valued by nature
    provenance       = ObservationProvenance(
        provider          = "<wmi|ssh|dhcp>",
        collection_method = "<route-table|dhcp-option-3|...>",
        observed_at, source_run),
)
```

**Why the host is the subject.** The resolver's `(subject, category)` grouping and its CONFLICTING rule are *correct* for this shape:

- **One host, one gateway:** `WEAK`.
- **Route table and DHCP lease agree:** `CONFIRMED`. They are independent `(provider, collection_method)` pairs.
- **Two sources name different gateways:** `CONFLICTING`, and this time the conflict is real (for example a stale lease against a static route).

No resolver change is needed for this shape.

### 9.3 Category and directionality

`default_gateway` is **directional**, from host to gateway, and is distinct from:
- `arp_neighbor`, which says G has resolved H;
- `connected_to`, which is a layer-2 LLDP link;
- `bridge_fdb`, which is layer-2 reachability.

It must not be derived from `arp_neighbor` by inverting the subject. An ARP entry on G is not evidence that H routes through G (Section 5).

### 9.4 What ARP evidence becomes under this design

`arp_neighbor` stays as it is, as adjacency evidence. A later consumer may use it to **corroborate** a `default_gateway` claim: the claimed gateway G should have an interface on H's segment. That is cross-category corroboration, which ADR-013's independence rules do not define today. It is noted here as a future design question, not designed in this report.

### 9.5 The open question that does need ADR-level treatment

Multi-valued categories (`arp_neighbor`, `bridge_fdb`, and `connected_to` from switches) need a corroboration semantics in which many related subjects are normal. Possible directions, none of which this report chooses:

1. **Per-category cardinality:** declare each category single-valued or multi-valued, and group multi-valued ones by `(subject, related_subject, category)`.
2. **Per-edge groups:** move to triple-keyed groups everywhere and detect conflict per claim instead.
3. **Leave the resolver alone** and recast multi-valued infrastructure evidence as host-subject observations.

Any of these changes what CONFLICTING means under ADR-013, so it needs an ADR-013 amendment or a new ADR. It is not a provider decision.

---

## 10. Recommendation: Do Not Build the First Topology Provider Yet

The charter asked for a first topology provider recommendation **only if the evidence justifies it**. It does not:

1. **No production relationship evidence exists.** All implemented providers yield 0 relationships on the production dataset. A new provider would be the fourth unexercised one, not the first useful one.
2. **The implemented evidence can't answer the gateway question, even once collected.** It proves adjacency, not gateway use, and it would surface as at most 6 CONFLICTING records (Section 7, S1).
3. **The deterministic sources are host-side** (route table, DHCP option 3). ARCH-021 assessed host-side collection as the most expensive acquisition path, and nothing in this dataset reduces that cost.
4. **The resolver's semantics for multi-valued categories are unsettled** (Section 9.5). Building on top of them now would put a mislabelled state in front of technicians.

### 10.1 Roadmap

| Step | Type | Deliverable | Why it comes first |
|---|---|---|---|
| 1 | **OPS-001**: SNMP-enabled production capture | One production run with `--snmp --snmp-arp --snmp-lldp --snmp-bridge-fdb`. Its relationship observations are exported (for example via the FEAT-027 relationship CSV) and the run records its scan targets. | Turns every bound in Section 7 into a measurement. It also shows whether SNMP is reachable at all on this network, which is the cheapest way to learn whether the existing three providers are worth anything in production. |
| 2 | **ARCH-027**: multi-valued relationship semantics | An investigation and ADR-013 amendment proposal (Section 9.5), validated against Step 1's real fan-out data | Fixes the CONFLICTING mislabel before any topology consumer depends on it |
| 3 | **TEST**: end-to-end fan-out coverage | Tests that send multi-entry ARP, FDB and LLDP tables through the resolver and assert the intended state | Closes the coverage gap in Section 8.4, whichever semantics Step 2 chooses |
| 4 | **Decision point**: host-side `default_gateway` | Go or no-go for a `default_gateway` provider (Section 9), weighing WMI/SSH acquisition cost against Step 1's evidence of how ambiguous the gateway really is | Only worth paying for if Steps 1–2 show that infrastructure-side evidence can't identify the gateway |
| 5 | **Small, independent**: run-metadata gap | Record scan targets (and the auto-detected subnet) in run metadata or the report | Needed by every later topology replay; cheap; can be folded into any sprint |

Steps 1 and 5 can proceed now. Step 2 should wait for Step 1's data. Step 4 should wait for both.

---

## 11. Scope Exclusions

These are excluded per the charter: visualization, layout and graph rendering; any production code, test or schema change; changes to `IdentityResolver` or `RelationshipResolver`; persistence of observations; a design for host-side collection (WMI/SSH) beyond the observation shape in Section 9; routing-table (`ipRouteTable`) collection; cross-run corroboration; and any re-decision of ARCH-020 to ARCH-025.

---

## 12. Risks

- **The flat-segment inference could be wrong.** If the scanner was multi-homed, or the run used several `--subnet` targets on a scanner with layer-2 presence in each, the three /24s could be separately routed. Section 8.3's evidence gap is what prevents settling this. Step 1 (recording scan targets) and any SNMP route data would settle it.
- **SNMP may simply be unavailable in production.** If Step 1 finds the L3 devices and switches don't answer SNMP with the available credentials, all three implemented providers stay at zero yield. Host-side evidence (Step 4) then becomes the only deterministic path, at its full acquisition cost. That would be a significant finding for the whole relationship lineage, and it is better learned from one run than from another provider sprint.
- **Treating classification as topology evidence.** It is tempting to infer "the firewall is the gateway" from `device_type`. Doing so would make classification an input to relationship determination, which ADR-013 places in the other direction (topology consumes canonical relationships; it does not derive them from interpretations).

---

## 13. Open Questions

1. Is 172.16.100.0/22 (or larger) the scanned segment? What `--subnet` values did the 2026-09-04 run use?
2. Are 172.16.100.2 and 172.16.100.6 an HA pair, and if so, how should an HA virtual gateway address be represented as a `related_subject`?
3. Should cross-category corroboration (an `arp_neighbor` entry supporting a `default_gateway` claim) count toward CONFIRMED under ADR-013's independence rules, or stay separate evidence?
4. Does any L3 candidate expose its default route over SNMP (`ipCidrRouteTable`)? If so, that would give the segment's *upstream* gateway deterministically, though not which hosts use which local gateway.
