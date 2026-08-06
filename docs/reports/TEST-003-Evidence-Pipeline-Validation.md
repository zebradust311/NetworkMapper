# Status

Investigation Complete

Production Code Modified: No

ADR Required: No — every gap identified is a wiring/coverage gap within
ADR-009's existing model, not a model-shape problem. No finding in this
report requires a new evidence category, a new field type, or a change
to how `Device`/`ServiceEvidence` are structured.

Recommended Next Sprint:
No single implementation sprint is recommended as an automatic next
step. See Recommended Implementation Order for a menu of small,
independently-approvable fixes; none are pre-authorized by this report.

---

## Report Naming Correction

This investigation's objective titled it "TEST-002," but that ID is
already in use: commit `233ad6b` ("TEST-002: Add comprehensive
validation mode") already implemented `devtools validate --all` and
`tests/test_devtools_validate.py` — the very tooling this investigation
relies on throughout. No `docs/reports/TEST-002-*.md` file exists (that
sprint predates or fell outside this project's report-per-sprint
convention), but the ID itself is taken. Consistent with how this
project's report series has handled identical situations (ARCH-002 →
ARCH-003; FEAT-003E/F naming), this report is filed as **TEST-003**
instead. This is a naming correction only; it does not change scope or
content.

---

## Summary

This investigation traced all 19 evidence fields NetworkMapper currently
collects (10 `Device`-level, 9 `ServiceEvidence`-level) through every
stage of the pipeline: discovery extraction, storage, serialization,
benchmark loading, developer tooling, product-facing reporting (CSV/
Markdown), and classification. The findings fall into four themes:

1. **A hard split between "classification-era" evidence and "reporting-era" evidence.**
   Every field added since FEAT-003D (`product`, `version`, `http_title`,
   `tls_subject`, `tls_issuer`, `http_auth_realm`, `operating_system`,
   `computer_name`, `domain`, `smb_signing`) reaches the discovery →
   storage → serialization → workbench chain reliably. **None of them
   reach the CSV or Markdown exporters** — the only two report formats
   an actual end user of NetworkMapper receives today. Both exporters
   were last touched before FEAT-003C and have not been extended
   alongside any evidence-model growth since. This is the single
   largest, most consistent gap this audit found.

2. **A systemic benchmark-coverage blind spot for free-text evidence.**
   `product`, `http_title`, `tls_subject`, `tls_issuer`, and
   `http_auth_realm` are all classification-active (read by 3-5 rules
   each) and thoroughly unit-tested, but **zero** benchmark fixture
   across `enterprise`/`homelab`/`small_office` populates any of them.
   These fields' real-world classification behavior has only ever been
   exercised in isolation (one rule, one synthetic `ServiceEvidence`,
   one unit test) — never through the full `NmapProvider → Device →
   DeviceClassifier → BenchmarkReport` path the benchmark suite exists
   to validate.

