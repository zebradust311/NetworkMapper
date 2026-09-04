# Status

Plan Drafted, Revision 2 (architect review correction to Section 2 / `CameraVendorRule`) — Pending Engineer Approval

Revision 2 replaces Revision 1's bare-vendor `CameraVendorRule` (vendor
identity alone → `CAMERA`) after architect review found it encodes a
site-specific fact (all 38 Axis devices in this one deployment happen to
be cameras) as a universal vendor-identity rule, which Axis Communications'
own broader product catalog (door controllers, network audio, PoE
switches, encoders) does not support in general. Section 2 is rewritten
to document a full re-investigation of the real per-device evidence and a
narrower rule requiring vendor evidence AND camera/video-specific product
evidence together. See Section 2 for the corrected design and the
false-positive tradeoff it accepts.

Authority: This document's own investigation against the current codebase and against real production evidence (see Section 1.3). No ARCH precedes it — see Section 8: no architectural concept changes, only rule content.

Implements: RULE-005 — Classification Refinement (Axis Cameras + Ubiquiti AP Detection via Captive-Portal Evidence)

Production Code Modified: Yes (see Section 4)

New ADR Required: No (Section 8)

---

## 0. Naming note

The request that produced this plan titled the work "CLASS-00X." This
project's `ROADMAP.md` shows `CLASS-001` through `CLASS-007` as Phase 2's
now-closed rule-*framework* work ("Rule framework," "Rule ordering,"
"RuleResult migration," etc.), and every rule file already in
`networkmapper/classification/rules/` cites the actively-used successor
lineage for exactly this kind of change — rule *content* refinement —
as `RULE-002` (Classification Maturation), `RULE-003` (HTTP Evidence
Utilization Expansion), `RULE-004` (SNMP Evidence Utilization). This
sprint is content refinement (two vendor-keyword additions/corrections
to existing rules), not framework work, so it is filed as **RULE-005**,
continuing the lineage its own predecessors are cited from throughout the
codebase, rather than reopening the closed `CLASS-` framework sequence.
Flagged here rather than silently substituted.

---

## 1. Investigation Findings

### 1.1 Rule framework (confirmed unchanged by this plan)

`DeviceClassifier` (`device_classifier.py`) holds an ordered
`list[ClassificationRule]` and evaluates it first-match-wins
(`classify()`, lines 55-75). Each rule is a small, independent class
implementing `ClassificationRule.classify(device) -> RuleResult`
(`classification_rule.py`). Shared substring/lookup logic lives in
`evidence_helpers.py` (`normalize_vendor`, `first_matching_identifier`,
`first_containing`, etc.) and is reused across rules. This plan adds one
new rule and edits the internals of two existing ones; it does not touch
`DeviceClassifier`, `ClassificationRule`, or `RuleResult`'s contracts.

### 1.2 Issue 1 — Axis Communications AB has no matching rule, and vendor identity alone is not camera-specific evidence

No existing rule's vendor-keyword list contains "axis" or "axis
communications" (`printer_vendor_rule.py`, `switch_vendor_rule.py`,
`voice_vendor_rule.py`, `sonicwall_firewall_rule.py`,
`dell_workstation_rule.py`, `network_appliance_rule.py` all checked).
`DeviceType` (`core/models.py`) has no `CAMERA` member at all — the
target classification is structurally impossible today, not just
unmatched. Confirmed directly against the real production report
(`output/2026-09-04_111544_standard/report.md`): 38 devices with
`Vendor: Axis Communications AB` all show every rule's "not matched"
reason and land on `Device Type: Unknown`.

**Architect review correction (Revision 2):** Revision 1 proposed
matching on vendor identity alone. Architect review rejected this: Axis
Communications' product catalog is not exclusively cameras (it also
includes door controllers, network audio, PoE switches, and encoders),
so "vendor is Axis" is manufacturer identity, not device-category
identity — encoding "all 38 Axis devices in this one deployment are
cameras" as "every device with this vendor string is a camera" would
bake a site-specific fact into a universal rule. Directed to investigate
whether the *retained* evidence for these 38 devices contains anything
more specific than vendor/MAC before designing the rule.

