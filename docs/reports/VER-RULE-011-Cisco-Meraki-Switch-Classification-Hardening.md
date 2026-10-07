# VER-RULE-011 Verification Report: Cisco Meraki Switch Classification Hardening

Independent verification of RULE-011 against `docs/plans/PLAN-RULE-011-Cisco-Meraki-Switch-Classification-Hardening.md` as approved, including its two architect amendments: the two-part replay contract (Section 12, criterion 6) and the exclusion confined to the bare vendor tier (Section 6; Section 12, criterion 7).

**Commit under verification:**
```
ed4a313e964ade0d96f19b46f0b11e848f498eea
FEAT-RULE-011: Harden Cisco Meraki switch classification
```
Parent: `0df44a15b46070b93b5a421df1178e3ef85c3876`, the pre-RULE-011 baseline.

This is an independent verification pass. No claim below relies on the FEAT-RULE-011 implementation report or on its replay output. Every check was re-run from scratch:

- **Source:** re-read from the commit with `git show ed4a313:...` and `git diff ed4a313~1 ed4a313`.
- **Package exports:** both packages were exported fresh with `git archive` into isolated scratch directories. The baseline came from the parent commit. The candidate came from the committed `HEAD`, not the working tree.
- **Replay harness:** written new for this pass. It does not reuse the implementation session's script.
- **Mutation test:** run in a scratch copy only, to check that the exclusion-scope regression guard actually detects the prohibited early-return shape.

No production code, test, or plan file was modified during verification.

## 1. Verification Summary

**The commit:**
- `HEAD` is `ed4a313` and its message is as expected.
- The diff against the parent touches exactly the 5 files RULE-011 intends:
  - the rule file
  - two extended test modules
  - the validation test-count check
  - the plan

**The rule (`SwitchVendorRule`):**
- The only behavioural change is a single added condition, `"meraki" not in vendor`, on the existing bare Cisco vendor branch.
- The identifier tier and the hostname tier still run after that branch declines.
- There is no early return, no new `matched=False` short-circuit, no helper-level exclusion, and no classifier-level exclusion.

**Unit tests:**
- The six required cases are present.
- A mutation test in a scratch copy confirmed that the identifier-tier and hostname-tier guards fail if the exclusion is rewritten as an early return. The guard works.

**Production replay:**
- All 244 real devices were replayed against the parent commit.
- Exactly two devices changed: 172.16.100.70 and 172.16.102.80, both from SWITCH to UNKNOWN.
- The other 242 kept the same `DeviceType`, the same winning rule, and the same reason text.
- Both genuine Cisco devices (172.16.100.1 and 172.16.100.40) remain SWITCH via `SwitchVendorRule` at position 9.

**Validation:**
- `pytest`: 753 passed.
- `devtools validate --all`: PASS, with all three benchmarks at 100.0%.

## 2. PASS / FAIL

**PASS.**

## 3. Acceptance Criteria Checklist

Against PLAN-RULE-011 Section 12.

| # | Criterion | Result |
|---|---|---|
| 1 | The bare vendor tier matches vendor strings containing `"cisco"` except those also containing `"meraki"`, case-insensitively. No other tier changed. | ✅ PASS |
| 2 | The `DeviceClassifier` rule list and ordering are unchanged. | ✅ PASS (`device_classifier.py` is not in the diff) |
| 3 | No rule file other than `switch_vendor_rule.py` changes. | ✅ PASS |
| 4 | `VoiceVendorRule` is not modified. | ✅ PASS |
| 5 | The full test suite passes, and `devtools validate --all` reports 100% on all three benchmarks. | ✅ PASS (753 passed; 100% × 3) |
| 6a | Replay: exactly two devices change, 172.16.100.70 and 172.16.102.80, both SWITCH → UNKNOWN. | ✅ PASS |
| 6b | Replay: the other 242 devices keep both the same `DeviceType` and the same winning rule. | ✅ PASS (242/242 on type, 242/242 on rule, 242/242 on reason text) |
| 7 | The exclusion is confined to the bare vendor branch: no early return, pre-filter, shared helper or classifier logic, and later higher-confidence evidence can still match. | ✅ PASS (confirmed by source review and by mutation test, Section 4) |

## 4. Rule Verification

Source read with `git show ed4a313:networkmapper/classification/rules/switch_vendor_rule.py`.

**The diff.** The only hunk in the rule file (`@@ -80,7 +80,14 @@`) does two things:
- It changes `if "cisco" in vendor:` to `if "cisco" in vendor and "meraki" not in vendor:`.
- It adds a 7-line comment above that line explaining the exclusion's scope.