3. **A validation-architecture reason the CSV exporter bug went unnoticed.**
   `python -m devtools validate` (the fast path, referenced in nearly
   every implementation sprint's own instructions) runs exactly 11
   classification-only test modules (`STANDARD_REGRESSION_TESTS`). It
   never runs `test_csv_exporter`, `test_markdown_exporter`,
   `test_nmap_provider_scan_profile`, `test_project_serializer`,
   `test_benchmark_runner`, `test_classification_workbench`,
   `test_project_summary`, or `test_project_comparator`. Only
   `--all` reaches those, and every sprint that has run `--all` since
   FEAT-003F has correctly logged the `test_csv_exporter` failure as
   "pre-existing, unrelated" and moved on — accurately, but without
   anyone being tasked to fix it. This investigation found the failure
   is actually **two independent bugs**, not one (see Pipeline
   Findings).

4. **A real architectural gap for the multi-provider future.**
   `NetworkGraph.add_device()` silently drops any device whose IP
   address is already present — no merge, no update, no warning. This
   is invisible today because `NmapProvider` is the only
   `DiscoveryProvider` and it already merges its own two scan passes
   internally before returning `Device` objects. It becomes a real data-
   loss risk the moment a second provider exists (SNMP, LLDP, CDP, ARP,
   mDNS, DNS, NetBIOS enrichment — all listed in ROADMAP.md Phase 6):
   whichever provider's devices are added to the graph *second* for a
   given IP will be silently discarded in full, not merged field-by-
   field the way `NmapProvider`'s own SMB/RDP precedence logic
   (FEAT-003I) does internally.

No code was changed to produce this report. Every finding below is
traced against the current state of the repository as read, not
assumed from prior sprint reports.

---

## Evidence Coverage Matrix

Legend: **Ser** = Serialization (save+load), **WB** = Workbench Display,
**MD** = Markdown Report, **CSV** = CSV Report, **Bench** = Benchmark
Support (loader schema / actually populated in a fixture).

### Device-level fields

| Field | Producer(s) | Ser | WB | MD | CSV | Classification Consumers | Bench (loader / fixtures) | Validation Coverage | Status |
|---|---|---|---|---|---|---|---|---|---|
| `ip_address` | `NmapProvider._build_device` | Y | Y | Y | Y | None (identity, not evidence) | Y / all 3 | Nearly every test file | Fully wired |
| `hostname` | `NmapProvider._extract_hostname` | Y | Y | Y | Y | 7 of 8 rules (all except `PrinterVendorRule`) | Y / all 3 | Nearly every test file | Fully wired |
| `mac_address` | `NmapProvider._extract_mac_address` | Y (code only) | Y | **N** | **N** | None directly; drives `vendor` at discovery time via OUI lookup; sole identity key in `ProjectComparator` | Y (loader) / **not populated in any fixture** | `test_nmap_provider_scan_profile`, `test_classification_workbench`, `test_project_comparator` — **no `test_project_serializer` or `test_benchmark_runner` coverage** | Collected, not report-exposed, round-trip untested |
| `vendor` | `NmapProvider._extract_vendor` (MAC OUI) | Y | Y | Y | Y | 6 of 8 rules | Y / all 3 | Nearly every test file | Fully wired |
| `operating_system` | `NmapProvider._extract_smb_identity` (SMB, preferred) + `_extract_rdp_identity` (RDP, fallback) | Y | Y | **N** | **N** | `ServerHostnameRule`, `HypervisorHostnameRule` (both corroboration-only) | Y / **enterprise only** (3 of 9 devices) | `test_nmap_provider_scan_profile`, `test_server_hostname_rule`, `test_hypervisor_hostname_rule`, `test_project_serializer`, `test_benchmark_runner`, `test_classification_workbench` | Consumed, not report-exposed |
| `computer_name` | Same two producers as `operating_system` | Y | Y | **N** | **N** | **None** | Y / enterprise only | `test_nmap_provider_scan_profile`, `test_project_serializer`, `test_benchmark_runner`, `test_classification_workbench` | Collected, no consumer, not report-exposed |
| `domain` | Same two producers as `operating_system` | Y | Y | **N** | **N** | **None** | Y / enterprise only | Same four files as `computer_name` | Collected, no consumer, not report-exposed |
| `smb_signing` | `NmapProvider._extract_smb_identity` only (no RDP equivalent) | Y | Y | **N** | **N** | **None** (explicitly documented in `Device.smb_signing`'s docstring as intentional — "for future security/compliance reporting") | Y / enterprise only (1 device) | Same four files as `computer_name` | Collected for a report that doesn't exist yet |
| `discovery_sources` | `NmapProvider._build_device` — **hardcoded to `["nmap"]`**, not per-field provenance | Y | **N** | Y | Y | None | Y (loader) / **not populated in any fixture** | `test_classification_workbench` (construction only, not asserted on), `test_csv_exporter`, `test_markdown_exporter`, `test_nmap_provider_scan_profile`, `test_project_serializer` | Static constant, not real sourcing data — see Pipeline Findings |
| `device_type` | `DeviceClassifier` (classification **output**, not discovery evidence) | Y | Y | Y (heading only) | Y | N/A — this *is* the classification result | N/A (benchmark `expected_results.json` is the ground truth this field is compared against) | Universal | Not evidence; included here only for completeness |

### ServiceEvidence-level fields (per open port)

| Field | Producer(s) | Ser | WB | MD | CSV | Classification Consumers | Bench (loader / fixtures) | Validation Coverage | Status |
|---|---|---|---|---|---|---|---|---|---|
| `port` | `NmapProvider._extract_services` (`-sV`) | Y | Y | **N** | **N** | 5 of 8 rules via `service_ports()` | Y / enterprise + homelab | Extensive (all rule tests, nmap_provider, benchmark, serializer, workbench) | Fully wired for classification, not report-exposed |
| `protocol` | `NmapProvider._extract_services` (`-sV` result key) | Y | Y | **N** | **N** | **None** (intentional — added in FEAT-003C as diagnostic evidence about the `-sU`/SNMP scanning gap, not device evidence; reconfirmed in ARCH-003) | Y / enterprise + homelab | nmap_provider, benchmark, serializer, workbench | Intentionally not classification input |
| `service` | `NmapProvider._extract_services` (`-sV`) | Y | Y | **N** | **N** | 5 of 8 rules via `service_names()` | Y / enterprise + homelab | Extensive | Fully wired for classification, not report-exposed |
| `product` | `NmapProvider._extract_services` (`-sV`) | Y | Y | **N** | **N** | `CiscoSwitchRule` (`first_matching_product`); `HypervisorHostnameRule`/`SonicWallFirewallRule`/`PrinterVendorRule` (via `first_matching_identifier`) | Y (loader) / **not populated in any fixture** | Unit tests only (`test_classifier`, all 4 consumer rule tests, nmap_provider) — **zero benchmark-corpus exercise** | Classified, never benchmarked |
| `version` | `NmapProvider._extract_version` (prefers `vmware-version` NSE over `-sV` guess) | Y | Y | **N** | **N** | **None** — flagged as dormant in FEAT-003F, ARCH-003, and again here (third time) | Y (loader) / **not populated in any fixture** | nmap_provider, benchmark loader, workbench display only | Collected, no consumer, unresolved (see Classification Gaps) |
| `http_title` | `NmapProvider` (`http-title` NSE, FEAT-003F) | Y | Y | **N** | **N** | `HypervisorHostnameRule`, `SonicWallFirewallRule`, `PrinterVendorRule` (via `first_matching_identifier`) | Y (loader) / **not populated in any fixture** | `test_classifier`, all 3 consumer rule tests, nmap_provider, benchmark, serializer, workbench | Classified, never benchmarked |
| `tls_subject` | `NmapProvider` (`ssl-cert` NSE, FEAT-003F) | Y | Y | **N** | **N** | Same 3 rules as `http_title` | Y (loader) / **not populated in any fixture** | `test_classifier`, `test_hypervisor_hostname_rule`, `test_sonicwall_firewall_rule`, nmap_provider, benchmark, serializer, workbench | Classified, never benchmarked |
| `tls_issuer` | `NmapProvider` (`ssl-cert` NSE, FEAT-003F) | Y | Y | **N** | **N** | Same 3 rules as `http_title` | Y (loader) / **not populated in any fixture** | `test_classifier`, `test_sonicwall_firewall_rule`, nmap_provider, benchmark, serializer, workbench (not separately tested in `test_hypervisor_hostname_rule`) | Classified, never benchmarked |
| `http_auth_realm` | `NmapProvider` (`http-auth` NSE, FEAT-003G) | Y | Y | **N** | **N** | Same 3 rules as `http_title` | Y (loader) / **not populated in any fixture** | `test_classifier`(indirectly via `first_matching_identifier` tests)*, all 3 consumer rule tests, nmap_provider, benchmark, serializer, workbench | Classified, never benchmarked |

\* `first_matching_identifier`'s HTTP-auth-realm check is exercised through the three rule test files, not a dedicated `test_classifier.py` case the way `http_title`/`tls_subject`/`tls_issuer` have one — a minor, low-priority test-symmetry gap.

---

## Pipeline Findings

### 1. The CSV exporter failure is two bugs, not one

`tests/test_csv_exporter.py::test_export_writes_expected_csv_rows` has
been failing since before this session (flagged as pre-existing in
every FEAT-003F/G/H/I validation run). Tracing it fully:

- **Bug A (the visible one):** the test constructs
  `Device(..., device_type="server", ...)` — a raw string, not
  `DeviceType.SERVER`. `Device` is a plain dataclass with no
  `__post_init__` validation, so this succeeds at construction.
  `CsvExporter.export()` then runs `device.device_type.name`, and
  `str` has no `.name` → `AttributeError`.
- **Bug B (hidden behind Bug A):** even if the test were fixed to
  construct `DeviceType.SERVER` properly, it would **still fail** on
  the next line. The test's own expected row is
  `["...", "server", "..."]` — lowercase, matching `DeviceType.SERVER.value`
  (`"server"`). But `CsvExporter` reads `.name`, which for a `StrEnum`
  member is the uppercase identifier (`"SERVER"`), not the value. The
  test's expectation and the exporter's implementation disagree about
  which enum attribute is the "correct" display convention — the same
  question `MarkdownExporter` already answers differently (it uses
  `.value.replace("_", " ").title()` → `"Server"`).

This means CSV export has had **zero passing test coverage** for an
unknown period, and fixing only the surface symptom (Bug A) would leave
a second, currently-masked failure. Both bugs are in test/exporter code
only — `Device.device_type` itself is fine.

### 2. `python -m devtools validate` (fast path) cannot see 8 of the project's test modules

`STANDARD_REGRESSION_TESTS` in `devtools/validate.py` lists exactly 11
modules, all classification rule/framework tests. `discover_test_modules()`
(used only by `--all`) finds significantly more. The fast path — the
one nearly every implementation sprint in this project's history has
been instructed to run — structurally cannot catch a regression in:
discovery extraction (`test_nmap_provider_scan_profile`), persistence
(`test_project_serializer`), benchmark loading
(`test_benchmark_runner`), developer tooling
(`test_classification_workbench`), or either product report format
(`test_csv_exporter`, `test_markdown_exporter`), or project comparison/
summary (`test_project_comparator`, `test_project_summary`). This isn't
a defect in TEST-002's design — the fast path is deliberately
classification-scoped for iteration speed — but it is worth naming
explicitly as the reason a real, two-bug exporter failure has persisted
silently: nothing prompts a developer to run `--all` except the
explicit instruction at the end of an implementation sprint, and no
sprint to date has been scoped to fix what `--all` reports as
pre-existing.

### 3. `NetworkGraph.add_device()` has no merge semantics

Confirmed by direct read: `add_device()` returns immediately if the IP
is already a key in `self._devices`, discarding the incoming `Device`
entirely. Within a single `NmapProvider.discover()` call this is never
triggered — the provider merges its own `-sn` and enrichment passes
internally before constructing final `Device` objects, and
`DiscoveryEngine` currently only ever runs one provider. But
`DiscoveryEngine.discover()` is already written generically for
`Iterable[DiscoveryProvider]`, and ROADMAP.md Phase 6 lists six future
providers (SNMP, LLDP, CDP, ARP, mDNS, DNS/NetBIOS enrichment) that
would all add devices to the same graph. The first provider to report a
given IP would permanently win; every other provider's evidence for
that IP would be silently and completely lost, with no warning, no log
line, and no test that would catch it (no existing test constructs a
`DiscoveryEngine` with two providers reporting an overlapping IP).

### 4. `discovery_sources` does not track per-field provenance

The field name implies it records *which* discovery mechanism produced
a device's evidence, but the only producer, `NmapProvider._build_device()`,
hardcodes it to the literal `["nmap"]` for every device, always — a
finding FEAT-003A already made once. This report reconfirms it and adds
a sharper point: since FEAT-003I, `operating_system`/`computer_name`/
`domain` can each be sourced from either SMB or RDP *within the same
provider*, and that per-field precedence decision (documented in code
comments and FEAT-003I's report) is **not recorded anywhere on the
`Device` itself** — there is no way, from a saved project file or the
workbench, to tell whether a given device's `operating_system` came
from `smb-os-discovery` or `rdp-ntlm-info`. This is a minor provenance/
debuggability gap, not a correctness bug.

### 5. Reporting/debugging tool coverage has an asymmetric blind spot

`ClassificationWorkbench.generate()` filters to
`device.device_type == DeviceType.UNKNOWN` only. It is the only tool in
the codebase that shows rule-by-rule evidence for a classification
decision. `BenchmarkRunner`'s mismatch reporting
(`BenchmarkMismatch`/`render_console_report`) shows *which* devices were
misclassified (expected vs. actual `DeviceType`) but not *why* — no
per-rule evidence is attached to a `BenchmarkMismatch`. The practical
result: a device that gets a **wrong but non-`UNKNOWN`** classification
(e.g. a Hyper-V host misclassified as `SERVER`, the exact FEAT-003H
regression this session already hit once via benchmark testing, not
tooling) has **no diagnostic path** in this codebase today short of
manually re-running `DeviceClassifier` in a script or debugger. The
tool that would have shown *why* the FEAT-003H bug happened, had it
slipped past benchmark testing, doesn't cover that device's case.

---

## Unused Evidence

Fields with **zero classification consumers**, cross-referenced against
whether their non-use is intentional:

| Field | Consumed by classification? | Intentional? | Basis |
|---|---|---|---|
| `mac_address` | No (used by `ProjectComparator` and indirectly by `vendor` derivation instead) | **Yes** | Its classification value is already captured one step upstream, via the OUI → `vendor` lookup at discovery time. Consuming it again directly in a rule would be redundant with `vendor`. |
| `protocol` | No | **Yes, documented** | FEAT-003C added it explicitly as scan-completeness diagnostic evidence (is UDP/161 actually reached?), not device-identity evidence. Reconfirmed in ARCH-003. |
| `smb_signing` | No | **Yes, documented** | `Device.smb_signing`'s docstring explicitly scopes it to a future security/compliance report, not classification. ARCH-003 assessed it as a security-posture indicator with no reliable device-type signal. |
| `computer_name` | No | **Undocumented — no stated reason** | No docstring or report has explicitly ruled this out for classification. It is the same *kind* of evidence as `hostname` (a self-reported machine name), just sourced from SMB/RDP protocol negotiation instead of DNS/NetBIOS resolution. See Classification Gaps. |
| `domain` | No | **Undocumented — no stated reason** | Same situation as `computer_name`. |
| `version` | No | **Ambiguous — flagged 3 times, never resolved or explicitly justified** | Flagged as dormant in FEAT-003F's Known Issues, reconfirmed in ARCH-003, reconfirmed again here. Unlike `protocol`/`smb_signing`, no report has ever stated *why* it isn't consumed — only that it isn't. See Classification Gaps for this investigation's assessment of why that might actually be justified. |

---

## Reporting Gaps

### Product-facing reports (CSV, Markdown)

Both exporters were last modified before FEAT-003C (per the field lists
in the Evidence Coverage Matrix, neither has ever read `services` at
all). Every enrichment field added since — `operating_system` through
`http_auth_realm`, ten fields total — is invisible in both formats. For
a tool whose stated vision (`ROADMAP.md`) is "Produce professional
documentation," the two document formats a user actually receives
contain strictly less information than the developer-only
`ClassificationWorkbench` text dump. Concretely:

- Neither report shows per-service evidence (`port`, `protocol`,
  `service`, `product`, `version`) at all — a device's open
  ports/services, the most basic "what did we find on this box" fact,
  isn't in either report.
- Neither report shows `operating_system`, `computer_name`, or `domain`
  — a domain controller correctly identified via SMB evidence produces
  a Markdown/CSV row indistinguishable from a device identified by
  hostname guesswork alone.
- `smb_signing` — evidence explicitly collected *for* a future
  security/compliance report — has no report to appear in yet.

### Engineering/debugging reports

- `docs/reports/*.md` sprint reports are historical artifacts by
  design (per `docs/reports/README.md`'s lifecycle rules) — appropriate
  for their purpose, not a gap.
- `ClassificationWorkbench`'s `UNKNOWN`-only scope (Pipeline Finding 5)
  is the one real gap in the engineering-debugging tooling: there is no
  tool that explains a *wrong* (not unknown) classification.
- `BenchmarkRunner`'s mismatch output reports outcomes, not reasoning,
  compounding the same gap at the benchmark level.

---

## Classification Gaps

Per this sprint's instruction not to broaden classification rules, this
section assesses intent only — no rule changes are proposed for
immediate implementation.

- **`computer_name` / `domain` — undocumented non-consumers, plausible
  future feature.** These are structurally identical in kind to
  `hostname` (self-reported machine identity), just sourced from a
  different protocol. A hostname-style keyword rule (e.g. matching
  `"dc"`/`"cam"` patterns against `computer_name` the way
  `ServerHostnameRule` already does against `hostname`) is a plausible,
  low-risk future corroboration — but implementing it now would violate
  this sprint's "do not broaden classification rules" constraint.
  Recommend scoping as a small, dedicated future sprint if pursued, not
  a silent addition to an unrelated one.
- **`version` — this investigation's assessment: likely already
  justified, just never stated.** `product` carries classification
  value because Nmap's product strings are free text that frequently
  includes vendor/model names (`"VMware ESXi Server httpd"`, `"HP
  LaserJet 4250"`). `version` strings are typically bare numbers
  (`"2.4.41"`, `"6.7.0"`) with no vendor-identifying text — structurally
  closer to `protocol` (diagnostic, not identifying) than to `product`.
  This may be *why* no rule has ever consumed it, without anyone having
  written that reasoning down. Recommend closing this three-times-
  flagged item with a one-line documentation note (in `models.py`'s
  docstring, mirroring `smb_signing`'s pattern) rather than continuing
  to re-flag it as an open question in future investigations.
- **`mac_address`, `protocol`, `smb_signing` — confirmed intentional,
  no action needed.** Already documented elsewhere (see Unused Evidence
  table); this investigation found no reason to revisit any of them.

---

## Recommendations

Presented as independent, individually-approvable items — this report
recommends, it does not authorize implementation of any of them.

1. **Fix the CSV exporter (both bugs).** Decide the enum-display
   convention once (`.value`-based, matching `MarkdownExporter`'s
   existing choice, is the more consistent option) and apply it in both
   the exporter and the test. Smallest, highest-confidence fix in this
   report — a real, currently-broken code path with zero test coverage.
2. **Extend `CsvExporter`/`MarkdownExporter` to surface the ten
   currently-invisible `Device`/`ServiceEvidence` fields.** At minimum:
   `operating_system`, `computer_name`, `domain`, `smb_signing` at the
   device level, and a per-service line (port/protocol/service/product/
   version, plus the identifier-tier fields where present) mirroring
   `ClassificationWorkbench._format_service()`'s existing rendering
   logic, which could plausibly be extracted into a shared helper both
   the workbench and the exporters call.
3. **Add benchmark fixture coverage for `product`, `http_title`,
   `tls_subject`, `tls_issuer`, and `http_auth_realm`.** One device per
   field (or a small number of devices covering several at once) in an
   existing dataset would close the "classified but never benchmarked"
   gap identified for all five fields, matching the pattern FEAT-003H/I
   already used for `operating_system`/`computer_name`/`domain`/
   `smb_signing`.
4. **Extend `ClassificationWorkbench` (or add a sibling tool) to cover
   misclassified-but-not-`UNKNOWN` devices**, likely by accepting an
   optional expected-type map (benchmark-style) and reporting rule
   evidence for any device whose actual type doesn't match, not only
   `UNKNOWN` ones. This directly addresses Pipeline Finding 5 and would
   have shown the FEAT-003H Hyper-V/SERVER regression's root cause
   without needing to read code.
5. **Document `version`'s non-consumption rationale** in
   `core/models.py` (one line, `smb_signing`-docstring-style), closing
   a finding re-flagged three times without resolution.
6. **Consider giving `NetworkGraph.add_device()` merge semantics**
   before a second `DiscoveryProvider` is introduced (ROADMAP Phase 6).
   Out of scope for immediate action — no second provider exists yet —
   but should be resolved *before* one is built, not discovered as a
   data-loss bug after.
7. **Add a `test_project_serializer`/`test_benchmark_runner` round-trip
   assertion for `mac_address`.** The field is already wired in both
   code paths; only the test coverage is missing.

## Recommended Implementation Order

1. **Recommendation 1** (CSV exporter bugs) — smallest, isolated,
   already-failing, zero design ambiguity once the enum-convention
   question is settled.
2. **Recommendation 7** (`mac_address` round-trip test) — trivial,
   additive, no design decisions.
3. **Recommendation 5** (`version` docstring) — trivial, additive, no
   design decisions, closes a repeatedly-reopened finding.
4. **Recommendation 3** (benchmark fixture coverage for the five
   unbenchmarked classification-active fields) — mechanical, follows an
   established pattern (FEAT-003H/I), no classification rule changes.
5. **Recommendation 2** (CSV/Markdown field expansion) — larger, needs
   a design decision about output shape (new columns vs. a
   services-detail section; how to render multiple services per
   device in CSV's row-per-device format), but high product value and
   no classification-logic risk.
6. **Recommendation 4** (workbench mismatch-evidence coverage) —
   valuable but the largest design surface of this list (needs an
   expected-type input mechanism); best scoped as its own sprint once
   1-5 are settled.
7. **Recommendation 6** (`NetworkGraph` merge semantics) — correctly
   sequenced last: it has no observable effect until a second
   `DiscoveryProvider` exists, and the merge *policy* (field-by-field
   like FEAT-003I's SMB/RDP precedence? last-write-wins? explicit
   conflict reporting?) deserves its own design discussion, likely
   alongside whichever sprint first introduces a second provider.