#### 1.2.1 Full re-investigation of the real per-device evidence

Every one of the 38 real `Vendor: Axis Communications AB` device blocks
in `output/2026-09-04_111544_standard/report.md` was parsed and compared
directly (not sampled) — see the table below. Three genuinely distinct
evidence tiers were found:

| Tier | Evidence pattern | Count | Camera/video-specific? |
|---|---|---|---|
| **A** | Generic embedded web server only — `Boa httpd` or bare `Apache httpd x.y.z`, HTTP title `"Index page"` (or no distinguishing title at all) | 25 of 38 (e.g. `172.16.101.100`–`.121`, `.123`–`.125`, `.127`, `.128`, `.133`) | **No.** `Boa httpd` and bare `Apache httpd` are common on many embedded/IoT device families, not Axis-specific; `"Index page"` is Nmap's own generic fallback title. Nothing here identifies the device beyond vendor/MAC. |
| **B** | HTTP title naming an `index.shtml` resource (`"Index page Requested resource was http://<ip>/index.shtml"`) | 2 of 38 (`172.16.101.122`, `.129`) | **No, too weak to rely on.** `.shtml` (server-side includes) is a generic, decades-old web technology used by many embedded devices, not unique to Axis. Treating it as camera evidence would repeat exactly the kind of weak-textual-coincidence reasoning Section 1.3(a) already found and rejected for `PrinterVendorRule`'s bare `"hp"`. |
| **C** | Self-branded HTTP title `"AXIS"`, self-signed TLS cert with `commonName=axis-<mac-hex>`/`organizationName=Axis Communications AB` | 2 of 38 (`172.16.101.130`, `.134`) | **Confirms genuinely Axis-manufactured, not camera-specific.** This is Axis's own device-generated identity (not a MAC-OUI guess), but the same branding and certificate-naming convention would appear identically on any Axis network product — a door controller or PoE switch would look the same by this evidence alone. |
| **D** | TLS cert issued by Axis's own device-identity CA (`commonName=Axis device ID Intermediate CA ECC <n>`), CN `axis-<mac-hex>-eccp256-1` | 4 of 38 (`172.16.101.136`, `.142`, `.144`, plus one `axis-<hex>`-only variant at `.135`) | **Same as Tier C** — confirms Axis manufacturing PKI, not a camera-specific product signal. |
| **E** | TLS cert **issued by `"AXIS Camera Station root certificate"`** | 3 of 38 (`172.16.101.138`, `.140`, `.143`) | **Yes.** AXIS Camera Station is Axis's own video-management-software product — a device whose certificate is issued by (i.e., enrolled and managed under) AXIS Camera Station is evidence of participation in an Axis *camera* fleet specifically, not merely Axis manufacturing identity. This is the one evidence string in the entire dataset that names Axis's camera/video product line by name. |
| **F** | Redirect-notice title only, no TLS fields captured | 2 of 38 (`172.16.101.139`, `.141`) | **No** — same as Tier A, nothing beyond vendor/MAC. |

25 + 2 + 2 + 4 + 3 + 2 = 38, confirmed accounted for exactly.

**Finding: the retained evidence does NOT contain nothing beyond
vendor/MAC (Tiers C/D/E exist), so this is not the "stop and report" case
— but only Tier E is genuinely camera/video-*specific* evidence.** Tiers
C and D confirm the device is authentically Axis-manufactured (stronger
than a MAC-OUI vendor guess alone), but Axis's own non-camera products
would present identically under that same evidence, so treating C/D as
"camera evidence" would still be encoding an unproven assumption
("Axis network device" implies "camera") rather than reading it from the
evidence itself — a subtler version of the same mistake Revision 1 made,
one layer down.

### 1.3 Issue 2 — root cause, confirmed against real production evidence, not assumed

