import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.windows_workstation_rule import WindowsWorkstationRule
from networkmapper.core.models import Device, DeviceType


class WindowsWorkstationRuleTest(unittest.TestCase):
    def setUp(self):
        self.rule = WindowsWorkstationRule()

    def test_windows_10_enterprise_caption_matches(self):
        """Reproduces MIS3030a (172.16.101.0) exactly -- the one real
        production device this sprint resolves."""
        device = Device(
            ip_address="172.16.101.0",
            hostname="MIS3030a.wrf.scterm.com",
            vendor="ASUSTek Computer",
            operating_system="Windows 10 Enterprise 19045 (Windows 10 Enterprise 6.3)",
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)
        self.assertIn("matched known Windows client edition caption", result.reason)

    def test_windows_7_professional_caption_matches(self):
        """Reproduces SCT2053 (172.16.102.135) exactly -- already
        correctly WORKSTATION via DellWorkstationRule; this rule agrees
        independently on the same outcome."""
        device = Device(
            ip_address="172.16.102.135",
            hostname="SCT2053.wrf.scterm.com",
            vendor="Dell",
            operating_system="Windows 7 Professional 7601 Service Pack 1 (Windows 7 Professional 6.1)",
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)

    def test_windows_10_home_caption_matches(self):
        """PLAN-RULE-007 Section 21 amendment: added prospectively for MSP
        fleets; no corresponding real device exists in captured evidence."""
        device = Device(ip_address="11", operating_system="Windows 10 Home 19045 (Windows 10 Home 6.3)")

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)

    def test_windows_10_home_single_language_variant_matches(self):
        """Realistic OEM/regional Home variant -- still contains the
        version-qualified "windows 10 home" substring."""
        device = Device(ip_address="12", operating_system="Windows 10 Home Single Language 19045")

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)

    def test_windows_11_home_caption_matches(self):
        device = Device(ip_address="13", operating_system="Windows 11 Home 23H2")

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)

    def test_matching_is_case_insensitive(self):
        device = Device(ip_address="1", operating_system="WINDOWS 11 ENTERPRISE")

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)

    def test_home_matching_is_case_insensitive(self):
        device = Device(ip_address="14", operating_system="windows 10 home 19045")

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)

    def test_bare_pro_does_not_match(self):
        """Deliberately excluded per PLAN-RULE-007 Section 12: a bare
        three-letter substring is exactly the collision risk RULE-005
        already found and fixed for PrinterVendorRule's "hp" keyword."""
        device = Device(ip_address="2", operating_system="Windows 10 Pro 19045")

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_windows_home_server_does_not_match(self):
        """PLAN-RULE-007 Section 21.3: the exact reason bare "home"/
        "windows home" were rejected -- Windows Home Server is a real,
        shipped Microsoft product (2007-2013), and a bare substring
        would have matched it. The approved version-qualified keywords
        ("windows 10 home"/"windows 11 home") are disjoint from this
        caption by word order."""
        device = Device(ip_address="15", operating_system="Windows Home Server 2011")

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_bare_home_without_version_qualifier_does_not_match(self):
        """Locks in the precision decision: only the version-qualified
        "windows 10 home"/"windows 11 home" forms are approved -- a bare
        "Home" with no Windows 10/11 prefix must not match."""
        device = Device(ip_address="16", operating_system="Home Edition 19045")

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_ambiguous_build_6_3_9600_does_not_match(self):
        device = Device(ip_address="4", operating_system="6.3.9600")

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_ambiguous_build_10_0_26100_does_not_match(self):
        device = Device(ip_address="5", operating_system="10.0.26100")

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_generic_windows_caption_without_edition_does_not_match(self):
        device = Device(ip_address="6", operating_system="Windows Server 2019 Standard 17763")

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_samba_flavored_os_does_not_match(self):
        device = Device(ip_address="7", operating_system="Windows 6.1 (Samba 4.7.6-Ubuntu)")

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_vendor_alone_does_not_match(self):
        device = Device(ip_address="8", vendor="Dell", operating_system=None)

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_hostname_alone_does_not_match(self):
        device = Device(
            ip_address="9", hostname="enterprise-laptop-01", operating_system=None
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_no_operating_system_does_not_match(self):
        device = Device(ip_address="10", operating_system=None)

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)


if __name__ == "__main__":
    unittest.main()
