# Status

Plan Approved (Revision 3 — corrected local-subnet detection contract)

Approval: Revision 3 was engineer-approved and served as the implementation authority for FEAT-013A.

Authority: This document's own investigation against the current codebase (no ARCH precedes it — see Section 7: the composition architecture PLAN-013A relies on already exists and was not re-litigated).

Implements: FEAT-013A — Configurable Multi-Subnet Discovery

Production Code Modified: Yes (see Section 3)

New ADR Required: No (Section 7)

---

This is Revision 3 of this plan. Revision 1 proposed removing the
hard-coded `172.16.100.0/24` default and making `--subnet` unconditionally
required. Revision 2 replaced that with local-subnet auto-detection as the
no-`--subnet` fallback, but **overstated what the detection technique
actually guarantees** — it described the OS routing-table probe as
something that "gets right" the disconnected-adapter and
prefer-physical-over-virtual distinctions, which is not an accurate claim
about what a single routed-source-address lookup can promise. **Revision
3 corrects that claim** to the technique's actual, honest contract
(Section 1.4), adds explicit documentation of the two edge cases that
follow from that honest contract (a preferred VPN/virtual route may be
selected; an isolated network may fail detection entirely), states plainly
that neither edge case is handled by adding interface-ranking logic in
FEAT-013A (the existing `--subnet` override is the handling mechanism for
both), and adds a new requirement that the detected source address and
derived subnet are printed clearly before discovery begins so the operator
can sanity-check what was actually selected. The approved behavior itself
is unchanged: explicit `--subnet` values completely override
auto-detection; with no `--subnet`, exactly one local IPv4 subnet is
detected; every attached interface is never enumerated; there is no
hard-coded fallback. Sections 1.4, 2.4, 2.5, 3, 5, and 8 are revised
accordingly; Sections 1.1, 1.3, 4, 6, 7, and 9's ordering are carried
forward unchanged (already confirmed against the code, unaffected by this
correction).

Grounded against the code as it stands today: `application.py`,
`discovery_engine.py`, `nmap_provider.py`, `run_diagnostics.py`,
`discovery_summary.py`, `report_run.py`, `project_summary.py`,
`project/models.py`, `csv_exporter.py`, `markdown_exporter.py`,
`identity/resolver.py`, `relationships/resolver.py`,
`runtime/cli_renderer.py`, `runtime/telemetry.py`,
`tests/test_application_cli.py`, `tests/test_discovery_engine.py`,
`requirements.txt`, and the installed `venv/` (confirmed no `psutil`,
`netifaces`, or `pywin32` present — Section 1.4).

---

## 1. Investigation Findings

### 1.1 Already generalized to N providers (confirmed by reading the code, not assumed)

- **`DiscoveryEngine.discover()`** (`discovery_engine.py:73-79`) iterates
  `self._providers` in list order, merges devices into `devices_by_ip` via
  `setdefault` (first provider to report an IP wins on collision — already
  exercised by `test_duplicate_ip_across_discovery_providers_is_deduplicated`
  and `test_multiple_providers_contribute_to_the_same_graph` in
  `tests/test_discovery_engine.py`), and aggregates `self.observations` from
  every provider in the same order (`test_discovery_engine_aggregates_observations_from_multiple_providers`).
  Nothing here is scoped to exactly one provider, and nothing needs to
  change.
- **`NmapProvider`** already takes a single `subnet_cidr: str` per instance
  (`nmap_provider.py:105-127`) — it was never a multi-subnet aggregator and
  doesn't need to become one. One instance per CIDR is already the
  correct shape, whether that CIDR came from an explicit `--subnet` or
  from auto-detection.
- **`IdentityResolver`** groups purely by `subject` (today, an IP address)
  across whatever observation collection it's handed
  (`identity/resolver.py:62-64`). No change.
- **`RelationshipResolver`** is likewise subject/category-keyed with no
  provider or subnet awareness (`relationships/resolver.py:111-114`). No
  change.
