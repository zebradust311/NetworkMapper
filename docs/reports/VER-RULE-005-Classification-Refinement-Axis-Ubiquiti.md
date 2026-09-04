# VER-RULE-005 Verification Report: Classification Refinement (Axis Cameras + Ubiquiti AP Detection)

**Revision 2** — verifies the corrected `CameraVendorRule` (vendor AND
camera/video-specific product evidence) that replaced the original
vendor-alone design after architect review, before staging. All
Ubiquiti-related findings are unchanged from Revision 1.

## 1. Verification Summary

RULE-005 was independently re-verified against PLAN-RULE-005 (Revision 2)
by re-reading every changed file fresh, confirming no file outside
classification logic changed, running the full automated suite plus the
project's own dynamic full-validation tool, re-running all three curated
benchmark datasets through the real CLI, and — most importantly —
programmatically parsing and re-classifying all **38** real Axis device
records (not a sample) and the real Ubiquiti AP evidence from
`output/2026-09-04_111544_standard/report.md` through the real, unmocked
`DeviceClassifier`. Both reported defects are fixed, `CameraVendorRule`
now requires vendor evidence and camera/video-specific product evidence
together, and no regression was found in any area required to remain
unchanged.

## 2. PASS / FAIL Determination

**PASS.** No defects found. Two pre-existing, out-of-scope observations
are named (Section 7) but require no action from this sprint. The
corrected `CameraVendorRule`'s low recall against the real dataset (3 of
38 devices) is a deliberate, explained design tradeoff (PLAN-RULE-005
Section 2.1), not a defect.

## 3. Acceptance Criteria Checklist

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Axis Communications AB vendor **with camera/video-specific product evidence** classifies as Camera; vendor alone does not | ✅ PASS | Unit tests (`test_camera_vendor_rule.py`) covering the match case and every non-match boundary; integration tests (`test_classifier.py`); direct re-classification of all 38 real Axis device records parsed from the production report — exactly 3 (`.138`, `.140`, `.143`) → `CAMERA`, the other 35 → `UNKNOWN` |
| 2 | UniFi captive-portal redirect classifies as Wireless Access Point | ✅ PASS | Unit tests (`test_ubiquiti_access_point_rule.py`), integration test (`test_classifier.py`), and direct manual re-classification of the real captured `172.16.100.116` device (exact redirect URL/token, exact TLS subject, no hostname) → `DeviceType.ACCESS_POINT`, matched by `UbiquitiAccessPointRule`'s new path |
| 3 | Existing printer classifications still pass | ✅ PASS | Every pre-existing `test_printer_vendor_rule.py` case re-run unmodified and passing; new test confirms a genuine `"HP LaserJet Pro MFP - Status"` title (containing "hp" in ordinary context) still matches |
| 4 | Existing AP classifications still pass | ✅ PASS | Every pre-existing `test_ubiquiti_access_point_rule.py` case re-run unmodified; reason strings asserted byte-for-byte identical (Section 5.2 of the plan) |
| 5 | No regression of existing classifier behavior | ✅ PASS | Full suite (618 tests) passes; `python -m devtools validate --all` passes; all three curated benchmarks remain at 100% accuracy |

## 4. Regression Checklist

| Area | Touched? | Result |
|---|---|---|
| Discovery engine / providers | No | ✅ No regression (not in file inventory) |
| Nmap provider | No | ✅ No regression |
| Evidence collection (`ServiceEvidence`, provider observation emission) | No | ✅ No regression — both fixes operate on already-collected evidence; nothing upstream changed |
| Exporters (CSV/Markdown) | No | ✅ No regression |
| Serialization (`ProjectSerializer`) | No | ✅ No regression — confirmed `device_type.value`/`DeviceType(value)` round-trip is additive-safe for the new `CAMERA` member by direct code reading |
| CLI (`application.py`) | No | ✅ No regression |
| `DeviceClassifier` orchestration / `RuleResult` / `ClassificationRule` contracts | No | ✅ No regression — only the rule *list* gained one entry; evaluation model unchanged |
| `SwitchVendorRule`'s "Ubiquiti EdgeSwitch" detection | No | ✅ No regression — `test_ubiquiti_edgeswitch_still_classifies_as_switch_not_access_point` confirms genuine EdgeSwitch devices are unaffected by `UbiquitiAccessPointRule`'s new guest-portal path |
| Curated benchmark datasets (`homelab`, `small_office`, `enterprise`) | No | ✅ No regression — all three at 100% accuracy; no Axis or guest-portal-path fixture data exists in either dataset (confirmed by direct search) |

## 5. Test Execution Summary

