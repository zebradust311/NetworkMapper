import unittest

from networkmapper.classification.rules.printer_vendor_rule import PrinterVendorRule
from networkmapper.core.models import Device, DeviceType


class PrinterVendorRuleTest(unittest.TestCase):

    SUPPORTED_PRINTER_VENDORS = (
        "Brother",
        "HP",
        "Hewlett-Packard",
        "Canon",
        "Ricoh",
        "Konica Minolta",
        "Epson",
        "Xerox",
        "Lexmark",
        "Kyocera",
        "Sharp",
        "Toshiba",
        "Zebra",
        "Datamax",
        "Fujifilm Business Innovation",
    )

    def setUp(self):
        self.rule = PrinterVendorRule()

    def test_supported_printer_vendors_classify_as_printer(self):
        for vendor in self.SUPPORTED_PRINTER_VENDORS:
            with self.subTest(vendor=vendor):
                device = Device(
                    ip_address="192.168.1.10",
                    vendor=vendor,
                )

                self.assertEqual(
                    DeviceType.PRINTER,
                    self.rule.classify(device),
                )

    def test_vendor_matching_is_case_insensitive(self):
        device = Device(
            ip_address="192.168.1.11",
            vendor="kONiCA miNoLTA",
        )

        self.assertEqual(
            DeviceType.PRINTER,
            self.rule.classify(device),
        )

    def test_empty_vendor_is_ignored(self):
        device = Device(
            ip_address="192.168.1.12",
            vendor="",
        )

        self.assertIsNone(
            self.rule.classify(device),
        )

    def test_none_vendor_is_ignored(self):
        device = Device(
            ip_address="192.168.1.13",
            vendor=None,
        )

        self.assertIsNone(
            self.rule.classify(device),
        )

    def test_non_printer_vendor_is_ignored(self):
        device = Device(
            ip_address="192.168.1.14",
            vendor="SonicWall",
        )

        self.assertIsNone(
            self.rule.classify(device),
        )


if __name__ == "__main__":
    unittest.main()