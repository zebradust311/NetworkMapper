# PLAN-RULE-009: Classification Hardening and Evidence Audit

**Status:** Investigation/architecture audit only. No production code, test, or classifier change has been made. Nothing has been staged, committed, or pushed.

**Source of truth:** the classifier as committed at `HEAD` (`270827f`, i.e. through RULE-008/VER-RULE-008), run against the real 244-device production dataset (`output/Test Network.nmproj`).

## 1. Executive Summary

This is not a rule-discovery sprint. It is a full audit of the 13-rule classification pipeline after eight RULE sprints, intended to produce a roadmap, not an implementation.

Headline findings:

- **Two rules lean on bare vendor identity with no independent exclusion of that vendor's other product lines**, and both are evidence-confirmed to carry real risk: `DellWorkstationRule`'s bare `"dell"` vendor branch accounts for **27 of its 28 production wins (96%)**, entirely dependent on upstream rules (`WindowsServerRule`, `ServerHostnameRule`, `HypervisorHostnameRule`) to intercept every Dell **server** first — several of the 27 confirmed-workstation Dell devices carry either no `operating_system` evidence at all or a build number shared with a server SKU, and are classified WORKSTATION on vendor alone. `SwitchVendorRule`'s bare `"cisco"` vendor branch matches **two real "Cisco Meraki" devices** with zero corroborating evidence — Meraki is a multi-product-line brand (switches, access points, and MX-series security appliances), so a bare substring match cannot actually tell these three product classes apart, and neither Meraki device in this dataset carries any evidence beyond the vendor string.
- **The single largest UNKNOWN cluster (35 of 122 devices, 29%) is Axis Communications-vendor network devices without the `"axis camera station"` product identifier.** This is `CameraVendorRule` working exactly as designed (RULE-005 deliberately requires vendor **and** camera-specific product evidence, since Axis also makes non-camera network gear) — not a defect, but the single highest-value evidence-gathering target for a future sprint if further product-line evidence can be found.
- **A 28-device cluster of Windows hosts is UNKNOWN purely because `operating_system` is a bare, ambiguous build number** (shared between a Windows client release and a Windows Server release) **with no edition caption** — this is `WindowsServerRule`/`WindowsWorkstationRule` correctly declining to guess, not a coverage gap that a keyword change could safely close.
- **One real device (172.16.100.8) is a Netgate pfSense firewall/router**, self-identifying via an explicit HTTP title (`"Netgate pfSense Plus - Login"`) and a product-specific TLS certificate CN (`"pfSense-<hex>"`) — directly analogous in evidence quality to the EdgeOS/SonicWall precedent already implemented, and currently uncovered by any rule.
- **`NetworkApplianceRule` has never fired once** against the 244-device production dataset or any of the three curated benchmarks — its only coverage is its own unit test file. This is not evidence it is wrong; it is evidence this specific customer's environment has no ReadyNAS device, which is the only identifier it recognizes.
- TLS certificate subject/issuer and vendor-specific product strings remain, empirically, the most reliable evidence types observed across all eight RULE sprints to date: zero confirmed false-positive collisions in either field across the entire audit, versus at least two confirmed historical false positives in HTTP title text (RULE-005's "hp" redirect-notice collision) and product text (RULE-006's "Microsoft lpd" collision).

No new rule is proposed by this document. Section 11 lays out a prioritized roadmap for future, separately-chartered sprints.

## 2. Current Architecture

`DeviceClassifier` holds an ordered list of 13 `ClassificationRule` instances; `classify()` iterates in order and returns on the first `matched=True` result. `get_last_rule_results()` exposes the full evaluation trace. Current order (confirmed by direct read of `HEAD`):

```
1.  ServerHostnameRule        8.  SwitchVendorRule
2.  NetworkApplianceRule      9.  CameraVendorRule
3.  HypervisorHostnameRule    10. WindowsServerRule
4.  UbiquitiAccessPointRule   11. PrinterVendorRule
5.  EdgeRouterRule            12. DellWorkstationRule
6.  SonicWallFirewallRule     13. WindowsWorkstationRule
7.  VoiceVendorRule
```

Current production distribution (244 real devices):

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

Evidence model: `Device` carries `hostname`, `vendor` (MAC-OUI-derived), `operating_system` (SMB/RDP-negotiation-only), `computer_name`, `domain`, `smb_signing`, five SNMP fields, and a list of per-port `ServiceEvidence` (service/product/version/http_title/tls_subject/tls_issuer/http_auth_realm). `first_matching_identifier()` is the shared helper nearly every rule's strongest tier uses; it checks, in fixed order: `product` → `http_title` → `tls_subject` → `tls_issuer` → `http_auth_realm` → `snmp_sys_descr` (optional, corroboration-only per RULE-004's own stated principle).

## 3. Keyword Collision Audit

Every keyword was searched, case-insensitively, against its actual matching field(s) across all 244 real devices (not merely against the devices that currently win via that rule — this measures raw substring presence, independent of ordering).

### 3.1 Vendor keywords

