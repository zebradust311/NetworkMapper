import unittest
from unittest.mock import AsyncMock, patch

from pysnmp.hlapi.v3arch.asyncio import NoSuchInstance, NoSuchObject

from networkmapper.discovery.snmp_client import (
    DOT1D_TP_FDB_PORT_OID,
    DOT1D_TP_FDB_STATUS_OID,
    IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID,
    IP_NET_TO_PHYSICAL_TYPE_OID,
    LLDP_REM_CHASSIS_ID_OID,
    LLDP_REM_CHASSIS_ID_SUBTYPE_OID,
    LLDP_REM_MAN_ADDR_IF_SUBTYPE_OID,
    LLDP_REM_PORT_DESC_OID,
    LLDP_REM_PORT_ID_OID,
    LLDP_REM_PORT_ID_SUBTYPE_OID,
    LLDP_REM_SYS_CAP_ENABLED_OID,
    LLDP_REM_SYS_CAP_SUPPORTED_OID,
    LLDP_REM_SYS_DESC_OID,
    LLDP_REM_SYS_NAME_OID,
    PysnmpClient,
    SYSTEM_GROUP_OIDS,
)
from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion

_CREDENTIALS = SnmpCredentials(version=SnmpVersion.V2C, community="public")


def _var_binds(values: list) -> list:
    """Build a var_binds list matching SYSTEM_GROUP_OIDS's order and length."""
    return [(name, value) for (name, _oid), value in zip(SYSTEM_GROUP_OIDS, values)]


def _walk_cmd_side_effect(responses_per_call: list[list[tuple]]):
    """Build a `walk_cmd` replacement returning a fresh async generator per
    call, yielding `responses_per_call[call_index]` in order.

    `get_arp_table()` calls `walk_cmd()` twice per host (PhysAddress, then
    Type) — this lets a test control each walk's response independently,
    including a walk that fails or a walk that returns zero rows, without
    needing any real pysnmp response-resolution machinery (this codebase
    has no precedent for inspecting a *returned* OID, so fixtures use
    plain OID strings, matching how var_binds' values only ever need to
    support `bytes()`/`int()` — plain `bytes`/`int` fixtures work exactly
    like a real varbind value would).
    """
    call_index = {"n": 0}

    def side_effect(*_args, **_kwargs):
        index = call_index["n"]
        call_index["n"] += 1
        events = responses_per_call[index] if index < len(responses_per_call) else []

        async def _generator():
            for event in events:
                yield event

        return _generator()

    return side_effect