- **`ProjectSummary`, `RunMetadata`, `CsvExporter`, `MarkdownExporter`**
  contain no per-subnet or single-provider assumption at all —
  `ProjectSummary.discovered_networks` is hard-coded to `[]` today
  (`project_summary.py:53`). Confirmed unchanged.
- **`RuntimeTelemetryRecorder`** (`runtime/telemetry.py:50-68`) appends a
  new `PhaseTelemetry` to a list on every `PHASE_COMPLETED` event; safe
  under sequential multi-provider execution (Revision 1's analysis,
  unaffected by how the subnet list was populated). Confirmed unchanged.

### 1.2 The actual limitation (unchanged from Revision 1)

`application.py:89-91` constructs exactly one `NmapProvider` from a
hard-coded literal, and everything downstream in `Application.run()` holds
a single `provider` variable. This remains the only place requiring
change; Revision 2 changes *what replaces the literal*, not *where*.

### 1.3 Failure semantics — a real, pre-existing gap, deliberately not fixed here (unchanged from Revision 1)

`DiscoveryEngine.discover()`'s per-provider loop has no try/except around
`provider.discover()` — only `EnrichmentProvider.enrich()` gets that
safety net. Not changed by this revision; see Revision 1's analysis
(retained in full in Section 1.3 of this document's history — the
mitigations named there, CLI-layer CIDR validation eliminating the
realistic exception source, apply identically whether the CIDR list came
from `--subnet` or from local-subnet auto-detection, since both paths
converge on the same validated `subnets: list[str]` before any
`NmapProvider` is constructed).

### 1.4 Local IPv4 subnet auto-detection — new investigation for Revision 2

**No dependency currently installed supports this.** `requirements.txt`
lists only `python-nmap` and `pysnmp`; `venv/Lib/site-packages` has no
`psutil`, `netifaces`, or `pywin32`. Per the instruction to prefer
standard-library/already-installed tooling and avoid adding a dependency
unless genuinely necessary, this plan uses only `socket`, `ipaddress`, and
`subprocess` (all stdlib) plus `powershell.exe` — a component of Windows
itself, not a pip dependency, and already this project's own documented
primary shell.

**Design: split into two narrow, independently-reliable steps, rather
than one heuristic that tries to enumerate and rank adapters.**

**Step 1 — identify the active address via a UDP "connect" to a
routable, non-loopback destination:**

```python
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.connect(("8.8.8.8", 80))
address = sock.getsockname()[0]
```

`connect()` on a `SOCK_DGRAM` socket never transmits a packet — it only
asks the OS kernel to resolve which local interface and source address
its routing table would use to reach that destination, then binds the
socket to it. `getsockname()` then reads that source address back. This
is why it works without real internet connectivity (any reachable route,
including a private LAN gateway with no upstream internet, is sufficient).

**Accurate contract — corrected from an earlier draft of this plan that
overstated it:** this technique does not "avoid virtual adapters" or
"select the physical LAN" as a guaranteed property. Its actual, honest
contract is: **NetworkMapper selects the primary routed IPv4
source/interface that Windows itself chooses for this probe destination,
then derives that interface's subnet.** Whatever Windows' routing table
resolves for a route to `8.8.8.8:80` is what this returns — nothing more
is claimed and nothing more is verified. It requires no adapter-enumeration
code of our own precisely because it asks the kernel for its answer rather
than computing one independently, but "the kernel's answer" is not the
same guarantee as "the physical LAN adapter" or "never a disconnected/
virtual adapter." Two concrete consequences follow directly, and are
documented here rather than silently left for an operator to discover:

- **A preferred VPN or other virtual route may be selected.** If a VPN
  client has installed a virtual adapter as the system's preferred/default
  route (a full-tunnel VPN, for example), this technique will report that
  VPN adapter's address and subnet — not the underlying physical LAN's.
  This is Windows' own routing decision being reported faithfully, not a
  detection bug, but it may not be the network the operator actually
  intends to scan.
- **An isolated network with no usable outbound/default route may fail
  automatic detection entirely.** If Windows has no route it would use for
  an external destination at all (no default gateway configured, fully
  air-gapped host), the `connect()` call itself fails, and detection
  reports failure (Section 2.5) rather than guessing.

