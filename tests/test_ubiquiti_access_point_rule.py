import unittest

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

        self.assertEqual(result, DeviceType.ACCESS_POINT)

    def test_u6_hostname_classifies_as_access_point(self):
        device = Device(
            ip_address="192.168.1.21",
            hostname="U6-Pro",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertEqual(result, DeviceType.ACCESS_POINT)

    def test_u7_hostname_classifies_as_access_point(self):
        device = Device(
            ip_address="192.168.1.22",
            hostname="U7-Pro",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertEqual(result, DeviceType.ACCESS_POINT)

    def test_other_ubiquiti_devices_remain_unaffected(self):
        device = Device(
            ip_address="192.168.1.23",
            hostname="Switch-01",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsNone(result)

    def test_non_ubiquiti_devices_are_ignored(self):
        device = Device(
            ip_address="192.168.1.24",
            hostname="UAP-AC-LR",
            vendor="Cisco",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
