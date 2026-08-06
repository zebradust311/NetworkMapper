# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

ADR Required: No

Recommended Next Sprint:
DISC-002 - Discovery Evidence Observability and Run Diagnostics

---

## Summary

This investigation audited whether NetworkMapper's current STANDARD discovery
profile can actually collect all enrichment evidence the current architecture
and evidence model support.

Conclusion: every implemented enrichment field in scope is reachable from a
STANDARD scan, but only conditionally. The most likely causes of widespread
"No additional evidence collected." output are operational and environmental,
not parser/storage defects:

1. The application CLI defaults to FAST, not STANDARD. FAST collects host
   identity only and no enrichment evidence.
2. DEEP is currently equivalent to FAST.
3. STANDARD enrichment is constrained to a curated 16-port set and only open
   ports.
4. Several fields require target-side behavior (for example, an auth challenge
   that includes a realm, SMB/RDP reachability, TLS cert exposure).

The evidence pipeline itself is complete for implemented fields:

- Collection is requested in STANDARD arguments.
- Parsing exists in `NmapProvider`.
- Storage exists in `Device`/`ServiceEvidence`.
- Persistence exists in `ProjectSerializer`.

No code or configuration changes were made in this sprint.

---

## Investigation

### Scope Reviewed

This audit traced each requested field through:

1. STANDARD scan configuration and arguments.
2. Nmap feature/script prerequisites.
3. Parsing in discovery provider code.
4. In-memory storage model fields.
5. Persistence serialization/deserialization.
6. Conditions that can block collection.

### Primary Sources

- [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py)
- [networkmapper/core/models.py](../../networkmapper/core/models.py)
- [networkmapper/project/serializer.py](../../networkmapper/project/serializer.py)
- [networkmapper/application.py](../../networkmapper/application.py)
- [networkmapper/discovery/scan_profile.py](../../networkmapper/discovery/scan_profile.py)
- [tests/test_nmap_provider_scan_profile.py](../../tests/test_nmap_provider_scan_profile.py)
- [networkmapper/exporters/markdown_exporter.py](../../networkmapper/exporters/markdown_exporter.py)
- [docs/ADR.md](../ADR.md)

---

## Evidence Collection Matrix

| Evidence Field | Profile(s) That Should Collect It | Nmap Feature / Prerequisite | Parser Extraction Location | Stored On | Conditions That Prevent Collection |
|---|---|---|---|---|---|
| HTTP title | STANDARD | `-sV` + `http-title` NSE on scanned HTTP/HTTPS ports | `_extract_services()` reads `scripts["http-title"]` and normalizes via `_clean_script_output()` in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | `ServiceEvidence.http_title` in [networkmapper/core/models.py](../../networkmapper/core/models.py) | Host not discovered in phase 1; port not in curated set; port not open; script yields no title |
| HTTP authentication realm | STANDARD | `-sV` + `http-auth` NSE; service must issue `401` challenge containing `realm=` | `_extract_http_auth_realm()` used by `_extract_services()` in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | `ServiceEvidence.http_auth_realm` | No auth challenge; challenge lacks `realm=`; port not reachable/open/scanned |
| TLS subject | STANDARD | `-sV` + `ssl-cert` NSE on TLS endpoint | `_extract_labeled_field(..., "Subject")` from `scripts["ssl-cert"]` in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | `ServiceEvidence.tls_subject` | No cert presented; missing label; port not reachable/open/scanned |
| TLS issuer | STANDARD | `-sV` + `ssl-cert` NSE on TLS endpoint | `_extract_labeled_field(..., "Issuer")` from `scripts["ssl-cert"]` in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | `ServiceEvidence.tls_issuer` | No cert presented; missing label; port not reachable/open/scanned |
| SMB computer name | STANDARD | `smb-os-discovery` host script (SMB on 445 reachable) | `_extract_smb_identity()` via hostscript output in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | `Device.computer_name` | SMB blocked/filtered; script missing; output missing `Computer name:` |
| SMB domain | STANDARD | `smb-os-discovery` host script | `_extract_smb_identity()` reads `Domain name:` or `Workgroup:` in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | `Device.domain` | SMB blocked/filtered; no `Domain name:`/`Workgroup:` fields |
| SMB signing | STANDARD | `smb-security-mode` host script | `_extract_smb_identity()` reads `message_signing:` in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | `Device.smb_signing` | Script absent; field absent; SMB not reachable |
| Operating system | STANDARD | SMB OS caption (`smb-os-discovery`) preferred; RDP fallback (`rdp-ntlm-info` Product_Version) | Merge logic in `_discover_with_standard_enrichment()` using `_extract_smb_identity()` and `_extract_rdp_identity()` in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | `Device.operating_system` | Neither SMB nor RDP evidence available; labels missing; no `-O` OS fingerprint path exists |
| RDP identity | STANDARD | `rdp-ntlm-info` NSE on TCP 3389 | `_extract_rdp_identity()` reads `NetBIOS_*` and `Product_Version` in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | Merged into `Device.operating_system`, `Device.computer_name`, `Device.domain` | 3389 closed/filtered; script absent; labels absent; SMB precedence can supersede overlapping RDP values |
| Service product | STANDARD | `-sV` service detection | `_extract_services()` uses `service_data.get("product")` in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | `ServiceEvidence.product` | Port not open/scanned; weak or absent banner |
| Service version | STANDARD | `-sV` version detection; `vmware-version` script takes precedence when present | `_extract_version()` in [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py) | `ServiceEvidence.version` | Port not open/scanned; no version info; script output unavailable |

