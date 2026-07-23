import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.ubiquiti_access_point_rule import UbiquitiAccessPointRule
from networkmapper.core.models import Device, DeviceType


class UbiquitiAccessPointRuleTest(unittest.TestCase):
    def test_uap_hostname_classifies_as_access_point(self):
        device = Device(
            ip_address="192.168.1.20",
            hostname="UAP-AC-LR",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ACCESS_POINT)
        self.assertEqual(
            result.reason,
            "Vendor 'Ubiquiti' and hostname 'UAP-AC-LR' matched known wireless infrastructure vendor.",
        )

    def test_u6_hostname_classifies_as_access_point(self):
        device = Device(
            ip_address="192.168.1.21",
            hostname="U6-Pro",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ACCESS_POINT)
        self.assertEqual(
            result.reason,
            "Vendor 'Ubiquiti' and hostname 'U6-Pro' matched known wireless infrastructure vendor.",
        )

    def test_u7_hostname_classifies_as_access_point(self):
        device = Device(
            ip_address="192.168.1.22",
            hostname="U7-Pro",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ACCESS_POINT)
        self.assertEqual(
            result.reason,
            "Vendor 'Ubiquiti' and hostname 'U7-Pro' matched known wireless infrastructure vendor.",
        )

    def test_other_ubiquiti_devices_remain_unaffected(self):
        device = Device(
            ip_address="192.168.1.23",
            hostname="Switch-01",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(
            result.reason,
            "Vendor 'Ubiquiti' and hostname 'Switch-01' did not match known wireless infrastructure vendor patterns.",
        )

    def test_non_ubiquiti_devices_are_ignored(self):
        device = Device(
            ip_address="192.168.1.24",
            hostname="UAP-AC-LR",
            vendor="Cisco",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(
            result.reason,
            "Vendor 'Cisco' and hostname 'UAP-AC-LR' did not match known wireless infrastructure vendor patterns.",
        )


if __name__ == "__main__":
    unittest.main()