The keyword sets (`SWITCH_HOSTNAME_HINTS`, `SWITCH_MANAGEMENT_PORTS`, `SWITCH_MANAGEMENT_SERVICES`, `SWITCH_PRODUCT_KEYWORDS`, `SWITCH_IDENTIFIER_KEYWORDS`), the imports, and the other tiers are all byte-identical to the parent.

| Check | Result |
|---|---|
| The Cisco vendor tier excludes vendor strings containing `"meraki"`. | ✅ Line 90: `if "cisco" in vendor and "meraki" not in vendor:` |
| The match is case-insensitive. | ✅ `vendor` comes from `normalize_vendor(raw_vendor, strip=False)`, which lowercases. Behaviour unchanged from the parent. |
| The exclusion exists only inside the bare Cisco vendor branch. | ✅ `git grep -i meraki ed4a313 -- networkmapper devtools` returns only line 90 and two comment lines, all in `switch_vendor_rule.py`. |
| No early return. | ✅ The rule still has exactly four `return RuleResult(...)` statements: bare vendor (line 91), identifier tier (105), hostname tier (139) and final fall-through (146). That is the same set as the parent. No `meraki`-conditioned return exists. |
| No `matched=False` short-circuit. | ✅ The only `matched=False` is the final fall-through at line 147, which is unchanged from the parent. |
| No helper-level exclusion. | ✅ `evidence_helpers.py` is not in the diff, and `meraki` does not appear in it. |
| No classifier-level exclusion. | ✅ `device_classifier.py` and `classifier.py` are not in the diff, and `meraki` does not appear in them. |
| The identifier tier still runs after the vendor tier declines. | ✅ Structurally, when the line-90 condition is false, control falls through to `first_matching_identifier(...)` at line 98. Behaviourally, see the next table. |

**Behavioural confirmation (committed unit tests at `HEAD`):**

| Device | Expected | Result |
|---|---|---|
| `vendor="Cisco Meraki"`, `product="EdgeSwitch"` | SWITCH via the identifier tier, with reason `Detected service product 'EdgeSwitch' matched known switch identifier.` | ✅ |
| `vendor="Cisco Meraki"`, `hostname="core-sw-01"`, ssh/22 | SWITCH via the hostname tier | ✅ |

**Mutation test (scratch copy only).** I exported a copy of `HEAD` and injected the shape the plan prohibits, ahead of the bare vendor branch:

```python
if "meraki" in vendor:
    return RuleResult(matched=False, ...)
```

Then I ran the committed `tests/test_switch_vendor_rule.py` against the mutated copy. Result: **3 failed, 20 passed.**

| Test | Outcome under the mutation | What it means |
|---|---|---|
| `test_cisco_meraki_with_existing_identifier_still_matches_identifier_tier` | Failed | Correct. The identifier tier was cut off. |
| `test_cisco_meraki_with_switch_hostname_and_management_signal_still_matches` | Failed | Correct. The hostname tier was cut off. |
| `test_cisco_meraki_vendor_alone_does_not_match` | Failed | The reason text changed. |
| `test_cisco_meraki_with_unsupported_cisco_product_documents_future_intent` | Passed | Expected. This test documents future intent only and was never meant to detect this mutation (see Section 8, observation 2). |

The guard tests therefore detect the prohibited shape.

## 5. Production Replay

**Method:**
- **Baseline:** parent `0df44a1`, exported with `git archive` into an isolated directory.
- **Candidate:** `HEAD` `ed4a313`, exported the same way.
- **Package check:** each run asserted that `networkmapper` was imported from its own export directory.
- **Input:** all 244 devices from `output/Test Network.nmproj`.
- **Isolation:** each device was deep-copied and given a fresh `DeviceClassifier`.
- **Recorded per device:** final `DeviceType`, winning rule class, winning position, rules evaluated, and winning reason. The winning rule comes from `get_last_rule_results()` paired with the classifier's rule list. The harness also asserted that exactly one matching result exists and that it is the last one evaluated, which checks the first-match stopping behaviour.

**Delta:**

| Metric | Result |
|---|---|
| Devices compared | 244 |
| Final `DeviceType` changes | **2** |
| Winning-rule changes | **2** (the same two devices) |
| Any recorded-field changes | **2** (the same two devices) |
| Same type | 242 |
| Same type and same winning rule | **242 / 242** |
| Same type and same reason text | 242 / 242 |

