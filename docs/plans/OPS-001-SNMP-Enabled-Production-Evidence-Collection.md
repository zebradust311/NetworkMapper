# Status

**Closed, not executed; no production evidence collected.**

Outcome: see [OPS-001 Results](../reports/OPS-001-SNMP-Production-Evidence-Collection-Results.md). Authorized for one collection run on 2026-10-19. Launches 1–4 stopped before collection. No collection evidence was found for launches 5–6; their termination remains unconfirmed. The operator reported that SNMP is not enabled on any production device. The project owner closed OPS-001. The procedure below is retained unchanged as the historical record.

Revision: procedure revised against `84492b7` to the implemented observation export, the replay command and the ARCH-029 replay-verification ruling. Architect rulings D1–D4 (Section 2) still apply. Collection has **not** been run.

Amendment (after `897884a`): step 3 now states the operator scope confirmation as an explicit gate. It accepts only the complete word `YES`, ignoring case and surrounding whitespace. No other step changed.

Authority:
- [ARCH-026](../reports/ARCH-026-Gateway-Relationship-Evidence-Readiness.md): the current production dataset contains zero relationship observations and no deterministic gateway evidence. Recommends OPS-001.
- [ADR-013 Amendment 1](../ADR.md), [PLAN-028](PLAN-028-Relationship-Cardinality-Resolver-Support.md), FEAT-RELATIONSHIP-CARDINALITY (`7668763`) and [VER-028](../reports/VER-028-Relationship-Cardinality-Resolver-Support.md) (`11bd9d5`): resolver cardinality semantics are corrected and verified.
- [ADR-011 Amendment 1](../ADR.md) (`84153e0`), [PLAN-029](PLAN-029-Observation-JSON-Export.md) (`7184256`) and [VER-029](../reports/VER-029-Observation-JSON-Export.md): the replay observation export, its replay command and their verification.
- [ARCH-029](../reports/ARCH-029-Inventory-Mapping-Reporting-Capability-Boundaries.md) (`84492b7`), Section 9: the architect ruling that scopes the endpoint-gate exclusion analysis in Appendix A.

Baseline: `HEAD` `84492b710404f23e0335ae3306c3f4a2b1999f0c`. All code references are as of that commit.

Production Code Modified: No. This is an operations plan. The run uses the committed application unchanged.

New ADR Required: No. ADR-011 Amendment 1 settled the question this plan previously left open (Section 13).

---

## 0. Prerequisite History and Execution Baseline

| Commit | What it established |
|---|---|
| `84153e0` | ADR-011 Amendment 1: a per-run replay artifact is authorized |
| `7184256` | PLAN-029 approved |
| `e12b81a` | FEAT-OBSERVATION-JSON-EXPORT: `observations.json` written on every run; `python -m devtools replay-observations <run_dir>` |
| `97b22e7` | Identity observation tie ordering made deterministic, so replay reproduces canonical identities exactly (ADR-011 Amendment 1, Decision 6) |
| `cd1a53d` | VER-029: the feature verified at `97b22e7`; `source_run` regression tests added |
| `84492b7` | ARCH-029: capability boundaries, and the replay-verification ruling for endpoint-gate analysis |

**Execution baseline (pinned).** The application code at execution time must be identical to `84492b7` in every path that affects collection, reporting or replay:
- `networkmapper/`
- `devtools/`
- `main.py`
- `requirements.txt`

Documentation-only commits after `84492b7`, including the commit of this revision, do not change the baseline.

Step 1 checks this mechanically. If any of those paths differs from `84492b7`, **OPS-001 stops and must be re-reviewed** before it runs, even if the change looks unrelated. Capability work proposed in ARCH-029 would fall under this rule.

---

## 1. Purpose and Non-Goals

**Purpose.** Run the existing NetworkMapper application once against the production network with the three existing SNMP relationship providers enabled, and preserve **every retained observation** it collects. Within the evidence that run collects, measure:
- whether production devices answer SNMP at all;
- how much `arp_neighbor`, `bridge_fdb` and `connected_to` evidence exists;
- how much of that evidence resolves to canonical relationships, and why the rest does not (Appendix A).

The preserved observations must allow the committed resolvers to be replayed against this exact evidence.

**Non-goals (hard constraints):**
- No gateway provider, no `default_gateway` category, and no gateway inference of any kind, heuristic or otherwise.
- No topology rendering, layout or graph consumer.
- No physical-connectivity claims.
  - `arp_neighbor` claims L3 cache knowledge.
  - `bridge_fdb` claims L2 reachability through a port.
  - `connected_to` claims LLDP protocol adjacency.
  - A `CONFIRMED` state means independent sources agree; it does not mean a physical link exists (ARCH-029 Section 6.2).
- No claim of complete network coverage. The run sees only what host discovery found and what queried devices reported.
- No classification rule changes, and no code changes as part of OPS-001.
- No production credentials committed to the repository, written to any file, or copied into any report.
- No raw production artifacts committed (Section 11).
- No interpretation beyond what the committed resolvers produce. **Unknown or no evidence is an acceptable outcome**, and "SNMP did not respond" is a valid, reportable result.

---

## 2. Architect Rulings

### D1: Raw observations must be persisted before collection

**Ruling (unchanged):** do not run OPS-001 until raw observations can be persisted, and verified.

**Status: satisfied.** `e12b81a` writes `observations.json` on every run. `97b22e7` makes identity replay exact. VER-029 (`cd1a53d`) verified both. The artifact keeps every retained observation, including those whose endpoints never resolve, with full provenance (`provider`, `collection_method`, `observed_at`, `source_run`).

### D2: Exclude `--snmp`

**Ruling (unchanged):** leave out `--snmp` if the relationship providers can run without mutating classification inputs. Classification must remain comparable to the baseline.

**The condition is still met** at `84492b7`. None of `SnmpArpNeighborProvider`, `SnmpLldpNeighborProvider` or `SnmpBridgeFdbProvider` writes any `Device` attribute. `DiscoveryEngine` classifies only after enrichment completes (`discovery_engine.py:100-107`). `--snmp` (`SnmpEnrichmentProvider`) fills `Device` SNMP fields that classification reads, so it stays excluded.

### D3: Explicit baseline subnets

**Ruling (unchanged):** use explicit baseline subnets, derived locally into a gitignored targets file. Do not rely on auto-detection.

### D4: Sanitization of committed material

**Architect decision (unchanged):** Committed reports may include aggregate counts, provider names, relationship categories, and sanitized stable host IDs only. Do not commit real hostnames, MACs, public IPs, serials, SNMP community strings, customer names, or raw production artifacts. Private production IPs remain local unless sanitized.

Section 11 applies this ruling. This plan names no production subnet, host, scanner or address.

---

## 3. Target Environment and Device Scope

| Item | Value |
|---|---|
| Network | The same production network as the protected baseline dataset (`output\Test Network.nmproj`, scanned 2026-09-04, 244 devices). `Test Network` is the project name hard-coded in `application.py:198`, not a customer name. |
| Subnets | `BASELINE_NET_1` … `BASELINE_NET_n`: the distinct /24 networks in the baseline dataset, derived locally (D3; step 3). ARCH-026 found three. |
| Scan host | The same Windows scanner used for the baseline, attached directly to the scanned segment |
| Scan profile | `standard`, matching the baseline. **The CLI default is `fast` (`application.py:77`), so the flag is required.** |
| SNMP query scope | **Every discovered device.** The CLI has no host filter, so each relationship provider queries all devices discovery returned ("Hosts Eligible"). All queries are read-only (Section 4.3). |
| Expected SNMP responders | Unknown, and that is what the run measures. |

