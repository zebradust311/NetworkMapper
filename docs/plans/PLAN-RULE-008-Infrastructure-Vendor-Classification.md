# PLAN-RULE-008: Infrastructure Vendor Classification

**Status:** Proposed — pending architect review. Planning/investigation sprint only. No production code, test, or classifier change has been made. Nothing has been staged, committed, or pushed.

## 1. Executive Summary

This sprint investigated three infrastructure classification opportunities identified but deferred during the RULE-006/RULE-007 production investigation: Ubiquiti EdgeOS evidence (candidate for `ROUTER`), TP-Link switch product evidence (candidate for `SWITCH`), and a single UniFi OS device (candidate hypothesis: `ROUTER`).

Evidence supports implementing **two** of the three candidates, at different scopes than originally hypothesized, and rejects the third:

- **Candidate A (EdgeOS → `ROUTER`): JUSTIFIED.** Three real production devices carry an HTTP title of exactly `"EdgeOS"` and a self-signed TLS certificate whose subject/issuer common name is literally `"UbiquitiRouterUI"` — Ubiquiti's own router management UI self-identifying as a router. All three are currently `unknown`. A new identifier-tier rule, `EdgeRouterRule`, resolves all three to `ROUTER` with no vendor-bare-match fallback.
- **Candidate B (TP-Link switch evidence → `SWITCH`): JUSTIFIED, narrower than "any TP-Link device."** Of four real TP-Link-vendor devices, exactly two carry an explicit product string, `"TP-LINK switch http admin"`. The other two have vendor identity only, no product evidence, and must remain `unknown`. This is implemented as a one-keyword extension to the existing `SwitchVendorRule` identifier tier (`SWITCH_IDENTIFIER_KEYWORDS`), not a new rule — it is the same evidence shape (`procurve`, `edgeswitch`) that tier already exists to hold.
- **Candidate C (UniFi OS → possibly `ROUTER`): REJECTED for this sprint.** The single real UniFi OS device is a UniFi Cloud Key — a network **controller/management appliance**, not a routing device. Its strongest identifying evidence (`CloudKey`, `organizationName=Ubiquiti Networks`) names a controller product, not a router, firewall, or switch. No existing `DeviceType` value fits it without stretching `SERVER` (the `NetworkApplianceRule` precedent) onto a single, unconfirmed evidence pattern. Recommendation: leave `unknown`. Do not implement.

Net production impact of implementing A and B: **5 of 244 devices change**, all from `unknown` to a specific type, with zero unexpected movement elsewhere in the 244-device set (verified by full replay, both by device type and by winning-rule identity, for every device — not just the changed ones).

## 2. Current-State Findings

Investigation used the real 244-device production dataset (`output/Test Network.nmproj`) classified with the classifier as committed at `HEAD` (`a038289`, i.e. including RULE-006 and RULE-007). Current distribution:

| Type | Count |
|---|---:|
| unknown | 127 |
| workstation | 28 |
| access_point | 26 |
| printer | 23 |
| server | 12 |
| switch | 10 |
| phone | 10 |
| hypervisor | 3 |
| camera | 3 |
| firewall | 2 |

`DeviceType.ROUTER` exists in `networkmapper/core/models.py` but is produced by **zero** current rules (confirmed by direct grep across `networkmapper/classification/rules/*.py` for `DeviceType.ROUTER`: no matches). No device in the production dataset is currently `router`.

## 3. Candidate A — EdgeOS

**Exact matches found:** 3 devices, all vendor `"Ubiquiti"`, all currently `unknown` (no rule matched; `get_last_rule_results()` shows no rule claims them today).

| IP | Vendor | Hostname | Port 443 evidence |
|---|---|---|---|
| 172.16.100.4 | Ubiquiti | (none) | `http_title="EdgeOS"`, `tls_subject`/`tls_issuer` CN=`UbiquitiRouterUI`, org=`Ubiquiti Inc.` |
| 172.16.100.7 | Ubiquiti | (none) | identical evidence shape to above |
| 172.16.100.240 | Ubiquiti | (none) | identical evidence shape to above |