Grepping the same real report for the reported symptom found the exact
mechanism, for real Ubiquiti access points in this deployment:

```
Vendor: Ubiquiti
Hostname: Unknown
...
80/tcp http
  - HTTP Title: Did not follow redirect to http://172.16.100.89:8880/guest/s/default/?ap=0c:ea:14:b7:41:9d&ec=4i5lQ9ecDwcp-LCkH1697alvguXoqmWg3DshpMadGs7OTsAnAWcJPf0sYnKy8ojRBcJi_Y1ufPWjH83WzPykZQVDKM69S_1zOYbsdo_Ap_lS_GvffHB9ChHzwyQZbAbIQidsKmk8IcTTrbO5dKbG5w
...
Matching Rule: PrinterVendorRule
Reason: Detected HTTP title '...' matched known printer vendor identifier.
```

Two independent, confirmed root causes, both traced to real evidence, not guessed:

**(a) `PrinterVendorRule` fires because of an incidental substring collision, not a printer signal.**
`PrinterVendorRule._find_printer_vendor_identifier()` calls
`first_matching_identifier()` against `SUPPORTED_PRINTER_VENDOR_KEYWORDS`,
which includes the bare two-character keyword `"hp"`. nmap's `http-title`
script emits the fixed-format notice `"Did not follow redirect to
<url>"` when a page redirects without following it — this is scanner
commentary, not device-reported identity text — and UniFi's guest-portal
redirect embeds a long opaque, effectively-random base64-like ticket
token (`&ec=...`) in that URL. In the captured evidence above, the
substring `"...DshpMadGs7OT..."` contains `hp` purely by chance
(`first_containing()` lowercases before matching, so `Hp`/`HP`/`hp`
anywhere in the token collides identically). This is confirmed, not
theoretical: manually re-running `PrinterVendorRule().classify()` against
a `Device` carrying this exact captured `http_title` reproduces the
match with the identical reason string seen in the report (verified
during this investigation).

