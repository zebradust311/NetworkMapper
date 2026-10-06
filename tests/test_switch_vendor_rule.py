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

    def test_tp_link_switch_product_classifies_as_switch(self):
        """RULE-008: the exact real production evidence shape -- a
        TP-Link-vendor device self-reporting an explicit switch product
        string, with no hostname or other switch signal."""
        device = Device(
            ip_address="172.16.102.12",
            hostname=None,
            vendor="TP-Link Technologies",
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    product="TP-LINK switch http admin",
                ),
            ],
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Detected service product 'TP-LINK switch http admin' matched known "
            "switch identifier.",
        )

    def test_tp_link_switch_product_matching_is_case_insensitive(self):
        device = Device(
            ip_address="172.16.102.65",
            hostname=None,
            vendor="TP-Link Technologies",
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    product="tp-link SWITCH http admin",
                ),
            ],
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)

    def test_tp_link_technologies_vendor_alone_does_not_match(self):
        """RULE-008: the real production evidence shape for a TP-Link
        device with no product/title/TLS/auth-realm evidence at all --
        must remain unmatched. Bare TP-Link vendor is deliberately never
        an independent trigger."""
        device = Device(
            ip_address="172.16.102.95",
            hostname=None,
            vendor="TP-Link Technologies",
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_tp_link_systems_vendor_alone_does_not_match(self):
        device = Device(
            ip_address="172.16.102.143",
            hostname=None,
            vendor="TP-Link Systems",
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_cisco_meraki_vendor_alone_does_not_match(self):
        """RULE-011: the exact real production evidence shape for
        172.16.100.70/172.16.102.80 -- vendor "Cisco Meraki" with no other
        evidence of any kind. Meraki spans switches, access points, and MX
        security appliances, so bare vendor identity cannot assert SWITCH."""
        device = Device(
            ip_address="172.16.100.70",
            hostname=None,
            vendor="Cisco Meraki",
        )

        result = SwitchVendorRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.reason, "Vendor 'Cisco Meraki' is not a known switch vendor.")

    def test_cisco_meraki_exclusion_is_case_insensitive(self):
        for vendor in ("cisco meraki", "CISCO MERAKI", "Cisco MERAKI"):
            with self.subTest(vendor=vendor):
                device = Device(
                    ip_address="172.16.102.80",
                    hostname=None,
                    vendor=vendor,
                )

                result = SwitchVendorRule().classify(device)

                self.assertFalse(result.matched)
                self.assertIsNone(result.suggested_device_type)

    def test_genuine_cisco_systems_device_still_matches_bare_vendor_tier(self):
        """RULE-011 regression guard: reproduces 172.16.100.1's real
        evidence shape. A non-Meraki Cisco vendor string must still match
        through the bare vendor tier, unchanged."""
        device = Device(
            ip_address="172.16.100.1",
            hostname=None,
            vendor="Cisco Systems",
            services=[
                ServiceEvidence(port=22, protocol="tcp", service="ssh", product="Cisco SSH"),
                ServiceEvidence(
                    port=80, protocol="tcp", service="http",
                    product="Cisco IOS http config",
                    http_title="Site doesn't have a title.",
                    http_auth_realm="level_15_access",
                ),
                ServiceEvidence(
                    port=443, protocol="tcp", service="https",
                    tls_subject="commonName=IOS-Self-Signed-Certificate-1970477952",
                    tls_issuer="commonName=IOS-Self-Signed-Certificate-1970477952",
                ),
            ],
        )

        result = SwitchVendorRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(result.reason, "Vendor 'Cisco Systems' matched known switch vendor.")

    def test_cisco_meraki_with_existing_identifier_still_matches_identifier_tier(self):
        """RULE-011 exclusion-scope regression guard (PLAN-RULE-011 Section
        6, Section 12 criterion 7). The Meraki exclusion applies only inside
        the bare Cisco vendor branch; it must never short-circuit later,
        higher-confidence tiers. A "Cisco Meraki" device carrying an
        already-supported identifier keyword must still match SWITCH via the
        identifier tier. If the exclusion were ever turned into an early
        return or a matched=False short-circuit, this test would fail."""
        device = Device(
            ip_address="192.168.1.60",
            hostname=None,
            vendor="Cisco Meraki",
            services=[
                ServiceEvidence(port=80, protocol="tcp", product="EdgeSwitch"),
            ],
        )

        result = SwitchVendorRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Detected service product 'EdgeSwitch' matched known switch identifier.",
        )
        self.assertNotIn("known switch vendor", result.reason)

    def test_cisco_meraki_with_switch_hostname_and_management_signal_still_matches(self):
        """RULE-011 exclusion-scope guard: the hostname + management-signal
        tier also remains reachable for a "Cisco Meraki" vendor string."""
        device = Device(
            ip_address="192.168.1.61",
            hostname="core-sw-01",
            vendor="Cisco Meraki",
            services=[ServiceEvidence(port=22, protocol="tcp", service="ssh")],
        )

        result = SwitchVendorRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SWITCH)
        self.assertEqual(
            result.reason,
            "Hostname 'core-sw-01' with open port 22 and service 'ssh' matched "
            "known switch management evidence.",
        )

    def test_cisco_meraki_with_unsupported_cisco_product_documents_future_intent(self):
        """RULE-011 documented hypothetical (PLAN-RULE-011 Section 11). A
        "Cisco Meraki" device with a Cisco product-line identifier such as
        "Cisco Catalyst Switch" must remain reachable by a future,
        evidence-backed identifier-tier Cisco keyword. No "catalyst" (or any
        other Cisco/Meraki) keyword exists in this sprint, so today this
        device does not match -- because that identifier keyword is missing,
        not because of the Meraki exclusion, which declines only inside the
        bare vendor branch. If a later sprint adds such a keyword, this
        expectation should flip to SWITCH via the identifier tier."""
        device = Device(
            ip_address="192.168.1.62",
            hostname=None,
            vendor="Cisco Meraki",
            services=[
                ServiceEvidence(port=443, protocol="tcp", product="Cisco Catalyst Switch"),
            ],
        )

        result = SwitchVendorRule().classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)


if __name__ == "__main__":
    unittest.main()
