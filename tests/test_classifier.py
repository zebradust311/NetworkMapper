import unittest

from networkmapper.classification.classifier import DeviceClassifier
from networkmapper.core.models import Device, DeviceType


class DeviceClassifierTest(unittest.TestCase):
    def test_hostname_rules_take_precedence_over_vendor_rules(self):
        device = Device(
            ip_address="192.168.1.10",
            hostname="DC-01",
            vendor="Cisco",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.SERVER)

    def test_unknown_device_stays_unknown(self):
        device = Device(
            ip_address="192.168.1.99",
            hostname="host-01",
            vendor="Unknown Vendor",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.UNKNOWN)

    def test_first_matching_rule_wins(self):
        device = Device(
            ip_address="192.168.1.50",
            hostname="CAM-01",
            vendor="Brother",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.SERVER)

    def test_ubiquiti_access_point_rule_is_executed_in_classifier(self):
        device = Device(
            ip_address="192.168.1.60",
            hostname="UAP-AC-LR",
            vendor="Ubiquiti",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.ACCESS_POINT)

    def test_sonicwall_firewall_rule_is_executed_in_classifier(self):
        device = Device(
            ip_address="192.168.1.61",
            hostname="fw-01",
            vendor="SonicWall",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.FIREWALL)

    def test_voice_vendor_rule_is_executed_in_classifier(self):
        device = Device(
            ip_address="192.168.1.62",
            hostname="phone-01",
            vendor="Yealink",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.PHONE)


if __name__ == "__main__":
    unittest.main()