Removing `"hp"` from the keyword list is not an option — it is required,
correctly-matching evidence for real HP printers throughout
`test_printer_vendor_rule.py` (vendor `"HP"`, HTTP title `"HP LaserJet
MFP M479 - Home"`, `http_auth_realm="HP LaserJet 4250"`, SNMP `sysDescr`
"HP LaserJet 4250, Firmware..."). The fix must exclude the *evidence
category* (a scanner's own redirect-notice commentary), not the keyword.

**(b) `UbiquitiAccessPointRule` doesn't fire, because it requires a
non-empty hostname unconditionally — and these real access points have
none.** `UbiquitiAccessPointRule.classify()`'s current gate is:

```python
if vendor != "ubiquiti" or not hostname:
    return <not matched>
```

Every real Ubiquiti AP in the captured report shows `Hostname: Unknown`
— vendor correctly normalizes to `"ubiquiti"` (an exact match, so that
half of the gate already passes), but `not hostname` is `True`, so the
rule returns not-matched *before ever consulting the strong evidence it
does have* (the TLS certificate subject `organizationName=Ubiquiti
Networks, Inc.` and, more specifically, the same guest-portal redirect
URL that trips up `PrinterVendorRule`). `UbiquitiAccessPointRule` already
runs *before* `PrinterVendorRule` in `DeviceClassifier`'s ordering — so
teaching it to recognize this evidence, independent of hostname, is
sufficient on its own to resolve these devices correctly before
`PrinterVendorRule` is ever reached for them.

**Both (a) and (b) are fixed by this plan, not just (b).** Relying solely
on (b) (winning the "which rule fires first" race) would leave `"hp"`'s
incidental-substring risk live for any *other* device whose HTTP title
happens to contain a long opaque token — not just Ubiquiti hardware. Per
the sprint's own instruction not to "simply reorder rules without
understanding why the printer rule fires," both are addressed on their
own merits.

### 1.4 A related, pre-existing landmine — confirmed, named, deliberately NOT touched by this plan

`ServerHostnameRule` (`server_hostname_rule.py`, line 54) treats `"cam"`
as a **server**-indicating hostname substring: `if "dc" in hostname or
"cam" in hostname: ... suggested_device_type=DeviceType.SERVER`.
`ServerHostnameRule` runs *first* in `DeviceClassifier`'s ordering, ahead
of every vendor rule including the new `CameraVendorRule` this plan adds.
If a real Axis camera is ever discovered with a hostname containing
`"cam"` (a highly plausible camera-naming pattern — e.g. `"cam-01"`,
`"front-cam"`), `ServerHostnameRule` would classify it `SERVER` before
`CameraVendorRule` ever runs, regardless of this plan's fix.

This is **not** the reported issue: all 38 Axis devices in the real
report show `Hostname: Unknown`, so this landmine is not presently
triggered, and is not part of Issue 1 as described. It is also
**consistent with this codebase's own established, deliberate
precedent** — every existing vendor rule (`PrinterVendorRule`,
`SwitchVendorRule`, `VoiceVendorRule`, etc.) is already subordinate to
`ServerHostnameRule`/`NetworkApplianceRule`/`HypervisorHostnameRule` in
the ordering, i.e. hostname-based identity signals already outrank
vendor-based ones project-wide. `CameraVendorRule` following that same,
already-accepted precedent is not a new risk this plan introduces.

**Named, not silently resolved, per this project's own practice**: if
Axis cameras with `"cam"`-containing hostnames are seen in a future scan,
`ServerHostnameRule`'s "cam" keyword and `CameraVendorRule`'s ordering
relative to it should be revisited together as their own, separately
scoped decision — not fixed unprompted here, since `"cam"`'s presence in
`ServerHostnameRule` appears deliberate (named explicitly in its own
docstring: `"such as those containing 'dc' or 'cam'"`) and its original
intent is not established by anything in this investigation.

### 1.5 Confirmed non-conflicts (why the two fixes are safe)

- `SwitchVendorRule`'s "Ubiquiti EdgeSwitch" HTTP-title match
  (`SWITCH_IDENTIFIER_KEYWORDS = {"procurve", "edgeswitch"}`) is
  unaffected — it matches a completely different, genuine device-reported
  title on a different device family (`172.16.100.10/.149/.153` in the
  same report, all correctly classified `SWITCH` already) and runs before
  `UbiquitiAccessPointRule`'s change is ever reached for those devices.
- No `SUPPORTED_PRINTER_VENDOR_KEYWORDS` entry appears in
  `"axis communications"` (checked every keyword by hand), so
  `CameraVendorRule`'s placement relative to `PrinterVendorRule` carries
  no precedence risk in either direction.
- Neither `benchmarks/homelab/inventory.json`'s `"office-nanohd-01"`
  (matches via existing `nanohd` hostname keyword) nor
  `benchmarks/small_office/inventory.json`'s `"UAP-AC-LR"` (matches via
  existing `uap` hostname prefix) is affected by the `UbiquitiAccessPointRule`
  change — both already match via the untouched hostname path, and neither
  has a guest-portal HTTP title in its fixture data.
- `ProjectSerializer` serializes `device_type.value` (a plain string) and
  deserializes via `DeviceType(value)` (`project/serializer.py`, lines
  51/103) — adding a new `DeviceType.CAMERA = "camera"` member is
  additive and round-trips correctly with zero serializer changes.
- `MarkdownExporter`'s `_plural_title()` has no `"Camera"` entry in its
  pluralization dict and will fall back to `_display_title()`'s generic
  singular rendering (`"Camera"`, not `"Cameras"`) for section headings —
  the same fallback `DeviceType.PHONE` already receives today (also
  absent from that dict). This is pre-existing, accepted behavior for any
  device type outside the dict, not a defect introduced here, and
  reporting code is out of this sprint's scope regardless.

---

## 2. Issue 1 Fix — `CameraVendorRule` (Revision 2: vendor AND product evidence)

