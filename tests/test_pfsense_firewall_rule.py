import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.pfsense_firewall_rule import PfSenseFirewallRule
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


class PfSenseFirewallRuleTest(unittest.TestCase):
    def setUp(self):
        self.rule = PfSenseFirewallRule()

    def test_pfsense_http_title_classifies_as_firewall(self):
        device = Device(
            ip_address="172.16.100.8",
            hostname=None,
            vendor="Silicom",
            services=[
                ServiceEvidence(port=443, protocol="tcp", http_title="Netgate pfSense Plus - Login"),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(
            result.reason,
            "Detected HTTP title 'Netgate pfSense Plus - Login' matched known "
            "pfSense firewall identifier.",
        )

    def test_pfsense_tls_subject_classifies_as_firewall(self):
        device = Device(
            ip_address="172.16.100.8",
            hostname=None,
            vendor="Silicom",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    tls_subject=(
                        "commonName=pfSense-697b4472a5cba/organizationName=Netgate "
                        "pfSense Plus GUI default Self-Signed Certificate"
                    ),
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(
            result.reason,
            "Detected TLS certificate subject "
            "'commonName=pfSense-697b4472a5cba/organizationName=Netgate pfSense "
            "Plus GUI default Self-Signed Certificate' matched known pfSense "
            "firewall identifier.",
        )

    def test_pfsense_tls_issuer_classifies_as_firewall(self):
        device = Device(
            ip_address="172.16.100.8",
            hostname=None,
            vendor="Silicom",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    tls_issuer=(
                        "commonName=pfSense-697b4472a5cba/organizationName=Netgate "
                        "pfSense Plus GUI default Self-Signed Certificate"
                    ),
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)

    def test_pfsense_http_auth_realm_classifies_as_firewall(self):
        device = Device(
            ip_address="172.16.100.9",
            hostname=None,
            vendor="Silicom",
            services=[
                ServiceEvidence(port=443, protocol="tcp", http_auth_realm="pfSense"),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(
            result.reason,
            "Detected HTTP authentication realm 'pfSense' matched known "
            "pfSense firewall identifier.",
        )

    def test_bare_netgate_http_auth_realm_without_pfsense_does_not_match(self):
        """Architect correction (PLAN-RULE-010 Section 16): "Netgate" is
        manufacturer/product-family identity, not pfSense-specific identity
        -- Netgate also manufactures TNSR, a separate router product line.
        A bare "Netgate" string, with no "pfsense" text anywhere, must not
        independently classify FIREWALL."""
        device = Device(
            ip_address="172.16.100.13",
            hostname=None,
            vendor="Silicom",
            services=[
                ServiceEvidence(port=443, protocol="tcp", http_auth_realm="Netgate"),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "No known pfSense firewall identifier evidence was detected.",
        )

    def test_pfsense_snmp_sys_descr_classifies_as_firewall(self):
        device = Device(
            ip_address="172.16.100.10",
            hostname=None,
            vendor="Silicom",
            snmp_sys_descr="pfSense 2.7.2-RELEASE",
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(
            result.reason,
            "Detected SNMP sysDescr 'pfSense 2.7.2-RELEASE' matched known "
            "pfSense firewall identifier.",
        )

    def test_case_insensitive_pfsense_matching(self):
        device = Device(
            ip_address="172.16.100.11",
            hostname=None,
            vendor="Silicom",
            services=[ServiceEvidence(port=443, protocol="tcp", http_title="NETGATE PFSENSE PLUS - LOGIN")],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)

    def test_unrelated_firewall_evidence_does_not_match(self):
        """A SonicWall firewall's own identifier evidence must not match here."""
        device = Device(
            ip_address="192.168.1.30",
            hostname="fw-01",
            vendor="SonicWall",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    http_title="SonicWALL - Network Security Appliance",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_unrelated_appliance_evidence_does_not_match(self):
        device = Device(
            ip_address="172.16.100.4",
            hostname=None,
            vendor="Ubiquiti",
            services=[ServiceEvidence(port=443, protocol="tcp", http_title="EdgeOS")],
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_bare_vendor_without_identifier_does_not_match(self):
        """The real device's own vendor field (Silicom, a NIC/hardware OEM)
        must never be an independent trigger."""
        device = Device(
            ip_address="172.16.100.8",
            hostname=None,
            vendor="Silicom",
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "No known pfSense firewall identifier evidence was detected.",
        )

    def test_hostname_only_does_not_match(self):
        device = Device(
            ip_address="192.168.1.50",
            hostname="pfsense-router",
            vendor=None,
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_unrelated_services_do_not_match(self):
        device = Device(
            ip_address="192.168.1.60",
            hostname="web-01",
            vendor="Dell",
            services=[
                ServiceEvidence(port=443, protocol="tcp", http_title="Welcome to nginx!"),
                ServiceEvidence(port=53, protocol="tcp", service="domain", product="Unbound"),
            ],
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_both_http_title_and_tls_present_prefers_http_title(self):
        """Reproduces the exact real production evidence shape (172.16.100.8) --
        the device carries both the HTTP title and the TLS subject/issuer
        simultaneously. first_matching_identifier checks product, then HTTP
        title, then TLS subject, then TLS issuer, then HTTP auth realm, then
        SNMP sysDescr, in that fixed order, so with both present the match
        must deterministically resolve to the HTTP title tier, never the
        TLS tier."""
        device = Device(
            ip_address="172.16.100.8",
            hostname=None,
            vendor="Silicom",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    http_title="Netgate pfSense Plus - Login",
                    tls_subject=(
                        "commonName=pfSense-697b4472a5cba/organizationName=Netgate "
                        "pfSense Plus GUI default Self-Signed Certificate"
                    ),
                    tls_issuer=(
                        "commonName=pfSense-697b4472a5cba/organizationName=Netgate "
                        "pfSense Plus GUI default Self-Signed Certificate"
                    ),
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)
        self.assertEqual(
            result.reason,
            "Detected HTTP title 'Netgate pfSense Plus - Login' matched known "
            "pfSense firewall identifier.",
        )


if __name__ == "__main__":
    unittest.main()
