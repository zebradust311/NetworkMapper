import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.sonicwall_firewall_rule import SonicWallFirewallRule
from networkmapper.core.models import Device, DeviceType


class SonicWallFirewallRuleTest(unittest.TestCase):
    def test_matching_vendor_returns_rule_result_with_firewall_type(self):
        device = Device(
            ip_address="192.168.1.30",
            hostname="fw-01",
            vendor="SonicWall",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(result.reason, "Vendor 'SonicWall' matched known firewall vendor.")

    def test_case_insensitive_vendor_matching(self):
        device = Device(
            ip_address="192.168.1.31",
            hostname="fw-02",
            vendor="sonicwall",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(result.reason, "Vendor 'sonicwall' matched known firewall vendor.")

    def test_empty_vendor_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.32",
            hostname="fw-03",
            vendor="",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(result.reason, "Vendor '' is not a known firewall vendor.")

    def test_non_matching_vendor_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.33",
            hostname="fw-04",
            vendor="Cisco",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(result.reason, "Vendor 'Cisco' is not a known firewall vendor.")


if __name__ == "__main__":
    unittest.main()