**Neither case is handled by adding interface-ranking, adapter-preference,
or multi-candidate logic in FEAT-013A.** Both are handled the same way:
the operator sees exactly what was selected (this revision's new
print-before-discovery requirement, Section 2.4) and, if it is wrong or
detection fails outright, supplies `--subnet` explicitly — which
completely overrides auto-detection (Section 2.2) and requires no code
change to work correctly today. Building adapter-ranking heuristics to
try to prefer "the real LAN" over a VPN would be exactly the kind of
speculative, unrequested generalization this plan otherwise avoids, and
would still not be reliably correct in every environment — the explicit
override is the correct escape hatch, not a workaround.

**Step 2 — explicitly reject loopback and APIPA, even though Step 1
should not normally produce them:**

```python
parsed = ipaddress.ip_address(address)
if parsed.is_loopback or parsed.is_link_local:
    return None
```

`ipaddress.ip_address(...).is_loopback` covers `127.0.0.0/8`;
`.is_link_local` covers `169.254.0.0/16` (APIPA). This check is kept even
though Step 1's routing-table approach should never surface either
address in practice — it is the explicit, cheap defense-in-depth the
sprint asks for by name, rather than an implicit assumption about Step
1's behavior.

**Step 3 — resolve that address's prefix length via `Get-NetIPAddress`:**

The standard library has no cross-platform (or Windows-specific) way to
read an interface's subnet mask/prefix length — `socket` alone cannot do
this on any platform. Two Windows-native options were considered:

- **Parsing `ipconfig` output** — rejected. `ipconfig`'s field labels
  (`"Subnet Mask"`, etc.) are localized to the OS display language, so a
  non-English Windows install would silently break a text-label parser.
  This is a real, known class of fragility, not a hypothetical one.
- **`Get-NetIPAddress -AddressFamily IPv4 -IPAddress <address>`
  (PowerShell's `NetTCPIP` module, built into Windows 8/Server 2012 and
  later, present by default on the Windows 11 target environment)** —
  chosen. It exposes `PrefixLength` as a structured integer property, not
  a localized text field, so the query is immune to the `ipconfig`
  fragility above. Invoked via `subprocess`, requesting a bare
  `-ExpandProperty PrefixLength` value (no JSON parsing needed for a
  single scalar), scoped to exactly the one address Step 1 already
  identified — this call answers only "what is this specific, already-known
  address's prefix length," not "which adapter is active," so it carries
  none of the adapter-selection risk enumerating all adapters would.

```python
subprocess.run(
    ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
     f"(Get-NetIPAddress -AddressFamily IPv4 -IPAddress '{address}' "
     f"-ErrorAction Stop).PrefixLength"],
    capture_output=True, text=True, timeout=5.0, check=True,
)
```