Persistence coverage for all listed fields is implemented in both save/load paths
in [networkmapper/project/serializer.py](../../networkmapper/project/serializer.py).

---

## STANDARD Profile Capability Matrix

### Exact STANDARD Behavior

STANDARD is implemented as two-phase discovery (ADR-001):

1. Phase 1 host discovery: `-sn`
2. Phase 2 enrichment on discovered hosts only:
   `-Pn -sV --version-light --script <allowlist> -p <classification ports>`

Implementation source:

- [networkmapper/discovery/nmap_provider.py](../../networkmapper/discovery/nmap_provider.py)
- Verified by tests in [tests/test_nmap_provider_scan_profile.py](../../tests/test_nmap_provider_scan_profile.py)

### Exact Enrichment Arguments

`-Pn -sV --version-light --script http-title,ssl-cert,vmware-version,http-auth,rdp-ntlm-info,smb-os-discovery,smb-security-mode -p 22,53,80,161,443,445,515,631,9100,3389,5060,5061,8080,8443,902,903`

### Enabled NSE Scripts

- `http-title`
- `ssl-cert`
- `vmware-version`
- `http-auth`
- `rdp-ntlm-info`
- `smb-os-discovery`
- `smb-security-mode`

### Disabled / Not Requested NSE Scripts

- Any NSE script not explicitly listed above is not requested in STANDARD.

### Service Detection Settings

- Enabled: `-sV`
- Version intensity: `--version-light`

### Host Discovery Behavior

- Authoritative host set comes from phase 1 (`-sn`).
- Enrichment augments only those hosts discovered in phase 1.
- Enrichment does not create new devices.

### OS Detection Behavior

- No `-O`/OS fingerprint detection flags are used.
- OS data currently comes from SMB/RDP script outputs only.

---

## Implemented vs Reachable Evidence

| Category | Assessment |
|---|---|
| Implemented and reachable from STANDARD | All in-scope fields are implemented and can be collected from STANDARD when target/network prerequisites are met. |
| Implemented but often environment-dependent | SMB and RDP identity fields; HTTP auth realm; TLS subject/issuer. These depend on service exposure and script-returned content. |
| Implemented but profile-gated | All enrichment fields are unavailable in FAST and DEEP today (DEEP currently maps to FAST behavior). |
| Implemented but representation-limited | RDP identity is not retained as a separate evidence object; it is merged into shared `Device` identity fields with SMB precedence. |
| Implemented but scope-limited | Collection is limited to the curated `CLASSIFICATION_PORTS` list and open-port results only. |

---

## Findings

1. The most probable non-network root cause of missing enrichment is profile
   selection drift: CLI default is FAST (`--scan-profile` default `fast`),
   not STANDARD.
2. DEEP is currently non-differentiated and provides no enrichment beyond FAST.
3. STANDARD enrichment is correctly wired for all implemented fields, but
   evidence yield is constrained by:
   - phase-1 host discovery success,
   - curated port scope,
   - open-state filtering,
   - and target-service behavior.
4. No parser or storage gaps were found for the fields in scope.
5. The report phrase "No additional evidence collected." is produced when
   both `device.services` and `device.smb_signing` are empty in exporter
   rendering; this can occur even when other identity fields are present.
6. Current discovery path is unauthenticated by design; there is no credentialed
   scanning path in production discovery code.

---

## Recommendations

1. Operational guardrail first: enforce explicit scan profile selection during
   production runs and avoid relying on CLI default.
2. Add diagnostics in a future sprint (investigation-approved, no discovery
   behavior changes in this sprint):
   - selected profile,
   - exact enrichment argument string,
   - per-host missing-evidence reasons (no open curated ports, scripts absent,
     labels absent, transport blocked).
3. Define DEEP profile architecture and intent before implementation so profile
   naming aligns with real capability.
4. Decide whether additional transport/protocol coverage (for example, UDP)
   belongs in STANDARD or DEEP based on risk/cost.
5. If richer identity is required in hardened networks, scope a separate
   authenticated-discovery profile as its own architecture-reviewed effort.
6. Consider improving report wording in a later sprint so evidence absence is
   more granularly explained to operators.

---

## Risks

- False-negative interpretation risk: users may infer parser defects from empty
  evidence where conditions actually prevented collection.
- Operational inconsistency risk: profile defaults can produce materially
  different evidence outcomes across runs.
- Visibility risk: lack of run-level diagnostics makes collection failures hard
  to attribute without code inspection.

---

## Assumptions

- Production scan behavior matches current code and scan profile usage.
- Nmap script availability aligns with script IDs requested in STANDARD.
- Network conditions in production include typical segmentation and filtering.

---

## ADR Considerations

No new ADR is required for this investigation report.

Potential future ADR trigger points (not part of this sprint):

- Defining a differentiated DEEP profile.
- Introducing authenticated discovery modes.
- Expanding protocol surface beyond current STANDARD scope.

---

## Recommended Implementation Order

If deficiencies are accepted, recommended sequence:

1. DISC-002 - Discovery Evidence Observability and Run Diagnostics
2. ARCH-00X - DEEP Profile Definition and Scope
3. FEAT-00X - Implement DEEP per approved architecture
4. FEAT-00X - Optional protocol-surface expansion (profile-gated)
5. FEAT-00X - Optional authenticated discovery profile (separate controls)
6. REPORT-00X - Operator-facing evidence absence messaging improvements
