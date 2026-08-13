# Status

Investigation Complete

Implementation: Not Started

Production Code Modified: No

Dependencies Added: No

ADR Required: Yes, for one structural decision — the `DiscoveryProvider` /
`EnrichmentProvider` split and `DiscoveryEngine`'s two-phase orchestration
(see ADR Recommendation). Not required for the SNMP canonical evidence
fields themselves — these follow the plain incremental named-field
pattern ADR-009 already establishes and ARCH-003 Section 3 already
concluded applies to `sysDescr`/`sysObjectID` specifically.

Recommended Next Sprint:
FEAT-005 — Implement the `EnrichmentProvider` contract and a v2c-only
`SnmpEnrichmentProvider` per this architecture (system-group evidence
only; SNMPv3 and interface/topology evidence explicitly out of scope —
see Implementation Sequence).

---

## Summary

SNMP is architecturally unlike every discovery source NetworkMapper has
integrated so far. `NmapProvider` is the only implemented
`DiscoveryProvider`, and it plays two roles at once inside one class:
finding hosts (`-sn`) and then enriching the hosts it just found
(`-sV`/NSE), merging both into the same `Device` objects by IP before
ever returning them (`NmapProvider._discover_with_enrichment`). SNMP has
no host-discovery role at all — ARCH-003/BENCH-002 already established
that its entire value (`sysDescr`/`sysObjectID`, "the single most
deterministic device-identity field evaluated across this project's
entire investigation history, when reachable") is enrichment of hosts
some other source already found. Forcing SNMP through the current
`DiscoveryProvider.discover() -> list[Device]` contract as a second,
independent provider would not compose safely: `DiscoveryEngine` today
concatenates every provider's device list and `NetworkGraph.add_device`
silently drops any device whose IP is already present, so a second
provider producing `Device` objects for IPs Nmap already found would
either overwrite or lose evidence depending on provider order, with no
merge logic anywhere to prevent it.

This investigation recommends a new, narrower provider category —
`EnrichmentProvider` — that receives the already-discovered device set
and adds evidence to it in place, structurally separate from
`DiscoveryProvider`'s host-finding role. SNMP becomes the first concrete
`EnrichmentProvider`. It never discovers hosts, is optional by
construction (simply absent from the provider list when no credentials
are supplied), fails per-host without ever raising out of `enrich()`,
and is opt-in independent of the FAST/STANDARD/DEEP ladder rather than
bundled into any of them.

The recommended v1 evidence scope is narrow and cheap: the standard MIB-2
"system group" (`sysDescr`, `sysObjectID`, `sysUpTime`, `sysContact`,
`sysName`, `sysLocation` — OIDs `1.3.6.1.2.1.1.1` through `.6`), all
retrievable in a single GET-request PDU per host — one UDP round trip,
regardless of how many of those six scalars are requested. Interface
inventory (`ifTable`) and any topology/relationship evidence are
explicitly deferred, reconfirming ARCH-003/BENCH-002's existing finding
that they require a topology/relationship model no part of the
architecture has today — this investigation found no new information
that changes that.

Version strategy: SNMPv2c only for v1. SNMPv3 is deferred to its own
follow-on sprint once v2c's field value is validated — its
authentication/privacy negotiation is a meaningfully larger
implementation and testing surface, and bundling it into the same sprint
as the core provider boundary risks the same kind of scope conflation
ARCH-010 already flagged once (UDP reachability vs. SNMP evidence
collection as "two separate decisions, not one").

Credentials are runtime-only, sourced from environment variables or an
interactive prompt (never CLI plaintext arguments, never a config file,
never persisted), and structurally excluded from the canonical model —
they have no path into `Device`, `RunMetadata`, or the knowledge
repository because nothing in this design ever attaches them to those
objects, not because a filter is expected to catch them later.

SNMP is recommended as an explicit opt-in flag, orthogonal to
`--scan-profile`, not part of FAST, STANDARD, or DEEP — it requires a
credential none of the three need, and BENCH-002/ARCH-003 both already
established that UDP timeout cost is dominated by non-responding hosts,
which SNMP will hit more often than most environments realize ("many
modern enterprise networks disable public SNMP entirely," per ARCH-003
2.7).

## Existing Architecture Assessment

Three properties of the current implementation directly shape this
design and are worth stating precisely rather than assumed:

**1. `DiscoveryProvider` has exactly one method and no input.**
[`networkmapper/discovery/provider.py`](../../networkmapper/discovery/provider.py)
defines `discover(self) -> list[Device]` with no parameters. Every
implementation is expected to be fully self-contained — it decides what
to scan, scans it, and returns finished `Device` objects. `NmapProvider`
is constructed with a subnet CIDR and profile; nothing about the
interface expresses "operate on hosts someone else already found."

**2. `DiscoveryEngine` does not merge devices across providers.**
[`networkmapper/discovery/discovery_engine.py`](../../networkmapper/discovery/discovery_engine.py)
`discover()` calls `provider.discover()` for each configured provider,
`extend()`s one flat `all_devices` list, then classifies every device in
that list before inserting each into `NetworkGraph`.
`NetworkGraph.add_device`
([`networkmapper/core/network_graph.py`](../../networkmapper/core/network_graph.py))
is a first-write-wins keyed dict: `if device.ip_address in self._devices:
return`. Today this is harmless because exactly one provider ever runs.
It is not safe to add a second, independent `DiscoveryProvider` that can
produce a `Device` for an IP another provider already produced — the
second one's classification work would run and then be silently
discarded, or (depending on registration order) it would silently win
and drop the first provider's evidence instead. This is not a defect in
the current single-provider system; it is a gap the current interface
was never asked to close, and SNMP is the first thing that would expose
it if bolted on carelessly.

**3. `NmapProvider` already contains the merge pattern this design
needs — just scoped inside one class.**
`_discover_with_enrichment()` builds `devices_by_ip: dict[str, Device]`
from its own host-discovery phase, then writes enrichment results
(`device.services`, `device.operating_system`, `device.computer_name`,
`device.domain`, `device.smb_signing`) into those same objects by
looking them up in that dict. This is exactly the shape SNMP needs — a
phase that receives an existing IP-keyed device set and adds evidence to
it — except NmapProvider's version is private to itself. Promoting this
shape to a boundary `DiscoveryEngine` understands, rather than
reimplementing it a second time inside a new SNMP-specific merge, is the
central proposal in this report (see Proposed SNMP Provider Boundary).

**4. The field-precedence convention already exists and generalizes
cleanly.** `_discover_with_enrichment()`'s SMB/RDP merge is
field-by-field, fallback-only: SMB is preferred when both are present,
RDP "only fills in fields SMB left empty" (see the extensive comment at
[`nmap_provider.py:266-284`](../../networkmapper/discovery/nmap_provider.py)).
The same rule — never overwrite evidence that already exists, only fill
gaps — is the correct precedent for how SNMP evidence should merge into
devices Nmap already populated (see Canonical Evidence Mapping).

**5. ADR-008 does not block this.** ADR-008 ("Discovery is Immutable,
Interpretation is Adjustable") establishes that a recorded observation
is immutable *across* scans — a rescan creates a new observation rather
than silently overwriting a prior one. It does not restrict a single
run's own evidence-gathering pipeline from writing into a `Device` object
incrementally as different sources contribute — that is exactly what
`NmapProvider` already does internally between its own two phases.
Enrichment providers adding evidence to the same run's already-discovered
`Device` objects is consistent with existing practice, not a new
exception to it.

## Proposed SNMP Provider Boundary

Introduce a second abstract provider category alongside
`DiscoveryProvider`:

```python
class EnrichmentProvider(ABC):
    """Adds evidence to already-discovered devices; never discovers them."""

    @abstractmethod
    def enrich(self, devices: Sequence[Device]) -> None:
        """Add evidence to devices in place.

        Implementations must never add a Device for an IP not already
        present in `devices`, never remove a Device, and never raise —
        a failure for one device must be recorded as per-device
        diagnostics and must not stop enrichment of the remaining
        devices. See Failure Model.
        """
        raise NotImplementedError
```

**What it receives:** the full, already-built device set —
`Sequence[Device]` — assembled from every registered `DiscoveryProvider`
before classification runs. This is the same authoritative list
`NmapProvider`'s internal `devices_by_ip` already represents for its own
two phases, just handed to a provider outside `NmapProvider` for the
first time.

**What it returns:** nothing. `enrich()` mutates the `Device` objects it
was given, the same way `_discover_with_enrichment()` already mutates
its own freshly-built devices in place. Diagnostics are exposed the same
way `NmapProvider.run_diagnostics` already is — as a post-run instance
attribute (e.g. `SnmpEnrichmentProvider.run_diagnostics:
SnmpRunDiagnostics | None`), not a return value. This keeps the pattern
identical to the one every existing test and the CLI diagnostics printer
(`Application._print_discovery_diagnostics`) already knows how to
consume.

**Whether it operates on already-discovered hosts:** always. SNMP has no
other mode in this design.

**Whether it ever participates in host discovery:** no, by construction
— `enrich()`'s type signature has no path to introduce a new IP. This is
a deliberate, permanent boundary, not a v1 simplification: sweeping a
subnet for SNMP responders would be a slower, noisier, lower-yield host
discovery mechanism than Nmap's `-sn` ping sweep, and nothing in the
evidence reviewed for this investigation suggests otherwise.

**How failures are isolated:** two layers.
- Per-device: `enrich()` catches every expected SNMP failure mode
  internally (see Failure Model) and never raises for them. A device
  that failed SNMP still has whatever `NmapProvider` (or any other
  discovery provider) already gave it.
- Per-run: `DiscoveryEngine` wraps each `EnrichmentProvider.enrich()`
  call so that even an unexpected exception (a library bug, not a
  protocol-level failure) is caught, logged, and does not prevent
  classification from running on the devices as they stood before that
  provider ran. This mirrors the sprint's own instruction — "a failed
  SNMP query must not break the entire discovery run" — applied at both
  the device and the provider level.

**How the provider remains optional:** `DiscoveryEngine` is constructed
with `providers: Iterable[DiscoveryProvider]` today; this proposal adds
`enrichment_providers: Iterable[EnrichmentProvider] = ()` alongside it.
When no SNMP credentials are supplied, `Application` simply never
constructs `SnmpEnrichmentProvider` and never adds it to that list — the
same "safe no-op when nothing is wired up" pattern `RuntimeEventBus`
already uses for subscribers. No flag, config check, or conditional is
needed inside `DiscoveryEngine` itself.

**Boundary enforcement — no SNMP types leak out:** `SnmpEnrichmentProvider`
takes `SnmpCredentials` and produces only two things visible outside
itself: writes into existing `Device` fields (see Canonical Evidence
Mapping) and an `SnmpRunDiagnostics` object consumed the same way
`RunDiagnostics` is today — by the CLI/telemetry layer, never by
`DeviceClassifier` or any exporter. Classification rules read `Device`
fields only, exactly as they do today; a future SNMP-consuming rule
never needs to know SNMP was the source.

**Orchestration change in `DiscoveryEngine.discover()`:**

```python
def discover(self) -> NetworkGraph:
    graph = NetworkGraph()

    devices_by_ip: dict[str, Device] = {}
    for provider in self._providers:
        for device in provider.discover():
            devices_by_ip.setdefault(device.ip_address, device)

    devices = list(devices_by_ip.values())
    for enrichment_provider in self._enrichment_providers:
        enrichment_provider.enrich(devices)

    self._classify_devices(devices, graph)
    return graph
```

This is a small, additive change to shared orchestration code — it does
not alter `NmapProvider`, `ScanProfile`, or any classification rule, and
the discovery-provider loop's behavior is unchanged for the
single-provider case that exists today. It incidentally also closes the
latent multi-`DiscoveryProvider` collision described in Existing
Architecture Assessment (item 2) by deduplicating on IP before
enrichment and classification, rather than relying on
`NetworkGraph.add_device`'s first-write-wins behavior to do it silently
later. That fix is a side effect of the design, not a goal of this
sprint, and is called out so it isn't mistaken for scope creep.

## SNMP Version Strategy

**v2c — implement first.** Community-string GET semantics, the
operational model ARCH-003/BENCH-002 already scoped this evidence
around ("community string (not real auth)"). Every enterprise SNMP
agent still deployed supports v2c or an SNMPv1-compatible mode under it.

**v1 — not a separate code path.** SNMPv1 and v2c share the same
community-based trust model; the only real differences (v2c's
`GetBulkRequest`, richer error codes) aren't needed for a six-OID
`GetRequest`. Whether v1 is supported is therefore a one-line protocol
version flag on whatever client library is chosen at implementation
time, not a second implementation. If the chosen library makes v1
meaningfully more code than a flag, drop it — no field evidence in this
investigation identifies a device family reachable only via v1 and not
v2c.

**v3 — explicitly deferred, not part of v1.** v3 introduces an
authentication protocol, an authentication secret, a privacy protocol, a
privacy secret, and (structurally) engine-ID discovery — a materially
larger implementation and test surface than a community string, and a
capability this investigation found no evidence-backed urgency for yet
(no BENCH-002/ARCH-003 finding claims v1/v2c-only coverage is
insufficient in practice). Sequencing it as a follow-on sprint after v2c
ships mirrors ARCH-010's own precedent for SNMP: land the smaller,
well-understood piece, verify it against a real environment, then decide
whether the more expensive piece earns its cost. One genuine advantage
v3 has, worth recording even though it's deferred: v3 failures are
usually distinguishable (`usmStats*` counters / report PDUs), unlike
v1/v2c's silent-timeout ambiguity described in Failure Model — a real
argument for eventually adding it, not a reason to add it now.

**Recommendation: v2c only for v1, matching "smallest complete
implementation that provides useful field value."**

## Credential Strategy

**Representation.** A runtime-only dataclass, never a subclass or
extension of anything in `networkmapper.core.models`:

```python
@dataclass(repr=False)
class SnmpCredentials:
    version: SnmpVersion  # V1 | V2C | V3
    community: str | None = None          # v1/v2c
    username: str | None = None           # v3
    auth_protocol: str | None = None      # v3
    auth_secret: str | None = None        # v3
    priv_protocol: str | None = None      # v3
    priv_secret: str | None = None        # v3
```

`repr=False` (with a hand-written `__repr__` that never prints secret
fields) is deliberate — a dataclass's default `repr` prints every field
value, and this object will inevitably end up in a debugger session,
traceback, or `print()` during development if nothing prevents it.

**Where credentials must never appear (all restated from the sprint
brief and made concrete against this codebase):**
- Not in `Device`, `ServiceEvidence`, or any canonical model field.
- Not in `RunMetadata` — REPORT-002 already documents that
  `RunMetadata` gets embedded directly into exported reports "so a
  single Markdown file can stand alone." Credentials must never be
  constructed as, or derived into, a `RunMetadata` field.
- Not in `ObservationScan`/`ObservationEvidence` — KNOW-003's capture
  path (`knowledge/capture.py`) builds `Observation` records from
  `Device` and `RunMetadata` only; if credentials never enter either,
  they structurally cannot reach the knowledge repository.
- Not in any `RuntimeEvent.activity` string — the SNMP phase's activity
  text must describe counts only ("Querying 42 host(s) via SNMP..."),
  never the community string, username, or a target's credential state.
- Not in exception messages surfaced to the CLI or logs — some SNMP
  client libraries embed the request context (occasionally the
  community string) in exception text; `SnmpEnrichmentProvider` must
  catch library exceptions and re-raise/re-log its own diagnostic
  messages rather than propagating library exception text verbatim.

**Supply mechanism.** `networkmapper/config/__init__.py` is currently
empty — there is no existing configuration-file mechanism to extend, and
`ENGINEERING.md`'s Deployment Philosophy calls for "minimal
configuration" and a self-contained, offline tool. Given that, and given
credentials must never persist:

- **Environment variables** (e.g. `NETWORKMAPPER_SNMP_COMMUNITY`,
  `NETWORKMAPPER_SNMPV3_USERNAME`) as the primary mechanism for
  lower-sensitivity values like the community string or v3 username.
  Not visible in shell history the way a CLI argument is, and requires
  no new dependency (`os.environ`).
- **Interactive prompt** (stdlib `getpass`, not echoed, not stored in
  shell history) for v3's `auth_secret`/`priv_secret` specifically, once
  v3 is implemented — these are the two values most analogous to a
  password.
- **CLI plaintext arguments are explicitly discouraged for any secret
  value.** They are visible in shell history and, on multi-user systems,
  in process listings for the duration of the run. Non-secret parameters
  (SNMP version selection, target port, timeout) are fine as CLI flags —
  only the secret-shaped fields are restricted.
- **No config file, this sprint.** If a future sprint adds one for other
  reasons, credentials should still be excluded from it explicitly
  rather than included by default.

This keeps SNMP credential handling entirely additive to
`Application`'s existing `argparse` usage — no new configuration
subsystem, consistent with "avoid dependencies until their value is
demonstrated."

## Evidence / OID Strategy

The MIB-2 **system group** (`1.3.6.1.2.1.1`, OIDs `.1`–`.6`) is the only
evidence this sprint recommends collecting:

| OID | Name | Tier |
|---|---|---|
| `1.3.6.1.2.1.1.1.0` | `sysDescr` | Classification |
| `1.3.6.1.2.1.1.2.0` | `sysObjectID` | Classification (primary) |
| `1.3.6.1.2.1.1.3.0` | `sysUpTime` | Inventory/detail |
| `1.3.6.1.2.1.1.4.0` | `sysContact` | Inventory/detail |
| `1.3.6.1.2.1.1.5.0` | `sysName` | Identity |
| `1.3.6.1.2.1.1.6.0` | `sysLocation` | Inventory/detail |

All six are retrievable in a **single `GetRequest` PDU** — one UDP round
trip per host, regardless of whether all six or fewer are requested.
This is the justification the sprint requires for every proposed query:
the marginal runtime cost of `sysUpTime`/`sysContact`/`sysLocation`
beyond `sysDescr`/`sysObjectID`/`sysName` is zero, because they ride the
same PDU virtually every SNMP agent (v1/v2c/v3, any vendor) implements
as mandatory MIB-2 scalars.

**Not proposed for this sprint, with reasons:**
- **Interface inventory / `ifTable`** — requires `GetNext`/`GetBulk`
  walk operations (one round trip per interface, potentially per row),
  a categorically higher cost than the fixed one-PDU system group, and
  — reconfirming ARCH-003 Section 2.7/Section 3 and BENCH-002 without
  new information — has nowhere to be recorded: `NetworkGraph` has no
  interface/relationship model, and this would require its own ADR
  regardless of SNMP's provider architecture. Out of scope here.
- **Topology evidence (LLDP/CDP-via-SNMP, neighbor tables)** — same
  finding, reconfirmed: relationship data between two devices, not a
  fact about either device in isolation; no representation exists to
  receive it.
- **Vendor-specific enterprise MIBs beyond `sysObjectID` itself** — see
  OID Handling below; explicitly rejected as provider behavior.
- **`snmp-win32-software`/`snmp-processes`-equivalent enumeration** —
  reconfirming ARCH-003's rejection on product-philosophy grounds: host
  software/process audit is not network discovery.

**OID Handling.** The provider's responsibility stops at collecting and
normalizing these six fixed, standard OIDs — it does not interpret
`sysObjectID`'s enterprise-number prefix into a vendor or product guess.
No vendor-specific OID database is embedded in the provider, per the
sprint's explicit instruction. `sysObjectID` is stored verbatim (the
numeric dotted string) as a `Device` field; interpreting it (e.g.
recognizing a `1.3.6.1.4.1.9.*` prefix as Cisco) is classification's job,
via a future rule with a small, curated, evidence-backed lookup table —
the same incremental-keyword-list discipline every existing
classification rule already follows (e.g.
`NetworkApplianceRule.NETWORK_APPLIANCE_VENDOR_KEYWORDS`), grown only as
KNOW-003's Observation → Knowledge → Rule lifecycle corroborates a
specific vendor/OID pairing. This is deliberately not proposed as part
of this sprint's implementation sequence (see Implementation Sequence)
— it is evidence-collection architecture only, and a rule needs
corroborated field data to be written responsibly, which doesn't exist
until the provider itself has shipped.

## Canonical Evidence Mapping

| SNMP value | Destination | New field? | Rationale |
|---|---|---|---|
| `sysName` | `Device.hostname`, fallback-only | No | Reuses the existing field, following the same fallback-only precedent RDP already uses against SMB (`nmap_provider.py:286-291`) — never overwrite a hostname another source already resolved, fill it only when empty. |
| `sysObjectID` | `Device.snmp_sys_object_id` | **Yes** | Reconfirms ARCH-003 Section 3's own conclusion: Device-level, not a new evidence model, does not conflict with ADR-009. A vendor-registered numeric identifier has no existing field to reuse. |
| `sysDescr` | `Device.snmp_sys_descr` | **Yes** | Deliberately **not** folded into `Device.operating_system`, even though some agents' `sysDescr` text resembles an OS caption. `operating_system` today means "an installed OS caption for general-purpose compute," populated only by SMB/RDP identity negotiation. A switch's or printer's `sysDescr` (e.g. "Cisco IOS Software, C2960...", "HP LaserJet 4250, Firmware...") is a device description, not an operating system, and forcing it into that field would dilute a field classification rules already trust for a specific meaning — the same explainability concern ARCH-009's "explicit named fields over a generic container" reasoning already applies elsewhere. A distinct field preserves the existing field's meaning and gives a future classification rule a clean, honestly-named source to match against. |
| `sysUpTime` | `Device.snmp_sys_uptime` | Yes, optional | No classification consumer. Included only because it rides the same free PDU and has direct technician-confidence/documentation value ("this device has been up 47 days" is a hard, measured fact, consistent with OBS-002's "hard metrics only" discipline). Defer the exact final decision to implementation if it's judged not worth the field — see Open Questions. |
| `sysContact` / `sysLocation` | `Device.snmp_sys_contact` / `Device.snmp_sys_location` | Yes, optional | Administrator-entered free text with no classification role, but direct value to the Customer/Account Manager personas `ENGINEERING.md` defines ("Documentation," "Asset inventory"). Same free-PDU justification as `sysUpTime`. |

**Discovery source tracking.** `Device.discovery_sources` already exists
as a list (`NmapProvider` sets `["nmap"]`); `SnmpEnrichmentProvider`
appends `"snmp"` to it for any device it successfully queried, following
the existing convention rather than inventing a new one.

**No canonical model change beyond incremental fields.** This
investigation found no SNMP evidence in scope for v1 that the current
`Device` model cannot represent as a plain named field, consistent with
ADR-009's established pattern and ARCH-003's prior conclusion for this
exact evidence. `ServiceEvidence` is untouched — none of this evidence
is per-port.

## Scan Profile Recommendation

**SNMP is explicit opt-in, orthogonal to `--scan-profile`. It is not
added to FAST, STANDARD, or DEEP — including DEEP.**

Rationale, drawn directly from prior investigations rather than
re-derived:

- **Credentials break the zero-config property every profile currently
  has.** FAST/STANDARD/DEEP are unauthenticated by design (DISC-001
  Finding 6, reaffirmed by ARCH-010's Framing section: any future
  authenticated/credentialed capability "should be its own mode
  alongside DEEP, not layered on top of it"). A community string is
  "not real auth" per ARCH-003, but it is still an operator-supplied
  credential none of the three profiles require today — bundling it in
  would mean the profile silently no-ops or fails for any operator who
  didn't think to supply one.
- **Yield is environment-dependent in a way that punishes bundling.**
  ARCH-003 2.7: "many modern enterprise networks disable public SNMP
  entirely." BENCH-002 and ARCH-010 both already demonstrated, for UDP
  and OS fingerprinting respectively, that a default profile paying a
  real timeout cost for frequently-zero evidence is exactly the failure
  mode DEEP's own diminishing-returns finding warned about. SNMP is a
  second, independent case of the same risk, not a new one.
- **A technician's time onsite is limited** (the sprint's own framing).
  STANDARD is BENCH-002's established default specifically because its
  cost-to-evidence ratio is favorable; adding a variable-yield,
  UDP-timeout-bound phase to it by default would erode that property for
  every run, not just the ones where SNMP is actually useful.

**Recommended mechanism:** a new CLI flag (e.g. `--snmp`) independent of
`--scan-profile`, so `--scan-profile standard --snmp` composes cleanly —
`SnmpEnrichmentProvider` is added to `DiscoveryEngine`'s enrichment
provider list only when the flag is present and credentials resolve
successfully (see Credential Strategy). If credentials are not
resolvable when `--snmp` is passed, this is an operator configuration
error and should fail fast at startup, distinct from a per-host SNMP
failure during the run (see Failure Model).

## Runtime Telemetry Design

Add one new `RuntimePhase` value — `SNMP_ENRICHMENT` — positioned after
`SERVICE_ENRICHMENT` and before `CLASSIFICATION`, matching the
orchestration order in Proposed SNMP Provider Boundary (enrichment
completes before classification runs). No changes to `RuntimeEvent`,
`ProgressMeasurement`, or `RuntimeEventBus` — the existing model already
expresses everything the sprint's own metric list needs:

| Metric | Representation |
|---|---|
| SNMP phase started | `RuntimeEvent(phase=SNMP_ENRICHMENT, kind=PHASE_STARTED)`, `activity="Querying N host(s) via SNMP..."` |
| Hosts eligible | `ProgressMeasurement.total` at phase start — known in advance, same as Service Enrichment's `total_hosts`, since the device set is already fixed by prior discovery/enrichment phases. |
| Hosts queried / responded / timed out | Three separate `PROGRESS` events (or one `ProgressMeasurement` per host as the phase proceeds, mirroring `SERVICE_ENRICHMENT`'s per-host `PROGRESS` events today), each with an honest `unit_label` ("Hosts Queried", "Hosts Responded", "Hosts Timed Out") — never a computed percentage or ETA, per OBS-002's existing constraint. |
| Evidence collected | Expressed the same way Discovery Summary already expresses Nmap evidence coverage (`DiscoverySummary.hosts_with_*` counters) — a follow-on `SnmpDiscoverySummary`-shaped counter set (e.g. `hosts_with_sys_object_id`, `hosts_with_sys_descr`), not a new telemetry primitive. |
| SNMP phase completed / duration | `RuntimeEvent(phase=SNMP_ENRICHMENT, kind=PHASE_COMPLETED)` — `RuntimeTelemetryRecorder` already computes `duration_seconds` from `PHASE_STARTED`/`PHASE_COMPLETED` timestamps for any registered phase with zero SNMP-specific code. |

**Diagnostics object**, following `RunDiagnostics`/`HostDiagnostics`
exactly:

```python
@dataclass
class SnmpHostDiagnostics:
    responded: bool
    fields_returned: list[str]          # which of the six OIDs came back
    failure_reason: str | None          # see Failure Model's categories

@dataclass
class SnmpRunDiagnostics:
    hosts_eligible: int
    hosts_queried: int
    hosts_responded: int
    hosts_timed_out: int
    community_or_version_used: str      # version only — never the secret
    host_diagnostics: dict[str, SnmpHostDiagnostics]
```

This is a new dataclass, not a change to the existing `RunDiagnostics` —
SNMP is a distinct phase with a distinct diagnostics shape, the same way
`HostDiagnostics` is specific to Nmap enrichment rather than generic.
`Application._print_discovery_diagnostics` gains a parallel, SNMP-specific
print block rather than a conditional branch inside the existing one.

## Failure Model

| Condition | Behavior |
|---|---|
| No credentials supplied | `SnmpEnrichmentProvider` is never constructed; no phase, no event, no failure — purely absent. |
| Incorrect community string (v1/v2c) | **Indistinguishable from "host doesn't run SNMP" or "UDP/161 filtered."** SNMPv1/v2c has no authentication-failure response — a bad community string produces silence, identical at the wire level to a non-responding host. Counted as `timed_out`, not a distinct error category. This ambiguity must be stated plainly to the operator (in `profile_message`-style documentation and in the diagnostics output) rather than implied away — the same "hard metrics only" honesty OBS-002 already insists on applies here: NetworkMapper cannot claim to know *why* a host didn't respond under v1/v2c. |
| Unsupported SNMP version requested | Provider-level configuration error, not a per-host failure — fails fast at startup (see Scan Profile Recommendation), since the version is chosen once for the whole run, not per host. |
| Timeout | Counted (`hosts_timed_out`), bounded retry (small, fixed — e.g. 1 retry, per Performance below), then move to the next host. Never blocks other hosts. |
| Unreachable UDP/161 | Same observable behavior as timeout — UDP has no equivalent to TCP's RST-on-closed-port; "unreachable" and "no response within timeout" are the same event from the provider's perspective. |
| Partial response (some OID varbinds return, others error) | Keep whatever succeeded; record which of the six fields came back in `SnmpHostDiagnostics.fields_returned`. SNMPv2c can return per-varbind exception values (`noSuchObject`/`noSuchInstance`) inside an otherwise-successful PDU — this is a legitimate partial-success case, not a failure, and should never discard fields that did return. |
| Malformed response | Caught inside `enrich()`'s per-host loop, recorded as a `failure_reason`, host skipped, loop continues. Never raised. |
| Authorization failure (v3, once implemented) | Distinct diagnostic category from timeout — v3 has real, distinguishable error responses (`usmStats*` counters/report PDUs), unlike v1/v2c's silent ambiguity above. Worth designing `failure_reason` as an open string (not a fixed enum) now, specifically so v3's more granular failure modes have somewhere to go later without a schema change. |

**Governing rule, restated:** `enrich()` never raises for any condition
in this table. A truly unexpected exception (a library defect, not a
protocol-level failure) is the one case `DiscoveryEngine`'s per-provider
wrapper (Proposed SNMP Provider Boundary) exists to catch, so that even
a provider bug degrades to "SNMP contributed nothing this run" rather
than aborting discovery entirely.

## Security Considerations

Restating each item the sprint requires, made concrete against this
codebase:

- **Credential exposure** — structurally prevented rather than filtered:
  `SnmpCredentials` never becomes a field of, or input to constructing,
  `Device`, `ServiceEvidence`, `RunMetadata`, `Observation`, or any
  exporter input. See Credential Strategy.
- **Logs** — `SnmpEnrichmentProvider`'s `_publish()` (mirroring
  `NmapProvider._publish()`) must only ever pass count-based `activity`
  strings, never credential values. Recommend a regression test that
  asserts no `RuntimeEvent.activity` string emitted during an SNMP run
  contains the community string used in that test, closing the gap
  between "designed not to" and "verified it doesn't."
- **Reports** — `MarkdownExporter`/`CsvExporter` read `Device`/`Project`
  only; since credentials never enter those objects, no export code path
  needs to remember to exclude them.
- **Exception messages** — some SNMP client libraries embed request
  context (occasionally the community string) in `str(exception)`.
  `SnmpEnrichmentProvider` must catch library exceptions internally and
  construct its own diagnostic text, never propagate or log a caught
  exception's message verbatim without auditing what the chosen library
  actually includes in it — a concrete task for whichever library is
  selected at implementation time (see Open Questions).
- **Command history** — addressed by preferring environment
  variables/interactive prompts over CLI arguments for secret-shaped
  values (Credential Strategy).
- **Temporary files** — none are introduced by this design; if a chosen
  SNMP library has an optional debug/trace/pcap mode, it must be off by
  default and never enabled by NetworkMapper's own code.
- **Test fixtures** — recommend fixtures use obviously non-production
  values (`"public"`/`"test-community"` community strings, RFC 5737
  documentation-range IPs) so nothing resembling a real credential or
  real customer network ever lands in version control, consistent with
  the synthetic-fixture discipline BENCH-002 already established for its
  own test methodology.

## Performance Considerations

**Serial for v1, deliberately.** `DiscoveryEngine`/`NmapProvider` are
entirely synchronous today — there is no concurrency primitive anywhere
in the runtime to extend. Introducing one for SNMP specifically would be
a new architectural capability, not a small increment, and
`ENGINEERING.md`'s "Benchmark before optimizing" / this sprint's own "do
not optimize prematurely" instruction both argue against speculative
concurrency before a real measurement exists.

**Design for future concurrency without requiring a rewrite.** Structure
the per-host query as a pure, stateless function —
`_query_host(ip: str, credentials: SnmpCredentials, timeout: float) ->
SnmpHostResult` — with no shared mutable state beyond the result it
returns. `enrich()`'s loop then becomes a straightforward candidate for
`concurrent.futures.ThreadPoolExecutor` later (SNMP GETs are
high-latency, low-CPU, and embarrassingly parallel — a textbook
thread-pool workload) without changing the function's signature or the
diagnostics/merge logic around it.

**Timeouts matter more here than anywhere else in the codebase.** Unlike
a closed TCP port (near-instant RST), a firewalled or non-SNMP-speaking
UDP/161 host silently consumes the full timeout on every attempt — and
per ARCH-003, that's the common case in modern enterprise networks. A
conservative, explicit timeout (recommend 1–2s) and a small bounded
retry count (recommend 1) are load-bearing design choices, not tuning
details: on a serial /24 sweep where most hosts don't respond, timeout ×
retry × host count directly is the SNMP phase's total runtime. This is
the single largest realistic performance risk this design carries — see
Risks.

**Cancellation is out of scope for v1.** No cancellation primitive
exists anywhere in the current runtime; adding one for SNMP alone would
be disproportionate to this sprint's scope. Flagged as a real limitation
for large subnets, not silently ignored.

## Testing Strategy

Mirrors the existing `test_nmap_provider_*.py` pattern of mocking the
underlying client rather than depending on a live network — `NmapProvider`'s
tests already mock `nmap.PortScanner`; `SnmpEnrichmentProvider`'s tests
should mock whichever SNMP client library is chosen the same way.

- **Mocked/fixture responses** — canned per-host varbind responses (full
  system-group success, partial response, `noSuchObject` on specific
  OIDs, timeout exception, malformed payload), one fixture per row in
  the Failure Model table.
- **Version-specific behavior** — separate test cases for the v2c code
  path now; v3 test cases added only when v3 itself is implemented, not
  stubbed in ahead of time.
- **Timeout handling** — assert that a device with existing Nmap
  evidence retains that evidence unchanged when its SNMP query times
  out (directly tests the fallback-only merge and failure isolation
  design together).
- **Authentication failures** — deferred to the v3 follow-on sprint,
  since v1/v2c has no authentication-failure case to test (see Failure
  Model).
- **Canonical mapping** — assert `sysDescr`/`sysObjectID`/etc. land in
  their new fields, and specifically that `sysName` and (if a device
  already has one) `operating_system`-adjacent evidence are **not**
  overwritten when already populated — the same fallback-precedence
  test shape FEAT-003H/I already established for SMB/RDP.
- **Telemetry** — assert the `RuntimeEvent` stream for `SNMP_ENRICHMENT`
  never contains the fixture's credential value (the concrete security
  regression test named in Security Considerations), and that
  `ProgressMeasurement` counts match a controlled fixture exactly (N
  eligible, M responded, K timed out).
- **Provider independence** — two tests: (1) `DiscoveryEngine` produces
  an unchanged device set when no `EnrichmentProvider` is registered at
  all (the default case, should require no new behavior); (2) a run
  completes with Nmap-only evidence when the registered
  `SnmpEnrichmentProvider` raises an unexpected exception internally,
  proving the per-provider isolation wrapper actually works.
- **Local SNMP fixture/container** — acknowledged as valuable future
  integration-test infrastructure (a dockerized `net-snmp` daemon would
  let timeout/retry behavior be tested against something that actually
  speaks UDP), but explicitly **not** added this sprint per the sprint's
  own instruction. Revisit once mocked coverage's limits are felt in
  practice, as its own small TEST-00X sprint.

## Implementation Sequence

1. **FEAT-005** — `EnrichmentProvider` contract,
   `DiscoveryEngine` two-phase orchestration change (Proposed SNMP
   Provider Boundary), `SnmpEnrichmentProvider` (v2c only), the six
   system-group `Device` fields, credential handling (env var/prompt),
   `SNMP_ENRICHMENT` telemetry phase, `SnmpRunDiagnostics`, the `--snmp`
   opt-in flag. Serial, no concurrency. This is the "smallest complete
   implementation" this report recommends — everything else below
   depends on it shipping and being run against a real environment
   first.
2. **RULE-00X (follow-on, evidence-gated)** — a classification rule
   consuming `sysObjectID`/`sysDescr`, written only after FEAT-005 has
   produced corroborated field observations through KNOW-003's capture
   path (`should_capture` already scopes automatic capture to `UNKNOWN`
   devices — SNMP-evidenced `UNKNOWN` devices become exactly the
   Observation → Knowledge → Rule input this rule needs), the same
   evidence-gated process RULE-003 already followed for HTTP evidence.
   Not started until FEAT-005 ships.
3. **SNMPv3 (follow-on)** — once v2c's field value is validated,
   scoped as its own architecture-reviewed increment to
   `SnmpCredentials`/`SnmpEnrichmentProvider`, not a v1 feature.
4. **Deferred indefinitely, pending a separate topology/relationship
   ADR** — interface/`ifTable` inventory, LLDP/CDP-via-SNMP. Unaffected
   by whether FEAT-005 ships; reconfirms ARCH-003/BENCH-002 without
   new information.
5. **Deferred, pending measurement** — bounded concurrency for the
   per-host query loop, informed by a future BENCH-00X run against
   FEAT-005's actual measured phase duration in a representative
   environment, mirroring BENCH-002's own role for DEEP.

## Risks

- **v1/v2c failure ambiguity undermines telemetry precision.** "Hosts
  timed out" cannot distinguish wrong-community-string from
  SNMP-disabled from host-down. This must be documented to operators
  plainly (in `profile_message`-equivalent text and diagnostics output),
  not smoothed over — OBS-002's own "hard metrics only" principle is
  only honest if its limits are stated too.
- **Large-subnet runtime risk.** Serial, timeout-bound queries against a
  subnet where most hosts don't run SNMP could make the SNMP phase
  disproportionately slow relative to its own opt-in value proposition —
  directly analogous to BENCH-002's DEEP finding. Should get its own
  BENCH-00X once FEAT-005 exists, not be assumed acceptable.
- **Credential-handling discipline is easy to violate by accident.** A
  single future f-string slip in a diagnostic message could leak a
  secret. The regression test named in Security Considerations/Testing
  Strategy should be treated as a standing requirement for any future
  change to `SnmpEnrichmentProvider`, not a one-time check.
- **The provider-boundary change touches shared orchestration code.**
  `DiscoveryEngine.discover()` is modified even though `NmapProvider`'s
  own behavior is unchanged. This needs its own regression coverage
  (item 2 in Testing Strategy's "provider independence" tests) reviewed
  and passing before SNMP-specific code lands on top of it.
- **OID/vendor interpretation scope creep.** "Add a small vendor OID
  lookup" is an easy first step toward the large embedded OID database
  this report explicitly argues against. Any future `sysObjectID` rule
  must stay evidence-gated (Implementation Sequence item 2), the same
  discipline every existing classification rule's keyword list already
  follows.
- **SNMPv3 is a bigger lift than it looks from the credential field
  list alone.** Engine-ID discovery and auth/priv negotiation are
  protocol machinery, not just extra dataclass fields — treat it as a
  full follow-on sprint, not a v2c sprint extension, per Implementation
  Sequence.

## Open Questions

For architecture review to confirm, not unilaterally decided here:

1. Is an environment variable an acceptable channel for the v1/v2c
   community string specifically (lower sensitivity than a real
   password), or should even that be prompt-only? This report
   recommends env-var-acceptable but flags it as a judgment call.
2. Should `sysUpTime`/`sysContact`/`sysLocation` ship in v1 scope at
   all, given they have asserted-but-unmeasured documentation value and
   zero classification role? This report leans toward including them
   (they're free), but the value claim is not evidence-backed the way
   `sysObjectID`'s classification value is.
3. Final field naming on `Device` (`snmp_sys_descr` vs. an alternative)
   — cosmetic, but should be settled once at implementation time rather
   than iterated across a later refactor.
4. Which SNMP client library to standardize on. Deliberately not decided
   in this architecture sprint ("do not add dependencies"), but
   `ENGINEERING.md`'s Deployment Philosophy ("self-contained Windows
   executable") means the choice should be screened for
   packaging-friendliness (no compiled/C-extension dependency that
   complicates a future standalone build) before FEAT-005 starts, not
   discovered as a blocker mid-implementation.
5. Should the Markdown/CSV report surface "SNMP: not attempted" when the
   `--snmp` flag wasn't used, or stay silent? A reporting-design question
   this SNMP-focused sprint didn't fully scope; worth a decision before
   FEAT-005's report-facing pieces are implemented, given the Markdown
   report's established role as NetworkMapper's primary engineering
   interface (REPORT-001/002).

## ADR Recommendation

**One new ADR is recommended, to be written alongside FEAT-005 (the
same "decided concurrently with, but prior to, the implementation
sprint that needs it" sequencing ADR-009 itself followed) — not before
this report's review, and not silently skipped when implementation
starts:**

**"Enrichment Providers Operate on Already-Discovered Devices"** —
formalizing:
- the `EnrichmentProvider` contract and its structural separation from
  `DiscoveryProvider` (Proposed SNMP Provider Boundary);
- `DiscoveryEngine`'s two-phase discovery-then-enrichment orchestration,
  generalized beyond `NmapProvider`'s internal, previously-private
  pattern;
- the fallback-only, never-overwrite merge rule for evidence fields,
  extending the SMB/RDP precedent (`nmap_provider.py:266-284`) from a
  single provider's internal convention to a project-wide rule any
  future `EnrichmentProvider` (SNMP first, potentially others later)
  must follow.

**No ADR is required for the SNMP canonical evidence fields themselves.**
`sysDescr`/`sysObjectID`/`sysName`/`sysUpTime`/`sysContact`/`sysLocation`
as plain incremental `Device` fields reconfirm, rather than revise,
ADR-009's existing pattern and ARCH-003 Section 3's prior conclusion —
consistent with this sprint's own instruction to change the canonical
model "only if the investigation proves the current model cannot
represent required SNMP evidence cleanly." It can.
