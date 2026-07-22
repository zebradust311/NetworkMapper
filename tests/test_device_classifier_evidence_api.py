import unittest

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.device_classifier import DeviceClassifier
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


class LegacyNonMatchingRule(ClassificationRule):
    def classify(self, device: Device) -> RuleResult:
        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason="No device evidence matched",
            suggested_device_type=None,
        )


class MatchingSwitchRule(ClassificationRule):
    def classify(self, device: Device) -> RuleResult:
        return RuleResult(
            matched=True,
            confidence_contribution=0,
            reason="Switch evidence matched",
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


class DeviceClassifierEvidenceApiTest(unittest.TestCase):
    def test_rule_results_are_available_after_classification(self):
        classifier = DeviceClassifier()
        classifier._rules = [LegacyNonMatchingRule(), MatchingSwitchRule()]

        device = Device(ip_address="192.168.1.10", hostname="host-01", vendor="Cisco")
        classifier.classify(device)

        evidence = classifier.get_last_rule_results()
        self.assertEqual(len(evidence), 2)
        self.assertIsInstance(evidence[0], RuleResult)
        self.assertIsInstance(evidence[1], RuleResult)
        self.assertFalse(evidence[0].matched)
        self.assertTrue(evidence[1].matched)
        self.assertEqual(evidence[1].suggested_device_type, DeviceType.SWITCH)

    def test_returned_collection_cannot_mutate_classifier_state(self):
        classifier = DeviceClassifier()
        classifier._rules = [MatchingSwitchRule()]

        device = Device(ip_address="192.168.1.11", hostname="host-02", vendor="Cisco")
        classifier.classify(device)

        evidence = classifier.get_last_rule_results()

        self.assertIsInstance(evidence, tuple)
        with self.assertRaises(TypeError):
            evidence[0] = RuleResult(
                matched=False,
                confidence_contribution=0,
                reason="tamper",
                suggested_device_type=None,
            )

        self.assertEqual(len(classifier.get_last_rule_results()), 1)
        self.assertTrue(classifier.get_last_rule_results()[0].matched)

    def test_rule_results_from_multiple_rules_appear_in_evidence(self):
        classifier = DeviceClassifier()
        classifier._rules = [LegacyNonMatchingRule(), StructuredMatchingRule()]

        device = Device(ip_address="192.168.1.12", hostname="host-03", vendor="Brother")
        classifier.classify(device)

        evidence = classifier.get_last_rule_results()

        self.assertEqual(len(evidence), 2)
        self.assertEqual(evidence[0].reason, "No device evidence matched")
        self.assertFalse(evidence[0].matched)
        self.assertEqual(evidence[0].confidence_contribution, 0)

        self.assertEqual(evidence[1].reason, "Structured rule matched")
        self.assertTrue(evidence[1].matched)
        self.assertEqual(evidence[1].confidence_contribution, 7)
        self.assertEqual(evidence[1].suggested_device_type, DeviceType.PRINTER)


if __name__ == "__main__":
    unittest.main()