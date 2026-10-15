# ARCH-029 — Inventory, Mapping and Reporting Capability Boundaries

# Status

Investigation Complete. **Architect-reviewed (2026-10-15).**

Review covers the investigation's findings and the replay-scope ruling in Section 9. It does **not** approve any option in Section 7 for implementation. Every decision in Section 8 remains pending with the owner.

Implementation: Not Started. Not authorized by this report.

Production Code Modified: No

ADR Required: Not by this report. Option G2-b (a target-list discovery provider) and any client/MSP deliverable that persists or reloads findings would each need their own decision before implementation (Section 7).

Baseline: `HEAD` `cd1a53d8f84f919c5a9fdac465072db345f46a94`, confirmed before investigation. All line references are to that commit.

**Labels used throughout:**
- **[Fact]** marks something read directly from the repository at the baseline.
- **[Rec]** marks a recommendation of this report.
- **[Q]** marks an open question that needs an owner decision.

---

## 1. Summary

- **[Fact]** NetworkMapper has one entry point and one linear pipeline. Every run performs, in order: host discovery, optional enrichment, classification, identity and relationship resolution, and all report artifacts. There is no capability selection. "Inventory" and "mapping" exist only as which optional flags were passed.
- **[Fact]** Inventory-only runs work today: omit the SNMP relationship flags. The reports handle the empty relationship case.
- **[Fact]** Mapping does **not** depend on classification. No module on the mapping path reads `device_type`, so UNKNOWN devices are tolerated by construction.
- **[Fact]** Mapping **does** depend on host discovery in the same run, for three reasons:
  - relationship providers are enrichment providers and only query already-discovered devices (ADR-010);
  - the relationship resolver only emits edges whose endpoints have canonical identities;
  - two of the three relationship providers resolve endpoints through a MAC index built from identity observations collected earlier in the run.

  This is a structural dependency, not incidental wiring. Offline loading of a previous run's observations is not authorized for mapping (ADR-011 Amendment 1), so the dependency cannot be met from an earlier artifact.
- **[Fact]** The incidental couplings are all in `Application.run()`:
  - classification is unconditional;
  - inventory report sections are always written;
  - the project name is hard-coded;
  - a `.nmproj` save/load harness overwrites one fixed file on every run;
  - which capabilities ran is recorded only in console output, never in the report.
- **[Fact]** The current outputs (`report.md`, `devices.csv`, `relationships.csv`, `observations.json`) are engineering artifacts. No client or MSP deliverable exists. Two read-only view models, `ProjectSummary` and `CanonicalPresentation`, are the reusable contracts for future deliverables.
- **[Rec]** Whatever "independent mapping" comes to mean, it must still include the shared needs: same-run host discovery and identity evidence. Whether a mapping-only run also classifies devices, and which inventory presentation it produces, are separate, **pending** owner decisions (Section 8). They are not settled here.
- **[Rec]** The smallest viable steps, all additive and all subject to owner approval, are:
  1. explicit capability selection in the CLI that never turns on relationship providers, SNMP traffic or a credential requirement unless the operator asks for them (G1);
  2. recording what was requested, what was attempted, how each provider ended and how much evidence it produced, in run metadata and the report (G4).
- **[Rec]** OPS-001 can proceed after its existing procedure update, before any of this capability work. It uses the current application unchanged, in the "both together" configuration. Capability work is not a prerequisite for OPS-001.

---

## 2. Current Execution Trace

**[Fact]** Entry point: `main.py:3-7` constructs `Application` and calls `run()`. The `run()` docstring still describes itself as a "temporary persistence validation harness" (`networkmapper/application.py:61`).