**No existing camera rule system exists, per Section 1.2 — a new
`CameraVendorRule` is created.** Per the architect's explicit direction,
it requires vendor evidence **and** camera/video-specific product
evidence together — never vendor alone:

```python
SUPPORTED_CAMERA_VENDOR_KEYWORDS = ("axis communications",)
CAMERA_PRODUCT_IDENTIFIER_KEYWORDS = ("axis camera station",)
```

`"axis communications"` (the two-word phrase), not a bare `"axis"`, is
used deliberately — directly applying the lesson of Section 1.3(a):
prefer a longer, more specific phrase over a short one wherever the
evidence supports it, to avoid this rule becoming a future source of the
same class of incidental-substring risk.

`"axis camera station"` is the identifier tier, checked via the existing
`first_matching_identifier()` helper (product, HTTP title, TLS
subject/issuer, HTTP auth realm, SNMP `sysDescr`, in that order — the
real evidence lives in `tls_issuer`) — the same established shape
`PrinterVendorRule`/`SwitchVendorRule`/`SonicWallFirewallRule` already
use for their own identifier tiers. Unlike those rules, which treat a
matched identifier as sufficient on its own (no vendor requirement),
`CameraVendorRule` requires **both** the vendor gate and the identifier
match — the literal "vendor AND product evidence" the architect
specified, and a deliberately more conservative choice here since the
vendor string alone carries no product-category information for this
particular vendor.

### 2.1 Why Tier E only, and the tradeoff this accepts

Applying this rule against the real 38-device dataset (Section 1.2.1)
classifies exactly **3 of 38** devices as `CAMERA` (Tier E:
`172.16.101.138`, `.140`, `.143`) and leaves the remaining **35 of 38**
`UNKNOWN` (Tiers A, B, C, D, F) — including the 6 devices (Tiers C/D)
whose evidence confirms genuine Axis manufacturing identity, just not
camera-specificity.

**This is the narrowest defensible policy given what the retained
evidence actually supports, and it is deliberately low-recall in
exchange for zero false-positive risk:**

- **False-negative cost (accepted):** most real cameras in this
  deployment (32 of 35 non-`CAMERA` devices, if the operator's own
  on-site knowledge is correct that all 38 are cameras) will report
  `UNKNOWN` rather than `CAMERA`. An operator reading the report loses
  the summary convenience of seeing "38 cameras" at a glance for this
  fleet.
- **False-positive cost (avoided):** including Tiers C/D would classify
  *any* Axis network product presenting that same self-signed
  certificate/branding pattern as `CAMERA` — a door controller, a PoE
  switch, an encoder — with no product-specific evidence backing that
  label. Because `DeviceClassifier` is first-match-wins and stops at the
  first match, a wrongly-labeled `CAMERA` result is not just imprecise
  reporting; it forecloses whatever more accurate classification a
  future rule might otherwise have produced for that device, and reads
  as a confident, evidence-backed claim to anyone consuming the report
  even though it isn't one for that device.
- **Why this direction is the right tradeoff for a classification
  engine reused across sites:** `DeviceClassifier`'s rules are shared,
  global policy applied to every future scan of every future site — a
  false `CAMERA` claim actively misinforms an operator at some other
  site with Axis door controllers or PoE gear, whereas a false `UNKNOWN`
  merely withholds a label a human can still supply by inspection. This
  matches `RuleResult`'s own established design principle
  (`docs/architecture/classification.md`): explainable, evidence-backed
  claims only, deterministic and conservative rather than inferential.

If the project later wants Tier C/D coverage, that is a distinct,
explicit product-catalog decision (e.g., "treat any Axis self-identified
device as a camera unless proven otherwise") that should be proposed and
reviewed on its own terms, with its own stated false-positive tolerance
— not folded into this correction silently.

`DeviceType.CAMERA = "camera"` is added to `core/models.py`'s
`DeviceType` enum (Section 1.5 confirms this is additive-only and
serialization-safe). This is the one unavoidable `core/models.py`
change: "DeviceType = Camera" cannot exist without it, and `core/models.py`
is not among the sprint's excluded areas (discovery engine, Nmap
provider, evidence collection, exporters, serialization, CLI, reporting)
— it is the shared vocabulary classification rules assign into.

