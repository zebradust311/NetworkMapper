# OPS-001 — SNMP-Enabled Production Evidence Collection: Results

**Outcome: CLOSED, NOT EXECUTED. No production evidence was collected.**

OPS-001 was authorized for one collection run on 2026-10-19. Six launches of the local runner were made. Launches 1–4 stopped before collection; for launches 5 and 6 no collection evidence was found. The operator then reported that no device on the production network has SNMP enabled, so no SNMP read-only community exists for the procedure to use. The project owner closed OPS-001 on that basis rather than enable SNMP on production devices.

Collection validity (Part 1) and findings (Part 2) are kept separate, as the procedure requires. Because no collection evidence exists, most validity criteria are **not reached**. The criteria that depend on cleanup and leak scanning (V6) or on step 10 (V7, V8) are reported against their exact definitions, not as passes.

Sanitization follows OPS-001 Section 11 (architect decision D4). This report contains no addresses, subnets, hostnames, MAC addresses, credential values or raw artifacts. No individual host is referenced, so no sanitized host IDs were needed.

## Evidence classes

Every factual statement below is labelled with its source:

| Label | Meaning |
|---|---|
| **[Inspected]** | Local evidence examined directly: runner step logs, file listings and timestamps, SHA-256 hashes, process listings, environment-variable scopes, git state, and the runner source |
| **[Operator]** | Reported by the operator in the session and not independently verified |
| **[Deduced]** | Inferred from inspected evidence plus the documented behavior of the runner or procedure. Each deduction names what it rests on |

Local inspections were made at several points during the session; the last full inspection was at 11:34 local time on 2026-10-19. Nothing later is covered.

---

## 1. Authority and Baseline

| Item | Value |
|---|---|
| Procedure | [`docs/plans/OPS-001-SNMP-Enabled-Production-Evidence-Collection.md`](../plans/OPS-001-SNMP-Enabled-Production-Evidence-Collection.md) at `897884aca5cb1674fe6c4ecba8d845006039135c`, amended by `080363b72b40500bb50b2979f6c7f6d69dbd0d61` (*Make OPS-001 scope confirmation case-insensitive*; step 3 only) |
| Pinned application baseline | `84492b710404f23e0335ae3306c3f4a2b1999f0c`. Pinned paths equal it at both procedure commits **[Inspected]** |
| Reviewed `gate_analysis.py` SHA-256 | `dae9a8212be16c92897d8966526e437cbb36ab6b3b66f00d928109033809bc99`, matched **[Inspected]**; never run |
| Runner | Generated from the procedure; all 11 procedure blocks present verbatim, the owner-approved waiver line the only substitution **[Inspected]**. SHA-256 `E3A7CD80006E71774568B091F6AF073B33D6CAC989A5AFDFA78605A3D31808D4` for launches 4–6; file unmodified since before launch 4 **[Inspected]** |
| Authorization | Project owner, 2026-10-19: one collection run, STANDARD profile, explicit baseline subnets, `--snmp-arp --snmp-lldp --snmp-bridge-fdb`, no `--snmp` |
| Owner decisions recorded | 12-hex HMAC-SHA256 host IDs for sanitized reports; historical-baseline identity **waived**; network-owner prerequisites and window confirmed |
| Closing decision | Project owner, 2026-10-19: close OPS-001; do not enable SNMP for this purpose |

---

## Part 1: Collection Validity

### 2. Sanitized run manifest

| Item | Value |
|---|---|
| Date | 2026-10-19 |
| Scan profile and flags (planned) | `standard`; `--snmp-arp --snmp-lldp --snmp-bridge-fdb`; `--snmp` not used |
| Subnets | 3 explicit baseline /24 networks, derived locally from the baseline dataset (D3); addresses local only **[Inspected]** |
| Tooling | Nmap 7.99 **[Inspected: step logs]**. Python 3.13; the project virtual environment was in use for launches 4–6 **[Deduced: `pytest` succeeded, and the global interpreter has no `pytest`]** |
| Observation export | None found **[Inspected: no run directory]** |
| Collection | **No collection evidence found** (Section 3) |

