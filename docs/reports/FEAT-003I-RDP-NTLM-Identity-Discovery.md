# Status

Investigation Complete

Implementation: Completed

Production Code Modified: Yes

ADR Required: No — this sprint adds a second producer for three already-
existing `Device` fields (`operating_system`, `computer_name`, `domain`,
all added in FEAT-003H); no new field, evidence category, or model.

Recommended Next Sprint:
Tier 4 of ARCH-003's roadmap (SNMP `sysDescr`/`sysObjectID`) is next in
sequence, but is blocked on confirming and fixing the `-sU` UDP scanning
gap first — not yet actionable as its own clean sprint. See
`ROADMAP.md`.

---

## Summary

Implements ARCH-003 Tier 3: RDP NTLM identity discovery via
`rdp-ntlm-info`. Unlike FEAT-003H's `smb-os-discovery`/`smb-security-mode`
(Nmap "hostrule" scripts reporting once per host), `rdp-ntlm-info` is a
"portrule" script scoped to port 3389 — its output lives in the normal
per-port script dict, the same place `http-title`/`ssl-cert` live, not
`host_data["hostscript"]`. It discloses target identity information
during an incomplete CredSSP/NTLM negotiation; no credentials are used
and no authentication succeeds, consistent with this sprint's "do not
introduce authenticated discovery" constraint and the same operational
profile as `http-auth` (FEAT-003G).

Per this sprint's explicit instruction to reuse existing fields rather
than duplicate evidence, `rdp-ntlm-info`'s `NetBIOS_Computer_Name`,
`NetBIOS_Domain_Name`, and `Product_Version` map onto the exact same
`Device.computer_name`, `Device.domain`, and `Device.operating_system`
fields FEAT-003H already introduced. **No new `Device` or `ServiceEvidence`
field was added.** `Target_Name`, `DNS_Domain_Name`, `DNS_Computer_Name`,
`DNS_Tree_Name`, and `System_Time` were deliberately not captured:
the DNS-qualified variants are redundant with the NetBIOS ones for
identity purposes (and using them would produce longer, FQDN-style
values inconsistent with SMB's shorter NetBIOS-style values for the same
field), and `System_Time` has no identified consumer — the same
"no stated purpose" reasoning ARCH-003 and FEAT-003H already applied to
`smb2-time`'s equivalent field.

**Precedence between SMB and RDP evidence** — the question FEAT-003H's
Known Issues flagged as this sprint's responsibility — is resolved as:
**SMB wins, decided per field, not per source.** A host whose SMB output
only yields one of the three fields (e.g. a Samba server that blanks its
own computer name) still takes the remaining fields from RDP rather than
leaving them empty; see `test_standard_enrichment_falls_back_to_rdp_field_by_field_when_smb_partial`.
SMB is preferred wherever both sources produce a value because
`smb-os-discovery` reports a full OS caption (e.g. `"Windows Server 2019
Standard 17763"`) while `rdp-ntlm-info`'s `Product_Version` is a bare
build number (e.g. `"10.0.14393"`) with no edition or vendor text —
strictly less informative both for a human reading the report and for
`ServerHostnameRule`/`HypervisorHostnameRule`'s keyword-based OS
corroboration, which a bare build number will never match. This
"prefer the more descriptive/specific source" reasoning is the same
kind of routine implementation decision FEAT-003F used for
`vmware-version` vs. `-sV`'s own guess.

**Classification required zero code changes.** `ServerHostnameRule` and
`HypervisorHostnameRule` already corroborate on `Device.operating_system`
generically (added in FEAT-003H) — they have no way to know, and no
need to know, whether that value came from SMB or RDP. This is the
architecture working as intended: reusing an existing Device-level field
means a new discovery producer benefits every existing consumer for
free. The one behavioral nuance worth flagging (not a bug): a device
identified *only* via RDP (SMB absent) gets a bare build number in
`operating_system`, which — unlike SMB's full caption — will not
contain the word "server" and therefore will not trigger
`ServerHostnameRule`'s OS corroboration text, even though the hostname
match alone still classifies it correctly. Documented as a regression
test (`test_rdp_sourced_build_number_does_not_corroborate_server_match`)
rather than left as a silent surprise.

ARCH-003's original `rdp-ntlm-info` description (Section 2.2) was
checked against the script's actual documented output during this
sprint, the same verification step that caught FEAT-003H's `smb2-time`
error. This time, no factual error was found — ARCH-003's field list
(NetBIOS computer/domain name, DNS computer/domain name, OS build
number) matches the script's real output exactly. **ARCH-003 required
no correction this sprint.**

## Files Changed

