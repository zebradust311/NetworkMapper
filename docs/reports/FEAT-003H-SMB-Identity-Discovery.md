# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — `computer_name`, `domain`, and `smb_signing` are new
incremental named fields on `Device`, the same pattern ADR-009
established for `ServiceEvidence` and FEAT-003E/F/G already used for
`Device`-level identity facts. No new evidence category or model is
introduced.

Recommended Next Sprint:
FEAT-003I — RDP NTLM Info (ARCH-003 Tier 3). See `ROADMAP.md` for the
FEAT-003G/FEAT-003H/FEAT-003I sprint-numbering history.

---

## Summary

Implements ARCH-003 Tier 2: SMB identity discovery via `smb-os-discovery`
and `smb-security-mode`. Both are Nmap "hostrule" NSE scripts — they
negotiate against the SMB port already in `CLASSIFICATION_PORTS` (445)
but report their findings once per host (Nmap's "Host script results",
surfaced by python-nmap as `host_data["hostscript"]`), not once per port,
because the facts they reveal (OS, computer name, domain, signing
posture) describe the host itself rather than any specific service. Per
ADR-009 and this sprint's explicit steer ("prefer device-level evidence
for information describing the host"), all four resulting fields —
`Device.operating_system` (previously dormant since FEAT-003A; this is
its first producer), `Device.computer_name`, `Device.domain`, and
`Device.smb_signing` — were added at the `Device` level, not
`ServiceEvidence`.