`address` is a value this process just read from its own socket's
`getsockname()`, not external/operator input, so no shell-injection
concern applies to the interpolated PowerShell string. A 5-second timeout
and `check=True` (raising on non-zero exit) both convert any failure mode
— PowerShell unavailable, the address no longer present, the cmdlet
missing on an older Windows build — into the same "detection failed"
outcome (Section 1.4's Step 4), never a hang or an unhandled traceback.

**Step 4 — combine, and fail closed:**

```python
@dataclass(frozen=True)
class DetectedLocalSubnet:
    source_address: str   # e.g. "192.168.1.55" — the raw address Step 1 found
    subnet_cidr: str      # e.g. "192.168.1.0/24" — the canonical derived network

network = ipaddress.ip_network(f"{address}/{prefix_length}", strict=False)
return DetectedLocalSubnet(source_address=address, subnet_cidr=str(network))
```

`detect_local_subnet()` returns `DetectedLocalSubnet | None`, not a bare
CIDR string — this revision's new requirement (Section 2.4) is that the
operator sees both the raw detected address *and* the derived subnet
before discovery begins, so both must be available to the caller, not
just the final network. `strict=False` plus reconstructing via
`ip_network` produces the canonical network CIDR (host bits cleared) from
the host address and prefix length — e.g. `192.168.1.55/24` →
`"192.168.1.0/24"`. Any failure at Step 1 (socket error), Step 2
(loopback/APIPA), or Step 3 (PowerShell failure, non-integer output,
timeout) returns `None` from the detection function as a whole. **No step
falls back to a guessed or hard-coded value at any point** — an unresolved
prefix length does not default to `/24`; it is treated as total detection
failure, per the sprint's explicit instruction not to fall back to any
hard-coded network.

**Named, accepted limitations:**
- Steps 1 and 3 are two separate OS queries a few milliseconds apart; a
  DHCP lease change or adapter state change in that window could
  theoretically make Step 3's lookup miss the address Step 1 found. This
  is an unmitigated, negligible race — not defended against, and not
  worth the added complexity for a window this narrow.
- A preferred VPN/virtual route being selected, and an isolated network
  producing outright detection failure, are not "limitations" to fix in
  this plan at all — they are the technique's documented, accurate
  contract (above), explicitly handled by the existing `--subnet`
  override rather than by new detection logic.

---

## 2. CLI Contract (Revised Decision)

### 2.1 Flag: repeatable `--subnet` (unchanged from Revision 1)

```
python main.py --subnet 172.16.100.0/24 --subnet 172.16.101.0/24 --scan-profile fast
```

Added via `action="append"`, matching the sprint's suggested UX.

### 2.2 Explicit vs. auto-detected scan scope — the revised decision

**If one or more `--subnet` values are supplied, they define the complete
scan scope, exactly as validated (Section 2.3) — full stop.** Local
subnet detection is never consulted, never merged in, and never even
attempted when at least one `--subnet` was given. This is enforced
structurally, not by a flag check that could drift: the CLI-parsing code
path and the auto-detection code path are mutually exclusive branches
(Section 2.4), so there is no code path in which both execute and their
results combine.

**If no `--subnet` values are supplied, NetworkMapper attempts to
auto-detect the active local IPv4 subnet (Section 1.4) and uses that
single subnet as the entire scan scope.** This replaces Revision 1's "no
subnet supplied → error" decision.

**The hard-coded `172.16.100.0/24` literal is still removed entirely** —
Revision 2 does not reintroduce it in any form, including as a fallback
if detection itself fails (Section 2.5).

### 2.3 Validation rules for explicit `--subnet` values (unchanged from Revision 1)

- **CIDR parsing**: `ipaddress.ip_network(value, strict=False)` per value.
- **IPv4-only for this sprint**: any `version == 6` value is rejected with
  a clear stderr message.
- **Invalid CIDR**: rejected with a clear stderr message naming the
  offending value, `SystemExit(2)`, before any `NmapProvider` is
  constructed.
- **Duplicate subnets**: deduplicated by canonical network string,
  preserving first-occurrence order.
- **Provider ordering**: deterministic, equal to CLI argument order after
  dedup.

These rules apply only to explicit `--subnet` values. The auto-detected
subnet (Section 1.4) is already canonical by construction (Step 4) and
needs no separate validation pass — it is IPv4 by construction (Step 1
only ever queries an IPv4 destination) and already loopback/APIPA-checked
(Step 2).

### 2.4 Control flow

```python
subnets = self._parse_subnets(args.subnet)   # [] if --subnet was never passed
if not subnets:
    detected = detect_local_subnet()
    if detected is None:
        print(<error>, file=sys.stderr)      # Section 2.5
        raise SystemExit(2)
    print(
        f"No --subnet supplied. Detected local IPv4 address "
        f"{detected.source_address} -> using subnet {detected.subnet_cidr}."
    )
    subnets = [detected.subnet_cidr]
```

`_parse_subnets()` no longer raises/exits on an empty *input* (Revision
1's "no subnet supplied → exit 2" behavior moves entirely into the
`detected is None` branch above); it still raises/exits exactly as before
for an explicitly-supplied-but-invalid value, since that is unambiguously
an operator error, not a "no preference stated" case.

**New requirement (Revision 3): the detected source address and the
derived subnet are both printed, together, before discovery begins** —
not just the final subnet in isolation. This is deliberate, not
redundant: printing only `subnet_cidr` would hide *which* interface/route
Windows actually selected (Section 1.4's corrected contract), which is
exactly the information an operator needs to notice "that's my VPN, not
my LAN" before a scan runs against the wrong network. This line prints
unconditionally whenever detection succeeds — it is not gated behind any
verbosity flag, since it is the operator's only pre-scan opportunity to
catch a wrong-route selection.

### 2.5 Failure behavior when local detection fails (new, per instruction)

When `--subnet` was not supplied **and** `detect_local_subnet()` returns
`None` (any of Section 1.4's Steps 1–3 failed — most notably, per
Section 1.4's corrected contract, an isolated host with no usable
outbound/default route, where Step 1's `connect()` itself fails):

- Print a clear, specific error to stderr — naming that automatic
  detection was attempted and failed (not a generic "invalid input"
  message, so an operator can distinguish this from a typo'd `--subnet`
  value).
- Advise the operator to supply `--subnet` explicitly.
- Exit with `SystemExit(2)`, matching every other CLI validation failure
  already in `application.py` (`_parse_scan_profile`,
  `_resolve_snmp_credentials`).
- **Do not fall back to any hard-coded network** — there is no literal
  CIDR anywhere in this code path for this case to fall back to.

Example message: `"Error: no --subnet supplied and NetworkMapper could
not automatically determine an active local IPv4 subnet. Provide
--subnet explicitly."`

---

## 3. File Inventory (Revised)

| File | Change |
|---|---|
| `networkmapper/discovery/local_subnet.py` | **New.** `DetectedLocalSubnet` (frozen dataclass: `source_address`, `subnet_cidr`) and `detect_local_subnet()` with its three injectable steps (Section 1.4): active-address detection (injectable socket factory), loopback/APIPA rejection, prefix-length resolution (injectable PowerShell runner), canonical-CIDR assembly. Returns both the raw detected address and the derived subnet, not just the subnet, so the caller can print both per Section 2.4's new requirement. No dependency on `application.py`, `NmapProvider`, or `DiscoveryEngine` — a standalone, independently testable module, mirroring this codebase's existing pattern of isolating OS/protocol-facing logic (`snmp_client.py`). |
| `tests/test_local_subnet_detection.py` | **New.** Unit tests for `local_subnet.py`, using injected fake socket and fake PowerShell-runner callables — no real network calls, no real `powershell.exe` invocation, no live-network access. See Section 8.1. |
| `networkmapper/application.py` | Add `--subnet` (`action="append"`) to the argument parser; add `_parse_subnets()` (CIDR validation, IPv4-only check, dedup — returns `[]` rather than exiting when no values were supplied, per Section 2.4); import and call `detect_local_subnet()` when `_parse_subnets()` returns `[]`, exiting per Section 2.5 if it returns `None`; replace the single hard-coded `provider = NmapProvider(...)` with `providers = [NmapProvider(cidr, scan_profile=scan_profile, event_bus=event_bus) for cidr in subnets]`; pass `providers` (not `[provider]`) to `DiscoveryEngine`; replace the single-provider diagnostics block with a loop over `zip(subnets, providers)` printing a `Subnet: <cidr>` header before each provider's existing `_print_discovery_diagnostics()` call (Section 5, unchanged from Revision 1 — the loop is agnostic to whether `subnets` came from `--subnet` or detection). |
| `tests/test_application_cli.py` | Update the shared `_run_application` helper and existing tests: tests exercising explicit single/multi-subnet behavior now pass `--subnet` directly (unchanged from Revision 1's intent); tests exercising the *no-`--subnet`* path now mock `detect_local_subnet` instead of expecting an immediate error (Revision 1's "no subnet supplied exits with non-zero code" test is replaced, not kept — see Section 8.2). Add new tests per Section 8.2. |

No changes to `requirements.txt` — no new dependency. No new `Project`
fields, no new resolver behavior, no new discovery-provider class, no
`DiscoveryEngine`/`NmapProvider` changes.

---

## 4. Discovery Composition (Revised)

```
--subnet values (repeated, optional)
      │
      ├─ present ──────────────► _parse_subnets(): validate, IPv4-only,
      │                          dedup  ──────────────────────────┐
      │                                                            │
      └─ absent ───► detect_local_subnet() ──► DetectedLocalSubnet │
                      (address + canonical CIDR, both printed), or │
                      None → print error, exit(2)                  │
                            │                                      │
                            └──────────────────────────────────────┤
                                                                    ▼
                                                    validated `subnets: list[str]`
                                                    (never populated from both
                                                     branches — mutually exclusive)
                                                                    │
                                                                    ▼
                                                one NmapProvider per CIDR
                                                                    │
                                                                    ▼
                                                DiscoveryEngine(providers)
                                                (unchanged constructor/discover())
                                                                    │
                                                                    ▼
                                                single merged NetworkGraph
```

Confirmed against the actual code (Section 1.1), not assumed. No
`MultiSubnetNmapProvider`, no second `DiscoveryEngine`, no subnet
aggregation inside `NmapProvider`, no new resolver behavior, no new
`Project` field.

---

## 5. Diagnostics / Telemetry (unchanged from Revision 1)

Diagnostics are printed once per subnet, each block labeled with its own
CIDR, regardless of whether that subnet came from `--subnet` or from
auto-detection — the printing loop operates on `subnets`/`providers`
uniformly and has no branch on where the list came from:

```python
for subnet_cidr, provider in zip(subnets, providers):
    if provider.run_diagnostics is not None:
        print(f"\nSubnet: {subnet_cidr}")
        self._print_discovery_diagnostics(scan_profile, provider.run_diagnostics)
```

When auto-detection supplied the single subnet, the operator has already
seen the Section 2.4 line naming both the detected source address and the
derived subnet before this loop runs, so the `Subnet:` header here is
confirmatory, not the only place the detected value is surfaced — the
address/subnet announcement is the operator's sanity-check point, printed
once, unconditionally, before discovery starts.

`RunDiagnostics` and `DiscoverySummary` remain unchanged (Section 1.1).
The Runtime Summary's per-subnet-row labeling gap (named in Revision 1) is
unaffected by this revision and remains an accepted, unfixed cosmetic
limitation.

---

## 6. SNMP Enrichment / Identity / Relationship Pipeline (unchanged from Revision 1)

Unaffected by whether `subnets` was populated from `--subnet` or from
detection — both produce the same shape (`list[str]` of one or more
canonical IPv4 CIDRs) before any downstream code runs. Section 6's full
analysis from Revision 1 (single shared SNMP-family provider set
regardless of subnet count; resolvers are subnet-unaware;
overlapping-CIDR collision handling already works) carries forward
without modification.

---

## 7. ADR / ARCH Requirement

**No new ADR or ARCH is required**, with one point flagged rather than
silently absorbed:

This plan introduces the codebase's **first OS-specific runtime
behavior** — `local_subnet.py` invokes `powershell.exe` and is
Windows-only by construction (Section 1.4's chosen mechanism has no
Linux/macOS equivalent). This is acceptable and requires no ADR *now*
because: this sprint's explicit target environment is Windows (the
authority section's own PowerShell examples, the recorded dev
environment, and the current absence of any cross-platform
abstraction anywhere else in `networkmapper/`), and introducing a
speculative cross-platform abstraction for a capability with exactly one
real target platform today would itself be the kind of unrequested
abstraction `ENGINEERING.md`'s Architecture Policy warns against.

**Named for future reference, per this project's practice of surfacing an
unreached decision rather than ignoring it:** if NetworkMapper is later
asked to run local-subnet detection on Linux or macOS, that will require
either a per-platform branch inside `local_subnet.py` or a small
architectural decision about how OS-specific capability is structured
project-wide (a `platform.system()` dispatch, a small strategy interface,
etc.). That decision is not reached by this plan and is not required for
FEAT-013A as scoped.

Everything else in this plan remains additive CLI/application-layer
plumbing over an already-existing, unmodified `DiscoveryEngine` — none of
it touches ADR-010 through ADR-013's subject matter.

---

## 8. Testing Strategy (Revised)

All tests use mocked/injected dependencies — no live network access, no
real `powershell.exe` invocation, no real socket connection, consistent
with the sprint's explicit requirement.

### 8.1 `networkmapper/discovery/local_subnet.py` — new unit tests (`tests/test_local_subnet_detection.py`)

Using an injected fake socket object (stub `.connect()`/`.getsockname()`/`.close()`)
and an injected fake PowerShell-runner callable (returns a canned stdout
string or raises, mirroring the existing `SnmpClient`-stub injection
pattern already used throughout this codebase):

- `test_detected_address_and_prefix_combine_into_a_canonical_cidr` (fake socket → `"192.168.1.55"`, fake runner → `"24"`; asserts `DetectedLocalSubnet(source_address="192.168.1.55", subnet_cidr="192.168.1.0/24")` — both the raw address and the host-bits-cleared network are asserted, not just the subnet)
- `test_result_preserves_the_raw_source_address_distinct_from_the_derived_subnet` (fake socket → `"10.0.0.200"`, fake runner → `"8"`; asserts `source_address == "10.0.0.200"` while `subnet_cidr == "10.0.0.0/8"` — the two fields must not collapse into one, since the CLI layer prints both separately)
- `test_loopback_address_is_rejected` (fake socket → `"127.0.0.1"`; asserts `None`, PowerShell runner never invoked)
- `test_apipa_address_is_rejected` (fake socket → `"169.254.10.5"`; asserts `None`, PowerShell runner never invoked)
- `test_socket_failure_returns_none` (fake socket raises `OSError` on `connect()` — the documented "isolated network, no default route" case from Section 1.4; asserts `None`)
- `test_powershell_failure_returns_none` (fake runner raises; asserts `None`, no exception propagates)
- `test_powershell_timeout_returns_none`
- `test_non_integer_prefix_length_output_returns_none` (fake runner returns unparsable stdout, e.g. empty string)
- `test_no_hard_coded_network_is_ever_returned_on_any_failure_path` (parameterized over every failure mode above; asserts the return value is `None`, never a `DetectedLocalSubnet` built from a literal/guessed value)
- `test_a_vpn_or_virtual_adapter_address_is_returned_without_special_casing` (fake socket → an address in a documented-as-virtual test range, e.g. `"10.8.0.6"` with fake runner → `"24"`; asserts detection succeeds and returns that address/subnet exactly as given — proving, per Section 1.4's corrected contract, that this function does not attempt to distinguish "virtual" from "physical" and is not expected to)

### 8.2 `tests/test_application_cli.py` — CLI integration (revised)

- `test_explicit_single_subnet_overrides_local_detection` (`--subnet 172.16.100.0/24`; mocks `detect_local_subnet`; asserts it is **never called**, and the provider is constructed with the explicit value)
- `test_explicit_multiple_subnets_bypass_local_detection` (`--subnet` × 2; asserts `detect_local_subnet` never called; two providers constructed in CLI order)
- `test_no_subnet_supplied_uses_detected_local_subnet` (no `--subnet`; mocks `detect_local_subnet` to return `DetectedLocalSubnet(source_address="192.168.1.55", subnet_cidr="192.168.1.0/24")`; asserts exactly one provider constructed with `"192.168.1.0/24"`)
- `test_detected_source_address_and_subnet_are_both_printed_before_discovery_begins` (same mock as above; asserts stdout contains **both** `"192.168.1.55"` and `"192.168.1.0/24"`, and that this line appears before the discovery-diagnostics/graph-processing output — this is the new Section 2.4 sanity-check requirement, not merely a byproduct of the subnet being used)
- `test_local_detection_failure_exits_cleanly` (no `--subnet`; mocks `detect_local_subnet` to return `None`; asserts `SystemExit(2)`, a stderr message advising `--subnet`, and that `NmapProvider`/`DiscoveryEngine` are never constructed)
- `test_duplicate_subnets_construct_only_one_provider`
- `test_invalid_subnet_exits_before_any_provider_is_constructed`
- `test_diagnostics_are_printed_once_per_subnet_each_labeled_with_its_cidr` (multi-subnet, each with distinct `run_diagnostics`)
- `test_existing_single_subnet_diagnostics_output_is_unchanged` (regression, explicit `--subnet`)
- `test_snmp_flags_compose_with_multiple_subnets` (`--subnet` × 2 plus SNMP-family flags: each SNMP-family provider still constructed exactly once)
- All pre-existing tests (scan-profile selection, workbench flag, per-profile diagnostics content, SNMP flag gating/credential errors) updated to pass `--subnet 172.16.100.0/24` explicitly; assertions otherwise unchanged.

**Explicitly removed from Revision 1's plan:** a test named
`test_no_subnet_supplied_exits_with_non_zero_code` with no detection
mock — under Revision 2, "no `--subnet`" is a valid, meaningful path
(attempt detection) rather than an immediate error, so that exact test
name/intent no longer describes correct behavior. It is replaced by
`test_local_detection_failure_exits_cleanly` above, which asserts the
*same* exit behavior but only conditioned on detection itself failing.

### 8.3 `tests/test_discovery_engine.py` — confirmed sufficient, no new tests required (unchanged from Revision 1)

### 8.4 Identity/relationship pipeline — confirmed sufficient, no new tests required (unchanged from Revision 1)

---

## 9. Implementation Order (Revised)

1. `networkmapper/discovery/local_subnet.py` (`detect_local_subnet()` and its three steps, with injectable socket factory and PowerShell runner) plus `tests/test_local_subnet_detection.py` (Section 8.1) — fully isolable, no dependency on `application.py`.
2. `_parse_subnets()` in `application.py`, revised to return `[]` on no input rather than exiting.
3. Wire the `detected is None → error/exit` branch (Section 2.4/2.5) into `Application.run()`.
4. Replace hard-coded `provider`/`NmapProvider(...)` construction with the `providers` list comprehension over `subnets`.
5. Update the `DiscoveryEngine(...)` call site to pass `providers`.
6. Replace the single-provider diagnostics block with the per-subnet loop (Section 5).
7. Update `tests/test_application_cli.py`'s shared helper and all existing tests to pass `--subnet` explicitly where appropriate; add the new tests from Section 8.2, including the local-detection mocking tests.
8. Full-suite validation (`pytest`) — confirms Sections 8.3/8.4's "no change required" claims rather than merely asserting them.

---

## 10. Scope Confirmation (Revised)

This plan implements: CLI-level acceptance of one or more explicit,
validated IPv4 CIDRs; automatic single-subnet local-IPv4 detection as the
fallback when none are supplied; one `NmapProvider` per distinct subnet
either way; all feeding one `DiscoveryEngine` and one merged
`NetworkGraph`/observation set; diagnostics preserved per subnet; clean,
non-zero-exit failure when neither an explicit subnet nor a usable
detected subnet is available.

It does not implement, and no step above introduces: automatic VLAN
discovery, multi-subnet auto-detection (only a single local subnet is
ever auto-detected — enumerating and scanning *every* locally-attached
subnet automatically is a materially larger feature, not requested here
and not implied by "determine the active local IPv4 subnet"), Q-BRIDGE-MIB/VLAN
enumeration, routing-table or gateway discovery beyond the one
kernel-routing query in Section 1.4 Step 1, network-interface discovery
as a reportable feature, topology, new SNMP credential handling, IPv6
discovery or IPv6 local detection, non-Windows local-subnet detection,
scan-concurrency changes, presentation changes, or ARCH-025 — all
explicitly out of scope, either from the original sprint framing or from
this revision's own narrower "single active local IPv4 subnet" wording.
**Also explicitly excluded by this revision:** any interface-enumeration,
interface-ranking, or "prefer physical over virtual" adapter-selection
logic for local-subnet detection (Section 1.4) — a VPN/virtual route being
selected, or detection failing outright on an isolated network, are both
resolved by the operator's existing `--subnet` override, never by adding
such logic in FEAT-013A.