| Step | Where | What happens | Conditional? |
|---|---|---|---|
| 1. Arguments | `application.py:75-82` | `--workbench`, `--scan-profile` (default `fast`), `--subnet`, `--snmp`, `--snmp-arp`, `--snmp-lldp`, `--snmp-bridge-fdb` | — |
| 2. Host discovery providers | `application.py:112-115` | One `NmapProvider` per subnet | **Always** |
| 3. Enrichment providers | `application.py:121-136` | SNMP system group, ARP, LLDP and FDB providers, each only if its flag is set; one shared credential from the environment (`:122`) | Optional |
| 4. Discovery, enrichment, classification | `discovery_engine.py:51-109`, called at `application.py:144` | Discovery providers run and devices are de-duplicated by IP (`:73-80`). Each enrichment provider receives the observations so far, enriches, and adds its own (`:100-105`). **Classification always runs** (`:107`, `:111-146`) | Classification unconditional |
| 5. Console summaries | `application.py:146-190` | Per-provider diagnostics, then a classification summary and sample table | Diagnostics conditional on providers |
| 6. Resolution | `application.py:194-195` | `IdentityResolver` over all observations; `RelationshipResolver` over all observations plus identities | **Always** |
| 7. Project | `application.py:197-203` | `customer_name="Test Network"` hard-coded (`:198`) | Always |
| 8. Workbench | `application.py:205-212` | Classification workbench, optional | `--workbench` |
| 9. Reports | `application.py:227-256` | `observations.json`, `devices.csv`, `relationships.csv`, `report.md`, in that order, into one run directory | **Always, all four** |
| 10. Persistence harness | `application.py:268-285` | Save to `output/Test Network.nmproj` (overwritten every run), reload, compare device counts | **Always** |

**[Fact]** `report.md` section order (`markdown_exporter.py:84-96`):
1. executive summary;
2. classification overview;
3. device inventory, which re-runs `DeviceClassifier` to explain each classification (`:51`);
4. canonical identity;
5. canonical relationships;
6. appendices.

---

## 3. Actual Dependencies Versus Incidental Wiring

### 3.1 What inventory and diagnostics needs

**[Fact]**
- **Host discovery** (`NmapProvider`), with service enrichment at STANDARD or DEEP.
- **Classification** (`DiscoveryEngine._classify_devices`).
- **Optionally**, SNMP system-group enrichment (`--snmp`), which fills `Device` fields that classification reads (OPS-001 D2).
- **Reporting** from `network_graph`, via `ProjectSummary` (`reporting/project_summary.py:33-51`) and `MarkdownExporter`.

Inventory needs no relationship provider and no relationship resolution. The report states the empty case plainly ("No canonical relationship evidence collected.", `markdown_exporter.py:431-435`), and `relationships.csv` is written with its header only (verified in VER-029).

### 3.2 What mapping needs

| Dependency | Evidence | Kind |
|---|---|---|
| A device set to query | `EnrichmentProvider` "never discovers" devices; it only enriches the set it is given (`enrichment_provider.py:10-18`; ADR-010 Decision). ARP, LLDP and FDB query every device in that set ("Hosts Eligible", `arp_neighbor_provider.py:140`, `lldp_neighbor_provider.py:181`, `bridge_fdb_provider.py:168`) | **Structural** (ADR-010) |
| Canonical identities for both endpoints | `RelationshipResolver` drops observations whose subject or related subject has no identity (`relationships/resolver.py:136-144`) | **Structural** (ADR-013 Relationship Endpoints) |
| Identity evidence for endpoints | Identities come only from `IdentityObservation`s. `NmapProvider` emits hostname, MAC, computer name and domain (`nmap_provider.py:140-187`). ARP emits MAC identities **only for IPs already in the device set** (`arp_neighbor_provider.py:97,192-220`). LLDP emits `sysName` only for discovered neighbors (`lldp_neighbor_provider.py:130,238`) | **Structural** |
| A MAC-to-subject index | `bridge_fdb` and LLDP MAC chassis IDs resolve through `build_mac_index()` over the observations received so far (`identity/mac_index.py:19-31`; `bridge_fdb_provider.py:108-124`; `lldp_neighbor_provider.py:117-134`) | Structural for those resolution paths; absence reduces coverage, never correctness (`enrichment_provider.py:52-56`) |
| An SNMP credential | `application.py:122,374-384` | Operational |

**Consequence [Fact].** A canonical relationship can only connect two subjects that **both have a canonical identity** in the same run.

