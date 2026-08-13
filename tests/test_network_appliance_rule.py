import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.network_appliance_rule import NetworkApplianceRule
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


class NetworkApplianceRuleTest(unittest.TestCase):
    def setUp(self):
        self.rule = NetworkApplianceRule()

    def test_http_auth_realm_alone_classifies_as_server(self):
        """The exact BENCH-002 evidence shape (http-auth realm only)."""
        device = Device(
            ip_address="172.16.100.20",
            vendor=None,
            hostname=None,
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_auth_realm="NETGEAR ReadyNAS"),
            ],
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertEqual(
            result.reason,
            "Detected HTTP authentication realm 'NETGEAR ReadyNAS' matched known "
            "NAS/network appliance identifier.",
        )

    def test_http_title_alone_classifies_as_server(self):
        device = Device(
            ip_address="172.16.100.21",
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_title="ReadyNAS 214 - Login"),
            ],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertIn("HTTP title", result.reason)

    def test_product_string_alone_classifies_as_server(self):
        device = Device(
            ip_address="172.16.100.22",
            services=[
                ServiceEvidence(port=443, protocol="tcp", product="Netgear ReadyNAS httpd"),
            ],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertIn("service product", result.reason)

    def test_case_insensitive_identifier_matching(self):
        device = Device(
            ip_address="172.16.100.23",
            services=[ServiceEvidence(port=80, protocol="tcp", http_title="READYNAS Storage")],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)

    def test_vendor_corroborates_reason_when_present(self):
        device = Device(
            ip_address="172.16.100.20",
            vendor="Netgear",
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_auth_realm="NETGEAR ReadyNAS"),
            ],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(
            result.reason,
            "Detected HTTP authentication realm 'NETGEAR ReadyNAS' matched known "
            "NAS/network appliance identifier. Vendor 'Netgear' corroborates known "
            "NAS/network appliance vendor.",
        )

    def test_hostname_corroborates_reason_when_present(self):
        """The full BENCH-002 netgear-nas-01 evidence shape: identifier,
        vendor, and hostname all present and all corroborating."""
        device = Device(
            ip_address="172.16.100.20",
            vendor="Netgear",
            hostname="netgear-nas-01",
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_auth_realm="NETGEAR ReadyNAS"),
            ],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(
            result.reason,
            "Detected HTTP authentication realm 'NETGEAR ReadyNAS' matched known "
            "NAS/network appliance identifier. Vendor 'Netgear' corroborates known "
            "NAS/network appliance vendor. Hostname 'netgear-nas-01' corroborates "
            "known NAS naming convention.",
        )

    def test_bare_netgear_vendor_without_identifier_does_not_match(self):
        """Netgear also makes routers/switches/APs -- vendor alone must
        never independently trigger a match (RULE-003's "no single weak
        indicator" principle)."""
        device = Device(
            ip_address="172.16.100.24",
            vendor="Netgear",
            hostname="netgear-router-01",
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_bare_nas_hostname_without_identifier_does_not_match(self):
        device = Device(
            ip_address="172.16.100.25",
            vendor=None,
            hostname="nas-01",
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_unrelated_nas_brand_not_in_keyword_list_does_not_match(self):
        """Deliberately narrow scope: only the BENCH-002-observed
        ReadyNAS identifier is recognized today. A different NAS brand
        with no corroborated benchmark evidence is left for a future,
        similarly evidence-backed extension rather than guessed at."""
        device = Device(
            ip_address="172.16.100.26",
            services=[ServiceEvidence(port=80, protocol="tcp", http_title="Synology DiskStation")],
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)

    def test_snmp_sys_descr_alone_classifies_as_server(self):
        """RULE-004: SNMP sysDescr participates in the same identifier tier
        as product string/HTTP title/HTTP auth realm."""
        device = Device(
            ip_address="172.16.100.28",
            vendor=None,
            hostname=None,
            snmp_sys_descr="ReadyNAS 214, ReadyNASOS 6.10.8",
        )

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertEqual(
            result.reason,
            "Detected SNMP sysDescr 'ReadyNAS 214, ReadyNASOS 6.10.8' matched "
            "known NAS/network appliance identifier.",
        )

    def test_snmp_sys_descr_is_checked_after_service_evidence(self):
        device = Device(
            ip_address="172.16.100.29",
            services=[ServiceEvidence(port=80, protocol="tcp", http_auth_realm="NETGEAR ReadyNAS")],
            snmp_sys_descr="ReadyNAS 214, ReadyNASOS 6.10.8",
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(
            result.reason,
            "Detected HTTP authentication realm 'NETGEAR ReadyNAS' matched known "
            "NAS/network appliance identifier.",
        )

    def test_no_evidence_at_all_does_not_match(self):
        device = Device(ip_address="172.16.100.27")

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "No known NAS/network appliance identifier evidence was detected.",
        )


if __name__ == "__main__":
    unittest.main()
