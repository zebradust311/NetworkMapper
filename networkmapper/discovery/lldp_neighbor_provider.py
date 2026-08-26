"""SNMP LLDP-neighbor enrichment provider (ARCH-023; FEAT-012A).

A new, sibling provider to `SnmpArpNeighborProvider` — not an extension of
it or of `SnmpEnrichmentProvider`. ARCH-023 Section 8 re-applies ARCH-020
Section 8's reasoning for keeping ARP separate from system-group
enrichment to this second, independent table-walk provider, and explicitly
considered and rejected generalizing the provider shape itself (Section
8/10 item 9): two similar providers are not sufficient justification for a
generic table-walk framework at this stage.
"""

from __future__ import annotations

import ipaddress
import uuid
from collections.abc import Sequence
from datetime import datetime

from networkmapper.core.models import Device
from networkmapper.discovery.enrichment_provider import EnrichmentProvider
from networkmapper.discovery.snmp_client import (
    PysnmpClient,
    SnmpClient,
    SnmpLldpNeighborEntry,
    SnmpLldpTableResult,
)
from networkmapper.discovery.snmp_credentials import SnmpCredentials
from networkmapper.discovery.snmp_lldp_diagnostics import SnmpLldpHostDiagnostics, SnmpLldpRunDiagnostics
from networkmapper.identity.mac_index import build_mac_index
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.runtime.events import (
    ProgressMeasurement,
    RuntimeEvent,
    RuntimeEventBus,
    RuntimeEventKind,
    RuntimePhase,
)

# ARCH-023 Section 4: one category regardless of which of the three
# resolution paths (management address, networkAddress chassis ID,
# macAddress chassis ID) produced the row — all three corroborate the
# same underlying physical fact, an LLDP link to this neighbor (a
# reasonable engineering approximation, not a claim the three fields are
# semantically identical). Distinct from "arp_neighbor" (ARCH-020 Section
# 7): ARP and LLDP remain different *kinds* of claims (L3 cache knowledge
# vs. direct L2 protocol adjacency).
LLDP_NEIGHBOR_CATEGORY = "connected_to"

_CHASSIS_ID_SUBTYPE_MAC_ADDRESS = 4
_CHASSIS_ID_SUBTYPE_NETWORK_ADDRESS = 5

_METHOD_MANAGEMENT_ADDRESS = "lldp-management-address"
_METHOD_CHASSIS_NETWORK_ADDRESS = "lldp-chassis-network-address"
_METHOD_CHASSIS_MAC = "lldp-chassis-mac"


