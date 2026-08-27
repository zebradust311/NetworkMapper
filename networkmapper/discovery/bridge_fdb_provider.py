"""SNMP Bridge-MIB forwarding-table relationship provider (ARCH-024; PLAN-012B; FEAT-012B).

A new, sibling provider to `SnmpArpNeighborProvider`/`SnmpLldpNeighborProvider`
— not an extension of either or of `SnmpEnrichmentProvider`. ARCH-024
Section 8 re-applies ARCH-020/ARCH-023's own reasoning for keeping each
table-walk provider separate to this third, independent case.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from networkmapper.core.models import Device
from networkmapper.discovery.enrichment_provider import EnrichmentProvider
from networkmapper.discovery.snmp_bridge_fdb_diagnostics import (
    SnmpBridgeFdbHostDiagnostics,
    SnmpBridgeFdbRunDiagnostics,
)
from networkmapper.discovery.snmp_client import PysnmpClient, SnmpBridgeFdbResult, SnmpClient
from networkmapper.discovery.snmp_credentials import SnmpCredentials
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

# ARCH-024 Section 5: a new category, distinct from "connected_to" and
# "arp_neighbor" — a forwarding-table entry proves L2 reachability
# through a port, not confirmed direct physical adjacency (an unmanaged
# switch/hub between the queried bridge and the learned MAC is invisible
# to this evidence). Directional, not symmetric, reaffirming ARP's own
# directionality (ARCH-020 Section 6) unmodified.
BRIDGE_FDB_CATEGORY = "bridge_fdb"

# ARCH-024 Section 6: the only dot1dTpFdbStatus value Stage 1 emits
# relationship evidence for. self(4)/mgmt(5)/other(1)/invalid(2)/
# unresolved status (None) are all excluded by this single filter — the
# provider layer's own line of defense against a self(4) row producing a
# self-referential claim (self rows carry status "self", never
# "learned"); RelationshipResolver's own self-loop exclusion
# (relationships/resolver.py) is the second, independent line.
_QUALIFYING_STATUS = "learned"

_METHOD_DOT1D_TP_FDB = "dot1dTpFdbTable"


class SnmpBridgeFdbProvider(EnrichmentProvider):
    """Adds Bridge-MIB forwarding-table relationship evidence for already-discovered devices.

    ARCH-024: walks each device's `dot1dTpFdbTable` (its bridge forwarding
    database) via SNMP and emits one `RelationshipObservation` per
    resolved, `learned`-status row — `subject` is the queried bridge,
    `related_subject` is the subject resolved for the learned MAC via the
    MAC-to-Subject Reverse Index (`build_mac_index()`, fed by
    `receive_observations()`). Never touches any `Device` field. SNMPv2c
    only, matching `SnmpArpNeighborProvider`/`SnmpLldpNeighborProvider`.
    Never raises — every per-device failure is caught, recorded as
    diagnostics, and the remaining hosts are still queried.

    Unlike `SnmpArpNeighborProvider`/`SnmpLldpNeighborProvider`, this
    provider never emits an `IdentityObservation` of any kind (ARCH-024
    Section 5): `dot1dTpFdbTable` carries no identity-bearing field about
    the resolved neighbor at all — no hostname, no management address,
    only a MAC, a port, and a status. Resolution is therefore entirely
    dependent on another source (ARP or Nmap) already having populated
    the reverse index; there is no partial, non-index resolution path the
    way LLDP has one.
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
        self.run_diagnostics: SnmpBridgeFdbRunDiagnostics | None = None
        self._observations: list[IdentityObservation | RelationshipObservation] = []
        self._received_observations: tuple[IdentityObservation | RelationshipObservation, ...] = ()

    def receive_observations(
        self, observations: tuple[IdentityObservation | RelationshipObservation, ...]
    ) -> None:
        """Store the immutable snapshot this run's `build_mac_index()` call
        will consume (ARCH-024 Section 6, reusing ARCH-022's mechanism
        unmodified). Never a live, mutable reference — the same contract
        every `EnrichmentProvider` receives this under (`enrichment_provider.py`)."""
        self._received_observations = observations

    def enrich(self, devices: Sequence[Device]) -> None:
        """Walk each device's Bridge-MIB forwarding table. Never mutates any `Device` field."""
        total = len(devices)
        self._observations = []
        # Computed once per enrich() call, not per row — mirrors
        # SnmpLldpNeighborProvider's own once-per-call mac_index
        # computation (ARCH-024 Section 6).
        mac_index = build_mac_index(self._received_observations)
        run_id = uuid.uuid4().hex
        observed_at = datetime.now()
        self._publish(
            RuntimeEventKind.PHASE_STARTED,
            activity=f"Walking Bridge-MIB forwarding tables via SNMP for {total} host(s)...",
        )

        host_diagnostics: dict[str, SnmpBridgeFdbHostDiagnostics] = {}
        hosts_responded = 0
        hosts_timed_out = 0

        for index, device in enumerate(devices, start=1):
            result = self._query_host(device.ip_address)

            if result.responded:
                hosts_responded += 1
                self._collect_observations_for_host(
                    device.ip_address, result, mac_index, run_id, observed_at
                )
            else:
                hosts_timed_out += 1

            host_diagnostics[device.ip_address] = SnmpBridgeFdbHostDiagnostics(
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

        self.run_diagnostics = SnmpBridgeFdbRunDiagnostics(
            hosts_eligible=total,
            hosts_queried=total,
            hosts_responded=hosts_responded,
            hosts_timed_out=hosts_timed_out,
            version=self._credentials.version.value,
            host_diagnostics=host_diagnostics,
        )

    def _query_host(self, ip_address: str) -> SnmpBridgeFdbResult:
        """Query one host, catching any unexpected client failure.

        `SnmpClient` implementations are documented to never raise, but
        this is the run-level safety net ARCH-012's Failure Model
        requires regardless — a client defect must degrade to "no
        evidence for this host," never abort the run. Mirrors
        `SnmpArpNeighborProvider._query_host`/
        `SnmpLldpNeighborProvider._query_host` exactly.
        """
        try:
            return self._client.get_bridge_fdb(
                ip_address, self._credentials, self._timeout, self._retries
            )
        except Exception:
            return SnmpBridgeFdbResult(responded=False, failure_reason="malformed response")

    def collect_observations(self) -> list[IdentityObservation | RelationshipObservation]:
        """Return retained observations from the most recent enrich() call."""
        return list(self._observations)

    def _collect_observations_for_host(
        self,
        ip_address: str,
        result: SnmpBridgeFdbResult,
        mac_index: dict[str, frozenset[str]],
        run_id: str,
        observed_at: datetime,
    ) -> None:
        for entry in result.entries:
            if entry.status != _QUALIFYING_STATUS:
                # ARCH-024 Section 6: self(4)/mgmt(5)/other(1)/invalid(2)/
                # unresolved status (None) all excluded here, never an
                # error.
                continue

            subjects = mac_index.get(entry.mac_address, frozenset())
            if len(subjects) != 1:
                # Absent (len == 0) or ambiguous (len > 1) — contributes
                # nothing, never an error (ARCH-022 Section 5's own
                # caller-decision recommendation, reused unmodified).
                continue

            self._observations.append(
                RelationshipObservation(
                    subject=ip_address,
                    related_subject=next(iter(subjects)),
                    category=BRIDGE_FDB_CATEGORY,
                    provenance=ObservationProvenance(
                        provider="snmp",
                        collection_method=_METHOD_DOT1D_TP_FDB,
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
