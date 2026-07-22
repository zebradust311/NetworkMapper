import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.dell_workstation_rule import DellWorkstationRule
from networkmapper.core.models import Device, DeviceType


class DellWorkstationRuleTest(unittest.TestCase):
    def test_matching_vendor_returns_rule_result_with_workstation_type(self):
        device = Device(
            ip_address="192.168.1.70",
            hostname="ws-01",
            vendor="Dell Inc.",
        )

        result = DellWorkstationRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)
        self.assertTrue(result.reason)

    def test_case_insensitive_vendor_matching(self):
        device = Device(
            ip_address="192.168.1.71",
            hostname="ws-02",
            vendor="dElL",
        )

        result = DellWorkstationRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)
        self.assertTrue(result.reason)

    def test_non_matching_vendor_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.72",
            hostname="ws-03",
            vendor="Lenovo",
        )

        result = DellWorkstationRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertTrue(result.reason)


if __name__ == "__main__":
    unittest.main()