| Rule | Keyword | Field | Hits | Devices | Risk |
|---|---|---|---:|---|---|
| DellWorkstationRule | `dell` | vendor | 33 | 27→WORKSTATION, 4→SERVER (caught upstream), 2→HYPERVISOR (caught upstream) | **HIGH** — see 3.4 |
| SwitchVendorRule | `cisco` | vendor | 4 | 172.16.100.1, .40 (Cisco Systems); 172.16.100.70, 172.16.102.80 (**Cisco Meraki**) | **HIGH** — see 3.4 |
| SonicWallFirewallRule | `sonicwall` | vendor | 2 | 172.16.100.2, .6 | LOW — SonicWall is a single-product-line (security appliance) vendor; no known SonicWall consumer product this substring could misidentify |
| UbiquitiAccessPointRule | `ubiquiti` (gate, not sole trigger) | vendor | 36 | gates further hostname/title checks only — never an independent trigger | SAFE (gate only, not a match trigger by itself) |
| CameraVendorRule | `axis communications` | vendor (gate, not sole trigger) | 38 | gates the required `axis camera station` identifier check — never an independent trigger | SAFE (gate only; RULE-005 explicitly redesigned this away from a bare-vendor trigger) |
| VoiceVendorRule | `yealink` | vendor | 10 | all 10 → PHONE, no collision found | SAFE |
| VoiceVendorRule | `poly`, `polycom`, `grandstream`, `mitel`, `avaya`, `cisco ip phone` | vendor | 0 each | none observed | Untested in the wild (0 production hits); `poly` in particular is a 4-letter substring risk (`polycom` itself, and generically "poly-" prefixed company names) never yet exercised against real data — **MEDIUM** (unconfirmed, not LOW, precisely because it has never been tested against a live collision) |
| PrinterVendorRule | `hp` | vendor + identifier | 7 (vendor) + 17 (identifier) | historically collided with ProCurve switches (RULE-002) and a UniFi guest-portal redirect notice (RULE-005) — both fixed by ordering/filtering, not by removing the keyword | **MEDIUM** — two known historical collisions, both mitigated, but the keyword itself is still a bare two-letter substring |
| PrinterVendorRule | `brother`,`canon`,`ricoh`,`konica minolta`,`epson`,`xerox`,`lexmark`,`kyocera`,`sharp`,`toshiba`,`zebra`,`datamax`,`fujifilm business innovation`,`hewlett-packard`,`hewlett packard` | vendor + identifier | 1–5 each (0 for canon/xerox/lexmark/kyocera/sharp/toshiba/hewlett-packard in this dataset) | no collisions found | SAFE — each is a full brand name, long enough to avoid generic-word collision; `sharp` and `toshiba` are worth future watching (both companies make non-printer electronics) but zero hits means zero observed risk today |
| NetworkApplianceRule | `netgear` (corroboration only) | vendor | 1 | 172.16.100.170 (not currently NAS-identified; see 6) | SAFE (corroboration only, never an independent trigger) |

### 3.2 Hostname keywords

| Rule | Keyword | Hits | Risk |
|---|---|---:|---|
| ServerHostnameRule | `dc` | 2 | SAFE in this dataset (both genuine domain controllers), but `dc` is a two-letter substring with a known historical false-positive shape elsewhere in this codebase's own lessons (RULE-005's "hp" collision was exactly this class of risk) — **MEDIUM** on general principle, no observed collision |
| ServerHostnameRule | `cam` | 1 | **MEDIUM** — `cam` is a substring of "camera"; no camera-hostname collision observed in this dataset only because no camera in this dataset carries a hostname at all (see 6.1) |
| ServerHostnameRule | `srv` | 1 | LOW — short but not a common English/product substring |
| ServerHostnameRule | `server` | 0 (hostname) | SAFE — 0 hits, and `server` as a substring of a hostname is unambiguous when it does occur |
| HypervisorHostnameRule | `esx`,`esxi`,`hyperv`,`vcenter`,`vmhost` | 0 each | Untested in the wild — SAFE in principle (vendor-committed product names), unconfirmed by this dataset |
| HypervisorHostnameRule | `vsh` | 3 | Explicitly documented in-code as "a single customer-observed convention... not a vendor or product naming standard" — **LOW RISK but explicitly non-generalizable**, already flagged by its own docstring |
| UbiquitiAccessPointRule | `uap`/`u6`/`u7` (prefix only, not substring) | 0 in this exact dataset (26 AP wins all via the `guest/s/default` HTTP-title tier instead) | SAFE — prefix-anchored, and unused in this dataset's real evidence shape (worth noting: the hostname tier this rule was originally built around has zero production utilization here; the HTTP-title tier added later by RULE-005 is what actually carries all 26 AP wins) |
| SonicWallFirewallRule | `tz`,`nsa`,`soho` (hostname prefix) | 0 each | Untested in the wild |
| VoiceVendorRule | `phone`,`voip`,`handset` (hostname) | 0 each | Untested in the wild |
| SwitchVendorRule | `switch`,`sw-`,`core-sw`,`dist-sw`,`access-sw` (hostname) | 0 each | Untested in the wild — all 12 real switch wins in this dataset come from the identifier tier (`procurve`/`edgeswitch`/`tp-link switch`) or the bare `cisco` vendor tier, never the hostname tier |
| DellWorkstationRule | `optiplex`,`latitude`,`precision`,`xps`,`vostro`,`inspiron` | 0 each | Untested in the wild — every one of the 27 Dell workstation wins in this dataset comes from the bare vendor branch, never the hostname branch (see 3.4) |
| NetworkApplianceRule | `nas` (corroboration only) | 0 | SAFE (never an independent trigger) |

### 3.3 Identifier keywords (product/HTTP title/TLS subject/TLS issuer/HTTP auth realm/SNMP sysDescr)