The resolver's gate checks identity, not discovery (`relationships/resolver.py:136-144`). A canonical identity exists only for a subject with at least one `IdentityObservation` (`identity/resolver.py:58-71`). Nmap emits an identity observation only when it actually observed a value (`nmap_provider.py:172-173`). So **a discovered device alone does not establish a canonical identity**: a host found by discovery with no hostname, MAC or other identity value has no identity, and its edges are dropped.

Discovery is still necessary, because the relationship providers only query discovered devices and only emit identity observations for discovered IPs. But it is not sufficient. An ARP or LLDP neighbor without a canonical identity is retained as an observation (and in `observations.json`) but never becomes a canonical edge. Mapping coverage is therefore bounded by canonical-identity coverage, which is itself bounded by host-discovery coverage.

**External note, not verified here:** Nmap normally reports a MAC address only for hosts on the scanner's own segment. `NmapProvider` takes the MAC only when Nmap supplies one (`nmap_provider.py:510-513`).

### 3.3 What mapping does not need

**[Fact]** The needs separate into three groups:
- **Shared by both capabilities:** host discovery (the device set) and identity evidence (the observations behind canonical identities). Mapping cannot work without these (Section 3.2).
- **Inventory-specific:** classification and inventory presentation (device-type grouping, classification explanations, `ProjectSummary` counts).
- **Mapping-specific:** relationship providers, relationship resolution and relationship presentation.

The mapping path itself does not need:
- **Classification.** No module on the mapping path reads `device_type`. A repository-wide search finds `device_type` reads only in classification, knowledge, developer tooling, `ProjectSummary`, the two device-oriented exporters, the serializer, and `Application`'s console summary (`application.py:170-189`). None appears in `discovery/`, `identity/`, `relationships/` or `reporting/canonical_presentation.py`. **Mapping tolerates UNKNOWN by construction.** Whether a mapping-only run should nonetheless classify is a pending decision (Section 8, decision 2).
- **Service enrichment.** STANDARD and DEEP service scans feed classification and inventory evidence, not relationship providers. FAST host discovery supplies the device set and the MAC and hostname identity evidence.
- **SNMP system-group enrichment (`--snmp`).** It is independent of the three relationship providers.
- **A previous inventory run.** Nothing reads a prior run's output.

### 3.4 Incidental wiring that blocks clean independent execution

**[Fact]**
1. **No capability selection.** Host discovery and classification always run, and all four report artifacts are always written. A "mapping-only" run is approximated today by `--scan-profile fast` plus the relationship flags, but it still classifies and still writes full inventory sections.
2. **Classification is inside `DiscoveryEngine.discover()`** (`discovery_engine.py:107`), not a separate step the application chooses.
3. **Run provenance is console-only, and one failure mode is silent.** Which providers ran, and their reachability diagnostics, are printed (`application.py:146-160`) but not written to `report.md`. `RunMetadata` records only timestamp, scan profile, customer name, device count and version (`reporting/report_run.py:11-24`). A report reader cannot tell "no relationship evidence because mapping did not run" from "mapping ran and found nothing". ARCH-025 Section 16 noted this ambiguity for the reload case.

   An enrichment provider that raises is caught and discarded with no record (`discovery_engine.py:100-105`). Each relationship provider sets its `run_diagnostics` only after its query loop finishes (`arp_neighbor_provider.py:139`, `lldp_neighbor_provider.py:180`, `bridge_fdb_provider.py:167`), so a provider that fails mid-run leaves no diagnostics block and contributes no observations. Its absence from the console is the only trace.
4. **Hard-coded project identity and a shared overwrite.** `customer_name="Test Network"` (`application.py:198`), and every run overwrites `output/Test Network.nmproj` (`:268-272`). OPS-001 step 2 exists only to protect the baseline from this.

---

## 4. Requirement-to-Current-Support Table

