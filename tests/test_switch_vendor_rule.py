import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.switch_vendor_rule import SwitchVendorRule
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


class SwitchVendorRuleTest(unittest.TestCase):
    def test_matching_vendor_returns_rule_result_with_switch_type(self):
        device = Device(
            ip_address="192.168.1.40",
            hostname="sw-01",
            vendor="Cisco Systems",
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(result.reason, "Vendor 'Cisco Systems' matched known switch vendor.")

    def test_case_insensitive_vendor_matching(self):
        device = Device(
            ip_address="192.168.1.41",
            hostname="sw-02",
            vendor="cIsCo",
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(result.reason, "Vendor 'cIsCo' matched known switch vendor.")

    def test_non_matching_vendor_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.42",
            hostname="sw-03",
            vendor="Juniper",
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(result.reason, "Vendor 'Juniper' is not a known switch vendor.")

    def test_switch_hostname_with_management_signals_matches_without_vendor(self):
        device = Device(
            ip_address="192.168.1.43",
            hostname="switch-core-01",
            vendor="Unknown",
            services=[ServiceEvidence(port=161, protocol="udp", service="snmp")],
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Hostname 'switch-core-01' with open port 161 and service 'snmp' matched known switch management evidence.",
        )

    def test_switch_hostname_with_management_signal_and_cisco_product_enriches_reason(self):
        device = Device(
            ip_address="192.168.1.44",
            hostname="switch-core-02",
            vendor="Unknown",
            services=[
                ServiceEvidence(port=22, protocol="tcp", service="ssh", product="Cisco SSH"),
            ],
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Hostname 'switch-core-02' with open port 22 and service 'ssh' matched "
            "known switch management evidence. Detected service product 'Cisco SSH' "
            "matched known Cisco product identifier.",
        )

    def test_switch_hostname_without_management_signal_does_not_match_on_product_alone(self):
        device = Device(
            ip_address="192.168.1.45",
            hostname="switch-core-03",
            vendor="Unknown",
            services=[
                ServiceEvidence(port=80, protocol="tcp", product="Cisco embedded httpd"),
            ],
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_edgeswitch_http_title_classifies_as_switch_without_vendor_or_hostname(self):
        device = Device(
            ip_address="192.168.1.46",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_title="Ubiquiti EdgeSwitch"),
            ],
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Detected HTTP title 'Ubiquiti EdgeSwitch' matched known switch identifier.",
        )

    def test_procurve_product_classifies_as_switch_despite_hp_vendor(self):
        device = Device(
            ip_address="192.168.1.47",
            hostname="hp-sw-01",
            vendor="Hewlett-Packard",
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    product="HP ProCurve Switch 2530-24G",
                ),
            ],
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Detected service product 'HP ProCurve Switch 2530-24G' matched known "
            "switch identifier.",
        )

    def test_procurve_http_title_classifies_as_switch_without_hostname_hint(self):
        device = Device(
            ip_address="192.168.1.48",
            hostname="hpswitch01",
            vendor="HP",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    http_title="ProCurve Switch 2810-24G",
                ),
            ],
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Detected HTTP title 'ProCurve Switch 2810-24G' matched known switch identifier.",
        )

    def test_procurve_snmp_sys_descr_classifies_as_switch_without_vendor_or_hostname(self):
        """RULE-004: SNMP sysDescr participates in the same identifier tier
        as product string/HTTP title, using the existing switch identifier
        keyword list."""
        device = Device(
            ip_address="192.168.1.50",
            hostname=None,
            vendor="Hewlett-Packard",
            snmp_sys_descr="HP ProCurve Switch 2530-24G",
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Detected SNMP sysDescr 'HP ProCurve Switch 2530-24G' matched known "
            "switch identifier.",
        )

    def test_snmp_sys_descr_is_checked_after_service_evidence(self):
        """When both a service-derived identifier and SNMP sysDescr are
        present, the service-derived one is preferred for the reported
        label, consistent with "SNMP evidence corroborates, it does not
        override" (RULE-004)."""
        device = Device(
            ip_address="192.168.1.51",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_title="Ubiquiti EdgeSwitch"),
            ],
            snmp_sys_descr="EdgeSwitch 24-Lite, 6.2.9",
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Detected HTTP title 'Ubiquiti EdgeSwitch' matched known switch identifier.",
        )

    def test_unrelated_snmp_sys_descr_does_not_match(self):
        device = Device(
            ip_address="192.168.1.52",
            hostname="host-01",
            vendor="Unknown",
            snmp_sys_descr="Linux host-01 5.15.0 x86_64",
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_hp_vendor_without_switch_identifier_does_not_match(self):
        device = Device(
            ip_address="192.168.1.49",
            hostname="printer-01",
            vendor="HP",
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)


if __name__ == "__main__":
    unittest.main()
