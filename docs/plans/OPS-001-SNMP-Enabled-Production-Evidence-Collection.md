# Status

**Blocked.** OPS-001 must not run until its prerequisite, **FEAT-OBSERVATION-JSON-EXPORT**, has been implemented **and verified** (Section 2, D1).

Revision: architect rulings D1–D4 applied (Section 2). Collection has **not** been run.

Authority:
- [ARCH-026](../reports/ARCH-026-Gateway-Relationship-Evidence-Readiness.md): the current production dataset contains zero relationship observations and no deterministic gateway evidence. Recommends OPS-001.
- [ADR-013 Amendment 1](../ADR.md), [PLAN-028](PLAN-028-Relationship-Cardinality-Resolver-Support.md), FEAT-RELATIONSHIP-CARDINALITY (`7668763`) and [VER-028](../reports/VER-028-Relationship-Cardinality-Resolver-Support.md) (`11bd9d5`): resolver cardinality semantics are corrected and verified.

Baseline: `HEAD` `11bd9d5`. All code references are as of that commit.

Production Code Modified: No. This is an operations plan; the run will use the committed application unchanged, once the prerequisite FEAT has landed.

New ADR Required: Not by OPS-001 itself. The prerequisite FEAT must settle one ADR question before it is implemented (Section 13).

---

## 1. Purpose and Non-Goals

**Purpose.** Run the existing NetworkMapper application once against the production network with the three existing SNMP relationship providers enabled, and preserve **every retained observation** it collects. The run should answer, with measurements rather than bounds:
- whether production devices answer SNMP at all;
- how much `arp_neighbor`, `bridge_fdb` and `connected_to` evidence exists;
- whether that evidence resolves to canonical relationships between discovered devices.

The preserved observations must allow any future resolver to be re-run against this exact evidence.

**Non-goals (hard constraints):**
- No gateway provider, no `default_gateway` category, and no gateway inference of any kind, heuristic or otherwise.
- No topology rendering, layout or graph consumer.
- No classification rule changes, and no other code changes as part of OPS-001.
- No production credentials committed to the repository, written to any file, or copied into any report.
- No raw production artifacts committed (Section 11).
- No interpretation beyond what the committed resolvers produce. **Unknown or no evidence is an acceptable outcome**, and "SNMP did not respond" is a valid, reportable result.

---

## 2. Architect Rulings

### D1: Raw observations must be persisted before collection

**Ruling:** do not run OPS-001 until raw observations can be persisted. A prerequisite FEAT for observation JSON export is required.

**Canonical-only replay is insufficient** for NetworkMapper's evidence-first standard (ADR-011, ADR-012, ADR-013):
- `Project.observations` is never persisted (`ProjectSerializer` drops it, ARCH-019), and no exporter writes raw observations.
- Without an export, only *canonical* output survives a run, in `relationships.csv` and `report.md`.
- Observations whose endpoint was not discovered are removed at the resolver's endpoint gate, and so appear in **no** artifact. The only trace is aggregate counts in the console diagnostics.
- `source_run` and full-precision `observed_at` are not preserved anywhere.
- Canonical output is itself an *interpretation* (ADR-013). Keeping only interpretations means the evidence behind them cannot be re-interpreted: re-running a corrected resolver, for example after ARCH-027 Open Questions 2 and 6 are addressed, would be impossible for this run's evidence.

**Consequence:** OPS-001 is **blocked** until FEAT-OBSERVATION-JSON-EXPORT is implemented **and** verified by its own VER report (Section 14).

### D2: Exclude `--snmp`

**Ruling:** leave out `--snmp` if the relationship providers can run without mutating classification inputs. Classification must remain comparable to the baseline.

