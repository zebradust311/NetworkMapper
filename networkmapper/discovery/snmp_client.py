from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    EndOfMibView,
    NoSuchInstance,
    NoSuchObject,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd,
)

from networkmapper.discovery.snmp_credentials import SnmpCredentials

SNMP_PORT = 161

# ARCH-012 Evidence/OID Strategy: the six MIB-2 "system group" scalars,
# retrievable in a single GetRequest PDU (one UDP round trip per host,
# regardless of how many of these six are requested). No other OID is
# collected — interface/topology evidence is explicitly out of scope
# (see ARCH-012).
SYSTEM_GROUP_OIDS: tuple[tuple[str, str], ...] = (
    ("sysDescr", "1.3.6.1.2.1.1.1.0"),
    ("sysObjectID", "1.3.6.1.2.1.1.2.0"),
    ("sysUpTime", "1.3.6.1.2.1.1.3.0"),
    ("sysContact", "1.3.6.1.2.1.1.4.0"),
    ("sysName", "1.3.6.1.2.1.1.5.0"),
    ("sysLocation", "1.3.6.1.2.1.1.6.0"),
)

_UNRESOLVED_VALUE_TYPES = (NoSuchObject, NoSuchInstance, EndOfMibView)


@dataclass(frozen=True)
class SnmpHostResult:
    """The outcome of one SNMP system-group query against one host.

    Attributes:
        responded: Whether the host returned at least one usable field.
        fields: System-group field name (e.g. "sysDescr") to its raw
            string value, for every field that came back. May be a
            proper subset of `SYSTEM_GROUP_OIDS` — SNMPv2c can return a
            per-varbind noSuchObject/noSuchInstance exception for
            individual OIDs without failing the whole PDU.
        failure_reason: A short, fixed diagnostic string when
            `responded` is False. Deliberately never derived from a
            caught exception's raw message — see ARCH-012 Security
            Considerations.
    """

    responded: bool
    fields: dict[str, str] = field(default_factory=dict)
    failure_reason: str | None = None


class SnmpClient:
    """Boundary between `SnmpEnrichmentProvider` and the SNMP wire protocol.

    Kept narrow and swappable via dependency injection (per
    ENGINEERING.md's "prefer dependency injection") so provider tests
    mock this contract directly rather than pysnmp internals.
    """

    def get_system_group(
        self,
        host: str,
        credentials: SnmpCredentials,
        timeout: float,
        retries: int,
    ) -> SnmpHostResult:
        """Query one host's MIB-2 system group. Must never raise."""
        raise NotImplementedError


class PysnmpClient(SnmpClient):
    """Default `SnmpClient`, backed by pysnmp's asyncio hlapi (SNMPv2c only)."""

    def get_system_group(
        self,
        host: str,
        credentials: SnmpCredentials,
        timeout: float,
        retries: int,
    ) -> SnmpHostResult:
        try:
            return asyncio.run(self._get(host, credentials, timeout, retries))
        except Exception:
            # A pysnmp-internal or transport-level failure this client
            # did not anticipate. Never propagate the caught exception's
            # message — it could, in principle, echo request context —
            # and never raise out of this method (ARCH-012 Failure Model).
            return SnmpHostResult(responded=False, failure_reason="malformed response")

    async def _get(
        self,
        host: str,
        credentials: SnmpCredentials,
        timeout: float,
        retries: int,
    ) -> SnmpHostResult:
        engine = SnmpEngine()
        target = await UdpTransportTarget.create(
            (host, SNMP_PORT), timeout=timeout, retries=retries
        )
        error_indication, error_status, _error_index, var_binds = await get_cmd(
            engine,
            CommunityData(credentials.community, mpModel=1),  # mpModel=1: SNMPv2c
            target,
            ContextData(),
            *(ObjectType(ObjectIdentity(oid)) for _, oid in SYSTEM_GROUP_OIDS),
        )

        if error_indication:
            # Timeout, unreachable UDP/161, and (for v2c) an incorrect
            # community string are all indistinguishable at this layer —
            # SNMPv2c has no authentication-failure response. See
            # ARCH-012 Failure Model.
            return SnmpHostResult(responded=False, failure_reason="timeout")

        if error_status:
            # A PDU-level error rather than a per-varbind exception value
            # (e.g. a malformed request) — not a case the fixed
            # six-OID system-group GET should trigger in practice, but
            # handled explicitly rather than assumed away.
            return SnmpHostResult(responded=False, failure_reason="protocol error")

        fields: dict[str, str] = {}
        for (name, _oid), var_bind in zip(SYSTEM_GROUP_OIDS, var_binds):
            _, value = var_bind
            if isinstance(value, _UNRESOLVED_VALUE_TYPES):
                continue
            text = str(value).strip()
            if text:
                fields[name] = text

        if not fields:
            return SnmpHostResult(responded=False, failure_reason="empty response")

        return SnmpHostResult(responded=True, fields=fields)
