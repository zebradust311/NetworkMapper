import unittest
from unittest.mock import AsyncMock, patch

from pysnmp.hlapi.v3arch.asyncio import NoSuchInstance, NoSuchObject

from networkmapper.discovery.snmp_client import (
    IP_NET_TO_PHYSICAL_PHYS_ADDRESS_OID,
    IP_NET_TO_PHYSICAL_TYPE_OID,
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


if __name__ == "__main__":
    unittest.main()