| Requirement | Current support | Evidence | Gap |
|---|---|---|---|
| One application supports inventory/diagnostics and mapping | **Yes** | One `Application`; Nmap plus the three relationship providers (`application.py:112-136`) | — |
| Either capability runs independently, without first running the other | **Inventory: yes. Mapping: partial** | Inventory: omit relationship flags. Mapping never needs a prior inventory *run*, but always runs classification and inventory reporting, and structurally needs same-run host discovery (Section 3.2) | G1, G2, G3 |
| Both run together | **Yes** | All flags together; this is OPS-001's configuration | — |
| Mapping tolerates UNKNOWN classifications | **Yes** | No `device_type` read on the mapping path (Section 3.3) | — |
| Inventory useful without relationship evidence | **Yes** | Empty-section handling (`markdown_exporter.py:431-435`); header-only `relationships.csv` | — |
| Later client/MSP reports use either capability's findings or both | **Not yet** | Only engineering artifacts exist; ROADMAP Phase 8 lists "Asset inventory reports" and "Executive reports" as planned (`ROADMAP.md:236-244`) | G3, G4 |
| Conclusions preserve evidence, uncertainty and provenance | **Yes per record; partial per run** | Canonical records carry state and full observations with provenance (ADR-012/013; `canonical_presentation.py`); `observations.json` keeps every observation (ADR-011 Amendment 1). Run-level provenance (which capabilities ran, reachability) is console-only | G4 |

---

## 5. Reusable Contracts

**[Fact]**

| Contract | Location | Reuse for |
|---|---|---|
| `DiscoveryProvider` / `EnrichmentProvider` roles, with optional `collect_observations()` and `receive_observations()` | `discovery/provider.py:7-32`, `discovery/enrichment_provider.py:10-58`; ADR-010 | Composing a capability as a choice of provider lists without changing the engine |
| `DiscoveryEngine(providers, enrichment_providers, event_bus)` | `discovery_engine.py:24-49` | Capability selection is just which lists are passed |
| `IdentityObservation`, `RelationshipObservation`, `ObservationProvenance` | `observations/models.py`, `observations/provenance.py`; ADR-011 | Evidence and provenance for both capabilities |
| `IdentityResolver`, `RelationshipResolver` | pure functions; ADR-012/013 | Shared by mapping and by identity in inventory |
| Category meanings | `ARP_NEIGHBOR_CATEGORY` (`arp_neighbor_provider.py:31-38`), `BRIDGE_FDB_CATEGORY` (`bridge_fdb_provider.py:34-40`), `LLDP_NEIGHBOR_CATEGORY` (`lldp_neighbor_provider.py:40-48`) | Preserving what each edge does and does not claim (Section 6.2) |
| `ProjectSummary` (aggregate inventory) and `CanonicalPresentation` (per-record identity and relationship view) | `reporting/project_summary.py`, `reporting/canonical_presentation.py`; ARCH-025, ADR-005 | Future client/MSP renderers, without recomputing states |
| `RunMetadata` and `ReportRunPaths` | `reporting/report_run.py` | Recording run-level capability provenance (G4) |
| `observations.json` and `devtools replay-observations` | ADR-011 Amendment 1; PLAN-029; VER-029 | **Verification replay only.** Not a mapping input (Section 6.1) |

---

## 6. Constraints Applied

### 6.1 No offline artifact loading for mapping

**[Fact]** ADR-011 Amendment 1 authorizes reading `observations.json` only for replay verification, and forbids loading observations into any normal run, report, comparison, workbench or benchmark workflow. Independent mapping therefore cannot be built as "map from a previous run's artifact". Mapping must collect its evidence, including the host-discovery and identity evidence it depends on, within its own run.

The endpoint-gate exclusion analysis described in Section 9 does not contradict this. Under the architect ruling recorded there, it is replay verification of a single run's own artifact, performed only to explain the committed resolvers. It is not mapping and not a normal workflow.

### 6.2 Category meaning and corroboration

**[Fact]** Each category makes a different, directional claim:

| Category | What it claims | What it does not claim |
|---|---|---|
| `arp_neighbor` | An L3 device has resolved another IP to a MAC in its own cache | Physical adjacency |
| `bridge_fdb` | L2 reachability through a bridge port | Direct adjacency; an unmanaged switch in between is invisible |
| `connected_to` | An LLDP neighbor relationship (protocol adjacency) | — |

