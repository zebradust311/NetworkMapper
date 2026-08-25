"""SNMP ARP-neighbor enrichment provider (ARCH-020; FEAT-010A).

Not an extension of `SnmpEnrichmentProvider` — ARCH-020 Section 8 found
that bundling a table walk into the same opt-in flag as system-group
enrichment would remove a customer's ability to enable one without the
other, and that each provider's own docstring should stay narrowly scoped
to what it actually does.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from networkmapper.core.models import Device
from networkmapper.discovery.enrichment_provider import EnrichmentProvider
from networkmapper.discovery.snmp_arp_diagnostics import SnmpArpHostDiagnostics, SnmpArpRunDiagnostics
from networkmapper.discovery.snmp_client import PysnmpClient, SnmpArpTableResult, SnmpClient
from networkmapper.discovery.snmp_credentials import SnmpCredentials
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.runtime.events import (
    ProgressMeasurement,
    RuntimeEvent,
    RuntimeEventBus,
    RuntimeEventKind,
    RuntimePhase,
)

# ARCH-020 Section 7: a new category, distinct from "connected_to"
# (reserved for LLDP/CDP's stronger, direct physical-adjacency claim) —
# an ARP-table entry claims only that the queried device has resolved
# another IP to a MAC in its own cache, not confirmed physical adjacency.
# Directional, not symmetric: two devices' ARP caches for each other are
# independently-maintained entries that can diverge, not two views of one
# physical fact (unlike an LLDP link).
ARP_NEIGHBOR_CATEGORY = "arp_neighbor"


class SnmpArpNeighborProvider(EnrichmentProvider):
    """Adds ARP-table relationship evidence for already-discovered devices.

    ARCH-020: walks each device's `ipNetToPhysicalTable` (its ARP cache)
    via SNMP and emits one `RelationshipObservation` per IPv4 entry found —
    `subject` is the queried device, `related_subject` is each entry's IP.
    Never touches any `Device` field: ARCH-020 Section 8 found no `Device`
    attribute this evidence maps to. SNMPv2c only, matching
    `SnmpEnrichmentProvider`. Never raises — every per-device failure is
    caught, recorded as diagnostics, and the remaining hosts are still
    queried.

    ARCH-022/FEAT-011A: also emits a `mac_address` `IdentityObservation`
    for each entry, but only when the entry's IP already belongs to the
    independently-discovered device set — never unconditionally, unlike
    the `RelationshipObservation` emission above. An entry for an
    undiscovered IP must not become identity evidence: doing so would let
    this same ARP evidence manufacture a `CanonicalIdentity` for a host
    nothing else confirms exists, which would then let the same evidence
    resolve its own relationship endpoint (ARCH-022 Section 4).
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
        self.run_diagnostics: SnmpArpRunDiagnostics | None = None
        self._observations: list[IdentityObservation | RelationshipObservation] = []

    def enrich(self, devices: Sequence[Device]) -> None:
        """Walk each device's ARP table. Never mutates any `Device` field."""
        total = len(devices)
        self._observations = []
        discovered_ips = {device.ip_address for device in devices}
        run_id = uuid.uuid4().hex
        observed_at = datetime.now()
        self._publish(
            RuntimeEventKind.PHASE_STARTED,
            activity=f"Walking ARP tables via SNMP for {total} host(s)...",
        )

        host_diagnostics: dict[str, SnmpArpHostDiagnostics] = {}
        hosts_responded = 0
        hosts_timed_out = 0

        for index, device in enumerate(devices, start=1):
            result = self._query_host(device.ip_address)

            if result.responded:
                hosts_responded += 1
                self._collect_relationship_observations(device.ip_address, result, run_id, observed_at)
                self._collect_mac_identity_observations(result, discovered_ips, run_id, observed_at)
            else:
                hosts_timed_out += 1

            host_diagnostics[device.ip_address] = SnmpArpHostDiagnostics(
                responded=result.responded,
                entries_returned=len(result.entries),
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

        self.run_diagnostics = SnmpArpRunDiagnostics(
            hosts_eligible=total,
            hosts_queried=total,
            hosts_responded=hosts_responded,
            hosts_timed_out=hosts_timed_out,
            version=self._credentials.version.value,
            host_diagnostics=host_diagnostics,
        )

    def _query_host(self, ip_address: str) -> SnmpArpTableResult:
        """Query one host, catching any unexpected client failure.

        `SnmpClient` implementations are documented to never raise, but
        this is the run-level safety net ARCH-012's Failure Model
        requires regardless — a client defect must degrade to "no
        evidence for this host," never abort the run.
        """
        try:
            return self._client.get_arp_table(
                ip_address, self._credentials, self._timeout, self._retries
            )
        except Exception:
            return SnmpArpTableResult(responded=False, failure_reason="malformed response")

    def collect_observations(self) -> list[IdentityObservation | RelationshipObservation]:
        """Return retained observations from the most recent enrich() call."""
        return list(self._observations)

    def _collect_relationship_observations(
        self,
        ip_address: str,
        result: SnmpArpTableResult,
        run_id: str,
        observed_at: datetime,
    ) -> None:
        for entry in result.entries:
            self._observations.append(
                RelationshipObservation(
                    subject=ip_address,
                    related_subject=entry.ip_address,
                    category=ARP_NEIGHBOR_CATEGORY,
                    provenance=ObservationProvenance(
                        provider="snmp",
                        collection_method="ipNetToPhysicalTable",
                        observed_at=observed_at,
                        source_run=run_id,
                    ),
                )
            )

    def _collect_mac_identity_observations(
        self,
        result: SnmpArpTableResult,
        discovered_ips: set[str],
        run_id: str,
        observed_at: datetime,
    ) -> None:
        """Emit `mac_address` `IdentityObservation`s only for ARP entries
        whose IP already belongs to the independently-discovered device
        set (ARCH-022 Section 4) — gated, unlike the unconditional
        `RelationshipObservation` emission above. An entry for an
        undiscovered IP must not become identity evidence: doing so would
        let this same ARP evidence manufacture a `CanonicalIdentity` for a
        host nothing else confirms exists, which would then let the same
        evidence resolve its own relationship endpoint — the
        endpoint-bootstrapping defect ARCH-022 Section 4 found and this
        gate exists specifically to prevent.
        """
        for entry in result.entries:
            if entry.ip_address not in discovered_ips:
                continue

            self._observations.append(
                IdentityObservation(
                    subject=entry.ip_address,
                    property_name="mac_address",
                    value=entry.mac_address,
                    provenance=ObservationProvenance(
                        provider="snmp",
                        collection_method="ipNetToPhysicalTable",
                        observed_at=observed_at,
                        source_run=run_id,
                    ),
                )
            )

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
