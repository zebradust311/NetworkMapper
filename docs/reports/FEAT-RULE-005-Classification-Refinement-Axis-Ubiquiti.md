# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No

Recommended Next Sprint:
None identified as a direct follow-on. `ServerHostnameRule`'s "cam"
hostname keyword (Section 1.4 of PLAN-RULE-005) is named as a
pre-existing, unresolved risk for a future Axis-camera-with-hostname
scenario, not scheduled here.

---

## Summary

Implements PLAN-RULE-005 exactly, including a Revision 2 correction from
architect review before staging (see below). Two real production
classification defects, both confirmed against the actual scan report
(`output/2026-09-04_111544_standard/report.md`) rather than assumed:

1. **Axis Communications AB cameras classified `Unknown`.** No rule
   existed for this vendor, and `DeviceType` had no `CAMERA` member. Added
   `DeviceType.CAMERA` and a new `CameraVendorRule`.

   **Revision 2 correction:** the first implementation matched on vendor
   identity alone (`"axis communications"` present anywhere in `vendor`).
   Architect review rejected this before staging — Axis Communications
   also makes non-camera network products (door controllers, network
   audio, PoE switches, encoders), so vendor identity is manufacturer
   identity, not device-category identity. Re-investigating the retained
   evidence for all 38 real Axis devices in the production report (not a
   sample) found three genuine evidence tiers: 25 devices have nothing
   beyond a generic embedded web server and no distinguishing title; 6
   devices (`.130`, `.134`, `.136`, `.142`, `.144`, `.135`) present an
   Axis self-signed certificate or device-identity CA — confirming
   genuine Axis manufacturing identity, but not camera-specificity, since
   any Axis network product would look identical by this evidence alone;
   and exactly 3 devices (`.138`, `.140`, `.143`) present a TLS
   certificate issued by `"AXIS Camera Station root certificate"` — Axis's
   own camera/video-management-software product, the one string in the
   entire dataset that names Axis's camera line specifically. The rule
   now requires vendor evidence **and** that identifier together
   (`CAMERA_PRODUCT_IDENTIFIER_KEYWORDS = ("axis camera station",)`),
   matching only those 3 of 38 real devices and leaving the other 35
   `UNKNOWN` — a deliberate, narrow, low-recall/zero-false-positive
   tradeoff explained in PLAN-RULE-005 Section 2.1.
2. **Ubiquiti UniFi access points classified `Printer`.** Root-caused to
   two independent, confirmed mechanisms, both fixed on their own merits
   rather than by reordering rules:
   - `PrinterVendorRule`'s bare `"hp"` keyword incidentally matched a
     substring inside a UniFi guest-portal redirect's opaque, random-looking
     ticket token, surfaced via nmap's `"Did not follow redirect to
     ..."` notice in `http_title`. Fixed by excluding that specific,
     fixed-format scanner notice from `PrinterVendorRule`'s identifier
     search — scoped to that one rule, not the shared helper every other
     rule also uses.
   - `UbiquitiAccessPointRule` required a non-empty hostname
     unconditionally, but every real affected access point reports none.
     Fixed by adding a second, hostname-independent match path: the same
     guest-portal redirect URL (`/guest/s/default/`), recognized as
     UniFi-specific evidence.

Both fixes were verified directly against the real captured evidence
strings from the production report, not only against synthetic test
fixtures (see Validation Performed).

## Files Changed