---

## 4. Credential Handling and Safety

### 4.1 Credential handling

- **One source only.** The community string is read solely from the `NETWORKMAPPER_SNMP_COMMUNITY` environment variable (`application.py:50`, `_resolve_snmp_credentials`). **SNMPv2c only.** There is no command-line argument, config file or prompt.
- **Fail-fast if missing.** If any SNMP flag is passed and the variable is unset, the application exits with code 2 before scanning (`application.py:383-391`).
- **Never typed literally on a command line.** PowerShell's PSReadLine saves typed commands to `ConsoleHost_history.txt`, and `Start-Transcript` records them. Use the `Read-Host -AsSecureString` sequence in step 4. An empty entry stops the procedure.
- **Session-scoped only.** Set it in the single PowerShell session that runs the scan. Never set it machine-wide or user-wide, and never in a `.env` file.
- **Confined to a `try/finally`** (step 4). The `finally` block clears the variable and the session copies of the secret whether collection succeeds, fails or is interrupted.
- **Not printed by the application.** `SnmpCredentials.__repr__` masks the community as `'***'`. VER-029 verified that a sentinel community never reaches `observations.json`. The post-run leak scan (step 6) still checks every artifact rather than assuming it, and fails closed.
- **Read-only community only**, confirmed with the network owner.

### 4.2 Authorization and network-owner coordination (prerequisites)

- [ ] Written authorization from the network owner for an SNMP sweep of the baseline subnets, with the date and time window recorded locally.
- [ ] The owner accepts that **SNMPv2c sends the community string in cleartext over UDP/161** on the local segment. Where possible, use a dedicated RO community restricted by ACL to the scanner.
- [ ] Monitoring staff are notified that agents may raise `authenticationFailure` traps or log entries, and that IDS/SIEM tools may flag a UDP/161 sweep.
- [ ] A rollback contact is named for the window.
- [ ] **Owner approval of this revised procedure, including Appendix A.**

### 4.3 Network-impact safety

- **Read-only.** `SnmpClient` uses only `get_cmd` and `walk_cmd`; there is no `SET` operation.
- **Sequential, low rate.** Enrichment providers run one after another, and each queries hosts serially with a 1.5 s timeout and 1 retry (`arp_neighbor_provider.py:66-67`, `lldp_neighbor_provider.py:89-90`, `bridge_fdb_provider.py:80-81`).
- **Approximate duration, beyond nmap STANDARD.** Two parts:
  - **Non-responder timeout budget.** For each provider, a host that does not answer costs roughly one timed-out walk: about timeout × (1 + retries) ≈ 1.5 s × 2 ≈ 3 s. Each provider returns early when its first walk fails (`snmp_client.py:476-484`, `534-543`, `723-731`). The budget is therefore about 3 providers × 3 s × the number of non-responding hosts. If all of roughly 244 eligible hosts were non-responders, that would be about 37 minutes.
  - **Responder walk time, additional and unmeasured.** It grows with ARP-cache, LLDP and forwarding-table sizes. LLDP alone issues up to ten table walks per responding host.

  Both figures are approximations, not measurements.
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

`DiscoveryEngine` passes each enrichment provider every observation collected so far before it runs. The ARP provider's MAC identity observations therefore feed the MAC index that LLDP and FDB use.

### 5.2 Expected evidence

Every row below is preserved in `observations.json`, including observations that never become canonical.

| Evidence | Emitted by | Becomes a canonical edge when |
|---|---|---|
| Identity observations: `mac_address`, `hostname`, `computer_name`, `domain` | `NmapProvider` | — (they create canonical identities) |
| `mac_address` identity for ARP entries whose IP was discovered | `SnmpArpNeighborProvider` | — (contributes to identity corroboration) |
| LLDP `sysName` identity for discovered neighbors | `SnmpLldpNeighborProvider` | — (contributes to identity corroboration) |
| `arp_neighbor` (MULTIPLE): L3 device → each IP in its ARP cache | `SnmpArpNeighborProvider` (`ipNetToPhysicalTable`) | Both endpoints have a canonical identity, and they differ |
| `bridge_fdb` (MULTIPLE): switch → host owning a learned MAC | `SnmpBridgeFdbProvider` (`dot1dTpFdbTable`) | The MAC maps to exactly one subject, the row status is `learned`, and both endpoints have a canonical identity |
| `connected_to` (MULTIPLE): device → LLDP neighbor | `SnmpLldpNeighborProvider` (`lldpRemTable`) | The neighbor resolves to a subject, and both endpoints have a canonical identity |

**Identity, not discovery, gates an edge.** A canonical identity exists only for a subject with at least one identity observation. A discovered device with no observed identity value has no canonical identity, and its edges are excluded (ARCH-029 Section 3.2). Appendix A measures this.

**All outcomes below are acceptable findings:**
- **Zero SNMP responders,** giving zero relationship observations.
- **Some responders,** giving WEAK edges per category with no CONFLICTING (all three categories are MULTIPLE).
- **Rare CONFIRMED edges.** Any that appear are examined against ARCH-027 Open Question 6.

---

## 6. Exact Procedure (not to be run until approved)

Run all steps from the repository root in **one elevated PowerShell session** (Windows PowerShell 5.1). Do not use `Start-Transcript` in this session. Keep `$ErrorActionPreference` at its default (`Continue`): under `Stop`, Windows PowerShell 5.1 turns a native command's stderr output into a terminating error. Every check below stops the procedure explicitly with `throw` instead.

The hidden `ps:` markers before the code blocks identify the blocks the synthetic control-flow validation exercised (Appendix B).

**Step 1: Pre-flight.** Every check stops the procedure on failure.

