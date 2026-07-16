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


if __name__ == "__main__":
    unittest.main()
