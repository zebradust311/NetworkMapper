import unittest

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.device_classifier import DeviceClassifier
from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.cisco_switch_rule import CiscoSwitchRule
from networkmapper.classification.rules.printer_vendor_rule import PrinterVendorRule
from networkmapper.core.models import Device, DeviceType


class NonMatchingRule(ClassificationRule):
    def classify(self, device: Device) -> RuleResult:
        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason="Non-matching rule did not match",
            suggested_device_type=None,
        )


class MatchingSwitchRule(ClassificationRule):
    def classify(self, device: Device) -> RuleResult:
        return RuleResult(
            matched=True,
            confidence_contribution=0,
            reason="Switch rule matched",
            suggested_device_type=DeviceType.SWITCH,
        )


class StructuredMatchingRule(ClassificationRule):
    def classify(self, device: Device) -> RuleResult:
        return RuleResult(
            matched=True,
            confidence_contribution=7,
            reason="Structured rule matched",
            suggested_device_type=DeviceType.PRINTER,
        )


class RuleResultFrameworkTest(unittest.TestCase):
    def test_rule_result_creation(self):
        result = RuleResult(
            matched=True,
            confidence_contribution=5,
            reason="Vendor matched",
            suggested_device_type=DeviceType.FIREWALL,
        )

        self.assertTrue(result.matched)
        self.assertEqual(result.confidence_contribution, 5)
        self.assertEqual(result.reason, "Vendor matched")
        self.assertEqual(result.suggested_device_type, DeviceType.FIREWALL)

    def test_rule_results_are_collected_for_evaluated_rules(self):
        classifier = DeviceClassifier()
        classifier._rules = [
            NonMatchingRule(),
            MatchingSwitchRule(),
            StructuredMatchingRule(),
        ]

        device = Device(ip_address="192.168.1.10", hostname="host-01", vendor="Cisco")
        result = classifier.classify(device)

        self.assertEqual(result.device_type, DeviceType.SWITCH)
        self.assertEqual(len(classifier._last_rule_results), 2)
        self.assertFalse(classifier._last_rule_results[0].matched)
        self.assertTrue(classifier._last_rule_results[1].matched)
        self.assertEqual(
            classifier._last_rule_results[1].suggested_device_type,
            DeviceType.SWITCH,
        )

    def test_structured_rule_result_is_collected_and_used(self):
        classifier = DeviceClassifier()
        classifier._rules = [StructuredMatchingRule()]

        device = Device(ip_address="192.168.1.20", hostname="host-02", vendor="Brother")
        result = classifier.classify(device)

        self.assertEqual(result.device_type, DeviceType.PRINTER)
        self.assertEqual(len(classifier._last_rule_results), 1)
        self.assertEqual(
            classifier._last_rule_results[0].reason,
            "Structured rule matched",
        )
        self.assertEqual(classifier._last_rule_results[0].confidence_contribution, 7)

    def test_migrated_rule_result_is_collected_and_used(self):
        classifier = DeviceClassifier()
        classifier._rules = [CiscoSwitchRule()]

        device = Device(ip_address="192.168.1.30", vendor="Cisco")
        result = classifier.classify(device)

        self.assertEqual(result.device_type, DeviceType.SWITCH)
        self.assertEqual(len(classifier._last_rule_results), 1)
        self.assertTrue(classifier._last_rule_results[0].matched)
        self.assertEqual(
            classifier._last_rule_results[0].suggested_device_type,
            DeviceType.SWITCH,
        )

    def test_multiple_migrated_rules_classify_identically(self):
        classifier = DeviceClassifier()
        classifier._rules = [PrinterVendorRule(), CiscoSwitchRule()]

        printer_device = Device(ip_address="192.168.1.31", vendor="Brother")
        switch_device = Device(ip_address="192.168.1.32", vendor="Cisco")

        printer_result = classifier.classify(printer_device)
        self.assertEqual(printer_result.device_type, DeviceType.PRINTER)
        self.assertEqual(len(classifier._last_rule_results), 1)
        self.assertIsInstance(classifier._last_rule_results[0], RuleResult)

        switch_result = classifier.classify(switch_device)
        self.assertEqual(switch_result.device_type, DeviceType.SWITCH)
        self.assertEqual(len(classifier._last_rule_results), 2)
        self.assertFalse(classifier._last_rule_results[0].matched)
        self.assertTrue(classifier._last_rule_results[1].matched)


if __name__ == "__main__":
    unittest.main()