**The condition is met** (verified at `11bd9d5`):
- None of `SnmpArpNeighborProvider`, `SnmpLldpNeighborProvider` or `SnmpBridgeFdbProvider` writes any `Device` attribute.
- Each has a `test_device_fields_are_never_mutated` test (`tests/test_arp_neighbor_provider.py:165`, `tests/test_lldp_neighbor_provider.py:273`, `tests/test_bridge_fdb_provider.py:230`).
- `DiscoveryEngine` classifies devices only after enrichment completes.
- `--snmp` (`SnmpEnrichmentProvider`) *does* fill `Device` SNMP fields, which RULE-004 classification reads, so it is excluded.

With the relationship providers only, every classification input comes from nmap, exactly as in the baseline's nmap-only STANDARD run.

### D3: Explicit baseline subnets

**Ruling:** use explicit baseline subnets. Do not rely on auto-detection.

- The run passes the baseline's subnets explicitly with `--subnet`.
- The subnets are the distinct /24 networks present in the protected baseline dataset. They are derived **locally** (Section 6, step 3) into a gitignored targets file, so the private addresses are never written into this committed plan (D4).
- Auto-detection (`local_subnet.py`) is not used.

### D4: Sanitization of committed material

**Architect decision:** Committed reports may include aggregate counts, provider names, relationship categories, and sanitized stable host IDs only. Do not commit real hostnames, MACs, public IPs, serials, SNMP community strings, customer names, or raw production artifacts. Private production IPs remain local unless sanitized.

Section 11 applies this ruling, and this plan follows it: it names no production subnet, host, scanner or address.

---

## 3. Target Environment and Device Scope

| Item | Value |
|---|---|
| Network | The same production network as the protected baseline dataset (`output\Test Network.nmproj`, scanned 2026-09-04, 244 devices). `Test Network` is the project name hard-coded in `application.py`, not a customer name. |
| Subnets | `BASELINE_NET_1` … `BASELINE_NET_n`: the distinct /24 networks in the baseline dataset, derived locally (D3; Section 6, step 3). ARCH-026 found three. |
| Scan host | The same Windows scanner used for the baseline, attached directly to the scanned segment |
| Scan profile | `standard`, matching the baseline. **The CLI default is `fast`, so the flag is required.** |
| SNMP query scope | **Every discovered device.** The CLI has no host filter, so each SNMP provider queries all devices discovery returned ("Hosts Eligible"). All queries are read-only (Section 4.3). |
| Expected SNMP responders | Unknown, and that is what the run measures. Current classification has 6 L3-capable devices and 10 switches as the most likely candidates (ARCH-026 §8.1, RULE-011). |

---

## 4. Credential Handling and Safety

### 4.1 Credential handling

- **One source only.** NetworkMapper reads the community string solely from the `NETWORKMAPPER_SNMP_COMMUNITY` environment variable (`application.py:49`, `_resolve_snmp_credentials`). It supports **SNMPv2c only**. There is no command-line argument, config file or prompt.
- **Never typed literally on a command line.** PowerShell's PSReadLine saves typed commands to `ConsoleHost_history.txt`, and `Start-Transcript` records them. Use the `Read-Host -AsSecureString` sequence in Section 6, step 4.
- **Session-scoped only.** Set it in the single PowerShell session that runs the scan. Never set it machine-wide or user-wide, and never in a `.env` file.
- **Cleared immediately** after the run (Section 6, step 6).
- **Not printed by the application.** `SnmpCredentials.__repr__` masks the community as `'***'`, and no print, log or event path includes it (verified at `11bd9d5`). The post-run leak scan (Section 6, step 8) still checks this rather than assuming it, and the scan now **includes the observation JSON export**.
- **Read-only community only**, confirmed with the network owner.

### 4.2 Authorization and network-owner coordination (prerequisites)

- [ ] Written authorization from the network owner for an SNMP sweep of the baseline subnets, with the date and time window recorded (locally).
- [ ] The owner accepts that **SNMPv2c sends the community string in cleartext over UDP/161** on the local segment. Where possible, use a dedicated RO community restricted by ACL to the scanner.
- [ ] Monitoring staff are notified that agents may raise `authenticationFailure` traps or log entries, and that IDS/SIEM tools may flag a UDP/161 sweep.
- [ ] A rollback contact is named for the window.

