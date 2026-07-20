import unittest

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
                self.assertEqual(rule.classify(device), DeviceType.PHONE)

    def test_case_insensitive_matching(self):
        device = Device(ip_address="192.168.1.21", vendor="yEaLiNk")

        result = VoiceVendorRule().classify(device)

        self.assertEqual(result, DeviceType.PHONE)

    def test_empty_vendor_returns_none(self):
        device = Device(ip_address="192.168.1.22", vendor="")

        result = VoiceVendorRule().classify(device)

        self.assertIsNone(result)

    def test_none_vendor_returns_none(self):
        device = Device(ip_address="192.168.1.23", vendor=None)

        result = VoiceVendorRule().classify(device)

        self.assertIsNone(result)

    def test_unsupported_vendor_returns_none(self):
        device = Device(ip_address="192.168.1.24", vendor="SonicWall")

        result = VoiceVendorRule().classify(device)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