`WEAK` and `CONFIRMED` count independent `(provider, collection_method)` sources (`relationships/resolver.py:57-65`). They say how well a claim is supported, not that the claim is physical connectivity.

**[Rec]** Any mapping output, including future client deliverables, must label edges by category meaning. It must not merge categories into a generic "link", and must not imply physical connectivity from `CONFIRMED`.

### 6.3 ARCH-025 read against current code

**[Fact]** ARCH-025 predates ADR-013 Amendment 1 and PLAN-028. Its statements that there is one `CanonicalRelationship` per `(subject, category)`, and that the record has no `related_subject` field (ARCH-025 Sections 3 and 7), are superseded: records are now per edge, with `related_subject` and `cardinality`. Its presentation architecture (a read-only view model; renderers never recompute state; device enrichment optional) is implemented as `CanonicalPresentation` and remains the right contract for future reports.

### 6.4 Lab material

**[Fact]** `docs/LAB.md` "Executive Reporting" (`LAB.md:278-301`) and "Asset Intelligence" are research topics in the lab's promotion process (`LAB.md:68-98`), not approved architecture. They are not relied on here.

---

## 7. Gaps and Smallest Viable Options

All options are additive. None adds confidence scores, inferred links, persistence, historical merging or a new canonical model.

**G1. No explicit capability selection.**

**[Fact] Current defaults** (`application.py:75-136`, `:374-392`):
- With no flags, a run performs Nmap host discovery at the **FAST** profile (`--scan-profile` defaults to `fast`, `:77`), classification, both resolvers and all four report artifacts.
- No SNMP provider is constructed, no SNMP traffic is sent, and no credential is read unless at least one of `--snmp`, `--snmp-arp`, `--snmp-lldp` or `--snmp-bridge-fdb` is passed (`:121-136`).
- When any of those flags is passed and `NETWORKMAPPER_SNMP_COMMUNITY` is unset, the run exits with code 2 before scanning (`_resolve_snmp_credentials`, `:374-392`).
- So today's default run is effectively inventory with an empty relationship section, not "both".

**[Rec] Option G1-a (smallest).** Add a capability selection to the CLI that maps onto the existing provider lists and report steps, with one firm constraint: **selecting a capability must never silently turn on relationship providers, SNMP traffic or a credential requirement.** Provider activation, and therefore any SNMP traffic and credential check, stays explicit. A run with none of the new options behaves exactly as today.

**[Q]** The exact contract is left to an approved plan:
- the option's name and values;
- what a mapping selection does when no relationship provider is named (refuse, or run only host discovery and identity);
- how it combines with the four existing SNMP flags, which must keep working.

No engine or resolver change is needed for the provider side.

**G2. Mapping cannot reach subjects without a canonical identity in the same run** (Section 3.2, Consequence), including every device host discovery did not find.
- **[Rec] Option G2-a (no change).** Accept it, and measure how often it matters using OPS-001's evidence. `observations.json` makes the drop-off countable, because observations dropped at the gate are retained. The counting method is defined under G4 ("Endpoint-gate losses").
- **Option G2-b (only if OPS-001 shows meaningful loss at the endpoint gate).** A new `DiscoveryProvider` that turns an operator-supplied target list into devices. This fits ADR-010's existing roles, but it changes what "discovered" means. **[Q]** It needs its own investigation and decision. **[Rec]** Defer it.

**G3. Classification is unconditional, and inventory sections are always rendered.**

**[Fact]** Classification runs in two places:
- inside `DiscoveryEngine.discover()` (`discovery_engine.py:107`). `_classify_devices` both classifies each device and adds it to the graph (`:123-125`), so classification and graph construction are currently one loop;
- again in `MarkdownExporter`, which re-runs `DeviceClassifier` to explain each device's classification (`markdown_exporter.py:51`, used by the device-inventory section, `:89`).

