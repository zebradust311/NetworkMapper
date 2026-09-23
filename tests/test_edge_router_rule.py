import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.edge_router_rule import EdgeRouterRule
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


class EdgeRouterRuleTest(unittest.TestCase):
    def setUp(self):
        self.rule = EdgeRouterRule()

    def test_edgeos_http_title_classifies_as_router(self):
        device = Device(
            ip_address="172.16.100.4",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(port=443, protocol="tcp", http_title="EdgeOS"),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ROUTER)
        self.assertEqual(
            result.reason,
            "Detected HTTP title 'EdgeOS' matched known EdgeOS router identifier.",
        )

    def test_ubiquitirouterui_tls_subject_classifies_as_router(self):
        device = Device(
            ip_address="172.16.100.7",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    tls_subject="commonName=UbiquitiRouterUI/organizationName=Ubiquiti Inc.",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ROUTER)
        self.assertEqual(
            result.reason,
            "Detected TLS certificate subject "
            "'commonName=UbiquitiRouterUI/organizationName=Ubiquiti Inc.' "
            "matched known EdgeOS router identifier.",
        )

    def test_ubiquitirouterui_tls_issuer_classifies_as_router(self):
        device = Device(
            ip_address="172.16.100.240",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    tls_issuer="commonName=UbiquitiRouterUI/organizationName=Ubiquiti Inc.",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ROUTER)

    def test_case_insensitive_edgeos_matching(self):
        device = Device(
            ip_address="172.16.100.5",
            hostname=None,
            vendor="Ubiquiti",
            services=[ServiceEvidence(port=443, protocol="tcp", http_title="EDGEOS")],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ROUTER)

    def test_case_insensitive_ubiquitirouterui_matching(self):
        device = Device(
            ip_address="172.16.100.6",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(port=443, protocol="tcp", tls_subject="commonName=UBIQUITIROUTERUI"),
            ],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ROUTER)

    def test_bare_ubiquiti_vendor_without_identifier_does_not_match(self):
        device = Device(
            ip_address="172.16.100.160",
            hostname=None,
            vendor="Ubiquiti",
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "No known EdgeOS router identifier evidence was detected.",
        )

    def test_ap_shaped_ubiquiti_hostname_without_identifier_does_not_match(self):
        """A real Ubiquiti access point (UbiquitiAccessPointRule's own
        evidence shape) must not be claimed by this rule -- it carries no
        EdgeOS/UbiquitiRouterUI identifier at all."""
        device = Device(
            ip_address="172.16.100.50",
            hostname="U6-LR-Lobby",
            vendor="Ubiquiti",
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_unrelated_non_ubiquiti_evidence_does_not_match(self):
        device = Device(
            ip_address="192.168.1.60",
            hostname="web-01",
            vendor="Dell",
            services=[
                ServiceEvidence(port=443, protocol="tcp", http_title="Welcome to nginx!"),
            ],
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_snmp_sys_descr_containing_edgeos_classifies_as_router(self):
        device = Device(
            ip_address="172.16.100.8",
            hostname=None,
            vendor="Ubiquiti",
            snmp_sys_descr="EdgeOS ubnt-v2.0.9",
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ROUTER)
        self.assertEqual(
            result.reason,
            "Detected SNMP sysDescr 'EdgeOS ubnt-v2.0.9' matched known EdgeOS "
            "router identifier.",
        )

    def test_both_edgeos_title_and_ubiquitirouterui_tls_present_prefers_http_title(self):
        """Reproduces the exact real production evidence shape -- all 3
        real EdgeOS devices carry both the HTTP title and the TLS
        common name simultaneously. first_matching_identifier checks
        product, then HTTP title, then TLS subject/issuer, then HTTP
        auth realm, then SNMP sysDescr, in that fixed order, so with
        both present the match must deterministically resolve to the
        HTTP title tier, never the TLS tier."""
        device = Device(
            ip_address="172.16.100.4",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    http_title="EdgeOS",
                    tls_subject=(
                        "commonName=UbiquitiRouterUI/organizationName=Ubiquiti Inc."
                        "/stateOrProvinceName=New York/countryName=US"
                    ),
                    tls_issuer=(
                        "commonName=UbiquitiRouterUI/organizationName=Ubiquiti Inc."
                        "/stateOrProvinceName=New York/countryName=US"
                    ),
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ROUTER)
        self.assertEqual(
            result.reason,
            "Detected HTTP title 'EdgeOS' matched known EdgeOS router identifier.",
        )


if __name__ == "__main__":
    unittest.main()