All three additionally expose SSH (OpenSSH, Debian-based) and a DNS resolver service (`dnsmasq`) on port 53 — evidence consistent with, though not independently used by, a router/gateway function (local DHCP/DNS resolution is a standard EdgeRouter feature, not something any other current rule reads).

Answers to the required investigation questions:

1. **What exact field contains "EdgeOS"?** `services[].http_title` on port 443, exact value `"EdgeOS"` (verbatim, no surrounding text).
2. **Is the evidence product-specific enough to mean router/gateway rather than generic Ubiquiti hardware?** Yes. EdgeOS is Ubiquiti's dedicated routing/gateway OS (the EdgeMAX line: EdgeRouter and USG). It is not the OS Ubiquiti ships on its access points (AirOS/UniFi AP firmware) or its EdgeSwitch line (which self-identifies as "EdgeSwitch," a distinct product name already handled by `SwitchVendorRule`'s `SWITCH_IDENTIFIER_KEYWORDS`). The TLS certificate common name goes further than the OS name alone: `UbiquitiRouterUI` explicitly contains the word "Router," which is Ubiquiti's own self-description of this exact management interface, not an inference this plan is making.
3. **Are all real EdgeOS devices currently UNKNOWN?** Yes, 3/3.
4. **Would any existing rule claim them if ordering changed?** No. `UbiquitiAccessPointRule` is the only rule that inspects vendor `"ubiquiti"` at all; it requires either a hostname matching AP-specific prefixes/keywords (all three EdgeOS devices have no hostname) or an HTTP title containing the UniFi guest-portal redirect path `"guest/s/default"` (these devices' title is `"EdgeOS"`, not a guest-portal redirect). Confirmed directly: `UbiquitiAccessPointRule().classify()` returns `matched=False` for all three regardless of position in the rule list.
5. **Would ROUTER be the correct DeviceType for every observed case?** Yes for all 3 observed cases — identical evidence shape, no variation.
6. **Is there any evidence that EdgeOS appears on non-router classes in this dataset?** No. All three occurrences carry the identical `http_title`/`tls_subject`/`tls_issuer` pattern; there is no case in this dataset where `"EdgeOS"` or `"UbiquitiRouterUI"` co-occurs with camera, printer, phone, switch, or AP-identifying evidence.

**Recommendation: high-confidence, narrowest identifier-tier rule** — see Section 7.

## 4. Candidate B — TP-Link Switch Evidence

**Exact matches found:** 4 devices carrying `"tp-link"` (case-insensitive) anywhere in their retained evidence, across both observed vendor-name variants:

| IP | Vendor | Product/title evidence | Switch-specific? |
|---|---|---|---|
| 172.16.102.12 | TP-Link Technologies | `product="TP-LINK switch http admin"` | **Yes** — explicit |
| 172.16.102.65 | TP-Link Technologies | `product="TP-LINK switch http admin"` | **Yes** — explicit |
| 172.16.102.95 | TP-Link Systems | none (no title, no product) | No — vendor only |
| 172.16.102.143 | TP-Link Systems | none (no title, no product) | No — vendor only |

Answers to the required investigation questions:

1. **Which devices have explicit switch-identifying product/title evidence?** Exactly 2: `.12` and `.65`, both `product="TP-LINK switch http admin"` verbatim.
2. **Which devices have only vendor/OUI evidence and nothing product-specific?** Exactly 2: `.95` and `.143` — vendor field only, no `services[]` product/title/TLS/auth-realm text of any kind.
3. **Should the rule match product/title text only, vendor+product corroboration, or both vendor variants?** Product text only, as an independent identifier-tier trigger — **not** gated on vendor. This is consistent with the existing `SwitchVendorRule.SWITCH_IDENTIFIER_KEYWORDS` tier's own established precedent (`"procurve"`, `"edgeswitch"`): the identifier string itself is the trusted signal, and vendor is never required as a co-condition for that tier today. Because the match is on product text alone, it is automatically indifferent to which of the two observed vendor-string variants (`"TP-Link Technologies"` vs. `"TP-Link Systems"`) is present — no vendor-variant-specific logic is needed or proposed.
4. **Must bare TP-Link vendor identity remain insufficient?** Yes — confirmed necessary by the data itself: `.95` and `.143` have no product evidence at all, and forcing a bare-vendor match would misclassify both with zero corroborating evidence. The proposed change does not add a vendor-based trigger of any kind for TP-Link.

**Recommendation: extend `SwitchVendorRule`'s existing identifier tier by one keyword** — see Section 7. This is not a new rule and requires no new ordering decision.

## 5. Candidate C — UniFi OS Decision

**Exact match found:** 1 device, `172.16.100.89`, vendor `"Ubiquiti"`, currently `unknown`.

Full retained evidence:

- Port 22: `ssh`, `product="OpenSSH"`, version `8.4p1 Debian 5+deb11u7`
- Port 80: `http`, `product="nginx"`, `http_title="Did not follow redirect to https://172.16.100.89/"`
- Port 443: `http`, `product="nginx"`, `http_title="UniFi OS"`, `tls_subject`/`tls_issuer` CN=`unifi.local`
- Port 8080: `http`, `product="Apache Tomcat"`, `http_title="HTTP Status 400 – Bad Request"`
- Port 8443: `http`, `product="Apache Tomcat"`, `http_title="Site doesn't have a title."`, `tls_subject`/`tls_issuer` CN=`CloudKey`, organizationName=`Ubiquiti Networks`

No hostname, no `operating_system`, no SNMP evidence of any kind.

Answers to the required investigation questions (verbatim from the sprint charter):

1. **Does the evidence support ROUTER?** No. Nothing in this evidence indicates a routing/NAT/WAN-uplink function. The device is reachable purely as a management/API surface (nginx front end on 443, Tomcat-based application server on 8080/8443) — a controller, not a gateway.
2. **Does it support FIREWALL?** No. No firewall-specific product, title, or certificate text of any kind (contrast with the `SonicWallFirewallRule` identifier tier, which has an explicit, self-branded match).
3. **Does it support NETWORK_APPLIANCE only?** `DeviceType` has no dedicated "network appliance" or "controller" value — the only existing precedent for appliance-shaped evidence is `NetworkApplianceRule`, which maps a NAS identifier (`"readynas"`) onto the closest existing type, `SERVER`. The `CloudKey` TLS common name is genuinely stronger, more specific evidence than the bare "UniFi OS" the sprint charter anticipated — a UniFi Cloud Key is a real, specific Ubiquiti controller appliance, not a generic label. However, mapping it to `SERVER` would extend `NetworkApplianceRule`'s "appliance evidence → SERVER" precedent to a second, unrelated product family, based on exactly one observed instance, inside a sprint explicitly chartered around routers and switches. That is a distinct decision this sprint was not chartered to make, and a single instance is a thin evidentiary base for a **new** identifier-tier keyword. This plan does not propose it.
4. **Does it support no existing DeviceType with sufficient confidence?** Yes — this is the correct conclusion.

**Recommendation: reject Candidate C for this sprint. Leave `172.16.100.89` `unknown`.** The evidence is real and specific (a genuine UniFi Cloud Key), but it identifies a controller/management appliance, not a router, firewall, or switch — the only device-function categories this sprint was chartered to address — and forcing it into `SERVER` would be a `NetworkApplianceRule`-precedent extension decision that deserves its own evidence base and its own review, not a rider on RULE-008. See Section 15 (Open Questions) for a note on deferring this as a possible future, narrowly-scoped candidate.

## 6. ROUTER Taxonomy Analysis

- `DeviceType.ROUTER` already exists in `networkmapper/core/models.py:10`. Confirmed directly by reading the file.
- No current rule produces `ROUTER`. Confirmed by grepping every file in `networkmapper/classification/rules/` for `DeviceType.ROUTER`: zero matches.
- Adding the first `ROUTER`-producing rule requires no new ADR. It is a direct application of an already-modeled `DeviceType` value through the established `ClassificationRule` contract (`classify(device) -> RuleResult`), the same mechanism every other type-producing rule already uses. No new architectural concept, data model field, or resolution mechanism is introduced.
- Existing Cisco/`SwitchVendorRule` ambiguity (the bare `"cisco"` vendor-match tier, and its interaction with `VoiceVendorRule`) is unaffected by this sprint's proposed changes and is out of scope, per the sprint's own hard non-goals.

## 7. Proposed Rule Changes

### 7.1 New rule: `EdgeRouterRule` (Candidate A)

New file `networkmapper/classification/rules/edge_router_rule.py`, modeled directly on the existing identifier-tier pattern used by `NetworkApplianceRule` and (for its identifier tier) `SonicWallFirewallRule`/`SwitchVendorRule`:

```python
EDGE_ROUTER_IDENTIFIER_KEYWORDS = {"edgeos", "ubiquitirouterui"}

class EdgeRouterRule(ClassificationRule):
    def classify(self, device: Device) -> RuleResult:
        matched_identifier = first_matching_identifier(
            device.services,
            EDGE_ROUTER_IDENTIFIER_KEYWORDS,
            snmp_sys_descr=device.snmp_sys_descr,
        )
        if matched_identifier is not None:
            label, value = matched_identifier
            return RuleResult(
                matched=True, confidence_contribution=0,
                reason=f"Detected {label} {value!r} matched known EdgeOS router identifier.",
                suggested_device_type=DeviceType.ROUTER,
            )
        return RuleResult(
            matched=False, confidence_contribution=0,
            reason="No known EdgeOS router identifier evidence was detected.",
            suggested_device_type=None,
        )
```

Deliberately **no vendor-bare-match tier** (unlike `SonicWallFirewallRule`'s `vendor == "sonicwall"` check) and **no hostname-based tier**: `"Ubiquiti"` vendor alone is explicitly excluded by this sprint's hard non-goals ("`vendor = Ubiquiti therefore router`"), and no EdgeOS device in the dataset carries a hostname to design a hostname signal from — adding one now would be exactly the kind of imagined-evidence heuristic this project's engineering discipline rejects.

This was simulated (not implemented) against the real dataset in an isolated copy of the package; see Section 10.

### 7.2 Extend `SwitchVendorRule` (Candidate B)

One-line change to the existing `SWITCH_IDENTIFIER_KEYWORDS` set in `networkmapper/classification/rules/switch_vendor_rule.py`:

```python
SWITCH_IDENTIFIER_KEYWORDS = {"procurve", "edgeswitch", "tp-link switch"}
```

No other code in `SwitchVendorRule` changes. `first_matching_identifier` already checks `product`, `http_title`, `tls_subject`, `tls_issuer`, `http_auth_realm`, and (via the optional parameter) `snmp_sys_descr` — the same mechanism that already serves `"procurve"` and `"edgeswitch"`. No new helper, no new match tier, no ordering change: this rule already runs at its current position (index 7 of the current 12; index 8 once `EdgeRouterRule` is inserted per Section 8).

### 7.3 Candidate C: no code change proposed.

## 8. Rule Ordering

Current `DeviceClassifier._rules` (12 entries, from `HEAD`):

```
1. ServerHostnameRule       7. SwitchVendorRule
2. NetworkApplianceRule     8. CameraVendorRule
3. HypervisorHostnameRule   9. WindowsServerRule
4. UbiquitiAccessPointRule 10. PrinterVendorRule
5. SonicWallFirewallRule   11. DellWorkstationRule
6. VoiceVendorRule         12. WindowsWorkstationRule
```

**Proposed:** insert `EdgeRouterRule` at position 5, immediately after `UbiquitiAccessPointRule` and immediately before `SonicWallFirewallRule`:

```
1. ServerHostnameRule       7. SwitchVendorRule (extended)
2. NetworkApplianceRule     8. CameraVendorRule
3. HypervisorHostnameRule   9. WindowsServerRule
4. UbiquitiAccessPointRule 10. PrinterVendorRule
5. EdgeRouterRule    <NEW> 11. DellWorkstationRule
6. SonicWallFirewallRule   12. WindowsWorkstationRule
7. VoiceVendorRule
```

(`SwitchVendorRule`'s own position is unchanged; only its keyword set grows.)

**Rationale, checked against every rule named in the sprint charter:**

- **`UbiquitiAccessPointRule` (must run before or after?):** Confirmed no overlap exists today (Section 3, answer 4) — all three EdgeOS devices fail every `UbiquitiAccessPointRule` check regardless of order. Placed immediately after it purely to keep the two vendor-scoped Ubiquiti rules adjacent (readability grouping, not a safety requirement) — consistent with the precedent `NetworkApplianceRule`/`CameraVendorRule` already established for "grouped, not order-critical" placement.
- **`SonicWallFirewallRule`:** No keyword overlap (`"edgeos"`/`"ubiquitirouterui"` vs. `"sonicwall"`); no shared vendor gate. Order relative to this rule is not safety-relevant; `EdgeRouterRule` is placed before it only to keep it beside `UbiquitiAccessPointRule` as noted above.
- **`SwitchVendorRule`:** No keyword overlap between `EDGE_ROUTER_IDENTIFIER_KEYWORDS` and `SWITCH_IDENTIFIER_KEYWORDS` (confirmed by direct grep: neither `"edgeos"` nor `"ubiquitirouterui"` appears in `switch_vendor_rule.py`, and neither `"procurve"`, `"edgeswitch"`, nor the new `"tp-link switch"` appears in `edge_router_rule.py`). `EdgeRouterRule` running before `SwitchVendorRule` therefore changes nothing about which devices `SwitchVendorRule` sees.
- **`NetworkApplianceRule`:** No keyword overlap (`"readynas"` vs. `"edgeos"`/`"ubiquitirouterui"`). Not adjacent in the proposed ordering; no interaction.

**For `SwitchVendorRule`'s TP-Link extension:** no ordering change at all — it is the same rule, same position, one more keyword in an already-existing set. The two matched TP-Link devices carry no evidence that any earlier rule (`ServerHostnameRule` through `UbiquitiAccessPointRule`/`EdgeRouterRule`) would claim first (confirmed: no hostname, vendor is not Ubiquiti/SonicWall/Netgear, no hypervisor-hostname pattern) — verified directly in the full-dataset replay (Section 10): the winning rule for both is `SwitchVendorRule`, exactly as expected, with no other device's winning rule changing as a side effect of the keyword addition.

## 9. False-Positive Analysis

- **`EDGE_ROUTER_IDENTIFIER_KEYWORDS`:** A full-text substring search across every retained evidence field (hostname, vendor, operating_system, computer_name, domain, snmp_sys_descr, snmp_sys_object_id, and every service's product/version/http_title/tls_subject/tls_issuer/http_auth_realm) for `"edgeos"` across all 244 real devices returns exactly the 3 devices in Section 3 — no other device in the dataset contains this text anywhere. Same result for a targeted check of `"ubiquitirouterui"`/`"routerui"`. Neither keyword appears in any of the three curated benchmark fixtures (`benchmarks/enterprise`, `benchmarks/homelab`, `benchmarks/small_office`) — confirmed by direct grep, zero matches — so the benchmark suite cannot regress from this change and provides no positive coverage of it either (a gap the Test Plan below closes with unit tests instead).
- **`"tp-link switch"` (added to `SWITCH_IDENTIFIER_KEYWORDS`):** The same full-dataset substring search for `"tp-link"`/`"tplink"` returns exactly the 4 devices in Section 4; only 2 of those 4 contain the word `"switch"` immediately following the vendor prefix in their product string. The keyword is anchored to the explicit product-class word `"switch"`, not the bare vendor prefix, which is exactly why the other 2 TP-Link devices (vendor-only, no product text at all) are correctly left unmatched — there is no text in their retained evidence for this keyword, or any keyword, to match. Not present in any benchmark fixture (confirmed by grep).
- **Cross-candidate check:** neither `EDGE_ROUTER_IDENTIFIER_KEYWORDS` nor the new `"tp-link switch"` keyword appears anywhere in any other rule file's own keyword sets (confirmed by grep across `networkmapper/classification/rules/*.py`), so neither change can alter any other rule's behavior.
- **Rejected heuristics (explicitly not proposed, consistent with the sprint's non-goals):** bare `"ubiquiti"` vendor → `ROUTER`; bare `"tp-link"`/`"tplink"` vendor → `SWITCH`; any hostname-based EdgeOS signal (no hostname evidence exists to justify one); any SNMP `sysObjectID`-based signal (no SNMP evidence present on any of the 7 candidate devices in this dataset at all).

## 10. Expected Production Impact

Simulated in an isolated copy of the package (both proposed changes applied together, no other change), classified against all 244 real devices, diffed against the current `HEAD` classifier device-type-by-device-type **and** winning-rule-by-winning-rule for every device (not only the ones expected to change):

| Type | Before (HEAD) | After (simulated RULE-008) |
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

**Exact changed-device inventory (5 devices):**

| IP | Vendor | Before | After | Winning rule |
|---|---|---|---|---|
| 172.16.100.4 | Ubiquiti | unknown | router | EdgeRouterRule |
| 172.16.100.7 | Ubiquiti | unknown | router | EdgeRouterRule |
| 172.16.100.240 | Ubiquiti | unknown | router | EdgeRouterRule |
| 172.16.102.12 | TP-Link Technologies | unknown | switch | SwitchVendorRule |
| 172.16.102.65 | TP-Link Technologies | unknown | switch | SwitchVendorRule |

**Unchanged: 239/244.** Every one of those 239 devices was also confirmed to keep the *same winning rule* as before (not just the same final type) — i.e. inserting `EdgeRouterRule` at position 5 does not cause any device that previously reached `SonicWallFirewallRule` or any later rule to be intercepted earlier for an unrelated reason. No unplanned classification changes occurred; the delta is exactly the 5 devices predicted from the evidence in Sections 3 and 4, with no explanation required beyond what those sections already establish.

## 11. Files Likely Affected

- `networkmapper/classification/rules/edge_router_rule.py` (new)
- `networkmapper/classification/rules/switch_vendor_rule.py` (one-line keyword-set change)
- `networkmapper/classification/device_classifier.py` (import + insertion at position 5 + docstring ordering-rationale addition, following the existing per-rule docstring convention)
- `tests/test_edge_router_rule.py` (new)
- `tests/test_switch_vendor_rule.py` (extended: TP-Link identifier cases, both positive and the two bare-vendor negative cases)
- `tests/test_classifier.py` (extended: `EdgeRouterRuleIntegrationTest` using `get_last_rule_results()`, plus a `SwitchVendorRule` TP-Link integration case)
- `devtools/validate.py` (`STANDARD_REGRESSION_TESTS` gains `"tests.test_edge_router_rule"`)
- `tests/test_devtools_validate.py` (hardcoded `assertEqual(result.tests_run, N)` bump — routine, per VER-RULE-005/006/007 precedent)
- `docs/plans/PLAN-RULE-008-Infrastructure-Vendor-Classification.md` (this document; would gain an implementation-closeout note, not a rewrite, per this project's established amendment convention)

No change proposed to `evidence_helpers.py`, `classification_rule.py`, `rule_result.py`, `core/models.py`, or any other existing rule file.

## 12. Test Plan

`EdgeRouterRule` unit tests (new file), mirroring the existing per-rule test style:

- Exact `"EdgeOS"` HTTP title on port 443 → matches, `ROUTER`.
- Exact `"UbiquitiRouterUI"` TLS subject/issuer common name, no HTTP title match → matches, `ROUTER` (proves the identifier check reaches TLS fields independently of HTTP title).
- Case-insensitivity for both keywords.
- Vendor `"Ubiquiti"` alone, no identifier evidence → no match (proves no vendor-bare-match tier exists).
- Hostname-only Ubiquiti device (e.g. an AP-shaped hostname) with no EdgeOS/UbiquitiRouterUI evidence → no match.
- A non-Ubiquiti vendor device that happens to carry unrelated HTTP/TLS text → no match (baseline negative).
- SNMP `sysDescr` containing `"EdgeOS"`, no HTTP evidence → matches (proves the SNMP corroboration path).
- Both `"EdgeOS"` (HTTP title) and `"UbiquitiRouterUI"` (TLS subject/issuer) present simultaneously on the same device, reproducing the real production evidence shape exactly (all 3 real EdgeOS devices carry both) → matches, `ROUTER`, and the returned `(label, value)` pair is asserted to be deterministic: `first_matching_identifier` checks `product`, then `http_title`, then `tls_subject`, then `tls_issuer`, then `http_auth_realm`, then `snmp_sys_descr`, in that fixed order, so with both present the match must resolve to the HTTP title tier (`label="HTTP title"`, `value="EdgeOS"`), never the TLS tier — and the rule's `reason` string is asserted to name that same label and value. This test exists specifically to lock down which evidence field wins when more than one is present, rather than leaving it as an untested implementation detail of `first_matching_identifier`'s field ordering.

`SwitchVendorRule` extension tests (added to the existing file, current count 13):

- `product="TP-LINK switch http admin"` → matches, `SWITCH` (both real evidence forms: as the sole evidence, and case-insensitivity).
- Vendor `"TP-Link Technologies"` or `"TP-Link Systems"` alone, no product/title evidence → **no match**, remains reachable by no other rule (proves the two bare-vendor real devices are correctly left `unknown`).
- Confirm the new keyword does not collide with `"procurve"`/`"edgeswitch"` (existing tests already establish these; no change needed there).

`DeviceClassifier` integration tests (added to `tests/test_classifier.py`), using `get_last_rule_results()` to assert exact rule identity and stopping point, following the RULE-006/RULE-007 precedent:

- Real-shaped EdgeOS device → `ROUTER` via `EdgeRouterRule`, confirming it is not intercepted by `UbiquitiAccessPointRule` first.
- Real-shaped TP-Link switch-product device → `SWITCH` via `SwitchVendorRule`.
- Confirm no existing rule's test file changes: `git diff` across every pre-existing rule file other than `switch_vendor_rule.py` should be empty for the classification-logic portions (only the docstring in `device_classifier.py` gains ordering-rationale prose).

Full validation gate (per this project's standing convention): `python -m pytest tests/ -q`, `python -m devtools validate --all` (all three benchmarks must remain 100%), and a full 244-device production replay reproducing exactly the Section 10 delta before any commit.

## 13. Acceptance Criteria

1. `EdgeRouterRule` exists, matches only `EDGE_ROUTER_IDENTIFIER_KEYWORDS` (`"edgeos"`, `"ubiquitirouterui"`), case-insensitive, via `first_matching_identifier` (product/HTTP-title/TLS-subject/TLS-issuer/HTTP-auth-realm/SNMP-sysDescr), with no vendor-bare-match or hostname-based trigger.
2. `SwitchVendorRule.SWITCH_IDENTIFIER_KEYWORDS` gains exactly one new entry, `"tp-link switch"`; no other logic in the rule changes.
3. `DeviceClassifier` includes `EdgeRouterRule` at position 5 (immediately after `UbiquitiAccessPointRule`, immediately before `SonicWallFirewallRule`); `SwitchVendorRule`'s own position is unchanged.
4. No existing rule file's classification logic changes other than the one-line keyword addition to `switch_vendor_rule.py`.
5. Full test suite passes; `python -m devtools validate --all` reports 100% on all three benchmarks.
6. A full 244-device production replay against `HEAD` proves both of the following, for every one of the 244 devices, not just a spot check of the changed ones:
   - **Exactly the 5 intended devices change**, matching the Section 10 inventory precisely: 3 EdgeOS devices (172.16.100.4, 172.16.100.7, 172.16.100.240) → `router` via `EdgeRouterRule`; 2 TP-Link devices (172.16.102.12, 172.16.102.65) → `switch` via `SwitchVendorRule`.
   - **Every other device (239/244) retains both** its pre-existing final classification *and* its pre-existing winning rule identity — not merely an unchanged `device_type`. A device whose final type happens to stay the same but whose winning rule silently shifted (e.g. because `EdgeRouterRule`'s insertion at position 5 caused some other device to be intercepted earlier or later than before) is a failure of this criterion, even though Section 10's device-type distribution table would not show it.
7. `172.16.100.89` (the UniFi OS / CloudKey device) remains `unknown`; no code change targets it.

## 14. Explicit Non-Goals

Per the sprint charter, and reaffirmed here:

- Cisco corroboration/hardening.
- HP hardening.
- `ServerHostnameRule` cleanup.
- Windows classification changes.
- SNMP `sysObjectID` architecture work.
- New `DeviceType` values.
- Discovery or enrichment changes.
- A generic network-device fallback rule.
- `"vendor = Ubiquiti therefore router"`.
- `"vendor = TP-Link therefore switch"`.
- Implementing Candidate C (UniFi OS / CloudKey) in any form, including mapping it to `SERVER`.

## 15. Open Questions

1. **UniFi Cloud Key as a future `NetworkApplianceRule` extension.** The `CloudKey` TLS identifier is real, specific evidence — stronger than the sprint charter's "UniFi OS" hypothesis — but n=1 in this dataset, and mapping controller/management appliances onto `SERVER` is a `NetworkApplianceRule`-precedent decision that deserves its own evidence base (ideally more than one observed Cloud Key/controller device) and its own review, not a rider on an infrastructure-vendor sprint scoped around routers and switches. Flagged for a future, separately-chartered investigation — not part of this plan's proposed scope.
2. **EdgeOS on other Ubiquiti product lines.** This dataset shows a uniform evidence shape across all 3 EdgeOS occurrences (EdgeRouter/USG-class devices). Whether Ubiquiti ever ships the identical `"EdgeOS"`/`"UbiquitiRouterUI"` self-identification on a device that is not, functionally, a router cannot be ruled out from three same-shaped data points beyond what direct evidence shows — the plan does not claim certainty beyond this dataset, only that nothing in this dataset contradicts the router classification.
3. **TP-Link product-string stability across TP-Link's own product lines.** Only two exact product strings were observed (`"TP-LINK switch http admin"`), both switches. Whether TP-Link uses an analogous but differently-worded string for routers/APs (which would make the explicit `"switch"` word the safe discriminator, as this plan assumes) is inferred from the string's own content, not independently confirmed against a TP-Link router/AP sample — none exists in this dataset.

## 16. git status

```
 M review.diff
?? diff.md
```

No production code, test file, or classifier file has been modified by this sprint. `review.diff` and `diff.md` are pre-existing, unrelated artifacts from earlier sessions. This plan document is the only new file. Nothing has been staged, committed, or pushed.