<!-- ps:preflight -->
```powershell
$pin = "84492b710404f23e0335ae3306c3f4a2b1999f0c"
$pinned = @("networkmapper", "devtools", "main.py", "requirements.txt")
$allowedOutside = @("review.diff", "diff.md")          # known, unrelated, never part of a run

$head = (git rev-parse HEAD).Trim()                      # record locally

# 1. Committed application code equals the pinned baseline.
git diff --quiet $pin HEAD -- @pinned
if ($LASTEXITCODE -ne 0) { throw "STOP: committed application code differs from the pinned baseline; OPS-001 needs re-review" }

# 2. No staged, unstaged or untracked change anywhere in the pinned paths.
$pinnedChanges = @(git status --porcelain --untracked-files=all -- @pinned)
if ($pinnedChanges.Count -gt 0) { throw "STOP: $($pinnedChanges.Count) staged, unstaged or untracked change(s) in pinned paths" }

# 3. Nothing else changed in the working tree except the known unrelated files.
$otherChanges = @(git status --porcelain --untracked-files=all |
  ForEach-Object { $_.Substring(3).Trim('"') } |
  Where-Object { $allowedOutside -notcontains $_ })
if ($otherChanges.Count -gt 0) { throw "STOP: $($otherChanges.Count) unexpected working-tree change(s) outside the pinned paths" }

# 4. Every local operational location is actually gitignored.
foreach ($probe in "output/ops-001/probe.txt", "output/baselines/probe.nmproj", "output/0000-00-00_000000_standard/observations.json", "output/Test Network.nmproj") {
  git check-ignore -q -- $probe
  if ($LASTEXITCODE -ne 0) { throw "STOP: $probe is not gitignored" }
}

# 5. Tests and validation pass.
python -m pytest tests/ -q
if ($LASTEXITCODE -ne 0) { throw "STOP: pytest failed" }
python -m devtools validate --all
if ($LASTEXITCODE -ne 0) { throw "STOP: python -m devtools validate --all failed" }

# 6. Tools and console encoding. application.py prints "✓" after writing the report
#    artifacts; piped (step 4) without this setting, Python on Windows encodes as
#    cp1252, raises UnicodeEncodeError on "✓", and the run aborts before the .nmproj save.
nmap --version                                           # record locally
if ($LASTEXITCODE -ne 0) { throw "STOP: nmap is not available" }
$env:PYTHONIOENCODING = "utf-8"
python -c "print(chr(0x2713) + ' encoding ok')" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "STOP: console encoding check failed" }
```

**Step 2: Protect the historical baseline.** Every run **overwrites** `output\Test Network.nmproj` (`application.py:268`). That file is meant to be the 2026-09-04, 244-device dataset that ARCH-026 and the RULE replays depend on.

**Copying proves a copy, not history.** A matching source-and-copy hash proves only that the copy is faithful. It does **not** prove that the source is the historical dataset. Historical identity needs a SHA-256 recorded independently, at or near the time of the 2026-09-04 scan, outside this procedure.

The repository records no such hash (checked at `84492b7`). Until one is supplied, or the owner explicitly waives the requirement, step 2 stops (Section 13, item 5). An existing backup is never overwritten.

<!-- ps:baseline -->
```powershell
$source = "output\Test Network.nmproj"
$backup = "output\baselines\2026-09-04_Test-Network.nmproj"
$historicalHash = ""          # operator: the independently recorded SHA-256, if one exists
$historicalWaiver = $false    # operator: $true only with the owner's written waiver (Section 13, item 5)

if (-not (Test-Path -LiteralPath $source)) { throw "STOP: $source is missing" }
New-Item -ItemType Directory -Force output\baselines | Out-Null
$sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash

if (Test-Path -LiteralPath $backup) {
  # Never overwrite an existing backup. It must match the current source.
  $backupHash = (Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash
  if ($backupHash -ne $sourceHash) { throw "STOP: existing backup differs from $source; resolve which is historical before continuing" }
} else {
  Copy-Item -LiteralPath $source -Destination $backup
  $backupHash = (Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash
  if ($backupHash -ne $sourceHash) { throw "STOP: backup copy does not match its source" }
}

if (-not [string]::IsNullOrWhiteSpace($historicalHash)) {
  if ($sourceHash -ne $historicalHash.Trim().ToUpperInvariant()) { throw "STOP: $source is not the independently recorded historical dataset" }
  $historicalIdentity = "established by independent hash"
} elseif ($historicalWaiver) {
  $historicalIdentity = "NOT established; owner waiver recorded"
} else {
  throw "STOP: historical identity of $source cannot be established (no independent hash, no owner waiver)"
}
$baselineHash = $sourceHash                              # record locally, with $historicalIdentity
```

**Restoring the baseline.** Section 9 and steps 4 and 7 use this:

<!-- ps:restore -->
```powershell
Copy-Item -LiteralPath $backup -Destination $source -Force
if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $baselineHash) { throw "STOP: restored file does not match the baseline hash" }
```

**What baseline protection does and does not mean.**
- It preserves the *historical* dataset byte for byte.
- It does **not** imply that the new live scan should reproduce the baseline's devices or classifications. The network has changed since 2026-09-04, and classification rules RULE-008 to RULE-011 have landed since.
- Device and classification differences between the two are expected findings, reported as aggregate counts, never treated as failures.

**Step 3: Derive the explicit baseline subnets locally (D3).** The result goes to a gitignored file and is never committed.

The operator confirms the listed subnets match the authorized scope. Only the complete word `YES` continues, in any letter case and with surrounding whitespace ignored. Empty input, whitespace only, `y` or any other answer stops the procedure.

<!-- ps:targets -->
```powershell
New-Item -ItemType Directory -Force output\ops-001 | Out-Null
python -c "import json,ipaddress; d=json.load(open(r'output\baselines\2026-09-04_Test-Network.nmproj',encoding='utf-8'))['devices']; print('\n'.join(sorted({str(ipaddress.ip_network(x['ip_address']+'/24',strict=False)) for x in d})))" | Out-File -Encoding ascii output\ops-001\targets.local.txt
if ($LASTEXITCODE -ne 0) { throw "STOP: target derivation failed" }
Get-Content output\ops-001\targets.local.txt   # operator confirms the list matches the authorized scope
$confirmation = Read-Host "Confirm the subnets listed above match the authorized scope. Type YES to continue"
if (-not (([string]$confirmation).Trim() -ieq 'YES')) { throw "STOP: targets not confirmed by the operator" }
$subnetArgs = Get-Content output\ops-001\targets.local.txt | ForEach-Object { "--subnet"; $_ }
```

**Step 4: Collect, with the credential confined to a `try/finally`.**