```
pytest tests/test_camera_vendor_rule.py tests/test_printer_vendor_rule.py \
       tests/test_ubiquiti_access_point_rule.py tests/test_classifier.py
82 passed, 15 subtests passed

pytest tests
618 passed, 0 failed, 27 subtests passed

python -m devtools validate --all
618 tests executed, 0 failed, 0 errors
Benchmarks: Enterprise PASS, Homelab PASS, Small Office PASS
Overall Result: PASS

python -m devtools benchmark benchmarks/homelab      → 100.0% (5 devices)
python -m devtools benchmark benchmarks/small_office → 100.0% (5 devices)
python -m devtools benchmark benchmarks/enterprise   → 100.0% (9 devices)
```

Two mechanical test-count corrections were required in
`tests/test_devtools_validate.py`'s hardcoded `STANDARD_REGRESSION_TESTS`
tripwire (146 → 156 during the original implementation, then 156 → 157
after the Revision 2 correction replaced one `test_classifier.py` test
with two) — expected drift from adding/changing tests in already-curated
modules, not a defect.

## 6. Manual Verification Summary

Performed live, against **every** real captured Axis device record (all
38, programmatically parsed from the report, not a sample) and the real
Ubiquiti AP evidence, outside the test harness:

```
Axis devices (38 total, parsed from output/2026-09-04_111544_standard/report.md):
  camera : 3  -> 172.16.101.138, 172.16.101.140, 172.16.101.143
  unknown: 35 -> every other real Axis device, including the 6 devices
                 whose evidence confirms genuine Axis manufacturing
                 identity (self-signed "axis-<hex>" certs / "Axis device
                 ID Intermediate CA") but not camera-specificity

ap = Device(ip_address="172.16.100.116", hostname=None, vendor="Ubiquiti",
            services=[... exact captured SSH/HTTP/HTTPS evidence including
            the real redirect URL and real TLS subject from the report ...])
classifier.classify(ap)
# -> DeviceType.ACCESS_POINT
# Matched by: "Vendor 'Ubiquiti' and HTTP title 'Did not follow redirect
# to http://172.16.100.89:8880/guest/s/default/?ap=0c:ea:14:b7:41:9d&ec=...'
# matched known UniFi guest-portal captive-redirect evidence."
```

This is the strongest available confirmation that the corrected rule
does exactly what it is supposed to: it resolves the 3 devices whose
retained evidence genuinely names Axis's camera product line, and it
correctly declines to resolve the other 35 — including the 6 devices an
architect-rejected, less careful rule would have also matched — rather
than a reconstructed approximation of the fix.

## 7. Defects Discovered

None. Two pre-existing, out-of-scope items were identified during
investigation and are recorded (not resolved) per this project's
practice of naming rather than silently absorbing or ignoring findings
outside a sprint's scope:

- **`ServerHostnameRule`'s `"cam"` hostname keyword** would classify a
  future Axis camera with a `"cam"`-containing hostname as `SERVER`
  before `CameraVendorRule` ever runs (`ServerHostnameRule` runs first in
  `DeviceClassifier`'s ordering). Not presently triggered — all 38 real
  Axis devices in the production report have no hostname. Consistent
  with this codebase's existing, deliberate precedent that hostname-based
  rules already outrank every vendor rule, so this is not a new risk
  `CameraVendorRule` introduces; it is a pre-existing characteristic of
  `ServerHostnameRule` itself, which appears deliberate (named explicitly
  in its own docstring) and whose original intent this investigation
  could not establish. Retained as out-of-scope per explicit instruction.
- **`MarkdownExporter`'s pluralization table has no `"Camera"` entry**,
  so report section headings render `"Camera"` rather than `"Cameras"` —
  identical, pre-existing fallback behavior already exhibited by
  `DeviceType.PHONE`. Reporting code is outside this sprint's scope.

**Not a defect, but recorded for completeness:** the corrected rule
leaves 35 of the 38 real Axis devices in this deployment `UNKNOWN`, even
though the operator has confirmed by site knowledge that all 38 are
cameras. This is the intended, disclosed behavior of the narrowest
defensible policy (PLAN-RULE-005 Section 2.1) — not a gap this
verification pass is flagging as needing a fix.

## 8. Required Fixes

None.

## 9. Recommendation

**PASS.** RULE-005 (Revision 2) correctly resolves both reported
production classification defects using only evidence genuinely present
and genuinely specific to each device category, is confirmed against
*every* real device the sprint was chartered against (not a sample or a
synthetic reconstruction), introduces no regression in classification,
discovery, evidence collection, exporting, serialization, CLI, or
reporting, and stays within its approved, narrowly-scoped file inventory.
No further action is required before this work is considered complete.
