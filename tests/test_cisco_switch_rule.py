import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.cisco_switch_rule import CiscoSwitchRule
from networkmapper.core.models import Device, DeviceType


class CiscoSwitchRuleTest(unittest.TestCase):
    def test_matching_vendor_returns_rule_result_with_switch_type(self):
        device = Device(
            ip_address="192.168.1.40",
            hostname="sw-01",
            vendor="Cisco Systems",
        )

        result = CiscoSwitchRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(result.reason, "Vendor 'Cisco Systems' matched known switch vendor.")

    def test_case_insensitive_vendor_matching(self):
        device = Device(
            ip_address="192.168.1.41",
            hostname="sw-02",
            vendor="cIsCo",
        )

        result = CiscoSwitchRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(result.reason, "Vendor 'cIsCo' matched known switch vendor.")

    def test_non_matching_vendor_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.42",
            hostname="sw-03",
            vendor="Juniper",
        )

        result = CiscoSwitchRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(result.reason, "Vendor 'Juniper' is not a known switch vendor.")

    def test_switch_hostname_with_management_signals_matches_without_vendor(self):
        device = Device(
            ip_address="192.168.1.43",
            hostname="switch-core-01",
            vendor="Unknown",
            open_ports=[161],
            detected_services=["snmp"],
        )

        result = CiscoSwitchRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Hostname 'switch-core-01' with open port 161 and service 'snmp' matched known switch management evidence.",
        )


if __name__ == "__main__":
    unittest.main()