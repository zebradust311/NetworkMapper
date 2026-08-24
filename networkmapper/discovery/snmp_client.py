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
    walk_cmd,
)

from networkmapper.discovery.snmp_credentials import SnmpCredentials

SNMP_PORT = 161

# ARCH-020 Section 5/6: IP-MIB (RFC 4293) ipNetToPhysicalTable columns.
# PhysAddress (the MAC) and Type (dynamic/static/...) are walked as two
# separate GETNEXT subtree walks and joined by their shared row index
# (ifIndex, addressType, addressLength, address-octets...) — IP-MIB has no
# single column carrying both. IPv4 only for Stage 1 (ARCH-020 Section
# 5): a row's addressType must be 1; any other value (IPv6, dns, etc.) is
# skipped, never an error.
IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID = "1.3.6.1.2.1.4.35.1.4"
IP_NET_TO_PHYSICAL_TYPE_OID = "1.3.6.1.2.1.4.35.1.6"
_IPV4_ADDRESS_TYPE = 1

# ARCH-020 Section 12's own named risk (a table walk against a core
# router is materially larger than the fixed six-OID system-group GET) —
# this bounds a single host's walk rather than leaving it unbounded.
ARP_TABLE_MAX_ROWS = 10_000

_ARP_ENTRY_TYPE_NAMES: dict[int, str] = {
    1: "other",
    2: "invalid",
    3: "dynamic",
    4: "static",
    5: "local",
}

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


@dataclass(frozen=True)
class SnmpArpTableEntry:
    """One row of a device's `ipNetToPhysicalTable` (its ARP cache).

    Attributes:
        interface_index: The `ifIndex` this entry was learned on.
        ip_address: The IPv4 address this entry resolves — already in the
            same subject-reference namespace `IdentityObservation.subject`
            uses (ARCH-018 Section 1's translation requirement; ARCH-020
            Section 6 reconfirms it against this table's real shape).
        mac_address: The resolved MAC address, formatted as
            colon-separated hex (e.g. "AA:BB:CC:DD:EE:FF").
        entry_type: "other"/"invalid"/"dynamic"/"static"/"local", or
            `None` if the agent's response didn't include a matching
            `ipNetToPhysicalType` row for this entry. Retained per
            ARCH-020 Section 6 even though nothing consumes it yet.
    """

    interface_index: int
    ip_address: str
    mac_address: str
    entry_type: str | None = None