**Exact changed-device inventory:**

| IP | Vendor | Before (`0df44a1`) | After (`ed4a313`) |
|---|---|---|---|
| 172.16.100.70 | Cisco Meraki | SWITCH via `SwitchVendorRule` @ position 9 (9 rules evaluated) | UNKNOWN, no rule matched (14 rules evaluated) |
| 172.16.102.80 | Cisco Meraki | SWITCH via `SwitchVendorRule` @ position 9 (9 rules evaluated) | UNKNOWN, no rule matched (14 rules evaluated) |

**Genuine Cisco devices.** These are the only other devices whose vendor contains `cisco` or `meraki`:

| IP | Vendor | Before | After | Winning reason (after) |
|---|---|---|---|---|
| 172.16.100.1 | Cisco Systems | SWITCH via `SwitchVendorRule` @ 9 | SWITCH via `SwitchVendorRule` @ 9 | `Vendor 'Cisco Systems' matched known switch vendor.` |
| 172.16.100.40 | Cisco Systems | SWITCH via `SwitchVendorRule` @ 9 | SWITCH via `SwitchVendorRule` @ 9 | `Vendor 'Cisco Systems' matched known switch vendor.` |

**Distribution:**

| DeviceType | Before | After |
|---|---:|---:|
| UNKNOWN | 121 | **123** |
| WORKSTATION | 28 | 28 |
| ACCESS_POINT | 26 | 26 |
| PRINTER | 23 | 23 |
| SERVER | 12 | 12 |
| SWITCH | 12 | **10** |
| PHONE | 10 | 10 |
| CAMERA | 3 | 3 |
| FIREWALL | 3 | 3 |
| HYPERVISOR | 3 | 3 |
| ROUTER | 3 | 3 |

This matches PLAN-RULE-011 Section 9 exactly.

## 6. Regression Review

**Files changed in `ed4a313` relative to its parent** (from `git diff --name-only ed4a313~1 ed4a313`):

```
docs/plans/PLAN-RULE-011-Cisco-Meraki-Switch-Classification-Hardening.md   (new, +226)
networkmapper/classification/rules/switch_vendor_rule.py                   (+8 / -1)
tests/test_classifier.py                                                   (+60)
tests/test_devtools_validate.py                                            (+1 / -1)
tests/test_switch_vendor_rule.py                                           (+133)
```

The only change under `networkmapper/` is `switch_vendor_rule.py`. A path-filtered `git diff --name-only` over every protected area below returned no files:

| Area | Changed? |
|---|---|
| `DeviceType` (`networkmapper/core/`) | No |
| Classification framework (`classification_rule.py`, `rule_result.py`, `classifier.py`) | No |
| `DeviceClassifier` ordering (`device_classifier.py`) | No |
| `evidence_helpers.py` | No |
| `VoiceVendorRule` | No |
| `EdgeRouterRule` | No |
| `PfSenseFirewallRule` | No |
| Windows rules (`windows_server_rule.py`, `windows_workstation_rule.py`) | No |
| `PrinterVendorRule` | No |
| `CameraVendorRule` | No |
| Discovery, enrichment, exporters, serialization, CLI, reporting | No (no file outside `switch_vendor_rule.py` under `networkmapper/` changed) |
| `devtools/` (including `validate.py` and `STANDARD_REGRESSION_TESTS`) | No |

**The `tests/test_devtools_validate.py` change** is the hardcoded count in `test_run_validation_still_covers_exactly_the_standard_regression_tests`, raised from 240 to 249.
- Both extended modules, `tests.test_switch_vendor_rule` and `tests.test_classifier`, are already in `STANDARD_REGRESSION_TESTS` (`devtools/validate.py` lines 21 and 24).
- The commit adds 6 + 3 = 9 test methods, so the new count of 249 is correct.
- FEAT-RULE-007, FEAT-RULE-008 and FEAT-RULE-010 made the same kind of edit.

**Working tree.** At verification time, `git diff HEAD -- networkmapper tests devtools` is empty, so the tests and validation ran against exactly the committed code.

## 7. Test Summary

**Unit tests (`tests/test_switch_vendor_rule.py`, 17 → 23 tests at `HEAD`):**

