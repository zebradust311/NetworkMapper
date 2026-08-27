# Status

Plan Approved (post-correction)

Authority: ARCH-024-Bridge-MIB-Relationship-Provider-Architecture.md (design authority)

Implements: FEAT-012B — SNMP Bridge-MIB Forwarding-Table Relationship Provider

Production Code Modified: Yes (see Section 3)

New ADR Required: No (Section 6)

---

This document is the implementation plan for FEAT-012B, produced against
ARCH-024 and carried through one correction pass before implementation
began. It reproduces the plan exactly as approved — three planning
corrections (file-inventory reconciliation, integration-test role wording,
and CLI regression coverage) are incorporated below because they were
approved *before* implementation started; nothing below reflects an
implementation-time change. Section numbering is preserved exactly as
approved, including Sections 5 and 7.3, because in-code comments and test
docstrings cite this document by section number.

Grounded against the code as it stood at planning time: `lldp_neighbor_provider.py`,
`arp_neighbor_provider.py`, `snmp_client.py`, `snmp_lldp_diagnostics.py`,
`application.py`, `mac_index.py`, `relationships/resolver.py`,
`enrichment_provider.py`, `discovery_engine.py`, `test_lldp_neighbor_provider.py`,
`test_snmp_client.py`, `test_discovery_engine.py`, `test_application_cli.py`.

---

## 1. Implementation Order (ARCH-024 Section 13)

1. `SnmpClient.get_bridge_fdb()` + its dataclasses + unit tests — isolable, no dependency on the provider. OID-suffix confirmation happens here, before anything else is written.
2. `SnmpBridgeFdbProvider` + its unit tests — depends on (1) and the already-shipped `build_mac_index()`/`receive_observations()`.
3. `application.py` wiring — depends on (2).
4. Three-provider integration test (ARP + LLDP + Bridge-FDB) — depends on (2) and the existing ARP/LLDP providers.
5. Full-suite validation.

No step is reordered or parallelized relative to ARCH-024's own sequencing.

---

## 2. New Files

| File | Contents | ARCH-024 justification |
|---|---|---|
| `networkmapper/discovery/bridge_fdb_provider.py` | `SnmpBridgeFdbProvider(EnrichmentProvider)`, `BRIDGE_FDB_CATEGORY = "bridge_fdb"` | Section 8: "a new provider class, not an extension of `SnmpArpNeighborProvider`/`SnmpLldpNeighborProvider`/`SnmpEnrichmentProvider`"; Section 9 New-files list; Section 5 names the category. |
| `networkmapper/discovery/snmp_bridge_fdb_diagnostics.py` | `SnmpBridgeFdbHostDiagnostics`, `SnmpBridgeFdbRunDiagnostics` | Section 8/9: "new diagnostics types, mirroring `snmp_arp_diagnostics.py`/`snmp_lldp_diagnostics.py`'s established shape." Kept as its own type, not generalized — Section 8 flags generalization as a "worthwhile but non-blocking refinement, not a requirement," so it is explicitly **not** attempted here (would be scope expansion). |
| `tests/test_bridge_fdb_provider.py` | Provider unit tests | Section 11 ("Unit/provider" strategy). |

### `SnmpClient.get_bridge_fdb()` and its dataclasses land in the existing `networkmapper/discovery/snmp_client.py`, not a new file — mirroring where `get_arp_table`/`get_lldp_neighbors` already live (Section 9: "`SnmpClient.get_bridge_fdb()` plus `SnmpBridgeFdbEntry`/`SnmpBridgeFdbResult` dataclasses **in `snmp_client.py`**").

Concrete shape, derived from Section 3/6/7's table structure (dot1dTpFdbTable's single-6-octet-MAC index — no composite key, unlike ARP's `(ifIndex, addressType, addressLength, address)` or LLDP's `(TimeMark, LocalPortNum, RemIndex)`):

