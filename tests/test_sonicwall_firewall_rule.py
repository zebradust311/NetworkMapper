import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.sonicwall_firewall_rule import SonicWallFirewallRule
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


class SonicWallFirewallRuleTest(unittest.TestCase):
    def test_matching_vendor_returns_rule_result_with_firewall_type(self):
        device = Device(
            ip_address="192.168.1.30",
            hostname="fw-01",
            vendor="SonicWall",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(result.reason, "Vendor 'SonicWall' matched known firewall vendor.")

    def test_case_insensitive_vendor_matching(self):
        device = Device(
            ip_address="192.168.1.31",
            hostname="fw-02",
            vendor="sonicwall",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(result.reason, "Vendor 'sonicwall' matched known firewall vendor.")

    def test_empty_vendor_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.32",
            hostname="fw-03",
            vendor="",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(result.reason, "Vendor '' is not a known firewall vendor.")

    def test_non_matching_vendor_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.33",
            hostname="fw-04",
            vendor="Cisco",
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(result.reason, "Vendor 'Cisco' is not a known firewall vendor.")

    def test_sonicwall_hostname_with_management_signals_matches_without_vendor(self):
        device = Device(
            ip_address="192.168.1.34",
            hostname="tz-370",
            vendor="Unknown",
            services=[ServiceEvidence(port=443, protocol="tcp", service="https")],
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(
            result.reason,
            "Hostname 'tz-370' with open port 443 and service 'https' matched known firewall management evidence.",
        )

    def test_http_title_identifies_firewall_without_vendor_or_hostname_match(self):
        device = Device(
            ip_address="192.168.1.35",
            hostname="fw-05",
            vendor="Unknown",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    service="https",
                    http_title="SonicWALL - Network Security Appliance",
                ),
            ],
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(
            result.reason,
            "Detected HTTP title 'SonicWALL - Network Security Appliance' "
            "matched known firewall vendor identifier.",
        )

    def test_tls_certificate_subject_identifies_firewall(self):
        device = Device(
            ip_address="192.168.1.36",
            hostname="fw-06",
            vendor="Unknown",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    service="https",
                    tls_subject="commonName=SonicWALL",
                ),
            ],
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(
            result.reason,
            "Detected TLS certificate subject 'commonName=SonicWALL' matched "
            "known firewall vendor identifier.",
        )

    def test_identifier_match_takes_precedence_over_hostname_and_port_fallback(self):
        device = Device(
            ip_address="192.168.1.37",
            hostname="unrelated-01",
            vendor="Unknown",
            services=[
                ServiceEvidence(
                    port=8443,
                    protocol="tcp",
                    tls_issuer="commonName=SonicWALL",
                ),
            ],
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(
            result.reason,
            "Detected TLS certificate issuer 'commonName=SonicWALL' matched "
            "known firewall vendor identifier.",
        )

    def test_unrelated_http_title_does_not_match(self):
        device = Device(
            ip_address="192.168.1.38",
            hostname="web-01",
            vendor="Unknown",
            services=[
                ServiceEvidence(port=443, protocol="tcp", http_title="Welcome to nginx!"),
            ],
        )

        result = SonicWallFirewallRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)


if __name__ == "__main__":
    unittest.main()
