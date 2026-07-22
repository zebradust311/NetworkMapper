import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.hypervisor_hostname_rule import HypervisorHostnameRule
from networkmapper.core.models import Device, DeviceType


class HypervisorHostnameRuleTest(unittest.TestCase):
    def test_vsh_hostname_returns_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.60",
            hostname="SCTVSH01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertTrue(result.reason)

    def test_case_insensitive_hostname_matching(self):
        device = Device(
            ip_address="192.168.1.61",
            hostname="node-VsH-01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertTrue(result.reason)

    def test_non_matching_hostname_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.62",
            hostname="host-01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertTrue(result.reason)


if __name__ == "__main__":
    unittest.main()