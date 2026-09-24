# VER-RULE-008 Verification Report: Infrastructure Vendor Classification

Independent verification of RULE-008 (`EdgeRouterRule` and the `SwitchVendorRule` TP-Link identifier extension), commit `e8f7fd88c5f0a1afa1859a31154a2fe390e8de79` ("FEAT-RULE-008: Classify EdgeOS routers and TP-Link switch identifiers"), against `docs/plans/PLAN-RULE-008-Infrastructure-Vendor-Classification.md`.

**Commit under verification:**
```
$ git rev-parse HEAD
e8f7fd88c5f0a1afa1859a31154a2fe390e8de79

$ git log -1 --oneline
e8f7fd8 FEAT-RULE-008: Classify EdgeOS routers and TP-Link switch identifiers
```

This is an independent verification pass. The FEAT-RULE-008 implementation report was not relied upon for any claim below — every check was re-run from scratch: source was re-read directly via `git show HEAD:...`, a fresh 27-case unit-level battery was written independently (not reusing `tests/test_edge_router_rule.py` or the TP-Link additions to `tests/test_switch_vendor_rule.py`), the pre-RULE-008 baseline was rebuilt fresh via `git archive a038289`, and the full 244-device production replay was re-executed against that fresh baseline.

## 1. Verification Summary