### 3. Launch history

Six step logs exist in the local operational directory **[Inspected]**. The operator reported launches 1–5; launch 6 was found by local inspection and has not been reported or explained by the operator.

| # | Start | Last step-log entry **[Inspected]** | Cause | Evidence class of the cause |
|---|---|---|---|---|
| 1 | 10:13:26 | Stopped at the runner elevation check, before step 1 | Window not elevated | **[Inspected]** step log message |
| 2 | 10:14:02 | Stopped in step 1, check 5: `pytest failed` | The elevated window lacked the project virtual environment on `PATH`; the global interpreter has no `pytest` | **[Operator]** pasted error and interpreter path; **[Inspected]** global interpreter lacks `pytest`, venv has it |
| 3 | 10:25:17 | Steps 1–2 passed; stopped at step 3 confirmation | The runner's confirmation check was case-sensitive (runner-only code, absent from the procedure). The operator entered lowercase `yes`, which the case-sensitive check rejected | **[Operator]** pasted console shows lowercase `yes` entered; **[Inspected]** runner code and timestamps. Fixed by `080363b` |
| 4 | 11:05:55 | Steps 1–2 passed; stopped at step 3 confirmation | Empty answer about 30 ms after the prompt, too fast for a typed reply. The gate rejected it as designed. Suspected explanation: a keystroke buffered during pre-flight and consumed by the prompt. Not established | **[Inspected]** targets-file and stop timestamps; **[Operator]** pasted console with nothing typed after the prompt; buffering is a **suspected explanation** only |
| 5 | 11:07:22 | Steps 1–3 passed; **`START Step 4 collect`, no stop line** | The operator did not have an SNMP read-only community and entered an unrelated credential at the prompt (Section 5) | **[Operator]** |
| 6 | 11:27:55 | Steps 1–3 passed; **`START Step 4 collect`, no stop line** | Unknown | — |

**Launches 1–4 did not reach step 4** **[Inspected]**, so no credential prompt was shown and no collection command ran.