| File | Change |
|---|---|
| `networkmapper/core/models.py` | Added `DeviceType.CAMERA = "camera"`. |
| `networkmapper/classification/rules/camera_vendor_rule.py` | New. `CameraVendorRule` — requires vendor keyword `"axis communications"` AND product identifier `"axis camera station"` together (Revision 2). |
| `networkmapper/classification/device_classifier.py` | Registered `CameraVendorRule` between `SwitchVendorRule` and `PrinterVendorRule`; extended the ordering-rationale docstring. |
| `networkmapper/classification/rules/printer_vendor_rule.py` | Added `_REDIRECT_NOTICE_PREFIX` and `_without_redirect_notice_titles()`; applied it inside `_find_printer_vendor_identifier()`. |
| `networkmapper/classification/rules/ubiquiti_access_point_rule.py` | Added `UNIFI_GUEST_PORTAL_TITLE_KEYWORDS` and `_find_guest_portal_identifier()`; restructured `classify()` to consult it whenever hostname evidence doesn't match, preserving every existing reason string byte-for-byte. |
| `tests/test_camera_vendor_rule.py` | New. Unit tests for `CameraVendorRule`, including explicit boundary tests proving vendor-alone, and vendor-plus-generic-Axis-branding, both correctly do *not* match (Revision 2). |
| `tests/test_printer_vendor_rule.py` | Added 3 regression tests reproducing and closing the redirect-notice/`"hp"` collision. |
| `tests/test_ubiquiti_access_point_rule.py` | Added 4 tests for guest-portal HTTP-title matching, with and without hostname, plus a non-Ubiquiti-vendor negative case. |
| `tests/test_classifier.py` | Added 4 integration-level regression tests: Axis vendor + `"AXIS Camera Station"` evidence → `CAMERA`; Axis vendor alone (generic evidence) → `UNKNOWN` (Revision 2); the UniFi guest-portal fix; and a switch-vs-access-point non-regression guard. |
| `tests/test_devtools_validate.py` | Updated the fast-regression-suite's hardcoded expected test count twice (146 → 156 → 157) — a mechanical consequence of test methods added/changed in modules already in `STANDARD_REGRESSION_TESTS`; no test module list changed. |

No changes to discovery, the Nmap provider, evidence collection,
exporters, serialization logic, CLI, or reporting code.

## Validation Performed

- `pytest tests` — 618 passed, 0 failed (up from 598 passed pre-sprint).
- `python -m devtools validate --all` — full dynamic test discovery (618
  tests) plus all three curated benchmark datasets (`enterprise`,
  `homelab`, `small_office`), all PASS at 100% accuracy, unchanged from
  pre-sprint.
- `python -m devtools benchmark benchmarks/homelab` /
  `benchmarks/small_office` / `benchmarks/enterprise` — each independently
  re-run via the real CLI; 100% accuracy on all three, confirming neither
  curated dataset's existing Ubiquiti entries (matched via hostname,
  untouched by this sprint) regressed.
- **Direct re-classification against every real captured Axis device**
  (all 38, not a sample) and the real Ubiquiti AP evidence from
  `output/2026-09-04_111544_standard/report.md`, parsed programmatically
  from the report and run through the real `DeviceClassifier`:
  - **3 of 38** real Axis devices (`172.16.101.138`, `.140`, `.143` — the
    `"AXIS Camera Station"` TLS-issuer devices) → `DeviceType.CAMERA`.
  - The other **35 of 38** real Axis devices → `DeviceType.UNKNOWN`,
    confirmed as the intended, evidence-honest outcome, not a gap (Section
    2.1 of PLAN-RULE-005 explains the tradeoff explicitly).
  - `172.16.100.116` (Ubiquiti AP, real captured redirect `http_title` and
    `tls_subject`, no hostname) → `DeviceType.ACCESS_POINT`, matched by
    `UbiquitiAccessPointRule`'s new guest-portal path (previously
    `PrinterVendorRule` → `Printer`).

## Known Issues

- **`ServerHostnameRule`'s `"cam"` hostname keyword** (unrelated code,
  not modified by this sprint) classifies any device whose hostname
  contains `"cam"` as `SERVER`, and `ServerHostnameRule` runs before
  every vendor rule including the new `CameraVendorRule`. All 38 real
  Axis cameras in the production report report no hostname, so this is
  not presently triggered, but a future Axis camera with a hostname such
  as `"cam-01"` would still be misclassified `SERVER` rather than
  `CAMERA`. Identified during investigation (PLAN-RULE-005 Section 1.4),
  deliberately left unresolved — its apparent deliberateness (named
  explicitly in `ServerHostnameRule`'s own docstring) and unclear
  original intent make it a separate decision, not an incidental fix to
  fold into this sprint.
- **`MarkdownExporter`'s device-type pluralization table has no `"Camera"`
  entry**, so a Markdown report's Camera section heading will render as
  singular `"Camera"` rather than `"Cameras"`. This is the same
  fallback `DeviceType.PHONE` already receives (also absent from that
  table) — pre-existing, accepted behavior for any device type outside
  the table, not a defect this sprint introduces, and reporting code is
  outside this sprint's scope regardless.

## Next Recommended Sprint

None required as a direct follow-on to this sprint. If a future scan
surfaces an Axis camera (or any device) with a `"cam"`-containing
hostname misclassified as `SERVER`, that would be the trigger to revisit
`ServerHostnameRule`'s keyword list and its ordering relative to
`CameraVendorRule` together, as its own scoped decision.