**Discovery**
- `networkmapper/discovery/nmap_provider.py` — added `"rdp-ntlm-info"`
  to `STANDARD_ENRICHMENT_SCRIPTS` (port 3389 already in
  `CLASSIFICATION_PORTS`, no new scan target). Added
  `_extract_rdp_identity()`, reusing `_extract_labeled_field()`
  (FEAT-003F/H) against the per-port script dict rather than
  `hostscript`. Updated the SMB-identity merge step in
  `_discover_with_standard_enrichment()` to also compute RDP identity
  and merge with SMB-wins, per-field precedence (see Summary).

**Classification**
- No changes. `networkmapper/classification/rules/server_hostname_rule.py`
  and `hypervisor_hostname_rule.py` already consume
  `Device.operating_system` (FEAT-003H) and needed no modification to
  benefit from the new RDP producer.

**Persistence, benchmark loading, developer tooling**
- No changes. `networkmapper/project/serializer.py`,
  `networkmapper/developer/benchmark_runner.py`, and
  `networkmapper/developer/classification_workbench.py` already
  serialize, load, and display `operating_system`/`computer_name`/
  `domain` (FEAT-003H) — this sprint reuses those fields exactly, so
  the data flows through unchanged. Verified, not assumed: the new
  benchmark fixture below round-trips correctly with no code changes.

**Benchmarks**
- `benchmarks/enterprise/inventory.json` /
  `benchmarks/enterprise/expected_results.json` — added a new device
  (`srv-file02`, port 3389 only, no port 445) with RDP-shaped identity
  evidence (`operating_system: "10.0.14393"`), demonstrating the
  "SMB firewalled, RDP open" scenario ARCH-003 identified as RDP's
  value proposition. Classifies correctly via hostname match alone
  (`"srv"` keyword) — accuracy unchanged at 100%, now 9 devices.
- `benchmarks/homelab/`, `benchmarks/small_office/` — not modified.

**Documentation**
- `docs/architecture/overview.md`, `docs/architecture/classification.md`
  — updated to document that operating system/computer name/domain now
  have two independent unauthenticated producers (SMB, RDP) with SMB
  preferred, per this sprint's explicit documentation requirement.
- `docs/reports/ARCH-003-Nmap-Capability-Assessment.md` — not modified;
  no factual error found (see Summary).
- `ROADMAP.md` — Current Priority note updated: FEAT-003I marked
  complete; Tier 4 (SNMP) identified as next but blocked on the `-sU`
  gap.

**Tests**
- `tests/test_nmap_provider_scan_profile.py` — four new tests (RDP-only
  identity, SMB-wins precedence when both present, field-by-field
  fallback when SMB is partial, plus the updated `--script` argument
  string across five existing tests).
- `tests/test_server_hostname_rule.py` — one new test documenting that
  an RDP-sourced bare build number does not corroborate a server match
  (see Summary).
- `tests/test_devtools_validate.py` — fast-path test count pin updated
  108 → 109 (one new test added to `test_server_hostname_rule`, already
  in `STANDARD_REGRESSION_TESTS`).

**Not changed**
- No new `Device`/`ServiceEvidence` fields, no new `DiscoveryProvider`,
  no authenticated discovery, no WinRM/Active Directory/LDAP/SNMP/SSH
  work — all explicitly out of scope and untouched.

## Validation Performed

`python -m devtools validate --all`:

- Unit tests: 197 run, 0 failures, 1 error.
- The 1 error is the same pre-existing, previously-flagged
  `tests.test_csv_exporter.CsvExporterTest.test_export_writes_expected_csv_rows`
  (`AttributeError: 'str' object has no attribute 'name'`) — unrelated
  to this sprint's changes.
- Benchmarks: enterprise (now 9 devices), homelab, small_office all
  100.0% accuracy.

## Known Issues

- The pre-existing `test_csv_exporter` failure remains unresolved and
  out of scope, consistent with every prior sprint's handling of it.
- RDP-only `operating_system` values are bare build numbers (e.g.
  `"10.0.14393"`) rather than friendly OS captions, and cannot reliably
  distinguish a Server SKU from a Client SKU on their own (modern
  Windows client and server editions frequently share the same kernel
  build number) — this was evaluated and deliberately not addressed by
  inventing a build-number-to-edition lookup table, which would be
  exactly the kind of unsupported/speculative fingerprint this
  project's evidence standard rejects. `ServerHostnameRule`'s
  corroboration simply won't fire for RDP-only devices; hostname-based
  matching still works normally.
- Neither `Device.smb_signing` (FEAT-003H) nor any RDP-specific
  evidence field exists for RDP's own connection security posture (e.g.
  NLA enforcement) — out of this sprint's scope (ARCH-003 did not
  identify an equivalent RDP script), not evaluated here.

## Next Recommended Sprint

Per ARCH-003's roadmap, Tier 4 (SNMP `sysDescr`/`sysObjectID`) is next,
but is blocked on confirming and fixing the `-sU` UDP scanning gap
first — recommend that prerequisite be investigated before scoping a
SNMP implementation sprint.