`EdgeRouterRule` and `SwitchVendorRule` were read directly from `HEAD` and confirmed to match the approved plan exactly. A fresh, independently-written 27-case battery (not the implementation sprint's own test file) was run against both rules directly, covering every required positive case, every required negative case, case-insensitivity, and deterministic evidence precedence when both EdgeOS HTTP-title and UbiquitiRouterUI TLS evidence are present on the same device. `DeviceClassifier`'s live rule list was read directly and compared, entry-by-entry, against the plan's approved 13-rule ordering — exact match. Four full-pipeline cases (genuine AP, real EdgeOS shape, real TP-Link switch shape, and the Cloud Key device) were run through the live `DeviceClassifier`, using `get_last_rule_results()` to confirm winning-rule identity and pipeline stopping point, not just final `device_type`. `git diff a038289..e8f7fd8` was inspected for every file named in the sprint's regression/scope check — exactly 9 files changed, and among existing rule files only `switch_vendor_rule.py`, limited to the one approved keyword plus its documentation. The required 244-device production replay was performed by rebuilding the pre-RULE-008 baseline fresh from `git archive a038289` into an isolated package copy (confirmed to contain zero references to `EdgeRouterRule` and no `"tp-link switch"` keyword), then classifying all 244 real devices from `output/Test Network.nmproj` against both the baseline and the current code. The full test suite and the project's full-validation tool were re-run.

## 2. PASS / FAIL Determination

**PASS.**

## 3. Acceptance Criteria Checklist

(Against PLAN-RULE-008 Section 13, as amended.)

| # | Criterion | Result |
|---|---|---|
| 1 | `EdgeRouterRule` matches only `{"edgeos", "ubiquitirouterui"}`, case-insensitive, via `first_matching_identifier`, no vendor-bare-match or hostname trigger | ✅ PASS |
| 2 | `SwitchVendorRule.SWITCH_IDENTIFIER_KEYWORDS` gains exactly one new entry, `"tp-link switch"`; no other logic changes | ✅ PASS |
| 3 | `DeviceClassifier` includes `EdgeRouterRule` at position 5; `SwitchVendorRule`'s own position unchanged | ✅ PASS |
| 4 | No existing rule file's classification logic changes other than the one-line keyword addition | ✅ PASS |
| 5 | Full test suite passes; all three benchmarks 100% | ✅ PASS (729 passed, 0 failed/errors/skipped; 100% × 3) |
| 6 | Exactly 5/244 devices change; all other 239/244 retain both final type and winning-rule identity | ✅ PASS |
| 7 | `172.16.100.89` (UniFi OS/CloudKey) remains `unknown`; no code targets it | ✅ PASS |

## 4. EdgeRouterRule Verification

Source read directly via `git show HEAD:networkmapper/classification/rules/edge_router_rule.py`:

- **Uses only `first_matching_identifier()`:** confirmed — `classify()` contains exactly one call to it, and no other evidence-reading call.
- **Identifier keywords are exactly `{"edgeos", "ubiquitirouterui"}`:** confirmed by direct read of `EDGE_ROUTER_IDENTIFIER_KEYWORDS`.
- **Case-insensitive matching:** confirmed at the helper level — `first_containing()` (which `first_matching_identifier` delegates to) lowercases both the candidate value and compares against the (already-lowercase) keyword set. Independently exercised: `"EDGEOS"` and `"UBIQUITIROUTERUI"` both match.
- **Reads only the intended evidence paths:** confirmed via `first_matching_identifier`'s own source (`git show HEAD:networkmapper/classification/evidence_helpers.py`) — its fixed check order is `product`, `HTTP title`, `TLS certificate subject`, `TLS certificate issuer`, `HTTP authentication realm`, `SNMP sysDescr`, exactly the six paths required. `EdgeRouterRule` passes `device.services` and `device.snmp_sys_descr` and nothing else.
- **No vendor-bare-match branch:** confirmed by direct grep — `device.vendor` does not appear anywhere in the file. Independently exercised: a bare `vendor="Ubiquiti"` device with no identifier evidence does not match.
- **No hostname branch:** confirmed by direct grep — `device.hostname` does not appear anywhere in the file. Independently exercised: an AP-shaped Ubiquiti hostname (`"U6-LR-Lobby"`) with no identifier evidence does not match.
- **Produces `DeviceType.ROUTER` only on a match:** confirmed — the only `RuleResult(matched=True, ...)` branch sets `suggested_device_type=DeviceType.ROUTER`; the no-match branch sets `None`.

**Fresh independent test results (14/14 EdgeRouterRule cases passed):**

| Case | Result |
|---|---|
| EdgeOS HTTP title → ROUTER | ✅ |
| UbiquitiRouterUI TLS subject → ROUTER | ✅ |
| UbiquitiRouterUI TLS issuer → ROUTER | ✅ |
| SNMP sysDescr containing EdgeOS → ROUTER | ✅ |
| Case-insensitive `"EDGEOS"` → matched | ✅ |
| Case-insensitive `"UBIQUITIROUTERUI"` → matched | ✅ |
| Bare Ubiquiti vendor, no identifier → no match | ✅ |
| AP-shaped Ubiquiti hostname, no identifier → no match | ✅ |
| Unrelated non-Ubiquiti evidence → no match | ✅ |
| Both EdgeOS HTTP title + UbiquitiRouterUI TLS present → matched, ROUTER | ✅ |
| Deterministic precedence: HTTP title wins over TLS | ✅ |
| Reason string names `HTTP title` and `EdgeOS` when both present | ✅ |
| No `device.vendor` reference in `classify()` source | ✅ |
| No `device.hostname` reference in `classify()` source | ✅ |

The deterministic-precedence case reproduces the real production evidence shape exactly (all 3 real EdgeOS devices carry both HTTP title and TLS evidence simultaneously): with both present, the match resolves to the HTTP title tier (`label="HTTP title"`, `value="EdgeOS"`), and the rule's `reason` string reads `"Detected HTTP title 'EdgeOS' matched known EdgeOS router identifier."` — never the TLS tier. This is a direct consequence of `first_matching_identifier`'s fixed check order (product → HTTP title → TLS subject → TLS issuer → HTTP auth realm → SNMP sysDescr), verified against that helper's own source, not assumed.

## 5. SwitchVendorRule Verification

Source read directly via `git show HEAD:networkmapper/classification/rules/switch_vendor_rule.py`:

- **`SWITCH_IDENTIFIER_KEYWORDS` gained exactly `"tp-link switch"`:** confirmed — the set reads `{"procurve", "edgeswitch", "tp-link switch"}`; the two pre-existing entries are byte-identical to their pre-RULE-008 form (confirmed via `git diff a038289..e8f7fd8` — the only change to the line is the appended third element and its preceding docstring).
- **No bare `"tp-link"`/`"tplink"` trigger introduced:** confirmed by grep — neither bare string appears anywhere in the file.
- **No new TP-Link-specific branch or helper:** confirmed — `classify()`'s control flow is unchanged (cisco-vendor check → identifier-tier check via `first_matching_identifier` → hostname+management-signal check → no-match); the TP-Link keyword participates in the same pre-existing identifier-tier check that already serves `"procurve"`/`"edgeswitch"`, with no new code path.
- **Existing vendor and other switch logic unchanged:** confirmed — `git diff a038289..e8f7fd8 -- .../switch_vendor_rule.py` shows exactly one hunk, touching only the comment block and the `SWITCH_IDENTIFIER_KEYWORDS` line; every other line in the file is untouched.

**Fresh independent test results (7/7 SwitchVendorRule cases passed):**

| Case | Result |
|---|---|
| `product="TP-LINK switch http admin"` → SWITCH | ✅ |
| Case-insensitive `"tp-link SWITCH http admin"` → SWITCH | ✅ |
| Bare `vendor="TP-Link Technologies"`, no product evidence → no match | ✅ |
| Bare `vendor="TP-Link Systems"`, no product evidence → no match | ✅ |
| Existing ProCurve product-string case still → SWITCH | ✅ |
| Existing EdgeSwitch HTTP-title case still → SWITCH | ✅ |
| Static keyword-set equality check | ✅ |

## 6. Rule-Ordering Verification

`DeviceClassifier()._rules` was introspected live (not merely read as text) and its 13 entries compared programmatically against the plan's approved order:

```
1.  ServerHostnameRule        8.  SwitchVendorRule
2.  NetworkApplianceRule      9.  CameraVendorRule
3.  HypervisorHostnameRule    10. WindowsServerRule
4.  UbiquitiAccessPointRule   11. PrinterVendorRule
5.  EdgeRouterRule            12. DellWorkstationRule
6.  SonicWallFirewallRule     13. WindowsWorkstationRule
7.  VoiceVendorRule
```

Exact match, confirmed by an `assert` comparing the live class-name list against the expected list — no divergence.

`git diff a038289..e8f7fd8 -- networkmapper/classification/device_classifier.py` shows the only changes are: one new import line, `EdgeRouterRule()` inserted once into the list (immediately after `UbiquitiAccessPointRule()`, immediately before `SonicWallFirewallRule()`), and docstring prose. **`EdgeRouterRule` is confirmed the sole insertion** — every one of the 12 pre-existing rules retains the identical relative order to every other pre-existing rule (no reordering, only a single insertion point).

Full-pipeline confirmation via `get_last_rule_results()` (winning-rule identity and exact stopping point, not just final type):

| Case | Final type | Winning rule | Rules evaluated |
|---|---|---|---|
| Genuine UniFi AP (`"U6-LR-Lobby"` hostname, no EdgeOS evidence) | ACCESS_POINT | `UbiquitiAccessPointRule` (position 4) | 4 |
| Real EdgeOS evidence shape (172.16.100.4) | ROUTER | `EdgeRouterRule` (position 5) | 5 |
| Real TP-Link switch evidence shape (172.16.102.12) | SWITCH | `SwitchVendorRule` (position 8) | 8 |
| Cloud Key evidence shape (172.16.100.89) | UNKNOWN | none (falls through all 13) | 13 |

This confirms `UbiquitiAccessPointRule` still wins before `EdgeRouterRule` is ever reached for a genuine AP, `EdgeRouterRule` wins for the real EdgeOS shape, and `SwitchVendorRule` wins for the real TP-Link switch shape — each stopping at exactly the expected pipeline position, with no other rule intercepting first.

## 7. UniFi OS / Cloud Key Rejection Verification

The exact real evidence shape for `172.16.100.89` (vendor `Ubiquiti`, `http_title="UniFi OS"` on port 443 with `tls_subject`/`tls_issuer` CN=`unifi.local`, and `tls_subject`/`tls_issuer` CN=`CloudKey`/org=`Ubiquiti Networks` on port 8443, plus OpenSSH on 22 and Apache Tomcat on 8080) was reproduced and run through the live `DeviceClassifier`. Result: **`UNKNOWN`**, falling through all 13 rules with no match (confirmed via `get_last_rule_results()`: 13 rules evaluated, zero matched).

Confirmed no RULE-008 code targets this device by any path:
- `"UniFi OS"` — grepped across `edge_router_rule.py` and `switch_vendor_rule.py`: zero occurrences.
- `"CloudKey"` / `"cloudkey"` — grepped across both files: zero occurrences.
- Bare Ubiquiti vendor as ROUTER — confirmed absent in Section 4 (no `device.vendor` reference in `EdgeRouterRule` at all).
- Cloud Key as SERVER — confirmed: `NetworkApplianceRule` (the only rule that ever maps appliance-identifier evidence to `SERVER`) was not modified by this commit (`git diff a038289..e8f7fd8 -- .../network_appliance_rule.py` is empty), and its `NETWORK_APPLIANCE_IDENTIFIER_KEYWORDS` set (`{"readynas"}`) does not contain `"cloudkey"` or `"unifi"`.

## 8. Production Replay Results

Baseline reconstructed fresh via `git archive a038289 -- networkmapper` into an isolated package copy this verification pass built independently (confirmed by grep: zero references to `EdgeRouterRule`/`edge_router_rule`, and `SWITCH_IDENTIFIER_KEYWORDS` confirmed to be the pre-RULE-008 two-entry set). All 244 real devices from `output/Test Network.nmproj` classified against both the baseline and the current (`HEAD`) code.

| Type | Before (a038289) | After (e8f7fd8) |
|---|---:|---:|
| unknown | 127 | **122** |
| workstation | 28 | 28 |
| access_point | 26 | 26 |
| printer | 23 | 23 |
| switch | 10 | **12** |
| server | 12 | 12 |
| phone | 10 | 10 |
| router | 0 | **3** |
| hypervisor | 3 | 3 |
| camera | 3 | 3 |
| firewall | 2 | 2 |

**Exact changed-device inventory — matches the required set precisely, 5/5:**

| IP | Vendor | Before | After | Winning rule |
|---|---|---|---|---|
| 172.16.100.4 | Ubiquiti | unknown | router | EdgeRouterRule |
| 172.16.100.7 | Ubiquiti | unknown | router | EdgeRouterRule |
| 172.16.100.240 | Ubiquiti | unknown | router | EdgeRouterRule |
| 172.16.102.12 | TP-Link Technologies | unknown | switch | SwitchVendorRule |
| 172.16.102.65 | TP-Link Technologies | unknown | switch | SwitchVendorRule |

**Zero unexpected type changes.** **Zero devices outside this set changed winning-rule identity.** The required invariant — 239/244 devices retain both identical final `DeviceType` and identical winning-rule identity — was checked programmatically for every device, not spot-checked: 0 devices flagged.

`172.16.100.89` (UniFi OS/Cloud Key): `unknown` → `unknown`, confirmed in both baseline and current classification.

## 9. Regression Checklist

`git diff a038289..e8f7fd8 --name-only` — exactly 9 files changed:

```
devtools/validate.py
docs/plans/PLAN-RULE-008-Infrastructure-Vendor-Classification.md
networkmapper/classification/device_classifier.py
networkmapper/classification/rules/edge_router_rule.py
networkmapper/classification/rules/switch_vendor_rule.py
tests/test_classifier.py
tests/test_devtools_validate.py
tests/test_edge_router_rule.py
tests/test_switch_vendor_rule.py
```

Confirmed **no changes** (zero diff, or file not present in the changed-file list) to:

| Area | Result |
|---|---|
| `DeviceType` enum (`core/models.py`) | ✅ no diff |
| Classification framework contracts (`classification_rule.py`, `rule_result.py`) | ✅ no diff |
| `evidence_helpers.py` | ✅ no diff |
| Windows rules (`windows_server_rule.py`, `windows_workstation_rule.py`) | ✅ not in changed-file list |
| Printer rule (`printer_vendor_rule.py`) | ✅ not in changed-file list |
| Camera rule (`camera_vendor_rule.py`) | ✅ not in changed-file list |
| Firewall rule (`sonicwall_firewall_rule.py`) | ✅ not in changed-file list |
| AP rule (`ubiquiti_access_point_rule.py`) | ✅ not in changed-file list |
| Discovery, enrichment, exporters, serialization, CLI, reporting | ✅ none of these directories/files appear in the changed-file list |

The only existing classification-rule implementation that changed is `networkmapper/classification/rules/switch_vendor_rule.py`, and that change is limited to the one approved `"tp-link switch"` keyword plus its explanatory comment block (confirmed in Section 5 — the diff is a single hunk, no control-flow change).

## 10. Test Execution Summary

```
$ python -m pytest tests/ -q
729 passed, 27 subtests passed
0 failed, 0 errors, 0 skipped

$ python -m devtools validate --all
Tests Run: 729
Failures: 0
Errors: 0
Skipped: 0

Benchmarks:
  Dataset: enterprise    | Devices: 9 | Accuracy: 100.0% | PASS
  Dataset: homelab       | Devices: 5 | Accuracy: 100.0% | PASS
  Dataset: small_office  | Devices: 5 | Accuracy: 100.0% | PASS

Overall Result: PASS
```

## 11. Defects / Coverage Gaps

**None found.** Every claim in PLAN-RULE-008 and the FEAT-RULE-008 implementation was independently reproduced against the actual committed source at `HEAD`, not assumed from the plan or the implementation report.

One observation, not a defect: the curated benchmark fixtures (`benchmarks/enterprise`, `benchmarks/homelab`, `benchmarks/small_office`) contain no device carrying any of the RULE-008 keywords (`"edgeos"`, `"ubiquitirouterui"`, `"tp-link switch"`) — the unchanged 100% benchmark accuracy is structural (this rule pair is simply unreachable by any benchmark device), not evidence of correctness on its own. This is expected and was already flagged in PLAN-RULE-008 Section 9; unit-level and full-pipeline tests (Sections 4–6 above) are the actual coverage for this behavior, and both were independently re-verified in this pass.

## 12. Required Fixes

None.

## 13. Recommendation

**PASS.** `EdgeRouterRule`'s identifier scope, evidence paths, case-insensitivity, absence of vendor/hostname triggers, and deterministic evidence precedence; the `SwitchVendorRule` TP-Link extension's exact keyword and unchanged surrounding logic; the exact 13-rule `DeviceClassifier` ordering with `EdgeRouterRule` as the sole insertion; the Cloud Key rejection (no code targets it, confirmed `UNKNOWN`); and the exact 5-device production delta with the required 239-device winning-rule-and-classification invariant — all were independently reproduced from `HEAD`, not assumed from the plan or the implementation report. No defects were found. The sprint is complete; no further action is required.