- `SnmpBridgeFdbEntry(mac_address: str, port: int, status: str | None)` — `status` translated to a name (`"learned"/"self"/"mgmt"/"other"/"invalid"`, or `None` if unresolved), mirroring `SnmpArpTableEntry.entry_type`'s identical string-or-`None` shape via a new `_BRIDGE_FDB_STATUS_NAMES` dict (parallel to the existing `_ARP_ENTRY_TYPE_NAMES`).
- `SnmpBridgeFdbResult(responded: bool, entries: list[SnmpBridgeFdbEntry], failure_reason: str | None)` — same three-field shape as `SnmpArpTableResult`/`SnmpLldpTableResult`.
- `get_bridge_fdb(host, credentials, timeout, retries) -> SnmpBridgeFdbResult` on the abstract `SnmpClient` (raises `NotImplementedError`) and on `PysnmpClient` (the real `walk_cmd`-based implementation).
- Two column walks, joined by the MAC key parsed from each row's OID suffix — this mirrors `get_arp_table`'s exact two-column, load-bearing/best-effort shape (Section 7), not LLDP's eight-column shape, because Section 3 establishes Bridge-FDB's index is structurally simpler than either prior table:
  - `dot1dTpFdbPort` — **load-bearing** (Section 7: "without a MAC and a learning port, no usable row exists at all"). A failed walk fails the whole host, mirroring `get_arp_table`'s `PhysAddress` walk.
  - `dot1dTpFdbStatus` — **best-effort** (Section 7, corrected in the ARCH-024 review from an earlier draft that had this load-bearing). A failed status walk leaves `status=None` for every row but never fails the host.
- A new `_parse_bridge_fdb_row(oid_str, column_oid) -> str | None` helper — Section 8: "its own row-index parsing helper, since `dot1dTpFdbTable`'s single-6-octet-MAC index is a materially simpler shape than either prior table's composite index, not a reuse of either existing helper." Returns `None` (skip, not error) when the index does not yield exactly 6 octets each in `0–255` — mirroring `_parse_ipv4_arp_row`'s non-conforming-row treatment (Section 7: "malformed entries... skipped, not erroring").
- `BRIDGE_FDB_TABLE_MAX_ROWS` — a **new**, distinct constant, not a reuse of `ARP_TABLE_MAX_ROWS`/`LLDP_TABLE_MAX_ROWS`'s `10_000` (Section 7: "this provider should define its own constant, consciously chosen... rather than copied from a table plausibly an order of magnitude smaller in the realistic case"). **This plan does not fix its value** — Section 7 explicitly declines to fix it in the architecture itself, and no principled value can be derived from documentation alone. It is Step 1's own implementation-time decision, informed by uncertainty item 3 in Section 5 below.
- `dot1dBasePortTable` is **not** walked. `dot1dTpFdbPort` (a bridge-port number) is retained directly off `dot1dTpFdbTable` itself as a value column; its further mapping to `ifIndex` via `dot1dBasePortTable` is named only as unconsumed context (Section 5) and is not required to satisfy that retention — walking it would be scope beyond what Section 5/9 calls for.

---

## 3. Modified Files

*(Corrected: the original draft of this plan omitted three files it had already described changing in Section 7, and incorrectly claimed the list below to be "the entire modified-file list." That inconsistency was found and corrected before implementation began — the table below is the corrected, approved version.)*

| File | Change |
|---|---|
| `networkmapper/discovery/snmp_client.py` | Add `get_bridge_fdb()` (abstract + `PysnmpClient`), `SnmpBridgeFdbEntry`/`SnmpBridgeFdbResult`, `_BRIDGE_FDB_STATUS_NAMES`, `BRIDGE_FDB_TABLE_MAX_ROWS`, `_parse_bridge_fdb_row()`. |
| `networkmapper/application.py` | `--snmp-bridge-fdb` flag; credential gate extended to four flags; `fdb_provider` construction/list append; `_print_bridge_fdb_diagnostics()`. |
| `tests/test_snmp_client.py` | New `PysnmpClientBridgeFdbTest` class (§7.1). |
| `tests/test_discovery_engine.py` | Extend the existing stub-client integration pattern with a Bridge-FDB stub and provider (§7.3). |
| `tests/test_application_cli.py` | New CLI regression coverage for `--snmp-bridge-fdb` (§7.5). |

That is the full modified-file list.

---

## 4. Confirmed Unchanged (traced against current code, per ARCH-024 Section 9)