| Required coverage | Committed test | Result |
|---|---|---|
| Cisco Meraki vendor alone → no match | `test_cisco_meraki_vendor_alone_does_not_match` | ✅ |
| Case-insensitive Meraki exclusion | `test_cisco_meraki_exclusion_is_case_insensitive` (3 subtests: `cisco meraki`, `CISCO MERAKI`, `Cisco MERAKI`) | ✅ |
| Cisco Systems unchanged | `test_genuine_cisco_systems_device_still_matches_bare_vendor_tier` (172.16.100.1's real evidence shape; asserts the bare-vendor reason) | ✅ |
| Identifier-tier regression (EdgeSwitch proxy) | `test_cisco_meraki_with_existing_identifier_still_matches_identifier_tier` (asserts the identifier-tier reason and the absence of the bare-vendor reason) | ✅ |
| Hostname-tier regression | `test_cisco_meraki_with_switch_hostname_and_management_signal_still_matches` | ✅ |
| Documented future Catalyst intent | `test_cisco_meraki_with_unsupported_cisco_product_documents_future_intent` | ✅ |
| Existing ProCurve, EdgeSwitch, TP-Link and Cisco tests | All 17 pre-existing tests unchanged and passing | ✅ |

**Full-pipeline tests** (`tests/test_classifier.py`, new class `CiscoMerakiSwitchHardeningIntegrationTest`):

| Device | Expected | Committed assertion | Result |
|---|---|---|---|
| 172.16.100.70 | UNKNOWN | `device_type == UNKNOWN`, `len(get_last_rule_results()) == 14`, no rule matched | ✅ |
| 172.16.102.80 | UNKNOWN | Same assertions | ✅ |
| 172.16.100.40 | SWITCH via `SwitchVendorRule` | `device_type == SWITCH`, `len(get_last_rule_results()) == 9`, last result matched with the bare-vendor reason | ✅ |

The production replay (Section 5) also confirmed this stopping behaviour on the real stored evidence for all four devices, including 172.16.100.1, which the integration tests cover only at unit level.

**Execution:**

| Command | Result |
|---|---|
| `python -m pytest tests/ -q` | **753 passed**, 30 subtests passed, 0 failed, 0 errors |
| `python -m pytest tests/test_switch_vendor_rule.py tests/test_classifier.py tests/test_devtools_validate.py -q` | 106 passed, 3 subtests passed |
| `python -m devtools validate --all` | **PASS**: 753 executed, 753 passed, 0 failed, 0 errors |
| Benchmark: enterprise | PASS, 100.0% accuracy |
| Benchmark: homelab | PASS, 100.0% accuracy |
| Benchmark: small_office | PASS, 100.0% accuracy |

## 8. Defects

**No defects found.** There are no code defects, no test defects, and no replay drift.

The following observations do not affect PASS:

1. **Plan bookkeeping is stale relative to the implementation (documentation only).** The plan was committed alongside the implementation without a closeout note.
   - PLAN-RULE-011 Section 10 says "no `STANDARD_REGRESSION_TESTS` entry and no test-count-tripwire bump are anticipated". The implementation correctly raised the count from 240 to 249 (Section 6), because adding test methods to modules already in `STANDARD_REGRESSION_TESTS` changes the count even when no test file is added.
   - Section 10 itself says the plan "would gain an implementation-closeout note". That note was never added.
   - The plan's Section 15 git status and its status line describe the planning sprint, not the committed state.

   Severity: low (documentation accuracy). It does not affect behaviour.
2. **The Catalyst test documents intent and does not discriminate.** `test_cisco_meraki_with_unsupported_cisco_product_documents_future_intent` passes whether or not the exclusion is wrongly turned into an early return, as the mutation test confirmed. This matches its docstring and PLAN-RULE-011 Section 11. The tests that actually enforce the guarantee are the EdgeSwitch identifier-tier test and the hostname-tier test, and both were shown to detect the prohibited shape. This is noted so that no one mistakes the Catalyst test for an enforcement test.
3. **The integration tests identify the winning rule by position, not by class name.** They assert `len(get_last_rule_results())` of 14 or 9, plus the reason text. This follows the RULE-008 and RULE-010 integration-test convention, so any future sprint that inserts or reorders a rule will need to update these counts, as before.

## 9. Recommendation

**Accept RULE-011 as verified.** Commit `ed4a313` implements PLAN-RULE-011 exactly as approved, including both architect amendments.

**Optional, not blocking:** at the next documentation touchpoint, add a short implementation-closeout note to PLAN-RULE-011 that records two things:
- the test-count change from 240 to 249, which corrects Section 10's expectation
- the final commit hash

This is the closeout note Section 10 already anticipates. No code or test change is recommended.
