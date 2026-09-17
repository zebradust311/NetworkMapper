import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.windows_server_rule import WindowsServerRule
from networkmapper.core.models import Device, DeviceType


class WindowsServerRuleTest(unittest.TestCase):
    def test_explicit_windows_server_2003_caption_matches(self):
        device = Device(
            ip_address="172.16.100.52",
            hostname="sctts01.wrf.scterm.com",
            vendor="Microsoft",
            operating_system="Windows Server 2003 R2 3790 Service Pack 2 (Windows Server 2003 R2 5.2)",
        )

        result = WindowsServerRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertIn("matched known Windows Server caption", result.reason)

    def test_explicit_windows_server_2012_r2_datacenter_caption_matches(self):
        device = Device(
            ip_address="172.16.100.15",
            hostname="SCTSEPS.wrf.scterm.com",
            vendor="Microsoft",
            operating_system=(
                "Windows Server 2012 R2 Datacenter 9600 (Windows Server 2012 R2 Datacenter 6.3)"
            ),
        )

        result = WindowsServerRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)

    def test_explicit_windows_server_2019_caption_matches(self):
        device = Device(
            ip_address="172.16.100.19",
            hostname="SCT0008.wrf.scterm.com",
            vendor="Dell",
            operating_system=(
                "Windows Server 2019 Standard 17763 (Windows Server 2019 Standard 6.3)"
            ),
        )

        result = WindowsServerRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)

    def test_windows_server_caption_matching_is_case_insensitive(self):
        device = Device(
            ip_address="172.16.100.99",
            operating_system="windows server 2016 standard 14393",
        )

        result = WindowsServerRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)

    def test_exact_server_2022_build_matches(self):
        device = Device(
            ip_address="172.16.100.54",
            hostname="SCTRDS1.wrf.scterm.com",
            vendor="Microsoft",
            operating_system="10.0.20348",
        )

        result = WindowsServerRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertIn("unambiguous Windows Server 2022 build", result.reason)

    def test_ambiguous_build_6_3_9600_does_not_match(self):
        """Shared between Windows 8.1 and Server 2012 R2 -- reproduces the
        real SCTVSH01/SCTVSH02/SCT0020/PWD/SCT00CA evidence exactly."""
        device = Device(ip_address="172.16.100.14", operating_system="6.3.9600")

        result = WindowsServerRule().classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_ambiguous_build_10_0_26100_does_not_match(self):
        """Shared between Windows 11 24H2 and Server 2025."""
        device = Device(ip_address="172.16.102.9", operating_system="10.0.26100")

        result = WindowsServerRule().classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_ranged_product_string_is_never_consulted(self):
        """Proves the rule only ever reads operating_system, never
        product -- a ranged/ambiguous product string naming "Windows
        Server" must not make this rule match when operating_system
        itself is empty or ambiguous."""
        from networkmapper.core.models import ServiceEvidence

        device = Device(
            ip_address="172.16.100.11",
            operating_system="6.3.9600",
            services=[
                ServiceEvidence(
                    port=445,
                    protocol="tcp",
                    service="microsoft-ds",
                    product="Microsoft Windows Server 2008 R2 - 2012 microsoft-ds",
                )
            ],
        )

        result = WindowsServerRule().classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_samba_reported_os_does_not_match(self):
        device = Device(
            ip_address="172.16.102.112",
            operating_system="Windows 6.1 (Samba 4.7.6-Ubuntu)",
        )

        result = WindowsServerRule().classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_explicit_client_caption_does_not_match(self):
        device = Device(
            ip_address="172.16.101.0",
            operating_system="Windows 10 Enterprise 19045 (Windows 10 Enterprise 6.3)",
        )

        result = WindowsServerRule().classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_no_operating_system_does_not_match(self):
        device = Device(ip_address="172.16.101.6", operating_system=None)

        result = WindowsServerRule().classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)


if __name__ == "__main__":
    unittest.main()