- **`DiscoveryEngine.discover()`** — already generic over any number of `EnrichmentProvider`s, already calls `receive_observations()` immediately before each one's `enrich()`. A fourth provider is registered in `application.py`'s list; the engine itself needs no change.
- **`EnrichmentProvider`** — `receive_observations()`/`collect_observations()` contracts already fit exactly what this provider needs; `SnmpBridgeFdbProvider` implements the same ABC, no interface change.
- **`build_mac_index()`** — reused unmodified; already generic over any `IdentityObservation` stream regardless of source.
- **`IdentityResolver`** / **`RelationshipResolver`** — both already generic over any observation a provider emits. `RelationshipResolver`'s existing self-loop exclusion (`observation.subject != observation.related_subject`) is confirmed present and serves as Section 6's named second line of defense for `self`(4) rows, with zero code change.
- **`Project`, `ProjectSerializer`, `CsvExporter`, `MarkdownExporter`** — unaffected; no new `Project` field, no new report content.
- **`NmapProvider`, `SnmpEnrichmentProvider`, `SnmpArpNeighborProvider`, `SnmpLldpNeighborProvider`** — untouched; the new provider is a sibling, never a modification of any of these.
- **`RelationshipObservation`, `IdentityObservation`, `ObservationProvenance`** dataclasses — no new field required; `category="bridge_fdb"` is just a new string value in the already-open `category` field (ADR-013's already-declined-to-freeze-taxonomy stance).

### Provider roles in the wider pipeline (clarifying note)

`NmapProvider` (unconditional, self-reported) and `SnmpArpNeighborProvider` (gated on
an already-discovered IP) are this codebase's `mac_address` **identity-evidence
producers** — together they populate the MAC-to-Subject Reverse Index that
`build_mac_index()` builds. `SnmpLldpNeighborProvider` and the new
`SnmpBridgeFdbProvider` are both pure **consumers** of that index — each resolves a
learned MAC against it via its own resolution path, and neither one ever produces
`mac_address` evidence itself. This distinction matters for Section 7.3 below, whose
own stub-based test exercises only the ARP side of that producer set.

---

## 5. Implementation-Time Uncertainties Requiring Live-Device Verification

1. **Exact numeric OID suffixes** for `dot1dTpFdbPort`/`dot1dTpFdbStatus` (and the `dot1dTp`/`dot1dBridge` branch root). ARCH-024 Section 3 deliberately withholds these — must be confirmed against the authoritative BRIDGE-MIB module text (RFC 4188) before Step 1's walk code is written, the same disclosed-risk class every prior SNMP table-walk sprint (ARP, LLDP) carried.
2. **`dot1dTpFdbTable`'s real-world VLAN-scoping yield across representative vendors** (Section 4) — ARCH-024's own named single-highest-value open question. A plain SNMPv2c walk against a real VLAN-segmented switch may return only one VLAN's worth of data. Recommended as a pre-implementation check against a small representative device sample, per Section 4's "mirroring ARCH-023 Section 13's identical pattern" — non-blocking, but should happen early (ideally before or during Step 1) so a near-empty real-world yield is understood as expected, not mistaken for a bug during Step 4/5 testing.
3. **Realistic FDB table sizes on representative access/aggregation switches** — needed to set `BRIDGE_FDB_TABLE_MAX_ROWS` (Section 7) to a considered value rather than an arbitrary guess. Section 7's 8,000–32,000+ range is explicitly disclosed as an illustrative, unverified estimate.
4. **Whether `lookupMib=False` positional OID-suffix parsing behaves as expected against a single-6-octet-MAC index on a real device** — the same class of walk-behavior uncertainty ARCH-020/ARCH-023 already flagged for their own tables (`snmp_client.py`'s `_walk_column` docstring), now applied to a third, structurally different index shape.
5. **Whether a real device's best-effort `dot1dTpFdbStatus` walk actually partial-fails independently of the load-bearing `dot1dTpFdbPort` walk** the way the ARP/LLDP precedent assumes — only verifiable against a live agent's actual behavior under adverse conditions.

None of these block writing the unit tests (which use an injected stub `SnmpClient`, per the existing pattern) — they block confidence that the real `PysnmpClient` implementation and the chosen scale constant are correct against actual hardware, and are recommended checks, not gates, per ARCH-024's own posture.

---

## 6. ADR Requirement

**No new ADR is required**, confirmed by re-checking ARCH-024 Section 10's per-decision list against this plan's own file/change list — every item in Sections 2-3 above is a direct, traceable application of already-accepted policy (ADR-010's `EnrichmentProvider` contract, ADR-013's open relationship-category taxonomy, ADR-012/013's reuse of `build_mac_index()`) or established implementation precedent (ARP/LLDP's provider shape, load-bearing/best-effort column split, own-scale-constant pattern).

One candidate trigger is named and **remains deliberately unreached by this plan**: VLAN-scoped SNMP access (Q-BRIDGE-MIB's `dot1qTpFdbTable` or the vendor-specific community-string-indexing workaround) would require extending `SnmpCredentials` beyond ARCH-012's version+community model — that is out of this plan's scope entirely (ARCH-024 Section 12), so the trigger is not reached, not silently resolved.

**Stop condition — approved exactly as follows:** if uncertainty #2 in Section 5 above (live VLAN-scoping yield) reveals that classic `dot1dTpFdbTable` returns so little real-world coverage on the project's actual MSP target hardware that Stage 1 as scoped is not worth shipping — that would be genuinely new evidence ARCH-024 did not have, and per this plan's own instruction not to expand scope unilaterally, the correct response is to stop, report the finding, and let engineering review decide whether to pursue the VLAN-aware ADR-trigger path — not to quietly widen this plan's scope to `dot1qTpFdbTable` mid-implementation.

---

## 7. Testing Strategy

### 7.1 Unit — `SnmpClient.get_bridge_fdb()`
New class in `tests/test_snmp_client.py`, mirroring `PysnmpClientArpTableTest`/`PysnmpClientLldpNeighborTest`:

- `test_successful_walk_joins_port_and_status_by_mac_index`
- One test per `dot1dTpFdbStatus` value: `test_learned_status_row`, `test_self_status_row`, `test_mgmt_status_row`, `test_invalid_status_row`, `test_other_status_row` — mirroring how LLDP tests each chassis-ID subtype individually.
- `test_a_malformed_row_index_not_six_octets_is_skipped`
- `test_port_walk_error_indication_is_reported_as_timeout` (load-bearing failure fails the whole host)
- `test_status_walk_failure_does_not_fail_the_whole_result` (best-effort — row retained with `status=None`)
- `test_zero_rows_is_a_legitimate_responded_result`
- `test_missing_bridge_mib_support_is_a_legitimate_responded_result`
- `test_unexpected_exception_never_propagates`

### 7.2 Unit/provider — `SnmpBridgeFdbProvider`
New `tests/test_bridge_fdb_provider.py`, mirroring `test_lldp_neighbor_provider.py`'s template:

- `test_learned_status_row_resolves_via_fed_mac_index`
- `test_ambiguous_mac_lookup_skips_the_row`
- `test_absent_mac_lookup_skips_the_row`
- `test_self_status_row_produces_no_observation_at_all` — a **full-exclusion** test, distinct in shape from ARP's own `test_an_undiscovered_row_produces_relationship_evidence_only` (partial gating): this proves Section 6's defense-in-depth produces *no* observation of either kind.
- `test_mgmt_status_row_produces_no_observation`
- `test_unresolved_status_row_produces_no_observation` (status walk failed at the client layer)
- `test_other_and_invalid_status_rows_produce_no_observation`
- `test_no_identity_observation_is_ever_emitted` — asserts the provider **never** emits an `IdentityObservation`, the one structural difference from both ARP and LLDP's own providers (Section 5).
- `test_device_fields_are_never_mutated`
- `test_an_empty_but_responded_table_produces_no_observations_but_no_error`
- `test_no_observation_when_the_host_times_out`
- `test_client_exception_is_caught_and_recorded_as_a_failure`
- `test_run_diagnostics_report_hard_counts`
- `test_observations_reset_between_enrich_calls`
- `test_no_observations_before_enrich_is_called`
- `test_telemetry_events_use_snmp_enrichment_phase_and_never_contain_the_community_string`
- `test_enrich_with_zero_devices_still_publishes_phase_events`

### 7.3 Integration — three-provider registration

*(Corrected before implementation: the original draft of this section implied `SnmpLldpNeighborProvider` might be "the other MAC-emitting provider" alongside ARP. It does not — `SnmpLldpNeighborProvider` only ever emits `hostname` identity evidence, never `mac_address`. The wording below is the corrected, approved version.)*

**ARP is the MAC-evidence producer in this stub-based engine-level test** (mirroring `DiscoveryEngineTwoProviderIntegrationTest`'s existing scope, which already isolates provider composition from real `NmapProvider` behavior — see Section 4's provider-roles note for the fuller picture including Nmap). `SnmpLldpNeighborProvider` and `SnmpBridgeFdbProvider` are both independent *consumers* of `build_mac_index()`'s output, resolving via two structurally distinct paths (LLDP's `macAddress` chassis-ID-subtype fallback; Bridge-FDB's `dot1dTpFdbTable` MAC-keyed rows) — neither produces MAC evidence itself, in this test or in the real pipeline.

Tests (new `_StubBridgeFdbSnmpClient`, extending `test_discovery_engine.py`'s existing `_StubArpSnmpClient`/`_StubLldpSnmpClient` pattern):
- `test_bridge_fdb_resolves_via_arp_contributed_mac_evidence_when_arp_runs_first`
- `test_bridge_fdb_produces_reduced_but_correct_output_when_it_runs_before_arp`
- `test_bridge_fdb_produces_correct_output_when_arp_is_absent_entirely`
- `test_lldp_and_bridge_fdb_both_resolve_independently_from_the_same_arp_contributed_mac_index` — the one genuinely new case: two independent consumers reading the same snapshot in one run, not a repeat of either provider's own pairwise test.

### 7.4 Live-network verification — explicitly separated, not part of the automated suite
- Confirm exact numeric OID suffixes against the authoritative BRIDGE-MIB module (Section 5, uncertainty #1) — a one-time check before Step 1's client code is trusted.
- Real-world VLAN-scoping yield across representative vendor devices (Section 5, uncertainty #2).
- Realistic FDB table sizes on representative switches (Section 5, uncertainty #3), to inform `BRIDGE_FDB_TABLE_MAX_ROWS`.

These three are tracked as manual/operational verification items, run against real lab or representative devices — never gating the automated unit/provider/integration suite.

### 7.5 CLI regression coverage — `tests/test_application_cli.py`

*(Added before implementation, as part of the same correction pass as Section 7.3, after auditing existing CLI test coverage.)*

`tests/test_application_cli.py` is the existing, appropriate mechanism for this layer — it already exercises the flag parser, the shared credential gate, provider composition via `enrichment_providers`, and diagnostics dispatch, for the `--snmp` flag specifically.

**Finding, recorded as approved context, not acted on beyond its own scope:** this file has no equivalent coverage for `--snmp-arp` or `--snmp-lldp` — a pre-existing gap from FEAT-010A/FEAT-012A, not something FEAT-012B introduces. This plan does not backfill that gap; it covers only `--snmp-bridge-fdb`, which needs coverage because it exercises the same four code paths as `--snmp` does and no existing test touches any of them for a fourth flag.

Required additions (extend the shared `_run_application` helper to patch/return `networkmapper.application.SnmpBridgeFdbProvider`, mirroring its existing `snmp_provider_mock` handling; then add):
- `test_snmp_bridge_fdb_flag_absent_by_default` — asserts `fdb_provider_mock` not called.
- `test_snmp_bridge_fdb_flag_without_community_env_var_exits_with_non_zero_code` — proves the shared gate now fires on this fourth flag too.
- `test_snmp_bridge_fdb_flag_with_community_env_var_enables_bridge_fdb_enrichment` — asserts `fdb_provider_mock` called with correct credentials, `enrichment_providers` contains it, diagnostics section prints, community string never leaks to stdout.
- `test_snmp_bridge_fdb_flag_absent_prints_no_bridge_fdb_diagnostics`
- `test_snmp_bridge_fdb_flag_combines_with_arp_and_lldp_flags` — passes all three table-walk flags together, asserts `enrichment_providers` contains all three provider mocks and all three diagnostics sections print — the one composition case no existing test covers even for the current two flags.

---

## 8. Scope Confirmation

This plan implements exactly ARCH-024 Section 9's file list and Section 4's Stage 1 boundary: classic `dot1dTpFdbTable` only, `learned`-status rows only, `RelationshipObservation` emission only. It does not implement, and no step above introduces: `dot1qTpFdbTable`/Q-BRIDGE-MIB VLAN coverage, the community-string-indexing workaround, `dot1dBasePortTable`-derived `Interface`/port modeling, `self`(4)-as-self-identity corroboration, spanning-tree state, any port-fan-out directness heuristic, CDP, or topology rendering — all explicitly named as out of scope in ARCH-024 Section 12 and reaffirmed here as excluded from FEAT-012B.