### 4.3 Network-impact safety

- **Read-only.** `SnmpClient` uses only `get_cmd` and `walk_cmd`. There is no `SET` operation in the client (verified at `11bd9d5`).
- **Sequential, low rate.** Enrichment providers run one after another (`discovery_engine.py:82-103`), and each queries hosts serially, with a 1.5 s timeout and 1 retry.
- **Expected duration (worst case, beyond nmap STANDARD):** about 3.0 s per non-responding host per provider. For about 244 hosts × 3 providers that is **roughly 37 minutes**, plus walk time for responders.
- **No state change.** No configuration is pushed, and no device state is altered.

---

## 5. Providers and Expected Evidence

### 5.1 Providers that will run

| Provider | Flag | Runs? |
|---|---|---|
| `NmapProvider` (STANDARD), one per baseline subnet | `--scan-profile standard --subnet <BASELINE_NET_k>` | Yes |
| `SnmpArpNeighborProvider` | `--snmp-arp` | Yes |
| `SnmpLldpNeighborProvider` | `--snmp-lldp` | Yes |
| `SnmpBridgeFdbProvider` | `--snmp-bridge-fdb` | Yes |
| `SnmpEnrichmentProvider` (system group) | `--snmp` | **No** (D2) |

`DiscoveryEngine` passes each enrichment provider every observation collected so far (`receive_observations`) before it runs. The ARP provider's MAC identity observations therefore feed the MAC index that LLDP and FDB use.

### 5.2 Expected evidence

Once FEAT-OBSERVATION-JSON-EXPORT has landed, **every row below is preserved in the observation export**, including observations that never become canonical.

| Evidence | Emitted by | Becomes canonical when |
|---|---|---|
| Identity observations: `mac_address`, `hostname`, `computer_name`, `domain` | `NmapProvider` | Always (endpoint identities) |
| `mac_address` identity for ARP entries whose IP was discovered | `SnmpArpNeighborProvider` | Contributes to identity corroboration |
| LLDP `sysName` identity for discovered neighbors | `SnmpLldpNeighborProvider` | Contributes to identity corroboration |
| `arp_neighbor` (MULTIPLE): L3 device → each resolved IP | `SnmpArpNeighborProvider` (`ipNetToPhysicalTable`) | Both endpoints are discovered devices |
| `bridge_fdb` (MULTIPLE): switch → host owning a learned MAC | `SnmpBridgeFdbProvider` (`dot1dTpFdbTable`) | The MAC maps to exactly one discovered subject, and the row status is `learned` |
| `connected_to` (MULTIPLE): device → LLDP neighbor | `SnmpLldpNeighborProvider` (`lldpRemTable`) | The neighbor resolves to a discovered subject |

**Expected results, all acceptable:**
- **Zero SNMP responders,** giving zero relationship observations.
- **Some responders,** giving WEAK edges per category with no CONFLICTING (all three categories are MULTIPLE).
- **Rare CONFIRMED edges.** Any that appear are examined against ARCH-027 Open Question 6.

---

## 6. Exact Procedure (not to be run until unblocked)

Run all steps from the repository root in **one elevated PowerShell session**. Exact flags for the observation export are defined by FEAT-OBSERVATION-JSON-EXPORT, and **this section must be updated to match that FEAT before OPS-001 is approved to run.**

**Step 1: Pre-flight (the repository must be clean and green, and the prerequisite verified)**
```powershell
git rev-parse HEAD                        # record locally; must include FEAT-OBSERVATION-JSON-EXPORT and its VER report
git status --short                        # only review.diff / diff.md may appear; no code changes
python -m pytest tests/ -q                # all passing
python -m devtools validate --all         # PASS, all benchmarks 100.0%
nmap --version                            # record locally
```