There is no export flag: `observations.json` is written automatically on every run, with the other report artifacts, into a new run directory `output\<YYYY-MM-DD_HHMMSS>_standard\`. The timestamp is taken when report generation starts (`application.py:222-227`), not when the scan starts.

The Python exit code is captured on the line immediately after the pipeline. Completion is accepted only if the exit code is 0 **and** the console contains the persistence-success marker.

<!-- ps:collect -->
```powershell
$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$log = "output\ops-001\$stamp-console.log"
$runExit = $null
$collectError = $null
try {
  $snmpSecure = Read-Host "SNMP read-only community" -AsSecureString
  $plain = [System.Net.NetworkCredential]::new('', $snmpSecure).Password
  if ([string]::IsNullOrEmpty($plain)) { throw "empty community entered" }
  $env:NETWORKMAPPER_SNMP_COMMUNITY = $plain
  $plain = $null
  python main.py --scan-profile standard @subnetArgs `
    --snmp-arp --snmp-lldp --snmp-bridge-fdb 2>&1 |
    Tee-Object -FilePath $log
  $runExit = $LASTEXITCODE
} catch {
  $collectError = $_.Exception.Message      # handled below as "not accepted"
} finally {
  Remove-Item Env:NETWORKMAPPER_SNMP_COMMUNITY -ErrorAction SilentlyContinue
  Remove-Variable snmpSecure, plain -ErrorAction SilentlyContinue
}

$persisted = (Test-Path -LiteralPath $log) -and
  [bool](Select-String -LiteralPath $log -SimpleMatch -Pattern "Persistence validation successful" -Quiet)
$collectionAccepted = ($null -eq $collectError) -and ($runExit -eq 0) -and $persisted
"Collection exit code: $runExit; persistence marker: $persisted; error: $(if ($collectError) { 'yes' } else { 'none' }); accepted: $collectionAccepted"

if (-not $collectionAccepted) {
  # Preserve partial evidence locally. Do NOT copy output\Test Network.nmproj into any
  # run directory: it may be stale, or this run's unvalidated save.
  $exported = if (Test-Path -LiteralPath $log) { Select-String -LiteralPath $log -Pattern 'Observations exported to (.+)$' | Select-Object -Last 1 } else { $null }
  @(
    "collection NOT accepted",
    "python exit code: $runExit",
    "persistence marker present: $persisted",
    "error: $(if ($collectError) { $collectError } else { 'none' })",
    "run directory reported: $(if ($exported) { $exported.Matches[0].Groups[1].Value.Trim() } else { 'none' })"
  ) | Out-File -Encoding utf8 "output\ops-001\$stamp-NOT-ACCEPTED.txt"
  Copy-Item -LiteralPath $backup -Destination $source -Force
  if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $baselineHash) { throw "STOP: restored file does not match the baseline hash" }
  throw "STOP: collection not accepted$(if ($collectError) { " ($collectError)" }); partial evidence kept locally, baseline restored (Section 9)"
}
```

**How the `try/catch/finally` behaves.**
- **`finally` always runs:** whether collection succeeds, fails or is interrupted with Ctrl+C, it clears the credential variable and the session copies of the secret. If the window closes before `finally` runs, the environment variable dies with the process.
- **An error raised during collection** (including an empty community) is caught. It goes through the same not-accepted path: a note is written, the baseline is restored, and the procedure stops.
- **Ctrl+C runs `finally` but not `catch` or the not-accepted path.** After an interruption, the operator follows Section 9's interrupted-run row, including the restore block.

**Step 5: Identify and preserve the exact run directory** (only after step 4 accepted the collection).

Take the directory from the run's own console output, never from "the newest directory". The application prints the exact path (`application.py:253`). Only now is `output\Test Network.nmproj` known to be this run's validated save. It is copied into the run directory, and then the historical baseline is restored.

<!-- ps:identify -->
```powershell
$match = Select-String -LiteralPath $log -Pattern 'Observations exported to (.+)$' | Select-Object -Last 1
if ($null -eq $match) { throw "STOP: no 'Observations exported to' line in the console log" }
$runDir = Split-Path -Parent ($match.Matches[0].Groups[1].Value.Trim())
foreach ($name in "observations.json", "devices.csv", "relationships.csv", "report.md") {
  if (-not (Test-Path -LiteralPath (Join-Path $runDir $name))) { throw "STOP: missing $name in $runDir" }
}
$runDir                                                  # record locally

Copy-Item -LiteralPath $source -Destination (Join-Path $runDir "Test Network.nmproj")
Copy-Item -LiteralPath $log -Destination (Join-Path $runDir "console.log")
Get-ChildItem -LiteralPath $runDir -File | Get-FileHash -Algorithm SHA256 |
  Select-Object @{n='Name';e={Split-Path -Leaf $_.Path}}, Hash |
  Export-Csv -NoTypeInformation "output\ops-001\$stamp-sha256-collected.csv"

# Put the historical baseline back in place.
Copy-Item -LiteralPath $backup -Destination $source -Force
if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $baselineHash) { throw "STOP: restored file does not match the baseline hash" }
```

Hashes are kept outside the run directory, so the directory's contents never change after this step.

**Step 6: Credential leak scan.** It fails closed: an empty search value, an unreadable file or any scan error stops the procedure. Only counts are printed.

<!-- ps:leakscan -->
```powershell
$check = $null
try {
  $checkSecure = Read-Host "Re-enter community for leak scan" -AsSecureString
  $check = [System.Net.NetworkCredential]::new('', $checkSecure).Password
  if ([string]::IsNullOrEmpty($check)) { throw "STOP: empty leak-scan value" }
  $files = @(Get-ChildItem -LiteralPath $runDir, "output\ops-001" -File -Recurse -ErrorAction Stop)
  $matchCount = 0
  foreach ($file in $files) {
    $hits = @(Select-String -LiteralPath $file.FullName -SimpleMatch -Pattern $check -ErrorAction Stop)
    $matchCount += $hits.Count
  }
  "Leak scan: $($files.Count) files scanned, $matchCount matches"
  if ($matchCount -ne 0) { throw "STOP: credential found in an artifact (Section 9)" }
} finally {
  Remove-Variable check, checkSecure, hits -ErrorAction SilentlyContinue
}
```

`Select-String` reads UTF-8 and the UTF-16 files written by `Tee-Object`. With `-ErrorAction Stop`, a file it cannot open (for example, one locked by another process) raises a terminating error, so the scan never silently skips a file.

**Step 7: Provider acceptance checks** (Section 8.1, V4). Read the three diagnostics blocks in `$runDir\console.log`.

**Where the blocks come from.** Each block is printed only if its provider finished its query loop. The application prints a block only when that provider's `run_diagnostics` is set (`application.py:154-161`), and each provider sets `run_diagnostics` only after querying every host (`arp_neighbor_provider.py:139-146`, `lldp_neighbor_provider.py:180-187`, `bridge_fdb_provider.py:167-172`).

| Check | Rule (from current code) |
|---|---|
| Block present | `ARP Neighbor Diagnostics`, `LLDP Neighbor Diagnostics` and `Bridge FDB Diagnostics` all appear. **A missing block means that provider did not finish: it is a failed provider, not an empty result.** `DiscoveryEngine` swallows a provider exception without any record (`discovery_engine.py:100-105`), so a missing block is the only signal |
| SNMP version | `SNMP Version: v2c` |
| Hosts eligible | `Hosts Eligible` equals the `Device Count (Before)` line (`application.py:277`), because every enrichment provider receives the full discovered device list |
| Hosts queried | `Hosts Queried` equals `Hosts Eligible`. The code sets both to the device count once the loop finishes, so this confirms completion, not a separate measurement |
| Responded + timed out | `Hosts Responded` + `Hosts Timed Out` = `Hosts Queried`. Any non-response counts as "timed out", whatever its cause |
| ARP entries | The `arp_neighbor` observation count equals `Total ARP Entries Collected`, because every ARP entry from a responding host becomes exactly one observation (`arp_neighbor_provider.py:174-187`). Appendix A checks this mechanically (R6) |
| FDB entries | `bridge_fdb` observations ≤ `Total Bridge FDB Entries Collected`. Only `learned` rows whose MAC maps to exactly one subject become observations (`bridge_fdb_provider.py:205-231`) |
| LLDP entries | No numeric bound is asserted. One LLDP row can yield several observations (one per resolvable management address) or none |

**Interpreting the results.**
- **All hosts timed out:** with every block present and consistent, this is a **valid negative result**, not a failure.
- **Zero observations** from a provider whose block is missing is a failure, never "nothing found".

**Step 8: Replay verification.**
```powershell
$replayOut = "output\ops-001\$stamp-replay.txt"
python -m devtools replay-observations $runDir 2>&1 | Tee-Object -FilePath $replayOut
$replayExit = $LASTEXITCODE
if ($replayExit -ne 0) { throw "STOP: replay exited $replayExit (V5 failed)" }
```

| Exit code | Meaning |
|---|---|
| 0 | `Result : MATCH`. The relationship rows replayed from `observations.json` equal `relationships.csv` exactly: subject, category, related subject, corroboration state and provenance, in order |
| 1 | `Result : MISMATCH`. The rows differ. The run fails D1 (Section 9) |
| 2 | Replay could not run: missing directory or file, unexpected CSV header, or a rejected artifact (unknown format, version or type). The run fails D1 |

**What MATCH does and does not prove.**
- MATCH compares **relationship rows only.**
- The command prints canonical identity counts, labelled "not compared". A run directory has no machine-readable identity artifact, so MATCH does **not** prove exact equality of the run's canonical identities by comparison.
- Exact identity replay is established by the tests and independent verification in VER-029, not by this command.

**Step 9: Endpoint-gate exclusion analysis** (Appendix A). Run only after the owner has approved Appendix A and the script has been reviewed.
```powershell
python -I output\ops-001\gate_analysis.py $runDir --replay-output $replayOut 2>&1 |
  Tee-Object -FilePath "output\ops-001\$stamp-gate-analysis.txt"
$gateExit = $LASTEXITCODE
if ($gateExit -ne 0) { throw "STOP: gate analysis exited $gateExit (V11 or V9 failed; see Appendix A.3)" }
```

**Step 10: Post-run integrity.**
```powershell
Get-ChildItem -LiteralPath $runDir -File | Get-FileHash -Algorithm SHA256 |
  Select-Object @{n='Name';e={Split-Path -Leaf $_.Path}}, Hash |
  Export-Csv -NoTypeInformation "output\ops-001\$stamp-sha256-final.csv"
$diff = @(Compare-Object (Import-Csv "output\ops-001\$stamp-sha256-collected.csv") (Import-Csv "output\ops-001\$stamp-sha256-final.csv") -Property Name, Hash)
if ($diff.Count -ne 0) { throw "STOP: run directory changed after step 5 (V9 failed)" }
if ((git rev-parse HEAD).Trim() -ne $head) { throw "STOP: HEAD changed during the procedure" }
if (@(git status --porcelain --untracked-files=all -- @pinned).Count -ne 0) { throw "STOP: pinned paths changed during the procedure" }
if ((Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash -ne $baselineHash) { throw "STOP: baseline backup changed" }
if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $baselineHash) { throw "STOP: $source is not the restored baseline" }
"Post-run integrity: OK"
```

---

## 7. Artifacts to Preserve (local only)

All artifacts stay under `output\`, which is gitignored. **None is committed** (D4).

| Artifact | Location | Content |
|---|---|---|
| Baseline backup | `output\baselines\2026-09-04_Test-Network.nmproj` | The pre-run 244-device dataset, with its SHA-256 recorded locally |
| Targets file | `output\ops-001\targets.local.txt` | The explicit baseline subnets used (D3) |
| **Observation export** | `$runDir\observations.json` | **Every retained observation** (identity and relationship) with full provenance. The primary replay artifact (D1) |
| Run report | `$runDir\report.md` | Device inventory plus the canonical identity and relationship sections |
| Device CSV | `$runDir\devices.csv` | One row per device |
| Relationship CSV | `$runDir\relationships.csv` | One row per canonical edge |
| Project file | `$runDir\Test Network.nmproj` | A copy of the run's device data |
| Console log | `$runDir\console.log` (and `output\ops-001\<stamp>-console.log`) | Discovery and ARP/LLDP/FDB diagnostics; the exported-path lines. Written by `Tee-Object` as UTF-16 |
| Not-accepted note | `output\ops-001\<stamp>-NOT-ACCEPTED.txt` | Only if step 4 did not accept the collection: exit code, marker status, reported run directory |
| Hashes | `output\ops-001\<stamp>-sha256-collected.csv`, `-sha256-final.csv` | Integrity of the run directory after step 5 and after verification |
| Replay output | `output\ops-001\<stamp>-replay.txt` | The `replay-observations` report and its result |
| Gate analysis | `output\ops-001\gate_analysis.py`, `output\ops-001\<stamp>-gate-analysis.txt` | Appendix A script (local, gitignored) and its aggregate output |
| Run manifest | Kept locally with the artifacts | Commit, nmap version, operator, date and time window, command line (no credential), provider flags, `$runDir`, `$baselineHash` and `$historicalIdentity`. Only the sanitized fields in Section 11 go into the committed results report |

---

## 8. Success Criteria

Collection validity and positive findings are separate. A run can be fully valid and still find nothing.

### 8.1 Collection validity (all must hold)

1. **V1 Baseline.** Step 1 passed: the committed application code equals `84492b7` in every pinned path; no staged, unstaged or untracked change exists in those paths, or anywhere except the known unrelated files; operational locations are gitignored; tests, validation and the encoding check pass.
2. **V2 Completion.** Step 4 accepted the collection: the Python exit code captured immediately after the pipeline is 0, **and** the console contains "Persistence validation successful".
3. **V3 Artifacts.** The run directory identified in step 5 contains `observations.json`, `devices.csv`, `relationships.csv` and `report.md`.
4. **V4 Providers.** All step 7 checks pass for the ARP, LLDP and Bridge FDB providers. A missing diagnostics block fails V4 for that provider.
5. **V5 Replay.** `python -m devtools replay-observations` exits 0 with `Result : MATCH` (step 8).
6. **V6 No credential exposure.** The fail-closed leak scan (step 6) scanned every file and found 0 matches, and the `finally` blocks cleared the credential.
7. **V7 Baseline protected.** Historical identity was established by an independent hash, or explicitly waived by the owner (step 2). The backup and the restored `output\Test Network.nmproj` both equal `$baselineHash` at step 10.
8. **V8 No code change.** `HEAD` and the pinned paths are unchanged from step 1 to step 10.
9. **V9 Artifacts unchanged by verification.** The step 10 hash comparison finds no difference, and Appendix A's before/after hashes match.
10. **V10 Scope.** `--snmp` was not used; only the three relationship flags were.
11. **V11 Analysis consistency.** If Appendix A was run, it exited 0: all its reconciliation checks hold.

### 8.2 Findings (recorded; any value is acceptable)

- **SNMP reachability per provider:** hosts eligible, responded and timed out. **Zero responders is a valid negative result.**
- **Retained relationship observations per category and provider.**
- **Canonical edges per category,** with their state distribution (WEAK and CONFIRMED).
- **Endpoint-gate exclusions** by Appendix A bucket, as observation counts and distinct-triple counts.
- **Fan-out:** a distribution of edges per subject per category.
- **Aggregate device and classification counts** compared with the baseline's. Differences are expected (Section 6, step 2), not failures.

### 8.3 Constraint checks (a violation invalidates the run's use)

- **No CONFLICTING relationship.** All three categories are MULTIPLE, so CONFLICTING would contradict the committed policy.
- **No `default_gateway` category**, and no category outside {`arp_neighbor`, `bridge_fdb`, `connected_to`}.

### 8.4 Not claimed by OPS-001

- Complete network coverage.
- Physical topology or physical connectivity.
- Any gateway relationship.
- Exact production identity equality by comparison (step 8).
- Classification cost (ARCH-029 Section 9).

---

## 9. Failure Criteria, Rollback and No-Op Behavior

| Condition | Effect | Action |
|---|---|---|
| Owner approval of this procedure or of Appendix A missing | **OPS-001 does not start** (Appendix A: step 9 does not run) | No-op |
| Any step 1 check fails (pinned code, working-tree changes, gitignore, tests, validation, nmap, encoding) | **OPS-001 does not start** | Fix the cause. A pinned-code difference needs re-review of OPS-001 against the new code |
| Historical identity of the baseline cannot be established, or an existing backup differs from the source (step 2) | **OPS-001 does not start** | Obtain an independently recorded hash or an owner waiver (Section 13, item 5). Never overwrite the backup |
| Empty community entered, or credential variable unset | Step 4 stops, or the application exits with code 2 before scanning. Collection is not accepted | Follow the "collection not accepted" row, then restart from step 4 |
| **Collection not accepted** (step 4: Python exit code not 0, or the persistence marker missing) | V2 fails | Step 4 keeps the console log and writes `<stamp>-NOT-ACCEPTED.txt`. It **does not** copy `output\Test Network.nmproj` into any run directory, because that file may be stale or an unvalidated save. It restores the baseline and stops. Keep any partial run directory locally for diagnosis |
| All SNMP queries time out | **Not a failure.** Valid negative result, provided V4 passes | Record and report it. Do not retry with guessed communities |
| A diagnostics block is missing | V4 fails for that provider. **Not** an empty result | Mark the run invalid for that provider. Keep the artifacts locally for diagnosis. Fix through a FEAT before any re-run |
| Nmap fails or finds no hosts | No meaningful output | Treat as "collection not accepted". Keep the partial run directory locally, labelled by the note file. Restore the baseline `.nmproj` (step 2 procedure) |
| Run interrupted midway (Ctrl+C) | Partial or no artifacts | The step 4 `finally` block clears the credential. Treat as "collection not accepted": keep partial evidence locally, never label `output\Test Network.nmproj` as this run's, and restore the baseline (step 2 procedure) |
| No "Observations exported to" line, or a missing artifact (step 5) | V3 fails | Mark the run invalid. Keep whatever was written locally. Restore the baseline `.nmproj` |
| Replay exit 1 or 2 | V5 fails (D1 not satisfied) | Mark OPS-001 FAIL. Keep the artifacts locally for diagnosis. Fix through a FEAT before any re-run |
| Appendix A exits 1 (reconciliation failed), 2 (input rejected), 3 (artifact changed) or 4 (internal failure) | V11 or V9 fails | Treat its counts as unusable. Investigate before any reporting |
| Leak scan cannot read a file, or errors | Step 6 stops (fail closed) | Resolve the cause, then rerun step 6. The run is not usable until the scan completes with 0 matches |
| **Leak scan finds the credential in any artifact** | **Stop** | Delete every affected artifact, including copies. Notify the network owner so the community can be rotated. Record the incident (without the value) in the results report. Fix the leak path through a separate FEAT before any re-run |
| CONFLICTING relationship, `default_gateway`, or any code change detected | A constraint is violated (Section 8.3, V8) | Mark OPS-001 FAIL and investigate before any use of the data |
| Network owner reports impact | — | Stop the run (Ctrl+C). The `finally` block clears the credential. Follow the interrupted-run row |

**Rollback scope.** SNMP access is read-only and nmap sends probes only, so nothing on the network needs rolling back. Local rollback is limited to:
- restoring `output\Test Network.nmproj` from `output\baselines\`;
- deleting partial run directories.

The repository is never modified by this procedure.

---

## 10. Planned Post-Collection Report

After the run, write `docs/reports/OPS-001-SNMP-Production-Evidence-Collection-Results.md`. It must follow Section 11 strictly and needs architect approval before commit. It reports collection validity and findings in separate sections.

**Part 1: Collection validity**
1. **Sanitized run manifest:**
   - commit, and confirmation of the pinned-baseline check;
   - nmap version, date, scan profile and provider flags;
   - the number of subnets scanned (not their addresses);
   - the observation-export format and version (`networkmapper.retained-observations` v1).
2. **Each validity criterion V1–V11**, with its evidence (Section 8.1).
3. **Replay result,** with the statement that MATCH covers relationship rows only.
4. **Credential leak scan result,** and confirmation that no artifacts were committed.

**Part 2: Findings**

5. **Discovery summary:** aggregate host counts, compared with the 244-device baseline's aggregate count.
6. **SNMP reachability per provider:** hosts eligible, responded and timed out, and total entries collected. Zero responders is reported as a valid negative result.
7. **Relationship evidence by category:** retained observations, canonical edges, and Appendix A's exclusion buckets (observation and distinct-triple counts), with the reconciliation shown.
8. **Corroboration state distribution:** WEAK and CONFIRMED (and CONFLICTING, expected 0).
9. **Fan-out sizes:** a distribution of edges per subject per category, using sanitized host IDs where individual subjects must be referenced.
10. **Known-behavior occurrences:** ARCH-027 Open Questions 2 and 6.
11. **Aggregate classification note:** device-type counts compared with the baseline's. Differences are expected, not failures.

**Part 3: Limits and next steps**

12. **What the run does not show:**
    - complete coverage;
    - physical topology;
    - any gateway relationship;
    - exact production identity equality by comparison;
    - classification cost.
13. **Recommendation:** what the evidence supports next. Topology and gateway work stay out of scope unless the evidence and a new ADR justify them.

---

## 11. Sanitization and Redaction Policy (architect decision D4)

> **Architect decision (D4):** Committed reports may include aggregate counts, provider names, relationship categories, and sanitized stable host IDs only. Do not commit real hostnames, MACs, public IPs, serials, SNMP community strings, customer names, or raw production artifacts. Private production IPs remain local unless sanitized.

| Data | In committed material |
|---|---|
| Aggregate counts, state distributions and exclusion buckets | Allowed |
| Provider names (for example `SnmpArpNeighborProvider`, `snmp`, `ipNetToPhysicalTable`) | Allowed |
| Relationship categories (`arp_neighbor`, `bridge_fdb`, `connected_to`) | Allowed |
| Sanitized stable host IDs | Allowed: the only permitted way to refer to an individual host |
| Hostnames, MAC addresses, serials | **Prohibited** |
| Public IPs | **Prohibited** |
| Private production IPs and subnets | **Local only**, unless replaced by sanitized host IDs or placeholder names (`BASELINE_NET_k`) |
| SNMP community strings, or any secret in any form | **Prohibited** |
| Customer names | **Prohibited** (`Test Network` is the application's hard-coded project name, not a customer name) |
| Raw production artifacts (`.nmproj`, CSVs, `report.md`, `observations.json`, console logs, replay output, gate-analysis output and script, hash files, the targets file) | **Prohibited.** They stay in gitignored `output\` |

**Sanitized stable host IDs.** This is a recommendation, and it remains an **owner decision** (Section 13, item 2):
- **Format:** `host-` followed by the first **12** hex characters of HMAC-SHA256(local key, raw subject), for example `host-3f9a2c1e07b4`. Twelve characters (48 bits) are used from the outset, so collisions are unlikely even across thousands of hosts.
- **Key:** a random secret of at least 32 bytes, generated once, stored only in gitignored `output\ops-001\`, and never committed or shared.
- **Collision check:** when the report is generated, check that every distinct raw subject gets a distinct ID.
- **Deterministic extension:** if any two collide, extend **every** ID in that report by 4 hex characters (16, then 20, and so on) until all are distinct. Record the final length in the report. IDs stay stable for a given key and length.
- **What this is, and is not.** This is keyed pseudonymization, **not irreversible anonymization**.
  - Anyone holding the key can recompute the mapping.
  - With the key, the small private-address space can be enumerated to reverse an ID.
  - The protection rests entirely on keeping the key local and secret.

**Retroactive scope.** D4 governs material committed from now on. Sanitizing earlier reports retroactively is a separate decision and is not part of OPS-001.

---

## 12. Constraints Retained

- Baseline backup that is never overwritten, independent historical identity, hash verification and restoration (steps 2, 4 and 5; V7).
- Credential handling inside `try/finally`, and a fail-closed leak scan (Section 4.1; steps 4 and 6; V6).
- Explicit subnet selection with no auto-detection (D3; step 3).
- STANDARD profile, the three relationship flags, and no `--snmp` (D2; V10).
- No gateway inference, no topology rendering, no physical-connectivity claims, no coverage claims, no classification rule changes, and no committed credentials or raw production artifacts (Section 1; D4).

---

## 13. Open Questions

1. **Resolved.** The ADR question for the prerequisite was settled by ADR-011 Amendment 1 (`84153e0`). The feature is implemented (`e12b81a`, `97b22e7`) and verified (VER-029, `cd1a53d`).
2. **Owner decision:** approve, change or reject the recommended host-ID convention (Section 11): 12 hex characters of HMAC-SHA256 with a local secret key, a collision check and deterministic extension. It is keyed pseudonymization, not anonymization.
3. Does the network owner's window fit the approximate SNMP duration (Section 4.3)? That is about 3 providers × 3 s × the number of non-responding hosts (about 37 minutes if all of roughly 244 hosts were non-responders), plus unmeasured walk time for responders. Restricting queries to infrastructure would need a host filter, which is a code change and out of scope.
4. Approve Appendix A and review `output\ops-001\gate_analysis.py` (validated on synthetic data only; Appendix B) before step 9 runs.
5. **Historical identity of the baseline.** The repository holds no independently recorded SHA-256 of the 2026-09-04 `Test Network.nmproj`. Either supply one from an independent record, or record the owner's written waiver. Without one of these, step 2 stops.

---

## Appendix A: Single-Run Endpoint-Gate Exclusion Analysis

**Status: procedure documented for review. Not to be executed against production artifacts until the owner approves this appendix and the script described here has been written and reviewed.**

### A.1 Authority and scope

This analysis is performed under the architect ruling recorded in ARCH-029 Section 9:

> Endpoint-gate exclusion analysis is within replay verification when performed solely to explain the committed resolvers' treatment of a single run's retained observations. It may reconstruct canonical identities and count identity-gate exclusions and self-loops using the documented buckets, preserving observation multiplicity and distinguishing distinct relationship triples. This does not authorize normal application loading, cross-run analysis, new application reports, or changes to the devtools command. OPS-001 must document the analysis procedure for review before execution.

Accordingly, the analysis:
- reads **one** run directory, `$runDir` from step 5, plus that run's captured replay output, and nothing else;
- changes no application code and no `devtools` command, and adds no application report;
- never combines runs, and never feeds its results into a normal workflow.

### A.2 Inputs and tools

- **Inputs:** `$runDir\observations.json`, `$runDir\relationships.csv` and `$runDir\console.log` from step 5, and the step 8 replay output.
- **Loader:** the existing replay-format loader, `networkmapper.observations.replay_format.load_observations`, at the pinned baseline. It rejects an unknown format, version or observation type; any rejection stops the analysis.
- **Resolvers:** the pinned `networkmapper.identity.resolver.IdentityResolver` and `networkmapper.relationships.resolver.RelationshipResolver`. `RelationshipResolver` is constructed with no arguments, so the module cardinality policy applies, as in `Application.run()`.
- **Nothing else is imported from the application.**

### A.3 Script location and execution

- **Location.** The script lives at `output\ops-001\gate_analysis.py`. It is local, gitignored and never committed. It has been written and validated against synthetic run directories only (Appendix B). It has **not** been run against production artifacts.
- **Reviewed version.** The reviewed script has SHA-256 `DAE9A8212BE16C92897D8966526E437CBB36AB6B3B66F00D928109033809BC99`. Copy it to the scanner byte for byte (no line-ending conversion), then verify it before step 9:

  ```powershell
  if ((Get-FileHash -LiteralPath output\ops-001\gate_analysis.py -Algorithm SHA256).Hash -ne "DAE9A8212BE16C92897D8966526E437CBB36AB6B3B66F00D928109033809BC99") { throw "STOP: gate_analysis.py is not the reviewed version" }
  ```

  Any change to the script needs a new review and a new recorded hash.
- **Execution.** Run it as `python -I output\ops-001\gate_analysis.py <runDir> --replay-output <step 8 output file>` (step 9). Isolated mode (`-I`) stops the current directory and environment variables from adding modules to the import path. The script itself inserts the repository root, two levels above its own location, at the front of `sys.path`, so it imports the pinned application code. Because `-I` also ignores `PYTHONIOENCODING`, the script prints ASCII only.
- **Read-only.** The script opens its inputs for reading only, writes nothing into `$runDir`, and makes no network call. It reads `console.log` and the replay output whether they are UTF-16 (as written by `Tee-Object`) or UTF-8.
- **Output.** Aggregate counts only, to standard output, captured as `output\ops-001\<stamp>-gate-analysis.txt`. It never prints a subject, address, hostname or MAC.
- **Error output.** A fixed error category and the exit code only. Loader messages and file paths are withheld, because they can quote values from the input artifact.
- **Exit codes:**

  | Code | Meaning |
  |---|---|
  | 0 | Every reconciliation check holds, and the run directory is unchanged |
  | 1 | At least one reconciliation check failed; the counts are unusable |
  | 2 | Input error: a required file is missing, or the loader rejected the artifact |
  | 3 | Integrity failure: a file in `$runDir` changed during the analysis |
  | 4 | Unexpected internal failure; only the exception type is printed |

### A.4 Method

1. **Hash before.** Compute SHA-256 for every file in `$runDir`.
2. **Load.** `observations = load_observations($runDir\observations.json)`. Record the total, and the identity and relationship observation counts.
3. **Reconstruct identities.**
   - `identities = IdentityResolver().resolve(observations)`.
   - Let *I* be the set of `identity.subject` values.
   - *I* comes only from canonical identities, never from the discovered device list. A discovered device with no identity observation is not in *I*.
4. **Classify** every `RelationshipObservation`, in this order, mirroring the resolver's gate (`relationships/resolver.py:136-144`):

   | Bucket | Condition |
   |---|---|
   | **B1** subject missing | `subject` ∉ *I*, `related_subject` ∈ *I* |
   | **B2** related subject missing | `subject` ∈ *I*, `related_subject` ∉ *I* |
   | **B3** both missing | `subject` ∉ *I*, `related_subject` ∉ *I* |
   | **B4** self-loop | both ∈ *I*, and `subject` = `related_subject` (counted separately, after the identity gate) |
   | **P** passed | both ∈ *I*, and they differ |

   A self-loop whose single subject is not in *I* falls into B3. This precedence must be stated wherever the counts appear.
5. **Count** each bucket in two ways:
   - **observation count,** preserving multiplicity: every observation counts, including exact duplicates;
   - **distinct-triple count,** over distinct `(subject, category, related_subject)`.

   Report both overall and per category. Also report observation counts per category and per `(provider, collection_method)`; these supply the ARP check in step 7.
6. **Replay edges.** `relationships = RelationshipResolver().resolve(observations, identities)`.
7. **Reconcile.** Every check must hold; if any fails, the analysis stops and its counts are unusable (V11):
   1. Relationship observation count = P + B1 + B2 + B3 + B4 (observation counts).
   2. P (observation count) = the sum of `len(r.observations)` over `relationships`.
   3. P (distinct triples) = `len(relationships)`, because each canonical relationship is one distinct triple.
   4. The distinct-triple sets of P, B1, B2, B3 and B4 are pairwise disjoint. A triple's bucket depends only on its endpoints, so each triple falls in exactly one bucket.
   5. `len(identities)` and `len(relationships)` equal the "Canonical identities" and "Canonical relationships … replayed" counts printed by step 8, and `len(relationships)` equals the data-row count of `$runDir\relationships.csv`.
   6. The `arp_neighbor` observation count equals `Total ARP Entries Collected` in the ARP diagnostics block (step 7). A missing block or total fails this check.
8. **Hash after.** Recompute SHA-256 for every file in `$runDir`; the results must equal step 1's. Step 10 repeats this check independently.

### A.5 Output

The output contains aggregate counts only:
- totals;
- buckets P, B1–B4 by category, as observation and distinct-triple counts;
- per-provider observation counts;
- the reconciliation results;
- the before and after hash comparison.

These aggregate counts, and only these, may go into the committed results report (Section 10, item 7), sanitized per Section 11.

### A.6 What the analysis does not do

- It does not explain *why* a subject lacks an identity, beyond the bucket. For example, it cannot tell "not discovered" from "discovered with no observed identity value". Any such attribution in the results report must be stated as an inference, not a measurement.
- It does not measure network coverage, physical connectivity, gateways or classification cost.
- It does not compare runs, and does not write to the run directory.

---

## Appendix B: Synthetic Validation (no production data)

Both checks ran against scratch directories outside the repository. They used synthetic observations in documentation address ranges, the real exporters, and the real replay command. **No discovery ran, no device was queried, and no production artifact was read.** Neither harness, nor its output, is committed.

### B.1 `gate_analysis.py`: 24 of 24 checks passed, plus an error-output check

The harness runs the script as the operator will: `python -I output\ops-001\gate_analysis.py <run_dir> --replay-output <file>`. Console and replay files are written as UTF-16 with a BOM, like `Tee-Object`.

**Cases and results:**

| Case | Expected | Result |
|---|---|---|
| C1. Full run: duplicates, every bucket, a self-loop on an identity-less subject, passing edges | Exit 0 | P 4/3, B1 2/1, B2 2/2, B3 3/3, B4 3/2 (observations / distinct triples). All 9 reconciliation checks pass |
| C2. Identities only, empty relationship set | Exit 0 | All buckets 0/0. All 9 checks pass |
| C3. Unknown format identifier | Exit 2 | Rejected by the loader |
| C4. Invalid JSON | Exit 2 | Rejected by the loader |
| C5. Missing `console.log` | Exit 2 | Input error |
| C6. Extra `relationships.csv` row | Exit 1 | R5c fails |
| C7. ARP total disagrees | Exit 1 | R6 fails |
| C8. ARP diagnostics block missing | Exit 1 | R6 fails |
| C9. Replay output disagrees | Exit 1 | R5b and R5d fail |
| C10. No `--replay-output` | Exit 2 | Argument error |
| C11. UTF-8 inputs | Exit 0 | Read correctly |
| C12. File changed during the analysis | Exit 3 | Integrity failure. The harness patches `analyze()`; the script has no test hook |

**Checks that apply to every case:**
- C1–C11 leave every file in the run directory, and the directory listing, byte-identical.
- No case prints an address, MAC or hostname.
- Static checks confirm the script has no write-mode file access, and imports only the loader, the two resolvers and the observation models from the application.

**Error-output check.** Five malformed artifacts each carried a distinctive identifier: as an unknown type, an unknown key, a non-canonical timestamp, an unknown format identifier, and in a run-directory name. A missing input was tested separately. In every case the script exits 2, prints only the fixed category and exit code, and echoes no distinctive value. Before the change, all five malformed cases echoed it, through the loader message or the file path.

### B.2 PowerShell control flow: 28 of 28 checks passed, plus 11 of 11 for the step 3 amendment

The harness extracts the **exact** blocks marked `ps:` in Section 6 and runs them in Windows PowerShell 5.1 inside a scratch sandbox. `git`, `python` (for the scan), `nmap` and `Read-Host` are replaced by stubs, so nothing scans.

| Area | Result |
|---|---|
| Syntax | All 11 PowerShell blocks in this plan parse without errors (including the Appendix A.3 hash check) |
| Pre-flight | Passes on a clean tree (only `review.diff` and `diff.md` changed), and sets `PYTHONIOENCODING`. Stops on each of: a pinned-commit difference; a staged, unstaged or untracked change in a pinned path; any other unexpected change; a path not gitignored; a pytest failure; a validation failure |
| Baseline | Passes with a matching independent hash, or with an owner waiver. Stops with no hash and no waiver, with a mismatched historical hash, or when an existing backup differs from the source. An existing backup is never overwritten |
| Collection | **Success:** the credential is present only during the run and cleared afterwards; the new save is copied into the run directory; the baseline is restored; hashes are written. **Exit 0 without the marker, exit 1 with it, an exception mid-run, or an empty community:** all stop as "not accepted", with the credential cleared, a note written, the baseline restored, and no project file copied into the run directory |
| Native exit code | A real Python process exiting 3 through `2>&1 \| Tee-Object` leaves `$LASTEXITCODE` = 3. The `Tee-Object` file is UTF-16 LE with a BOM |
| Encoding check (real Python) | The exact step 1 check exits 1 without `PYTHONIOENCODING`, so it catches the hazard, and exits 0 with `PYTHONIOENCODING=utf-8` |
| Leak scan | A clean tree gives "0 matches", printing counts only. A credential planted in a UTF-16 file, an empty search value, and a locked (unreadable) file each stop the scan. The search value is cleared every time |
| Scope confirmation (step 3 amendment) | `YES`, `yes`, `Yes` and whitespace-padded `yes` continue. Empty input, whitespace only, `y` and unrelated text stop with "targets not confirmed". A null answer also stops |

**Not validated:** behavior on the production scanner, real SNMP agents, real artifact sizes, and Ctrl+C. Ctrl+C is covered by `finally` and Section 9's interrupted-run row, but was not exercised.
