# Status

Plan Proposed — Pending Review

Approval: Not yet architect-reviewed. Do not implement against this plan until it is approved.

Authority: A production-driven classification investigation (real production project file `output/Test Network.nmproj`, 244 devices, captured 2026-09-04) re-ran the current `DeviceClassifier` against every device's actual retained evidence and found two confirmed active misclassifications plus five currently-`UNKNOWN` devices with high-confidence Windows Server evidence, all sharing one root evidence family. This plan re-investigates each affected device's exact retained evidence (not the investigation's earlier estimates) and designs the narrowest rule change the real evidence supports, per this sprint's explicit "do not guess" instruction.

Implements: RULE-006 — High-Confidence Windows Server Classification Corrections, continuing the classification-rule-content lineage (RULE-002 through RULE-005) `DeviceClassifier`'s rule files already cite.

Production Code Modified: No. This is a planning sprint only; no source or test files are changed by this plan.

New ADR Required: No (Section 9 below) — this is rule-content refinement within the existing `ClassificationRule`/`RuleResult` contract, the same class of change RULE-002 through RULE-005 already made.

---

## 1. Current-State Findings

### 1.1 Rule framework (confirmed unchanged by this plan)

`DeviceClassifier` (`networkmapper/classification/device_classifier.py`) holds an ordered `list[ClassificationRule]` and evaluates it first-match-wins (`classify()`, lines 67-87): the first rule whose `RuleResult.matched` is `True` decides `device.device_type`, and no later rule is ever consulted. Current order:

```
1. ServerHostnameRule        6. VoiceVendorRule
2. NetworkApplianceRule      7. SwitchVendorRule
3. HypervisorHostnameRule    8. CameraVendorRule
4. UbiquitiAccessPointRule   9. PrinterVendorRule
5. SonicWallFirewallRule    10. DellWorkstationRule
```

Each rule is independent (`classification_rule.py`); shared substring/lookup primitives live in `evidence_helpers.py` (`normalize_vendor`, `first_matching_identifier`, `first_matching_port`, `first_matching_service`, etc.) and already operate on raw field values (strings, lists), never on a whole `Device`. This plan adds one new rule and edits the internals of one existing rule (`PrinterVendorRule`); it does not touch `DeviceClassifier`'s orchestration model, `ClassificationRule`, or `RuleResult`'s contracts, and — per re-investigation below — does **not** require any code change inside `DellWorkstationRule` itself (Section 4.2 explains why).

### 1.2 Re-verified against the real dataset, not the prior investigation's estimates

The prior investigation (informal, not this plan) estimated the affected population from a sampled view. This plan re-ran the exact same re-classification against the full 244-device production file and re-extracted every affected device's complete evidence record directly. Two corrections to the prior estimate were found in the process (both material to the design, Section 3):

- **The confirmed print-server misclassification is not explained by "SMB+RDP evidence contradicts printer evidence" in general.** All four confirmed hosts specifically carry `product == "Microsoft lpd"` on the exact `ServiceEvidence` entry (port 515) that `PrinterVendorRule`'s networking tier matches on. One of the four (`172.16.101.6`, `VM-3030-WIN7`) has **no `operating_system` field at all** — an OS-caption-based exclusion would miss it entirely. The real, complete, narrowest fix is keyed on the matched service entry's own `product` field, not on a separate OS/port lookup elsewhere on the device (Section 3.1).
- **There are three `operating_system == "10.0.20348"` devices in the dataset, not two**, and the third (`172.16.100.28`, `SCTVSH03`) is *already* correctly classified `HYPERVISOR` via `HypervisorHostnameRule`'s existing `"vsh"` hostname keyword. This is not a device the new rule should touch — it is the concrete, real regression case proving why rule ordering matters (Section 4). Two sibling hosts, `SCTVSH01`/`SCTVSH02` (`operating_system == "6.3.9600"`, an explicitly-excluded ambiguous build), are also currently `HYPERVISOR` and must also remain unchanged.
- **Three additional currently-`UNKNOWN` devices (`SCT0020`, `PWD`, `SCT00CA`) share the exact same ambiguous `"6.3.9600"` build and an ambiguous, range-form product string (`"Microsoft Windows Server 2008 R2 - 2012 microsoft-ds"`)** as `SCTVSH01`/`SCTVSH02`. These three must explicitly **not** become `SERVER` under this plan — they are real, concrete proof that "product string mentions a Windows Server range" is not high-confidence evidence, distinct from an `operating_system` field that has fully resolved to an explicit, unambiguous caption.

### 1.3 What `operating_system` evidence looks like across the dataset (grounding Design Question 1)

Every Windows-flavored `operating_system` value observed among the 244 devices falls into exactly one of these shapes:

| Shape | Example | High-confidence Windows Server evidence? |
|---|---|---|
| Fully-resolved explicit Server caption | `"Windows Server 2019 Standard 17763 (Windows Server 2019 Standard 6.3)"`, `"Windows Server 2003 R2 3790 Service Pack 2 (Windows Server 2003 R2 5.2)"`, `"Windows Server 2012 R2 Datacenter 9600 (...)"`, `"Windows Server 2016 Standard 14393 (...)"` | **Yes** — `smb-os-discovery` has already fully resolved the SKU and explicitly states "Windows Server." |
| Bare build number, unresolved | `"10.0.26100"`, `"10.0.19041"`, `"6.3.9600"`, `"10.0.17763"`, `"10.0.22631"` | **No** — a bare build number is never treated as evidence by this plan, regardless of whether the underlying build happens to be server-only, client-only, or shared. This plan hard-codes exactly **one** exception below. |
| The one unambiguous exception | `"10.0.20348"` (exact value) | **Yes, as its own explicit, narrow, hard-coded literal** — `10.0.20348` is Windows Server 2022's build number and is not reused by any Windows client release (verified against every `operating_system` value in this dataset and against public Microsoft servicing documentation). This plan treats it as an exact-value check on `operating_system`, never a substring or range check, and never generalizes to "nearby" build numbers. |
| Explicit client caption | `"Windows 10 Enterprise 19045 (...)"`, `"Windows 7 Professional 7601 Service Pack 1 (...)"` | No (not server evidence; also not treated as workstation evidence by this plan — no fallback rule of any kind is introduced here, per the hard exclusions). |
| Non-Windows OS spoofing an SMB caption | `"Windows 6.1 (Samba 4.7.6-Ubuntu)"` | No — explicitly excluded by the hard exclusions (no Samba-based inference), and irrelevant to this plan's design regardless, since this plan never triggers on a bare `"6.1"`/`"windows 6.1"` value in the first place. |
| Ambiguous range in a *product* string (not `operating_system`) | `"Microsoft Windows Server 2008 R2 - 2012 microsoft-ds"` | **No.** This string only ever appears in a `ServiceEvidence.product` field (nmap's own uncertainty notation when it cannot pin an exact SKU), never in `operating_system`. This plan does not read `product` strings for the new rule at all (Section 3.3) — this shape is excluded by construction, not by an explicit check against it. |

**Conclusion (Design Question 1): "high-confidence Windows Server evidence" is defined as exactly two independent conditions on `device.operating_system` alone:**

1. `operating_system` is non-empty and contains the substring `"windows server"` (case-insensitive) — matches every fully-resolved Server caption in the dataset, and only those.
2. `operating_system` equals exactly `"10.0.20348"`.

No other field, no range/partial product string, and no other build number is consulted by this predicate.

---

## 2. Exact Production Devices Affected

### 2.1 Confirmed `PrinterVendorRule` misclassifications (all four, exact evidence)

| Device | Hostname | Vendor | `operating_system` | Port 515 evidence | Current winning rule / reason |
|---|---|---|---|---|---|
| `172.16.100.17` | `sct0003.wrf.scterm.com` | Microsoft | `Windows Server 2003 R2 3790 Service Pack 2 (...)` | `service=printer`, **`product="Microsoft lpd"`** | `PrinterVendorRule`: "Open TCP port 515 (LPD) indicates printer networking. Detected PRINTER service indicates printer networking." |
| `172.16.100.53` | `sctts02.wrf.scterm.com` | Dell | `Windows Server 2003 R2 3790 Service Pack 2 (...)` | `service=printer`, **`product="Microsoft lpd"`** | same reason |
| `172.16.100.55` | `sctts04.wrf.scterm.com` | Microsoft | `Windows Server 2003 R2 3790 Service Pack 2 (...)` | `service=printer`, **`product="Microsoft lpd"`** | same reason |
| `172.16.101.6` | `VM-3030-WIN7.wrf.scterm.com` | Microsoft | *(none — `operating_system` is null)* | `service=printer`, **`product="Microsoft lpd"`** | same reason |

All four also carry `Microsoft Terminal Service(s)` on port 3389 and `microsoft-ds` on port 445; three of the four carry an explicit `"Windows Server 2003 R2..."` `operating_system` caption. The fourth has none — the only evidence common to all four, and the evidence this plan's fix actually keys on, is the **`product` field of the matched port-515 `ServiceEvidence` entry itself: `"Microsoft lpd"`.**

**Intended post-RULE-006 outcome:**
- `172.16.100.17`, `172.16.100.53`, `172.16.100.55` → `SERVER` (their explicit "Windows Server 2003 R2..." caption qualifies under the new rule, Section 3.2, once `PrinterVendorRule` stops claiming them first — Section 4).
- `172.16.101.6` → `UNKNOWN` (the printer misclassification is removed; no other rule, including the new one, has sufficient evidence to assign anything else — it has no `operating_system` value at all). This is a correct, honest outcome under this sprint's "no generic Windows → WORKSTATION fallback" exclusion, not an incomplete fix.

### 2.2 Confirmed `DellWorkstationRule` misclassification

| Device | Hostname | Vendor | `operating_system` | Port 445 evidence | Current winning rule / reason |
|---|---|---|---|---|---|
| `172.16.100.19` | `SCT0008.wrf.scterm.com` | Dell | `Windows Server 2019 Standard 17763 (Windows Server 2019 Standard 6.3)` | `product="Windows Server 2019 Standard 17763 microsoft-ds"` | `DellWorkstationRule`: "Vendor 'Dell' matched known workstation vendor." |

This is the only `WORKSTATION`-classified device in the entire 244-device dataset carrying any Windows-Server-grade OS evidence (verified by sweeping every `workstation`-classified device's `operating_system` field) — confirming the fix is narrowly scoped to exactly the reported case, with no other latent instance in this dataset.

**Intended post-RULE-006 outcome:** `172.16.100.19` → `SERVER`.

### 2.3 Currently-`UNKNOWN` devices with high-confidence Windows Server evidence

| Device | Hostname | `operating_system` | Basis |
|---|---|---|---|
| `172.16.100.15` | `SCTSEPS.wrf.scterm.com` | `Windows Server 2012 R2 Datacenter 9600 (...)` | Explicit caption |
| `172.16.100.52` | `sctts01.wrf.scterm.com` | `Windows Server 2003 R2 3790 Service Pack 2 (...)` | Explicit caption |
| `172.16.102.85` | `sctts03.wrf.scterm.com` | `Windows Server 2003 R2 3790 Service Pack 2 (...)` | Explicit caption |
| `172.16.100.54` | `SCTRDS1.wrf.scterm.com` | `10.0.20348` | Exact Server-2022 build |
| `172.16.101.180` | `SCT0025.wrf.scterm.com` | `10.0.20348` | Exact Server-2022 build |

**Intended post-RULE-006 outcome:** all five → `SERVER`.

### 2.4 Devices that MUST NOT change (explicit regression set, confirmed by real data)

| Device | Hostname | `operating_system` | Current classification | Why it must not change |
|---|---|---|---|---|
| `172.16.100.28` | `SCTVSH03.wrf.scterm.com` | `10.0.20348` (the exact literal this plan also treats as high-confidence) | `HYPERVISOR` (via `HypervisorHostnameRule`'s `"vsh"` hostname keyword) | Real proof that the new rule must run **after** `HypervisorHostnameRule` (Section 4). |
| `172.16.100.11` | `SCTVSH01.wrf.scterm.com` | `6.3.9600` (ambiguous, excluded) | `HYPERVISOR` | Sibling case; product field shows the ambiguous range string (`"Microsoft Windows Server 2008 R2 - 2012 microsoft-ds"`) — must not be read as server evidence by anything. |
| `172.16.100.12` | `SCTVSH02.wrf.scterm.com` | `6.3.9600` (ambiguous, excluded) | `HYPERVISOR` | Same as above. |
| `172.16.100.20` | `SCT00DC1.wrf.scterm.com` | `Windows Server 2016 Standard 14393 (...)` | `SERVER` (via `ServerHostnameRule`'s `"dc"` hostname match) | Must remain `SERVER` via its existing rule, unaffected by the new rule's placement after `ServerHostnameRule`. |
| `172.16.100.21` | `SCT00DC2.wrf.scterm.com` | `Windows Server 2016 Standard 14393 (...)` | `SERVER` (via `ServerHostnameRule`) | Same as above. |
| `172.16.100.14` | `SCT0020.wrf.scterm.com` | `6.3.9600` (ambiguous, excluded) | `UNKNOWN` | Must **stay** `UNKNOWN` — proves the ambiguous-build exclusion holds even though its `product` field mentions a Windows Server range. |
| `172.16.100.25` | `PWD.wrf.scterm.com` | `6.3.9600` (ambiguous, excluded) | `UNKNOWN` | Same as above. |
| `172.16.102.103` | `SCT00CA.wrf.scterm.com` | `6.3.9600` (ambiguous, excluded) | `UNKNOWN` | Same as above. |
| All 27 current `PRINTER` matches except the 4 in §2.1 | — | — | `PRINTER` | Verified: none of the other 23 have any `operating_system` value at all except `172.16.100.201` (`"FXNICOS 0.1 (FXNIC 0.01)"`, a Fuji Xerox printer-NIC firmware string, not Windows-related) — confirming the fix cannot steal any other printer match. |

---

## 3. Proposed Rule Changes

### 3.1 `PrinterVendorRule` — internal exclusion, keyed on the matched service entry's own `product` field (Design Question 3)

**What the real evidence supports, precisely (re-stating Section 1.2's finding):** the networking tier (`_find_printer_networking()`) currently treats a bare match on port `{515, 631, 9100}` or service name `{"ipp", "ipps", "jetdirect", "lpd", "printer", "raw", "pdl-datastream"}` as sufficient evidence of a physical printer, with no check on *what* is reporting that port/service. All four confirmed misclassifications share `product == "Microsoft lpd"` on the exact entry that produced the match.

**Fix:** when the networking tier finds a candidate port/service match, also inspect the `product` field of the specific `ServiceEvidence` entry that produced that match. If it indicates a Microsoft-branded implementation (contains `"microsoft"`, case-insensitive), treat this as **not** printer-networking evidence — a Windows host running an LPD/print-spooler service is not itself a printer.

**Why this is narrower and more correct than the prior investigation's guessed heuristic ("exclude when SMB port 445 + RDP port 3389 are also open"):**
- It fixes all four confirmed cases, including `172.16.101.6` (no `operating_system` at all), which a device-wide SMB/RDP-port exclusion would also have fixed — so on this dataset the two approaches happen to agree on outcome. The product-field check is preferred anyway because it is self-contained to the exact evidence being evaluated (no need to reach into unrelated ports), and it cannot suppress a genuine multi-function printer that happens to also expose SMB for scan-to-network-share (a real feature class the port-445-exclusion approach would have put at risk; the product-field check never triggers on a genuine printer vendor's own LPD/IPP/JetDirect product string).
- It requires no dependency on `operating_system` at all, so it is unaffected by whether `smb-os-discovery` succeeded in resolving a caption — exactly matching evidence rather than "Windows-like" inference the sprint says not to assume.

**Implementation-shape note (not code, per this plan's scope):** `_find_printer_networking()` currently calls two independent helpers — `first_matching_port(service_ports(...), ...)` and `first_matching_service(service_names(...), ...)` — which each scan a flattened list and can, in principle, return matches from two different `ServiceEvidence` entries. The fix needs the *entry* that produced the match (to read its `product`), not just the bare port/service value the existing helpers return. This is a small, local restructuring inside `PrinterVendorRule` (iterate `device.services` directly for this one check, or add a narrowly-scoped helper that returns the matching entry) — flagged here as a real implementation-complexity item for the FEAT sprint, not resolved by this plan.

**This exclusion is *not* shared with the other two corrections** (Design Question 6) — it is scoped to `PrinterVendorRule` alone, because its evidence source (a specific service entry's `product` field) is a genuinely different shape from `operating_system`-based evidence, and because it is the only one of the three corrections needed to fix `172.16.101.6` (which has no `operating_system` evidence for a shared helper to key on).

### 3.2 New rule: high-confidence Windows Server classification (Design Questions 1, 2)

A new rule (working name `WindowsServerRule`) implements exactly the two-branch predicate from Section 1.3:

- **Branch 1 — explicit caption:** `operating_system` contains `"windows server"` (case-insensitive) → `SERVER`.
- **Branch 2 — exact Server-2022 build:** `operating_system == "10.0.20348"` → `SERVER`.

**One rule, two internal branches, not two separate rule classes (Design Question 2):** both branches produce the same `DeviceType.SERVER` outcome from the same conceptual evidence family ("Windows Server, as resolved by SMB/RDP OS negotiation"), differing only in *how* that evidence presents. This mirrors the codebase's existing convention of one rule class bundling multiple evidence tiers for one outcome (e.g., `HypervisorHostnameRule` bundles hostname-keyword, port, service, product, and OS-corroboration checks in one class; `NetworkApplianceRule` bundles identifier/vendor/hostname checks in one class). Splitting into two rule classes here would be artificial ceremony with no benefit, since `DeviceClassifier`'s list is not the mechanism used to express "this is one evidence family" — a single class already is. The `RuleResult.reason` string states which branch actually fired, following the existing per-rule pattern of naming the specific evidence that matched (e.g. `PrinterVendorRule`'s `label, value` reporting).

**No corroborating port/service check is added.** Unlike `HypervisorHostnameRule` (which corroborates a hostname match with port 443/3389 or a VMware product string) or `ServerHostnameRule` (which corroborates a hostname match with an OS keyword), this rule's *only* signal is `operating_system` itself — because `operating_system` is populated exclusively by SMB/RDP-based OS negotiation (per `Device`'s own field documentation), it already carries a narrow, single-source provenance no additional port/service corroboration would meaningfully strengthen. Adding one would be complexity this sprint's "deliberately narrow" framing does not justify; verifying this provenance assumption against the discovery-side SMB provider is a reasonable quick check for whoever implements the FEAT, but does not block this plan.

### 3.3 `DellWorkstationRule` — no internal code change; protected by ordering (Design Question 4)

**Design Question 4 asked how `DellWorkstationRule` should defer when Windows Server evidence exists.** Re-investigation found this does not require an internal code change to `DellWorkstationRule` at all: because the new rule's Section 3.2 predicate is a strict superset of what would ever need to trigger a defensive exclusion inside `DellWorkstationRule` (every device `DellWorkstationRule` could wrongly claim via its bare `"dell"` vendor check that also has high-confidence Windows Server evidence is, by construction, a device the new rule already claims first) — placing the new rule **before** `DellWorkstationRule` in `DeviceClassifier`'s list resolves Design Question 4 entirely through ordering, with the identical predicate, and zero duplicated logic.

**This is a deliberate design choice, not an oversight,** and mirrors this codebase's own established practice of using rule *ordering* — not per-rule defensive code — to resolve precedence between two rules that could otherwise both claim the same device (the existing `DeviceClassifier` docstring already documents exactly this reasoning for why `VoiceVendorRule` precedes `SwitchVendorRule`, and why `SwitchVendorRule`/`VoiceVendorRule` precede `PrinterVendorRule`). The tradeoff — noted honestly per Design Question 7 — is that this protection is ordering-dependent: if a future engineer moves `DellWorkstationRule` ahead of the new rule for an unrelated reason, this protection silently disappears with no unit-test failure inside `DellWorkstationRule`'s own test file to catch it (only a full-pipeline/integration test would). This exact risk shape already exists for every other ordering-dependent precedence relationship in `DeviceClassifier` today (e.g., `CameraVendorRule`/`PrinterVendorRule` keyword non-overlap, `VoiceVendorRule`/`SwitchVendorRule` Cisco-phone precedence) and is mitigated the same way the codebase already mitigates it: an explicit, permanent comment in `DeviceClassifier.__init__`'s docstring stating the dependency and why (Section 4), plus an integration-level regression test (Section 7) that would fail if ordering were ever changed.

**Why this is *not* also true for `PrinterVendorRule` (Design Question 3 vs. 4 have genuinely different answers):** as established in Section 3.1, `172.16.101.6` has no `operating_system` evidence at all, so it can never be "claimed first" by the new OS-based rule regardless of ordering — `PrinterVendorRule`'s own internal fix is the only mechanism that resolves it. Ordering alone would resolve 3 of the 4 confirmed printer cases (the ones with an explicit caption) but not the 4th, so `PrinterVendorRule`'s internal fix remains necessary as a backstop even after the new rule is correctly positioned before it.

---

## 4. Rule-Ordering Decision (Design Question 5)

**The new rule is placed immediately after `CameraVendorRule` and immediately before `PrinterVendorRule`** — position 9 of what becomes an 11-rule list:

```
1. ServerHostnameRule        7. SwitchVendorRule
2. NetworkApplianceRule      8. CameraVendorRule
3. HypervisorHostnameRule    9. WindowsServerRule      <- NEW
4. UbiquitiAccessPointRule  10. PrinterVendorRule       (internal fix, Section 3.1)
5. SonicWallFirewallRule    11. DellWorkstationRule     (unchanged, protected by position 9)
6. VoiceVendorRule
```

**Why exactly here, grounded in the real regression set (Section 2.4), not a general principle alone:**

- **Must run after `HypervisorHostnameRule` (position 3).** `SCTVSH03` (`operating_system == "10.0.20348"`, the plan's own exact-match literal) is real production evidence, currently correctly `HYPERVISOR` via the `"vsh"` hostname keyword. If the new rule ran before `HypervisorHostnameRule`, this device would flip to `SERVER`, a real regression against real data — not a hypothetical.
- **Must run after `ServerHostnameRule` (position 1).** `SCT00DC1`/`SCT00DC2` are real, correctly-classified `SERVER` devices via hostname `"dc"` matching; there is no conflict either way (both rules agree on `SERVER`), but preserving existing precedence keeps `ServerHostnameRule`'s hostname-based reasoning authoritative for devices it already explains, consistent with this codebase's "hostname-based identity signals outrank vendor/OS-based ones" precedent (already documented in `PLAN-RULE-005` for the analogous `ServerHostnameRule`-before-`CameraVendorRule` relationship).
- **No conflict exists, but no benefit either, from placing it any earlier than position 9.** `UbiquitiAccessPointRule`, `SonicWallFirewallRule`, `VoiceVendorRule`, `SwitchVendorRule`, and `CameraVendorRule` all gate on vendor strings (`ubiquiti`, `sonicwall`, voice vendors, `cisco`, `axis communications`) that never co-occur with the Microsoft/Dell/Intel-vendor Windows hosts this plan targets — verified by checking that none of the 8 affected devices (Section 2) carry any of those vendor strings. Placing the new rule any earlier than position 9 would be unjustified movement with no evidence behind it.
- **Must run before `PrinterVendorRule` and `DellWorkstationRule` (positions 10-11).** This is the mechanism that resolves Design Question 4 for `DellWorkstationRule` (Section 3.3) and resolves 3 of 4 `PrinterVendorRule` cases via ordering alone (Section 3.1), with `PrinterVendorRule`'s own internal fix (Section 3.1) as the necessary backstop for the 4th.

This placement is the latest position in the pipeline that still achieves both required pre-emptions, directly satisfying the sprint's own instruction to place the rule "late enough... that it does not preempt more specific existing rules."

---

## 5. False-Positive Analysis

| Risk | Assessment |
|---|---|
| A real printer gets excluded from `PrinterVendorRule` by the new product-field check | **None observed, structurally unlikely.** No genuine printer vendor (Brother, HP, Canon, Ricoh, Konica Minolta, Epson, Xerox, Lexmark, Kyocera, Sharp, Toshiba, Zebra, Datamax, Fujifilm) reports `"Microsoft"` as its own LPD/IPP/JetDirect product string — verified against all 27 current `PRINTER` matches (Section 2.4), none of which would be affected. |
| A real Dell workstation gets swept into `SERVER` by the new rule | **None possible.** The new rule triggers only on `operating_system` evidence; a genuine Dell client machine's OS caption never contains `"windows server"` and is never exactly `"10.0.20348"` (a server-exclusive build). `DellWorkstationRule`'s hostname-keyword branch (`optiplex`/`latitude`/`precision`/`xps`/`vostro`/`inspiron`) is entirely untouched by this plan and continues to match Dell client hardware regardless of ordering. |
| A Hyper-V host gets misclassified `SERVER` instead of `HYPERVISOR` | **Prevented by ordering, confirmed against 3 real devices** (`SCTVSH01`, `SCTVSH02`, `SCTVSH03` — Section 2.4), not merely asserted. |
| An ambiguous-build Windows Server host (`6.3.9600` shared with Win 8.1; `10.0.26100` shared with Win 11 24H2) never gets classified `SERVER` when it actually is one | **Accepted, by design, per the hard exclusions.** This is a deliberate false-negative (a real server stays `UNKNOWN`), not a false positive — consistent with "ambiguous build-number guessing" being explicitly out of scope. Three real devices (`SCT0020`, `PWD`, `SCT00CA`) are confirmed to sit in exactly this state and are expected to remain `UNKNOWN` after this plan ships. |
| A non-Windows device (e.g., a NAS or embedded Linux box using Samba to expose SMB) gets classified `SERVER` | **Not possible under this design.** The predicate requires `"windows server"` as a substring or the exact literal `"10.0.20348"`; a Samba-based `operating_system` caption (e.g., `"Windows 6.1 (Samba 4.7.6-Ubuntu)"`) does not contain `"windows server"` and is never `"10.0.20348"`, so it is excluded by construction — no explicit Samba-detection logic is needed or added (the hard exclusion against "Samba-based inference" is satisfied by not needing any). |
| `172.16.101.6` (`VM-3030-WIN7`) ends up with no classification after losing its (wrong) `PRINTER` label | **Accepted, correct outcome.** This is the intended, honest result of removing a wrong answer where no rule has sufficient evidence to supply a right one — not a regression, and not something this plan's hard exclusions (no generic Windows fallback) permit fixing further. |

---

## 6. Files Likely Affected

| File | Change |
|---|---|
| `networkmapper/classification/rules/windows_server_rule.py` | **New.** `WindowsServerRule`, implementing the two branches in Section 3.2. |
| `networkmapper/classification/rules/printer_vendor_rule.py` | Internal change to `_find_printer_networking()` (or a narrowly-scoped helper it calls) to exclude a matched port/service entry whose own `product` field indicates a Microsoft-branded implementation (Section 3.1). |
| `networkmapper/classification/device_classifier.py` | Import and register `WindowsServerRule` at position 9 (between `CameraVendorRule` and `PrinterVendorRule`); extend the class docstring's ordering rationale to document the two dependencies from Section 4 (mirroring the existing documented-rationale style already used for `VoiceVendorRule`/`SwitchVendorRule`/`CameraVendorRule`/`NetworkApplianceRule`). |
| `tests/test_windows_server_rule.py` | **New.** Unit tests for `WindowsServerRule` (Section 7). |
| `tests/test_printer_vendor_rule.py` | Add regression tests for the `"Microsoft lpd"` exclusion, using the real captured evidence shape (Section 7). |
| `tests/test_dell_workstation_rule.py` | Add a regression test proving the *existing*, unmodified rule still returns `WORKSTATION` on its own for a Dell-vendor device with no Windows Server evidence (confirms no code change was needed there — Section 7). |
| `tests/test_hypervisor_hostname_rule.py` | No code change expected; add a regression test using the real `SCTVSH03`-shaped evidence (`"vsh"` hostname + `operating_system == "10.0.20348"`) to lock in the precedence this plan depends on. |
| `tests/test_classifier.py` | Add integration-level regression tests exercising the full pipeline for every device in Section 2 (Section 7). |
| `devtools/validate.py` (`STANDARD_REGRESSION_TESTS`) | Likely needs `tests.test_windows_server_rule` added to the fast-path regression list, alongside the other classification-rule test modules already listed there (`test_printer_vendor_rule`, `test_dell_workstation_rule`, `test_hypervisor_hostname_rule`, `test_server_hostname_rule`, etc.) — confirm exact list membership at implementation time. |

**Confirmed unaffected:** `core/models.py` (no new `DeviceType` value — none is needed, unlike RULE-005's `CAMERA` addition), `classification_rule.py`, `rule_result.py`, `evidence_helpers.py` (no new shared Device-level helper is introduced — Section 3.1's fix and Section 3.2's predicate are each implemented locally, per Design Question 6's answer), `server_hostname_rule.py`, `network_appliance_rule.py`, `ubiquiti_access_point_rule.py`, `sonicwall_firewall_rule.py`, `voice_vendor_rule.py`, `switch_vendor_rule.py`, `camera_vendor_rule.py`, discovery, enrichment, exporters, serialization, CLI.

---

## 7. Test Plan

1. **Known Windows print server no longer classifies as `PRINTER`** — `tests/test_printer_vendor_rule.py`: a device with port 515 `service="printer"`, `product="Microsoft lpd"` (reproducing all four real hosts' exact evidence shape) returns not-matched from `PrinterVendorRule`.
2. **Genuine printer remains `PRINTER`** — every existing `test_printer_vendor_rule.py` case re-run unmodified (vendor keywords, product/HTTP-title/auth-realm/SNMP identifier tiers, and the existing networking-tier tests using a real printer's own LPD/IPP/JetDirect product strings, e.g. none of which say "Microsoft"); a new explicit case confirms a printer-vendor device with port 515 and a *non-Microsoft* (or absent) product string still matches exactly as today.
3. **Dell PowerEdge + Windows Server evidence no longer classifies as `WORKSTATION`** — via `tests/test_classifier.py` (the full pipeline, since the fix is ordering-based, not internal to `DellWorkstationRule` — Section 3.3): a device shaped like `172.16.100.19` (vendor `"Dell"`, `operating_system` containing `"Windows Server 2019..."`) classifies `SERVER` via `WindowsServerRule`, never reaching `DellWorkstationRule`.
4. **Genuine Dell workstation remains `WORKSTATION`** — `tests/test_dell_workstation_rule.py`: every existing case re-run unmodified (bare `"Dell"` vendor with no OS evidence, `optiplex`/`latitude`/etc. hostname patterns), proving the rule itself needed no change; plus a new full-pipeline test in `test_classifier.py` confirming a Dell device with an *explicit client* OS caption (e.g. `"Windows 10 Enterprise..."`) still reaches and matches `DellWorkstationRule`.
5. **Explicit Windows Server evidence → `SERVER`** — `tests/test_windows_server_rule.py`: each of the three real caption shapes from Section 2.3/2.1 (`"Windows Server 2003 R2..."`, `"Windows Server 2012 R2 Datacenter..."`, `"Windows Server 2019 Standard..."`) matches, case-insensitively.
6. **Build `10.0.20348` → `SERVER`, confirmed the retained evidence supports it** — `tests/test_windows_server_rule.py`: `operating_system == "10.0.20348"` with no other evidence matches; reproduces `SCTRDS1`/`SCT0025`'s exact shape.
7. **Ambiguous Windows build does NOT automatically classify as `SERVER`** — `tests/test_windows_server_rule.py`: `operating_system == "6.3.9600"` alone does not match (reproduces `SCT0020`/`PWD`/`SCT00CA`'s real evidence exactly); `operating_system == "10.0.26100"` alone does not match; a device whose only Windows-Server-shaped evidence is a `product` field (not `operating_system`) containing `"Windows Server 2008 R2 - 2012"` does not match (proving the rule never reads `product`, only `operating_system`).
8. **Samba/non-Windows SMB device does NOT become `SERVER`** — `tests/test_windows_server_rule.py`: `operating_system == "Windows 6.1 (Samba 4.7.6-Ubuntu)"` does not match (contains neither `"windows server"` nor the exact `"10.0.20348"` literal).
9. **Existing `HypervisorHostnameRule` behavior remains intact** — `tests/test_hypervisor_hostname_rule.py`: every existing case re-run unmodified; a new case reproduces `SCTVSH03`'s real shape (hostname `"vsh"`-pattern, `operating_system == "10.0.20348"`) and confirms `HypervisorHostnameRule` alone still returns `HYPERVISOR`; a full-pipeline test in `test_classifier.py` confirms the *same* device, run through the complete ordered classifier, still resolves to `HYPERVISOR` and never reaches `WindowsServerRule`.
10. **Existing `ServerHostnameRule` behavior remains intact** — `tests/test_server_hostname_rule.py`: every existing case re-run unmodified; a full-pipeline test confirms a `SCT00DC1`-shaped device (hostname `"dc"` pattern + explicit `"Windows Server 2016..."` caption) still resolves to `SERVER` via `ServerHostnameRule` specifically (not `WindowsServerRule`), i.e. it never reaches position 9.
11. **Full classifier regression suite remains green** — `pytest tests/ -q` and `python -m devtools validate --all`, both with zero new failures against the current baseline (661 passed as of FEAT-027).
12. **Production replay demonstrates only intended devices change** — a dedicated regression test (or a documented one-off replay, per whichever the FEAT sprint's own validation section prefers) re-classifies all 244 real devices from `output/Test Network.nmproj` with the post-RULE-006 code and asserts: exactly the 9 devices in Sections 2.1-2.3 change (3 printer→server, 1 printer→unknown, 1 workstation→server, 5 unknown→server — noting `172.16.100.19` and the three explicit-caption unknowns total the 5 "unknown→server" count correctly: `SCTSEPS`, `sctts01`, `sctts03`, `SCTRDS1`, `SCT0025`), and every other one of the remaining 235 devices' `device_type` is byte-identical to the current-code baseline captured during this investigation.

---

## 8. Acceptance Criteria

1. `WindowsServerRule.classify(device)` returns `SERVER` when `device.operating_system` contains `"windows server"` (case-insensitive) or equals exactly `"10.0.20348"`, and not-matched otherwise.
2. `WindowsServerRule` never reads `product`, `http_title`, `tls_subject`, `tls_issuer`, `http_auth_realm`, `snmp_sys_descr`, `vendor`, or `hostname` — `operating_system` is the sole input.
3. `WindowsServerRule` is registered in `DeviceClassifier` at position 9 (after `CameraVendorRule`, before `PrinterVendorRule`).
4. `PrinterVendorRule`'s networking tier no longer matches when the matched port/service entry's own `product` field indicates a Microsoft-branded implementation; every other `PrinterVendorRule` matching path (vendor tier, identifier tier) is unchanged.
5. `DellWorkstationRule`'s source code is unmodified; its existing behavior for every currently-passing test case is unchanged.
6. All ten real production devices in Sections 2.1-2.3 change classification exactly as specified; all devices in Section 2.4 (the explicit regression set) do not change.
7. No new `DeviceType` value is introduced.
8. No new shared helper is added to `evidence_helpers.py`; the printer-tier fix and the new rule's predicate are each implemented locally within their own rule file.
9. `pytest tests/ -q` and `python -m devtools validate --all` both pass with zero regressions once implemented.

---

## 9. Explicit Non-Goals

Restating this sprint's own required exclusions, cross-referenced to where each is upheld:

- **No generic Windows → `WORKSTATION` fallback** — `WindowsServerRule` only ever produces `SERVER`; `172.16.101.6` (no qualifying evidence) is left `UNKNOWN`, not defaulted to `WORKSTATION` (Section 2.1, Section 5).
- **No ambiguous build-number guessing** — only the single, exact, hard-coded `"10.0.20348"` literal is treated as build-based evidence; every other build number (`6.3.9600`, `10.0.19041`, `10.0.26100`, `10.0.22631`, `10.0.17763`) is deliberately inert to this rule (Section 1.3, Section 7 item 7).
- **No Windows 8.1 / Server 2012 R2 shared-build assumption** — `6.3.9600` is explicitly excluded and tested against real devices that would otherwise wrongly qualify (`SCTVSH01`, `SCTVSH02`, `SCT0020`, `PWD`, `SCT00CA`).
- **No Windows 11 / Server 2025 shared-build assumption** — `10.0.26100` is not treated as evidence anywhere in this design.
- **No Samba-based inference** — no Samba-specific detection logic is added or needed (Section 5).
- **No EdgeOS / UniFi OS router work, no TP-Link work, no Cisco hardening, no HP hardening, no `ServerHostnameRule` cleanup, no SNMP `sysObjectID` classification** — none of these are touched by any file in Section 6.
- **No taxonomy changes, no new `DeviceType` values** — confirmed in Section 6 and Acceptance Criterion 7.
- **No discovery or enrichment changes** — confirmed in Section 6; `operating_system` is already collected today by existing SMB/RDP discovery, unmodified by this plan.

---

## 10. Open Questions

- **Exact rule file/class name.** This plan uses `WindowsServerRule` as a working name (`networkmapper/classification/rules/windows_server_rule.py`). An architect may prefer a name that more precisely scopes it to OS-evidence-based classification (e.g., to leave room for a *possible*, explicitly-separate future `WORKSTATION`-side rule using the same evidence family) — naming is not load-bearing to this design and can be finalized at implementation time.
- **`devtools/validate.py`'s `STANDARD_REGRESSION_TESTS` membership** — Section 6 flags that the new test module likely belongs in the fast-path regression list alongside its sibling classification-rule test modules; the exact list edit is a one-line addition to confirm during implementation, not a design decision this plan needs to resolve.
- **Whether the "production replay" test (Section 7, item 12) should be a permanent, checked-in regression test or a one-time validation artifact reported in the FEAT's own deliverables** (mirroring how `PLAN-RULE-005`'s Section 5.1 item 5 re-ran the curated benchmark datasets as a validation step rather than a permanent new test asset). This plan recommends treating it as a permanent test given how directly it encodes this plan's own Section 2 evidence table, but leaves the final call to whoever implements the FEAT.
- **Whether `PrinterVendorRule`'s product-field restructuring (Section 3.1's implementation-shape note) is best done as a small local change inside `printer_vendor_rule.py` or as a narrowly-scoped new `evidence_helpers.py` function returning the matching `ServiceEvidence` entry rather than just its port/service value.** This plan intentionally does not resolve this implementation detail (per "do not implement code"); Section 3.1 states only that the *evidence* the fix must consult is the matched entry's own `product` field, not which specific code shape delivers that.

---

## 11. git status

At the time this plan was written, no code was modified. Current working-tree state (for reference, unrelated to this plan):

```
 M review.diff
?? diff.md
?? docs/plans/PLAN-RULE-006-High-Confidence-Windows-Server-Classification.md
```