**Tradeoff [Q].** Keeping classification in a mapping-only run costs time and adds inventory-flavoured content that run did not ask for. Removing it adds a code path to shared orchestration. Neither the time cost nor the benefit has been measured. This report makes no performance claim either way.

**Smallest known change to skip it** (described, not implemented):
- an additive `DiscoveryEngine` constructor option that, when set, adds devices to the graph without calling the classifier;
- unclassified devices keep their default `DeviceType.UNKNOWN` (`core/models.py:113`), which the mapping path already tolerates;
- a mapping-only run would also omit the device-inventory report section, because that section re-runs the classifier;
- the default must stay "classify", so existing behavior and benchmarks are unchanged.

**Options:**
- **Option G3-a.** Keep classification in every run, and omit inventory-specific report sections in a mapping-only run.
- **Option G3-b.** Make classification skippable through the change above.

The choice between them is a pending owner decision (Section 8, decision 2). A measurement of classification time on a representative device set **may inform** the tradeoff, and no current artifact provides one by itself (Section 9). It is **not required** for the owner to decide what a mapping-only run means: that is a choice about capability semantics, which can be made on its own terms.

**G4. Run-level provenance is not in the report.**

**[Fact]** Five kinds of run-level fact are needed to interpret a report. They differ in whether the code can already observe them:

| Fact | Observable today? | Where | Instrumentation needed |
|---|---|---|---|
| **Requested capabilities** | Indirectly only: there is no capability concept, only the parsed flags | `application.py:75-82` | Record the request (from G1) |
| **Providers configured** | Yes, in process | Provider lists built at `application.py:112-136`. **This proves configuration only, not that a provider ran** | Record them; nothing is written today |
| **Providers attempted** | Partly, and only in the console | Each relationship provider publishes a `PHASE_STARTED` event with provider-specific text as it begins its query loop ("Walking ARP tables…", `arp_neighbor_provider.py:100-103`; LLDP `lldp_neighbor_provider.py:137-140`; FDB `bridge_fdb_provider.py:127-130`). The console renderer prints it (`runtime/cli_renderer.py:26-32`). The telemetry recorder keeps only completed phases, and all four SNMP providers share one phase name (`runtime/telemetry.py:50-68`; `runtime/events.py:20`), so the runtime summary cannot attribute a start to a provider. Nothing reaches the report | **Gap.** No structured record of an attempt exists. A provider that fails before its start event (in `receive_observations()`, or in `build_mac_index()` for LLDP and FDB, `lldp_neighbor_provider.py:134`, `bridge_fdb_provider.py:124`) leaves no trace at all. Establishing "attempted" needs a record made by `DiscoveryEngine` when it calls each provider (`discovery_engine.py:100-103`) |
| **Execution outcome per provider** | Partly | Hosts eligible, queried, responded and timed out are in each provider's `run_diagnostics` and printed to the console (`application.py:146-160`) | Record them. **A provider that raises is swallowed** (`discovery_engine.py:100-105`) and leaves no diagnostics (Section 3.4, item 3), so recording an outcome of "failed" needs new instrumentation at that `except` |
| **Evidence counts** | Derivable, not reported | Observations per provider, method and category are countable from `Project.observations`. Canonical counts come from the resolvers. Endpoint-gate losses are derivable as defined below | Compute and render; no new collection |

**Endpoint-gate losses [Fact and Rec].** These must be counted against the resolver's actual gate (`relationships/resolver.py:136-144`), not as "relationship observations minus those behind canonical edges". That subtraction would also absorb self-loop exclusions.
- **The gate.** Let *I* be the set of subjects in that run's canonical identities. A relationship observation passes only if its `subject` is in *I*, its `related_subject` is in *I*, and the two differ.
- **Separate buckets.** Classify each relationship observation that fails, in this order:
  1. subject missing from *I*, related subject present;
  2. related subject missing from *I*, subject present;
  3. both missing;
  4. both present, but subject equals related subject (self-loop exclusion, reported separately, not as an identity loss).

  A self-loop whose single subject lacks an identity falls into bucket 3; that precedence is a reporting choice and must be stated wherever the counts appear.
