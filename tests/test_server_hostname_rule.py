import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.server_hostname_rule import ServerHostnameRule
from networkmapper.core.models import Device, DeviceType


class ServerHostnameRuleTest(unittest.TestCase):
    def test_dc_hostname_returns_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.50",
            hostname="DC01",
            vendor="Unknown",
        )

        result = ServerHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertEqual(
            result.reason,
            "Hostname 'DC01' matched known server naming convention.",
        )

    def test_cam_hostname_returns_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.51",
            hostname="CAM-01",
            vendor="Unknown",
        )

        result = ServerHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertEqual(
            result.reason,
            "Hostname 'CAM-01' matched known server naming convention.",
        )

    def test_non_matching_hostname_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.52",
            hostname="host-01",
            vendor="Unknown",
        )

        result = ServerHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(
            result.reason,
            "Hostname 'host-01' did not match known server naming patterns.",
        )


if __name__ == "__main__":
    unittest.main()