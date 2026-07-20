import unittest

from networkmapper.classification.rules.sonicwall_firewall_rule import SonicWallFirewallRule
from networkmapper.core.models import Device, DeviceType


class SonicWallFirewallRuleTest(unittest.TestCase):
    def test_sonicwall_vendor_classifies_as_firewall(self):
        device = Device(
            ip_address="192.168.1.30",
            hostname="fw-01",
            vendor="SonicWall",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertEqual(result, DeviceType.FIREWALL)

    def test_case_insensitive_vendor_matching(self):
        device = Device(
            ip_address="192.168.1.31",
            hostname="fw-02",
            vendor="sonicwall",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertEqual(result, DeviceType.FIREWALL)

    def test_empty_vendor_is_ignored(self):
        device = Device(
            ip_address="192.168.1.32",
            hostname="fw-03",
            vendor="",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsNone(result)

    def test_non_sonicwall_vendor_is_ignored(self):
        device = Device(
            ip_address="192.168.1.33",
            hostname="fw-04",
            vendor="Cisco",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