- **Observations versus edges.** Report each bucket twice:
  - as an **observation count**, preserving multiplicity, so duplicate observations each count;
  - as a **distinct-edge count**, over distinct `(subject, category, related_subject)` triples.

  Repeated walks of the same table make the two differ, and conflating them overstates or understates loss.
- **Identity, not discovery.** *I* must come from the canonical identities, never from the discovered device list. A discovered device without a canonical identity counts as missing (Section 3.2, Consequence).
- **Two different uses.** Computing these buckets during a run, from in-memory data, and rendering them in `report.md` is part of option G4-a, which remains pending (Section 8, decision 4). Counting them after a run from that run's `observations.json` is replay verification, scoped by the architect ruling in Section 9. That ruling does not authorize new application reports.

**[Fact] Zero observations do not by themselves mean successful collection.** A category with no observations is consistent with any of the following, and the report cannot currently tell them apart:
- not requested;
- requested but never attempted;
- attempted and failed (silently, as above);
- attempted with every host timing out;
- attempted with devices answering with empty tables.

**[Rec] Option G4-a.** Add requested capabilities, providers configured, providers attempted, a per-provider outcome (including an explicit failed state) and evidence counts (including the endpoint-gate buckets) to `RunMetadata`, and render them in `report.md`. This lets a reader, and any later client/MSP deliverable, tell "not collected" from "collected, nothing found" from "failed".
- **Recording only:** requested capabilities, providers configured, the existing diagnostics, and evidence counts.
- **New instrumentation:** a structured record of each attempt, and the failed outcome. Both belong at the point where `DiscoveryEngine` calls each enrichment provider.

**[Fact]** None of this may be added to `observations.json`. Amendment 1 Decision 4 forbids run metadata in that artifact.

**G5. Incidental wiring: the hard-coded project name and the `.nmproj` overwrite harness.**
- **[Rec]** Leave as is until a separate, small decision. It does not block capability work, and OPS-001 already guards against it.

**G6. Client/MSP deliverables.**
- **[Rec]** Treat these as new read-only renderers over `ProjectSummary` and `CanonicalPresentation`, alongside the existing engineering report rather than replacing it.
- **[Q]** Audience, content and format need their own investigation.
- **[Q]** Any deliverable that combines runs, or reloads findings later, triggers the persistence decision that ARCH-025 Section 15 and ADR-011 Amendment 1 both reserve.

---

## 8. Decisions Requiring Owner Approval

All decisions below are **pending**. None is settled by this report.

1. **[Q] Definition of independent mapping.** Confirm that a mapping-only run still performs its own host discovery and collects identity evidence (recommended, because both are structural needs), rather than taking only an explicit target list (G2-b). This decision does not settle classification or inventory presentation; those are decisions 2 and 5.
2. **[Q] Classification in mapping-only runs.** Keep it in every run (G3-a) or make it skippable (G3-b). This report recommends neither. Classification timing may inform the choice, but it is not required: the owner can decide the capability semantics without it (G3). The decision remains pending.
3. **[Q] CLI contract** (G1-a). Approve capability selection in principle, under the constraint that it never silently activates relationship providers, SNMP traffic or a credential requirement. The option names, values, behavior when no relationship provider is named, and compatibility with the existing SNMP flags are for an approved plan.
4. **[Q] Run-level provenance in reports** (G4-a). Approve recording requested capabilities, providers configured, providers attempted and per-provider outcomes (attempt and failure both need new instrumentation), and evidence counts including the endpoint-gate buckets, in `RunMetadata` and `report.md`. Confirm that nothing is added to `observations.json`.
5. **[Q] Report separation.** Decide whether mapping-only and inventory-only runs produce one capability-aware `report.md`, or separate engineering documents.
6. **[Q] Client/MSP deliverables.** Approve a separate investigation (G6), with the persistence boundary stated up front.
7. **[Q] Project identity and the `.nmproj` harness** (G5). Decide whether and when to replace the hard-coded name and fixed-path overwrite.

---

## 9. Sequencing and Implications for OPS-001

