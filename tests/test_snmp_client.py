import unittest
from unittest.mock import AsyncMock, patch

from pysnmp.hlapi.v3arch.asyncio import NoSuchInstance, NoSuchObject

from networkmapper.discovery.snmp_client import PysnmpClient, SYSTEM_GROUP_OIDS
from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion

_CREDENTIALS = SnmpCredentials(version=SnmpVersion.V2C, community="public")


def _var_binds(values: list) -> list:
    """Build a var_binds list matching SYSTEM_GROUP_OIDS's order and length."""
    return [(name, value) for (name, _oid), value in zip(SYSTEM_GROUP_OIDS, values)]


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


if __name__ == "__main__":
    unittest.main()
