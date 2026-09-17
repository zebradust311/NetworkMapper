import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.dell_workstation_rule import DellWorkstationRule
from networkmapper.core.models import Device, DeviceType


class DellWorkstationRuleTest(unittest.TestCase):
    def test_matching_vendor_returns_rule_result_with_workstation_type(self):
        device = Device(
            ip_address="192.168.1.70",
            hostname="ws-01",
            vendor="Dell Inc.",
        )

        result = DellWorkstationRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)
        self.assertEqual(result.reason, "Vendor 'Dell Inc.' matched known workstation vendor.")

    def test_case_insensitive_vendor_matching(self):
        device = Device(
            ip_address="192.168.1.71",
            hostname="ws-02",
            vendor="dElL",
        )

        result = DellWorkstationRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)
        self.assertEqual(result.reason, "Vendor 'dElL' matched known workstation vendor.")

    def test_non_matching_vendor_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.72",
            hostname="ws-03",
            vendor="Lenovo",
        )

        result = DellWorkstationRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(
            result.reason,
            "Vendor 'Lenovo' and hostname 'ws-03' did not match known workstation indicators.",
        )

    def test_bare_dell_vendor_still_matches_with_no_windows_server_evidence(self):
        """RULE-006: confirms DellWorkstationRule itself needed no code
        change -- its bare vendor match is unaffected when no Windows
        Server evidence is present. The Dell PowerEdge + Windows Server
        misclassification (SCT0008) is resolved entirely by
        WindowsServerRule's position in DeviceClassifier's ordering, not
        by any change inside this rule (see PLAN-RULE-006 Section 3.3)."""
        device = Device(
            ip_address="192.168.1.74",
            hostname="ws-04",
            vendor="Dell",
            operating_system="10.0.19041",
        )

        result = DellWorkstationRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)
        self.assertEqual(result.reason, "Vendor 'Dell' matched known workstation vendor.")

    def test_dell_workstation_hostname_pattern_matches_without_vendor(self):
        device = Device(
            ip_address="192.168.1.73",
            hostname="OPTIPLEX-7090",
            vendor="Unknown",
        )

        result = DellWorkstationRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.WORKSTATION)
        self.assertEqual(
            result.reason,
            "Hostname 'OPTIPLEX-7090' matched known Dell workstation naming pattern.",
        )


if __name__ == "__main__":
    unittest.main()