import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.voice_vendor_rule import VoiceVendorRule
from networkmapper.core.models import Device, DeviceType


class VoiceVendorRuleTest(unittest.TestCase):
    def test_supported_voice_vendors_classify_as_phone(self):
        supported_vendors = [
            "Yealink",
            "Poly",
            "Polycom",
            "Grandstream",
            "Mitel",
            "Avaya",
            "Cisco IP Phone",
        ]

        rule = VoiceVendorRule()
        for vendor in supported_vendors:
            with self.subTest(vendor=vendor):
                device = Device(ip_address="192.168.1.20", vendor=vendor)
                result = rule.classify(device)
                self.assertIsInstance(result, RuleResult)
                self.assertTrue(result.matched)
                self.assertEqual(result.suggested_device_type, DeviceType.PHONE)
                self.assertTrue(result.reason)

    def test_case_insensitive_matching(self):
        device = Device(ip_address="192.168.1.21", vendor="yEaLiNk")

        result = VoiceVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PHONE)
        self.assertTrue(result.reason)

    def test_empty_vendor_returns_non_matching_rule_result(self):
        device = Device(ip_address="192.168.1.22", vendor="")

        result = VoiceVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertTrue(result.reason)

    def test_none_vendor_returns_non_matching_rule_result(self):
        device = Device(ip_address="192.168.1.23", vendor=None)

        result = VoiceVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertTrue(result.reason)

    def test_unsupported_vendor_returns_non_matching_rule_result(self):
        device = Device(ip_address="192.168.1.24", vendor="SonicWall")

        result = VoiceVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertTrue(result.reason)


if __name__ == "__main__":
    unittest.main()
