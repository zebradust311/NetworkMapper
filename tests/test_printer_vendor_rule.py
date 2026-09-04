import unittest

from networkmapper.classification.rules.printer_vendor_rule import PrinterVendorRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


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

                result = self.rule.classify(device)

                self.assertEqual(
                    DeviceType.PRINTER,
                    result.suggested_device_type,
                )
                self.assertEqual(result.reason, f"Vendor '{vendor}' matched known printer vendor.")

    def test_vendor_matching_is_case_insensitive(self):
        device = Device(
            ip_address="192.168.1.11",
            vendor="kONiCA miNoLTA",
        )

        self.assertEqual(
            DeviceType.PRINTER,
            self.rule.classify(device).suggested_device_type,
        )

    def test_empty_vendor_is_ignored(self):
        device = Device(
            ip_address="192.168.1.12",
            vendor="",
        )

        result = self.rule.classify(device)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "Vendor '' is not a known printer vendor and no printer networking protocols were detected.",
        )

    def test_none_vendor_is_ignored(self):
        device = Device(
            ip_address="192.168.1.13",
            vendor=None,
        )

        result = self.rule.classify(device)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "Vendor None is not a known printer vendor and no printer networking protocols were detected.",
        )

    def test_non_printer_vendor_is_ignored(self):
        device = Device(
            ip_address="192.168.1.14",
            vendor="SonicWall",
        )

        result = self.rule.classify(device)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "Vendor 'SonicWall' is not a known printer vendor and no printer networking protocols were detected.",
        )

    def test_printer_rule_emits_rule_result(self):
        device = Device(
            ip_address="192.168.1.15",
            vendor="Brother Industries",
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Vendor 'Brother Industries' matched known printer vendor.",
        )

    def test_printer_port_9100_classifies_without_vendor_match(self):
        device = Device(
            ip_address="192.168.1.16",
            vendor=None,
            services=[ServiceEvidence(port=9100, protocol="tcp")],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Open TCP port 9100 (JetDirect) indicates printer networking.",
        )

    def test_printer_ipp_service_classifies_without_vendor_match(self):
        device = Device(
            ip_address="192.168.1.17",
            vendor=None,
            services=[ServiceEvidence(port=80, protocol="tcp", service="ipp")],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Detected IPP service indicates printer networking.",
        )

    def test_printer_product_classifies_without_vendor_or_networking_match(self):
        device = Device(
            ip_address="192.168.1.18",
            vendor=None,
            services=[
                ServiceEvidence(
                    port=631,
                    protocol="tcp",
                    service="ipp",
                    product="HP LaserJet 4250",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Detected service product 'HP LaserJet 4250' matched known printer "
            "vendor identifier.",
        )

    def test_printer_product_takes_precedence_over_networking_only_signal(self):
        device = Device(
            ip_address="192.168.1.19",
            vendor="Unknown",
            services=[
                ServiceEvidence(
                    port=9100,
                    protocol="tcp",
                    service="jetdirect",
                    product="Brother HL-L2350DW series",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Detected service product 'Brother HL-L2350DW series' matched known "
            "printer vendor identifier.",
        )

    def test_printer_http_title_classifies_without_vendor_or_networking_match(self):
        device = Device(
            ip_address="192.168.1.21",
            vendor=None,
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    http_title="HP LaserJet MFP M479 - Home",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Detected HTTP title 'HP LaserJet MFP M479 - Home' matched known "
            "printer vendor identifier.",
        )

    def test_printer_http_auth_realm_classifies_without_vendor_or_networking_match(self):
        device = Device(
            ip_address="192.168.1.22",
            vendor=None,
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    http_auth_realm="HP LaserJet 4250",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Detected HTTP authentication realm 'HP LaserJet 4250' matched "
            "known printer vendor identifier.",
        )

    def test_snmp_sys_descr_classifies_without_vendor_or_networking_match(self):
        """RULE-004: SNMP sysDescr participates in the same identifier tier
        as product string/HTTP title/HTTP auth realm, per ARCH-012's own
        "HP LaserJet 4250, Firmware..." example sysDescr."""
        device = Device(
            ip_address="192.168.1.23",
            vendor=None,
            snmp_sys_descr="HP LaserJet 4250, Firmware Version: 08.061.3",
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Detected SNMP sysDescr 'HP LaserJet 4250, Firmware Version: "
            "08.061.3' matched known printer vendor identifier.",
        )

    def test_snmp_sys_descr_is_checked_after_service_evidence(self):
        device = Device(
            ip_address="192.168.1.24",
            vendor=None,
            services=[
                ServiceEvidence(
                    port=631,
                    protocol="tcp",
                    service="ipp",
                    product="Brother HL-L2350DW series",
                ),
            ],
            snmp_sys_descr="HP LaserJet 4250, Firmware Version: 08.061.3",
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Detected service product 'Brother HL-L2350DW series' matched known "
            "printer vendor identifier.",
        )

    def test_redirect_notice_http_title_does_not_match_incidental_hp_substring(self):
        """RULE-005: reproduces the real production defect exactly.

        A UniFi guest-portal redirect's opaque, effectively-random
        base64-like ticket token incidentally contains "hp" as a bare
        substring. Nmap's "Did not follow redirect to ..." notice is
        scanner commentary, not device-reported identity text, and must
        not be searched for printer vendor keywords.
        """
        device = Device(
            ip_address="172.16.100.116",
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    service="http",
                    http_title=(
                        "Did not follow redirect to "
                        "http://172.16.100.89:8880/guest/s/default/?ap=0c:ea:14:b7:41:9d"
                        "&ec=4i5lQ9ecDwcp-LCkH1697alvguXoqmWg3DshpMadGs7OTsAnAWcJPf0sYnKy8ojRBcJi"
                    ),
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_redirect_notice_exclusion_does_not_affect_genuine_printer_title_containing_hp(self):
        """Sanity check for the fix's precision: a genuine printer HTTP
        title containing "hp" in ordinary (non-redirect-notice) context
        must still match."""
        device = Device(
            ip_address="192.168.1.30",
            vendor=None,
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    http_title="HP LaserJet Pro MFP - Status",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)

    def test_redirect_notice_on_an_unrelated_port_does_not_hide_a_real_printer_title(self):
        """A device with a redirect notice on one port and a genuine
        printer identifier on another port must still be detected via
        the untouched evidence."""
        device = Device(
            ip_address="192.168.1.31",
            vendor=None,
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    http_title="Did not follow redirect to https://192.168.1.31/",
                ),
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    http_title="HP LaserJet MFP M479 - Home",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Detected HTTP title 'HP LaserJet MFP M479 - Home' matched known "
            "printer vendor identifier.",
        )

    def test_non_printer_product_falls_back_to_networking_signal(self):
        device = Device(
            ip_address="192.168.1.20",
            vendor=None,
            services=[
                ServiceEvidence(
                    port=9100,
                    protocol="tcp",
                    service="jetdirect",
                    product="Generic Print Server",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.PRINTER)
        self.assertEqual(
            result.reason,
            "Open TCP port 9100 (JetDirect) indicates printer networking. "
            "Detected JETDIRECT service indicates printer networking.",
        )


if __name__ == "__main__":
    unittest.main()