`CameraVendorRule` is registered in `DeviceClassifier`'s rule list
immediately after `SwitchVendorRule` and before `PrinterVendorRule`.
Per Section 1.5, its keywords don't overlap with any other rule's, so
(mirroring `NetworkApplianceRule`'s own documented precedent) this exact
position is not safety-relevant — it is placed there simply to keep the
vendor-based rules grouped together for readability.

---

## 3. Issue 2 Fix — two targeted, independent corrections

### 3.1 `PrinterVendorRule`: exclude redirect-notice HTTP titles from identifier matching

A new private helper strips `http_title` from any `ServiceEvidence` whose
title is nmap's `"Did not follow redirect to ..."` notice, before that
service list is handed to `first_matching_identifier()` — scoped to
`PrinterVendorRule._find_printer_vendor_identifier()` only:

```python
_REDIRECT_NOTICE_PREFIX = "did not follow redirect"

def _without_redirect_notice_titles(services):
    return [
        dataclasses.replace(entry, http_title=None)
        if entry.http_title and entry.http_title.strip().lower().startswith(_REDIRECT_NOTICE_PREFIX)
        else entry
        for entry in services
    ]
```

Only `http_title` is nulled on a shallow per-entry copy; `product`,
`tls_subject`, `tls_issuer`, `http_auth_realm`, and every other port's
own (non-redirect-notice) `http_title` are untouched, so a real printer
that happens to also show a redirect notice on an unrelated port remains
correctly detected via its other evidence. `_find_printer_networking()`
(the port/service-based tier) is not touched at all — the captured
evidence's open ports (22/80/443) and service names (`ssh`, `http`) never
matched printer networking signals in the first place (Section 1.3),
confirming this fix targets the actual, confirmed mechanism and nothing
broader.

**Why scoped to `PrinterVendorRule` alone, not `evidence_helpers.py`'s
shared `first_matching_identifier()`:** the sprint asks to "prefer
tightening the printer rule," and every other consumer of
`first_matching_identifier()` (`SwitchVendorRule`, `SonicWallFirewallRule`,
`NetworkApplianceRule`) uses multi-word, low-collision-risk keywords
(`"procurve"`, `"edgeswitch"`, `"sonicwall"`, `"readynas"`) with no
demonstrated redirect-notice collision risk today. Changing the shared
helper's behavior for every caller would be a wider, unrequested change
for a problem currently confirmed only in `PrinterVendorRule`'s own
`"hp"` keyword.

### 3.2 `UbiquitiAccessPointRule`: recognize the guest-portal redirect independent of hostname

```python
UNIFI_GUEST_PORTAL_TITLE_KEYWORDS = ("guest/s/default",)
```

`classify()` is restructured so the vendor gate (`vendor != "ubiquiti"`)
still short-circuits immediately, but the hostname-prefix and
hostname-keyword checks become one path *among two*, not the only path:
if hostname evidence doesn't match, a new
`_find_guest_portal_identifier()` check (searching `http_title` via the
existing `service_http_titles`/`first_containing` helpers) is now also
consulted before falling through to not-matched. A match produces
`DeviceType.ACCESS_POINT` with a new reason string naming the HTTP title
evidence explicitly. Every existing hostname-based reason string and
the final not-matched reason string are preserved byte-for-byte (Section
5.2 lists the exact preserved assertions).

`"guest/s/default"` is UniFi Network Controller's own guest-portal route
name — specific enough that requiring it *in addition to* the existing
`vendor == "ubiquiti"` gate (not as a standalone, vendor-independent
trigger) is a conservative, low-risk extension consistent with every
other rule's "identifier tier corroborates/extends a vendor or hostname
gate, never replaces it" pattern in this codebase.

---

## 4. File Inventory

| File | Change |
|---|---|
| `networkmapper/core/models.py` | Add `CAMERA = "camera"` to `DeviceType`. |
| `networkmapper/classification/rules/camera_vendor_rule.py` | **New.** `CameraVendorRule`, `SUPPORTED_CAMERA_VENDOR_KEYWORDS`. |
| `networkmapper/classification/device_classifier.py` | Import and register `CameraVendorRule` between `SwitchVendorRule` and `PrinterVendorRule`; extend the class docstring's ordering rationale. |
| `networkmapper/classification/rules/printer_vendor_rule.py` | Add `_REDIRECT_NOTICE_PREFIX`, `_without_redirect_notice_titles()`; call it inside `_find_printer_vendor_identifier()` before `first_matching_identifier()`. |
| `networkmapper/classification/rules/ubiquiti_access_point_rule.py` | Add `UNIFI_GUEST_PORTAL_TITLE_KEYWORDS`, `_find_guest_portal_identifier()`; restructure `classify()` per Section 3.2, preserving every existing reason string exactly. |
| `tests/test_camera_vendor_rule.py` | **New.** Unit tests for `CameraVendorRule` (Section 5.1). |
| `tests/test_printer_vendor_rule.py` | Add regression tests for the redirect-notice exclusion (Section 5.1), using the real captured evidence shape. |
| `tests/test_ubiquiti_access_point_rule.py` | Add tests for guest-portal HTTP-title matching, with and without hostname (Section 5.1). |
| `tests/test_classifier.py` | Add integration-level regression tests exercising the full `DeviceClassifier` for both fixed scenarios (Section 5.1). |

No changes to discovery, Nmap provider, evidence collection, exporters,
serialization *code* (only the `DeviceType` enum it already handles
generically), or CLI — confirmed against `git diff`-equivalent scope
before writing this plan (Section 1 traces every touched file to a
classification-only concern).

---

## 5. Testing Strategy

### 5.1 Required test cases (per the sprint's own list, plus the corroborating detail this investigation found)

1. **Axis vendor AND camera/video-specific product evidence classifies as
   Camera; vendor alone does not** — `tests/test_camera_vendor_rule.py`:
   the real Tier E pattern (vendor + `"AXIS Camera Station"` TLS
   issuer/subject) matches, case-insensitively on both fields; the real
   Tier A pattern (vendor alone, generic web server) does not match; the
   real Tier C/D patterns (vendor + bare `"AXIS"` title or
   `axis-<hex>`/"Axis device ID" certificate, but no "Camera Station"
   reference) do **not** match, proving the boundary is exactly where
   Section 2.1 draws it; a non-Axis vendor with `"AXIS Camera Station"`
   evidence present does not match (the vendor gate is required, not
   optional); and via the full `DeviceClassifier` in `test_classifier.py`
   for both the matching and non-matching real cases.
2. **UniFi captive-portal redirect classifies as Wireless Access Point** —
   `tests/test_ubiquiti_access_point_rule.py`: vendor `"Ubiquiti"`,
   hostname `None` (matching the real report exactly), HTTP title
   reproducing the real `"Did not follow redirect to
   .../guest/s/default/?ap=...&ec=..."` shape; also via
   `test_classifier.py` end-to-end, proving `UbiquitiAccessPointRule`
   wins before `PrinterVendorRule` is ever reached in the real pipeline
   ordering.
3. **Existing printer classifications still pass** — every existing
   `test_printer_vendor_rule.py` case (vendor keywords, product/HTTP
   title/auth-realm/SNMP identifier tiers, networking-only signals) is
   re-run unmodified; a new test confirms a *genuine* printer HTTP title
   containing `"hp"` in ordinary context (not a redirect notice) still
   matches.
4. **Existing AP classifications still pass** — every existing
   `test_ubiquiti_access_point_rule.py` hostname-based case (`UAP-`,
   `U6-`, `U7-`, `nanohd`, the `"Switch-01"` non-match, the non-Ubiquiti
   vendor non-match) is re-run unmodified, asserting byte-identical
   `reason` strings.
5. **No regression of existing classifier behavior** — full
   `tests/test_classifier.py` suite re-run; both curated benchmark
   datasets (`benchmarks/homelab`, `benchmarks/small_office`) re-run
   through the actual `BenchmarkRunner` CLI before and after, confirming
   accuracy does not regress (their two existing Ubiquiti entries already
   match via the untouched hostname path per Section 1.5, so no change is
   expected there); full project test suite re-run.

### 5.2 Exact preserved assertions (regression contract for `UbiquitiAccessPointRule`)

- `"Vendor 'Ubiquiti' and hostname 'UAP-AC-LR' matched known wireless infrastructure vendor."`
- `"Vendor 'Ubiquiti' and hostname 'U6-Pro' matched known wireless infrastructure vendor."`
- `"Vendor 'Ubiquiti' and hostname 'U7-Pro' matched known wireless infrastructure vendor."`
- `"Vendor 'Ubiquiti' and hostname 'office-nanohd-01' matched known wireless access point naming patterns."`
- `"Vendor 'Ubiquiti' and hostname 'Switch-01' did not match known wireless infrastructure vendor patterns."`
- `"Vendor 'Cisco' and hostname 'UAP-AC-LR' did not match known wireless infrastructure vendor patterns."`

---

## 6. Implementation Order

1. `DeviceType.CAMERA` in `core/models.py`.
2. `CameraVendorRule` + `tests/test_camera_vendor_rule.py` — isolable, no dependency on the other fix.
3. Register `CameraVendorRule` in `DeviceClassifier`.
4. `PrinterVendorRule`'s redirect-notice exclusion + new `tests/test_printer_vendor_rule.py` cases.
5. `UbiquitiAccessPointRule`'s guest-portal evidence path + new `tests/test_ubiquiti_access_point_rule.py` cases.
6. `tests/test_classifier.py` integration regression tests.
7. Full-suite validation, plus both benchmark datasets re-run via the real `BenchmarkRunner` CLI.

---

## 7. Scope Confirmation

This plan changes exactly: one new `DeviceType` member; one new camera
classification rule (`CameraVendorRule`) requiring both Axis
Communications manufacturer vendor evidence **and** `"AXIS Camera
Station"` camera/video-specific product evidence together — never
manufacturer vendor evidence alone (Section 2); one new evidence-exclusion
inside an existing rule; one new evidence-matching path inside another
existing rule; and their tests. It does not modify discovery, the Nmap
provider, evidence collection, exporters, serialization logic, CLI, or
reporting code. It does not introduce any new discovery-side camera
probing (e.g. RTSP or other camera-protocol probes), a networking/port-based
detection tier comparable to `PrinterVendorRule`'s 515/631/9100 tier, a
generalized "redirect-notice filtering" framework (Section 3.1 explains
why that fix stays local to `PrinterVendorRule`), or a confidence-scoring
mechanism — `CameraVendorRule`'s product-identifier tier reuses the
existing `first_matching_identifier` helper already shared by other
rules, not a new evidence framework. `ServerHostnameRule`'s `"cam"`
hostname landmine (Section 1.4) is identified and explicitly left
unresolved, not silently absorbed into this sprint's scope.

---

## 8. ADR / ARCH Requirement

**No new ADR or ARCH is required.** Every change is a direct,
non-architectural application of the existing `ClassificationRule`/
`RuleResult` contract (ADR-002/003/004, per
`docs/architecture/classification.md`) — adding a rule, adding an
`DeviceType` value, and refining two rules' own evidence handling are all
already-established, repeatable patterns in this codebase's own history
(RULE-002 through RULE-004 did exactly this shape of change). Nothing
here changes `DeviceClassifier`'s orchestration model, `RuleResult`'s
structure, or the discovery/classification boundary ADR-008 already
governs.