**[Rec] Sequence:**
1. **OPS-001 procedure update and approval** (already planned, VER-029 Section 9). This needs no capability work.
2. **Run OPS-001** as currently designed: STANDARD profile with `--snmp-arp --snmp-lldp --snmp-bridge-fdb`, which is the "both together" configuration.
3. **Capability selection and run provenance** (G1-a with G4-a) as one small PLAN and FEAT, after the owner decisions above. A run without the new options must behave exactly as today.
4. **Report separation** (decision 5), then **client/MSP deliverable investigation** (G6).
5. **Target-list discovery** (G2-b) only if evidence shows meaningful loss at the endpoint gate.

**What OPS-001 can and cannot establish [Fact and Rec].**

It **can** measure, within the corpus it collects:
- retained relationship observations, per provider and category (`observations.json` keeps all of them, including unresolved ones);
- losses at the endpoint gate, counted after the run from its own artifact, as replay verification, by the method under G4 ("Endpoint-gate losses"): observations whose subject, related subject or both lack a canonical identity in that run, with self-loop exclusions counted separately, each as an observation count and a distinct-edge count. The canonical identities themselves are not in any artifact, so the count needs *I* reconstructed by re-running the committed `IdentityResolver` over the run's `observations.json`, never the discovered device list. The scope of that analysis is set by the architect ruling below. OPS-001 Section 10, item 5 already plans this drop-off analysis;
- SNMP reachability for the hosts it queried (eligible, queried, responded, timed out);
- artifact sizes.

It **cannot** establish:
- **complete network coverage.** It sees only what host discovery found and what queried devices reported. Devices that neither found nor reported remain unknown, and there is no ground truth to compare against;
- **classification cost, or the effect of skipping classification.** The console log's OBS-002 runtime summary prints a duration for the Classification phase (`runtime/cli_renderer.py:50-72`, from events published at `discovery_engine.py:114-146`). That is one wall-clock observation from one run, with classification always on. It does not cover the second classification pass inside `MarkdownExporter`, and it gives no comparison with a run that skips classification. OPS-001 also does not list it as a measured output. A suitable measurement would need its own design.

So OPS-001 informs decision 1 and option G2 (how much relationship evidence is lost at the endpoint gate in that corpus). It does not settle decision 2, which can be made without timing data.

**Architect ruling: scope of endpoint-gate exclusion analysis (2026-10-15).**

> Endpoint-gate exclusion analysis is within replay verification when performed solely to explain the committed resolvers' treatment of a single run's retained observations. It may reconstruct canonical identities and count identity-gate exclusions and self-loops using the documented buckets, preserving observation multiplicity and distinguishing distinct relationship triples. This does not authorize normal application loading, cross-run analysis, new application reports, or changes to the devtools command. OPS-001 must document the analysis procedure for review before execution.

This ruling settles the scope question raised in an earlier draft of this section. It applies ADR-011 Amendment 1's existing replay-verification authorization; it does not amend it.

**Implications for OPS-001 [Fact and Rec]:**
- **OPS-001 is independent of this work, and capability work is not a prerequisite for it.** It runs the committed application unchanged and needs only its procedure update (step 5 artifact name, step 9 replay command, criterion 5 wording).
- **Run it against a pinned commit**, as its step 1 already records `HEAD`. If capability selection lands first, OPS-001 must either still use a configuration that behaves exactly as today or be re-reviewed. It should not depend on the intention that defaults stay unchanged.
- **Its artifacts stay valid** for later replay verification: `observations.json` is versioned, and replay is the authorized reader. They are not an input to mapping (Section 6.1).
- **Its provider-outcome evidence is limited** by the silent-failure path in Section 3.4, item 3. OPS-001 success criterion 3 already checks that each diagnostics block is present, which is the current way to detect a provider that failed outright.

---

## 10. Sanitization

This report contains no production addresses, hostnames, MACs, serials, credentials or customer names. It names only code locations, categories and documentation-only identifiers. `Test Network` is the application's hard-coded project name, not a customer name (OPS-001 Section 3).
