# PLAN-RULE-010: High-Confidence pfSense Classification

**Status:** Architect-approved (with two strengthening edits, applied) and implemented as `FEAT-RULE-010`. During final staged-implementation review, the architect issued a further correction narrowing the approved identifier scope — see **Section 16** for the correction record. Sections 1–15 below are preserved exactly as originally written and approved; they are the historical investigation and design record, not a live description of the shipped keyword set. The authoritative current scope is `PFSENSE_IDENTIFIER_KEYWORDS = {"pfsense"}`, per Section 16, not the two-keyword `{"pfsense", "netgate"}` set discussed throughout Sections 1–11 below.

## 1. Executive Summary

PLAN-RULE-009's audit flagged a single real production device (`172.16.100.8`) as a Netgate pfSense firewall/router, self-identifying via an HTTP title and a self-signed TLS certificate common name — evidence quality this plan finds to be directly comparable to the already-implemented `EdgeRouterRule` (RULE-008) and stronger than the SonicWall hostname-tier fallback.

**The evidence justifies a narrowly-scoped, identifier-tier rule.** Exactly one real device carries `"pfsense"`/`"netgate"` evidence anywhere in the 244-device dataset; neither keyword appears anywhere else, on any other device, in any field. This is the same "zero false-positive substring collisions across the whole dataset" bar `EdgeRouterRule`'s `"edgeos"`/`"ubiquitirouterui"` keywords cleared.

The one open judgment call — separate from the reliability question — is **yield**: this rule would resolve exactly one device, the lowest production yield of any RULE sprint to date (below `WindowsWorkstationRule`'s one real device and `SonicWallFirewallRule`'s two). Per the precedent this project already established in PLAN-RULE-007 ("the reliability question is answerable from evidence; the value question is a judgment call for the architect"), this plan presents the reliability findings and defers the yield judgment explicitly rather than deciding it.

**Recommended `DeviceType`: `FIREWALL`, not `ROUTER`.** pfSense's own product lineage (a stateful-packet-filter distribution — "pf" is FreeBSD's packet-filter firewall — historically marketed and self-described as firewall software first) and this device's own retained evidence contain no explicit self-declared "router" text comparable to `UbiquitiRouterUI`'s literal word "Router." This makes `FIREWALL` the better-supported choice, matching the `SonicWallFirewallRule` precedent rather than the `EdgeRouterRule` one. Full reasoning in Section 6.

## 2. Current-State Findings

Investigation used the real 244-device production dataset (`output/Test Network.nmproj`) classified with the classifier as committed at `HEAD` (`270827f`, i.e. through RULE-008/VER-RULE-008). Current distribution:

| Type | Count |
|---|---:|
| unknown | 122 |
| workstation | 28 |
| access_point | 26 |
| printer | 23 |
| switch | 12 |
| server | 12 |
| phone | 10 |
| router | 3 |
| hypervisor | 3 |
| camera | 3 |
| firewall | 2 |