@dataclass(frozen=True)
class SnmpArpTableResult:
    """The outcome of one `ipNetToPhysicalTable` walk against one host.

    Attributes:
        responded: Whether the walk completed successfully. `True` even
            when `entries` is empty — an empty ARP table is a legitimate
            result for a real, responding device (ARCH-020 Section
            5/`get_arp_table`'s own docstring), unlike
            `SnmpHostResult.responded`, where zero system-group fields
            does indicate non-response.
        entries: Every IPv4 entry found, in no particular order.
        failure_reason: A short, fixed diagnostic string when `responded`
            is False. Deliberately never derived from a caught exception's
            raw message — see ARCH-012 Security Considerations.
    """

    responded: bool
    entries: list[SnmpArpTableEntry] = field(default_factory=list)
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

    def get_arp_table(
        self,
        host: str,
        credentials: SnmpCredentials,
        timeout: float,
        retries: int,
    ) -> SnmpArpTableResult:
        """Walk one host's `ipNetToPhysicalTable` (ARCH-020). Must never raise."""
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

    def get_arp_table(
        self,
        host: str,
        credentials: SnmpCredentials,
        timeout: float,
        retries: int,
    ) -> SnmpArpTableResult:
        try:
            return asyncio.run(self._get_arp_table(host, credentials, timeout, retries))
        except Exception:
            # Mirrors get_system_group's identical safety net (ARCH-012
            # Failure Model): never propagate a caught exception's message,
            # never raise out of this method.
            return SnmpArpTableResult(responded=False, failure_reason="malformed response")

    async def _get_arp_table(
        self,
        host: str,
        credentials: SnmpCredentials,
        timeout: float,
        retries: int,
    ) -> SnmpArpTableResult:
        engine = SnmpEngine()
        target = await UdpTransportTarget.create(
            (host, SNMP_PORT), timeout=timeout, retries=retries
        )
        auth_data = CommunityData(credentials.community, mpModel=1)  # mpModel=1: SNMPv2c

        mac_by_key = await self._walk_column(
            engine, auth_data, target, IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID
        )
        if mac_by_key is None:
            # The PhysAddress walk is required — its failure is the
            # host's failure. Timeout and an unreachable/non-SNMP-speaking
            # host are indistinguishable at this layer, exactly as
            # get_system_group's own comment already documents.
            return SnmpArpTableResult(responded=False, failure_reason="timeout")

        # The Type walk is best-effort (ARCH-020 Section 6: retained but
        # not gated on). Its failure never fails the whole result — a
        # missing Type column still leaves every entry's mac_address
        # usable, with entry_type defaulting to None.
        type_by_key = await self._walk_column(
            engine, auth_data, target, IP_NET_TO_PHYSICAL_TYPE_OID
        ) or {}

        entries = [
            SnmpArpTableEntry(
                interface_index=if_index,
                ip_address=ip_address,
                mac_address=_format_mac(mac_value),
                entry_type=_ARP_ENTRY_TYPE_NAMES.get(_as_int(type_by_key.get((if_index, ip_address)))),
            )
            for (if_index, ip_address), mac_value in mac_by_key.items()
        ]

        return SnmpArpTableResult(responded=True, entries=entries)

    async def _walk_column(
        self,
        engine: SnmpEngine,
        auth_data: CommunityData,
        target: UdpTransportTarget,
        column_oid: str,
    ) -> dict[tuple[int, str], object] | None:
        """Walk one `ipNetToPhysicalTable` column, keyed by (ifIndex, ip_address).

        Returns `None` on any walk-level failure (timeout, transport
        error, protocol error) so the caller can distinguish "walk
        failed" from "walk succeeded with zero rows" — the same
        distinction `SnmpArpTableResult.responded` makes at the whole-host
        level, applied here per column.

        `lookupMib=False`: this codebase has no precedent for parsing a
        *returned* OID's index suffix — every existing SNMP interaction
        (`get_system_group`) only ever sends fixed, known OIDs and reads
        values positionally, never inspecting a response's OID. Forcing
        numeric-only OID rendering removes any dependency on which MIB
        modules happen to be installed in a given environment, which
        would otherwise make `str(name)`'s exact format
        environment-dependent. This is the one piece of this
        implementation without a live-network validation; Section 12's
        "no real evidence source exists yet" caveat applies here directly.
        """
        values_by_key: dict[tuple[int, str], object] = {}
        async for error_indication, error_status, _error_index, var_binds in walk_cmd(
            engine,
            auth_data,
            target,
            ContextData(),
            ObjectType(ObjectIdentity(column_oid)),
            lexicographicMode=False,
            maxRows=ARP_TABLE_MAX_ROWS,
            lookupMib=False,
        ):
            if error_indication or error_status:
                return None

            for name, value in var_binds:
                if isinstance(value, _UNRESOLVED_VALUE_TYPES):
                    continue
                parsed = _parse_ipv4_arp_row(str(name), column_oid)
                if parsed is None:
                    continue
                values_by_key[parsed] = value

        return values_by_key


def _parse_ipv4_arp_row(oid_str: str, column_oid: str) -> tuple[int, str] | None:
    """Parse one `ipNetToPhysicalTable` row's OID into `(ifIndex, ip_address)`.

    Row index: `{ ifIndex, addressType, addressLength, address-octets... }`
    (RFC 4293). Returns `None` for a non-IPv4 row (`addressType != 1`) or
    a malformed/unexpected OID shape — both are silently skipped, per
    ARCH-020's "never an error, only excluded" posture for evidence that
    doesn't fit this provider's IPv4-only Stage 1 scope.
    """
    prefix = column_oid + "."
    if not oid_str.startswith(prefix):
        return None

    try:
        components = [int(part) for part in oid_str[len(prefix):].split(".")]
    except ValueError:
        return None

    if len(components) < 3:
        return None

    if_index, address_type, address_length = components[0], components[1], components[2]
    if address_type != _IPV4_ADDRESS_TYPE or address_length != 4:
        return None

    octets = components[3 : 3 + address_length]
    if len(octets) != address_length or any(not (0 <= octet <= 255) for octet in octets):
        return None

    return if_index, ".".join(str(octet) for octet in octets)


def _format_mac(value: object) -> str:
    """Format a `PhysAddress` (OCTET STRING) varbind value as colon-hex."""
    return ":".join(f"{byte:02X}" for byte in bytes(value))


def _as_int(value: object) -> int:
    """Coerce a `Type` column varbind value to `int`; `-1` if absent/unusable."""
    if value is None:
        return -1
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1
