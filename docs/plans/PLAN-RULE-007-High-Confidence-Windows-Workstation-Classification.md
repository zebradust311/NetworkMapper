# Status

Plan Proposed — Pending Review

Approval: Not yet architect-reviewed. Do not implement against this plan until it is approved.

Authority: A production-driven classification investigation (real production project file `output/Test Network.nmproj`, 244 devices) re-ran the current, shipped `DeviceClassifier` (post-RULE-006) against every device's actual retained evidence, specifically searching for a workstation-side counterpart to RULE-006's server-side discriminator. This plan reports what was and was not found, with no invented or hypothetical evidence anywhere in it.

Implements: RULE-007 — investigation phase complete; a narrow, evidence-backed implementation is recommended (Section 9) but requires explicit architect sign-off on a value judgment this plan cannot resolve on evidence alone (Section 12).

Production Code Modified: No. This is an investigation-and-planning sprint only; no source or test files are changed by this plan.

New ADR Required: No (Section 11) — if implemented, this is rule-content refinement within the existing `ClassificationRule`/`RuleResult` contract, the same class of change RULE-002 through RULE-006 already made.

---

## 1. Objective, Restated

Not "detect Windows." Determine whether the real production dataset contains a discriminator that identifies a Windows **workstation** specifically — as opposed to a Windows server, hypervisor host, or domain controller — with the same reliability bar RULE-006 met for the server side. If no such discriminator exists, recommend adding nothing.

## 2. Method