`smb-security-mode`'s `message_signing` field is collected and exposed
as evidence (per ARCH-003's recommendation) but deliberately **not**
consumed by classification — ARCH-003 assessed it as a security-posture
indicator with no reliable device-type signal, and this sprint's own
instructions direct consuming SMB identity "only where it meaningfully
improves existing classification."

`smb2-time` — the third script this sprint's objective asked to
"evaluate" — was investigated and **not implemented**. ARCH-003's FEAT-003G
addendum had described it as reporting a negotiated SMB2/SMB3 dialect.
That description was independently verified against the script's actual
documented behavior during this sprint and found to be incorrect: the
script reports exactly two fields, `date` and `start_date` (current time
and server boot time), neither of which is device identity evidence. This
is a factual correction to ARCH-003, made under this sprint's explicit
"factual corrections discovered during implementation" allowance — see
ARCH-003 Section 2.1 and `ROADMAP.md` for the corrected record.

**Classification changes** (`ServerHostnameRule`, `HypervisorHostnameRule`)
went through one design iteration during implementation. The first
version treated "`operating_system` contains 'server'" as an
**independent** match trigger for `ServerHostnameRule` (the same tier
strength FEAT-003D/G gave self-identifying product/title/TLS/auth-realm
evidence). Running the full benchmark suite immediately surfaced why
that was wrong here: `ServerHostnameRule` runs *first* in
`DeviceClassifier`'s ordering, and the `enterprise` dataset's Hyper-V
host (`hyperv-node-01`) — which legitimately runs Windows Server, being
a Hyper-V host — was misclassified as `SERVER` before
`HypervisorHostnameRule` ever got evaluated. Unlike a self-served HTTP
title or TLS certificate naming a specific vendor, "runs Windows Server"
is not device-type-specific: plain member servers, Hyper-V hosts, and
domain-controller-as-hypervisor boxes all say the same thing. The fix
was to make the OS check **corroboration-only** for `ServerHostnameRule`
(it can only strengthen an already-matching hostname signal, never
independently trigger), matching the pattern `HypervisorHostnameRule`
already used for `HYPERVISOR_PRODUCT_KEYWORDS`. `HypervisorHostnameRule`
itself gained a parallel, always-safe corroboration check: a
`hyperv`/`vmhost`-style hostname match is now corroborated with
`"windows server"` in `operating_system` when present, since Hyper-V is
a Windows Server role.

No dedicated `DeviceType.DOMAIN_CONTROLLER` was added. `smb-os-discovery`'s
unauthenticated output cannot reliably distinguish a domain controller
from an ordinary member server, and `ServerHostnameRule`'s existing `"dc"`
hostname-substring branch already targets DC naming conventions —
OS-evidence corroboration now backs that branch up, which is the
extent of "Domain Controller" improvement this evidence supports
without inventing an unsupported signal.

## Files Changed

**Model**
- `networkmapper/core/models.py` — added `Device.computer_name`,
  `Device.domain`, `Device.smb_signing` (`Device.operating_system`
  already existed; this sprint gives it its first producer).

**Discovery**
- `networkmapper/discovery/nmap_provider.py` — added
  `STANDARD_HOST_ENRICHMENT_SCRIPTS = ["smb-os-discovery", "smb-security-mode"]`,
  appended to the same `--script` argument as the existing port scripts
  (no new scan target — port 445 is already scanned). Added
  `_host_script_output()` (reads `host_data["hostscript"]`, distinct
  from the per-port `script` dict), `_extract_smb_identity()`, and
  renamed `_extract_cert_field()` → `_extract_labeled_field()` (now
  generic, reused for both ssl-cert's Subject/Issuer and
  smb-os-discovery/smb-security-mode's `Label: value` lines).

**Classification**
- `networkmapper/classification/evidence_helpers.py` — added
  `normalize_operating_system()`.
- `networkmapper/classification/rules/server_hostname_rule.py` — added
  `SERVER_OPERATING_SYSTEM_KEYWORDS`; OS evidence corroborates an
  already-matching hostname reason, never triggers independently (see
  Summary for why).
- `networkmapper/classification/rules/hypervisor_hostname_rule.py` —
  added `HYPERVISOR_OPERATING_SYSTEM_KEYWORDS`; same corroboration-only
  pattern.
- `networkmapper/classification/rules/cisco_switch_rule.py`,
  `dell_workstation_rule.py`, `printer_vendor_rule.py`,
  `sonicwall_firewall_rule.py`, `ubiquiti_access_point_rule.py`,
  `voice_vendor_rule.py` — not modified; SMB identity evidence doesn't
  meaningfully improve any of these device types.

**Persistence**
- `networkmapper/project/serializer.py` — `computer_name`, `domain`,
  `smb_signing` added to both save and load paths.
- `networkmapper/developer/benchmark_runner.py` — `load_inventory()`
  reads the three new fields.

**Developer tooling**
- `networkmapper/developer/classification_workbench.py` — device
  section now renders `Computer Name:`, `Domain:`, and `SMB Signing:`
  alongside the existing `Operating System:` line.

**Benchmarks**
- `benchmarks/enterprise/inventory.json` /
  `benchmarks/enterprise/expected_results.json` — enriched
  `hyperv-node-01` with OS/computer-name/domain evidence to exercise
  `HypervisorHostnameRule`'s new corroboration path; added a new device
  (`app-server-02`, hostname already matches `SERVER_HOSTNAME_KEYWORDS`)
  with full SMB identity evidence to exercise `ServerHostnameRule`'s
  corroboration path. Both remain correctly classified — accuracy
  unchanged at 100%, now with richer, verified reason text.
- `benchmarks/homelab/`, `benchmarks/small_office/` — not modified; no
  existing device there needed new evidence to demonstrate the change.

**Documentation**
- `docs/architecture/overview.md`, `docs/architecture/classification.md`
  — evidence field lists updated to mention device-level identity
  evidence (OS, computer name, domain/workgroup, SMB signing).
- `docs/reports/ARCH-003-Nmap-Capability-Assessment.md` — factual
  correction to the `smb2-time` assessment (see Summary); "FEAT-003G"
  references describing the SMB sprint corrected to "FEAT-003H"
  throughout, and the RDP sprint's tentative label corrected from
  "FEAT-003H" to "FEAT-003I", per the FEAT-003G naming history in
  `ROADMAP.md`.
- `ROADMAP.md` — Current Priority note updated: FEAT-003H marked
  complete, FEAT-003I (RDP NTLM Info) identified as next.

**Tests**
- `tests/test_nmap_provider_scan_profile.py` — four new tests (domain-joined
  host, workgroup fallback, no-host-scripts case, plus the updated
  `--script` argument string across five existing tests).
- `tests/test_server_hostname_rule.py` — two new tests: OS corroboration,
  and (regression coverage for the design fix above) confirming OS
  evidence alone never independently triggers a match.
- `tests/test_hypervisor_hostname_rule.py` — two new tests: OS
  corroboration, and confirming a non-Windows-Server OS leaves the
  reason unaffected.
- `tests/test_project_serializer.py`, `tests/test_benchmark_runner.py`,
  `tests/test_classification_workbench.py` — one new test each for the
  three new `Device` fields.
- `tests/test_devtools_validate.py` — fast-path test count pin updated
  104 → 108 (four new tests added to `test_server_hostname_rule` and
  `test_hypervisor_hostname_rule`, both already in
  `STANDARD_REGRESSION_TESTS`).

**Not changed**
- No new `DiscoveryProvider`, no authenticated discovery, no RDP/SNMP/SSH/
  WinRM/Active Directory work — all explicitly out of scope and untouched.

## Validation Performed

`python -m devtools validate --all`:

- Unit tests: 193 run, 0 failures, 1 error.
- The 1 error is the same pre-existing, previously-flagged
  `tests.test_csv_exporter.CsvExporterTest.test_export_writes_expected_csv_rows`
  (`AttributeError: 'str' object has no attribute 'name'`) — unrelated to
  this sprint's changes.
- Benchmarks: enterprise (now 8 devices), homelab, small_office all
  100.0% accuracy.

## Known Issues

- The pre-existing `test_csv_exporter` failure remains unresolved and
  out of scope, consistent with every prior sprint's handling of it.
- `smb-os-discovery`'s "Computer name:"/"Domain name:"/"Workgroup:"
  parsing does not special-case the null-byte-padding artifact
  (`\x00`) Nmap sometimes shows in NetBIOS name fields (documented in
  ARCH-003's original candidate research). This sprint deliberately
  used the plain "Computer name:" line (not the NetBIOS-suffixed
  variant) to sidestep this in the common case, but a `Workgroup:`
  value could still carry the artifact verbatim as opaque text — safe
  (no crash, no incorrect data), just not cosmetically cleaned.
- `Device.smb_signing` is collected but has no consumer anywhere in the
  codebase yet (by design — see Summary). This is the same
  "producer without consumer" pattern flagged for `ServiceEvidence.version`
  in FEAT-003F/ARCH-003, now with a second, deliberate instance; its
  intended future consumer is a security/compliance report, not
  classification.
- The SMB/RDP field-precedence question ARCH-003 raised (Section 2.2:
  both `smb-os-discovery` and a future `rdp-ntlm-info` can populate
  `operating_system`/`computer_name`/`domain`) is now live —
  `operating_system` has its first real producer. FEAT-003I should
  decide this as a routine implementation choice when it lands, the
  same way FEAT-003F decided `vmware-version` vs. `-sV` precedence.

## Next Recommended Sprint

FEAT-003I — RDP NTLM Info (ARCH-003 Tier 3), including the SMB/RDP
`operating_system` precedence decision noted above.