class SnmpLldpNeighborProvider(EnrichmentProvider):
    """Adds LLDP-neighbor relationship evidence for already-discovered devices.

    ARCH-023: walks each device's `lldpRemTable`/`lldpRemManAddrTable` via
    SNMP and emits one `RelationshipObservation` per resolved neighbor
    address. Per row, resolution is attempted in priority order (ARCH-023
    Section 6): management addresses first (best-effort, possibly more
    than one — Section 3's multiplicity correction, never arbitrarily
    picking one); only when none resolved, a directly-usable
    `networkAddress`(5) chassis ID; only when that also isn't present, a
    `macAddress`(4) chassis ID resolved via the MAC-to-Subject Reverse
    Index (`build_mac_index()`, fed by `receive_observations()`). The
    remaining five chassis-ID subtypes (ARCH-023 Section 5) are
    permanently unresolvable and produce no `RelationshipObservation` for
    that row. Never touches any `Device` field. SNMPv2c only, matching
    `SnmpArpNeighborProvider`. Never raises — every per-device failure is
    caught, recorded as diagnostics, and the remaining hosts are still
    queried.

    Also emits a gated `hostname` `IdentityObservation` for a resolved
    neighbor already in the independently-discovered device set (ARCH-023
    Section 4, applying ARCH-022 Section 4's endpoint-bootstrapping gate)
    — never for an undiscovered neighbor, for the identical reason
    `SnmpArpNeighborProvider`'s own `mac_address` gate exists: the
    endpoint's existence must already be independently established before
    this evidence corroborates one more property about it.
    """

    def __init__(
        self,
        credentials: SnmpCredentials,
        timeout: float = 1.5,
        retries: int = 1,
        event_bus: RuntimeEventBus | None = None,
        client: SnmpClient | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            credentials: Runtime-only SNMP credentials. Never logged,
                never stored on any returned object.
            timeout: Per-attempt UDP response timeout, in seconds.
            retries: Retry attempts per host after the initial request.
            event_bus: OBS-002 runtime event bus. Defaults to a fresh,
                subscriber-less bus, so publishing is always a safe
                no-op when no caller wires one up.
            client: The SNMP wire-protocol client to use. Defaults to
                `PysnmpClient`; injectable so tests can supply a stub
                without touching the network.
        """
        self._credentials = credentials
        self._timeout = timeout
        self._retries = retries
        self._event_bus = event_bus if event_bus is not None else RuntimeEventBus()
        self._client = client if client is not None else PysnmpClient()
        self.run_diagnostics: SnmpLldpRunDiagnostics | None = None
        self._observations: list[IdentityObservation | RelationshipObservation] = []
        self._received_observations: tuple[IdentityObservation | RelationshipObservation, ...] = ()

    def receive_observations(
        self, observations: tuple[IdentityObservation | RelationshipObservation, ...]
    ) -> None:
        """Store the immutable snapshot this run's `build_mac_index()` call
        will consume (ARCH-023 Section 6). Never a live, mutable
        reference — the same contract every `EnrichmentProvider` receives
        this under (`enrichment_provider.py`)."""
        self._received_observations = observations

    def enrich(self, devices: Sequence[Device]) -> None:
        """Walk each device's LLDP neighbor table. Never mutates any `Device` field."""
        total = len(devices)
        self._observations = []
        discovered_ips = {device.ip_address for device in devices}
        # Computed once per enrich() call, not per row — mirrors
        # SnmpArpNeighborProvider's own once-per-call discovered_ips
        # computation (ARCH-023 Section 6).
        mac_index = build_mac_index(self._received_observations)
        run_id = uuid.uuid4().hex
        observed_at = datetime.now()
        self._publish(
            RuntimeEventKind.PHASE_STARTED,
            activity=f"Walking LLDP neighbor tables via SNMP for {total} host(s)...",
        )

        host_diagnostics: dict[str, SnmpLldpHostDiagnostics] = {}
        hosts_responded = 0
        hosts_timed_out = 0

        for index, device in enumerate(devices, start=1):
            result = self._query_host(device.ip_address)

            if result.responded:
                hosts_responded += 1
                self._collect_observations_for_host(
                    device.ip_address, result, discovered_ips, mac_index, run_id, observed_at
                )
            else:
                hosts_timed_out += 1

            host_diagnostics[device.ip_address] = SnmpLldpHostDiagnostics(
                responded=result.responded,
                entries_returned=len(result.entries),
                management_addresses_returned=sum(
                    len(entry.management_addresses) for entry in result.entries
                ),
                failure_reason=result.failure_reason,
            )

            self._publish(
                RuntimeEventKind.PROGRESS,
                progress=ProgressMeasurement(
                    completed=index, total=total, unit_label="Hosts Queried"
                ),
            )

        self._publish(
            RuntimeEventKind.PHASE_COMPLETED,
            progress=ProgressMeasurement(
                completed=hosts_responded, total=total, unit_label="Hosts Responded"
            ),
        )

        self.run_diagnostics = SnmpLldpRunDiagnostics(
            hosts_eligible=total,
            hosts_queried=total,
            hosts_responded=hosts_responded,
            hosts_timed_out=hosts_timed_out,
            version=self._credentials.version.value,
            host_diagnostics=host_diagnostics,
        )

    def _query_host(self, ip_address: str) -> SnmpLldpTableResult:
        """Query one host, catching any unexpected client failure.

        `SnmpClient` implementations are documented to never raise, but
        this is the run-level safety net ARCH-012's Failure Model requires
        regardless — a client defect must degrade to "no evidence for this
        host," never abort the run. Mirrors
        `SnmpArpNeighborProvider._query_host` exactly.
        """
        try:
            return self._client.get_lldp_neighbors(
                ip_address, self._credentials, self._timeout, self._retries
            )
        except Exception:
            return SnmpLldpTableResult(responded=False, failure_reason="malformed response")

    def collect_observations(self) -> list[IdentityObservation | RelationshipObservation]:
        """Return retained observations from the most recent enrich() call."""
        return list(self._observations)

    def _collect_observations_for_host(
        self,
        ip_address: str,
        result: SnmpLldpTableResult,
        discovered_ips: set[str],
        mac_index: dict[str, frozenset[str]],
        run_id: str,
        observed_at: datetime,
    ) -> None:
        for entry in result.entries:
            for related_subject, collection_method in self._resolve_related_subjects(entry, mac_index):
                self._observations.append(
                    RelationshipObservation(
                        subject=ip_address,
                        related_subject=related_subject,
                        category=LLDP_NEIGHBOR_CATEGORY,
                        provenance=ObservationProvenance(
                            provider="snmp",
                            collection_method=collection_method,
                            observed_at=observed_at,
                            source_run=run_id,
                        ),
                    )
                )

                # ARCH-023 Section 4: applies ARCH-022 Section 4's
                # endpoint-bootstrapping gate — only for a related_subject
                # already independently discovered, and only when this
                # neighbor actually advertised a system name.
                if entry.sys_name and related_subject in discovered_ips:
                    self._observations.append(
                        IdentityObservation(
                            subject=related_subject,
                            property_name="hostname",
                            value=entry.sys_name,
                            provenance=ObservationProvenance(
                                provider="snmp",
                                collection_method=collection_method,
                                observed_at=observed_at,
                                source_run=run_id,
                            ),
                        )
                    )

    def _resolve_related_subjects(
        self, entry: SnmpLldpNeighborEntry, mac_index: dict[str, frozenset[str]]
    ) -> list[tuple[str, str]]:
        """Resolve one `lldpRemTable` row to zero or more `(related_subject,
        collection_method)` pairs, per ARCH-023 Section 6's priority
        order. An ambiguous or absent MAC lookup, an out-of-scope chassis
        network address (e.g. IPv6), or any of the five permanently
        unresolvable chassis-ID subtypes contributes nothing — never an
        error, never a forced placeholder value.
        """
        if entry.management_addresses:
            return [
                (address, _METHOD_MANAGEMENT_ADDRESS) for address in entry.management_addresses
            ]

        if entry.chassis_id_subtype == _CHASSIS_ID_SUBTYPE_NETWORK_ADDRESS:
            # `chassis_id` is only guaranteed IPv4-parseable when the
            # client successfully decoded it as such — an out-of-scope
            # family (e.g. IPv6) is retained as opaque hex, which never
            # parses as an IPv4Address, so this check is what actually
            # declines to resolve it (snmp_client.py's
            # _format_lldp_chassis_id docstring).
            try:
                ipaddress.IPv4Address(entry.chassis_id)
            except ValueError:
                return []
            return [(entry.chassis_id, _METHOD_CHASSIS_NETWORK_ADDRESS)]

        if entry.chassis_id_subtype == _CHASSIS_ID_SUBTYPE_MAC_ADDRESS:
            subjects = mac_index.get(entry.chassis_id, frozenset())
            if len(subjects) == 1:
                return [(next(iter(subjects)), _METHOD_CHASSIS_MAC)]
            return []

        return []

    def _publish(
        self,
        kind: RuntimeEventKind,
        *,
        activity: str | None = None,
        progress: ProgressMeasurement | None = None,
    ) -> None:
        self._event_bus.publish(
            RuntimeEvent(
                phase=RuntimePhase.SNMP_ENRICHMENT,
                kind=kind,
                timestamp=datetime.now(),
                activity=activity,
                progress=progress,
            )
        )