| Rule | Keyword | Hits | Risk |
|---|---|---:|---|
| EdgeRouterRule | `edgeos`, `ubiquitirouterui` | 3 each (same 3 devices) | SAFE — verified in VER-RULE-008 to be unique to these 3 devices in the entire dataset |
| SwitchVendorRule | `procurve` | 2 | SAFE |
| SwitchVendorRule | `edgeswitch` | 4 | SAFE |
| SwitchVendorRule | `tp-link switch` | 2 | SAFE — verified in VER-RULE-008 |
| SwitchVendorRule | `cisco` (product, corroboration only) | 1 | SAFE (never an independent trigger) |
| CameraVendorRule | `axis camera station` | 3 | SAFE |
| NetworkApplianceRule | `readynas` | 0 | Untested in the wild in this dataset (see Part 5) |
| HypervisorHostnameRule | `vmware` (corroboration only) | 0 | Untested in the wild (corroboration only, never an independent trigger) |
| SonicWallFirewallRule | `sonicwall` (identifier) | 0 | Untested in the wild — both real SonicWall devices in this dataset matched via bare vendor instead |
| PrinterVendorRule | `hp` (identifier) | 17 | Same substring-length concern as the vendor-tier `hp` keyword above; no collision found in this dataset beyond the two already-fixed historical ones |
| PrinterVendorRule service-name keywords (`ipp`,`ipps`,`jetdirect`,`lpd`,`printer`,`raw`,`pdl-datastream`) | 0 (as an independent-service-name trigger; the "Microsoft lpd" collision this tier was hardened against in RULE-006 is filtered at the entry level, not counted here as a raw hit) | — | Already hardened (RULE-006); SAFE as currently implemented |

### 3.4 Headline collision findings (not merely keyword-level — cross-rule, vendor-primacy risk)

**`DellWorkstationRule`'s bare `"dell"` vendor branch (HIGH RISK).** Of 33 Dell-vendor devices in the dataset, 27 resolve to WORKSTATION via the bare-vendor branch with **zero** further corroboration — not hostname, not OS, not any identifier. Several of those 27 carry `operating_system=None` or a build number this codebase already treats as ambiguous/shared-with-server elsewhere (`10.0.19041`, `10.0.26100`) when reached from a non-Dell vendor. The only reason this has not produced a real misclassification in this dataset is that every genuine Dell **server** and Dell **hypervisor** host happens to also carry either a server-shaped hostname or an explicit/exact Windows Server OS signature, which is caught by an earlier rule (`ServerHostnameRule` position 1, `WindowsServerRule` position 10) before `DellWorkstationRule` (position 12) is ever reached. This is a correct outcome *today*, entirely dependent on that upstream coverage remaining complete — it is not a property `DellWorkstationRule` itself guarantees. A Dell PowerEdge server with an ambiguous/absent OS signature and no server-shaped hostname would be silently classified WORKSTATION.