`output/Test Network.nmproj` (244 devices) was re-classified with the current, shipped classifier (11 rules, `WindowsServerRule` included). Every device carrying any Windows-flavored evidence was extracted using a deliberately broad net — `operating_system` mentioning "windows"/"microsoft", a bare `N.N.NNNNN` build-number shape, any service `product` mentioning "microsoft"/"windows", `computer_name`/`domain` populated (SMB-only fields), or port 445/3389 present — specifically so the net would also catch false candidates (evidence that looks Windows-like but isn't) for Section 6's negative-case check. This produced **77 of 244 devices**. Every one of the 77 was inspected individually, not sampled.

## 3. Question 1 — Exactly Which Windows Devices Remain UNKNOWN

**36 devices.** Full inventory (hostname, IP, `operating_system`, vendor, matched rule, complete retained evidence):

| IP | Hostname | Vendor | `operating_system` | Retained services (port: product/service) |
|---|---|---|---|---|
| 172.16.100.14 | SCT0020.wrf.scterm.com | Microsoft | `6.3.9600` | 445: `Microsoft Windows Server 2008 R2 - 2012 microsoft-ds`; 3389: `ms-wbt-server` |
| 172.16.100.25 | PWD.wrf.scterm.com | Microsoft | `6.3.9600` | 445: `Microsoft Windows Server 2008 R2 - 2012 microsoft-ds`; 3389: `ms-wbt-server` |
| 172.16.100.49 | SCT0035.wrf.scterm.com | Microsoft | `10.0.17763` | 445: `microsoft-ds`; 3389: `ms-wbt-server` |
| 172.16.100.82 | *(none)* | Giga-byte Technology | *(none)* | 80/443: Apache httpd, "SCTBackup2 - Control Panel" (Datto backup appliance); 445: **`Samba smbd`**, `netbios-ssn` |
| 172.16.101.0 | MIS3030a.wrf.scterm.com | ASUSTek Computer | `Windows 10 Enterprise 19045 (Windows 10 Enterprise 6.3)` | 80: `Microsoft IIS httpd`; 443: TLS subject/issuer naming the host and an internal CA; 445: `Windows 10 Enterprise 19045 microsoft-ds`; 3389: `Microsoft Terminal Services`, self-signed cert named after hostname |
| 172.16.101.1 | MIS4040A.wrf.scterm.com | Intel Corporate | `10.0.26100` | 80: `Microsoft HTTPAPI httpd`; 445: `microsoft-ds`; 3389: `Microsoft Terminal Services`, self-signed cert named after hostname |
| 172.16.101.2 | VM-3030-WIN7.wrf.scterm.com | Microsoft | `10.0.26100` | 80: `Microsoft IIS httpd`, "dashboard.aspx" 404; 3389: `Microsoft Terminal Services`, cert CN `VM-LoggingPC.wrf.scterm.com` (mismatched from device hostname/`computer_name=VM-LOGGINGPC`) |
| 172.16.101.6 | VM-3030-WIN7.wrf.scterm.com | Microsoft | *(none)* | 80: `Microsoft IIS httpd`, "IIS7"; 445: `microsoft-ds`; 515: `Microsoft lpd` (RULE-006 print-server fix applies here); 3389: `Microsoft Terminal Service`, self-signed cert named after hostname |
| 172.16.101.9 | SCTLT38.wrf.scterm.com | Microsoft | `10.0.26100` | 445, 3389 only |
| 172.16.102.2 | SCTSG14.wrf.scterm.com | Intel Corporate | `10.0.26100` | 3389 only |
| 172.16.102.17 | SCTSG31.wrf.scterm.com | Intel Corporate | `10.0.26100` | 3389 only |
| 172.16.102.24 | SCTSP15.wrf.scterm.com | Magic Control Technology | `10.0.26100` | 445, 3389 |
| 172.16.102.25 | SCTSP07.wrf.scterm.com | Microsoft | *(none)* | 445 only |
| 172.16.102.30 | SCT2051.wrf.scterm.com | Intel Corporate | `10.0.19041` | 445, 3389 |
| 172.16.102.31 | SCTSG02.wrf.scterm.com | Intel Corporate | `10.0.26100` | 445, 3389 |
| 172.16.102.40 | SCTLT9002.wrf.scterm.com | Intel Corporate | `10.0.26100` | 445, 3389 |
| 172.16.102.42 | SCTSP16.wrf.scterm.com | Microsoft | `10.0.26100` | 445, 3389 |
| 172.16.102.50 | SCTSPLT0010.wrf.scterm.com | Magic Control Technology | *(none)* | 445 only |
| 172.16.102.52 | SCTLT108.wrf.scterm.com | *(none)* | *(none)* | 445 only |
| 172.16.102.55 | SCTSP13.wrf.scterm.com | Microsoft | `10.0.26100` | 445, 3389 |
| 172.16.102.56 | SCTSP21.wrf.scterm.com | Intel Corporate | `10.0.26100` | 445, 3389 |
| 172.16.102.58 | SCTSP28.wrf.scterm.com | Microsoft | `10.0.26100` | 445, 3389 |
| 172.16.102.68 | SCT1094.wrf.scterm.com | ASUSTek Computer | `10.0.19041` | 3389 only |
| 172.16.102.71 | *(none)* | Microsoft | `10.0.22631` | 22: `OpenSSH`; 3389: `tcpwrapped`. `computer_name`/`domain` = `UBUNTUITSRV1` |
| 172.16.102.74 | SCTSPLT0002.wrf.scterm.com | Microsoft | *(none)* | 445 only |
| 172.16.102.84 | SCT2073.wrf.scterm.com | Intel Corporate | `10.0.19041` | 3389 only |
| 172.16.102.89 | SCTSP14.wrf.scterm.com | Microsoft | `10.0.26100` | 445, 3389 |
| 172.16.102.103 | SCT00CA.wrf.scterm.com | Microsoft | `6.3.9600` | 445: `Microsoft Windows Server 2008 R2 - 2012 microsoft-ds` |
| 172.16.102.108 | OINSIGHT.wrf.scterm.com | Microsoft | `10.0.19041` | 445, 3389 |
| 172.16.102.112 | *(none)* | Microsoft | `Windows 6.1 (Samba 4.7.6-Ubuntu)` | 80: `Apache httpd`; 445: `Samba smbd`; `computer_name=vm-mis3030-ubuntu2` |
| 172.16.102.115 | SCTLTARM001.wrf.scterm.com | Cloud Network Technology Singapore PTE. | `10.0.26100` | 3389 only |
| 172.16.102.119 | SCTSP26.wrf.scterm.com | Microsoft | `10.0.26100` | 445, 3389 |
| 172.16.102.122 | SCTSG48.wrf.scterm.com | Intel Corporate | `10.0.26100` | 3389 only |
| 172.16.102.148 | SCTSP23.wrf.scterm.com | Intel Corporate | `10.0.26100` | 445, 3389 |
| 172.16.102.153 | SCTSG17.wrf.scterm.com | Intel Corporate | `10.0.26100` | 3389 only |
| 172.16.102.161 | MISLT03.wrf.scterm.com | Intel Corporate | `10.0.19041` | 445, 3389 |

No rule currently matches any of these 36 (all show `winner=None`, i.e., they fall through the entire 11-rule pipeline to `UNKNOWN`).

## 4. Question 2 — Why Each Remains UNKNOWN

The 36 sort cleanly into four causes, not "insufficient investigation":

| Cause | Count | Devices |
|---|---:|---|
| **Ambiguous build number** — `operating_system` is a bare `N.N.NNNNN` value that Microsoft has issued to both a client and a server release train, so no reading of it alone is safe (the exact reasoning RULE-006 already applied and hard-excluded) | 28 | Every `10.0.26100` (15), `10.0.19041` (5), `6.3.9600` (3), plus `10.0.17763` (1) and `10.0.22631` (1) — see Section 5 for why each of these specific builds is ambiguous, not just "looks like a build number" |
| **Insufficient evidence** — no `operating_system` value at all, and no other field carries anything more specific than "port 445 is open" | 4 | `SCTSP07`, `SCTSPLT0010`, `SCTSPLT0002`, `SCTLT108` — the last of these has **no vendor either** |
| **Deliberate classifier behavior (correct, not a gap)** — evidence that *looks* Windows-shaped but is not a Windows host at all | 2 | `172.16.100.82` (a Datto backup appliance running **Samba**, not Windows, on port 445 — vendor `Giga-byte Technology` is the backup appliance's motherboard NIC, not a PC brand) and `172.16.102.112` (`operating_system` literally says `"Windows 6.1 (Samba 4.7.6-Ubuntu)"` — a Linux host whose Samba daemon reports a Windows-shaped SMB dialect string; genuinely not Windows) |
| **`VM-3030-WIN7` duplicate-hostname anomaly** — the same hostname resolves to two different IPs with different retained evidence (`.101.2` shows `operating_system=10.0.26100` and a TLS cert naming `VM-LoggingPC`; `.101.6` shows no `operating_system` at all and the RULE-006-fixed `Microsoft lpd` entry) | 2 | 172.16.101.2, 172.16.101.6 — a real environment data-quality artifact (stale DHCP lease, VM clone, or re-IP), not a classifier defect; already covered by the "ambiguous build" and "insufficient evidence" buckets respectively, listed separately here only to name the anomaly |

No device in this list is UNKNOWN because of a classifier bug. Every one is either genuinely ambiguous, genuinely evidence-starved, or genuinely not Windows.

## 5. Why the Specific Ambiguous Builds Are Ambiguous (Not Just Asserted)

Applying RULE-006's own standard (only an *exact*, *structurally unique* build number is trustworthy on its own — Section 1.3 of PLAN-RULE-006):

- **`10.0.26100`** (15 of the 36): shared by Windows 11 24H2 (client) and Windows Server 2025 — the exact ambiguity RULE-006's own hard exclusions name explicitly.
- **`6.3.9600`** (3 of 36): shared by Windows 8.1 (client) and Windows Server 2012 R2 — RULE-006's other named hard exclusion. Two of these three (`SCT0020`, `SCT00CA`) additionally show the **ranged** product string `"Microsoft Windows Server 2008 R2 - 2012 microsoft-ds"` on port 445 — nmap's own uncertainty notation, not a resolved value, and (per PLAN-RULE-006 Section 1.3) never treated as evidence by this codebase's Windows-classification rules.
- **`10.0.19041`** (5 of 36): Windows 10 version 2004. Microsoft never shipped a Semi-Annual-Channel Windows Server release against this or any later 19045+/2004+ client build (the SAC Server track ended at 1909); no Server SKU carries this exact build number as far as this investigation could establish. This makes it a *plausible* unambiguous-client candidate structurally similar to RULE-006's `10.0.20348` — but it is deliberately **not** proposed as evidence here (Section 8) because, unlike `10.0.20348`, no device in this dataset corroborates it with any second, independent signal, and Microsoft's SAC servicing history is a considerably less certain, less-official-documented fact than a GA release build number. Treated as an open question (Section 12), not asserted as safe.
- **`10.0.17763`** (1 of 36, `SCT0035`): shared by Windows 10 version 1809 (client) **and Windows Server 2019** — genuinely, unambiguously ambiguous; Server 2019 is a mainstream, still-supported release on this exact build.
- **`10.0.22631`** (1 of 36, `SCT0071`/`UBUNTUITSRV1`): Windows 11 23H2, client-only as far as this investigation could establish — same caveat as `10.0.19041` above: plausible, not corroborated, not proposed as evidence.

No device's ambiguity claim in this plan rests on assumption alone where a corroborating fact was checkable against this dataset; where a build's client-exclusivity could not be corroborated by a second independent signal, this plan says so explicitly rather than asserting it.

## 6. Question 3 — Does Any Evidence Pattern Uniquely Identify a Windows Workstation?

Each candidate the sprint asked about, investigated against the real data, not assumed:

| Candidate | Investigated | Result |
|---|---|---|
| **Explicit workstation edition in OS caption** (`Enterprise`, `Pro`, `Home`, `Professional`) | Swept `operating_system` across **all 244 devices**, every classification bucket, not just the 36 unknowns | **Found: exactly 2 devices in the entire dataset.** `172.16.101.0` (`"Windows 10 Enterprise 19045..."`, currently `UNKNOWN`) and `172.16.102.135` (`"Windows 7 Professional 7601..."`, already `WORKSTATION` via `DellWorkstationRule`'s bare Dell-vendor match). Zero occurrences of `Pro` or `Home` anywhere. See Section 7/8. |
| **SMB banners** | Compared port-445 `product` strings across every classification bucket | No workstation-specific banner text exists. The two client-edition devices above happen to carry it (because it duplicates the OS caption verbatim), but this is the same signal as the caption itself, not an independent one. |
| **NetBIOS naming** | Checked `netbios-ssn` service occurrences and hostname conventions | `netbios-ssn` appears on exactly 2 devices dataset-wide (both non-Windows: the Datto/Samba box and one other), zero relevance to workstation identification. Hostname convention at this site (`SCT####`, `SCTSG##`, `SCTSP##`, `SCTLT####`, `MISLT##`) is asset-tag-based and applied identically across servers, a hypervisor host (`SCTVSH0x`), domain controllers (`SCT00DC1/2`), and workstations — already established as non-discriminating in the RULE-006 investigation and reconfirmed here. |
| **WinRM** | Searched for ports 5985/5986 across all 244 devices | **Zero devices** anywhere in the dataset expose WinRM. No evidence exists to build on; not usable regardless of theoretical merit. |
| **RDP** | Compared port-combination distributions by classification bucket | `(445, 3389)`, `(3389,)`, and `(445,)` are the *dominant* combination in **every** bucket — `unknown`, `server`, `hypervisor`, and `workstation` alike (Section 6.1 below). RDP's presence carries zero workstation-vs-server signal in this environment. |
| **Workstation-specific service combinations** | Full port-combination cross-tab, all 4 relevant buckets | No combination is unique to any one bucket. See table below. |
| **Manufacturer/vendor evidence** | Compared vendor strings across `server`/`hypervisor`/`workstation`/`unknown` | **Rejected with direct proof.** `vendor="Intel Corporate"` appears on a currently-`SERVER` device (`172.16.100.28`'s sibling — one Intel-vendor server) *and* on a currently-`HYPERVISOR` device *and* on 12 of the 36 `UNKNOWN` devices. `vendor="Microsoft"` appears on 7 `SERVER` devices and 17 `UNKNOWN` devices. These are NIC/motherboard-chipset OUI vendors (MAC-address-derived), not PC-brand identifiers, and are indistinguishable between server and workstation hardware in this environment — the same class of over-broad-vendor risk this codebase already learned to avoid with `SwitchVendorRule`'s bare `"cisco"` and `DellWorkstationRule`'s bare `"dell"`. |

### 6.1 Port-combination cross-tab (the decisive negative evidence for the service-combination and RDP candidates)

| Classification | Dominant port combinations (count) |
|---|---|
| `unknown` | `(445,3389)`×13, `(3389,)`×9, `(445,)`×4, `(80,443,445,3389)`×3, others singletons |
| `server` | `(445,515,3389)`×3, `(80,445,3389)`×2, `(80,443,445,3389)`×2, `(53,445,3389)`×2, `(445,3389)`×2 |
| `hypervisor` | `(80,445,3389)`×2, `(3389,)`×1 |
| `workstation` | `(445,3389)`×17, `(3389,)`×3, `(445,)`×3, `(80,445)`×1 |

`(445,3389)` and `(3389,)` are each present as the *top* pattern in three of these four buckets simultaneously. No port/service shape distinguishes a workstation from a server or hypervisor host here.

## 7. Question 4 — Would Any Windows Server Devices Falsely Satisfy the Candidate Predicate?

**No.** The `"enterprise"`/`"professional"` edition-caption predicate was checked against every one of the 244 devices' `operating_system` field, across every classification bucket including all 12 currently-`SERVER` devices. Zero Server-classified device's OS caption contains either keyword — consistent with the fact that "Enterprise" and "Professional" are not, and have never been, Windows Server edition names (Server ships as Standard/Datacenter/Essentials); the observed Server captions in this dataset (`2003 R2`, `2012 R2 Datacenter`, `2016 Standard`, `2019 Standard`) confirm this pattern holds in practice here, not just in the abstract.

## 8. Question 5 — Would Any Hyper-V Hosts Satisfy Them?

**No.** All three `HYPERVISOR`-classified devices (`SCTVSH01`, `SCTVSH02`, `SCTVSH03`) were checked directly; none carries `"enterprise"` or `"professional"` anywhere in `operating_system` (two show the bare ambiguous `6.3.9600`, one shows the bare `10.0.20348`). Note for completeness, not as a finding requiring action: Windows 10/11 Pro and Enterprise editions *can* run client-side Hyper-V as an optional feature, so a hostname matching `HypervisorHostnameRule`'s convention on a genuine Enterprise-edition workstation is theoretically possible at some future site — but `HypervisorHostnameRule` runs at position 3, strictly before wherever a new workstation rule would sit (Section 10), so it would already win first regardless; this is a pre-existing, unrelated characteristic of `HypervisorHostnameRule`'s own hostname-based matching, not something a new rule introduces or needs to guard against.

## 9. Question 6 — Would Any Domain Controllers Satisfy Them?

**No.** Both domain-controller devices (`SCT00DC1`, `SCT00DC2`, both already `SERVER` via `ServerHostnameRule`'s `"dc"` hostname match) carry the explicit caption `"Windows Server 2016 Standard 14393..."` — no edition keyword overlap, and `ServerHostnameRule` runs at position 1, first in the entire pipeline, so it would win regardless of where a new workstation rule sits.

## 10. Question 7 — Overlap With `DellWorkstationRule`

**One overlap, confirmed exactly**: `172.16.102.135` (`SCT2053.wrf.scterm.com`, vendor `Dell`, `operating_system="Windows 7 Professional 7601 Service Pack 1..."`) is already correctly `WORKSTATION`, currently via `DellWorkstationRule`'s bare `"dell"` vendor match.

- **Would ordering matter?** Only for which rule's `reason` string wins, never for the final `device_type` — both rules agree on `WORKSTATION` for this device. If a new rule ran *before* `DellWorkstationRule`, it would claim this device instead (same outcome, different reason). If it ran *after* (this plan's recommendation, Section 10), `DellWorkstationRule` keeps winning exactly as it does today, and the new rule never even evaluates this device.
- **Would `DellWorkstationRule` become redundant?** No. It independently covers 23 other devices via its bare-vendor and hostname-pattern (`optiplex`/`latitude`/`precision`/`xps`/`vostro`/`inspiron`) branches, none of which carry an explicit client-edition caption. The new rule's scope (non-Dell-vendor devices with an explicit edition caption) and `DellWorkstationRule`'s scope (any Dell-vendor device, or any device with a Dell-model hostname, regardless of OS evidence) are almost entirely disjoint; they intersect at exactly this one device.
- **Would overlap be intentional?** No — it is incidental, a consequence of one real device happening to carry two independently-sufficient signals (Dell vendor, and an explicit client-edition caption). Placing the new rule last (Section 10) makes this overlap inert: zero behavior change for `DellWorkstationRule`'s existing, already-tested output on this device.

## 11. Replay Simulation (Required Gate)

A candidate rule — trigger: `operating_system` contains `"enterprise"` or `"professional"` (case-insensitive substring, matching exactly the two keywords actually observed, nothing speculative); action: `WORKSTATION`; position: last in the pipeline, after `DellWorkstationRule` — was simulated against all 244 real devices exactly as RULE-006's candidate was simulated before implementation.

**Before → After distribution:**

| Type | Before | After |
|---|---:|---:|
| unknown | 128 | **127** |
| workstation (existing rules) | 27 | 27 |
| workstation (candidate rule) | 0 | **1** |
| access_point | 26 | 26 |
| printer | 23 | 23 |
| server | 12 | 12 |
| switch | 10 | 10 |
| phone | 10 | 10 |
| hypervisor | 3 | 3 |
| camera | 3 | 3 |
| firewall | 2 | 2 |

**Changed-device inventory: exactly 1 device.**

| Device | Hostname | Vendor | `operating_system` | Before | After |
|---|---|---|---|---|---|
| 172.16.101.0 | MIS3030a.wrf.scterm.com | ASUSTek Computer | `Windows 10 Enterprise 19045 (Windows 10 Enterprise 6.3)` | unknown | workstation |

**Regression candidates checked and confirmed clean**: the candidate predicate was also evaluated against every already-classified (non-`UNKNOWN`) device in the dataset. It matches exactly one — `172.16.102.135` (`SCT2053`), already `WORKSTATION` via `DellWorkstationRule` (Section 10) — and zero others. No `SERVER`, `HYPERVISOR`, `PRINTER`, or any other bucket is touched.

## 12. Rejected Approaches

- **Bare `"pro"` as a keyword** — rejected outright, not merely deprioritized. A three-letter substring is exactly the class of collision risk this codebase already has a real, named incident for (`PrinterVendorRule`'s bare `"hp"`, RULE-005). `"pro"` would collide with ordinary English words in HTTP titles, product strings, and hostnames (`"protocol"`, `"product"`, `"process"`, `"provider"`) with no way to bound the risk the way `"professional"` (a whole, specific word) already does. Not used anywhere in the recommended candidate.
- **`"Home"` and bare `"Pro"` edition keywords** — rejected for a different reason: zero occurrences anywhere in the real 244-device dataset. Adding them now would be exactly the "design from imagination" this sprint's own instructions prohibit. If a future scan surfaces a real `"Windows 10 Pro"`/`"Windows 11 Home"` device, that is new evidence justifying a future, separately-scoped keyword addition — not something to pre-guess today.
- **Bare ambiguous build numbers (`10.0.26100`, `6.3.9600`, `10.0.17763`) as workstation evidence** — rejected. These are the exact hard exclusions RULE-006 already established for the server side; the identical ambiguity applies symmetrically to a workstation-side reading. A device on `10.0.26100` is not more likely to be a workstation than a server from the build number alone — 15 of the 36 unknowns sit on this exact build with zero way to disambiguate role from it.
- **`10.0.19041`/`10.0.22631` as unambiguous client-only evidence** — investigated and *not* rejected on evidence grounds (no counter-example was found), but deliberately **not proposed**, because this plan could not independently corroborate their client-exclusivity to the same standard `10.0.20348` was corroborated for RULE-006 (a live, current GA release vs. a claim about historical Semi-Annual-Channel servicing this investigation cannot fully verify from the evidence on hand). Named as an open question (Section 15), not asserted as safe.
- **RDP/SMB port presence, port combinations, NetBIOS service presence, WinRM** — rejected: directly disproven or entirely absent from the dataset (Section 6).
- **Vendor/manufacturer evidence (`Intel Corporate`, `Microsoft`, `ASUSTek`, etc.)** — rejected: directly disproven by real counter-examples already in the dataset (Section 6, `SERVER` and `HYPERVISOR` devices sharing the identical vendor strings).
- **A generic "Windows detected → WORKSTATION" fallback rule** — rejected as out of scope by the sprint's own framing and by this codebase's established philosophy; would immediately misclassify the 12 real `SERVER` devices' close cousins (the 28 ambiguous-build `UNKNOWN` devices) the moment their build number happened to be shared with a client release.

## 13. Architecture Analysis

The one viable candidate is structurally identical in shape to `WindowsServerRule` (PLAN-RULE-006 Section 3.2): a single new rule class, reading exactly one field (`operating_system`), no port/service/vendor/hostname corroboration, no shared helper beyond the already-existing `normalize_operating_system` (already used by four other rules). This is a smaller, simpler rule than `WindowsServerRule` — it has only one branch, not two, since no second unambiguous-build literal is being proposed (Section 12).

Unlike `WindowsServerRule`, this candidate does not need to *preempt* any existing rule's incorrect behavior — it does not correct a bug the way RULE-006's `PrinterVendorRule`/`DellWorkstationRule` fixes did. It is purely additive: it only ever assigns a type to a device that would otherwise be `UNKNOWN`. This materially simplifies its ordering requirements (Section 14) relative to `WindowsServerRule`'s two-directional ordering constraint.

## 14. Ordering Analysis

Recommended position, if implemented: **last** in the pipeline — after `DellWorkstationRule`, immediately before the `UNKNOWN` fallback (position 12 of what would become a 12-rule list).

- **No rule needs to run after it.** By construction, a device this rule would claim is, by definition, one every other rule already declined (it only ever fires from the terminal `UNKNOWN` path in the current pipeline). Placing it anywhere earlier could only ever *narrow* its effect (by letting some other rule claim a device first) or introduce the `DellWorkstationRule` reason-string overlap named in Section 10 — never expand correctness.
- **It does not need to preempt anything.** Contrast with `WindowsServerRule`, which had two *hard* ordering requirements (after `HypervisorHostnameRule`/`ServerHostnameRule`, before `PrinterVendorRule`/`DellWorkstationRule`) because it was correcting existing over-broad matches. This candidate corrects nothing; it only fills a gap in the terminal fallback. Last position is therefore the *safest* possible placement, not merely a workable one.
- **Confirmed zero preemption risk against every rule that matters**: `ServerHostnameRule` (Section 9), `HypervisorHostnameRule` (Section 8), `WindowsServerRule` (Section 7 — the two rules' trigger fields overlap only in `operating_system`, but their keyword sets are disjoint by construction: `"windows server"`/`10.0.20348` vs. `"enterprise"`/`"professional"`, and no device in the dataset carries both), and `DellWorkstationRule` (Section 10).

## 15. Regression Risks

| Risk | Assessment |
|---|---|
| A real Windows Server device gets swept into `WORKSTATION` | None found; directly disproven against all 12 real `SERVER` devices (Section 7). |
| A real Hyper-V host gets swept into `WORKSTATION` | None found; directly disproven against all 3 real `HYPERVISOR` devices (Section 8). |
| A real domain controller gets swept into `WORKSTATION` | None found; directly disproven against both real DC devices (Section 9). |
| `DellWorkstationRule`'s existing behavior changes | None — placing the new rule last means `DellWorkstationRule`'s one overlapping device (`SCT2053`) is claimed exactly as it is today, before the new rule is ever evaluated (Section 10, Section 14). |
| The Samba-spoofed device (`172.16.102.112`) or the Datto/Samba appliance (`172.16.100.82`) gets swept in | Not possible — neither carries `"enterprise"` or `"professional"` anywhere in `operating_system` (one shows `"Windows 6.1 (Samba...)"`, the other has no `operating_system` at all); the candidate reads only that one field. |
| Future collision from a not-yet-observed edition string | Deliberately not guarded against by speculative keywords (Section 12) — the same "wait for real evidence" discipline this codebase already applies. If it happens, it is a future, separately-scoped investigation, not a defect in this one. |

## 16. Implementation Scope (If Approved)

**One new file**: `networkmapper/classification/rules/windows_workstation_rule.py` — a single rule class, one branch, reading only `device.operating_system`, keyword set `("enterprise", "professional")`, producing `DeviceType.WORKSTATION`.

**One line in `device_classifier.py`**: import + append at the end of `self._rules` (after `DellWorkstationRule()`), plus a docstring paragraph explaining why last position requires no ordering justification beyond "it corrects nothing and needs to preempt nothing" (contrast directly with `WindowsServerRule`'s two-directional constraint, Section 13/14).

**Tests**: a new `tests/test_windows_workstation_rule.py` (explicit caption match for both real observed shapes — `"Windows 10 Enterprise..."` and, for completeness, `"...Professional..."`; case-insensitivity; bare ambiguous builds `6.3.9600`/`10.0.26100`/`10.0.17763`/`10.0.19041`/`10.0.22631` do not match; Samba-spoofed OS does not match; `None`/empty OS does not match; a `product`-field-only occurrence of an edition keyword does not match, proving the rule never reads `product`) plus a `test_classifier.py` integration test reproducing `MIS3030a`'s exact real evidence end-to-end, a regression test reproducing `SCT2053`'s exact evidence confirming `DellWorkstationRule` still wins (rule-identity check via `get_last_rule_results()`, mirroring RULE-006's own verification pattern), and the `devtools/validate.py` `STANDARD_REGRESSION_TESTS` addition RULE-006 already established the precedent for.

**Confirmed unaffected**: `DeviceType` enum (no new value needed), `evidence_helpers.py` (reuses `normalize_operating_system`), `ServerHostnameRule`, `HypervisorHostnameRule`, `WindowsServerRule`, `PrinterVendorRule`, `DellWorkstationRule` (no code changes to any of them), discovery, enrichment, exporters, serialization, CLI, reporting.

## 17. Acceptance Criteria (If Approved)

1. The new rule returns `WORKSTATION` when `operating_system` contains `"enterprise"` or `"professional"` (case-insensitive), and not-matched otherwise.
2. The new rule never reads any field other than `operating_system`.
3. The new rule is registered last in `DeviceClassifier`'s rule list.
4. `DellWorkstationRule`'s source code is unmodified.
5. Exactly one real production device (`172.16.101.0`) changes classification, `UNKNOWN → WORKSTATION`; exactly zero other devices in the 244-device dataset change.
6. No new `DeviceType` value is introduced.
7. No new shared helper is added to `evidence_helpers.py`.
8. `pytest tests/ -q` and `python -m devtools validate --all` both pass with zero regressions once implemented.

## 18. Explicit Non-Goals

- Detecting "Windows" in general — only an explicit client-edition caption, nothing broader.
- Resolving the 28 ambiguous-build `UNKNOWN` devices, or the 4 insufficient-evidence `UNKNOWN` devices — no reliable discriminator exists for them (Sections 4-6); they remain `UNKNOWN`, correctly.
- Adding `"pro"` or `"home"` keywords — no real evidence supports either (Section 12).
- Treating `10.0.19041`/`10.0.22631` as safe unambiguous-client builds — not corroborated to the standard this plan requires (Section 5, Section 15 — carried forward as an open question, not decided here).
- Any change to `ServerHostnameRule`, `HypervisorHostnameRule`, `WindowsServerRule`, `PrinterVendorRule`, or `DellWorkstationRule`.
- Any taxonomy change, new `DeviceType` value, discovery change, or enrichment change.
- Investigating or fixing the `VM-3030-WIN7` duplicate-hostname anomaly (Section 4) — a real-environment data-quality artifact, not a classification defect.

## 19. Open Questions

- **Is a 1-device yield worth a permanently-maintained new rule?** This plan can answer the *reliability* question cleanly (Section 7-11: zero false-positive risk found anywhere in the real dataset), but the *value* question — whether one corrected device across 244 clears the bar for a new rule file, a new test file, and a permanent slot in `DeviceClassifier`'s ordering — is a judgment call this plan does not resolve. This codebase does have a precedent for shipping a rule justified by a single corroborated case (`NetworkApplianceRule`, RULE-003, one BENCH-002 device), which argues for approval; RULE-006's own bar (10 devices) was substantially larger, which argues for caution. Recommend explicit architect sign-off either way rather than defaulting silently in either direction.
- **`10.0.19041`/`10.0.22631` as a second, build-based branch** (mirroring `WindowsServerRule`'s two-branch design) — deliberately left undecided (Section 5, Section 12). Would need independent corroboration of Microsoft's Semi-Annual-Channel servicing history beyond what this investigation could establish from the dataset alone before being proposed as evidence, not merely plausibility.
- **The `VM-3030-WIN7` duplicate-hostname/mismatched-certificate anomaly** (Section 4) — flagged for whoever owns data quality on the discovery/scan side; not a classification concern.
- **Whether a future scan revealing `"Windows 10 Pro"`/`"Windows 11 Home"` should extend this rule's keyword list or require its own fresh investigation** — this plan takes no position; per Section 12, that is new evidence for a future sprint, not a decision to pre-make now.

## 20. ADR-Trigger Check

Walking ARCH-025-style/RULE-006-precedent reasoning against this candidate: no new view-model, no persistence change, no resolver change, one new rule class reading one already-consumed field via an already-existing helper, one additive line in `DeviceClassifier`'s list requiring no reordering of any existing rule. No ADR is required if this is implemented, for the same reasons PLAN-RULE-006 Section 9 already established for the identically-shaped `WindowsServerRule`.

---

## Summary Recommendation

**A reliable, evidence-backed Windows workstation discriminator exists, but its real-world yield in this dataset is exactly one device.** Every broader candidate the sprint asked about — SMB banners, NetBIOS naming, WinRM, RDP, service combinations, manufacturer evidence, bare ambiguous build numbers — was investigated directly against the real 244-device dataset and rejected on hard evidence, not assumption (Sections 6, 12). The one candidate that survives scrutiny (explicit `"Enterprise"`/`"Professional"` edition caption in `operating_system`) produces zero false positives against every real `SERVER`, `HYPERVISOR`, and domain-controller device in the dataset, and overlaps harmlessly with exactly one already-correct `DellWorkstationRule` match.

This plan recommends implementing the narrow rule described in Sections 13-17, **conditioned on explicit architect agreement that a 1-device yield is worth the addition** (Section 19) — this is the one place this plan defers a decision, because it is a value judgment, not an evidence question. If the architect judges the yield too small, the correct outcome per this sprint's own instructions is to implement nothing and leave all 36 devices honestly `UNKNOWN` — that is not a fallback position but a legitimate, fully-supported conclusion this investigation is equally prepared to stand behind.

---

## 21. Plan Amendment — Windows Home Client-Edition Evidence

**Status: approved, appended after implementation.** This section is an addendum, not a revision — the investigation and findings in Sections 1-20 above are preserved exactly as originally written and remain an accurate record of what was found at the time (zero Home-edition evidence existed in scope at that point because the original sprint never searched for it; it was not omitted or overlooked). This section documents a separate, later, explicitly-scoped follow-up investigation raised by architect review after RULE-007's Enterprise/Professional-only implementation had already shipped.

### 21.1 Trigger

Architect review raised a real-world MSP requirement: customer fleets managed by this tool will, in general, include consumer Windows editions (Windows 10/11 Home) that this dataset's one captured customer environment does not happen to contain. This is a prospective coverage question, not a report of a missed device in the data already investigated.

### 21.2 Evidence Search (New, Scoped Specifically to This Question)

The real production dataset (`output/Test Network.nmproj`, 244 devices) was searched for `operating_system` values containing `"home"` (case-insensitive): **zero matches**. A broader sweep of every evidence field (not just `operating_system`) found exactly one incidental occurrence of the substring "home" anywhere in the entire dataset — an HTTP title's URL path (`.../dattolocal.net/home`) on a Datto backup appliance, a field this rule has never read and does not read now. The three curated benchmark fixtures (`enterprise`, `homelab`, `small_office`) and the existing test suite were also searched; no `operating_system`-shaped Home-edition value existed anywhere prior to this amendment.

**No Home-edition device was observed in the current 244-device production dataset, or in any other evidence this project has captured.** This addition is made prospectively, on the strength of MSP fleet reality generally, not in response to a production defect this dataset demonstrates.

### 21.3 Why Bare `"home"` Is Rejected

Unlike `"enterprise"` and `"professional"` — which have zero overlap with any Windows Server edition name in Microsoft's product history — `"home"` has exactly one historical exception: **Windows Home Server**, a real, shipped Microsoft product (2007-2013, a consumer NAS/backup OS, since discontinued). A bare `"home"` substring check would match a `"Windows Home Server..."` caption exactly as readily as a genuine `"Windows 10 Home..."` caption, misclassifying the former as `WORKSTATION`. Bare `"windows home"` is equally unsafe for the identical reason (`"windows home server"` contains `"windows home"` as a substring). Neither is approved.

### 21.4 Approved Predicate

Two new, version-qualified keyword strings are added to `WINDOWS_CLIENT_EDITION_KEYWORDS`, checked exactly the same way as the existing two (case-insensitive substring against `operating_system` alone):

```
"windows 10 home"
"windows 11 home"
```

These are disjoint from `"windows home server"` by construction — the word order does not overlap (`"10 home"`/`"11 home"` vs. `"home server"`) — while still matching realistic OEM/regional Home variants (e.g., `"Windows 10 Home Single Language 19045"` contains `"windows 10 home"` as a substring). No other Home-related string is added.

### 21.5 Production Impact

**Zero.** No device in the 244-device production dataset, nor in any curated benchmark fixture, carries `"windows 10 home"` or `"windows 11 home"` (or any Home-edition text at all) in `operating_system`. This amendment changes no classification outcome in the current replay; it is purely preventive scope for future customer fleets. The sprint's only production-visible effect remains the one device already resolved by the original Enterprise/Professional predicate: `172.16.101.0` (`MIS3030a`), `UNKNOWN → WORKSTATION`.

### 21.6 Changes Made Under This Amendment

- `networkmapper/classification/rules/windows_workstation_rule.py`: `WINDOWS_CLIENT_EDITION_KEYWORDS` extended from `("enterprise", "professional")` to `("enterprise", "professional", "windows 10 home", "windows 11 home")`. No structural change to the rule's logic, evidence source, or ordering.
- `tests/test_windows_workstation_rule.py`: new positive-match tests for `"Windows 10 Home"`, `"Windows 10 Home Single Language"`, and `"Windows 11 Home"` captions; a case-insensitivity check for the new keywords; a negative test proving `"Windows Home Server 2011"` does not match (direct proof of Section 21.3's reasoning); a negative test proving a bare, non-version-qualified `"Home"` caption does not match (locking in the precision decision). The pre-existing `test_home_does_not_match` case asserted `"Windows 10 Home 19045"` does *not* match — an assertion this amendment necessarily inverts, since that exact caption is now a true positive — so it was replaced (not retained) by `test_windows_10_home_caption_matches` (the inverted positive case) and `test_bare_home_without_version_qualifier_does_not_match` (a new, differently-scoped negative case using a non-version-qualified fixture, preserving the *intent* of the original test — "an unqualified Home reference should not match" — without asserting something now false).
- `tests/test_classifier.py`: one new minimal full-pipeline regression test for an explicit Windows 10/11 Home caption, confirming `WindowsWorkstationRule` still wins last, with no change to any other rule's ordering.
- No change to `DeviceClassifier`'s rule *ordering* — `WindowsWorkstationRule` remains last, after `DellWorkstationRule`, exactly as Section 14 established. No change to any other rule file.