**Step 2: Protect the existing baseline.** Every run **overwrites** `output\Test Network.nmproj`, and that file is the 244-device dataset ARCH-026 and the RULE replays depend on.
```powershell
New-Item -ItemType Directory -Force output\baselines | Out-Null
Copy-Item "output\Test Network.nmproj" "output\baselines\2026-09-04_Test-Network.nmproj"
Get-FileHash "output\Test Network.nmproj","output\baselines\2026-09-04_Test-Network.nmproj" -Algorithm SHA256
# The two hashes must match before continuing. Record the hash locally.
```

**Step 3: Derive the explicit baseline subnets locally (D3).** The result goes to a gitignored file and is never committed.
```powershell
New-Item -ItemType Directory -Force output\ops-001 | Out-Null
python -c "import json,ipaddress; d=json.load(open(r'output\baselines\2026-09-04_Test-Network.nmproj',encoding='utf-8'))['devices']; print('\n'.join(sorted({str(ipaddress.ip_network(x['ip_address']+'/24',strict=False)) for x in d})))" | Out-File -Encoding ascii output\ops-001\targets.local.txt
Get-Content output\ops-001\targets.local.txt   # operator confirms the list matches the authorized scope
$subnetArgs = Get-Content output\ops-001\targets.local.txt | ForEach-Object { "--subnet"; $_ }
```

**Step 4: Load the credential into this session only, without echoing or recording it.**
```powershell
$snmpSecure = Read-Host "SNMP read-only community" -AsSecureString
$env:NETWORKMAPPER_SNMP_COMMUNITY = [System.Net.NetworkCredential]::new('', $snmpSecure).Password
```

**Step 5: Run collection, capturing the console.** Add the observation-export flag here if FEAT-OBSERVATION-JSON-EXPORT introduces one.
```powershell
$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
python main.py --scan-profile standard @subnetArgs `
  --snmp-arp --snmp-lldp --snmp-bridge-fdb 2>&1 |
  Tee-Object -FilePath "output\ops-001\$stamp-console.log"