**`SwitchVendorRule`'s bare `"cisco"` vendor branch also matches `"Cisco Meraki"` (HIGH RISK, directly observed).** Two real devices (172.16.100.70, 172.16.102.80) carry the vendor string `"Cisco Meraki"` and **no other evidence of any kind** (no hostname, no services, no product string). Meraki is Cisco's cloud-managed brand spanning switches (MS), access points (MR), and security appliances (MX) — three different `DeviceType` values this codebase already models separately (SWITCH, ACCESS_POINT, FIREWALL). The bare `"cisco"` substring cannot distinguish among them, and unlike the Dell case, there is no upstream rule in this pipeline that would ever intercept a Meraki AP or a Meraki MX before `SwitchVendorRule` claims it. This risk is pre-existing (documented in `switch_vendor_rule.py`'s own comment as "pre-existing, evidence-accepted behavior" from before RULE-002), but this audit is the first to confirm it is not hypothetical: it has two live, zero-corroboration production instances today.

## 4. Rule Ordering Audit

Walking every adjacent pair (plus the two non-adjacent pairs that are, in practice, the most safety-critical relationships in the whole pipeline):

| Pair | Could both match the same device? | Current ordering correct? | Documented? | Load-bearing? |
|---|---|---|---|---|
| ServerHostnameRule ↔ NetworkApplianceRule | Theoretically (a NAS with a `dc`/`srv`-shaped hostname) | Yes, but moot — both produce SERVER | Yes (device_classifier docstring) | No — harmless either order |
| NetworkApplianceRule ↔ HypervisorHostnameRule | Theoretically (a NAS with a `vsh`-shaped hostname) — never observed | Yes | Yes (docstring: "not safety-relevant") | No |
| HypervisorHostnameRule ↔ UbiquitiAccessPointRule | Theoretically (a Ubiquiti device with an `esx`/`vsh`-shaped hostname) — never observed, and architecturally implausible (different vendor ecosystems) | Yes | **No** — not called out anywhere | No, but undocumented; low-cost to add one sentence |
| UbiquitiAccessPointRule ↔ EdgeRouterRule | No — confirmed zero overlap in VER-RULE-008 | Yes | Yes, extensively (RULE-008) | No (by design) |
| EdgeRouterRule ↔ SonicWallFirewallRule | No — disjoint keyword sets, disjoint vendors | Yes | Yes (RULE-008 docstring) | No |
| SonicWallFirewallRule ↔ VoiceVendorRule | No — disjoint keyword sets | Yes | **No** — not called out anywhere | No, but undocumented |
| VoiceVendorRule ↔ SwitchVendorRule | **Yes, in principle** — `VoiceVendorRule`'s `"cisco ip phone"` vendor keyword vs. `SwitchVendorRule`'s bare `"cisco"` vendor keyword | Yes — Voice runs first specifically so a Cisco phone's more specific vendor text wins | **Yes** (device_classifier docstring, RULE-002 era) | **Yes** — the clearest example of a *documented and still theoretically live* ordering dependency, though it has zero production hits today (this dataset uses Yealink exclusively for phones) |
| SwitchVendorRule ↔ CameraVendorRule | No — disjoint vendors (`cisco` vs. `axis communications`) | Yes | Yes (docstring) | No |
| CameraVendorRule ↔ WindowsServerRule | No — architecturally impossible, not just unobserved: `operating_system` is populated exclusively by SMB/RDP negotiation (per `Device`'s own field documentation), and no Axis camera in this or any dataset would ever expose that protocol | Yes | **No** — the *reason* it's safe (a field-population invariant, not a keyword-overlap absence) is not spelled out anywhere in the ordering docstring | No, but worth documenting *why* it's safe, since it's a different kind of safety than every other pair in this table |
| WindowsServerRule ↔ PrinterVendorRule | **Yes, confirmed by real production data** — 4 real devices (RULE-006) | Yes | **Yes, extensively** (RULE-006 is entirely about this) | **Yes** — the single most production-confirmed ordering dependency in the codebase |
| PrinterVendorRule ↔ DellWorkstationRule | Theoretically (a Dell-branded printer) — never observed | Yes | No, but low-risk and unobserved | No |
| DellWorkstationRule ↔ WindowsWorkstationRule | **Yes, confirmed by real production data** — 1 real device (SCT2053, RULE-007) | Yes | **Yes** (RULE-007 docstring) | **Yes** |

**Called out separately — the most load-bearing *non-adjacent* pair in the entire pipeline:** `HypervisorHostnameRule` (position 3) and `WindowsServerRule` (position 10) are six positions apart, yet their interaction (a `vsh`-hostname host carrying the exact Server-2022 build `10.0.20348`) is the single most safety-critical ordering fact in this codebase — a real production device (`SCTVSH03`) would be misclassified SERVER instead of HYPERVISOR if `WindowsServerRule` ever moved ahead of `HypervisorHostnameRule`. It is already extensively documented (RULE-006). This audit calls it out specifically because a purely-adjacent-pairs review (as this section otherwise performs) would never surface it — **the most dangerous ordering dependencies in this pipeline are not necessarily between neighbors.**

**Accidental ordering dependencies identified:** none found that are both (a) undocumented and (b) currently load-bearing. The two undocumented pairs (`HypervisorHostnameRule`↔`UbiquitiAccessPointRule`, `SonicWallFirewallRule`↔`VoiceVendorRule`) are undocumented because they are genuinely inert today, not because a real dependency was missed.

## 5. Vendor vs Identifier Audit

| Rule | Evidence hierarchy (strongest → weakest tier actually implemented) | Confidence | Hardening opportunity |
|---|---|---|---|
| ServerHostnameRule | hostname (`dc`/`cam`, then `srv`/`server`) + OS corroboration only | Medium | Corroborate with product/service evidence the way most later rules do; currently pure hostname |
| NetworkApplianceRule | identifier (`readynas`) + vendor/hostname corroboration | High (when it fires) | None identified — never fires, so no evidence to harden against |
| HypervisorHostnameRule | hostname (6 keywords) + port/service + identifier + OS corroboration | High | Already the most heavily corroborated rule in the codebase |
| UbiquitiAccessPointRule | vendor gate + hostname OR HTTP-title identifier | High | None — RULE-005 already added the identifier tier this rule needed |
| EdgeRouterRule | identifier only (`first_matching_identifier`, 2 keywords) | High | None — narrowest, cleanest rule in the codebase (RULE-008) |
| SonicWallFirewallRule | vendor (bare, single-product-line vendor) OR identifier OR hostname+port | High | None — SonicWall's business model makes bare vendor safe here |
| VoiceVendorRule | vendor (7 keywords, mostly untested) OR hostname+port | Medium | 6 of 7 vendor keywords have zero production confirmation; `poly` in particular deserves scrutiny before being trusted elsewhere |
| SwitchVendorRule | **vendor (bare `"cisco"`)** OR identifier (3 keywords) OR hostname+port | **Vendor-primary for 4/16 real wins; identifier-primary for the rest** | **Harden the bare-vendor tier** — see 3.4; Meraki collision is real |
| CameraVendorRule | vendor gate AND identifier (both required) | High | None — RULE-005 explicitly redesigned this away from vendor-primacy |
| WindowsServerRule | operating_system only (2 forms) | High | None — single-field discipline is exactly right for its evidence source |
| PrinterVendorRule | vendor (16 keywords) OR identifier OR port/service | Medium-High | `hp` remains a 2-letter substring with 2 historical collisions, both mitigated by ordering rather than by narrowing the keyword itself |
| **DellWorkstationRule** | **vendor (bare `"dell"`) OR hostname (6 keywords, 0 production hits)** | **Vendor-primary for 27/28 real wins** | **Harden the bare-vendor tier** — see 3.4; this is the rule leaning most heavily on vendor identity in the entire codebase |
| WindowsWorkstationRule | operating_system only (4 forms) | High | None — mirrors WindowsServerRule's discipline |

**Rules still leaning primarily on vendor identity:** `DellWorkstationRule` (27/28 wins, 96%, from bare vendor) and, more narrowly, `SwitchVendorRule` (4/16 wins, 25%, from bare vendor with only 1 of those 4 corroborated by a second signal). Both are flagged in Section 9 as roadmap candidates, not implemented here.

## 6. Unknown Device Audit

122 of 244 devices (50%) are UNKNOWN. Every device was categorized by direct evidence inspection (not inferred) into the following buckets, which sum exactly to 122:

| Category | Count | Why |
|---|---:|---|
| Axis Communications vendor, no camera-station identifier | 35 | Insufficient evidence for `CameraVendorRule`'s intentionally-conservative design (RULE-005: vendor alone is not camera-specific) — **intentionally conservative**, not a gap |
| Non-Windows / IoT / unsupported vendor, distinct product evidence | 29 | Unsupported vendor/product family — real, product-identifying evidence exists (see 6.3) but no rule targets these vendors |
| Windows host, ambiguous shared client/server build only (no edition caption) | 28 | Ambiguous evidence — `10.0.19041`/`10.0.26100`/etc. are builds this codebase already knows are shared between a client release and a server release; **intentionally conservative** |
| Mercury Security / Honeywell access-control panel | 8 | Unsupported product family; also **requires new architecture** — no existing `DeviceType` value fits an access-control panel |
| Windows-shaped host (RDP/SMB), zero `operating_system` evidence | 5 | Insufficient evidence — SMB/RDP negotiation didn't resolve an OS caption at all |
| Private/randomized MAC vendor | 5 | Insufficient evidence — vendor field itself is `"Private"` (locally-administered/randomized MAC), the weakest possible starting point |
| Endress+Hauser process instrumentation | 4 | Unsupported product family (industrial process instrumentation, not a device class this project has ever targeted) |
| Ubiquiti vendor, no AP/EdgeOS/UniFiOS-specific identifier | 3 | Insufficient evidence — bare SSH-only Ubiquiti devices (Dropbear) with no further product signal |
| TP-Link vendor, no switch-specific identifier | 2 | **Intentionally conservative** — the exact RULE-008 Candidate B exclusion, confirmed correct |
| pfSense firewall/router (Netgate) | 1 | Unsupported product family — see Section 9, high-confidence future candidate |
| Datto backup appliance | 1 | Unsupported product family — commercial BDR/backup appliance (`dattolocal.net`, `"SCTBackup2 - Control Panel"`), single instance |
| Samba-spoofed Windows OS string (Linux host) | 1 | Conflicting evidence — `operating_system="Windows 6.1 (Samba 4.7.6-Ubuntu)"` is a real Linux host whose Samba daemon reports a Windows-shaped SMB dialect string; correctly not treated as a Windows caption |

### 6.1 Clusters

The three largest clusters (35 Axis, 29 misc-IoT, 28 ambiguous-Windows-build) together account for **92/122 (75%)** of all UNKNOWN devices. None of the three is a coverage gap in the sense of "a rule should have caught this" — each is either an intentionally conservative design decision already made in a prior sprint (Axis, ambiguous builds) or a genuinely heterogeneous long tail of single-vendor IoT/embedded devices with no shared product family large enough to justify a dedicated rule (the 29-device misc-IoT bucket spans 16 distinct vendors, no two of which share a product line).

The 8-device Mercury Security/Honeywell cluster is the one bucket that both has strong, uniform, self-branded evidence (`tls_subject`/`tls_issuer` naming `"Mercury Security EP-series"` or the product's own MAC-derived serial) **and** has no existing `DeviceType` to land in — flagged in Section 9 as a candidate requiring an architecture decision (a new `DeviceType`, or an explicit decision to map it onto `SERVER`/leave it `UNKNOWN` the way Candidate C was resolved in RULE-008), not a rule implementation.

### 6.2 Ambiguous-build cluster detail

The 28-device ambiguous-build cluster is entirely `operating_system` values drawn from `{10.0.19041, 10.0.22631, 10.0.26100}` (plus one `6.3.9600` elsewhere), all builds this codebase's own docstrings already document as shared between a Windows client release and a Windows Server release, combined with `vendor` values that are MAC-OUI/NIC-chipset identifiers (`Intel Corporate`, `Microsoft`, `ASUSTek Computer`, `Magic Control Technology`, `Cloud Network Technology Singapore PTE.`) rather than system-builder identities — none of which is `Dell`, so `DellWorkstationRule` never reaches them. This is real evidence of a customer environment with substantial non-Dell Windows fleet (laptops/desktops from various OEMs) that this codebase currently has **no vendor-independent path** to classify as WORKSTATION without either an edition-caption match (which none of these 28 carry) or a hostname-naming-convention rule (which would require establishing that convention from customer-side knowledge, not evidence this project has access to).

### 6.3 Non-Windows/IoT cluster detail

16 distinct vendors, no shared product family: `NetBurner`, `Weintek Labs.` (HMI, `"VNC desktop"` title), `TRENDnet`, `D-Link International` (×2, identical generic `"Login"` title), `Netgear` (bare, no ReadyNAS identifier), `AES` (`"IntelliNet2.0 Management"` — access-control/security brand), `Prosoft Technology` (`"PLX31-MBTCP-MBS4"` — industrial Modbus gateway), `Samsung Electronics` (×3, zero services), `GL Technologies (Hong Kong) Limited`, `Sonos`, `Cloud Network Technology Singapore PTE.`, `Nvidia`, plus several `Intel Corporate`/`Microsoft`-vendor devices exposing only bare `OpenSSH` (likely Linux servers/VMs whose MAC OUI resolves to a virtualization/cloud NIC vendor rather than a meaningful hardware vendor). No single vendor in this bucket has more than 3 instances; none is a repeatable pattern at this dataset's scale.

## 7. Rule Utilization

| Rule | Production wins | Notes |
|---|---:|---|
| DellWorkstationRule | 27 | Highest-firing rule; see Section 5 for the vendor-primacy concentration |
| UbiquitiAccessPointRule | 26 | All via the HTTP-title guest-portal tier (RULE-005), zero via the original hostname-prefix tier |
| PrinterVendorRule | 23 | Healthy mix of vendor and identifier tiers |
| SwitchVendorRule | 12 | Mixed vendor (4) and identifier (8) tiers |
| VoiceVendorRule | 10 | 100% from one vendor keyword (`yealink`); the other 6 vendor keywords and all 3 hostname-tier keywords are unused in this dataset |
| WindowsServerRule | 9 | Healthy — both the caption tier and the exact-build tier fire |
| WindowsWorkstationRule | 1 | Exactly as PLAN-RULE-007 predicted and accepted (a deliberately low-yield, evidence-honest rule) |
| ServerHostnameRule | 3 | |
| HypervisorHostnameRule | 3 | 100% from the single-customer `vsh` convention |
| EdgeRouterRule | 3 | Exactly as PLAN-RULE-008 predicted |
| CameraVendorRule | 3 | |
| SonicWallFirewallRule | 2 | |
| **NetworkApplianceRule** | **0** | **Never fires** — see below |

**Which rules never fire?** `NetworkApplianceRule` alone. Its only keyword, `"readynas"`, has zero hits anywhere in the 244-device production dataset.

**Which rules only fire in tests?** `NetworkApplianceRule` — confirmed by grepping all three curated benchmark fixtures (`benchmarks/{enterprise,homelab,small_office}`) for `"readynas"`/`"netgear"`: zero matches. Its only exercised code path in this entire repository is `tests/test_network_appliance_rule.py` (12 unit tests) and its `test_classifier.py` presence, if any.

**Which rules produce only one production hit?** None currently — the lowest nonzero producers are `WindowsWorkstationRule` (1) and the two `SonicWallFirewallRule` wins (2, tied lowest nonzero pair alongside camera/edge-router/server-hostname/hypervisor at 3).

**Which rules overlap another rule?** See Section 4 (`WindowsServerRule`/`HypervisorHostnameRule`, `WindowsServerRule`/`PrinterVendorRule`, `DellWorkstationRule`/`WindowsWorkstationRule`, `VoiceVendorRule`/`SwitchVendorRule` — all already load-bearing and documented) and Section 3.4 (the two undocumented vendor-primacy risks).

**Which rules appear obsolete?** None — `NetworkApplianceRule` firing zero times in this one customer's dataset is not evidence it is obsolete; it is evidence this customer has no ReadyNAS device. Per this project's own established production-driven-only investigation discipline, its removal would need to be justified the same way its addition was (RULE-003's own BENCH-002 evidence), not by absence in a single, later, unrelated customer capture. No removal is recommended.

## 8. Evidence Strength Analysis

Ranked strongest → weakest, using only what was actually observed across all eight RULE sprints and this audit's own keyword-collision findings (Section 3):

1. **TLS certificate subject/issuer common name.** Zero confirmed false-positive collisions across the entire audit. Every rule that uses it (`EdgeRouterRule`'s `UbiquitiRouterUI`/CloudKey, `SonicWallFirewallRule`'s certificate-based tier, the Mercury Security/pfSense/Axis identifiers surfaced in this audit) is self-signed by the device itself, naming its own product — this is the device manufacturer's own commitment, not a scanner inference.
2. **Vendor-specific product string** (Nmap service-probe `product` field, e.g. `"TP-LINK switch http admin"`, `"HP ProCurve Switch 2530-24G"`, `"VMware ESXi Server httpd"`). One confirmed historical false positive (RULE-006's `"Microsoft lpd"` inside a printer-protocol port), fixed by scoping the exclusion to the exact matching service-evidence entry rather than the whole device — a lesson about *scope*, not about the field's underlying reliability.
3. **Self-branded HTTP title, when product-specific** (e.g. `"EdgeOS"`, `"UniFi OS"`, `"Netgate pfSense Plus - Login"`, `"AXIS"`). One confirmed historical false positive (RULE-005's bare `"hp"` inside a UniFi guest-portal redirect notice's opaque query string) — this field is reliable *only* when the title text is itself product-specific; a large fraction of this dataset's HTTP titles are scanner boilerplate (`"Did not follow redirect..."`, `"Site doesn't have a title..."`, generic `"Login"`) that carry zero classification signal and, per the RULE-005 lesson, can actively mislead a naive substring match.
4. **HTTP authentication realm.** Used by exactly one rule (`NetworkApplianceRule`'s original BENCH-002 evidence); no collision ever observed, but sample size in this codebase's own history is a single digit of devices — reliable when present, rarely present.
5. **Exact/unambiguous OS build number** (e.g. `10.0.20348`). Perfectly reliable *by definition* when a build is confirmed unique to one Windows SKU family — but this reliability is binary and fragile: the same evidence *type* (a bare build number) is simultaneously the least reliable evidence in this dataset when the build is one of the many ambiguous ones (`6.3.9600`, `10.0.17763`, `10.0.19041`, `10.0.22631`, `10.0.26100`), which this audit's Section 6.2 shows account for 28+ UNKNOWN devices. Build number reliability is not a property of the evidence type in general — it is a property of each specific numeric value.
6. **Hostname naming convention.** Powerful and precise when a convention is confirmed (RULE-006/007's `SCT00DC*`/domain-controller pattern, the `vsh` convention), but entirely customer-specific and non-generalizable (explicitly documented for `vsh`), and — this audit's most important structural finding about hostname evidence — **completely absent on every appliance-class device observed**: not one of the Axis cameras, EdgeOS routers, TP-Link switches, Mercury Security panels, Endress+Hauser instruments, or SonicWall/UniFi devices in this entire 244-device dataset carries a hostname at all. Hostname-based rules structurally can only ever reach Windows-domain-joined hosts and a handful of customer-named exceptions; they can never be extended to cover the appliance/IoT side of a network by design, regardless of how many more hostname keywords are added.
7. **SNMP `sysDescr`.** Architecturally trusted as corroboration-equal to product/title evidence (RULE-004), but **empirically absent from this entire dataset** — every keyword-hit search against `snmp_sys_descr` in Section 3 returned zero, for every rule, across all 244 devices. This is a real, dataset-specific finding: whatever discovery pass produced this capture either did not attempt SNMP queries broadly or this customer's devices largely don't expose it. High theoretical trust, zero practical coverage in this specific environment.
8. **Vendor identity (MAC OUI) alone.** The most consistently collision-prone evidence type in the entire system, empirically: HP (printer vs. switch), Ubiquiti (AP vs. router vs. switch vs. controller), TP-Link (switch vs. everything else), Axis (camera vs. other network gear), Netgear (NAS vs. router/switch/AP), Cisco (switch vs. router vs. firewall vs. phone vs. Meraki's own further split), and now confirmed in this audit — Dell (workstation vs. server vs. hypervisor) and Cisco Meraki specifically (switch vs. AP vs. security appliance) both currently rely on bare vendor with no exclusion. Every rule in this codebase that starts from vendor and is considered safe today either (a) requires a second corroborating signal (Axis, Ubiquiti, TP-Link, Netgear, HP-vs-switch) or (b) is a genuinely single-product-line vendor (SonicWall). The two exceptions that are neither — Dell, Cisco/Meraki — are exactly the two HIGH RISK findings in Section 3.4.
9. **`operating_system` free text, generically** (i.e., without a specific caption or exact build match). Never used as an independent trigger anywhere in this codebase, and this audit found no evidence that would justify changing that — every rule that reads it either matches an exact string, a specific unambiguous build, or an explicit edition caption, never a bare "looks Windows-ish" heuristic.

## 9. Future RULE Candidates

Ranked by production evidence quality. No implementation is proposed; this is the input to a future architect decision on what to charter next.

| Candidate | Affected devices | Confidence | Complexity | False-positive risk | Priority |
|---|---:|---|---|---|---|
| **pfSense firewall/router identifier** (`"pfsense"` in HTTP title/TLS CN, e.g. `"Netgate pfSense Plus - Login"`, CN=`"pfSense-<hex>"`) | 1 (172.16.100.8) | High — self-branded, product-specific, same evidence quality as the already-implemented EdgeOS/SonicWall identifier tiers | Low — identical shape to EdgeRouterRule | Low — `"pfsense"` is a distinctive, single-product term | **High** |
| **Harden `SwitchVendorRule`'s bare `"cisco"` vendor tier against `"Cisco Meraki"`** | 2 confirmed zero-corroboration devices today; unknown how many future devices | High confidence this is a real, live risk; unclear what the *correct* resolution is without more evidence (Meraki AP vs. switch vs. MX cannot be told apart from vendor alone) | Medium — likely requires either an identifier-tier extension or accepting these devices should fall to UNKNOWN pending better evidence | N/A (this is itself a false-positive-reduction candidate) | **High** |
| **Harden `DellWorkstationRule`'s bare `"dell"` vendor tier** | 0 confirmed misclassifications today (upstream rules currently catch every real case), but 27/28 wins currently rest entirely on that continuing to hold | High confidence the *risk* is real; the dataset itself offers no counter-example to design a fix from (no Dell server currently slips through) | Medium — a corroboration requirement here risks *reducing* coverage of genuine Dell workstations that lack any other signal | Low today, by luck of upstream coverage, not by design | **Medium** |
| **Mercury Security / Honeywell access-control panel** (8 devices, uniform `"Mercury Security EP-series"` TLS CN evidence) | 8 | High — uniform, self-branded, product-specific evidence across all 8 | High — no existing `DeviceType` fits; requires an architecture decision (new type vs. map to an existing one vs. leave UNKNOWN), not just a rule | Low (evidence itself is unambiguous) | **Medium** (architecture-gated, not rule-gated) |
| **Datto backup appliance** (`dattolocal.net` / `"SCTBackup2 - Control Panel"`) | 1 | Medium — single instance, but distinctive, product-specific evidence (a named commercial BDR product) | Low — same NAS-as-SERVER precedent `NetworkApplianceRule` already established | Low | **Low** (single-instance; same "worth a keyword, not worth a sprint" calculus PLAN-RULE-007 already applied to its own 1-device WindowsWorkstationRule addition) |
| **Endress+Hauser process instrumentation** (4 devices, uniform `"RSGx5"` TLS CN) | 4 | Medium — uniform evidence, but no existing `DeviceType` fits an industrial process instrument any better than it fits an access-control panel | High — same architecture gate as Mercury Security | Low | **Low/Reject** — narrower product category than Mercury Security with the same architectural blocker, and only 4 devices |
| **VoiceVendorRule vendor-keyword hardening** (`poly` in particular) | 0 (no live collision found — this dataset has no `poly`-prefixed non-Polycom device) | Low — nothing to hardened against yet; purely precautionary | Low | Unconfirmed | **Reject for now** — no production evidence to act on; revisit only if a future dataset surfaces a real `poly`-prefix collision |
| **Axis Communications: additional camera-specific identifier evidence** (35-device cluster) | 35 | **Unknown** — this is explicitly not enough evidence to propose a keyword from; the 35 devices' only common evidence (`"Boa httpd"`/`"Apache httpd"` + generic `"Index page"`/`"AXIS"` titles) is exactly the class of *not-camera-specific* text RULE-005 already rejected as insufficient | N/A — no implementation exists yet because no sufficiently specific identifier has been found | High if attempted with today's evidence (Axis makes non-camera network products) | **Reject as currently evidenced** — flagged as the single highest-value *investigation* target (not implementation target) for a future sprint chartered specifically to look for stronger Axis camera-specific evidence (e.g. firmware version strings, SNMP once/if ever populated, or a different NSE probe) |
| **Ambiguous-build Windows workstation cluster** (28 devices) | 28 | Low, by design — the evidence itself (a bare shared build number) is genuinely ambiguous; no keyword or hostname pattern in this dataset resolves it safely | N/A | High if attempted from OS evidence alone | **Reject** — this is the correct, intentionally conservative outcome, not a gap |

## 10. Architectural Debt

- **Duplicated logic:** none found at the implementation level — every rule reuses the shared `evidence_helpers.py` primitives (`first_matching_identifier`, `normalize_*`, `first_matching_port/service`, `format_hostname_evidence_reason`) rather than reimplementing matching logic. This is a genuine strength of the current architecture, not a debt item.
- **Inconsistent rule styles:** minor. Most rules follow a strict "vendor gate, then identifier tier, then hostname+signal tier" shape, but a few diverge for evidence-driven reasons already documented in their own files (`WindowsServerRule`/`WindowsWorkstationRule` are single-field by design; `CameraVendorRule` requires two conditions jointly rather than layering tiers). This divergence is justified case-by-case, not an inconsistency needing cleanup.
- **Documentation gaps:** two identified in Section 4 (`HypervisorHostnameRule`↔`UbiquitiAccessPointRule` and `SonicWallFirewallRule`↔`VoiceVendorRule` adjacency, and the field-population-invariant reason `CameraVendorRule`↔`WindowsServerRule` is safe) — low-cost, documentation-only fixes for a future small housekeeping pass, not urgent.
- **Testing gaps:** `NetworkApplianceRule` has zero production or benchmark exercise (Section 7) — its 12 unit tests are the only coverage that exists anywhere in the repository for this rule's behavior. Not a defect, but worth knowing before assuming benchmark accuracy is a complete regression signal for this rule.
- **Ordering rationale needing documentation:** the two gaps named above; everything else load-bearing is already thoroughly documented (this is a strong point of the existing codebase, built up incrementally across RULE-002 through RULE-008).
- **Opportunities for future ADRs:** whether/how to model physical-security and industrial-instrumentation device classes (Mercury Security, Endress+Hauser) is a `DeviceType`-taxonomy-level architecture question, not a rule question, and would benefit from its own ADR before any RULE sprint attempts to address either cluster — consistent with this project's existing practice of writing an ADR before extending shared data-model concepts (ADR-011/012/013 precedent).

## 11. Prioritized Roadmap

1. **High — RULE-010 candidate: pfSense identifier rule.** Single device, but evidence quality matches the EdgeOS/SonicWall precedent exactly; cheapest, safest next RULE sprint.
2. **High — investigation sprint: `SwitchVendorRule` bare-`"cisco"`/Meraki risk.** Needs its own evidence-gathering pass (are there other Meraki devices elsewhere, and does any distinguishing evidence exist for AP vs. switch vs. MX?) before a fix can be designed — this audit found the risk, not the fix.
3. **Medium — investigation sprint: `DellWorkstationRule` hardening feasibility.** No counter-example exists in this dataset to design against; would need either more evidence (a real ambiguous Dell server) or an architectural decision to accept the current ordering-dependent safety net as sufficient and merely document it as an explicit, monitored assumption.
4. **Medium — ADR: physical-security / industrial-device taxonomy.** Resolve whether Mercury Security (8 devices) and, separately, Endress+Hauser (4 devices) warrant a new `DeviceType`, a mapping onto an existing one, or a permanent UNKNOWN determination — an architecture decision, not a rule decision.
5. **Low — single-instance keyword additions:** Datto backup appliance (1 device), following the `NetworkApplianceRule`/ReadyNAS precedent, if and when a second instance is ever observed to justify the same "not a single unconfirmed case" bar RULE-003 originally set.
6. **Low/ongoing — documentation-only housekeeping:** the two ordering-rationale gaps and the `CameraVendorRule`/`WindowsServerRule` field-invariant note (Section 4/10) — no code change, purely explanatory, can be folded into any future sprint's docstring work.
7. **Reject / not ready:** Axis camera-specific evidence (needs an investigation sprint to find better evidence before any rule can be proposed — flagged as high-value but not yet actionable), the 28-device ambiguous-build cluster (correctly conservative, no safe path forward from OS evidence alone), and `VoiceVendorRule` keyword hardening (no live collision to fix).

## 12. Acceptance Criteria

1. Every `ClassificationRule` in `HEAD` has its keyword inventory extracted and each keyword's real production hit count reported (Section 3).
2. Every adjacent rule pair in `DeviceClassifier` is evaluated for potential collision, current-ordering correctness, and documentation status (Section 4), plus the single most safety-critical non-adjacent pair is explicitly called out.
3. Every rule is categorized by its evidence hierarchy and checked for vendor-primacy risk (Section 5).
4. All 122 real UNKNOWN devices are categorized into evidence-backed buckets summing exactly to 122, with clusters identified (Section 6).
5. Rule firing frequency is measured directly against the 244-device production dataset and the three curated benchmarks, not assumed (Section 7).
6. Evidence-type reliability is ranked using only findings already produced by this audit and prior RULE sprints, with each ranking justified by a specific observation, not opinion (Section 8).
7. Every future candidate is backed by an exact device count and confidence assessment drawn from real evidence; no speculative heuristic is proposed (Section 9).
8. No code, test, or classifier file is modified by this sprint (Section 15 confirms).

## 13. Non-Goals

Per the sprint charter, and reaffirmed here: no code implementation, no classifier redesign, no invented heuristics, no unsupported rule proposals, no ordering changes, no test changes, no production file changes. This document also does not decide the physical-security/industrial-device taxonomy question raised in Section 10 — that decision is explicitly deferred to a future ADR.

## 14. Open Questions

1. **Does a second Datto/backup-appliance instance exist in any other captured environment?** If so, it would cross this project's own "not a single unconfirmed case" bar for a `NetworkApplianceRule`-style keyword addition; this dataset alone cannot answer that.
2. **Is there any feasible additional Axis camera-specific identifier** beyond `"axis camera station"` — a firmware string, a different NSE probe output, or SNMP data if ever populated — that could resolve some fraction of the 35-device Axis cluster without reintroducing the bare-vendor risk RULE-005 already rejected? This audit could not find one in the currently retained evidence fields.
3. **Should Mercury Security/Honeywell access-control panels and Endress+Hauser instrumentation share a new `DeviceType`, map to an existing one, or remain permanently UNKNOWN as a matter of explicit policy** (the way UniFi OS/Cloud Key was resolved in RULE-008)? This is an architecture question this audit is not chartered to answer.
4. **Is the SNMP evidence gap** (zero `snmp_sys_descr` population across all 244 devices) **a property of this discovery run's configuration, or of this customer's environment?** If the former, a future discovery-side fix (out of this audit's scope) could unlock evidence this classification layer already knows how to use.

## 15. git status

```
 M review.diff
?? diff.md
```

No production code, test file, or classifier file has been modified by this sprint. `review.diff` and `diff.md` are pre-existing, unrelated artifacts from earlier sessions. This plan document is the only new file. Nothing has been staged, committed, or pushed.