A full-text, case-insensitive search for `"pfsense"` and `"netgate"` across every retained evidence field (hostname, vendor, operating_system, computer_name, domain, snmp_sys_descr, snmp_sys_object_id, and every service's service/product/version/http_title/tls_subject/tls_issuer/http_auth_realm) on all 244 devices returns **exactly one device, in both searches**: `172.16.100.8`.

## 3. Production Evidence

**Device `172.16.100.8`:**

| Field | Value |
|---|---|
| IP | 172.16.100.8 |
| Hostname | `None` |
| Vendor (MAC OUI) | `Silicom` — a well-known network-appliance NIC/hardware OEM; Netgate's own hardware appliances are commonly built on Silicom network interface cards, so this is consistent with, though not itself proof of, a Netgate appliance |
| Current classification | `unknown` |
| Current winning rule | none (falls through all 13 rules) |
| operating_system | `None` |
| computer_name / domain | `None` / `None` |
| snmp_sys_descr / snmp_sys_object_id | `None` / `None` |

Service inventory:

| Port/proto | service | product | http_title | tls_subject | tls_issuer |
|---|---|---|---|---|---|
| 53/tcp | domain | `Unbound` | — | — | — |
| 80/tcp | http | `nginx` | `"Did not follow redirect to https://172.16.100.8/"` | — | — |
| 443/tcp | http | `nginx` | `"Netgate pfSense Plus - Login"` | `commonName=pfSense-697b4472a5cba/organizationName=Netgate pfSense Plus GUI default Self-Signed Certificate` | *(identical to tls_subject — self-signed)* |

No HTTP authentication realm evidence is present on this device. No SNMP evidence of any kind is present (consistent with PLAN-RULE-009's dataset-wide finding that SNMP evidence is absent from all 244 devices).

The port-53 `Unbound` DNS resolver is supporting context (Unbound is pfSense's built-in DNS Resolver service, enabled by default) but is not itself pfSense-specific — `Unbound` is a general-purpose open-source resolver used by many platforms — and this plan does not propose using it as matching evidence for that reason.

## 4. Identifier Analysis

`"pfsense"` occurs in exactly two evidence fields on this one device:

| Occurrence | Exact text | Field |
|---|---|---|
| 1 | `"Netgate pfSense Plus - Login"` | `service[443].http_title` |
| 2 | `"pfSense-697b4472a5cba"` (within the full CN string) | `service[443].tls_subject` |
| 3 | *(identical string)* | `service[443].tls_issuer` |

`"netgate"` occurs in the same three locations, as part of the same three strings (`"Netgate pfSense Plus - Login"`; `organizationName=Netgate pfSense Plus GUI default Self-Signed Certificate`, present in both `tls_subject` and `tls_issuer`). **The two keywords never occur independently of each other anywhere in this dataset — every occurrence of one is on the same evidence entry as the other.**

**Uniqueness / ambiguity:** both keywords are unique to this single device across the entire 244-device dataset — zero collisions, zero co-occurrence with any other rule's keyword or evidence pattern (confirmed by direct grep: neither string appears in any existing rule file's own keyword sets).

**Historical ambiguity:** none identified. Unlike `"hp"` (RULE-005) or `"dell"`/`"cisco"` (PLAN-RULE-009's Section 3.4 findings), neither `"pfsense"` nor `"netgate"` is a generic word, a short substring, or a term shared with an unrelated product line. Both are single-vendor, single-product brand terms.

**Comparison to existing identifier-tier precedents:**

| Precedent | Evidence shape | This device |
|---|---|---|
| `EdgeOS`/`UbiquitiRouterUI` (RULE-008) | HTTP title + self-signed TLS CN, both product-specific, co-occurring on the same real devices | **Same shape** — HTTP title + self-signed TLS CN, co-occurring |
| `SonicWall` (RULE-004/original) | Vendor field OR identifier OR hostname+port fallback | This device's vendor field (`Silicom`) does **not** say pfSense/Netgate — unlike SonicWall's bare-vendor tier, a vendor-based trigger is not available here at all, so the identifier tier is the *only* viable path, not merely the strongest one |
| `ReadyNAS` (RULE-003) | Single identifier keyword, corroborated by vendor/hostname when present | This device has no vendor/hostname corroboration available (vendor is the NIC OEM, not "Netgate"; no hostname at all) — weaker corroboration profile than ReadyNAS's original BENCH-002 case, but the identifier text itself is at least as specific |

**Conclusion: the evidence is comparable in strength to `EdgeOS`/`UbiquitiRouterUI`, not weaker.** Both are self-branded, product-specific text appearing redundantly across an HTTP title and a self-signed certificate, with zero corroboration needed because the identifier text itself is that specific.

## 5. False-Positive Analysis

- **Does `"pfSense"` ever appear on anything that is not a pfSense firewall/router?** No. Confirmed by a full-dataset, case-insensitive substring search across every retained field on all 244 devices: exactly one match, on the one confirmed pfSense device.
- **Does `"Netgate"` appear independently of `"pfSense"`?** No. Every occurrence of `"netgate"` in this dataset is on the same three evidence entries that also contain `"pfsense"`.
- **Would matching `"pfSense"` alone create any observed false positive?** No — zero collisions found.
- **Would matching `"Netgate"` alone create any observed false positive?** No — zero collisions found (same single device, same evidence entries).
- **Would both together improve confidence?** Not within this dataset specifically (both keywords are 100% co-occurrent here, so either alone already achieves the same result on this data). However, matching both is still the recommended design, for the same reason `EdgeRouterRule` matches both `"edgeos"` and `"ubiquitirouterui"` rather than just one: redundancy against a *future* device that might show only one of the two strings — e.g., a pfSense Community Edition install with a hostname-customized or CA-signed certificate that no longer says `"Netgate pfSense Plus GUI default Self-Signed Certificate"` but whose HTTP title still says `"pfSense - Login"`, or conversely a white-labeled Netgate appliance whose HTTP title has been customized but whose default self-signed certificate CN still starts with `"pfSense-"`. Neither scenario is observed in this dataset, but the two-keyword design costs nothing and directly mirrors the precedent already accepted for `EdgeRouterRule`.

Neither keyword was checked against `snmp_sys_descr` productively (no device in this dataset populates that field at all, per PLAN-RULE-009), but the proposed rule would still pass `snmp_sys_descr` into `first_matching_identifier()` for the same corroboration-only reason every other identifier-tier rule in this codebase does.

## 6. DeviceType Analysis

`DeviceType.ROUTER` and `DeviceType.FIREWALL` both already exist and are both plausible candidates; this plan does not propose a new value (per the sprint's explicit non-goal).

**Considered and rejected: `ROUTER`.** The `EdgeRouterRule` precedent for `ROUTER` rests specifically on the TLS CN containing the literal word `"Router"` (`UbiquitiRouterUI`) — an explicit, vendor-authored self-declaration of function, not an inference this project made. This device's evidence contains no comparable self-declaration of "router" function anywhere in its HTTP title or certificate text.

**Recommended: `FIREWALL`, matching the `SonicWallFirewallRule` precedent.** Reasoning:

1. **Product lineage.** pfSense is a fork of m0n0wall, itself built around FreeBSD's `pf` packet-filter firewall — the software's name is literally "packet-filter Sense." Its own project history and marketing position it as firewall software first, with routing as a supporting capability (the same relationship `SonicWallFirewallRule`'s target hardware has: a UTM/firewall appliance that also routes). This contrasts with EdgeOS/EdgeRouter's lineage (Vyatta-derived router software, USG variants adding firewall as a secondary capability).
2. **Existing firewall handling precedent.** `SonicWallFirewallRule` already establishes that this codebase classifies a firewall-appliance vendor's identifier evidence as `FIREWALL` even though the same physical appliance class also performs routing/NAT — this device fits that exact precedent more closely than the EdgeRouter one.
3. **The retained evidence itself does not discriminate.** The port-53 DNS resolver (`Unbound`) is present on both this device and the EdgeOS devices (which ran `dnsmasq`) — a LAN-facing DNS/DHCP resolver is common to both router-class and firewall-class network-edge appliances and was correctly not used as classification evidence in either case. With that evidence excluded, nothing in this device's retained evidence positively indicates routing function over firewall function, so the decision rests on product identity and lineage, which favors `FIREWALL`.

## 7. Proposed Rule Design

A new identifier-tier rule, `PfSenseFirewallRule`, modeled directly on `EdgeRouterRule`'s exact shape (the closest existing precedent, per Section 4):

```python
PFSENSE_IDENTIFIER_KEYWORDS = {"pfsense", "netgate"}

class PfSenseFirewallRule(ClassificationRule):
    def classify(self, device: Device) -> RuleResult:
        matched_identifier = first_matching_identifier(
            device.services,
            PFSENSE_IDENTIFIER_KEYWORDS,
            snmp_sys_descr=device.snmp_sys_descr,
        )
        if matched_identifier is not None:
            label, value = matched_identifier
            return RuleResult(
                matched=True, confidence_contribution=0,
                reason=f"Detected {label} {value!r} matched known pfSense firewall identifier.",
                suggested_device_type=DeviceType.FIREWALL,
            )
        return RuleResult(
            matched=False, confidence_contribution=0,
            reason="No known pfSense firewall identifier evidence was detected.",
            suggested_device_type=None,
        )
```

Deliberately **no vendor-bare-match tier** (the device's own vendor field, `Silicom`, is a NIC OEM, not Netgate — a vendor-based trigger is not even available here, let alone warranted) and **no hostname-based tier** (this device carries no hostname, and none of PLAN-RULE-009's other UNKNOWN devices suggest a pfSense-specific hostname convention exists in this dataset).

This was simulated (not implemented) against the real dataset in an isolated copy of the package; see Section 9.

## 8. Rule Ordering

**Proposed position: immediately after `SonicWallFirewallRule`, immediately before `VoiceVendorRule`** — grouping the two identifier-tier `FIREWALL`-producing rules adjacently, the same "grouped, not order-critical" convention already established for `ServerHostnameRule`+`NetworkApplianceRule` (both `SERVER`) and, most recently, `UbiquitiAccessPointRule`+`EdgeRouterRule` (RULE-008).

Proposed full 14-rule order:

```
1.  ServerHostnameRule        8.  SwitchVendorRule
2.  NetworkApplianceRule      9.  CameraVendorRule
3.  HypervisorHostnameRule    10. WindowsServerRule
4.  UbiquitiAccessPointRule   11. PrinterVendorRule
5.  EdgeRouterRule            12. DellWorkstationRule
6.  SonicWallFirewallRule     13. WindowsWorkstationRule
7.  PfSenseFirewallRule <NEW>
    VoiceVendorRule -> shifts to 8
```

**Interaction with `NetworkApplianceRule` (position 2):** no keyword overlap (`"readynas"` vs. `"pfsense"`/`"netgate"`); not adjacent in the proposed ordering; no interaction of any kind.

**Interaction with `EdgeRouterRule` (position 5):** no keyword overlap (`"edgeos"`/`"ubiquitirouterui"` vs. `"pfsense"`/`"netgate"`); the two target different `DeviceType` values (`ROUTER` vs. `FIREWALL`) for the same reason (Section 6), but neither rule's evidence could ever satisfy the other's keyword set — confirmed by grep, and by the fact that the one pfSense device fails `EdgeRouterRule`'s check entirely (no `"edgeos"`/`"ubiquitirouterui"` text anywhere in its evidence).

**Interaction with `SonicWallFirewallRule` (position 6, immediately preceding):** no keyword overlap (`"sonicwall"` vs. `"pfsense"`/`"netgate"`); both produce `FIREWALL`, so even in the hypothetical case of a future device carrying both vendors' evidence (not observed, and not architecturally plausible — a device cannot simultaneously be a SonicWall and a Netgate appliance), the outcome would be identical regardless of which of the two adjacent rules matched first. **Order between these two specific rules is not safety-relevant**, exactly as `ServerHostnameRule`/`NetworkApplianceRule`'s order is not safety-relevant for the same both-produce-the-same-type reason.

**Why this position and not earlier/later:** placing it any earlier (e.g. before `EdgeRouterRule`) would separate it from its natural `FIREWALL`-producing sibling for no benefit, since there is no overlap risk to resolve by reordering. Placing it later (e.g. after `SwitchVendorRule` or `CameraVendorRule`) would work identically for this device (no rule between the proposed and later positions can claim `172.16.100.8` first — confirmed in the replay, Section 9) but would break the "identifier-tier FIREWALL rules stay adjacent" grouping convention for no reason.

## 9. Expected Production Impact

Simulated in an isolated copy of the package (proposed rule inserted at position 7, no other change), classified against all 244 real devices, diffed against the current `HEAD` classifier device-type-by-device-type **and** winning-rule-by-winning-rule for every device:

| Type | Before (HEAD) | After (simulated RULE-010) |
|---|---:|---:|
| unknown | 122 | **121** |
| workstation | 28 | 28 |
| access_point | 26 | 26 |
| printer | 23 | 23 |
| switch | 12 | 12 |
| server | 12 | 12 |
| phone | 10 | 10 |
| firewall | 2 | **3** |
| router | 3 | 3 |
| hypervisor | 3 | 3 |
| camera | 3 | 3 |

**Exact changed-device inventory (1 device):**

| IP | Vendor | Before | After | Winning rule |
|---|---|---|---|---|
| 172.16.100.8 | Silicom | unknown | firewall | PfSenseFirewallRule |

**Unchanged: 243/244.** Every one of those 243 devices was also confirmed to keep the *same winning rule* as before (not just the same final type) — inserting `PfSenseFirewallRule` at position 7 causes zero devices to be intercepted earlier or later for an unrelated reason. No unplanned classification changes occurred. No benchmark fixture (`benchmarks/{enterprise,homelab,small_office}`) contains `"pfsense"` or `"netgate"` in any field (confirmed by grep), so the curated benchmark suite is unaffected and provides no positive coverage of this rule — unit tests are the only coverage available, per the same pattern already noted for `EdgeRouterRule`/`NetworkApplianceRule` in PLAN-RULE-009.

## 10. Files Likely Affected

- `networkmapper/classification/rules/pfsense_firewall_rule.py` (new)
- `networkmapper/classification/device_classifier.py` (import + insertion at position 7 + docstring ordering-rationale addition, following the existing per-rule docstring convention)
- `tests/test_pfsense_firewall_rule.py` (new)
- `tests/test_classifier.py` (extended: `PfSenseFirewallRuleIntegrationTest` using `get_last_rule_results()`; existing hardcoded `len(rule_results)`/"position N" assertions for every rule at or after position 7 will shift by one, the same mechanical consequence RULE-008 already required and documented)
- `devtools/validate.py` (`STANDARD_REGRESSION_TESTS` gains `"tests.test_pfsense_firewall_rule"`)
- `tests/test_devtools_validate.py` (hardcoded `assertEqual(result.tests_run, N)` bump — routine, per VER-RULE-005/006/007/008 precedent)
- `docs/plans/PLAN-RULE-010-High-Confidence-pfSense-Classification.md` (this document; would gain an implementation-closeout note, not a rewrite, per this project's established amendment convention)

No change proposed to `evidence_helpers.py`, `classification_rule.py`, `rule_result.py`, `core/models.py`, or any other existing rule file.

## 11. Test Plan

`PfSenseFirewallRule` unit tests (new file), mirroring `EdgeRouterRule`'s test structure:

- Exact `"Netgate pfSense Plus - Login"` HTTP title on port 443 → matches, `FIREWALL`.
- Exact `"pfSense-<hex>"` TLS subject common name, no HTTP title match → matches, `FIREWALL` (proves the identifier check reaches TLS fields independently of HTTP title).
- TLS issuer variant of the same → matches (self-signed certificates duplicate subject/issuer; confirm both fields are independently reachable).
- Case-insensitivity for both `"pfsense"` and `"netgate"`.
- Vendor `"Silicom"` alone (the device's real vendor field), no identifier evidence → no match (proves no vendor-bare-match tier exists).
- No hostname, no identifier evidence → no match (proves no hostname-based tier exists).
- A non-pfSense device with unrelated HTTP/TLS text → no match (baseline negative).
- SNMP `sysDescr` containing `"pfSense"`, no HTTP evidence → matches (proves the SNMP corroboration path, mirroring `EdgeRouterRule`'s equivalent test).
- **Deterministic multi-evidence case, reproducing the real production evidence shape exactly:** both the HTTP title `"Netgate pfSense Plus - Login"` **and** the TLS subject/issuer `"pfSense-..."` present simultaneously on the same device (172.16.100.8's actual shape — it carries both, not just one). The test must assert:
  - the rule matches, `suggested_device_type=FIREWALL`;
  - `first_matching_identifier()`'s returned `(label, value)` pair is deterministic, not incidental: since it checks `product` → `http_title` → `tls_subject` → `tls_issuer` → `http_auth_realm` → `snmp_sys_descr` in that fixed order, with both present the match must resolve to `label="HTTP title"`, `value="Netgate pfSense Plus - Login"` — never the TLS tier;
  - the rule's `reason` string names that same evidence (`"HTTP title"` and `"Netgate pfSense Plus - Login"`), not the TLS text.

  This locks down deterministic evidence precedence exactly as the equivalent test does for `EdgeRouterRule` (RULE-008).

`DeviceClassifier` integration tests (added to `tests/test_classifier.py`), using `get_last_rule_results()`:

- Real-shaped pfSense device (172.16.100.8's exact evidence) → `FIREWALL` via `PfSenseFirewallRule`, confirming it is not intercepted by `EdgeRouterRule` or `SonicWallFirewallRule` first, and reaches position 7 exactly.
- Confirm every pre-existing rule's own test file is unaffected: `git diff` across every rule file other than the new one and `device_classifier.py` should be empty.
- Mechanical position-shift updates to the existing hardcoded `len(rule_results)` assertions for `WindowsServerRule` (10→11), `DellWorkstationRule` (12→13), `WindowsWorkstationRule` (13→14) integration tests, the same kind of update RULE-008 already required and documented.

Full validation gate (per this project's standing convention): `python -m pytest tests/ -q`, `python -m devtools validate --all` (all three benchmarks must remain 100%), and a full 244-device production replay proving both halves of the Section 12 Acceptance Criterion 5 replay contract — **exactly 1 device changes (172.16.100.8, UNKNOWN → FIREWALL via PfSenseFirewallRule), and all other 243 devices retain both identical final DeviceType and identical winning-rule identity** — before any commit.

## 12. Acceptance Criteria

1. `PfSenseFirewallRule` exists, matches only `{"pfsense", "netgate"}`, case-insensitive, via `first_matching_identifier` (product/HTTP-title/TLS-subject/TLS-issuer/HTTP-auth-realm/SNMP-sysDescr), with no vendor-bare-match or hostname-based trigger.
2. `DeviceClassifier` includes `PfSenseFirewallRule` at position 7 (immediately after `SonicWallFirewallRule`, immediately before `VoiceVendorRule`); no pre-existing rule is reordered relative to any other pre-existing rule.
3. No existing rule file's classification logic changes.
4. Full test suite passes; `python -m devtools validate --all` reports 100% on all three benchmarks.
5. A full 244-device production replay against `HEAD` proves both of the following, for every one of the 244 devices, not just a spot check of the changed one — mirroring the replay contract adopted in RULE-008:
   - **Exactly one device changes**: `172.16.100.8`, `UNKNOWN` → `FIREWALL`, via `PfSenseFirewallRule`.
   - **Every other device (243/244) retains both** its pre-existing final `DeviceType` *and* its pre-existing winning-rule identity — not merely an unchanged `DeviceType`. A device whose final classification remains the same but whose winning rule changes is a failure of this criterion, even though a device-type distribution table alone would not show it.

## 13. Non-Goals

Per the sprint charter, and reaffirmed here: Cisco, Meraki, Dell, HP, Windows classification, camera rules, Mercury Security, any `DeviceType` taxonomy change, discovery changes, enrichment changes. This plan also does not decide the yield/value judgment call named in Section 1 — that is explicitly deferred to the architect, consistent with the PLAN-RULE-007 precedent for separating reliability from value.

## 14. Open Questions

1. **Is a single production instance sufficient yield to justify this sprint?** This is the lowest production yield of any RULE sprint's identifier-tier addition to date (below `SonicWallFirewallRule`'s 2 and `EdgeRouterRule`'s 3). The reliability evidence is not in question (Section 5); whether it is *worth* a dedicated sprint for one device is a judgment call this plan does not make.
2. **Would a future pfSense Community Edition (non-Netgate-branded) deployment still match?** This dataset only contains one Netgate-branded instance; a self-compiled or third-party-hardware pfSense CE install might present only `"pfSense"` text without `"Netgate"` anywhere (no `Netgate pfSense Plus` GUI branding). The proposed two-keyword design (Section 7) is intended to remain robust to that, but this dataset cannot confirm it — no such device exists in it.
3. **Should the `Unbound` DNS-resolver service be considered as future corroborating (never independent) evidence**, the way `dnsmasq` is documented as consistent-but-unused evidence for `EdgeRouterRule`? Not proposed here, since `Unbound` is not pfSense-specific (used by many non-pfSense platforms), but flagged for completeness.

## 15. git status

```
 M review.diff
?? diff.md
```

No production code, test file, or classifier file has been modified by this sprint. `review.diff` and `diff.md` are pre-existing, unrelated artifacts from earlier sessions. This plan document is the only new file. Nothing has been staged, committed, or pushed.

## 16. Post-Implementation-Review Correction (bare "netgate" rejected)

**This section is an append-only correction record, added after `FEAT-RULE-010` was implemented and staged for review. Sections 1–15 above are preserved exactly as originally written and approved — they are not rewritten to pretend this was the original design.** This project's established convention (see PLAN-RULE-007 Section 21, PLAN-RULE-006's Acceptance Criterion correction) is to append corrections rather than erase the historical investigation record, and that convention is followed here.

**What happened:** PLAN-RULE-010 was investigated, drafted, and architect-approved (with two strengthening edits to the replay contract and test plan, both applied) with a two-keyword identifier set, `PFSENSE_IDENTIFIER_KEYWORDS = {"pfsense", "netgate"}`, as documented throughout Sections 4, 5, 7, 8, and 11 above. `FEAT-RULE-010` implemented exactly that approved scope and passed an initial implementation review. During **final staged-review**, before commit, the architect identified a classification-safety issue in the approved design itself, not in the implementation of it.

**The correction:** `"netgate"` is rejected as an independent identifier keyword. `PFSENSE_IDENTIFIER_KEYWORDS` is narrowed to `{"pfsense"}` alone.

**Rationale:** "Netgate" is manufacturer/product-family identity, not pfSense-specific identity. Netgate manufactures more than one product line — notably **TNSR**, a separate, distinct router product, alongside pfSense. A bare `"netgate"` match (e.g. an HTTP authentication realm, a TLS field, or an SNMP `sysDescr` that says only `"Netgate"` with no `"pfsense"` text anywhere) cannot reliably distinguish a pfSense appliance from a TNSR one or from any other current or future Netgate product. This is the same class of risk this project has already named and corrected elsewhere — a vendor/manufacturer-level identifier being trusted as if it were product-level identity (compare PLAN-RULE-009 Section 3.4's `"dell"` and `"cisco"`/Meraki findings) — caught here before implementation shipped rather than after, because the specific product-line ambiguity (TNSR) was surfaced only at this later review stage, not during the original investigation.

**What does not change:** `"pfsense"` alone was, and remains, sufficient to cover the one real production device this sprint targets — the device's HTTP title (`"Netgate pfSense Plus - Login"`) and TLS subject/issuer (`"pfSense-697b4472a5cba/..."`, per Section 3) both independently contain the substring `"pfsense"`, entirely independent of whether `"netgate"` is also a recognized keyword. The production replay delta (Section 9), the `DeviceType` recommendation (`FIREWALL`, Section 6), the rule's ordering (position 7, Section 8), and the acceptance criteria (Section 12) are all unaffected by this correction — only the keyword set itself narrows.

**Corrected keyword set (supersedes Section 7's code sample and Section 12's Acceptance Criterion 1):**

```python
PFSENSE_IDENTIFIER_KEYWORDS = {"pfsense"}
```

**Corrected false-positive framing (supersedes Section 5's "would both together improve confidence?" discussion):** matching `"netgate"` independently of `"pfsense"` is no longer proposed at all, so the question of whether it would create a false positive *in this dataset* (Section 5 found it would not) is no longer the operative question — the operative concern is whether it *could* create one against evidence this dataset does not contain (a TNSR device), which this dataset cannot rule out and which Section 5's original analysis did not consider because TNSR was not yet identified as a relevant product line at that stage of investigation.

**Test-plan correction (supersedes Section 11's "case-insensitivity for both `"pfsense"` and `"netgate"`" line and its `"netgate"`-alone assertions):** every positive test case must use `"pfsense"` text; no test may assert that bare `"netgate"` text alone produces a match. A new negative regression test is required: an HTTP authentication realm of exactly `"Netgate"`, with no `"pfsense"` text anywhere in the device's evidence, must **not** match. This test was added directly to `tests/test_pfsense_firewall_rule.py` (`test_bare_netgate_http_auth_realm_without_pfsense_does_not_match`).

**Ordering-rationale correction (supersedes Section 8's "order between these two specific rules is not safety-relevant" framing):** `DeviceClassifier`'s docstring previously stated that ordering between `PfSenseFirewallRule` and `SonicWallFirewallRule` was "not safety-relevant either way" merely because both produce `FIREWALL`. This framing has been corrected in the implementation: the grouping remains deliberate and is retained, but the docstring no longer claims order-irrelevance as a general property — `classify()` is a first-match pipeline, so which of two adjacent rules matches first remains observable behavior (via winning-rule identity and `reason` text, both exposed by `get_last_rule_results()`) even when their `suggested_device_type` values happen to coincide. The absence of overlap is stated as a fact about currently observed evidence, not a permanent guarantee.

**Disposition:** all corrections above were applied directly to the already-implemented `FEAT-RULE-010` code and tests (not merely queued as a future follow-up), re-validated (full test suite, `devtools validate --all`, and a full 244-device production replay against the pre-RULE-010 baseline), and re-staged for final review under this corrected scope.
