from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from networkmapper.core.models import Device
from networkmapper.discovery.enrichment_provider import EnrichmentProvider
from networkmapper.discovery.snmp_client import PysnmpClient, SnmpClient, SnmpHostResult
from networkmapper.discovery.snmp_credentials import SnmpCredentials
from networkmapper.discovery.snmp_diagnostics import SnmpHostDiagnostics, SnmpRunDiagnostics
from networkmapper.runtime.events import (
    ProgressMeasurement,
    RuntimeEvent,
    RuntimeEventBus,
    RuntimeEventKind,
    RuntimePhase,
)

# ARCH-012 Performance Considerations: unlike a closed TCP port (near-
# instant RST), a firewalled or non-SNMP-speaking UDP/161 host silently
# consumes the full timeout on every attempt — and per ARCH-003, that's
# the common case in modern enterprise networks. These defaults are a
# deliberate, conservative choice given serial, non-concurrent querying.
DEFAULT_TIMEOUT_SECONDS = 1.5
DEFAULT_RETRIES = 1

# ARCH-012 Canonical Evidence Mapping: system-group field name to the
# `Device` attribute it fills. `sysName` is the one field that reuses an
# existing `Device` field (`hostname`) rather than a new SNMP-specific
# one.
_FIELD_TO_DEVICE_ATTRIBUTE = {
    "sysName": "hostname",
    "sysDescr": "snmp_sys_descr",
    "sysObjectID": "snmp_sys_object_id",
    "sysUpTime": "snmp_sys_uptime",
    "sysContact": "snmp_sys_contact",
    "sysLocation": "snmp_sys_location",
}


class SnmpEnrichmentProvider(EnrichmentProvider):
    """Adds MIB-2 system-group SNMP evidence to already-discovered devices.

    ARCH-012/ADR-010: SNMPv2c only. Never discovers hosts. Never raises —
    every per-host failure is caught, recorded as diagnostics, and the
    remaining hosts are still queried.
    """

    def __init__(
        self,
        credentials: SnmpCredentials,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        retries: int = DEFAULT_RETRIES,
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
                without touching the network (per ENGINEERING.md's
                "prefer dependency injection").
        """
        self._credentials = credentials
        self._timeout = timeout
        self._retries = retries
        self._event_bus = event_bus if event_bus is not None else RuntimeEventBus()
        self._client = client if client is not None else PysnmpClient()
        self.run_diagnostics: SnmpRunDiagnostics | None = None

    def enrich(self, devices: Sequence[Device]) -> None:
        """Query each device's MIB-2 system group and merge evidence in place."""
        total = len(devices)
        self._publish(
            RuntimeEventKind.PHASE_STARTED,
            activity=f"Querying {total} host(s) via SNMP...",
        )

        host_diagnostics: dict[str, SnmpHostDiagnostics] = {}
        hosts_responded = 0
        hosts_timed_out = 0

        for index, device in enumerate(devices, start=1):
            result = self._query_host(device.ip_address)

            if result.responded:
                hosts_responded += 1
                self._merge(device, result.fields)
                if "snmp" not in device.discovery_sources:
                    device.discovery_sources.append("snmp")
            else:
                hosts_timed_out += 1

            host_diagnostics[device.ip_address] = SnmpHostDiagnostics(
                responded=result.responded,
                fields_returned=sorted(result.fields),
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

        self.run_diagnostics = SnmpRunDiagnostics(
            hosts_eligible=total,
            hosts_queried=total,
            hosts_responded=hosts_responded,
            hosts_timed_out=hosts_timed_out,
            version=self._credentials.version.value,
            host_diagnostics=host_diagnostics,
        )

    def _query_host(self, ip_address: str) -> SnmpHostResult:
        """Query one host, catching any unexpected client failure.

        `SnmpClient` implementations are documented to never raise, but
        this is the run-level safety net ARCH-012's Failure Model
        requires regardless — a client defect must degrade to "no
        evidence for this host," never abort the run.
        """
        try:
            return self._client.get_system_group(
                ip_address, self._credentials, self._timeout, self._retries
            )
        except Exception:
            return SnmpHostResult(responded=False, failure_reason="malformed response")

    def _merge(self, device: Device, fields: dict[str, str]) -> None:
        """Merge returned fields into a device, fallback-only (ADR-010).

        Never overwrites a field another source already populated —
        generalizes the same precedent `NmapProvider` already uses for
        its SMB/RDP identity merge.
        """
        for field_name, value in fields.items():
            attribute = _FIELD_TO_DEVICE_ATTRIBUTE[field_name]
            if getattr(device, attribute) is None:
                setattr(device, attribute, value)

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