```
Do not use `Start-Transcript` for this session.

**Step 6: Clear the credential immediately, whatever the outcome.**
```powershell
Remove-Item Env:NETWORKMAPPER_SNMP_COMMUNITY -ErrorAction SilentlyContinue
Remove-Variable snmpSecure -ErrorAction SilentlyContinue
```

**Step 7: Preserve the artifacts (Section 7).**
```powershell
$run = Get-ChildItem output -Directory | Where-Object Name -like "*_standard" | Sort-Object Name | Select-Object -Last 1
Copy-Item "output\Test Network.nmproj" "$($run.FullName)\Test Network.nmproj"
Copy-Item "output\ops-001\$stamp-console.log" "$($run.FullName)\console.log"
Get-FileHash "$($run.FullName)\*" -Algorithm SHA256 | Format-Table -AutoSize | Out-File "$($run.FullName)\SHA256SUMS.txt"
```

**Step 8: Credential leak scan over every artifact, including the observation export.** Only a match count is printed.
```powershell
$check = [System.Net.NetworkCredential]::new('', (Read-Host "Re-enter community for leak scan" -AsSecureString)).Password
(Select-String -Path "$($run.FullName)\*","output\ops-001\*" -SimpleMatch -Pattern $check | Measure-Object).Count   # must be 0
Remove-Variable check
```

**Step 9: Replay check (D1).** Load the observation export, run the committed `IdentityResolver` and `RelationshipResolver`, and confirm the result reproduces the run's canonical identities and `relationships.csv` exactly. The exact replay command is defined by FEAT-OBSERVATION-JSON-EXPORT.

**Step 10: Post-run integrity.**
```powershell
git status --short                        # still no code changes
git rev-parse HEAD                        # unchanged from step 1
```

---

## 7. Artifacts to Preserve (local only)

All artifacts stay under `output\`, which is gitignored. **None is committed** (D4).

| Artifact | Location | Content |
|---|---|---|
| Baseline backup | `output\baselines\2026-09-04_Test-Network.nmproj` | The pre-run 244-device dataset, with a matching SHA-256 recorded locally |
| Targets file | `output\ops-001\targets.local.txt` | The explicit baseline subnets used (D3) |
| **Observation export** | `output\<run>\` (file name set by the FEAT) | **Every retained observation** (identity and relationship) with full provenance: provider, collection method, `observed_at`, `source_run`. The primary replay artifact (D1). |
| Run report | `output\<run>\report.md` | Device inventory plus the canonical identity and relationship sections |
| Device CSV | `output\<run>\devices.csv` | One row per device |
| Relationship CSV | `output\<run>\relationships.csv` | One row per canonical edge, header unchanged |
| Project file | `output\<run>\Test Network.nmproj` | A copy of the run's device data |
| Console log | `output\<run>\console.log` | Discovery and SNMP/ARP/LLDP/FDB diagnostics |
| Checksums | `output\<run>\SHA256SUMS.txt` | Integrity of the files above |
| Run manifest | Kept locally with the artifacts. Only the sanitized fields in Section 11 go into the committed results report. | Commit, nmap version, operator, date and time window, command line (no credential), provider flags |

---

## 8. Success Criteria

All of the following must hold:

1. **The prerequisite is in place.** FEAT-OBSERVATION-JSON-EXPORT is implemented and verified, and `HEAD` at step 1 includes both.
2. **The run completes.** The process exits normally, prints "Persistence validation successful", and writes all report files plus the observation export to a new run directory.
3. **The providers actually ran.** The console log contains ARP Neighbor, LLDP and Bridge FDB diagnostics blocks, each with `Hosts Queried` equal to `Hosts Eligible`.
4. **Observations are retained.** The export contains every retained observation, identity and relationship, including relationship observations whose endpoints did not resolve. Relationship observations are present if any provider collected entries. If none did, the zero result is recorded with each provider's timeout counts; **zero is a valid outcome.**
5. **Resolver replay is exact.** Running the committed `IdentityResolver` and `RelationshipResolver` on the export reproduces the run's canonical identities and `relationships.csv` exactly (Section 6, step 9).
6. **No false conflicts.** No canonical relationship has state `conflicting`.
7. **No gateway inference.** No `default_gateway` category appears in any artifact; the categories are a subset of {`arp_neighbor`, `bridge_fdb`, `connected_to`}. `HEAD` and the working-tree code are unchanged before and after.
8. **No credential exposure.** The leak scan finds 0 matches across every artifact, including the export, and the credential variable is cleared.
9. **The baseline is protected.** The baseline backup's hash equals the pre-run hash of `output\Test Network.nmproj`.
10. **Classification stays comparable (D2).** No classification code changed, `--snmp` was not used, and all classification inputs came from nmap. Device-type differences from the 2026-09-04 dataset are expected: the network has changed and RULE-008 to RULE-011 have landed since. They are reported as aggregate counts, not treated as failures.

---

## 9. Failure Criteria, Rollback and No-Op Behavior

| Condition | Effect | Action |
|---|---|---|
| Prerequisite FEAT not implemented or not verified | **OPS-001 does not start.** | No-op. |
| Credential variable unset | The application exits with code 2 at startup, **before any scanning**. Nothing is written. | Fix the setup and restart from step 4. |
| All SNMP queries time out | **Not a failure.** It is a valid finding. | Record and report it. Do not retry with guessed communities. |
| Nmap fails or finds no hosts | No meaningful output | Abort. Delete the partial run directory. Restore `output\Test Network.nmproj` from the baseline backup. |
| Run interrupted midway | Partial or no artifacts | Clear the credential. Delete the partial run directory. Confirm `output\Test Network.nmproj` still matches the baseline hash, and restore it if not. |
| "Persistence validation FAILED" | `RuntimeError` | Treat the run as failed. Keep the run directory for diagnosis. Restore the baseline `.nmproj`. |
| Observation export missing, or replay does not reproduce the canonical output exactly | D1 not satisfied | Mark OPS-001 FAIL. Keep the artifacts locally for diagnosis. Fix through a FEAT before any re-run. |
| **Leak scan finds the credential in any artifact** | **Stop.** | Delete every affected artifact, including copies. Notify the network owner so the community can be rotated. Record the incident (without the value) in the results report. Fix the leak path through a separate FEAT before any re-run. |
| `default_gateway`, a CONFLICTING relationship, or any code change detected | A constraint has been violated. | Mark OPS-001 FAIL and investigate before any use of the data. |
| Network owner reports impact | — | Stop the run (Ctrl+C), clear the credential, and follow the interrupted-run row. |

**Rollback scope.** SNMP access is read-only and nmap sends probes only, so nothing on the network needs rolling back. Local rollback is limited to restoring `output\Test Network.nmproj` from `output\baselines\` and deleting partial run directories. The repository is never modified by this procedure.

---

## 10. Proposed Post-Collection Report

After a successful run, write `docs/reports/OPS-001-SNMP-Production-Evidence-Collection-Results.md`. It must follow Section 11 strictly and needs architect approval before commit. It should contain:

1. **Sanitized run manifest:** commit, nmap version, date, scan profile, provider flags, the number of subnets scanned (not their addresses), and the observation-export format version.
2. **Success and failure criteria:** each Section 8 criterion checked, with evidence.
3. **Discovery summary:** aggregate host counts, compared with the 244-device baseline's aggregate count.
4. **SNMP reachability per provider:** hosts eligible, queried, responded and timed out, plus total entries collected.
5. **Relationship evidence by category:** observations retained compared with canonical edges, with the drop-off explained (undiscovered endpoints, ambiguous MACs, unresolvable chassis IDs). The export makes this measurable for the first time.
6. **Corroboration state distribution:** WEAK, CONFIRMED and CONFLICTING (expected 0).
7. **Fan-out sizes:** a distribution of edges per subject, per category, using sanitized host IDs where individual subjects must be referenced, compared with ARCH-026 §7's bounds.
8. **Known-behavior occurrences:** ARCH-027 Open Questions 2 and 6.
9. **ARCH-026 §8.3 (flat segment) revisited:** reported as aggregate evidence only, with **no gateway conclusion**.
10. **Replay result:** confirmation that resolver replay from the export reproduced the canonical output exactly.
11. **Aggregate classification note:** device-type counts compared with the baseline's counts.
12. **Credential leak scan result**, plus confirmation that no artifacts were committed.
13. **Recommendation:** what the evidence supports next. Topology and gateway work stay out of scope unless the evidence and a new ADR justify them.

---

## 11. Sanitization and Redaction Policy (architect decision D4)

> **Architect decision (D4):** Committed reports may include aggregate counts, provider names, relationship categories, and sanitized stable host IDs only. Do not commit real hostnames, MACs, public IPs, serials, SNMP community strings, customer names, or raw production artifacts. Private production IPs remain local unless sanitized.

**Applying it:**

| Data | In committed material |
|---|---|
| Aggregate counts and state distributions | Allowed |
| Provider names (for example `SnmpArpNeighborProvider`, `snmp`, `ipNetToPhysicalTable`) | Allowed |
| Relationship categories (`arp_neighbor`, `bridge_fdb`, `connected_to`) | Allowed |
| Sanitized stable host IDs | Allowed: the only permitted way to refer to an individual host |
| Hostnames, MAC addresses, serials | **Prohibited** |
| Public IPs | **Prohibited** |
| Private production IPs and subnets | **Local only**, unless replaced by sanitized host IDs or placeholder names (`BASELINE_NET_k`) |
| SNMP community strings, or any secret in any form | **Prohibited** |
| Customer names | **Prohibited** (`Test Network`, the application's hard-coded project name, is not a customer name) |
| Raw production artifacts (`.nmproj`, CSVs, `report.md`, console logs, the observation export, the targets file) | **Prohibited.** They stay in gitignored `output\`. |

**Sanitized stable host IDs.** These are the proposed convention and need architect confirmation:
- **Format:** `host-` followed by the first 8 hex characters of HMAC-SHA256(local salt, raw subject), for example `host-3f9a2c1e`.
- **The salt** is a random value generated once, stored only in gitignored `output\ops-001\`, and never committed. IDs therefore stay stable across this run's reports and any later replay that uses the same salt, but cannot be reversed or recomputed from public information.
- **Collisions** among 8-hex IDs are checked when the report is generated. If any occur, extend that report's IDs to 12 characters.

**Retroactive scope.** Earlier committed reports (for example ARCH-026 and the RULE reports) contain private production IPs and some hostnames. D4 governs material committed from now on. Whether to sanitize earlier reports retroactively is a separate decision and is **not** part of OPS-001.

---

## 12. Constraints Retained from the Original Draft

- Baseline backup and hash protection (Section 6, step 2; Section 8, criterion 9).
- Credential handling and leak scan (Section 4.1; Section 6, steps 4, 6 and 8; Section 8, criterion 8).
- Explicit subnet selection with no auto-detection (D3; Section 6, step 3).
- No gateway inference, no topology rendering, no classification rule changes, and no committed credentials or raw production artifacts (Section 1; D4).

---

## 13. Open Questions for the Architect

1. **The ADR question for the prerequisite FEAT.** ADR-011 and ADR-013 both list observation *persistence* and *storage design* as deferred, unauthorized work. Is a run-scoped, write-once observation export that is never loaded back into `Project` (only into a replay harness) within existing authority, or does it need an ADR-011 amendment first? This must be answered in the FEAT's plan before implementation.
2. Confirm the sanitized-host-ID convention (Section 11).
3. Is the roughly 37-minute worst-case SNMP sweep acceptable within the network owner's window? Restricting queries to infrastructure would need a host filter, which is a code change and out of scope.

---

## 14. Proposed Next Sprint: FEAT-OBSERVATION-JSON-EXPORT

This sprint unblocks OPS-001. It is **narrowly scoped to persisting retained observations so they can be replayed.**

**In scope:**
- **Export.** Write every observation in `engine.observations` (`IdentityObservation` and `RelationshipObservation`) to a JSON artifact in the run's report directory, alongside `report.md`, `devices.csv` and `relationships.csv`.
- **Lossless contents.** For each observation: its type; `subject`; `property_name` and `value` (identity) or `related_subject` and `category` (relationship); and full provenance, meaning `provider`, `collection_method`, `observed_at` as a full-precision ISO-8601 string, and `source_run`.
- **Deterministic and versioned.** A stable sort order, plus a top-level format version field.
- **A loader for replay only.** It reconstructs the observation objects so the committed `IdentityResolver` and `RelationshipResolver` can be re-run on them.
- **Tests:**
  - lossless round trip (export, then load, compares equal);
  - deterministic output;
  - replay reproduces `canonical_identities` and `canonical_relationships` exactly, including relationship observations whose endpoints do not resolve, which must be retained in the export;
  - the export never contains SNMP credentials (`SnmpCredentials` is never an observation input).

**Out of scope:**
- Changes to `ProjectSerializer` or the `.nmproj` format.
- Loading observations back into `Project` or into a future run.
- Cross-run corroboration.
- Any change to providers, resolvers, classification, the CSV or Markdown exporters, or the relationship categories.
- Any gateway, topology or heuristic work.

**Gate.** The ADR question in Section 13, item 1, must be settled first. FEAT-OBSERVATION-JSON-EXPORT must then be implemented, pass the full validation gate, and be **verified by its own VER report** before OPS-001 can be unblocked. After it lands, update Section 6 (steps 5 and 9) with the FEAT's actual flag and replay command, and resubmit OPS-001 for approval to run.