**Launches 5 and 6: no collection evidence was found; the inspected artifacts and runner behavior are consistent with termination at the credential prompt.** Inspected at 11:34:
- no `<stamp>-console.log` exists. The runner pipes `main.py` through `Tee-Object -FilePath $log`, which creates that file when the pipeline starts;
- no `<stamp>-NOT-ACCEPTED.txt` exists. Its absence establishes nothing about what was entered at the prompt: an interruption or failure could prevent it from being written;
- no run directory exists under `output\`;
- no `powershell.exe`, `python.exe` or `nmap.exe` process started at or after 11:07 was running, apart from an unrelated session started at 11:34. Both runner processes had therefore exited.

**Unknown:** how each of these launches ended (Ctrl+C, closing the window or otherwise), what was entered at launch 6's prompt, and whether an empty answer was submitted at either. For launch 5 the operator was instructed to press Ctrl+C but did not confirm doing so. For launch 6 there is no operator account.

### 4. Validity criteria (Section 8.1)

| Criterion | Result | Basis |
|---|---|---|
| V1 Baseline | **Pass** (launches 4, 5 and 6) | **[Inspected]** each step log records `DONE Step 1 pre-flight`; **[Deduced]** the runner writes that line only after all six step 1 checks pass. **[Operator]** launch 4 console: 882 tests passed, `devtools validate --all` PASS |
| V2 Completion | Not reached | No collection evidence found (Section 3) |
| V3 Artifacts | Not reached | **[Inspected]** no run directory |
| V4 Providers | Not reached | No provider output or diagnostics found **[Inspected]** |
| V5 Replay | Not reached | **[Inspected]** no `observations.json` |
| **V6 No credential exposure** | **Not verified** | See below |
| V7 Baseline protected | **Not reached as defined**; integrity holds on inspection | V7 requires both files to equal `$baselineHash` *at step 10*, which never ran. **[Inspected]** the source `output\Test Network.nmproj` and the backup both have SHA-256 `9F144AF0…F80A`, equal to the `baselineHash` each launch logged, at every inspection through 11:34. The backup was created during launch 3 **[Inspected: `output\baselines\` created 10:25:37]**; step 2 never overwrites an existing backup and stops if it differs from the source **[Inspected: runner code]**. Historical identity: **not established; owner waiver recorded** |
| V8 No code change | **Not reached as defined**; consistent on inspection | V8 compares HEAD and pinned paths at step 1 and step 10. **[Inspected]** at 11:34, HEAD is `080363b` (the documentation-only amendment) and the pinned paths equal `84492b7` |
| V9 Artifacts unchanged | Not reached | No run directory |
| V10 Scope | **Consistent; no collection command executed** | **[Inspected]** the runner's only `main.py` invocation uses `--scan-profile standard`, the subnet arguments and the three relationship flags, without `--snmp` |
| V11 Analysis consistency | Not reached | Appendix A not run |

**V6, against its exact definition.** V6 requires that *the fail-closed leak scan (step 6) scanned every file and found 0 matches, **and** the `finally` blocks cleared the credential*. Neither half was verified:
- **Leak scan: not performed.** No launch reached step 6 **[Inspected]**.
- **`finally` cleanup: not evidenced for launches 5 and 6.** Neither step log records a stop, and the runner logs nothing from `finally` **[Inspected]**. Launches 1–4 never entered step 4, so no credential was entered and cleanup does not apply to them **[Inspected]**.

What *is* established is narrower:
- **[Inspected]** `NETWORKMAPPER_SNMP_COMMUNITY` is unset at user and machine scope.
- **[Inspected]** Both runner processes had exited by 11:34. **[Deduced]** The procedure sets the variable only at process scope, so it ended with the process, whether or not `finally` ran.
- **[Inspected]** No collection evidence was found for any launch (Section 3). **[Deduced]** This is consistent with no SNMP traffic having been sent; it does not prove it.

V6 is therefore **not verified**, not passed.

### 5. Credential incident

- **[Operator]** At launch 5 the operator, unfamiliar with the term "SNMP community", entered an unrelated administrative credential (a firewall administrator password) at the masked community prompt. The operator was then instructed to press Ctrl+C and close the window; completion was not confirmed.
- **[Deduced]** No evidence indicates the credential was transmitted on the network: no collection evidence was found, and the inspected artifacts are consistent with termination at the credential prompt (Section 3). Transmission is not ruled out by measurement.
- **[Deduced]** The runner provides no path for the credential to reach a runner artifact before `main.py` starts, and no later-stage artifact was found (Section 3). The runner holds the prompt value only in a `SecureString`, a short-lived local variable and the process-scoped environment variable. It writes no artifact before `main.py` starts other than the step log and targets file, and neither is derived from the prompt value. **Not verified:** no leak scan was run against any file.
- **Launch 6:** what, if anything, was entered at its community prompt is **unknown**. The same evidence applies: no collection evidence was found.
- **Not recorded:** the credential value appears nowhere in this report or in the local manifest.
- **Rotation:** **[Deduced]** no evidence indicates exposure beyond the operator's own session. Because exposure was not ruled out by measurement, the file-level leak check was not performed and launch 6 is unexplained, rotating the affected credential as a precaution remains the owner's decision.

### 6. Limitations retained

- **Replay MATCH limitation.** Replay was not run. In any future collection, `Result : MATCH` covers **relationship rows only**. It does not prove exact equality of canonical identities by comparison; that rests on VER-029.
- **Baseline waiver.** The protected baseline was preserved byte for byte **[Inspected]**, but its identity as the 2026-09-04 historical dataset is **unverified**. The owner waived the requirement; no independent hash established it.
- **No raw artifacts committed.** The baseline backup, targets file, runner, step logs and run manifest remain in gitignored `output\` **[Inspected: gitignore probes]**.

---

## Part 2: Findings

### 7. SNMP availability

**[Operator]** SNMP is not enabled on any device on the production network, including the firewalls, the switches and all other infrastructure. The operator checked device configurations directly.

**Not measured.** No SNMP query was sent, so OPS-001 produced no reachability, responder or timeout counts.

**[Deduced]** If the operator report is accurate, none of the three committed relationship providers can produce evidence on this network as currently configured:

| Provider | Category | Usual source | Available, if the report holds |
|---|---|---|---|
| `SnmpArpNeighborProvider` | `arp_neighbor` | Routing firewall, L3 switches | No |
| `SnmpBridgeFdbProvider` | `bridge_fdb` | Managed switches | No |
| `SnmpLldpNeighborProvider` | `connected_to` | Managed switches, some APs and phones | No |

**[Deduced]** This is consistent with ARCH-026, which found zero relationship observations in the production dataset without establishing whether SNMP evidence existed. The operator report, if accurate, explains that result. It is not a measurement.

### 8. Not measured

Discovery host counts, SNMP reachability, relationship observations and canonical edges, Appendix A exclusion buckets, corroboration states, fan-out and classification comparisons were planned (procedure Section 10) but are **not available**, because no collection evidence exists. No values are inferred for them.

---

## Part 3: Limits and Next Steps

### 9. What this report does not show

- Any measured SNMP behavior. The SNMP finding is an operator report.
- How launches 5 and 6 ended, or whether the step 4 `finally` block ran for either.
- A completed credential leak scan.
- Complete network coverage, physical topology, physical connectivity or any gateway relationship.
- Exact production identity equality by comparison, or classification cost.

### 10. Operational lessons

- **Credential readiness before launch.** The handoff must explain what an SNMP read-only community is, state that it comes from the network owner, forbid substitution, and have the operator confirm it is in hand before launching.
- **Unreported launches.** Launch 6 was discovered only by inspection. Every launch should be reported, including how it ended.
- **Interpreter.** The runner relies on `python` resolving to the project virtual environment. A future run should put `venv\Scripts` first on `PATH` and verify it before launch.
- **Buffered input.** Launch 4's empty answer is suspected, not established, to have been a keystroke buffered during the long pre-flight. The gates fail safe either way. A future procedure could flush the console input buffer before each prompt, which would remove this possible cause.
- **Cleanup evidence.** The runner logs nothing from the step 4 `finally` block or on Ctrl+C. A future runner could log a non-secret line from `finally` after its cleanup statements run. Such a line would be evidence that those cleanup operations executed. It would not prove that every copy of the credential was removed: it would say nothing about copies outside the cleared variables, and it would be absent if the window were closed before `finally` ran.

### 11. Recommendation

1. **Close OPS-001** as not executed, with no production evidence collected (owner decision).
2. **Obtain the operator's account of launch 6** and of how launch 5 ended. Record both in the local manifest; neither changes the closing decision.
3. **Do not add or extend SNMP relationship providers** for this network while SNMP remains disabled.
4. **Review alternative evidence sources against existing architecture before implementation; create an ARCH report or ADR where that review warrants one.** Candidates include host-side evidence (for example default route or DHCP option 3, as identified in ARCH-026). Gateway inference is among the OPS-001 non-goals.
5. **Any future collection requires fresh owner authorization.** This closure does not carry the 2026-10-19 authorization forward. If SNMP is enabled later (v2c, read-only, ACL-restricted to the scanner, through the network owner's change process), a new run also requires revalidation of:
   - **scope:** subnets, devices and collection window;
   - **environment:** scanner, interpreter, tools and the pinned application baseline;
   - **credential readiness:** a confirmed read-only community in the operator's hands before launch;
   - **procedure applicability:** whether OPS-001 at `080363b`, or a reviewed successor, still fits the network and code at that time.

   Re-validating the pinned baseline in step 1 is not sufficient on its own.