class PysnmpClientTest(unittest.TestCase):
    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.get_cmd", new_callable=AsyncMock)
    def test_successful_response_returns_all_fields(self, get_cmd_mock, _target_mock):
        get_cmd_mock.return_value = (
            None,
            0,
            0,
            _var_binds(
                [
                    "Cisco IOS Software, C2960",
                    "1.3.6.1.4.1.9.1.516",
                    "12345",
                    "netops@example.com",
                    "sw-core-01",
                    "Server Room A",
                ]
            ),
        )

        result = PysnmpClient().get_system_group("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertIsNone(result.failure_reason)
        self.assertEqual(result.fields["sysDescr"], "Cisco IOS Software, C2960")
        self.assertEqual(result.fields["sysObjectID"], "1.3.6.1.4.1.9.1.516")
        self.assertEqual(result.fields["sysName"], "sw-core-01")

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.get_cmd", new_callable=AsyncMock)
    def test_timeout_is_reported_as_not_responded(self, get_cmd_mock, _target_mock):
        get_cmd_mock.return_value = (Exception("No SNMP response received before timeout"), 0, 0, ())

        result = PysnmpClient().get_system_group("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "timeout")
        self.assertEqual(result.fields, {})

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.get_cmd", new_callable=AsyncMock)
    def test_pdu_level_error_status_is_reported_as_not_responded(self, get_cmd_mock, _target_mock):
        get_cmd_mock.return_value = (None, 1, 0, ())

        result = PysnmpClient().get_system_group("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "protocol error")

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.get_cmd", new_callable=AsyncMock)
    def test_partial_response_keeps_returned_fields_and_skips_unresolved_ones(
        self, get_cmd_mock, _target_mock
    ):
        get_cmd_mock.return_value = (
            None,
            0,
            0,
            _var_binds(
                [
                    "A generic appliance",
                    NoSuchObject(),
                    "999",
                    NoSuchInstance(),
                    "appliance-01",
                    NoSuchObject(),
                ]
            ),
        )

        result = PysnmpClient().get_system_group("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(
            set(result.fields), {"sysDescr", "sysUpTime", "sysName"}
        )

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.get_cmd", new_callable=AsyncMock)
    def test_no_usable_fields_is_reported_as_not_responded(self, get_cmd_mock, _target_mock):
        get_cmd_mock.return_value = (
            None, 0, 0, _var_binds([NoSuchObject()] * 6)
        )

        result = PysnmpClient().get_system_group("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "empty response")

    @patch(
        "networkmapper.discovery.snmp_client.UdpTransportTarget.create",
        new_callable=AsyncMock,
        side_effect=RuntimeError("unexpected transport failure"),
    )
    def test_unexpected_exception_never_propagates(self, _target_mock):
        result = PysnmpClient().get_system_group("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "malformed response")
        self.assertNotIn("unexpected transport failure", (result.failure_reason or ""))


class PysnmpClientArpTableTest(unittest.TestCase):
    """ARCH-020 / FEAT-010A."""

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_successful_walk_joins_physaddress_and_type_by_row_index(
        self, walk_cmd_mock, _target_mock
    ):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                # PhysAddress walk: one row, ifIndex=1, IPv4 192.168.1.10.
                [
                    (
                        None,
                        0,
                        0,
                        [(f"{IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID}.1.1.4.192.168.1.10", b"\xaa\xbb\xcc\xdd\xee\xff")],
                    )
                ],
                # Type walk: the same row, type 3 (dynamic).
                [(None, 0, 0, [(f"{IP_NET_TO_PHYSICAL_TYPE_OID}.1.1.4.192.168.1.10", 3)])],
            ]
        )

        result = PysnmpClient().get_arp_table("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertIsNone(result.failure_reason)
        self.assertEqual(len(result.entries), 1)
        entry = result.entries[0]
        self.assertEqual(entry.interface_index, 1)
        self.assertEqual(entry.ip_address, "192.168.1.10")
        self.assertEqual(entry.mac_address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(entry.entry_type, "dynamic")

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_multiple_rows_are_all_returned(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                [
                    (
                        None,
                        0,
                        0,
                        [
                            (f"{IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID}.1.1.4.192.168.1.10", b"\x00" * 6),
                            (f"{IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID}.1.1.4.192.168.1.11", b"\x11" * 6),
                        ],
                    )
                ],
                [(None, 0, 0, [])],
            ]
        )

        result = PysnmpClient().get_arp_table("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual({entry.ip_address for entry in result.entries}, {"192.168.1.10", "192.168.1.11"})

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_a_row_missing_from_the_type_walk_defaults_entry_type_to_none(
        self, walk_cmd_mock, _target_mock
    ):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                [
                    (
                        None,
                        0,
                        0,
                        [(f"{IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID}.1.1.4.192.168.1.10", b"\xaa" * 6)],
                    )
                ],
                [(None, 0, 0, [])],  # Type walk returns nothing for this row.
            ]
        )

        result = PysnmpClient().get_arp_table("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertIsNone(result.entries[0].entry_type)

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_an_ipv6_row_is_skipped_not_erroring(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                [
                    (
                        None,
                        0,
                        0,
                        [
                            # addressType=2 (ipv6), addressLength=16 — skipped.
                            (
                                f"{IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID}.1.2.16."
                                + ".".join(["0"] * 16),
                                b"\xaa" * 6,
                            ),
                            (f"{IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID}.1.1.4.192.168.1.10", b"\xbb" * 6),
                        ],
                    )
                ],
                [(None, 0, 0, [])],
            ]
        )

        result = PysnmpClient().get_arp_table("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(result.entries[0].ip_address, "192.168.1.10")

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_zero_rows_is_a_legitimate_responded_result(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect([[(None, 0, 0, [])], [(None, 0, 0, [])]])

        result = PysnmpClient().get_arp_table("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(result.entries, [])
        self.assertIsNone(result.failure_reason)

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_physaddress_walk_error_indication_is_reported_as_timeout(
        self, walk_cmd_mock, _target_mock
    ):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [[(Exception("No SNMP response received before timeout"), 0, 0, [])]]
        )

        result = PysnmpClient().get_arp_table("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "timeout")
        self.assertEqual(result.entries, [])

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_type_walk_failure_does_not_fail_the_whole_result(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                [
                    (
                        None,
                        0,
                        0,
                        [(f"{IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID}.1.1.4.192.168.1.10", b"\xaa" * 6)],
                    )
                ],
                [(Exception("timeout"), 0, 0, [])],  # Type walk fails; best-effort.
            ]
        )

        result = PysnmpClient().get_arp_table("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertIsNone(result.entries[0].entry_type)

    @patch(
        "networkmapper.discovery.snmp_client.UdpTransportTarget.create",
        new_callable=AsyncMock,
        side_effect=RuntimeError("unexpected transport failure"),
    )
    def test_unexpected_exception_never_propagates(self, _target_mock):
        result = PysnmpClient().get_arp_table("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "malformed response")
        self.assertNotIn("unexpected transport failure", (result.failure_reason or ""))


_LLDP_WALK_ORDER = (
    "chassis_id_subtype",
    "chassis_id",
    "port_id_subtype",
    "port_id",
    "port_desc",
    "sys_name",
    "sys_desc",
    "sys_cap_supported",
    "sys_cap_enabled",
    "man_addr",
)


def _lldp_walks(**overrides: list[tuple]) -> list[list[tuple]]:
    """Build the 10-walk sequence `get_lldp_neighbors()` issues, in the
    exact order it issues them (`_get_lldp_neighbors`), defaulting every
    unspecified walk to a single empty, successful response. Keyword
    names match `_LLDP_WALK_ORDER`.
    """
    return [overrides.get(name, [(None, 0, 0, [])]) for name in _LLDP_WALK_ORDER]


class PysnmpClientLldpNeighborTest(unittest.TestCase):
    """ARCH-023 / FEAT-012A."""

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_macaddress_subtype_resolves(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(
                chassis_id_subtype=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_SUBTYPE_OID}.0.1.1", 4)])],
                chassis_id=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_OID}.0.1.1", b"\xaa\xbb\xcc\xdd\xee\xff")])],
            )
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertIsNone(result.failure_reason)
        self.assertEqual(len(result.entries), 1)
        entry = result.entries[0]
        self.assertEqual(entry.local_port_num, 1)
        self.assertEqual(entry.rem_index, 1)
        self.assertEqual(entry.chassis_id_subtype, 4)
        self.assertEqual(entry.chassis_id, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(entry.management_addresses, [])

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_networkaddress_subtype_resolves_ipv4(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(
                chassis_id_subtype=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_SUBTYPE_OID}.0.1.1", 5)])],
                chassis_id=[
                    (None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_OID}.0.1.1", bytes([1, 192, 168, 1, 10]))])
                ],
            )
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        entry = result.entries[0]
        self.assertEqual(entry.chassis_id_subtype, 5)
        self.assertEqual(entry.chassis_id, "192.168.1.10")

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_networkaddress_subtype_non_ipv4_family_retained_as_hex(self, walk_cmd_mock, _target_mock):
        # family=2 (IPv6, per the standard address-family numbering) —
        # retained as opaque hex, never dot-formatted, never mistaken for
        # a resolved IPv4 string downstream (ARCH-023 Section 5).
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(
                chassis_id_subtype=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_SUBTYPE_OID}.0.1.1", 5)])],
                chassis_id=[
                    (None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_OID}.0.1.1", bytes([2] + [0xFE, 0x80] + [0] * 14))])
                ],
            )
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertNotIn(".", result.entries[0].chassis_id)

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_non_resolvable_subtype_is_still_retained(self, walk_cmd_mock, _target_mock):
        # interfaceName(6) — not resolvable, but the row is still built
        # (ARCH-023 Section 5): resolvability is a provider-layer decision.
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(
                chassis_id_subtype=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_SUBTYPE_OID}.0.1.1", 6)])],
                chassis_id=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_OID}.0.1.1", b"Gi0/1")])],
            )
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(result.entries[0].chassis_id_subtype, 6)

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_malformed_macaddress_length_is_skipped(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(
                chassis_id_subtype=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_SUBTYPE_OID}.0.1.1", 4)])],
                chassis_id=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_OID}.0.1.1", b"\xaa\xbb\xcc")])],
            )
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(result.entries, [])

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_a_row_missing_from_the_chassis_id_walk_is_skipped(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(
                chassis_id_subtype=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_SUBTYPE_OID}.0.1.1", 4)])],
                chassis_id=[(None, 0, 0, [])],
            )
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(result.entries, [])

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_management_address_multiplicity(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(
                chassis_id_subtype=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_SUBTYPE_OID}.0.1.1", 4)])],
                chassis_id=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_OID}.0.1.1", b"\xaa" * 6)])],
                man_addr=[
                    (
                        None,
                        0,
                        0,
                        [
                            (f"{LLDP_REM_MAN_ADDR_IF_SUBTYPE_OID}.0.1.1.1.4.10.0.0.5", 1),
                            (f"{LLDP_REM_MAN_ADDR_IF_SUBTYPE_OID}.0.1.1.1.4.10.0.0.6", 1),
                        ],
                    )
                ],
            )
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(set(result.entries[0].management_addresses), {"10.0.0.5", "10.0.0.6"})

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_management_address_walk_failure_does_not_fail_the_host(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(
                chassis_id_subtype=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_SUBTYPE_OID}.0.1.1", 4)])],
                chassis_id=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_OID}.0.1.1", b"\xaa" * 6)])],
                man_addr=[(Exception("timeout"), 0, 0, [])],
            )
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(result.entries[0].management_addresses, [])

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_best_effort_column_failure_leaves_field_absent(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(
                chassis_id_subtype=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_SUBTYPE_OID}.0.1.1", 4)])],
                chassis_id=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_OID}.0.1.1", b"\xaa" * 6)])],
                sys_name=[(Exception("timeout"), 0, 0, [])],
            )
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertIsNone(result.entries[0].sys_name)

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_chassis_id_subtype_walk_failure_fails_the_host(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(chassis_id_subtype=[(Exception("timeout"), 0, 0, [])])
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "timeout")
        self.assertEqual(result.entries, [])

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_chassis_id_walk_failure_fails_the_host(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            _lldp_walks(
                chassis_id_subtype=[(None, 0, 0, [(f"{LLDP_REM_CHASSIS_ID_SUBTYPE_OID}.0.1.1", 4)])],
                chassis_id=[(Exception("timeout"), 0, 0, [])],
            )
        )

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "timeout")

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_zero_rows_is_a_legitimate_responded_result(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(_lldp_walks())

        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(result.entries, [])
        self.assertIsNone(result.failure_reason)

    @patch(
        "networkmapper.discovery.snmp_client.UdpTransportTarget.create",
        new_callable=AsyncMock,
        side_effect=RuntimeError("unexpected transport failure"),
    )
    def test_unexpected_exception_never_propagates(self, _target_mock):
        result = PysnmpClient().get_lldp_neighbors("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "malformed response")
        self.assertNotIn("unexpected transport failure", (result.failure_reason or ""))


# AA:BB:CC:DD:EE:FF and BB:CC:DD:EE:FF:00, as dot1dTpFdbTable's own
# 6-octet index suffix.
_MAC_A_OCTETS = "170.187.204.221.238.255"
_MAC_B_OCTETS = "187.204.221.238.255.0"


class PysnmpClientBridgeFdbTest(unittest.TestCase):
    """ARCH-024 / PLAN-012B / FEAT-012B."""

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_successful_walk_joins_port_and_status_by_mac(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                [(None, 0, 0, [(f"{DOT1D_TP_FDB_PORT_OID}.{_MAC_A_OCTETS}", 4)])],
                [(None, 0, 0, [(f"{DOT1D_TP_FDB_STATUS_OID}.{_MAC_A_OCTETS}", 3)])],
            ]
        )

        result = PysnmpClient().get_bridge_fdb("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertIsNone(result.failure_reason)
        self.assertEqual(len(result.entries), 1)
        entry = result.entries[0]
        self.assertEqual(entry.mac_address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(entry.port, 4)
        self.assertEqual(entry.status, "learned")

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_multiple_rows_are_all_returned(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                [
                    (
                        None,
                        0,
                        0,
                        [
                            (f"{DOT1D_TP_FDB_PORT_OID}.{_MAC_A_OCTETS}", 4),
                            (f"{DOT1D_TP_FDB_PORT_OID}.{_MAC_B_OCTETS}", 7),
                        ],
                    )
                ],
                [(None, 0, 0, [])],
            ]
        )

        result = PysnmpClient().get_bridge_fdb("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(
            {entry.mac_address for entry in result.entries},
            {"AA:BB:CC:DD:EE:FF", "BB:CC:DD:EE:FF:00"},
        )

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_a_row_missing_from_the_status_walk_leaves_status_none(
        self, walk_cmd_mock, _target_mock
    ):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                [(None, 0, 0, [(f"{DOT1D_TP_FDB_PORT_OID}.{_MAC_A_OCTETS}", 4)])],
                [(None, 0, 0, [])],  # Status walk returns nothing for this row.
            ]
        )

        result = PysnmpClient().get_bridge_fdb("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertIsNone(result.entries[0].status)

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_a_malformed_row_index_not_six_octets_is_skipped(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                [
                    (
                        None,
                        0,
                        0,
                        [
                            # Only 5 octets — malformed, skipped.
                            (f"{DOT1D_TP_FDB_PORT_OID}.170.187.204.221.238", 4),
                            (f"{DOT1D_TP_FDB_PORT_OID}.{_MAC_A_OCTETS}", 4),
                        ],
                    )
                ],
                [(None, 0, 0, [])],
            ]
        )

        result = PysnmpClient().get_bridge_fdb("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(result.entries[0].mac_address, "AA:BB:CC:DD:EE:FF")

    def _status_result_for(self, status_value: int):
        with patch(
            "networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock
        ), patch("networkmapper.discovery.snmp_client.walk_cmd") as walk_cmd_mock:
            walk_cmd_mock.side_effect = _walk_cmd_side_effect(
                [
                    [(None, 0, 0, [(f"{DOT1D_TP_FDB_PORT_OID}.{_MAC_A_OCTETS}", 4)])],
                    [(None, 0, 0, [(f"{DOT1D_TP_FDB_STATUS_OID}.{_MAC_A_OCTETS}", status_value)])],
                ]
            )
            return PysnmpClient().get_bridge_fdb("203.0.113.5", _CREDENTIALS, 1.0, 1)

    def test_learned_status_row(self):
        result = self._status_result_for(3)
        self.assertEqual(result.entries[0].status, "learned")

    def test_self_status_row(self):
        result = self._status_result_for(4)
        self.assertEqual(result.entries[0].status, "self")

    def test_mgmt_status_row(self):
        result = self._status_result_for(5)
        self.assertEqual(result.entries[0].status, "mgmt")

    def test_invalid_status_row(self):
        result = self._status_result_for(2)
        self.assertEqual(result.entries[0].status, "invalid")

    def test_other_status_row(self):
        result = self._status_result_for(1)
        self.assertEqual(result.entries[0].status, "other")

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_zero_rows_is_a_legitimate_responded_result(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect([[(None, 0, 0, [])], [(None, 0, 0, [])]])

        result = PysnmpClient().get_bridge_fdb("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(result.entries, [])
        self.assertIsNone(result.failure_reason)

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_missing_bridge_mib_support_is_a_legitimate_responded_result(
        self, walk_cmd_mock, _target_mock
    ):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                [(None, 0, 0, [(f"{DOT1D_TP_FDB_PORT_OID}.0", NoSuchObject())])],
                [(None, 0, 0, [(f"{DOT1D_TP_FDB_STATUS_OID}.0", NoSuchObject())])],
            ]
        )

        result = PysnmpClient().get_bridge_fdb("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(result.entries, [])
        self.assertIsNone(result.failure_reason)

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_port_walk_error_indication_is_reported_as_timeout(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [[(Exception("No SNMP response received before timeout"), 0, 0, [])]]
        )

        result = PysnmpClient().get_bridge_fdb("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "timeout")
        self.assertEqual(result.entries, [])

    @patch("networkmapper.discovery.snmp_client.UdpTransportTarget.create", new_callable=AsyncMock)
    @patch("networkmapper.discovery.snmp_client.walk_cmd")
    def test_status_walk_failure_does_not_fail_the_whole_result(self, walk_cmd_mock, _target_mock):
        walk_cmd_mock.side_effect = _walk_cmd_side_effect(
            [
                [(None, 0, 0, [(f"{DOT1D_TP_FDB_PORT_OID}.{_MAC_A_OCTETS}", 4)])],
                [(Exception("timeout"), 0, 0, [])],  # Status walk fails; best-effort.
            ]
        )

        result = PysnmpClient().get_bridge_fdb("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertTrue(result.responded)
        self.assertEqual(len(result.entries), 1)
        self.assertIsNone(result.entries[0].status)

    @patch(
        "networkmapper.discovery.snmp_client.UdpTransportTarget.create",
        new_callable=AsyncMock,
        side_effect=RuntimeError("unexpected transport failure"),
    )
    def test_unexpected_exception_never_propagates(self, _target_mock):
        result = PysnmpClient().get_bridge_fdb("203.0.113.5", _CREDENTIALS, 1.0, 1)

        self.assertFalse(result.responded)
        self.assertEqual(result.failure_reason, "malformed response")
        self.assertNotIn("unexpected transport failure", (result.failure_reason or ""))


if __name__ == "__main__":
    unittest.main()
